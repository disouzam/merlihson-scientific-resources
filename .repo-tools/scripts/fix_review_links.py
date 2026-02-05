#!/usr/bin/env python3
"""
Skill: Fix Review Links
Automatically fixes common issues in review markdown files:
- Corrects wrong review numbers
- Removes duplicate links (arxiv/HuggingFace/OpenReview)
- Removes dates from titles
- Separates embedded links from titles
- Verifies paper link matches review title
- Auto-corrects wrong paper links by searching arXiv
"""

import re
import sys
import urllib.request
import urllib.parse
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
            # Remove any standalone arxiv, HuggingFace, OpenReview, or Hebrew paper links
            if (stripped.startswith('https://arxiv.org/abs/') or
                stripped.startswith('https://huggingface.co/papers/') or
                stripped.startswith('https://openreview.net/') or
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

        new_content = fix_review_header(content, correct_number)
        if new_content != content:
            changes.append("Fixed header")
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


def fix_review_number_only(filepath: Path) -> Tuple[bool, str]:
    """Fix only the review number in a file (for reviews with just 1 link)."""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        correct_number = extract_review_number(filepath.name)
        if correct_number == 0:
            return False, "Could not extract review number"

        new_content = fix_review_header(content, correct_number)
        if new_content != content:
            filepath.write_text(new_content, encoding='utf-8')
            return True, "Fixed review number"

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
        print("Usage: fix_review_links.py <start> [count]")
        print("       fix_review_links.py --fix-numbers <start> <end>")
        sys.exit(1)

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    reviews_dir = repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md"

    # Mode: Fix numbering mismatches
    if sys.argv[1] == '--fix-numbers':
        if len(sys.argv) < 4:
            print("Usage: fix_review_links.py --fix-numbers <start> <end>")
            sys.exit(1)

        start_num = int(sys.argv[2])
        end_num = int(sys.argv[3])

        print(f"🔍 Checking for numbering mismatches in reviews {start_num}-{end_num}...")
        mismatches = find_numbering_mismatches(start_num, end_num, reviews_dir)

        if not mismatches:
            print("✓ No numbering mismatches found")
            return

        print(f"Found {len(mismatches)} reviews with wrong numbers")
        print("\n🔧 Fixing...")

        fixed = 0
        for filepath in mismatches:
            was_modified, desc = fix_review_number_only(filepath)
            if was_modified:
                print(f"✓ {filepath.name}: {desc}")
                fixed += 1

        print(f"\n✅ Fixed {fixed}/{len(mismatches)}")
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

    print(f"\n✅ Fixed {fixed}/{len(problematic)}")


if __name__ == "__main__":
    main()
