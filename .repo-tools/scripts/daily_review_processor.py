#!/usr/bin/env python3
"""
Daily Review Processor - Automated review file processing

This script:
1. Scans ~/Downloads/ for new Review_XXX.docx files
2. Deduplicates by checking existing reviews in the repo
3. Processes new reviews: copy DOCX, convert to markdown
4. Commits and pushes changes to GitHub
5. Logs all actions for monitoring

Run manually: python3 daily_review_processor.py [--dry-run]
Scheduled: Runs daily at 5:00 AM via launchd
"""

import sys
import re
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set

# Script configuration
DOWNLOADS_DIR = Path.home() / "Downloads"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_DIR = REPO_ROOT / "mike-paper-reviews-all"
DOCX_DIR = REVIEWS_DIR / "split-reviews-docx"
HEBREW_MD_DIR = REVIEWS_DIR / "split-hebrew-reviews-md"
ENGLISH_MD_DIR = REVIEWS_DIR / "split-english-reviews-md"
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
CONVERTER_SCRIPT = REPO_ROOT / ".repo-tools" / "scripts" / "convert_docx_to_md.py"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "daily_processor.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def get_existing_review_numbers() -> Set[int]:
    """Get set of all existing review numbers in repo."""
    existing = set()

    if not DOCX_DIR.exists():
        logger.warning(f"DOCX directory not found: {DOCX_DIR}")
        return existing

    for file in DOCX_DIR.glob("Review_*.docx"):
        match = re.search(r'Review_(\d+)\.docx', file.name)
        if match:
            existing.add(int(match.group(1)))

    logger.info(f"Found {len(existing)} existing reviews in repo (up to Review_{max(existing) if existing else 0})")
    return existing


def find_new_reviews() -> List[Dict[str, any]]:
    """Find Review_XXX.docx files in Downloads that don't exist in repo."""

    if not DOWNLOADS_DIR.exists():
        logger.error(f"Downloads directory not found: {DOWNLOADS_DIR}")
        return []

    existing_reviews = get_existing_review_numbers()
    new_reviews = []

    # Scan Downloads for Review files
    for file in DOWNLOADS_DIR.glob("Review_*.docx"):
        # Skip English files (we'll find them separately)
        if "_english" in file.name.lower():
            continue

        # Extract review number
        match = re.search(r'Review_(\d+)\.docx', file.name, re.IGNORECASE)
        if not match:
            logger.debug(f"Skipping file with unexpected format: {file.name}")
            continue

        review_num = int(match.group(1))

        # Deduplication: skip if already exists in repo
        if review_num in existing_reviews:
            logger.debug(f"Review_{review_num} already exists in repo, skipping")
            continue

        # Look for corresponding English file
        english_candidates = [
            DOWNLOADS_DIR / f"Review_{review_num}_english.docx",
            DOWNLOADS_DIR / f"Review_{review_num}_English.docx",
            DOWNLOADS_DIR / f"review_{review_num}_english.docx",
        ]

        english_file = None
        for candidate in english_candidates:
            if candidate.exists():
                english_file = candidate
                break

        new_reviews.append({
            'number': review_num,
            'hebrew_file': file,
            'english_file': english_file
        })

    # Sort by review number
    new_reviews.sort(key=lambda x: x['number'])

    if new_reviews:
        logger.info(f"Found {len(new_reviews)} new review(s) to process: {[r['number'] for r in new_reviews]}")
    else:
        logger.info("No new reviews found in Downloads")

    return new_reviews


def extract_title_from_markdown(md_path: Path) -> Optional[str]:
    """Extract paper title from markdown file (first substantial line)."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Look for first substantial line that's likely a title
        for line in lines[:15]:
            line = line.strip()
            # Skip empty lines, version numbers, and Hebrew-only lines
            if not line or len(line) < 10:
                continue
            if re.match(r'^v\d+$', line):
                continue
            # If line has English content, likely a title
            if re.search(r'[A-Za-z]', line):
                ascii_ratio = sum(1 for c in line if ord(c) < 128) / len(line)
                if ascii_ratio > 0.5:
                    return line

        return None
    except Exception as e:
        logger.error(f"Error extracting title from {md_path}: {e}")
        return None


def process_review(review_info: Dict[str, any], dry_run: bool = False) -> bool:
    """
    Process a single review: copy DOCX, convert to MD, format with title.

    Returns True if successful, False otherwise.
    """
    review_num = review_info['number']
    hebrew_file = review_info['hebrew_file']
    english_file = review_info['english_file']

    logger.info(f"Processing Review_{review_num}...")

    try:
        # Ensure directories exist
        DOCX_DIR.mkdir(parents=True, exist_ok=True)
        HEBREW_MD_DIR.mkdir(parents=True, exist_ok=True)
        ENGLISH_MD_DIR.mkdir(parents=True, exist_ok=True)

        # File paths
        hebrew_docx_dest = DOCX_DIR / f"Review_{review_num:03d}.docx"
        hebrew_md_dest = HEBREW_MD_DIR / f"Review_{review_num:03d}.md"
        english_md_dest = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"

        if dry_run:
            logger.info(f"  [DRY RUN] Would copy {hebrew_file.name} → {hebrew_docx_dest}")
            logger.info(f"  [DRY RUN] Would convert to {hebrew_md_dest.name}")
            if english_file:
                logger.info(f"  [DRY RUN] Would convert {english_file.name} → {english_md_dest.name}")
            return True

        # Step 1: Copy Hebrew DOCX to repo
        logger.info(f"  Copying {hebrew_file.name} → {hebrew_docx_dest.name}")
        shutil.copy2(hebrew_file, hebrew_docx_dest)

        # Step 2: Convert Hebrew DOCX to Markdown
        logger.info(f"  Converting Hebrew DOCX → Markdown")
        result = subprocess.run(
            [sys.executable, str(CONVERTER_SCRIPT), str(hebrew_file), str(hebrew_md_dest)],
            capture_output=True,
            text=True,
            check=True
        )
        logger.debug(f"  Converter output: {result.stdout.strip()}")

        # Step 3: Extract title and prepend to markdown
        title = extract_title_from_markdown(hebrew_md_dest)
        if title:
            # Read current content
            content = hebrew_md_dest.read_text(encoding='utf-8')
            # Prepend "Review XXX: TITLE"
            new_content = f"Review {review_num}: {title}\n\n{content}"
            hebrew_md_dest.write_text(new_content, encoding='utf-8')
            logger.info(f"  Added title header: Review {review_num}: {title[:50]}...")
        else:
            logger.warning(f"  Could not extract title from {hebrew_md_dest.name}")

        # Step 4: Convert English DOCX if exists
        if english_file:
            logger.info(f"  Converting English DOCX → Markdown")
            result = subprocess.run(
                [sys.executable, str(CONVERTER_SCRIPT), str(english_file), str(english_md_dest)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"  Converter output: {result.stdout.strip()}")
        else:
            logger.info(f"  No English file found for Review_{review_num}")

        logger.info(f"✓ Successfully processed Review_{review_num}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Conversion failed for Review_{review_num}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"✗ Error processing Review_{review_num}: {e}")
        return False


def commit_and_push(processed_reviews: List[int], dry_run: bool = False) -> bool:
    """
    Commit processed reviews and push to GitHub.

    The pre-commit hook will automatically update metadata.
    """
    if not processed_reviews:
        return True

    try:
        # Change to repo directory
        subprocess.run(['git', '-C', str(REPO_ROOT), 'status'], check=True, capture_output=True)

        if dry_run:
            logger.info(f"[DRY RUN] Would commit and push {len(processed_reviews)} review(s)")
            return True

        # Stage all new files
        logger.info("Staging files for commit...")
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'add',
             'mike-paper-reviews-all/split-reviews-docx/',
             'mike-paper-reviews-all/split-hebrew-reviews-md/',
             'mike-paper-reviews-all/split-english-reviews-md/'],
            check=True,
            capture_output=True
        )

        # Create commit message
        if len(processed_reviews) == 1:
            review_num = processed_reviews[0]
            commit_msg = f"Add Review_{review_num:03d} (automated daily processing)\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        else:
            review_list = ", ".join([f"Review_{num:03d}" for num in processed_reviews])
            commit_msg = f"Add {len(processed_reviews)} reviews: {review_list}\n\nAutomated daily processing\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

        # Commit (pre-commit hook will run and update metadata)
        logger.info("Creating commit...")
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'commit', '-m', commit_msg],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✓ Commit created (metadata auto-updated by pre-commit hook)")

        # Push to remote
        logger.info("Pushing to GitHub...")
        result = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'push'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("✓ Successfully pushed to GitHub")
            return True
        else:
            logger.error(f"✗ Push failed: {result.stderr}")
            logger.info("  Files are committed locally. You can manually push later.")
            return False

    except subprocess.TimeoutExpired:
        logger.error("✗ Push timed out (network issue?)")
        logger.info("  Files are committed locally. You can manually push later.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Git operation failed: {e.stderr if e.stderr else str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error during commit/push: {e}")
        return False


def wait_for_network(timeout: int = 60) -> bool:
    """
    Wait for network connection after wake from sleep.

    When Mac wakes from sleep, Wi-Fi takes a few seconds to connect.
    This function waits for network availability before proceeding.

    Args:
        timeout: Maximum seconds to wait for network (default: 60)

    Returns:
        True if network is available, False if timeout
    """
    import time

    logger.info("Checking network connectivity...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Try to ping Google DNS (8.8.8.8)
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✓ Network is available")
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            logger.debug(f"Network check error: {e}")

        logger.info("Waiting for network...")
        time.sleep(5)

    logger.warning(f"⚠️  Network timeout after {timeout}s, proceeding anyway")
    return False


def main():
    """Main entry point for daily review processor."""

    # Parse arguments
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No files will be modified")
        logger.info("=" * 60)

    logger.info("Starting daily review processor")
    logger.info(f"Repository: {REPO_ROOT}")
    logger.info(f"Downloads: {DOWNLOADS_DIR}")

    # Wait for network (important after wake from sleep)
    wait_for_network(timeout=60)

    # Find new reviews
    new_reviews = find_new_reviews()

    if not new_reviews:
        logger.info("No new reviews to process. Exiting.")
        return 0

    # Process each review
    processed = []
    failed = []

    for review in new_reviews:
        if process_review(review, dry_run=dry_run):
            processed.append(review['number'])
        else:
            failed.append(review['number'])

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Processing complete: {len(processed)} succeeded, {len(failed)} failed")
    if processed:
        logger.info(f"  Processed: {processed}")
    if failed:
        logger.info(f"  Failed: {failed}")
    logger.info("=" * 60)

    # Commit and push if we processed anything
    if processed and not dry_run:
        commit_and_push(processed, dry_run=dry_run)

    # Return exit code
    if failed:
        return 1  # Partial failure
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
