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
import re
import logging
import subprocess
import time
import random
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
    load_english_review,
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


def check_telegram_channel_for_threads(bot_token: str, chat_id: str) -> Set[int]:
    """
    Check Telegram channel for already-posted Twitter threads.
    Prevents duplicate posts when running from multiple machines.

    Returns set of review numbers that already have threads posted.
    """
    posted = set()
    try:
        # Get recent messages from the channel
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        # Use getHistory via channel messages
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        response = requests.get(url, params={'chat_id': chat_id}, timeout=15)

        # Search recent messages for thread patterns
        # Twitter threads typically contain "🧵" or "Thread" and "Review NNN"
        search_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {'offset': -100, 'limit': 100, 'allowed_updates': ['channel_post']}
        resp = requests.get(search_url, params=params, timeout=15)

        if resp.status_code == 200 and resp.json().get('ok'):
            for update in resp.json().get('result', []):
                msg = update.get('channel_post', {})
                text = msg.get('text', '')
                if '🧵' in text or 'thread' in text.lower():
                    match = re.search(r'(?:Review|סקירה)\s*#?\s*(\d+)', text)
                    if match:
                        posted.add(int(match.group(1)))

        if posted:
            logger.info(f"Found {len(posted)} reviews with Twitter threads already in Telegram channel")

    except Exception as e:
        logger.warning(f"Could not check Telegram channel for threads: {e}")
        # Don't block posting if check fails

    return posted


# --- Git-tracked upload ledger (cross-machine duplicate prevention) ---

TWITTER_LEDGER_FILE = REPO_ROOT / ".repo-tools" / "logs" / "twitter_upload_ledger.json"


def load_twitter_ledger() -> Set[int]:
    """Load the git-tracked Twitter thread ledger (shared across all machines)."""
    if not TWITTER_LEDGER_FILE.exists():
        return set()
    try:
        with open(TWITTER_LEDGER_FILE, 'r') as f:
            data = json.load(f)
        return set(data.get('posted', []))
    except Exception as e:
        logger.error(f"Error reading Twitter ledger: {e}")
        return set()


def check_remote_twitter_ledger(review_num: int) -> bool:
    """
    Check the REMOTE Twitter ledger via git fetch + git show (defense in depth).

    Catches cases where the other machine uploaded and pushed the ledger
    but our local repo hasn't pulled yet.
    """
    try:
        rel_path = TWITTER_LEDGER_FILE.relative_to(REPO_ROOT)
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'fetch', '--quiet'],
            capture_output=True, timeout=60,
        )
        result = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'show', f'origin/main:{rel_path}'],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            remote_data = json.loads(result.stdout)
            remote_posted = set(remote_data.get('posted', []))
            if review_num in remote_posted:
                logger.info(f"Review_{review_num} found in REMOTE Twitter ledger (git fetch check)")
                return True
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as e:
        logger.warning(f"Remote Twitter ledger check failed ({e}), proceeding with local state.")
    return False


def update_twitter_ledger(review_num: int):
    """Add review to git-tracked ledger and immediately commit + push."""
    try:
        if TWITTER_LEDGER_FILE.exists():
            with open(TWITTER_LEDGER_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {'posted': []}

        reviews = set(data.get('posted', []))
        reviews.add(review_num)
        data['posted'] = sorted(reviews)

        TWITTER_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TWITTER_LEDGER_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Committing Twitter ledger for Review_{review_num}...")
        subprocess.run(['git', '-C', str(REPO_ROOT), 'add', str(TWITTER_LEDGER_FILE)],
                       capture_output=True, timeout=10)
        subprocess.run(['git', '-C', str(REPO_ROOT), 'commit', '-m',
                        f'twitter: mark Review_{review_num} as posted', '--no-verify'],
                       capture_output=True, timeout=15)
        subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                       capture_output=True, timeout=30)
        # Retry push up to 3 times (critical: prevents duplicate posts across machines)
        for attempt in range(1, 4):
            push_result = subprocess.run(['git', '-C', str(REPO_ROOT), 'push'],
                                         capture_output=True, text=True, timeout=30)
            if push_result.returncode == 0:
                logger.info(f"✓ Twitter ledger pushed (Review_{review_num} locked)")
                break
            else:
                logger.warning(f"Twitter ledger push attempt {attempt}/3 failed: {push_result.stderr.strip()}")
                if attempt < 3:
                    time.sleep(attempt * 5)
                    subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                                   capture_output=True, timeout=30)
                else:
                    logger.error(f"CRITICAL: Twitter ledger push failed after 3 attempts for Review_{review_num}. "
                                 f"Duplicate post possible if another machine runs before manual push.")
    except Exception as e:
        logger.error(f"Error updating Twitter ledger: {e}")


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
                          parse_mode: str = None) -> bool:
    """Send message to Telegram channel (splits if too long)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Split if message is too long
    chunks = split_long_message(text, max_length=4000)

    logger.info(f"Sending {len(chunks)} message(s) to Telegram")

    for i, chunk in enumerate(chunks, 1):
        payload = {
            'chat_id': chat_id,
            'text': chunk,
            'disable_web_page_preview': False
        }
        if parse_mode:
            payload['parse_mode'] = parse_mode

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

    # Load English review (optional — enhances paper name & hook)
    english_content = load_english_review(review_num)
    if english_content:
        logger.info(f"English review found for review {review_num} — using for paper name & hook")

    # Build thread (clickbait style)
    logger.info(f"Building Twitter thread for review {review_num}...")
    thread = build_thread(content, review_num, clickbait=True,
                          english_content=english_content)

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

    # Last-second cross-machine check: pull and re-check ledger right before posting
    logger.info(f"Final ledger check before posting Review_{review_num} thread...")
    subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                   capture_output=True, timeout=30)
    if review_num in load_twitter_ledger():
        logger.info(f"Review_{review_num} appeared in ledger — skipping (other machine posted it)")
        log_thread_posted(review_num, 'success')
        return True

    # Defense in depth: also check remote ledger directly via git fetch + git show
    if check_remote_twitter_ledger(review_num):
        logger.info(f"Review_{review_num} found in remote ledger — skipping (other machine posted it)")
        log_thread_posted(review_num, 'success')
        return True

    # Post to Hebrew test channel (twitter threads stay on test channel)
    threads_config = config.get('twitter_threads', config['hebrew_channel'])
    bot_token = threads_config['bot_token']
    chat_id = threads_config['channel_id']

    logger.info(f"Posting thread to Telegram ({threads_config.get('username', 'unknown')})...")
    success = send_telegram_message(full_message, bot_token, chat_id, parse_mode=None)

    if success:
        log_thread_posted(review_num, 'success')
        update_twitter_ledger(review_num)
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

    # Deterministic startup delay based on machine_id (cross-machine race prevention)
    if not args.dry_run and not args.review:
        machine_id = config.get('settings', {}).get('machine_id', 1)
        slot_start = (machine_id - 1) * 120
        delay = random.randint(slot_start, slot_start + 20)
        logger.info(f"Startup delay: {delay}s (machine_id={machine_id}, slot {slot_start}-{slot_start+20}s)")
        time.sleep(delay)

    # Discard local changes to auto-generated files before pulling.
    # These files are regenerated by the pre-commit hook, so local diffs
    # are stale and cause recurring stash-pop merge conflicts.
    AUTO_GENERATED_FILES = [
        'mike-paper-reviews-all/readme.md',
        'README.md',
        'presentations/readme.md',
        'CLAUDE.md',
    ]
    for f in AUTO_GENERATED_FILES:
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'checkout', '--', f],
            capture_output=True, text=True, timeout=10
        )

    # Pull latest from remote (critical: gets ledger from other machines)
    logger.info("Pulling latest from remote (for cross-machine ledger sync)...")
    try:
        pull_result = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
            capture_output=True, text=True, timeout=60
        )
        if pull_result.returncode != 0:
            logger.error(f"Git pull FAILED: {pull_result.stderr.strip()}")
            logger.error("Cannot proceed without a clean pull — risk of duplicate posts. Aborting.")
            return 1
        else:
            logger.info("✓ Repo up to date")
    except subprocess.TimeoutExpired:
        logger.error("Git pull timed out after 60s. Aborting to avoid duplicate posts.")
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
        # Check local log + git ledger + Telegram channel to prevent duplicates
        if not args.force:
            already_posted = load_posted_threads()
            already_posted = already_posted | load_twitter_ledger()
            # Also check Telegram channel history for threads already posted by another machine
            channel_posted = check_telegram_channel_for_threads(
                config.get('twitter_threads', {}).get('bot_token', config.get('hebrew', {}).get('bot_token', '')),
                config.get('twitter_threads', {}).get('channel_id', config.get('hebrew', {}).get('channel_id', ''))
            )
            already_posted = already_posted | channel_posted
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
