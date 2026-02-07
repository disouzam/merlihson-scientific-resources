#!/usr/bin/env python3
"""
Fix English Review Metadata Spacing

Fixes the issue where "Mike's Daily Paper Review: DD.MM.YY, Review XXX"
is concatenated with the next line without proper spacing.

Example fix:
  BEFORE: Mike's Daily Paper Review: 06.02.26, Review 574Scaling Embedding...
  AFTER:  Mike's Daily Paper Review: 06.02.26, Review 574

          Scaling Embedding...
"""

import re
import sys
from pathlib import Path

# Configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENGLISH_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-english-reviews-md"


def fix_metadata_spacing(content: str) -> tuple[str, bool]:
    """
    Fix spacing in metadata line if it's concatenated with following text.

    Pattern to detect:
      Mike's Daily Paper Review: 06.02.26, Review 574SomeText...
                                                     ^-- No space here!

    Returns:
        (fixed_content, was_modified)
    """
    # Pattern: Metadata line concatenated with uppercase letter (start of title)
    pattern = r"(Mike's Daily Paper Review: \d{2}\.\d{2}\.\d{2}, Review \d+)([A-Z])"

    def replacement(match):
        metadata = match.group(1)
        next_char = match.group(2)
        # Insert newline + blank line + the character
        return f"{metadata}\n\n{next_char}"

    fixed_content, num_subs = re.subn(pattern, replacement, content)

    return fixed_content, num_subs > 0


def fix_single_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Fix spacing in a single markdown file.

    Returns:
        True if file was modified
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        fixed_content, was_modified = fix_metadata_spacing(content)

        if was_modified:
            if dry_run:
                print(f"[DRY RUN] Would fix: {file_path.name}")
                # Show the change
                original_line = re.search(
                    r"Mike's Daily Paper Review: \d{2}\.\d{2}\.\d{2}, Review \d+[A-Z].*",
                    content
                )
                if original_line:
                    print(f"  BEFORE: {original_line.group(0)[:80]}...")

                fixed_line = re.search(
                    r"Mike's Daily Paper Review: \d{2}\.\d{2}\.\d{2}, Review \d+\n",
                    fixed_content
                )
                if fixed_line:
                    print(f"  AFTER:  {fixed_line.group(0).strip()}")
                    print(f"          (newline added)")
                print()
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"✓ Fixed: {file_path.name}")

        return was_modified

    except Exception as e:
        print(f"✗ Error processing {file_path.name}: {e}")
        return False


def main():
    """Main entry point."""
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 60)
        print()

    print(f"Scanning English reviews in: {ENGLISH_MD_DIR}")
    print()

    # Get all English review markdown files
    review_files = sorted(ENGLISH_MD_DIR.glob("Review_*.md"))

    if not review_files:
        print("No review files found!")
        return 1

    print(f"Found {len(review_files)} review files")
    print()

    # Process each file
    fixed_count = 0
    for file_path in review_files:
        if fix_single_file(file_path, dry_run):
            fixed_count += 1

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total files checked: {len(review_files)}")
    print(f"Files with spacing issues: {fixed_count}")

    if dry_run and fixed_count > 0:
        print()
        print("Run without --dry-run to apply fixes")
    elif fixed_count > 0:
        print()
        print("✓ All spacing issues fixed!")
    else:
        print()
        print("✓ No spacing issues found - all files OK!")

    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
