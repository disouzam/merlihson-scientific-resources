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
import random
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
MESSAGE_IDS_FILE = LOG_DIR / "telegram_message_ids.json"

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
        self.hebrew_username = config['hebrew_channel'].get('username')  # Public channel username

        self.english_bot_token = config['english_channel']['bot_token']
        self.english_channel_id = config['english_channel']['channel_id']
        self.english_username = config['english_channel'].get('username')  # Public channel username

        self.max_message_length = config.get('settings', {}).get('max_message_length', 4096)
        self.check_history_depth = config.get('settings', {}).get('check_history_depth', 100)
        self.retry_on_failure = config.get('settings', {}).get('retry_on_failure', True)
        self.retry_count = config.get('settings', {}).get('retry_count', 2)
        self.retry_delay_seconds = config.get('settings', {}).get('retry_delay_seconds', 5)
        self.machine_id = config.get('settings', {}).get('machine_id', 1)

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


def format_header_bold(escaped_text: str) -> str:
    """
    Format the review header block as bold for Telegram.

    The header includes everything up to and including the metadata line
    (the line containing the review number pattern like "סקירה NNN").
    Any body text after the metadata line (even in the same paragraph) stays normal.
    Also inserts a newline after 'Review NNN:' to separate it from the title.
    """
    # Split into paragraphs
    paragraphs = escaped_text.split('\n\n')

    # Find the metadata line (contains "סקירה" or "סקירת") to determine header end
    header_end = 0
    for i, para in enumerate(paragraphs):
        if re.search(r'סקיר[הת]', para):
            header_end = i
            break

    # The metadata paragraph might contain body text after the metadata line.
    # Split it: only the metadata line (and lines before it) go in the header.
    meta_para = paragraphs[header_end]
    meta_lines = meta_para.split('\n')

    meta_line_idx = 0
    for j, line in enumerate(meta_lines):
        if re.search(r'סקיר[הת]', line):
            meta_line_idx = j
            break

    header_meta_lines = meta_lines[:meta_line_idx + 1]
    body_from_meta = [l for l in meta_lines[meta_line_idx + 1:] if l.strip()]

    # Build header
    header_parts = paragraphs[:header_end] + ['\n'.join(header_meta_lines)]
    header = '\n\n'.join(header_parts)

    # Insert newline after "Review NNN:" pattern (keep title on next line)
    header = re.sub(r'^(Review \d+:)\s*', r'\1\n', header)

    # Wrap header in bold tags
    formatted = f"<b>{header}</b>"

    # Append any body text that was in the same paragraph as the metadata line
    body_parts = paragraphs[header_end + 1:]
    if body_from_meta:
        formatted += "\n\n" + '\n'.join(body_from_meta)
    if body_parts:
        formatted += "\n\n" + "\n\n".join(body_parts)

    return formatted


def send_telegram_message(bot_token: str, chat_id: str, text: str,
                         retry_count: int = 2, retry_delay: int = 5) -> Tuple[bool, Optional[int]]:
    """
    Send message to Telegram channel via Bot API.

    Returns (success: bool, message_id: Optional[int])
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
                message_id = result.get('result', {}).get('message_id')
                return True, message_id
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                if attempt < retry_count:
                    logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{retry_count})")
                    time.sleep(retry_delay)
                else:
                    return False, None

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {e}")
            if attempt < retry_count:
                logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{retry_count})")
                time.sleep(retry_delay)
            else:
                return False, None

    return False, None


def get_channel_history(bot_token: str, chat_id: str, limit: int = 100) -> Set[int]:
    """
    Get recent review numbers from Telegram channel via Bot API getUpdates.

    This is a best-effort fallback check. The git-tracked ledger (checked
    separately in is_already_uploaded Method 2) is the authoritative
    cross-machine duplicate check. This function only queries the Telegram
    API for channel_post updates to catch uploads not yet in the ledger.
    """
    review_numbers = set()

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {"allowed_updates": '["channel_post"]', "limit": limit}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get('ok'):
            for update in result.get('result', []):
                if 'channel_post' in update:
                    text = update['channel_post'].get('text', '')
                    matches = re.findall(r'Review[_\s](\d+)', text, re.IGNORECASE)
                    for match in matches:
                        review_numbers.add(int(match))
    except Exception as e:
        logger.debug(f"getUpdates check failed (non-critical): {e}")

    logger.debug(f"Found {len(review_numbers)} reviews from channel updates")
    return review_numbers


# --- Git-tracked upload ledger (cross-machine duplicate prevention) ---

UPLOAD_LEDGER_FILE = REPO_ROOT / ".repo-tools" / "logs" / "telegram_upload_ledger.json"


def load_upload_ledger() -> Dict[str, Set[int]]:
    """
    Load the git-tracked upload ledger (shared across all machines).

    Unlike the local log (gitignored), this file is committed and pushed
    immediately after each upload, ensuring cross-machine consistency.
    """
    if not UPLOAD_LEDGER_FILE.exists():
        return {'hebrew': set(), 'english': set()}

    try:
        with open(UPLOAD_LEDGER_FILE, 'r') as f:
            data = json.load(f)
        return {
            'hebrew': set(data.get('hebrew', [])),
            'english': set(data.get('english', []))
        }
    except Exception as e:
        logger.error(f"Error reading upload ledger: {e}")
        return {'hebrew': set(), 'english': set()}


def check_remote_ledger(review_num: int, channel_type: str) -> bool:
    """
    Check the REMOTE ledger via git fetch + git show (defense in depth).

    This catches cases where the other machine uploaded and pushed the ledger
    but our local repo hasn't pulled yet, or where git pull failed/returned
    'up to date' incorrectly.
    """
    try:
        rel_path = UPLOAD_LEDGER_FILE.relative_to(REPO_ROOT)
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
            remote_reviews = set(remote_data.get(channel_type, []))
            if review_num in remote_reviews:
                logger.info(f"Review_{review_num} found in REMOTE ledger for {channel_type} (git fetch check)")
                return True
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as e:
        logger.warning(f"Remote ledger check failed ({e}), proceeding with local state.")
    return False


def update_upload_ledger(review_num: int, channel_type: str):
    """
    Add a review to the git-tracked ledger and immediately commit + push.

    This is the critical cross-machine lock — must happen right after a
    successful upload and before anything else.
    """
    try:
        # Load current ledger
        if UPLOAD_LEDGER_FILE.exists():
            with open(UPLOAD_LEDGER_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {'hebrew': [], 'english': []}

        # Add the review number (keep sorted, no duplicates)
        reviews = set(data.get(channel_type, []))
        reviews.add(review_num)
        data[channel_type] = sorted(reviews)

        # Write ledger
        UPLOAD_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(UPLOAD_LEDGER_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        # Immediately commit and push (this is the cross-machine lock)
        logger.info(f"Committing upload ledger for Review_{review_num} ({channel_type})...")
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'add', str(UPLOAD_LEDGER_FILE)],
            capture_output=True, timeout=10
        )
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'commit', '-m',
             f'telegram: mark Review_{review_num} ({channel_type}) as uploaded',
             '--no-verify'],
            capture_output=True, timeout=15
        )
        # Pull first to avoid rejection
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
            capture_output=True, timeout=30
        )
        # Retry push up to 3 times (critical: prevents duplicate posts across machines)
        for attempt in range(1, 4):
            push_result = subprocess.run(
                ['git', '-C', str(REPO_ROOT), 'push'],
                capture_output=True, text=True, timeout=30
            )
            if push_result.returncode == 0:
                logger.info(f"✓ Ledger pushed (Review_{review_num} {channel_type} locked)")
                break
            else:
                logger.warning(f"Ledger push attempt {attempt}/3 failed: {push_result.stderr.strip()}")
                if attempt < 3:
                    time.sleep(attempt * 5)
                    subprocess.run(
                        ['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                        capture_output=True, timeout=30
                    )
                else:
                    logger.error(f"CRITICAL: Ledger push failed after 3 attempts for Review_{review_num} ({channel_type}). "
                                 f"Duplicate post possible if another machine runs before manual push.")

    except Exception as e:
        logger.error(f"Error updating upload ledger: {e}")


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


def save_message_id(review_num: int, channel_type: str, message_id: int,
                   chat_id: str, username: Optional[str] = None):
    """
    Save message_id to JSON file for later retrieval (used by discord_poster).

    This enables other scripts to construct Telegram message links.
    """
    try:
        MESSAGE_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data
        if MESSAGE_IDS_FILE.exists():
            with open(MESSAGE_IDS_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {}

        # Add new entry
        review_key = str(review_num)
        if review_key not in data:
            data[review_key] = {}

        # Construct Telegram link
        if username:
            # Public channel format: https://t.me/username/message_id
            link = f"https://t.me/{username}/{message_id}"
        else:
            # Private channel format: https://t.me/c/chat_id/message_id
            clean_chat_id = chat_id.replace("-100", "")
            link = f"https://t.me/c/{clean_chat_id}/{message_id}"

        data[review_key][channel_type] = {
            'message_id': message_id,
            'chat_id': chat_id,
            'username': username,
            'link': link,
            'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }

        # Save back to file
        with open(MESSAGE_IDS_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved message_id for Review_{review_num} ({channel_type}): {message_id}")

        # Commit + push so other machines can see the Telegram links (needed by discord_poster)
        try:
            subprocess.run(['git', '-C', str(REPO_ROOT), 'add', str(MESSAGE_IDS_FILE)],
                           capture_output=True, timeout=10)
            subprocess.run(['git', '-C', str(REPO_ROOT), 'commit', '-m',
                            f'telegram: save message_id for Review_{review_num} ({channel_type})', '--no-verify'],
                           capture_output=True, timeout=15)
            subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                           capture_output=True, timeout=30)
            # Retry push up to 3 times
            for attempt in range(1, 4):
                push_result = subprocess.run(['git', '-C', str(REPO_ROOT), 'push'],
                                             capture_output=True, text=True, timeout=30)
                if push_result.returncode == 0:
                    logger.info(f"✓ Message IDs pushed (Review_{review_num} {channel_type})")
                    break
                else:
                    logger.warning(f"Message IDs push attempt {attempt}/3 failed: {push_result.stderr.strip()}")
                    if attempt < 3:
                        time.sleep(attempt * 5)
                        subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                                       capture_output=True, timeout=30)
        except Exception as push_err:
            logger.warning(f"Could not push message IDs: {push_err}")

    except Exception as e:
        logger.error(f"Error saving message_id: {e}")


def is_already_uploaded(review_num: int, channel_type: str,
                       uploaded_log: Dict[str, Set[int]],
                       bot_token: str, chat_id: str,
                       check_channel: bool = True) -> bool:
    """
    Check if review was already uploaded (triple method: local log + git ledger + channel updates).

    Returns True if already uploaded, False otherwise.
    """
    # Method 1: Check local log (fast, machine-local)
    if review_num in uploaded_log.get(channel_type, set()):
        logger.info(f"Review_{review_num} already in local log for {channel_type} channel")
        return True

    # Method 2: Check git-tracked ledger (cross-machine, authoritative)
    ledger = load_upload_ledger()
    if review_num in ledger.get(channel_type, set()):
        logger.info(f"Review_{review_num} found in git ledger for {channel_type} channel")
        # Sync local log for consistency
        log_upload(review_num, channel_type, 'success')
        return True

    # Method 3: Check channel updates (best-effort Telegram API check)
    if check_channel:
        channel_reviews = get_channel_history(bot_token, chat_id)
        if review_num in channel_reviews:
            logger.info(f"Review_{review_num} found in {channel_type} channel history")
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
        username = config.hebrew_username
    elif channel_type == 'english':
        file_path = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"
        bot_token = config.english_bot_token
        chat_id = config.english_channel_id
        username = config.english_username
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
        escaped_content = escape_for_telegram_html(content)
        messages = split_message(escaped_content, config.max_message_length - 24)
        logger.info(f"[DRY RUN]   Would split into {len(messages)} message(s)")
        return True

    # Last-second cross-machine check: pull + remote fetch before sending
    logger.info(f"Final ledger check before uploading Review_{review_num} ({channel_type})...")
    subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
        capture_output=True, timeout=30
    )
    ledger = load_upload_ledger()
    if review_num in ledger.get(channel_type, set()):
        logger.info(f"Review_{review_num} appeared in ledger during processing — skipping (other machine uploaded it)")
        log_upload(review_num, channel_type, 'success')
        return True

    # Defense in depth: also check remote ledger directly via git fetch + git show
    # (catches cases where other machine pushed but our pull missed it)
    if check_remote_ledger(review_num, channel_type):
        logger.info(f"Review_{review_num} found in remote ledger — skipping (other machine uploaded it)")
        log_upload(review_num, channel_type, 'success')
        return True

    # Escape content for HTML mode first, then split on escaped text.
    # This ensures message lengths account for HTML entity expansion
    # (e.g., quotes → &quot;) and bold tag overhead.
    escaped_content = escape_for_telegram_html(content)

    # Reserve space for bold tags (<b></b> x2 = 14 chars) and part indicator (~10 chars)
    messages = split_message(escaped_content, config.max_message_length - 24)

    # Upload each part
    success = True
    first_message_id = None  # Track first message ID for link construction

    for i, escaped_message in enumerate(messages, 1):
        # Format header block as bold (first message part only)
        if i == 1:
            escaped_message = format_header_bold(escaped_message)

        # Add part indicator if multiple parts
        if len(messages) > 1:
            part_indicator = f"({i}/{len(messages)})\n\n"
            final_text = part_indicator + escaped_message
        else:
            final_text = escaped_message

        logger.info(f"Uploading Review_{review_num} part {i}/{len(messages)} to {channel_type} channel...")

        send_success, message_id = send_telegram_message(bot_token, chat_id, final_text,
                                                         config.retry_count, config.retry_delay_seconds)

        if send_success:
            logger.info(f"✓ Sent part {i}/{len(messages)}")

            # Store first message_id (this is the main link we'll use)
            if i == 1 and message_id:
                first_message_id = message_id
                save_message_id(review_num, channel_type, message_id, chat_id, username)
        else:
            logger.error(f"✗ Failed to send part {i}/{len(messages)}")
            success = False
            break

        # Small delay between messages to avoid rate limiting
        if i < len(messages):
            time.sleep(1)

    if success:
        log_upload(review_num, channel_type, 'success')
        # Immediately update and push the git-tracked ledger (cross-machine lock)
        update_upload_ledger(review_num, channel_type)
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

    # Load configuration (needed early for machine_id)
    try:
        config = TelegramConfig(CONFIG_FILE)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Wait for network (important after wake from sleep)
    wait_for_network(timeout=60)

    # Deterministic startup delay to prevent race condition when multiple machines
    # have identical launchd schedules. Each machine gets a non-overlapping slot
    # based on its machine_id (set in telegram_config.yaml):
    #   machine_id 1 → 0-20s,  machine_id 2 → 120-140s,  machine_id 3 → 240-260s
    # This guarantees at least 100 seconds between any two machines.
    if not dry_run:
        machine_id = config.machine_id
        slot_start = (machine_id - 1) * 120
        delay = random.randint(slot_start, slot_start + 20)
        logger.info(f"Startup delay: {delay}s (machine_id={machine_id}, slot {slot_start}-{slot_start+20}s)")
        time.sleep(delay)

    # Discard local changes to auto-generated files before pulling.
    # These files are regenerated by the pre-commit hook, so local diffs
    # are stale and cause recurring stash-pop merge conflicts (#4 occurrence).
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

    # Pull latest from remote (critical: gets the upload ledger from the other machine)
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
