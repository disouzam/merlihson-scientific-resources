#!/usr/bin/env python3
"""
Telegram Review Uploader - Automated Telegram channel posting

This script:
1. Checks git log for reviews added in the last 24 hours
2. Reads markdown files from the repo
3. Checks for duplicates (local log + channel history)
4. Splits long messages at paragraph boundaries
5. Uploads to appropriate Telegram channel (Hebrew or English)
6. Logs all uploads

Run manually: python3 telegram_uploader.py [--dry-run] [--hours N]
Scheduled: Runs daily at 11:00 AM via launchd
"""

import sys
import re
import subprocess
import logging
import json
import time
import html
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
import requests
import yaml

# Script configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HEBREW_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-hebrew-reviews-md"
ENGLISH_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-english-reviews-md"
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
CONFIG_FILE = REPO_ROOT / ".repo-tools" / "scripts" / "telegram_config.yaml"
UPLOAD_LOG_FILE = LOG_DIR / "telegram_uploads.log"

# Telegram limits
MAX_MESSAGE_LENGTH = 4096

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "telegram_uploader.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TelegramConfig:
    """Configuration holder for Telegram credentials."""

    def __init__(self, config_path: Path):
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create it from telegram_config.yaml.template"
            )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.hebrew_bot_token = config['hebrew_channel']['bot_token']
        self.hebrew_channel_id = config['hebrew_channel']['channel_id']
        self.english_bot_token = config['english_channel']['bot_token']
        self.english_channel_id = config['english_channel']['channel_id']

        self.max_message_length = config.get('settings', {}).get('max_message_length', 4096)
        self.check_history_depth = config.get('settings', {}).get('check_history_depth', 100)
        self.retry_on_failure = config.get('settings', {}).get('retry_on_failure', True)
        self.retry_count = config.get('settings', {}).get('retry_count', 2)
        self.retry_delay_seconds = config.get('settings', {}).get('retry_delay_seconds', 5)

        # Validate tokens
        if 'YOUR_' in self.hebrew_bot_token or 'YOUR_' in self.english_bot_token:
            raise ValueError("Please configure your bot tokens in telegram_config.yaml")


def get_new_reviews_from_git(hours: int = 24) -> Dict[str, List[int]]:
    """
    Check git log for reviews added in the last N hours.

    Returns dict with 'hebrew' and 'english' keys, each containing list of review numbers.
    """
    since = f"{hours} hours ago"

    try:
        # Get files changed in last N hours
        result = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'log', f'--since={since}',
             '--name-only', '--pretty=format:'],
            capture_output=True,
            text=True,
            check=True
        )

        files = result.stdout.strip().split('\n')
        files = [f.strip() for f in files if f.strip()]

        hebrew_reviews = set()
        english_reviews = set()

        for file in files:
            # Check for Hebrew reviews
            if 'split-hebrew-reviews-md/Review_' in file and file.endswith('.md'):
                match = re.search(r'Review_(\d+)\.md', file)
                if match:
                    hebrew_reviews.add(int(match.group(1)))

            # Check for English reviews
            elif 'split-english-reviews-md/Review_' in file and file.endswith('.md'):
                match = re.search(r'Review_(\d+)\.md', file)
                if match:
                    english_reviews.add(int(match.group(1)))

        result = {
            'hebrew': sorted(list(hebrew_reviews)),
            'english': sorted(list(english_reviews))
        }

        logger.info(f"Found {len(result['hebrew'])} new Hebrew reviews, "
                   f"{len(result['english'])} new English reviews (last {hours} hours)")

        return result

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running git log: {e}")
        return {'hebrew': [], 'english': []}


def read_markdown_file(file_path: Path) -> Optional[str]:
    """Read markdown file and return content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split text into multiple messages at paragraph boundaries.

    Telegram has a 4096 character limit per message.
    We split at paragraph boundaries to maintain readability.
    """
    if len(text) <= max_length:
        return [text]

    # Split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    messages = []
    current_message = ""

    for para in paragraphs:
        # If adding this paragraph would exceed limit
        if len(current_message) + len(para) + 2 > max_length:
            # Save current message if not empty
            if current_message:
                messages.append(current_message.strip())
                current_message = ""

            # If single paragraph is too long, split it at sentence boundaries
            if len(para) > max_length:
                sentences = para.split('. ')
                temp = ""
                for sentence in sentences:
                    if len(temp) + len(sentence) + 2 < max_length:
                        temp += sentence + ". "
                    else:
                        if temp:
                            messages.append(temp.strip())
                        temp = sentence + ". "
                if temp:
                    current_message = temp
            else:
                current_message = para + "\n\n"
        else:
            current_message += para + "\n\n"

    # Add remaining content
    if current_message:
        messages.append(current_message.strip())

    return messages


def escape_for_telegram_html(text: str) -> str:
    """
    Escape text for Telegram HTML parse mode.

    HTML mode requires escaping: <, >, &, and "
    Python's html.escape() handles this perfectly.
    Parentheses, periods, and technical characters do NOT need escaping.
    """
    return html.escape(text, quote=True)


def send_telegram_message(bot_token: str, chat_id: str, text: str,
                         retry_count: int = 2, retry_delay: int = 5) -> bool:
    """
    Send message to Telegram channel via Bot API.

    Returns True if successful, False otherwise.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    for attempt in range(retry_count + 1):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                if attempt < retry_count:
                    logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{retry_count})")
                    time.sleep(retry_delay)
                else:
                    return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {e}")
            if attempt < retry_count:
                logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{retry_count})")
                time.sleep(retry_delay)
            else:
                return False

    return False


def get_channel_history(bot_token: str, chat_id: str, limit: int = 100) -> Set[int]:
    """
    Get recent messages from channel and extract review numbers.

    Returns set of review numbers found in channel history.
    """
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        result = response.json()

        if not result.get('ok'):
            logger.warning(f"Could not fetch channel history: {result.get('description')}")
            return set()

        # Extract review numbers from messages
        review_numbers = set()
        for update in result.get('result', [])[-limit:]:
            if 'channel_post' in update:
                text = update['channel_post'].get('text', '')
                # Look for "Review XXX" or "Review_XXX" pattern
                matches = re.findall(r'Review[_\s](\d+)', text, re.IGNORECASE)
                for match in matches:
                    review_numbers.add(int(match))

        logger.debug(f"Found {len(review_numbers)} reviews in channel history")
        return review_numbers

    except Exception as e:
        logger.warning(f"Error fetching channel history: {e}")
        return set()


def load_upload_log() -> Dict[str, Set[int]]:
    """
    Load upload history from local log file.

    Returns dict with 'hebrew' and 'english' keys, each containing set of uploaded review numbers.
    """
    if not UPLOAD_LOG_FILE.exists():
        return {'hebrew': set(), 'english': set()}

    uploaded = {'hebrew': set(), 'english': set()}

    try:
        with open(UPLOAD_LOG_FILE, 'r') as f:
            for line in f:
                # Format: timestamp | Review_XXX | hebrew/english | success
                parts = line.strip().split('|')
                if len(parts) >= 4 and parts[3].strip() == 'success':
                    review_id = parts[1].strip()
                    channel_type = parts[2].strip()

                    match = re.search(r'Review_(\d+)', review_id)
                    if match and channel_type in uploaded:
                        uploaded[channel_type].add(int(match.group(1)))

        logger.debug(f"Loaded upload log: {len(uploaded['hebrew'])} Hebrew, "
                    f"{len(uploaded['english'])} English")
        return uploaded

    except Exception as e:
        logger.error(f"Error reading upload log: {e}")
        return {'hebrew': set(), 'english': set()}


def log_upload(review_num: int, channel_type: str, status: str):
    """Append upload record to local log file."""
    try:
        UPLOAD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(UPLOAD_LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | Review_{review_num:03d} | {channel_type} | {status}\n")
    except Exception as e:
        logger.error(f"Error writing to upload log: {e}")


def is_already_uploaded(review_num: int, channel_type: str,
                       uploaded_log: Dict[str, Set[int]],
                       bot_token: str, chat_id: str,
                       check_channel: bool = True) -> bool:
    """
    Check if review was already uploaded (dual method: log + channel history).

    Returns True if already uploaded, False otherwise.
    """
    # Method 1: Check local log (fast)
    if review_num in uploaded_log.get(channel_type, set()):
        logger.info(f"Review_{review_num} already in local log for {channel_type} channel")
        return True

    # Method 2: Check channel history (slower but thorough)
    if check_channel:
        channel_reviews = get_channel_history(bot_token, chat_id)
        if review_num in channel_reviews:
            logger.info(f"Review_{review_num} found in {channel_type} channel history")
            # Update local log for consistency
            log_upload(review_num, channel_type, 'success')
            return True

    return False


def upload_review(review_num: int, channel_type: str, config: TelegramConfig,
                 dry_run: bool = False) -> bool:
    """
    Upload a single review to Telegram channel.

    Returns True if successful, False otherwise.
    """
    # Determine file path and bot credentials
    if channel_type == 'hebrew':
        file_path = HEBREW_MD_DIR / f"Review_{review_num:03d}.md"
        bot_token = config.hebrew_bot_token
        chat_id = config.hebrew_channel_id
    elif channel_type == 'english':
        file_path = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"
        bot_token = config.english_bot_token
        chat_id = config.english_channel_id
    else:
        logger.error(f"Unknown channel type: {channel_type}")
        return False

    # Check if file exists
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False

    # Read markdown content
    content = read_markdown_file(file_path)
    if not content:
        logger.error(f"Failed to read {file_path}")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would upload Review_{review_num} to {channel_type} channel")
        logger.info(f"[DRY RUN]   Content length: {len(content)} characters")
        messages = split_message(content, config.max_message_length)
        logger.info(f"[DRY RUN]   Would split into {len(messages)} message(s)")
        return True

    # Split message if needed
    messages = split_message(content, config.max_message_length)

    # Upload each part
    success = True
    for i, message_text in enumerate(messages, 1):
        # Escape content for HTML mode
        escaped_message = escape_for_telegram_html(message_text)

        # Add part indicator if multiple parts
        if len(messages) > 1:
            part_indicator = f"({i}/{len(messages)})\n\n"
            final_text = part_indicator + escaped_message
        else:
            final_text = escaped_message

        logger.info(f"Uploading Review_{review_num} part {i}/{len(messages)} to {channel_type} channel...")

        if send_telegram_message(bot_token, chat_id, final_text,
                                config.retry_count, config.retry_delay_seconds):
            logger.info(f"✓ Sent part {i}/{len(messages)}")
        else:
            logger.error(f"✗ Failed to send part {i}/{len(messages)}")
            success = False
            break

        # Small delay between messages to avoid rate limiting
        if i < len(messages):
            time.sleep(1)

    if success:
        log_upload(review_num, channel_type, 'success')
        logger.info(f"✓ Successfully uploaded Review_{review_num} to {channel_type} channel")
    else:
        log_upload(review_num, channel_type, 'failed')
        logger.error(f"✗ Failed to upload Review_{review_num} to {channel_type} channel")

    return success


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
    """Main entry point for Telegram uploader."""

    # Parse arguments
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv

    # Get custom hours if specified
    hours = 24
    if '--hours' in sys.argv:
        try:
            idx = sys.argv.index('--hours')
            hours = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            logger.error("Invalid --hours argument, using default 24 hours")

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No messages will be sent")
        logger.info("=" * 60)

    logger.info("Starting Telegram review uploader")
    logger.info(f"Repository: {REPO_ROOT}")
    logger.info(f"Checking reviews from last {hours} hours")

    # Wait for network (important after wake from sleep)
    wait_for_network(timeout=60)

    # Load configuration
    try:
        config = TelegramConfig(CONFIG_FILE)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Get new reviews from git log
    new_reviews = get_new_reviews_from_git(hours)

    if not new_reviews['hebrew'] and not new_reviews['english']:
        logger.info("No new reviews found in git log. Exiting.")
        return 0

    # Load upload history
    uploaded_log = load_upload_log()

    # Process Hebrew reviews
    hebrew_uploaded = 0
    hebrew_skipped = 0
    hebrew_failed = 0

    for review_num in new_reviews['hebrew']:
        if is_already_uploaded(review_num, 'hebrew', uploaded_log,
                              config.hebrew_bot_token, config.hebrew_channel_id,
                              check_channel=not dry_run):
            logger.info(f"Skipping Review_{review_num} (Hebrew) - already uploaded")
            hebrew_skipped += 1
            continue

        if upload_review(review_num, 'hebrew', config, dry_run=dry_run):
            hebrew_uploaded += 1
        else:
            hebrew_failed += 1

    # Process English reviews
    english_uploaded = 0
    english_skipped = 0
    english_failed = 0

    for review_num in new_reviews['english']:
        if is_already_uploaded(review_num, 'english', uploaded_log,
                              config.english_bot_token, config.english_channel_id,
                              check_channel=not dry_run):
            logger.info(f"Skipping Review_{review_num} (English) - already uploaded")
            english_skipped += 1
            continue

        if upload_review(review_num, 'english', config, dry_run=dry_run):
            english_uploaded += 1
        else:
            english_failed += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Upload Summary")
    logger.info("=" * 60)
    logger.info(f"Hebrew Channel:")
    logger.info(f"  Uploaded: {hebrew_uploaded}")
    logger.info(f"  Skipped:  {hebrew_skipped}")
    logger.info(f"  Failed:   {hebrew_failed}")
    logger.info(f"English Channel:")
    logger.info(f"  Uploaded: {english_uploaded}")
    logger.info(f"  Skipped:  {english_skipped}")
    logger.info(f"  Failed:   {english_failed}")
    logger.info("=" * 60)

    # Return exit code
    if hebrew_failed > 0 or english_failed > 0:
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
