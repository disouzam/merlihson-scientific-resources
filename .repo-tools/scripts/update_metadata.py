#!/usr/bin/env python3
"""
Enhanced updater for metadata and ALL documentation files.
Automatically updates:
- Metadata files (CSV, TXT)
- README.md statistics
- METADATA_UPDATE_PROCESS.md statistics
- All review counts, file paths, and dates
"""
import re
import csv as csv_module
import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime

def clean_title(title: str) -> str:
    """Remove emojis and [Short] markers from title."""
    # Remove [Short] markers
    title = re.sub(r'\[[Ss]hort\]\s*:?\s*', '', title)

    # Remove emojis
    emoji_pattern = re.compile("[" "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    title = emoji_pattern.sub('', title)

    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()

    return title

def _is_english_title(text: str) -> bool:
    """Check if text is a valid English paper title (not Hebrew, not a formula, long enough)."""
    if not text or len(text) < 10:
        return False
    # Must contain letters
    if not re.search(r'[A-Za-z]', text):
        return False
    # Must be predominantly ASCII (English)
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text)
    if ascii_ratio < 0.7:
        return False
    # Reject if contains Hebrew characters
    if re.search(r'[\u0590-\u05FF]', text):
        return False
    # Reject if it looks like a math formula (no words longer than 3 chars)
    words = re.findall(r'[A-Za-z]+', text)
    if not words or max(len(w) for w in words) < 4:
        return False
    return True


def _extract_title_from_lines(lines: List[str]) -> Optional[str]:
    """Try to extract an English paper title from review file lines."""
    # Strategy 1: Check if first line has "Review X: Title" format
    if lines and lines[0]:
        first_line = lines[0]
        review_match = re.match(r'^Review\s+\d+[ab]?:\s*(.+)$', first_line, re.IGNORECASE)
        if review_match:
            candidate = review_match.group(1).strip()
            if _is_english_title(candidate):
                return candidate

    # Strategy 2: Look for English title in first 15 lines
    for line in lines[:15]:
        if not line or len(line) < 10:
            continue

        # Skip lines that start with known non-title patterns
        if re.match(r'^(Review|Paper:|v\d+$|תחום|מושגים)', line):
            continue

        # If line has Hebrew header keywords, try to extract English part after date/number
        if 'סקירה' in line or 'המאמר' in line or 'סקירת' in line:
            # "...סקירות עד XXX Title"
            hebrew_match = re.search(r'סקירות עד \d+\s+(.+)$', line)
            if hebrew_match:
                candidate = hebrew_match.group(1).strip()
                if _is_english_title(candidate):
                    return candidate

            # "DD.MM.YY Title" or "DD.MM.YY: Title"
            date_match = re.search(r'\d{2}\.\d{2}\.\d{2}[:\s]+([A-Z].+)$', line)
            if not date_match:
                date_match = re.search(r'\d{2}\.\d{2}\.\d{2}([A-Za-z].+)$', line)
            if date_match:
                candidate = date_match.group(1).strip()
                if _is_english_title(candidate):
                    return candidate

            # "...1024.TITLE"
            period_match = re.search(r'\d{4}\.([A-Z][A-Za-z\s:,-]+)', line)
            if period_match:
                candidate = period_match.group(1).strip()
                if _is_english_title(candidate):
                    return candidate

            continue

        # Standalone line with significant English content
        if _is_english_title(line):
            return line

    return None


def extract_title_and_link(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Extract paper title and arxiv link from a review markdown file.

    Tries the Hebrew review file first. If no valid English title is found,
    falls back to the corresponding English review file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]

        title = None
        arxiv_link = None

        # Try extracting title from Hebrew file
        title = _extract_title_from_lines(lines)

        # Always prefer English review file title when available — it has the
        # canonical English paper name in "Review N: Title" format on line 1.
        english_dir = file_path.parent.parent / "split-english-reviews-md"
        english_file = english_dir / file_path.name
        if english_file.exists():
            with open(english_file, 'r', encoding='utf-8') as f:
                english_lines = [line.strip() for line in f.readlines()]
            english_title = _extract_title_from_lines(english_lines)
            if english_title:
                title = english_title

        # Look for paper link (can appear anywhere in the file)
        # Priority 1: arxiv links
        for line in lines:
            if 'arxiv' in line.lower():
                # Extract the arxiv URL - handle various typos and missing protocols
                arxiv_match = re.search(
                    r'(?:https?:?/+)?(?:www\.)?arxiv\.org/(?:abs|pdf|absl)/[\d.]+(?:v\d+)?',
                    line,
                    re.IGNORECASE
                )
                if arxiv_match:
                    arxiv_link = arxiv_match.group(0)
                    # Normalize: ensure https://, remove www., change /pdf/ to /abs/, fix /absl/ typo
                    if not arxiv_link.startswith('http'):
                        arxiv_link = 'https://' + arxiv_link
                    arxiv_link = arxiv_link.replace('www.arxiv.org', 'arxiv.org')
                    arxiv_link = arxiv_link.replace('/pdf/', '/abs/')
                    arxiv_link = arxiv_link.replace('/absl/', '/abs/')
                    # Fix single-slash typo: https:/arxiv -> https://arxiv
                    arxiv_link = re.sub(r'https?:/([^/])', r'https://\1', arxiv_link)
                    break

        # Priority 2: If no arxiv link, look for other paper sources
        if not arxiv_link:
            paper_sources = [
                r'https?://(?:www\.)?(?:cdn\.)?openai\.com/(?:papers|index)/[^\s\)]+',  # OpenAI
                r'https?://(?:www\.)?aclanthology\.org/[^\s\)]+',  # ACL Anthology
                r'https?://(?:www\.)?nature\.com/articles/[^\s\)]+',  # Nature
                r'https?://(?:www\.)?dl\.acm\.org/doi/[^\s\)]+',  # ACM
                r'https?://(?:www\.)?doi\.org/[^\s\)]+',  # DOI
                r'https?://(?:www\.)?openreview\.net/forum\?id=[^\s\)]+',  # OpenReview
                r'https?://(?:www\.)?researchsquare\.com/article/[^\s\)]+',  # Research Square
                r'https?://(?:www\.)?research\.google/blog/[^\s\)]+',  # Google Research
                r'https?://(?:www\.)?sciencedirect\.com/science/article/[^\s\)]+',  # ScienceDirect
                r'https?://(?:www\.)?huggingface\.co/papers/[^\s\)]+',  # HuggingFace Papers
            ]

            for line in lines:
                for pattern in paper_sources:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        arxiv_link = match.group(0)
                        # Ensure proper protocol
                        if not arxiv_link.startswith('http'):
                            arxiv_link = 'https://' + arxiv_link
                        break
                if arxiv_link:
                    break

        # Clean the title if found
        if title:
            title = clean_title(title)

        return title, arxiv_link

    except Exception as e:
        print(f"Error extracting from {file_path.name}: {e}")
        return None, None

def get_repo_stats(repo_root: Path) -> Dict[str, Any]:
    """Get repository statistics for documentation updates."""
    stats = {}

    # Count Hebrew reviews
    hebrew_reviews = list((repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md").glob("Review_*.md"))
    stats['hebrew_reviews'] = len(hebrew_reviews)
    stats['reviews'] = len(hebrew_reviews)  # Alias for backward compatibility

    # Count English reviews
    english_reviews_path = repo_root / "mike-paper-reviews-all" / "split-english-reviews-md"
    if english_reviews_path.exists():
        english_reviews = list(english_reviews_path.glob("Review_*.md"))
        stats['english_reviews'] = len(english_reviews)
    else:
        stats['english_reviews'] = 0

    # Count DOCX files
    docx_path = repo_root / "mike-paper-reviews-all" / "split-reviews-docx"
    if docx_path.exists():
        docx_files = list(docx_path.glob("Review_*.docx"))
        stats['docx_files'] = len(docx_files)
    else:
        stats['docx_files'] = stats['hebrew_reviews']

    # Count reviews with links from CSV
    csv_path = repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "paper_with_links.csv"
    if csv_path.exists():
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv_module.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                # Count rows with non-empty link (3rd column)
                stats['reviews_with_links'] = sum(1 for row in rows if len(row) >= 3 and row[2].strip())
        except:
            stats['reviews_with_links'] = stats['hebrew_reviews']
    else:
        stats['reviews_with_links'] = stats['hebrew_reviews']

    # Get highest review number
    if hebrew_reviews:
        review_numbers = []
        for f in hebrew_reviews:
            match = re.search(r'Review_(\d+)\.md', f.name)
            if match:
                review_numbers.append(int(match.group(1)))
        stats['max_review'] = max(review_numbers) if review_numbers else 1
    else:
        stats['max_review'] = 1

    # Count learning categories
    learning_materials = repo_root / "learning-materials"
    if learning_materials.exists():
        categories = [d for d in learning_materials.iterdir() if d.is_dir() and not d.name.startswith('.')]
        stats['categories'] = len(categories)
    else:
        stats['categories'] = 21  # Default

    # Count presentations
    presentations = repo_root / "presentations"
    if presentations.exists():
        presentation_files = list(presentations.glob("*.pdf"))
        stats['presentations'] = len(presentation_files)
    else:
        stats['presentations'] = 9  # Default

    # Get repo size (approximate)
    try:
        total_size = sum(f.stat().st_size for f in repo_root.rglob('*') if f.is_file() and not '.git' in str(f))
        stats['size_gb'] = total_size / (1024**3)  # Convert to GB
    except:
        stats['size_gb'] = 2.0  # Default

    # Daily reviews start at 209
    stats['daily_reviews'] = 209

    # Get current date for "Last Updated"
    stats['current_date'] = datetime.now().strftime("%B %-d, %Y")  # e.g., "February 6, 2026"

    return stats

def update_readme(readme_path: Path, stats: Dict[str, Any]) -> bool:
    """Update README with current statistics."""
    try:
        content = readme_path.read_text(encoding='utf-8')
    except IOError as e:
        print(f"Error reading {readme_path}: {e}")
        return False

    original_content = content

    # Enhanced patterns to update in README
    patterns = [
        # Highlights table
        (r'(<h3>📄 )\d+\+?(</h3>)', r'\g<1>{reviews}+\2'),
        (r'(<h3>📚 )\d+(</h3>)', r'\g<1>{categories}\2'),
        (r'(<h3>🎯 )[\d.]+( GB</h3>)', r'\g<1>{size_gb:.1f}\2'),

        # Quick Start table - file path ranges
        (r'(\| Individual review files \(DOCX\) \| `mike-paper-reviews-all/split-reviews-docx/Review_001\.docx` - `Review_)\d+(\.docx` \|)',
         r'\g<1>{max_review:03d}\2'),
        (r'(\| Individual reviews \(Markdown\) \| `mike-paper-reviews-all/split-hebrew-reviews-md/Review_001\.md` - `Review_)\d+(\.md` \|)',
         r'\g<1>{max_review:03d}\2'),

        # Paper Reviews section - main description
        (r'(The core collection containing \*\*)\d+( individual paper reviews\*\*)', r'\g<1>{reviews}\2'),

        # Paper Reviews section - Daily Reviews range
        (r'(\| \*\*Daily Reviews\*\* \| )209-\d+', r'\g<1>209-{max_review}'),

        # Formats Available section
        (r'(- \*\*`split-hebrew-reviews-md/`\*\* - )\d+( Hebrew review markdown files)', r'\g<1>{hebrew_reviews}\2'),
        (r'(- \*\*`split-english-reviews-md/`\*\* - )\d+( English review markdown files)', r'\g<1>{english_reviews}\2'),
        (r'(- \*\*`split-reviews-docx/`\*\* - )\d+ DOCX source files \(`Review_001\.docx` → `Review_\d+\.docx`\)',
         r'\g<1>{docx_files} DOCX source files (`Review_001.docx` → `Review_{max_review:03d}.docx`)'),

        # Automated Metadata Updates section
        (r'(\| \*\*Total Reviews\*\* \| )\d+( \|[^\n]*\n[^\n]*\| \*\*With Paper Links\*\* \| )\d+',
         r'\g<1>{reviews}\g<2>{reviews_with_links}'),

        # Collection Statistics table
        (r'(\| \*\*Total Paper Reviews\*\* \| )\d+', r'\g<1>{reviews}'),
        (r'(\| \*\*Hebrew Reviews \(Markdown\)\*\* \| )\d+( files)', r'\g<1>{hebrew_reviews}\2'),
        (r'(\| \*\*English Reviews \(Markdown\)\*\* \| )\d+( files)', r'\g<1>{english_reviews}\2'),
        (r'(\| \*\*Reviews with Paper Links\*\* \| )\d+( \(100% coverage!\))', r'\g<1>{reviews_with_links}\2'),
        (r'(\| \*\*Daily Reviews\*\* \| )\d+', r'\g<1>{daily_reviews}'),
        (r'(\| \*\*Learning Categories\*\* \| )\d+', r'\g<1>{categories}'),
        (r'(\| \*\*Presentations\*\* \| )\d+', r'\g<1>{presentations}'),
        (r'(\| \*\*Total Repository Size\*\* \| )[\d.]+( GB)', r'\g<1>{size_gb:.1f}\2'),

        # Repository Structure section
        (r'(│   ├── split-hebrew-reviews-md/     # )\d+( Hebrew review markdown files)', r'\g<1>{hebrew_reviews}\2'),
        (r'(│   │   └── \.\.\. → Review_)\d+(\.md)', r'\g<1>{max_review:03d}\2'),
        (r'(│   ├── split-english-reviews-md/    # )\d+( English review markdown files)', r'\g<1>{english_reviews}\2'),
        (r'(│   ├── split-reviews-docx/          # )\d+( DOCX source files)', r'\g<1>{docx_files}\2'),
        (r'(│   │   └── \.\.\. → Review_)\d+(\.docx)', r'\g<1>{max_review:03d}\2'),
        (r'(│   │   ├── paper_with_links\.csv     # )\d+( reviews with links)', r'\g<1>{reviews_with_links}\2'),

        # For Researchers section
        (r'(- \*\*Literature Reviews\*\*: )\d+( analyzed papers)', r'\g<1>{reviews}\2'),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        formatted_replacement = replacement.format(**stats)
        content = re.sub(pattern, formatted_replacement, content)

    # Write if changed
    if content != original_content:
        try:
            readme_path.write_text(content, encoding='utf-8')
            return True
        except IOError as e:
            print(f"Error writing {readme_path}: {e}")
            return False

    return False

def update_metadata_doc(doc_path: Path, stats: Dict[str, Any]) -> bool:
    """Update METADATA_UPDATE_PROCESS.md with current statistics."""
    if not doc_path.exists():
        print(f"Warning: {doc_path} not found, skipping")
        return False

    try:
        content = doc_path.read_text(encoding='utf-8')
    except IOError as e:
        print(f"Error reading {doc_path}: {e}")
        return False

    original_content = content

    # Calculate expected CSV line count (header + reviews)
    csv_lines = stats['reviews'] + 1

    # Patterns to update in METADATA_UPDATE_PROCESS.md
    patterns = [
        # Current Statistics table
        (r'(\| \*\*Total Reviews\*\* \| )\d+', r'\g<1>{reviews}'),
        (r'(\| \*\*With Paper Links\*\* \| )\d+( \(100% coverage!\))', r'\g<1>{reviews_with_links}\2'),
        (r'(\| \*\*Hebrew Reviews\*\* \| )\d+( markdown files)', r'\g<1>{hebrew_reviews}\2'),
        (r'(\| \*\*English Reviews\*\* \| )\d+( markdown files)', r'\g<1>{english_reviews}\2'),
        (r'(\| \*\*DOCX Source Files\*\* \| )\d+( files)', r'\g<1>{docx_files}\2'),

        # Manual verification - CSV line count
        (r'(# Should show: )\d+( \(1 header \+ )\d+( reviews\))', r'\g<1>{csv_lines}\g<2>{reviews}\3'),

        # Quality Assurance checklist
        (r'(Total count matches in all files \()\d+( reviews\))', r'\g<1>{reviews}\2'),
        (r'(Sequential numbering with no gaps \(Review_001 to Review_)\d+(\))', r'\g<1>{max_review:03d}\2'),

        # Last Updated date
        (r'(\*\*Last Updated:\*\* )[^\n]+', r'\g<1>{current_date}'),

        # Coverage at bottom
        (r'(\*\*Coverage:\*\* )\d+/\d+( reviews)', r'\g<1>{reviews}/{reviews}\2'),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        formatted_replacement = replacement.format(**stats, csv_lines=csv_lines)
        content = re.sub(pattern, formatted_replacement, content)

    # Write if changed
    if content != original_content:
        try:
            doc_path.write_text(content, encoding='utf-8')
            return True
        except IOError as e:
            print(f"Error writing {doc_path}: {e}")
            return False

    return False

def update_paper_reviews_readme(readme_path: Path, stats: Dict[str, Any]) -> bool:
    """Update mike-paper-reviews-all/readme.md with current statistics."""
    if not readme_path.exists():
        print(f"Warning: {readme_path} not found, skipping")
        return False

    try:
        content = readme_path.read_text(encoding='utf-8')
    except IOError as e:
        print(f"Error reading {readme_path}: {e}")
        return False

    original_content = content

    # Calculate daily reviews count
    daily_count = stats['reviews'] - 208  # Reviews 209-XXX

    # Get current date for Last Updated
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")

    # Patterns to update
    patterns = [
        # Header section
        (r'(\*\*Total Reviews\*\*: )\d+', r'\g<1>{reviews}'),
        (r'(Review_001 to Review_)\d+', r'\g<1>{max_review:03d}'),
        (r'(\*\*Last Updated\*\*: ).*', r'\g<1>' + current_date),

        # Reviews range in structure section
        (r'(Reviews 1-)\d+', r'\g<1>{reviews}'),
        (r'(Reviews 209-)\d+', r'\g<1>{max_review:03d}'),
        (r'(Daily Reviews \()\d+( files\))', r'\g<1>' + str(daily_count) + r'\2'),

        # Statistics section
        (r'(\*\*Total Individual Files\*\*: )\d+', r'\g<1>{reviews}'),
        (r'(\*\*Individual Reviews\*\*: )\d+( files)', r'\g<1>208\2'),
        (r'(\*\*Daily Reviews\*\*: )\d+', r'\g<1>' + str(daily_count)),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement.format(**stats, daily_count=daily_count), content)

    if content != original_content:
        try:
            readme_path.write_text(content, encoding='utf-8')
            return True
        except IOError as e:
            print(f"Error writing {readme_path}: {e}")
            return False

    return False

def update_presentations_readme(readme_path: Path, stats: Dict[str, Any]) -> bool:
    """Update presentations/readme.md with current presentation count."""
    if not readme_path.exists():
        print(f"Warning: {readme_path} not found, skipping")
        return False

    try:
        content = readme_path.read_text(encoding='utf-8')
    except IOError as e:
        print(f"Error reading {readme_path}: {e}")
        return False

    original_content = content

    # Pattern to update presentation count
    patterns = [
        (r'(\*\*Total Presentations\*\*: )\d+( PDF files)', r'\g<1>{presentations}\2'),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement.format(**stats), content)

    if content != original_content:
        try:
            readme_path.write_text(content, encoding='utf-8')
            return True
        except IOError as e:
            print(f"Error writing {readme_path}: {e}")
            return False

    return False

def update_claude_md(claude_path: Path, stats: Dict[str, Any]) -> bool:
    """Update CLAUDE.md with current review counts (only numeric stats)."""
    if not claude_path.exists():
        print(f"Warning: {claude_path} not found, skipping")
        return False

    try:
        content = claude_path.read_text(encoding='utf-8')
    except IOError as e:
        print(f"Error reading {claude_path}: {e}")
        return False

    original_content = content

    # Only update numeric review counts, nothing else
    patterns = [
        # First paragraph: "577+ AI/ML paper reviews" → "578+ AI/ML paper reviews"
        (r'(A curated knowledge base of )\d+(\+ AI/ML paper reviews)', r'\g<1>{reviews}\2'),

        # Hebrew reviews count: "577 files" → "578 files"
        (r'(split-hebrew-reviews-md/\` \()\d+( files, primary\))', r'\g<1>{hebrew_reviews}\2'),

        # English reviews count: "210 files" → "211 files"
        (r'(split-english-reviews-md/\` \()\d+( files\))', r'\g<1>{english_reviews}\2'),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement.format(**stats), content)

    if content != original_content:
        try:
            claude_path.write_text(content, encoding='utf-8')
            return True
        except IOError as e:
            print(f"Error writing {claude_path}: {e}")
            return False

    return False

def main():
    """Main function to update metadata and all documentation."""
    # Use git to find repo root (works from any directory in the repo)
    import subprocess
    try:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True, check=True)
        repo_root = Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Fallback to hardcoded path
        repo_root = Path("/Users/michaelerlihson/Personal/repos/scientific_repo")

    reviews_path = repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md"
    metadata_path = repo_root / "mike-paper-reviews-all" / "reviews_metadata"

    if not reviews_path.exists():
        print(f"Error: Reviews path not found: {reviews_path}")
        return 1

    print("📝 Extracting metadata from Hebrew review files...")

    # Extract all reviews
    reviews_data = []
    review_files = sorted(reviews_path.glob("Review_*.md"))

    for review_file in review_files:
        match = re.search(r'Review_(\d+)\.md$', review_file.name)
        if not match:
            continue

        review_num = int(match.group(1))
        title, link = extract_title_and_link(review_file)

        if title:
            reviews_data.append({
                "review_num": review_num,
                "title": title,
                "link": link or ""
            })

    print(f"✓ Extracted {len(reviews_data)} reviews")

    # Count missing links
    missing_links = [r for r in reviews_data if not r["link"]]
    print(f"  Reviews with missing links: {len(missing_links)}")

    # Update metadata files
    print("\n📊 Updating metadata files...")

    # Update paper_with_links.csv
    csv_path = metadata_path / "paper_with_links.csv"
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv_module.writer(f)
        writer.writerow(['review_number', 'title', 'link'])
        for review in reviews_data:
            review_id = f"Review_{review['review_num']:03d}"
            title = re.sub(r'\s+', ' ', review['title']).strip()
            link = review['link']
            writer.writerow([review_id, title, link])

    print(f"✓ Updated {csv_path.name}")

    # Update all_paper_titles.txt
    titles_path = metadata_path / "all_paper_titles.txt"
    with open(titles_path, 'w', encoding='utf-8') as f:
        for review in reviews_data:
            title = re.sub(r'\s+', ' ', review['title']).strip()
            f.write(f"{review['review_num']}. {title}\n")

    print(f"✓ Updated {titles_path.name}")

    # Update clean_titles_for_search.txt
    clean_path = metadata_path / "clean_titles_for_search.txt"
    with open(clean_path, 'w', encoding='utf-8') as f:
        for review in reviews_data:
            title = re.sub(r'\s+', ' ', review['title']).strip()
            f.write(f"{title}\n")

    print(f"✓ Updated {clean_path.name}")

    # Update reviews_from_208_titles.txt
    reviews_208_plus = [r for r in reviews_data if r['review_num'] >= 208]
    titles_208_path = metadata_path / "reviews_from_208_titles.txt"
    with open(titles_208_path, 'w', encoding='utf-8') as f:
        f.write("# 📚 Paper Titles from Reviews 208+ (Auto-generated)\n")
        f.write(f"# Successfully extracted: {len(reviews_208_plus)} titles\n")
        f.write("\n")
        for idx, review in enumerate(reviews_208_plus, 1):
            title = re.sub(r'\s+', ' ', review['title']).strip()
            f.write(f"  {idx}. {title}\n")

    print(f"✓ Updated {titles_208_path.name}")

    # Get repository statistics
    print("\n📊 Collecting repository statistics...")
    stats = get_repo_stats(repo_root)

    # Update README
    print("\n📄 Updating README.md...")
    readme_path = repo_root / "README.md"

    if update_readme(readme_path, stats):
        print(f"✓ Updated README.md with current statistics")
    else:
        print(f"  README.md already up to date")

    # Update METADATA_UPDATE_PROCESS.md
    print("\n📄 Updating METADATA_UPDATE_PROCESS.md...")
    metadata_doc_path = repo_root / "METADATA_UPDATE_PROCESS.md"

    if update_metadata_doc(metadata_doc_path, stats):
        print(f"✓ Updated METADATA_UPDATE_PROCESS.md with current statistics")
    else:
        print(f"  METADATA_UPDATE_PROCESS.md already up to date")

    # Update mike-paper-reviews-all/readme.md
    print("\n📄 Updating mike-paper-reviews-all/readme.md...")
    paper_reviews_readme = repo_root / "mike-paper-reviews-all" / "readme.md"

    if update_paper_reviews_readme(paper_reviews_readme, stats):
        print(f"✓ Updated mike-paper-reviews-all/readme.md with current statistics")
    else:
        print(f"  mike-paper-reviews-all/readme.md already up to date")

    # Update presentations/readme.md
    print("\n📄 Updating presentations/readme.md...")
    presentations_readme = repo_root / "presentations" / "readme.md"

    if update_presentations_readme(presentations_readme, stats):
        print(f"✓ Updated presentations/readme.md with current statistics")
    else:
        print(f"  presentations/readme.md already up to date")

    # Update CLAUDE.md (only numeric stats)
    print("\n📄 Updating CLAUDE.md...")
    claude_path = repo_root / "CLAUDE.md"

    if update_claude_md(claude_path, stats):
        print(f"✓ Updated CLAUDE.md with current review counts")
    else:
        print(f"  CLAUDE.md already up to date")

    print(f"\n✅ All files updated successfully!")
    print(f"\n📊 Repository Statistics:")
    print(f"   Hebrew reviews: {stats['hebrew_reviews']}")
    print(f"   English reviews: {stats['english_reviews']}")
    print(f"   DOCX files: {stats['docx_files']}")
    print(f"   Reviews with links: {stats['reviews_with_links']} ({stats['reviews_with_links']/stats['reviews']*100:.1f}%)")
    print(f"   Latest review: Review_{stats['max_review']:03d}")
    print(f"   Missing links: {len(missing_links)}")
    print(f"   Categories: {stats['categories']}")
    print(f"   Presentations: {stats['presentations']}")
    print(f"   Repo size: {stats['size_gb']:.1f} GB")

    return 0

if __name__ == "__main__":
    exit(main())
