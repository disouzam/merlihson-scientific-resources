#!/usr/bin/env python3
"""
Skill: Fix Review Links
Automatically fixes common issues in review markdown files:
- Corrects wrong review numbers
- Removes duplicate links (arxiv/HuggingFace/OpenReview)
- Removes dates from titles
- Separates embedded links from titles
- Verifies paper link matches review title
"""

import re
import sys
import urllib.request
from pathlib import Path
from typing import List, Tuple, Optional
from difflib import SequenceMatcher


def extract_review_number(filename: str) -> int:
    """Extract review number from filename."""
    match = re.search(r'Review_(\d+)\.md', filename)
    return int(match.group(1)) if match else 0


def count_paper_links(content: str) -> int:
    """Count number of paper links in content."""
    patterns = [
        r'arxiv\.org/abs/',
        r'huggingface\.co/papers/',
        r'openreview\.net'
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
    # Example: Review 124: [Short] Title, 14.08.23https://huggingface.co/papers/2308.06259
    pattern1 = r'^Review (\d+):(.*?),?\s*\d{2}\.\d{2}\.\d{2}https?://[^\s]+$'
    match1 = re.match(pattern1, first_line)
    if match1:
        title_part = match1.group(2).strip()
        lines[0] = f'Review {correct_number}:{title_part}'
        return '\n'.join(lines)

    # Pattern 2: Review number with embedded link without date
    # Example: Review 117: Title, 06.08.23https://kfirgoldberg.github.io/...
    pattern2 = r'^Review (\d+):(.*?)https?://[^\s]+$'
    match2 = re.match(pattern2, first_line)
    if match2:
        title_part = match2.group(2).strip().rstrip(',')
        lines[0] = f'Review {correct_number}:{title_part}'
        return '\n'.join(lines)

    # Pattern 3: Just wrong review number
    # Example: Review 124: [Short] Title
    pattern3 = r'^Review (\d+):(.*)$'
    match3 = re.match(pattern3, first_line)
    if match3:
        current_num = int(match3.group(1))
        if current_num != correct_number:
            title_part = match3.group(2).strip()
            lines[0] = f'Review {correct_number}:{title_part}'

    return '\n'.join(lines)


def remove_duplicate_links(content: str) -> str:
    """Remove duplicate paper links, keeping only the Paper: line."""
    lines = content.split('\n')

    # Find the main Paper: link
    paper_link = None
    paper_line_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Paper:'):
            paper_link = line
            paper_line_idx = i
            break

    if not paper_link:
        return content

    # Extract the paper ID from the main link
    paper_id_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', paper_link)
    if not paper_id_match:
        return content

    paper_id = paper_id_match.group(1)

    # Remove duplicate links after the Paper: line
    cleaned_lines = []
    for i, line in enumerate(lines):
        # Skip lines that are duplicate links
        if i > paper_line_idx and i < len(lines) - 1:
            stripped = line.strip()
            if (stripped.startswith('https://arxiv.org/abs/' + paper_id) or
                stripped.startswith('https://huggingface.co/papers/') or
                stripped.startswith('https://openreview.net/') or
                stripped.startswith('למאמר:')):
                if i + 1 < len(lines) and lines[i + 1].strip():
                    continue
                if i + 2 < len(lines) and not lines[i + 1].strip() and lines[i + 2].strip():
                    continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def extract_title_from_review(content: str) -> Optional[str]:
    """Extract the title from the review header."""
    lines = content.split('\n')
    if not lines:
        return None

    first_line = lines[0]
    # Pattern: Review 123: [Short] Title or Review 123: Title
    match = re.match(r'^Review \d+:\s*(?:\[Short\]\s*)?(.*?)$', first_line, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Clean up any trailing punctuation or dates
        title = re.sub(r',?\s*\d{2}\.\d{2}\.\d{2}.*$', '', title)
        return title
    return None


def extract_paper_link(content: str) -> Optional[str]:
    """Extract the Paper: link from the review."""
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('Paper:'):
            # Extract URL from the line
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                return url_match.group(0)
    return None


def fetch_arxiv_title(arxiv_id: str) -> Optional[str]:
    """Fetch paper title from arXiv API."""
    try:
        # Remove version number if present
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
        url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'

        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')
            # Parse XML to extract title from <entry> section (not the feed title)
            entry_match = re.search(r'<entry>(.*?)</entry>', content, re.DOTALL)
            if entry_match:
                entry_content = entry_match.group(1)
                title_match = re.search(r'<title>(.*?)</title>', entry_content, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                    # Clean up whitespace and newlines
                    title = re.sub(r'\s+', ' ', title)
                    return title
    except Exception as e:
        print(f"  ⚠️  Error fetching arXiv title: {e}")
    return None


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    # Normalize: lowercase, remove extra whitespace
    s1 = re.sub(r'\s+', ' ', str1.lower().strip())
    s2 = re.sub(r'\s+', ' ', str2.lower().strip())
    return SequenceMatcher(None, s1, s2).ratio()


def verify_paper_link(content: str, filepath: Path) -> Tuple[bool, str]:
    """Verify that the paper link matches the review title."""
    review_title = extract_title_from_review(content)
    paper_link = extract_paper_link(content)

    if not review_title or not paper_link:
        return True, "No title or link to verify"

    # Extract arXiv ID
    arxiv_match = re.search(r'arxiv\.org/abs/([\d.]+(?:v\d+)?)', paper_link)
    if not arxiv_match:
        return True, "Not an arXiv link, skipping verification"

    arxiv_id = arxiv_match.group(1)
    paper_title = fetch_arxiv_title(arxiv_id)

    if not paper_title:
        return True, "Could not fetch paper title"

    # Calculate similarity
    similarity = similarity_ratio(review_title, paper_title)

    if similarity < 0.6:  # Less than 60% similarity is suspicious
        return False, f"Title mismatch (similarity: {similarity:.1%})\n  Review: {review_title}\n  Paper:  {paper_title}"

    return True, f"Link verified (similarity: {similarity:.1%})"


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

        new_content = fix_review_header(content, correct_number)
        if new_content != content:
            changes.append("Fixed header")
            content = new_content

        new_content = remove_duplicate_links(content)
        if new_content != content:
            changes.append("Removed duplicates")
            content = new_content

        # Verify paper link matches the title
        link_valid, verify_msg = verify_paper_link(content, filepath)
        if not link_valid:
            # Report the mismatch but don't fail the operation
            print(f"\n⚠️  {filepath.name}: {verify_msg}")
            changes.append("⚠️ Link verification failed")

        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            result_msg = "; ".join(changes)
            if link_valid and "verified" in verify_msg.lower():
                result_msg += f" [{verify_msg}]"
            return True, result_msg

        return False, "No changes"

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


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_review_links.py <start> [count]")
        sys.exit(1)

    start_num = int(sys.argv[1])
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    reviews_dir = repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md"

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

    print(f"\n✅ Fixed {fixed}/{len(problematic)}")


if __name__ == "__main__":
    main()
