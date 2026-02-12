#!/usr/bin/env python3
"""
Twitter Thread Auto Poster to Telegram

Runs after telegram_uploader.py completes.
Generates Twitter threads for newly uploaded reviews and posts to Telegram.

Workflow:
1. Check which reviews were uploaded to Telegram today
2. Generate clickbait Twitter thread for each
3. Post thread to Hebrew Telegram channel
4. Log completion

Run manually:
  python3 twitter_thread_auto_poster.py --dry-run
  python3 twitter_thread_auto_poster.py

Scheduled: Runs at 11:05 AM daily (5 min after telegram upload)
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set, Dict
import yaml
import requests

# Add scripts directory to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / ".repo-tools" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import our thread builder
from twitter_thread_builder import (
    load_hebrew_review,
    build_thread,
    format_thread_for_telegram,
    extract_title,
    extract_arxiv_link
)

# Paths
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
MESSAGE_IDS_FILE = LOG_DIR / "telegram_message_ids.json"
TWITTER_THREADS_LOG = LOG_DIR / "twitter_threads_posted.log"
TELEGRAM_CONFIG_FILE = SCRIPTS_DIR / "telegram_config.yaml"
IMAGE_DIR = Path("/tmp/twitter_images")

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "twitter_thread_auto_poster.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_telegram_config() -> Dict:
    """Load Telegram configuration."""
    if not TELEGRAM_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Telegram config not found: {TELEGRAM_CONFIG_FILE}")

    with open(TELEGRAM_CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)


def get_reviews_uploaded_today() -> List[int]:
    """
    Get list of reviews uploaded to Telegram today.

    Returns:
        List of review numbers uploaded today
    """
    if not MESSAGE_IDS_FILE.exists():
        logger.warning(f"Message IDs file not found: {MESSAGE_IDS_FILE}")
        return []

    try:
        with open(MESSAGE_IDS_FILE, 'r') as f:
            message_data = json.load(f)

        today = datetime.now().date()
        today_reviews = []

        for review_key, data in message_data.items():
            # Skip non-numeric keys
            if not review_key.isdigit():
                continue

            review_num = int(review_key)

            # Check if Hebrew review was uploaded today
            hebrew_data = data.get('hebrew', {})
            timestamp_str = hebrew_data.get('timestamp', '')

            if timestamp_str:
                try:
                    # Parse timestamp: "2026-02-12T11:00:02"
                    upload_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    if upload_time.date() == today:
                        today_reviews.append(review_num)
                        logger.info(f"Found review {review_num} uploaded today at {timestamp_str}")
                except ValueError as e:
                    logger.warning(f"Could not parse timestamp for review {review_num}: {e}")

        return sorted(today_reviews)

    except Exception as e:
        logger.error(f"Error reading message IDs file: {e}")
        return []


def load_posted_threads() -> Set[int]:
    """Load reviews that already have Twitter threads posted."""
    if not TWITTER_THREADS_LOG.exists():
        return set()

    posted = set()
    try:
        with open(TWITTER_THREADS_LOG, 'r') as f:
            for line in f:
                # Format: timestamp | Review_XXX | success
                parts = line.strip().split('|')
                if len(parts) >= 3 and parts[2].strip() == 'success':
                    review_id = parts[1].strip()
                    if 'Review_' in review_id:
                        review_num = int(review_id.split('_')[1])
                        posted.add(review_num)
        return posted
    except Exception as e:
        logger.error(f"Error reading threads log: {e}")
        return set()


def log_thread_posted(review_num: int, status: str):
    """Log that Twitter thread was posted."""
    try:
        TWITTER_THREADS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(TWITTER_THREADS_LOG, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | Review_{review_num:03d} | {status}\n")
    except Exception as e:
        logger.error(f"Error writing to threads log: {e}")


def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long message into chunks."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by lines
    lines = text.split('\n')

    for line in lines:
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + '\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + '\n'

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def send_telegram_message(text: str, bot_token: str, chat_id: str,
                          parse_mode: str = 'HTML') -> bool:
    """Send message to Telegram channel (splits if too long)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Split if message is too long
    chunks = split_long_message(text, max_length=4000)

    logger.info(f"Sending {len(chunks)} message(s) to Telegram")

    for i, chunk in enumerate(chunks, 1):
        payload = {
            'chat_id': chat_id,
            'text': chunk,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info(f"✓ Message {i}/{len(chunks)} sent to Telegram")
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False

            # Small delay between chunks
            if i < len(chunks):
                import time
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error sending to Telegram: {e}")
            return False

    return True


def post_thread_to_telegram(review_num: int, config: Dict, dry_run: bool = False) -> bool:
    """
    Generate and post Twitter thread to Telegram.

    Args:
        review_num: Review number
        config: Telegram configuration
        dry_run: If True, don't actually post

    Returns:
        True if successful
    """
    logger.info(f"Processing review {review_num}...")

    # Load Hebrew review
    content = load_hebrew_review(review_num)
    if not content:
        logger.error(f"Could not load review {review_num}")
        return False

    # Build thread (clickbait style)
    logger.info(f"Building Twitter thread for review {review_num}...")
    thread = build_thread(content, review_num, clickbait=True)

    logger.info(f"✓ Thread built: {len(thread)} tweets")

    # Format for Telegram
    telegram_message = format_thread_for_telegram(thread)

    # Add header with review info
    title = extract_title(content)
    arxiv_link = extract_arxiv_link(content)

    header = f"🐦 TWITTER THREAD - Review {review_num}\n"
    header += f"📄 {title}\n"
    if arxiv_link:
        header += f"🔗 {arxiv_link}\n"
    header += "\n" + "="*40 + "\n\n"

    full_message = header + telegram_message

    if dry_run:
        logger.info("[DRY RUN] Would post to Telegram:")
        logger.info(f"  Review: {review_num}")
        logger.info(f"  Tweets: {len(thread)}")
        logger.info(f"  Message length: {len(full_message)} chars")
        return True

    # Post to Hebrew channel
    hebrew_config = config['hebrew_channel']
    bot_token = hebrew_config['bot_token']
    chat_id = hebrew_config['channel_id']

    logger.info(f"Posting thread to Telegram Hebrew channel...")
    success = send_telegram_message(full_message, bot_token, chat_id, parse_mode='HTML')

    if success:
        log_thread_posted(review_num, 'success')
        logger.info(f"✓ Twitter thread posted for review {review_num}")
    else:
        log_thread_posted(review_num, 'failed')
        logger.error(f"✗ Failed to post thread for review {review_num}")

    return success


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Auto-post Twitter threads to Telegram")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be posted')
    parser.add_argument('--force', action='store_true', help='Post even if already posted')
    parser.add_argument('--review', type=int, help='Post specific review number')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No messages will be posted")
        logger.info("=" * 60)

    logger.info("Starting Twitter Thread Auto Poster")
    logger.info(f"Repository: {REPO_ROOT}")

    # Load Telegram config
    try:
        config = load_telegram_config()
        logger.info("✓ Telegram config loaded")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1

    # Get reviews to process
    if args.review:
        reviews_to_process = [args.review]
        logger.info(f"Processing specific review: {args.review}")
    else:
        reviews_uploaded_today = get_reviews_uploaded_today()
        logger.info(f"Found {len(reviews_uploaded_today)} reviews uploaded today: {reviews_uploaded_today}")

        if not reviews_uploaded_today:
            logger.info("No reviews uploaded today. Nothing to do.")
            return 0

        # Filter out already posted (unless --force)
        if not args.force:
            already_posted = load_posted_threads()
            reviews_to_process = [r for r in reviews_uploaded_today if r not in already_posted]

            if len(reviews_to_process) < len(reviews_uploaded_today):
                skipped = len(reviews_uploaded_today) - len(reviews_to_process)
                logger.info(f"Skipping {skipped} already posted reviews")
        else:
            reviews_to_process = reviews_uploaded_today

    if not reviews_to_process:
        logger.info("No new reviews to process")
        return 0

    logger.info(f"Will process {len(reviews_to_process)} reviews: {reviews_to_process}")

    # Process each review
    success_count = 0
    failed_count = 0

    for review_num in reviews_to_process:
        try:
            if post_thread_to_telegram(review_num, config, dry_run=args.dry_run):
                success_count += 1
            else:
                failed_count += 1

            # Small delay between reviews
            if len(reviews_to_process) > 1 and not args.dry_run:
                import time
                time.sleep(2)

        except Exception as e:
            logger.exception(f"Error processing review {review_num}: {e}")
            failed_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Twitter Thread Posting Summary")
    logger.info("=" * 60)
    logger.info(f"  Posted:  {success_count}")
    logger.info(f"  Failed:  {failed_count}")
    logger.info("=" * 60)

    return 0 if failed_count == 0 else 1


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
