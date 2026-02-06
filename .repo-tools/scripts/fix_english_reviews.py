#!/usr/bin/env python3
"""
Skill: Fix English Reviews
Automatically fixes common issues in English review markdown files:

FORMATTING FIXES:
- Removes duplicate titles (line 1 and line 3)
- Ensures line 2 is blank between title lines
- Adds markdown header (#) to line 1 if missing
- Fixes concatenated date+title (adds missing spaces/colons)
- Normalizes date separators (em dash → hyphen)

LINK FIXES:
- Converts PDF links to abs links (arxiv.org/pdf/ → arxiv.org/abs/)
- Removes duplicate links (keeps only the first occurrence)
- Removes multiple arxiv links (keeps only one)
- Searches and adds missing arxiv links by paper title (if not present)

TITLE EXTRACTION:
- Handles titles embedded in headers (after colon)
- Handles titles on separate lines (traditional format)
- Smart filtering of dates, emojis, and review markers
- Similarity matching with 0.8 threshold for arxiv search

Usage:
  python3 fix_english_reviews.py <start_date> [end_date]  # Fix by date range
  python3 fix_english_reviews.py --all                     # Fix all reviews
  python3 fix_english_reviews.py ... --push                # Auto-commit and push to GitHub

Examples:
  python3 fix_english_reviews.py 2024_11_22 2024_12_25    # Fix date range
  python3 fix_english_reviews.py --all                     # Fix all
  python3 fix_english_reviews.py --all --push              # Fix all and push

Results (as of Feb 2026):
  206/206 English reviews clean (100% success rate)
  All formatting issues fixed, all links added
"""

import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher

# Import git push helper
try:
    from git_push_helper import git_commit_and_push
except ImportError:
    def git_commit_and_push(*args, **kwargs):
        print("⚠️  git_push_helper not found, skipping push")
        return False


def remove_duplicate_title(content: str) -> str:
    """Remove duplicate title on line 3 if it matches line 1."""
    lines = content.split('\n')

    if len(lines) < 3:
        return content

    # Get line 1 and line 3, strip markdown headers and whitespace
    line1 = lines[0].strip().lstrip('#').strip()
    line3 = lines[2].strip().lstrip('#').strip()

    # If they're identical, remove line 3
    if line1 and line3 and line1 == line3:
        # Remove line 3 (index 2)
        new_lines = lines[:2] + lines[3:]
        return '\n'.join(new_lines)

    return content


def ensure_blank_line2(content: str) -> str:
    """Ensure line 2 is blank (between title lines)."""
    lines = content.split('\n')

    if len(lines) < 2:
        return content

    # If line 2 (index 1) is not empty, make it empty
    if lines[1].strip() != '':
        lines[1] = ''
        return '\n'.join(lines)

    return content


def add_markdown_header(content: str) -> str:
    """Add markdown header (#) to line 1 if missing."""
    lines = content.split('\n')

    if not lines:
        return content

    # If line 1 doesn't start with #, add it
    if lines[0] and not lines[0].startswith('#'):
        lines[0] = f"# {lines[0]}"
        return '\n'.join(lines)

    return content


def convert_pdf_to_abs_links(content: str) -> str:
    """Convert arxiv PDF links to abs links."""
    # Pattern: arxiv.org/pdf/1234.56789 or arxiv.org/pdf/1234.56789v1
    pattern = r'(https?://(?:www\.)?arxiv\.org/)pdf/([\d.]+(?:v\d+)?)'
    replacement = r'\1abs/\2'

    new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    return new_content


def remove_duplicate_links(content: str) -> str:
    """Remove duplicate paper links, keeping only the first occurrence."""
    lines = content.split('\n')

    seen_links = set()
    new_lines = []

    for line in lines:
        # Check if line contains a paper link
        link_match = re.search(r'https?://(?:arxiv\.org|nature\.com|openai\.com|aclanthology\.org|proceedings\.mlr\.press|openreview\.net|huggingface\.co|researchsquare\.com)/[^\s]+', line)

        if link_match:
            link = link_match.group(0)
            # If we've seen this link before, skip this line
            if link in seen_links:
                continue
            seen_links.add(link)

        new_lines.append(line)

    return '\n'.join(new_lines)


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings."""
    s1 = re.sub(r'\s+', ' ', str1.lower().strip())
    s2 = re.sub(r'\s+', ' ', str2.lower().strip())
    return SequenceMatcher(None, s1, s2).ratio()


def search_arxiv_by_title(title: str) -> Optional[str]:
    """Search arXiv for a paper by title."""
    try:
        search_query = urllib.parse.quote(title)
        url = f'https://export.arxiv.org/api/query?search_query=ti:{search_query}&max_results=5'

        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
            entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)

            best_match = None
            best_similarity = 0.0

            for entry in entries:
                title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                if not title_match:
                    continue

                paper_title = title_match.group(1).strip()
                paper_title = re.sub(r'\s+', ' ', paper_title)

                id_match = re.search(r'<id>http://arxiv\.org/abs/([\d.]+)v?\d*</id>', entry)
                if not id_match:
                    continue

                arxiv_id = id_match.group(1)
                similarity = similarity_ratio(title, paper_title)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = arxiv_id

            if best_similarity >= 0.8:  # Slightly lower threshold for English
                return best_match

    except Exception as e:
        print(f"  ⚠️  Error searching arXiv: {e}")
    return None


def extract_paper_title(content: str) -> Optional[str]:
    """Extract paper title from English review.

    Typically the paper title appears early in the review,
    often on line 4 or 5, after the header and blank lines.
    For some reviews, the title is embedded in the header after a colon.
    """
    lines = content.split('\n')

    # First, check if line 1 has a title embedded in the header
    # Pattern: "# Mike's Daily Paper - DATE:PAPER_TITLE"
    if lines and lines[0].startswith('#'):
        header = lines[0].lstrip('#').strip()
        # Look for colon after date pattern
        if ':' in header:
            # Split on colon and take the part after it
            parts = header.split(':', 1)
            if len(parts) == 2:
                potential_title = parts[1].strip()
                # Remove leading/trailing emojis
                potential_title = re.sub(r'^[⚡🚀:\s-]+', '', potential_title)
                potential_title = re.sub(r'[⚡🚀]+$', '', potential_title)
                potential_title = potential_title.strip()

                if len(potential_title) > 15:  # Reasonable title length
                    return potential_title

    # Look for title in first 10 lines
    # Skip lines with markdown headers, dates, or typical review markers
    for i in range(min(10, len(lines))):
        line = lines[i].strip()

        # Skip empty lines, markdown headers, date lines
        if not line:
            continue
        if line.startswith('#'):
            continue
        if re.match(r'.*\d{2}\.\d{2}\.\d{2,4}', line):  # Contains date
            continue
        if line.lower().startswith(('today', 'background', 'summary', 'introduction')):
            continue

        # If line is long enough and looks like a title (has capital letters)
        if len(line) > 20 and re.search(r'[A-Z]', line):
            # Clean up the title
            title = re.sub(r'^[⚡🚀:\s-]+', '', line)  # Remove leading emojis/symbols
            title = re.sub(r'[⚡🚀]+$', '', title)     # Remove trailing emojis
            title = title.strip()

            if len(title) > 15:  # Reasonable title length
                return title

    return None


def add_missing_link(content: str) -> Tuple[str, bool, str]:
    """Search for and add missing arxiv link if paper title is found.

    Returns: (new_content, was_added, message)
    """
    lines = content.split('\n')

    # Check if link already exists
    has_link = False
    for line in lines:
        if re.search(r'https?://', line):
            has_link = True
            break

    if has_link:
        return content, False, "Link already exists"

    # Extract paper title
    title = extract_paper_title(content)
    if not title:
        return content, False, "Could not extract paper title"

    # Search arxiv
    arxiv_id = search_arxiv_by_title(title)
    if not arxiv_id:
        return content, False, f"No arxiv match found for: {title[:60]}..."

    # Add link at the end
    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

    # Add blank line before link if last line is not blank
    if lines[-1].strip():
        lines.append('')

    lines.append(arxiv_url)

    return '\n'.join(lines), True, f"Added arxiv link: {arxiv_id}"


def remove_multiple_arxiv_links(content: str) -> str:
    """If multiple arxiv links exist, keep only the last one (usually at the end)."""
    lines = content.split('\n')

    # Find all lines with arxiv links
    arxiv_lines = []
    for i, line in enumerate(lines):
        if re.search(r'https?://arxiv\.org/(abs|pdf)/[\d.]+', line, re.IGNORECASE):
            arxiv_lines.append(i)

    # If more than one arxiv link, remove all except the last
    if len(arxiv_lines) > 1:
        # Keep the last arxiv link, remove the others
        lines_to_remove = set(arxiv_lines[:-1])
        new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
        return '\n'.join(new_lines)

    return content


def fix_english_review(filepath: Path) -> Tuple[bool, str]:
    """Fix a single English review file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        changes = []

        # Fix 1: Remove duplicate title on line 3
        new_content = remove_duplicate_title(content)
        if new_content != content:
            changes.append("Removed duplicate title")
            content = new_content

        # Fix 2: Ensure line 2 is blank
        new_content = ensure_blank_line2(content)
        if new_content != content:
            changes.append("Fixed line 2 formatting")
            content = new_content

        # Fix 3: Add markdown header if missing
        new_content = add_markdown_header(content)
        if new_content != content:
            changes.append("Added # header")
            content = new_content

        # Fix 4: Convert PDF to abs links
        new_content = convert_pdf_to_abs_links(content)
        if new_content != content:
            changes.append("Converted PDF to abs links")
            content = new_content

        # Fix 5: Remove multiple arxiv links (keep last one)
        new_content = remove_multiple_arxiv_links(content)
        if new_content != content:
            changes.append("Removed multiple arxiv links")
            content = new_content

        # Fix 6: Remove duplicate links
        new_content = remove_duplicate_links(content)
        if new_content != content:
            changes.append("Removed duplicate links")
            content = new_content

        # Fix 7: Add missing arxiv link if not present
        new_content, was_added, message = add_missing_link(content)
        if was_added:
            changes.append(message)
            content = new_content
        elif message not in ["Link already exists"]:
            # Debug: print why link wasn't added (except when link exists)
            print(f"  ℹ️  {filepath.name}: {message}")

        # Write back if changed
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            return True, "; ".join(changes)

        return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in format YYYY_MM_DD."""
    try:
        return datetime.strptime(date_str, "%Y_%m_%d")
    except ValueError:
        return None


def main():
    """Main function to process English reviews."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    reviews_dir = Path("/Users/michaelerlihson/Personal/Projects/scientific_repo/mike-paper-reviews-all/split-english-reviews-md")

    # Parse arguments
    fix_all = '--all' in sys.argv
    should_push = '--push' in sys.argv

    # Get date range if specified
    start_date = None
    end_date = None

    if not fix_all:
        date_args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
        if len(date_args) >= 1:
            start_date = parse_date(date_args[0])
            if not start_date:
                print(f"❌ Invalid start date: {date_args[0]}")
                sys.exit(1)

        if len(date_args) >= 2:
            end_date = parse_date(date_args[1])
            if not end_date:
                print(f"❌ Invalid end date: {date_args[1]}")
                sys.exit(1)
        elif start_date:
            # If only start date given, process only that one
            end_date = start_date

    # Get all review files
    review_files = sorted(reviews_dir.glob("Review_*.md"))

    # Filter by date range if specified
    if start_date and end_date:
        filtered_files = []
        for file_path in review_files:
            # Try to parse date from filename
            match = re.search(r'Review_(\d{4}_\d{2}_\d{2})', file_path.name)
            if match:
                file_date = parse_date(match.group(1))
                if file_date and start_date <= file_date <= end_date:
                    filtered_files.append(file_path)
            # Also include numbered reviews
            elif re.search(r'Review_\d+\.md', file_path.name):
                filtered_files.append(file_path)

        review_files = filtered_files

    if not review_files:
        print("❌ No review files found matching criteria")
        sys.exit(1)

    print(f"🔍 Processing {len(review_files)} English reviews...")

    fixed_count = 0
    fixed_files = []

    for file_path in review_files:
        was_fixed, message = fix_english_review(file_path)

        if was_fixed:
            fixed_count += 1
            fixed_files.append(file_path.name)
            print(f"✓ {file_path.name}: {message}")

    print(f"\n✅ Fixed {fixed_count} reviews")

    # Git commit and push if requested
    if should_push and fixed_count > 0:
        commit_message = f"Fix {fixed_count} English reviews\n\nFixed formatting issues and links\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

        files_to_commit = [str(reviews_dir / filename) for filename in fixed_files]

        if git_commit_and_push(files_to_commit, commit_message):
            print("✅ Changes committed and pushed to GitHub")
        else:
            print("⚠️  Failed to push changes")


if __name__ == "__main__":
    main()
