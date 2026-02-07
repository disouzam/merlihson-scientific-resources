#!/usr/bin/env python3
"""Diagnostic check for English review markdown files."""

import re
from pathlib import Path
from collections import defaultdict

def check_english_review(file_path: Path) -> list[str]:
    """Check a single English review file for issues. Returns list of issue descriptions."""
    issues = []

    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        if not lines:
            issues.append("Empty file")
            return issues

        # Check 1: Duplicate title on line 1 and line 3
        if len(lines) >= 4:
            line1 = lines[0].strip().lstrip('#').strip()
            line3 = lines[2].strip().lstrip('#').strip()

            if line1 and line3 and line1 == line3:
                issues.append(f"Duplicate title: '{line1[:60]}...'")

        # Check 2: Count paper links
        arxiv_links = re.findall(r'https?://(?:www\.)?arxiv\.org/(abs|pdf)/[\d.]+', content)
        nature_links = re.findall(r'https?://(?:www\.)?nature\.com/articles/', content)
        doi_links = re.findall(r'https?://doi\.org/', content)
        openai_links = re.findall(r'https?://openai\.com/', content)
        acl_links = re.findall(r'https?://aclanthology\.org/', content)
        google_links = re.findall(r'https?://research\.google/', content)
        other_links = re.findall(r'https?://(?:proceedings\.mlr\.press|openreview\.net|huggingface\.co/papers|researchsquare\.com)', content)

        total_links = len(arxiv_links) + len(nature_links) + len(doi_links) + len(openai_links) + len(acl_links) + len(google_links) + len(other_links)

        if total_links == 0:
            issues.append("No paper link found")
        elif total_links > 1:
            issues.append(f"Multiple links: {len(arxiv_links)} arxiv, {len(nature_links)} nature, {len(doi_links)} doi, {len(openai_links)} openai, {len(acl_links)} acl, {len(google_links)} google, {len(other_links)} other")

        # Check 3: PDF links instead of abs
        pdf_links = [link for link in arxiv_links if 'pdf' in link[1]]
        if pdf_links:
            issues.append(f"PDF links found: {len(pdf_links)}")

        # Check 4: Line 1 should start with "Review XXX:" format (not markdown #)
        if lines[0] and not re.match(r'^Review \d+:', lines[0]):
            issues.append("Line 1 should start with 'Review XXX:' format")

        # Check 5: Check for common formatting issues
        # Empty line 2 (should be between title lines)
        if len(lines) >= 2 and lines[1].strip() != '':
            issues.append("Line 2 not empty (should be blank between titles)")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def main():
    """Check all English review files."""
    reviews_dir = Path("/Users/michaelerlihson/Personal/Projects/scientific_repo/mike-paper-reviews-all/split-english-reviews-md")

    all_issues = defaultdict(list)
    issue_counts = defaultdict(int)
    clean_count = 0
    total_count = 0

    # Get all review files
    review_files = sorted(reviews_dir.glob("Review_*.md"))

    for file_path in review_files:
        total_count += 1
        issues = check_english_review(file_path)

        if issues:
            all_issues[file_path.name] = issues
            for issue in issues:
                # Categorize issue
                if "Duplicate title" in issue:
                    issue_counts["Duplicate titles"] += 1
                elif "No paper link" in issue:
                    issue_counts["No link"] += 1
                elif "Multiple links" in issue:
                    issue_counts["Multiple links"] += 1
                elif "PDF links" in issue:
                    issue_counts["PDF links"] += 1
                elif "should start with 'Review XXX:'" in issue:
                    issue_counts["Missing Review XXX: header"] += 1
                elif "Line 2 not empty" in issue:
                    issue_counts["Line 2 formatting"] += 1
        else:
            clean_count += 1

    # Print summary
    print(f"\n{'='*80}")
    print(f"ENGLISH REVIEWS DIAGNOSTIC CHECK")
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

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
