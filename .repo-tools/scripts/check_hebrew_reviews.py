#!/usr/bin/env python3
"""Diagnostic check for Hebrew review markdown files.

Checks for actual formatting issues, excluding intentional format differences:
- Hebrew reviews use 'Review XXX: TITLE' format (no # header) - this is intentional
- Reference links are OK (YouTube, blogs, etc.) - only flag duplicate paper links
"""

import re
from pathlib import Path
from collections import defaultdict

def has_hebrew(text: str) -> bool:
    """Check if text contains Hebrew characters."""
    return bool(re.search(r'[\u0590-\u05FF]', text))

def check_hebrew_review(file_path: Path) -> list[str]:
    """Check a single Hebrew review file for issues. Returns list of issue descriptions."""
    issues = []

    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        if not lines:
            issues.append("Empty file")
            return issues

        # Check 1: Line 1 should be in English (not Hebrew) - excluding "Review XXX:" prefix
        if lines[0]:
            line1_text = lines[0].replace('Review ', '').split(':', 1)[-1].strip()
            if has_hebrew(line1_text):
                issues.append(f"Hebrew title on line 1: '{line1_text[:40]}...'")

        # Check 2: Duplicate title on line 1 and line 3
        if len(lines) >= 3:
            line1 = lines[0].strip()
            line3 = lines[2].strip()

            if line1 and line3 and line1 == line3:
                issues.append(f"Duplicate title: '{line1[:40]}...'")

        # Check 3: Count paper links (arxiv, nature, etc.)
        arxiv_links = re.findall(r'https?://(?:www\.)?arxiv\.org/(abs|pdf)/[\d.]+', content)
        nature_links = re.findall(r'https?://(?:www\.)?nature\.com/articles/[^\s]+', content)
        doi_links = re.findall(r'https?://doi\.org/[^\s]+', content)
        acl_links = re.findall(r'https?://aclanthology\.org/[^\s]+', content)
        other_paper_links = re.findall(r'https?://(?:proceedings\.mlr\.press|openreview\.net|researchsquare\.com)/[^\s]+', content)

        # Collect all paper links
        all_paper_links = []
        for link in arxiv_links:
            all_paper_links.append(f"arxiv.org/{link[0]}/{link[1]}" if isinstance(link, tuple) else str(link))
        all_paper_links.extend(nature_links)
        all_paper_links.extend(doi_links)
        all_paper_links.extend(acl_links)
        all_paper_links.extend(other_paper_links)

        # Check for no paper links
        if len(all_paper_links) == 0:
            issues.append("No paper link found")

        # Check for duplicate paper links (same link appearing multiple times)
        link_counts = {}
        for link in all_paper_links:
            link_counts[link] = link_counts.get(link, 0) + 1

        duplicates = [link for link, count in link_counts.items() if count > 1]
        if duplicates:
            issues.append(f"Duplicate paper links: {len(duplicates)} link(s)")

        # Check 4: PDF links instead of abs
        pdf_links = [link for link in arxiv_links if 'pdf' in str(link)]
        if pdf_links:
            issues.append(f"PDF links found: {len(pdf_links)}")

        # Check 5: Line 2 should be blank
        if len(lines) >= 2 and lines[1].strip() != '':
            issues.append("Line 2 not empty (should be blank)")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def main():
    """Check all Hebrew review files."""
    reviews_dir = Path("/Users/mike_erlihson/personal/repos/scientific-resources/mike-paper-reviews-all/split-hebrew-reviews-md")

    all_issues = defaultdict(list)
    issue_counts = defaultdict(int)
    clean_count = 0
    total_count = 0

    # Get all review files
    review_files = sorted(reviews_dir.glob("Review_*.md"))

    for file_path in review_files:
        total_count += 1
        issues = check_hebrew_review(file_path)

        if issues:
            all_issues[file_path.name] = issues
            for issue in issues:
                # Categorize issue
                if "Duplicate title" in issue:
                    issue_counts["Duplicate titles"] += 1
                elif "Hebrew title" in issue:
                    issue_counts["Hebrew titles"] += 1
                elif "No paper link" in issue:
                    issue_counts["No link"] += 1
                elif "Duplicate paper links" in issue:
                    issue_counts["Duplicate paper links"] += 1
                elif "PDF links" in issue:
                    issue_counts["PDF links"] += 1
                elif "Line 2 not empty" in issue:
                    issue_counts["Line 2 formatting"] += 1
        else:
            clean_count += 1

    # Print summary
    print(f"\n{'='*80}")
    print(f"HEBREW REVIEWS DIAGNOSTIC CHECK")
    print(f"{'='*80}\n")
    print(f"Total reviews checked: {total_count}")
    print(f"Clean reviews: {clean_count} ({clean_count/total_count*100:.1f}%)")
    print(f"Reviews with issues: {len(all_issues)} ({len(all_issues)/total_count*100:.1f}%)")
    print(f"\n{'='*80}")
    print(f"ISSUE BREAKDOWN")
    print(f"{'='*80}\n")

    if issue_counts:
        for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            print(f"  {issue_type}: {count}")
    else:
        print("  ✅ No issues found!")

    # Print detailed issues (first 20)
    if all_issues:
        print(f"\n{'='*80}")
        print(f"SAMPLE ISSUES (first 20 files)")
        print(f"{'='*80}\n")

        for i, (filename, issues) in enumerate(sorted(all_issues.items())[:20]):
            print(f"\n{filename}:")
            for issue in issues:
                print(f"  - {issue}")

        if len(all_issues) > 20:
            print(f"\n... and {len(all_issues) - 20} more files with issues")

    print(f"\n{'='*80}")
    print(f"NOTE: Reference links (YouTube, blogs, etc.) are NOT flagged as issues.")
    print(f"      Hebrew reviews use 'Review XXX: TITLE' format (no # header) - this is intentional.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
