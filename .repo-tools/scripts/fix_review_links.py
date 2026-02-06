#!/usr/bin/env python3
"""
Skill: Fix Review Links
Automatically fixes common issues in review markdown files:

LINK FIXES:
- Corrects wrong review numbers
- Removes duplicate links (arxiv/HuggingFace/OpenReview)
- Converts PDF links to abs links (arxiv.org/pdf/ → arxiv.org/abs/)
- Verifies paper link matches review title
- Auto-corrects wrong paper links by searching arXiv

HEADER FIXES:
- Adds missing "Review X:" headers
- Replaces Hebrew titles with English paper titles
- Extracts English titles from mixed Hebrew/English line 1
- Completes truncated titles by finding full version
- Adds proper spacing after "Review X:" colon
- Moves misplaced titles from line 5 to line 1

DUPLICATE REMOVAL:
- Removes standalone duplicate title lines
- Removes duplicate titles stuck to daily markers
- Handles partial title matches and variations

FORMATTING:
- Separates embedded links from titles
- Separates daily markers from paper titles
- Fixes attached text on daily marker lines
- Removes dates from titles
- Normalizes spacing after Paper: line

Usage:
  python3 fix_review_links.py <start> [count]           # Fix reviews with multiple links
  python3 fix_review_links.py --fix-all <start> <end>   # Fix all formatting issues
  python3 fix_review_links.py ... --push                # Auto-commit and push to GitHub
"""

import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional
from difflib import SequenceMatcher

# Import git push helper
try:
    from git_push_helper import git_commit_and_push
except ImportError:
    # Fallback if not found
    def git_commit_and_push(*args, **kwargs):
        print("⚠️  git_push_helper not found, skipping push")
        return False


def extract_review_number(filename: str) -> int:
    """Extract review number from filename."""
    match = re.search(r'Review_(\d+)\.md', filename)
    return int(match.group(1)) if match else 0


def count_paper_links(content: str) -> int:
    """Count number of paper links in content."""
    patterns = [
        r'arxiv\.org/abs/',
        r'huggingface\.co/papers/',
        r'openreview\.net',
        r'openai\.com/research/',
        r'cdn\.openai\.com/papers/'
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content, re.IGNORECASE))
    return count


def fix_review_header(content: str, correct_number: int) -> str:
    """Fix the review number and title formatting."""
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Pattern 1: Review number with embedded link in title
    pattern1 = r'^Review (\d+):(.*?),?\s*\d{2}\.\d{2}\.\d{2}https?://[^\s]+$'
    match1 = re.match(pattern1, first_line)
    if match1:
        title_part = match1.group(2).strip()
        lines[0] = f'Review {correct_number}:{title_part}'
        return '\n'.join(lines)

    # Pattern 2: Review number with date but no embedded link
    pattern2 = r'^Review (\d+):(.*?),\s*\d{2}\.\d{2}\.\d{4}$'
    match2 = re.match(pattern2, first_line)
    if match2:
        title_part = match2.group(2).strip()
        lines[0] = f'Review {correct_number}:{title_part}'
        return '\n'.join(lines)

    # Pattern 3: Review number with embedded link without date
    pattern3 = r'^Review (\d+):(.*?)https?://[^\s]+$'
    match3 = re.match(pattern3, first_line)
    if match3:
        title_part = match3.group(2).strip().rstrip(',')
        lines[0] = f'Review {correct_number}:{title_part}'
        return '\n'.join(lines)

    # Pattern 4: Just wrong review number
    pattern4 = r'^Review (\d+):(.*)$'
    match4 = re.match(pattern4, first_line)
    if match4:
        current_num = int(match4.group(1))
        if current_num != correct_number:
            title_part = match4.group(2).strip()
            lines[0] = f'Review {correct_number}:{title_part}'

    return '\n'.join(lines)


def convert_pdf_to_abs_links(content: str) -> str:
    """Convert arxiv.org/pdf/ links to arxiv.org/abs/ links."""
    lines = content.split('\n')
    modified = False

    for i, line in enumerate(lines):
        # Match PDF links and convert to abs links
        # Handles both: arxiv.org/pdf/2301.12345.pdf and arxiv.org/pdf/2301.12345
        new_line = re.sub(
            r'https://arxiv\.org/pdf/(\d+\.\d+)(v\d+)?(\.pdf)?',
            r'https://arxiv.org/abs/\1\2',
            line
        )
        if new_line != line:
            lines[i] = new_line
            modified = True

    return '\n'.join(lines) if modified else content


def add_space_after_review_colon(content: str) -> str:
    """Ensure there's a space after 'Review X:' before the title."""
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Pattern: "Review 123:Title" -> "Review 123: Title"
    # Only add space if there isn't one already
    pattern = r'^(Review \d+):([^\s])'
    match = re.match(pattern, first_line)

    if match:
        lines[0] = f'{match.group(1)}: {match.group(2)}'
        lines[0] = lines[0][:match.end(1) + 2] + first_line[match.end(1) + 1:]
        # Simpler approach:
        lines[0] = re.sub(r'^(Review \d+):([^\s])', r'\1: \2', first_line)
        return '\n'.join(lines)

    return content


def fix_emoji_only_title(content: str, correct_number: int) -> str:
    """Replace emoji-only titles with actual English title from content."""
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Check if line 1 has "Review X:" pattern
    match = re.match(r'^Review (\d+):\s*(.+)$', first_line)
    if not match:
        return content

    current_title = match.group(2).strip()

    # Check if title contains only emojis/symbols (no letters)
    if re.search(r'[a-zA-Z]', current_title):
        # Title has letters, it's probably fine
        return content

    # Title is emoji-only, find the real English title
    for i in range(1, min(15, len(lines))):
        line = lines[i].strip()
        # Skip empty lines
        if not line:
            continue
        # Skip Hebrew-only lines
        if re.match(r'^[\u0590-\u05FF\s:,.0-9-⚡🚀🔥💡✨🎯]+$', line):
            continue
        # Found a line with English letters
        if re.search(r'[a-zA-Z]', line):
            # This should be the title
            english_title = line.strip()
            lines[0] = f"Review {correct_number}: {english_title}"
            return '\n'.join(lines)

    return content


def fix_missing_review_header(content: str, correct_number: int) -> str:
    """Add missing 'Review X:' header if first line doesn't have it."""
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Check if first line already has "Review X:" pattern
    if re.match(r'^Review \d+:', first_line):
        return content

    # Find title on first few lines
    # Look for English titles (starting with capital letter or all caps)
    title = None
    title_line_idx = None

    for i in range(min(6, len(lines))):
        line = lines[i].strip()
        # Skip empty lines and Hebrew-only lines (daily markers)
        if not line or re.match(r'^[\u0590-\u05FF\s:,.0-9-]+$', line):
            continue
        # Found a line with English text - assume it's the title
        title = line
        title_line_idx = i
        break

    if title and title_line_idx is not None:
        # Remove the title from its current position
        new_lines = [f"Review {correct_number}: {title}", ""]
        # Add all other lines except the one with the title
        for i, line in enumerate(lines):
            if i != title_line_idx:
                new_lines.append(line)

        return '\n'.join(new_lines)

    # No title found - just add empty header
    return f"Review {correct_number}:\n\n" + content


def move_title_from_line5_to_line1(content: str, correct_number: int) -> str:
    """Move title from line 5 (or nearby) to line 1 if it's missing there."""
    lines = content.split('\n')
    if len(lines) < 3:
        return content

    first_line = lines[0]

    # Check if line 1 has "Review X:" but no title after colon
    match = re.match(r'^Review \d+:\s*$', first_line)
    if not match:
        return content

    # Find title in next few lines (usually line 5, index 4)
    title = None
    title_line_idx = None

    for i in range(1, min(10, len(lines))):
        line = lines[i].strip()
        # Skip empty lines and Hebrew-only lines
        if not line or re.match(r'^[\u0590-\u05FF\s:,.0-9-]+$', line):
            continue
        # Found a line with English text - assume it's the title
        title = line
        title_line_idx = i
        break

    if title and title_line_idx is not None:
        # Put title on line 1, remove from its current position
        new_lines = [f"Review {correct_number}: {title}"]
        for i, line in enumerate(lines[1:], start=1):
            if i != title_line_idx:
                new_lines.append(line)

        return '\n'.join(new_lines)

    return content


def fix_hebrew_title_in_header(content: str, correct_number: int) -> str:
    """Replace Hebrew title in header with proper English title from content."""
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Check if line 1 has "Review X:" pattern
    match = re.match(r'^Review (\d+):\s*(.+)$', first_line)
    if not match:
        return content

    current_title = match.group(2).strip()

    # Check if current title contains Hebrew characters
    if not re.search(r'[\u0590-\u05FF]', current_title):
        # Title is already in English, nothing to do
        return content

    # First try to extract English title from the current_title itself
    # This handles cases where line 1 has: "Review X: Hebrew text + date + English title"
    english_title = None
    date_match = re.search(r'\d{2}\.\d{2}\.\d{2}(.+)$', current_title)
    if date_match:
        after_date = date_match.group(1)
        # Extract everything after date that starts with capital letter
        english_match = re.search(r'([A-Z].+)$', after_date)
        if english_match:
            # Remove any trailing Hebrew text
            potential_title = re.sub(r'[\u0590-\u05FF].*$', '', english_match.group(1)).strip()
            if potential_title:
                english_title = potential_title
                lines[0] = f"Review {correct_number}: {english_title}"
                return '\n'.join(lines)

    # If not found on line 1, look for English title in the content
    # Look for lines with ONLY English text (no Hebrew at all)
    for i in range(1, min(15, len(lines))):
        line = lines[i].strip()
        # Skip empty lines
        if not line:
            continue
        # If line has Hebrew, try to extract English title from it
        if re.search(r'[\u0590-\u05FF]', line):
            # Look for English text after Hebrew daily marker and date
            # Pattern: Hebrew text + date + possible more Hebrew + English title
            match = re.search(r'[\u0590-\u05FF].*?\d{2}\.\d{2}\.\d{2}(.+)$', line)
            if match:
                after_date = match.group(1)
                # Extract everything after date that starts with capital letter
                english_match = re.search(r'([A-Z].+)$', after_date)
                if english_match:
                    # Remove any trailing Hebrew text
                    potential_title = re.sub(r'[\u0590-\u05FF].*$', '', english_match.group(1)).strip()
                    if potential_title:
                        english_title = potential_title
                        break
            continue
        # Must contain at least some English letters
        if not re.search(r'[a-zA-Z]', line):
            continue
        # Found a line with only English text - this is the title
        english_title = line
        break

    if english_title:
        lines[0] = f"Review {correct_number}: {english_title}"
        return '\n'.join(lines)

    return content


def remove_duplicate_title_from_daily_marker(content: str) -> str:
    """Remove duplicate English title from daily marker line if it matches header title."""
    lines = content.split('\n')
    if len(lines) < 4:
        return content

    # Extract title and review number from line 1
    first_line = lines[0]
    match = re.match(r'^Review (\d+):\s*(.+)$', first_line)
    if not match:
        return content

    review_num = int(match.group(1))
    header_title = match.group(2).strip()

    # Check lines 2-6 for daily marker with duplicate title
    for i in range(1, min(7, len(lines))):
        line = lines[i]
        # Skip empty lines
        if not line.strip():
            continue
        # Look for Hebrew daily marker
        if re.search(r'[\u0590-\u05FF]', line):
            # Extract title after the date if present
            date_match = re.search(r'\d{2}\.\d{2}\.\d{2}(.+)$', line)
            if date_match:
                after_date = date_match.group(1).strip()
                # Extract English title (skip Hebrew text like "סקירה 544,")
                english_match = re.search(r'([A-Z].+)$', after_date)
                if english_match:
                    full_title = re.sub(r'[\u0590-\u05FF].*$', '', english_match.group(1)).strip()
                    # Check if this matches or extends the header title
                    if full_title.startswith(header_title) or header_title in full_title:
                        # Update line 1 with the full title if header was truncated
                        if full_title != header_title and len(full_title) > len(header_title):
                            lines[0] = f"Review {review_num}: {full_title}"
                        # Remove the duplicate title from daily marker line
                        cleaned = re.sub(r'(\d{2}\.\d{2}\.\d{2}).*?(' + re.escape(full_title) + r')\s*', r'\1', line)
                        if cleaned != line:
                            lines[i] = cleaned.rstrip()
                            return '\n'.join(lines)

    return content


def move_link_from_end_to_top(content: str) -> str:
    """Move standalone paper link from end of review to proper Paper: line at top.

    Detects reviews where:
    - No "Paper:" line exists in first 10 lines
    - A standalone link (arxiv, openai, nature, etc.) exists at the end (after line 20)
    - Moves the link to line 3 in "Paper: URL" format
    - Removes the link from the end
    """
    lines = content.split('\n')

    # Check if Paper: line already exists in first 10 lines
    has_paper_line = False
    for i in range(min(10, len(lines))):
        if lines[i].strip().startswith('Paper:'):
            has_paper_line = True
            break

    if has_paper_line:
        return content

    # Look for standalone link at the end (after line 20, on its own line)
    link_patterns = [
        r'^https?://arxiv\.org/abs/[\d.]+(?:v\d+)?$',
        r'^https?://(?:www\.)?nature\.com/articles/[\w-]+$',
        r'^https?://openai\.com/[\w/-]+$',
        r'^https?://(?:cdn\.)?openai\.com/papers/[\w.-]+$',
        r'^https?://aclanthology\.org/[\w.-/]+$',
        r'^https?://proceedings\.mlr\.press/[\w/]+\.html$',
        r'^https?://openreview\.net/[\w?=&]+$',
        r'^https?://huggingface\.co/papers/[\d.]+$'
    ]

    found_link = None
    link_line_idx = None

    # Search from end backwards for standalone link
    for i in range(len(lines) - 1, 19, -1):  # Start from end, stop at line 20
        line = lines[i].strip()
        for pattern in link_patterns:
            if re.match(pattern, line):
                found_link = line
                link_line_idx = i
                break
        if found_link:
            break

    if not found_link or link_line_idx is None:
        return content

    # Insert Paper: line after title (line 0), with blank line
    # Structure should be:
    # Line 0: Review XXX: Title
    # Line 1: (blank)
    # Line 2: Paper: URL
    # Line 3: (blank)
    # Line 4: Daily marker or content...

    new_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            # Add title line
            new_lines.append(line)
            new_lines.append('')
            new_lines.append(f'Paper: {found_link}')
        elif i == link_line_idx:
            # Skip the link line at the end
            continue
        elif i == link_line_idx - 1 and not lines[i].strip():
            # Skip empty line before the link if it exists
            continue
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def remove_standalone_duplicate_title(content: str) -> str:
    """Remove standalone lines that duplicate the header title."""
    lines = content.split('\n')
    if len(lines) < 4:
        return content

    # Extract title from line 1
    first_line = lines[0]
    match = re.match(r'^Review \d+:\s*(.+)$', first_line)
    if not match:
        return content

    header_title = match.group(1).strip()

    # Check lines 2-15 for standalone duplicate titles
    modified = False
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip line 1 (the header itself)
        if i == 0:
            new_lines.append(line)
            continue
        # If line exactly matches the header title, skip it
        if stripped == header_title:
            modified = True
            continue
        # Add the line to output
        new_lines.append(line)

    if modified:
        return '\n'.join(new_lines)

    return content


def remove_duplicate_links(content: str, correct_arxiv_id: Optional[str] = None) -> str:
    """Remove duplicate paper links, keeping only the Paper: line."""
    lines = content.split('\n')

    paper_link = None
    paper_line_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Paper:'):
            paper_link = line
            paper_line_idx = i
            break

    if not paper_link:
        return content

    # If we have a correct arXiv ID and the current Paper: link is wrong, fix it
    if correct_arxiv_id:
        current_id_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', paper_link)
        if current_id_match and current_id_match.group(1) != correct_arxiv_id:
            lines[paper_line_idx] = f'Paper: https://arxiv.org/abs/{correct_arxiv_id}'
            paper_link = lines[paper_line_idx]

    paper_id_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', paper_link)
    if not paper_id_match:
        return content

    paper_id = paper_id_match.group(1)

    # Remove ALL standalone paper links (both before and after the Paper: line)
    # This includes duplicates AND wrong links with different IDs
    cleaned_lines = []
    for i, line in enumerate(lines):
        if i != paper_line_idx:
            stripped = line.strip()
            # Remove any standalone paper links (arxiv, HuggingFace, OpenReview, OpenAI, Hebrew)
            # Also handle lines with multiple URLs separated by commas
            if (stripped.startswith('https://arxiv.org/abs/') or
                stripped.startswith('https://huggingface.co/papers/') or
                stripped.startswith('https://openreview.net/') or
                stripped.startswith('https://openai.com/') or
                stripped.startswith('https://cdn.openai.com/') or
                stripped.startswith('http://openai.com/') or
                stripped.startswith('http://cdn.openai.com/') or
                stripped.startswith('למאמר:')):
                continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def extract_title_from_review(content: str) -> Optional[str]:
    """Extract the title from the review header."""
    lines = content.split('\n')
    if not lines:
        return None

    first_line = lines[0]
    match = re.match(r'^Review \d+:\s*(?:\[Short\]\s*)?(.*?)$', first_line, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        title = re.sub(r',?\s*\d{2}\.\d{2}\.\d{2}.*$', '', title)
        return title
    return None


def extract_paper_link(content: str) -> Optional[str]:
    """Extract the Paper: link from the review."""
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('Paper:'):
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                return url_match.group(0)
    return None


def extract_all_arxiv_ids(content: str) -> List[str]:
    """Extract all arXiv IDs from the content."""
    arxiv_ids = []
    # Match arxiv IDs: YYYY.NNNNN optionally followed by vN
    # Don't capture trailing dots (from .pdf extensions)
    arxiv_matches = re.findall(r'arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?', content, re.IGNORECASE)
    arxiv_ids.extend(arxiv_matches)
    hf_matches = re.findall(r'huggingface\.co/papers/(\d{4}\.\d{4,5})(?:v\d+)?', content, re.IGNORECASE)
    arxiv_ids.extend(hf_matches)

    seen = set()
    unique_ids = []
    for arxiv_id in arxiv_ids:
        if arxiv_id not in seen:
            seen.add(arxiv_id)
            unique_ids.append(arxiv_id)
    return unique_ids


def fetch_arxiv_title(arxiv_id: str) -> Optional[str]:
    """Fetch paper title from arXiv API."""
    try:
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
        url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'

        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')
            entry_match = re.search(r'<entry>(.*?)</entry>', content, re.DOTALL)
            if entry_match:
                entry_content = entry_match.group(1)
                title_match = re.search(r'<title>(.*?)</title>', entry_content, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                    title = re.sub(r'\s+', ' ', title)
                    return title
    except Exception as e:
        print(f"  ⚠️  Error fetching arXiv title: {e}")
    return None


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings."""
    s1 = re.sub(r'\s+', ' ', str1.lower().strip())
    s2 = re.sub(r'\s+', ' ', str2.lower().strip())
    return SequenceMatcher(None, s1, s2).ratio()


def find_correct_arxiv_id(content: str, review_title: str) -> Optional[str]:
    """Find which arXiv ID in the content best matches the review title."""
    arxiv_ids = extract_all_arxiv_ids(content)

    if not arxiv_ids:
        return None
    if len(arxiv_ids) == 1:
        return arxiv_ids[0]

    best_id = None
    best_similarity = 0.0

    for arxiv_id in arxiv_ids:
        paper_title = fetch_arxiv_title(arxiv_id)
        if paper_title:
            similarity = similarity_ratio(review_title, paper_title)
            if similarity > best_similarity:
                best_similarity = similarity
                best_id = arxiv_id

    if best_similarity >= 0.7:
        return best_id
    return None


def search_arxiv_by_title(title: str) -> Optional[str]:
    """Search arXiv for a paper by title."""
    try:
        search_query = urllib.parse.quote(title)
        url = f'http://export.arxiv.org/api/query?search_query=ti:{search_query}&max_results=5'

        with urllib.request.urlopen(url, timeout=10) as response:
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

            if best_similarity >= 0.9:
                return best_match

    except Exception as e:
        print(f"  ⚠️  Error searching arXiv: {e}")
    return None


def normalize_paper_link_spacing(content: str) -> str:
    """Ensure exactly one blank line after the Paper: line."""
    lines = content.split('\n')

    # Find the Paper: line
    paper_line_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Paper:'):
            paper_line_idx = i
            break

    if paper_line_idx is None:
        return content

    # Remove any blank lines immediately after Paper: line
    new_lines = []
    i = 0
    while i < len(lines):
        new_lines.append(lines[i])

        # If this is the Paper: line, ensure exactly one blank line follows
        if i == paper_line_idx:
            # Skip any existing blank lines
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            # Add exactly one blank line
            new_lines.append('')
            continue

        i += 1

    return '\n'.join(new_lines)


def separate_daily_marker_from_title(content: str, correct_number: int) -> str:
    """Separate daily marker (המאמר היומי של מייק) from paper title.

    Handles patterns like:
    - ⚡️🚀המאמר היומי של מייק 14.09.24: ⚡️🚀Beyond Neural Scaling Laws...
    - המאמר היומי של מייק - 13.02.25One Initialization to Rule them All...
    """
    lines = content.split('\n')
    if not lines:
        return content

    first_line = lines[0]

    # Pattern 1: Emojis + "המאמר היומי של מייק" + date + emojis + Paper Title (all on one line)
    # Example: ⚡️🚀המאמר היומי של מייק 14.09.24: ⚡️🚀Beyond Neural Scaling Laws...
    pattern1 = r'^[⚡️🚀\s]*המאמר היומי של מייק[^:]*:\s*[⚡️🚀\s]*(.+)$'
    match1 = re.match(pattern1, first_line)

    if match1:
        # Extract paper title
        paper_title = match1.group(1).strip()

        # Extract the daily marker part (everything before the paper title)
        daily_marker = first_line[:first_line.rfind(paper_title)].rstrip()
        # Remove trailing colon and whitespace
        daily_marker = re.sub(r':\s*$', '', daily_marker).strip()

        # Build new content
        new_lines = [
            f"Review {correct_number}:{paper_title}",
            "",
            daily_marker,
            ""
        ] + lines[1:]

        return '\n'.join(new_lines)

    # Pattern 2: "המאמר היומי של מייק" + date + Paper Title (no space between date and title)
    # Example: המאמר היומי של מייק - 13.02.25One Initialization to Rule them All...
    pattern2 = r'^המאמר היומי של מייק[^a-zA-Z]*([A-Z].+)$'
    match2 = re.match(pattern2, first_line)

    if match2:
        # Extract paper title (starts with capital letter)
        paper_title = match2.group(1).strip()

        # Extract the daily marker part
        daily_marker = first_line[:first_line.find(paper_title)].strip()

        # Build new content
        new_lines = [
            f"Review {correct_number}:{paper_title}",
            "",
            daily_marker,
            ""
        ] + lines[1:]

        return '\n'.join(new_lines)

    return content


def fix_attached_text_on_daily_marker(content: str) -> str:
    """Fix reviews where title text is still attached to daily marker line.

    Handles cases where the daily marker separation happened but text remained attached.
    Example line 3: המאמר היומי של מייק - 13.02.25One Initialization to Rule them All
    Should become:
    - Line 1: Review XXX:One Initialization to Rule them All: [original title]
    - Line 3: המאמר היומי של מייק - 13.02.25
    """
    lines = content.split('\n')

    if len(lines) < 3:
        return content

    # Check if line 3 (index 2) has the pattern: "המאמר היומי של מייק" + date + English text
    pattern = r'^(המאמר היומי של מייק[^A-Z]*)([A-Z].+)$'
    match = re.match(pattern, lines[2])

    if match:
        daily_marker = match.group(1).strip()
        attached_title = match.group(2).strip()

        # Get current title from line 1
        current_title_match = re.match(r'^Review (\d+):(.+)$', lines[0])
        if not current_title_match:
            return content

        review_num = current_title_match.group(1)
        current_title = current_title_match.group(2).strip()

        # Combine titles: attached_title + current_title
        full_title = f"{attached_title}: {current_title}"

        # Update the lines
        lines[0] = f"Review {review_num}:{full_title}"
        lines[2] = daily_marker

        return '\n'.join(lines)

    return content


def verify_paper_link(content: str, filepath: Path) -> Tuple[bool, str, Optional[str]]:
    """Verify that the paper link matches the review title."""
    review_title = extract_title_from_review(content)
    paper_link = extract_paper_link(content)

    if not review_title or not paper_link:
        return True, "No title or link to verify", None

    arxiv_match = re.search(r'arxiv\.org/abs/([\d.]+(?:v\d+)?)', paper_link)
    if not arxiv_match:
        return True, "Not an arXiv link, skipping verification", None

    arxiv_id = arxiv_match.group(1)
    paper_title = fetch_arxiv_title(arxiv_id)

    if not paper_title:
        return True, "Could not fetch paper title", None

    similarity = similarity_ratio(review_title, paper_title)

    if similarity < 0.6:
        print(f"  🔍 Searching for correct paper: {review_title}")
        correct_arxiv_id = search_arxiv_by_title(review_title)

        if correct_arxiv_id:
            found_title = fetch_arxiv_title(correct_arxiv_id)
            if found_title:
                found_similarity = similarity_ratio(review_title, found_title)
                if found_similarity >= 0.9:
                    old_link = paper_link
                    new_link = f"https://arxiv.org/abs/{correct_arxiv_id}"
                    corrected_content = content.replace(old_link, new_link)

                    msg = f"Link auto-corrected (was {similarity:.1%}, now {found_similarity:.1%})\n"
                    msg += f"  Old: {old_link}\n"
                    msg += f"  New: {new_link}\n"
                    msg += f"  Paper: {found_title}"
                    return True, msg, corrected_content

        return False, f"Title mismatch (similarity: {similarity:.1%})\n  Review: {review_title}\n  Paper:  {paper_title}", None

    return True, f"Link verified (similarity: {similarity:.1%})", None


def fix_review_file(filepath: Path) -> Tuple[bool, str]:
    """Fix a single review file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        correct_number = extract_review_number(filepath.name)
        if correct_number == 0:
            return False, "Could not extract review number"

        link_count = count_paper_links(content)
        if link_count <= 1:
            return False, "Only one link"

        changes = []

        # Fix missing "Review X:" header
        new_content = fix_missing_review_header(content, correct_number)
        if new_content != content:
            changes.append("Added missing header")
            content = new_content

        # Fix emoji-only titles
        new_content = fix_emoji_only_title(content, correct_number)
        if new_content != content:
            changes.append("Replaced emoji-only title with real title")
            content = new_content

        # Fix Hebrew title in header (replace with English title)
        new_content = fix_hebrew_title_in_header(content, correct_number)
        if new_content != content:
            changes.append("Replaced Hebrew title with English")
            content = new_content

        # Remove duplicate title from daily marker line
        new_content = remove_duplicate_title_from_daily_marker(content)
        if new_content != content:
            changes.append("Removed duplicate title from daily marker")
            content = new_content

        # Remove standalone duplicate title lines
        new_content = remove_standalone_duplicate_title(content)
        if new_content != content:
            changes.append("Removed standalone duplicate title")
            content = new_content

        # Move title from line 5 to line 1 if needed
        new_content = move_title_from_line5_to_line1(content, correct_number)
        if new_content != content:
            changes.append("Moved title to line 1")
            content = new_content

        # Separate daily marker from title (if present)
        new_content = separate_daily_marker_from_title(content, correct_number)
        if new_content != content:
            changes.append("Separated daily marker")
            content = new_content

        # Fix attached text on daily marker line
        new_content = fix_attached_text_on_daily_marker(content)
        if new_content != content:
            changes.append("Fixed attached text")
            content = new_content

        new_content = fix_review_header(content, correct_number)
        if new_content != content:
            changes.append("Fixed header")
            content = new_content

        # Add space after colon in "Review X:Title"
        new_content = add_space_after_review_colon(content)
        if new_content != content:
            changes.append("Added space after colon")
            content = new_content

        # Convert PDF links to abs links
        new_content = convert_pdf_to_abs_links(content)
        if new_content != content:
            changes.append("Converted PDF to abs links")
            content = new_content

        review_title = extract_title_from_review(content)
        correct_arxiv_id = None
        if review_title:
            correct_arxiv_id = find_correct_arxiv_id(content, review_title)

        new_content = remove_duplicate_links(content, correct_arxiv_id)
        if new_content != content:
            changes.append("Removed duplicates")
            content = new_content

        # Normalize spacing after Paper: line (ensure exactly one blank line)
        new_content = normalize_paper_link_spacing(content)
        if new_content != content:
            changes.append("Normalized spacing")
            content = new_content

        link_valid, verify_msg, corrected_content = verify_paper_link(content, filepath)

        if corrected_content:
            content = corrected_content
            changes.append("✅ Link auto-corrected")
            print(f"\n✅ {filepath.name}: {verify_msg}")
        elif not link_valid:
            print(f"\n⚠️  {filepath.name}: {verify_msg}")
            changes.append("⚠️ Link verification failed")

        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            result_msg = "; ".join(changes)
            if link_valid and "verified" in verify_msg.lower() and not corrected_content:
                result_msg += f" [{verify_msg}]"
            return True, result_msg

        return False, "No changes"

    except Exception as e:
        return False, f"Error: {str(e)}"


def fix_review_number_and_spacing(filepath: Path) -> Tuple[bool, str]:
    """Fix review number and spacing in a file (for reviews with just 1 link)."""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content
        changes = []

        correct_number = extract_review_number(filepath.name)
        if correct_number == 0:
            return False, "Could not extract review number"

        # Fix missing "Review X:" header
        new_content = fix_missing_review_header(content, correct_number)
        if new_content != content:
            changes.append("Added missing header")
            content = new_content

        # Fix emoji-only titles
        new_content = fix_emoji_only_title(content, correct_number)
        if new_content != content:
            changes.append("Replaced emoji-only title with real title")
            content = new_content

        # Fix Hebrew title in header (replace with English title)
        new_content = fix_hebrew_title_in_header(content, correct_number)
        if new_content != content:
            changes.append("Replaced Hebrew title with English")
            content = new_content

        # Remove duplicate title from daily marker line
        new_content = remove_duplicate_title_from_daily_marker(content)
        if new_content != content:
            changes.append("Removed duplicate title from daily marker")
            content = new_content

        # Remove standalone duplicate title lines
        new_content = remove_standalone_duplicate_title(content)
        if new_content != content:
            changes.append("Removed standalone duplicate title")
            content = new_content

        # Move title from line 5 to line 1 if needed
        new_content = move_title_from_line5_to_line1(content, correct_number)
        if new_content != content:
            changes.append("Moved title to line 1")
            content = new_content

        # Separate daily marker from title (if present)
        new_content = separate_daily_marker_from_title(content, correct_number)
        if new_content != content:
            changes.append("Separated daily marker")
            content = new_content

        # Fix attached text on daily marker line
        new_content = fix_attached_text_on_daily_marker(content)
        if new_content != content:
            changes.append("Fixed attached text")
            content = new_content

        # Fix review number
        new_content = fix_review_header(content, correct_number)
        if new_content != content:
            changes.append("Fixed review number")
            content = new_content

        # Add space after colon in "Review X:Title"
        new_content = add_space_after_review_colon(content)
        if new_content != content:
            changes.append("Added space after colon")
            content = new_content

        # Convert PDF links to abs links
        new_content = convert_pdf_to_abs_links(content)
        if new_content != content:
            changes.append("Converted PDF to abs links")
            content = new_content

        # Normalize spacing after Paper: line
        new_content = normalize_paper_link_spacing(content)
        if new_content != content:
            changes.append("Normalized spacing")
            content = new_content

        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            return True, "; ".join(changes)

        return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {str(e)}"


def find_problematic_reviews(start_num: int, count: int, reviews_dir: Path) -> List[Path]:
    """Find reviews with multiple links."""
    problematic = []
    for i in range(start_num, start_num + 200):
        filepath = reviews_dir / f"Review_{i:03d}.md"
        if not filepath.exists():
            continue
        try:
            content = filepath.read_text(encoding='utf-8')
            if count_paper_links(content) > 1:
                problematic.append(filepath)
                if len(problematic) >= count:
                    break
        except Exception:
            continue
    return problematic


def find_numbering_mismatches(start_num: int, end_num: int, reviews_dir: Path) -> List[Path]:
    """Find reviews where filename number doesn't match content number."""
    mismatches = []
    for i in range(start_num, end_num + 1):
        filepath = reviews_dir / f"Review_{i:03d}.md"
        if not filepath.exists():
            continue
        try:
            content = filepath.read_text(encoding='utf-8')
            lines = content.split('\n')
            if not lines:
                continue

            # Extract review number from first line
            match = re.match(r'^Review (\d+):', lines[0])
            if match:
                content_number = int(match.group(1))
                if content_number != i:
                    mismatches.append(filepath)
        except Exception:
            continue
    return mismatches


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_review_links.py <start> [count] [--push]")
        print("       fix_review_links.py --fix-all <start> <end> [--push]")
        print("\nOptions:")
        print("  --push    Automatically commit and push changes to GitHub")
        sys.exit(1)

    # Check for --push flag
    auto_push = '--push' in sys.argv
    if auto_push:
        sys.argv.remove('--push')

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    reviews_dir = repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md"

    # Track modified files for pushing
    modified_files = []

    # Mode: Fix all formatting (numbers + spacing) for ALL reviews
    if sys.argv[1] == '--fix-all':
        if len(sys.argv) < 4:
            print("Usage: fix_review_links.py --fix-all <start> <end>")
            sys.exit(1)

        start_num = int(sys.argv[2])
        end_num = int(sys.argv[3])

        print(f"🔍 Checking reviews {start_num}-{end_num} for formatting issues...")

        fixed = 0
        checked = 0
        for i in range(start_num, end_num + 1):
            filepath = reviews_dir / f"Review_{i:03d}.md"
            if not filepath.exists():
                continue

            checked += 1
            was_modified, desc = fix_review_number_and_spacing(filepath)
            if was_modified:
                print(f"✓ {filepath.name}: {desc}")
                fixed += 1
                # Track modified file (relative to repo root)
                rel_path = str(filepath.relative_to(repo_root))
                modified_files.append(rel_path)

        print(f"\n✅ Checked {checked} reviews, fixed {fixed}")

        # Push if requested and files were modified
        if auto_push and modified_files:
            print(f"\n🚀 Pushing {len(modified_files)} modified files...")
            # Also include the skill itself
            skill_path = str(Path(__file__).relative_to(repo_root))
            if skill_path not in modified_files:
                modified_files.append(skill_path)

            commit_msg = f"Fix {fixed} reviews (Review_{start_num:03d}-{end_num:03d})\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
            success = git_commit_and_push(modified_files, commit_msg, repo_root)
            if success:
                print("✓ Pushed to GitHub successfully")
            else:
                print("✗ Push failed (see errors above)")

        return

    # Mode: Fix links (original functionality)
    start_num = int(sys.argv[1])
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"🔍 Finding {count} reviews from {start_num}...")
    problematic = find_problematic_reviews(start_num, count, reviews_dir)

    if not problematic:
        print("✓ None found")
        return

    print(f"Found: {[p.name for p in problematic]}")
    print("\n🔧 Fixing...")

    fixed = 0
    for filepath in problematic:
        was_modified, desc = fix_review_file(filepath)
        if was_modified:
            print(f"✓ {filepath.name}: {desc}")
            fixed += 1
            # Track modified file (relative to repo root)
            rel_path = str(filepath.relative_to(repo_root))
            modified_files.append(rel_path)

    print(f"\n✅ Fixed {fixed}/{len(problematic)}")

    # Push if requested and files were modified
    if auto_push and modified_files:
        print(f"\n🚀 Pushing {len(modified_files)} modified files...")
        # Also include the skill itself
        skill_path = str(Path(__file__).relative_to(repo_root))
        if skill_path not in modified_files:
            modified_files.append(skill_path)

        review_names = ", ".join([p.name for p in problematic[:3]])
        if len(problematic) > 3:
            review_names += f" and {len(problematic) - 3} more"

        commit_msg = f"Fix review links: {review_names}\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        success = git_commit_and_push(modified_files, commit_msg, repo_root)
        if success:
            print("✓ Pushed to GitHub successfully")
        else:
            print("✗ Push failed (see errors above)")


if __name__ == "__main__":
    main()
