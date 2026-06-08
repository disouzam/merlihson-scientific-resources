#!/usr/bin/env python3
"""
Discord Review Poster

Posts paper review links to Discord community channel via bot.
Creates a new thread for each review and posts the content inside.

How it works:
1. Load Telegram message links from telegram_message_ids.json
2. For each new review (not yet posted to Discord):
   a. Get Substack link via substack_scraper.py
   b. Get review title from markdown file
   c. Create thread "Daily Paper Review: {date}"
   d. Format Discord message with all 5 links
   e. Post to thread via Discord Bot API
   f. Log success to discord_posts.log

Run manually:
  python3 discord_poster.py --dry-run          # Show what would be posted
  python3 discord_poster.py --test-bot-token   # Test bot token only
  python3 discord_poster.py --test-create-thread  # Test thread creation
  python3 discord_poster.py --review 574       # Post specific review
  python3 discord_poster.py                    # Post all new reviews

Scheduled: Runs at 12:00 PM and 6:00 PM (primary + backup)
"""

import sys
import json
import re
import logging
import subprocess
import time
import random
from pathlib import Path
from typing import Optional, Dict, List, Set
from datetime import datetime
import requests
import yaml

# Script configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
CONFIG_DIR = REPO_ROOT / ".repo-tools" / "config"
SCRIPTS_DIR = REPO_ROOT / ".repo-tools" / "scripts"

CONFIG_FILE = CONFIG_DIR / "discord_config.yaml"
MESSAGE_IDS_FILE = LOG_DIR / "telegram_message_ids.json"
DISCORD_LOG_FILE = LOG_DIR / "discord_posts.log"

HEBREW_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-hebrew-reviews-md"
ENGLISH_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-english-reviews-md"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "discord_poster.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class DiscordConfig:
    """Configuration holder for Discord and Substack settings."""

    def __init__(self, config_path: Path):
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create it from the template."
            )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        discord_config = config.get('discord', {})

        # Bot configuration (primary method)
        self.bot_token = discord_config.get('bot_token')
        self.channel_id = discord_config.get('channel_id')
        self.thread_name_format = discord_config.get('thread_name_format', 'Daily Paper Review: {date}')

        # Webhook URL (deprecated, kept for backward compatibility)
        self.webhook_url = discord_config.get('webhook_url')

        self.substack_url = config.get('substack', {}).get('base_url')

        # GitHub repo URLs
        github_config = config.get('github', {})
        self.github_repo_url = github_config.get('repo_url', 'https://github.com/merlihson/scientific-resources')
        self.hebrew_path = github_config.get('hebrew_path', 'mike-paper-reviews-all/split-hebrew-reviews-md')
        self.english_path = github_config.get('english_path', 'mike-paper-reviews-all/split-english-reviews-md')

        # Validate bot configuration
        if not self.bot_token or 'YOUR_' in self.bot_token:
            raise ValueError("Please configure 'discord.bot_token' in discord_config.yaml")

        if not self.channel_id or 'YOUR_' in self.channel_id:
            raise ValueError("Please configure 'discord.channel_id' in discord_config.yaml")

        if not self.substack_url or 'YOUR_' in self.substack_url:
            raise ValueError("Please configure 'substack.base_url' in discord_config.yaml")

        # Additional channels to cross-post to
        self.additional_channels = discord_config.get('additional_channels', [])

        # Optional settings
        settings = config.get('settings', {})
        self.retry_on_failure = settings.get('retry_on_failure', True)
        self.retry_count = settings.get('retry_count', 2)
        self.retry_delay_seconds = settings.get('retry_delay_seconds', 30)
        self.machine_id = settings.get('machine_id', 1)


def load_telegram_links() -> Dict:
    """Load Telegram message links from JSON file."""
    if not MESSAGE_IDS_FILE.exists():
        logger.warning(f"Telegram message links file not found: {MESSAGE_IDS_FILE}")
        return {}

    try:
        with open(MESSAGE_IDS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading Telegram links: {e}")
        return {}


def load_posted_reviews() -> set:
    """
    Load reviews that have already been posted to Discord.

    Returns set of review numbers.
    """
    if not DISCORD_LOG_FILE.exists():
        return set()

    posted = set()
    try:
        with open(DISCORD_LOG_FILE, 'r') as f:
            for line in f:
                # Format: timestamp | Review_XXX | success/failed
                parts = line.strip().split('|')
                if len(parts) >= 3 and parts[2].strip() == 'success':
                    review_id = parts[1].strip()
                    match = re.search(r'Review_(\d+)', review_id)
                    if match:
                        posted.add(int(match.group(1)))

        logger.debug(f"Loaded {len(posted)} previously posted reviews")
        return posted

    except Exception as e:
        logger.error(f"Error reading Discord log: {e}")
        return set()


def get_discord_channel_threads(channel_id: str, bot_token: str) -> set:
    """
    Check Discord channel for existing threads to find already-posted reviews.
    This prevents duplicate posts when running from multiple machines.

    Returns set of review numbers already posted.
    """
    posted = set()
    try:
        # Get active threads
        url = f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public"
        headers = {"Authorization": f"Bot {bot_token}"}

        # Also check active threads
        active_url = f"https://discord.com/api/v10/guilds"
        # Use channel messages to find threads with Review_ in name
        threads_url = f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public?limit=100"
        response = requests.get(threads_url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            for thread in data.get('threads', []):
                thread_name = thread.get('name', '')
                # Check first message in thread for Review_NNN pattern
                thread_id = thread.get('id')
                if thread_id:
                    msg_url = f"https://discord.com/api/v10/channels/{thread_id}/messages?limit=1"
                    msg_resp = requests.get(msg_url, headers=headers, timeout=15)
                    if msg_resp.status_code == 200:
                        messages = msg_resp.json()
                        for msg in messages:
                            content = msg.get('content', '')
                            match = re.search(r'Review\s+(\d+)', content)
                            if match:
                                posted.add(int(match.group(1)))

        # Also get active (non-archived) threads via guild endpoint
        # First get guild_id from channel
        ch_url = f"https://discord.com/api/v10/channels/{channel_id}"
        ch_resp = requests.get(ch_url, headers=headers, timeout=15)
        if ch_resp.status_code == 200:
            guild_id = ch_resp.json().get('guild_id')
            if guild_id:
                active_url = f"https://discord.com/api/v10/guilds/{guild_id}/threads/active"
                active_resp = requests.get(active_url, headers=headers, timeout=15)
                if active_resp.status_code == 200:
                    for thread in active_resp.json().get('threads', []):
                        thread_id = thread.get('id')
                        parent_id = thread.get('parent_id')
                        if parent_id == channel_id and thread_id:
                            msg_url = f"https://discord.com/api/v10/channels/{thread_id}/messages?limit=1"
                            msg_resp = requests.get(msg_url, headers=headers, timeout=15)
                            if msg_resp.status_code == 200:
                                for msg in msg_resp.json():
                                    match = re.search(r'Review\s+(\d+)', msg.get('content', ''))
                                    if match:
                                        posted.add(int(match.group(1)))

        if posted:
            logger.info(f"Found {len(posted)} reviews already posted in Discord channel")

    except Exception as e:
        logger.warning(f"Could not check Discord channel history: {e}")
        # Don't block posting if check fails — fall back to local log only

    return posted


def log_discord_post(review_num: int, status: str):
    """Append Discord post record to log file."""
    try:
        DISCORD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DISCORD_LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | Review_{review_num:03d} | {status}\n")
    except Exception as e:
        logger.error(f"Error writing to Discord log: {e}")


# --- Git-tracked upload ledger (cross-machine duplicate prevention) ---

DISCORD_LEDGER_FILE = REPO_ROOT / ".repo-tools" / "logs" / "discord_upload_ledger.json"


def load_discord_ledger() -> Set[int]:
    """Load the git-tracked Discord upload ledger (shared across all machines)."""
    if not DISCORD_LEDGER_FILE.exists():
        return set()
    try:
        with open(DISCORD_LEDGER_FILE, 'r') as f:
            data = json.load(f)
        return set(data.get('posted', []))
    except Exception as e:
        logger.error(f"Error reading Discord ledger: {e}")
        return set()


def update_discord_ledger(review_num: int):
    """Add review to git-tracked ledger and immediately commit + push."""
    try:
        if DISCORD_LEDGER_FILE.exists():
            with open(DISCORD_LEDGER_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {'posted': []}

        reviews = set(data.get('posted', []))
        reviews.add(review_num)
        data['posted'] = sorted(reviews)

        DISCORD_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DISCORD_LEDGER_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Committing Discord ledger for Review_{review_num}...")
        subprocess.run(['git', '-C', str(REPO_ROOT), 'add', str(DISCORD_LEDGER_FILE)],
                       capture_output=True, timeout=10)
        subprocess.run(['git', '-C', str(REPO_ROOT), 'commit', '-m',
                        f'discord: mark Review_{review_num} as posted', '--no-verify'],
                       capture_output=True, timeout=15)
        subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                       capture_output=True, timeout=30)
        # Retry push up to 3 times (critical: prevents duplicate posts across machines)
        for attempt in range(1, 4):
            push_result = subprocess.run(['git', '-C', str(REPO_ROOT), 'push'],
                                         capture_output=True, text=True, timeout=30)
            if push_result.returncode == 0:
                logger.info(f"✓ Discord ledger pushed (Review_{review_num} locked)")
                break
            else:
                logger.warning(f"Discord ledger push attempt {attempt}/3 failed: {push_result.stderr.strip()}")
                if attempt < 3:
                    time.sleep(attempt * 5)
                    subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                                   capture_output=True, timeout=30)
                else:
                    logger.error(f"CRITICAL: Discord ledger push failed after 3 attempts for Review_{review_num}. "
                                 f"Duplicate post possible if another machine runs before manual push.")
    except Exception as e:
        logger.error(f"Error updating Discord ledger: {e}")


def get_review_title(review_num: int) -> str:
    """
    Extract review title from markdown file.

    Tries Hebrew first, then English.
    Returns "Paper Title" or a default if not found.
    """
    # Try Hebrew first
    hebrew_file = HEBREW_MD_DIR / f"Review_{review_num:03d}.md"
    english_file = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"

    for file_path in [english_file, hebrew_file]:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract title (typically first line after "Review XXX:")
                # Format: "Review 574: Title Here" or just "Title Here"
                lines = content.strip().split('\n')
                for line in lines[:5]:  # Check first 5 lines
                    # Remove markdown formatting
                    line = line.strip().replace('#', '').strip()

                    # Try to extract title after "Review XXX:"
                    match = re.search(r'Review\s*\d+\s*:\s*(.+)', line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()

                    # If line is substantial, use it as title
                    if len(line) > 10 and not line.startswith('('):
                        return line

            except Exception as e:
                logger.debug(f"Error reading {file_path}: {e}")
                continue

    # Default fallback
    return f"Paper Review {review_num}"


def get_substack_link(config: DiscordConfig, review_num: int) -> Optional[str]:
    """
    Get Substack link for a review by calling substack_scraper.py.

    Args:
        config: Discord configuration (includes Substack URL)
        review_num: Review number to find

    Returns:
        Substack URL or None if not found
    """
    try:
        # Import and call the substack scraper
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))

        from substack_scraper import get_latest_review_post

        logger.info(f"Fetching Substack link for Review_{review_num}...")
        url = get_latest_review_post(config.substack_url, review_num)

        if url:
            logger.info(f"✓ Found Substack link: {url}")
        else:
            logger.warning(f"Substack link not found for Review_{review_num}")

        return url

    except Exception as e:
        logger.error(f"Error getting Substack link: {e}")
        return None


def format_discord_message(review_num: int, title: str,
                          hebrew_link: Optional[str],
                          english_link: Optional[str],
                          substack_link: Optional[str],
                          hebrew_github_link: Optional[str] = None,
                          english_github_link: Optional[str] = None) -> str:
    """
    Format the Discord message with all links.

    Format:
      📢 New paper review published:
      📄 Review 574: Paper Title

      🇮🇱 Hebrew: https://t.me/c/.../12345
      🇬🇧 English: https://t.me/c/.../12346
      📝 Substack: https://yoursubstack.com/p/review-574
      📖 Review Files:
      🇮🇱 Hebrew (GitHub): [link]
      🇬🇧 English (GitHub): [link]
    """
    lines = [
        "📢 **New paper review published:**",
        "",
        f"📄 **Review {review_num}: {title}**",
        ""
    ]

    # Telegram links
    lines.append(f"✈️ **Telegram:**")
    lines.append(f"🇮🇱 **Hebrew:** {hebrew_link}")
    lines.append(f"🇬🇧 **English:** {english_link}")
    lines.append("")
    lines.append(f"📝 **Substack:** {substack_link}")

    # GitHub repo links
    if hebrew_github_link or english_github_link:
        lines.append("")
        lines.append("📖 **Review Files (GitHub):**")
        if hebrew_github_link:
            lines.append(f"🇮🇱 **Hebrew:** {hebrew_github_link}")
        if english_github_link:
            lines.append(f"🇬🇧 **English:** {english_github_link}")

    return "\n".join(lines)


def post_to_discord(webhook_url: str, message: str) -> bool:
    """
    Post message to Discord via webhook (deprecated, kept for backward compatibility).

    Args:
        webhook_url: Discord webhook URL
        message: Message content

    Returns:
        True if successful, False otherwise
    """
    try:
        payload = {"content": message}

        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()

        logger.info("✓ Message posted to Discord")
        return True

    except Exception as e:
        logger.error(f"Error posting to Discord: {e}")
        return False


def create_thread(channel_id: str, thread_name: str, bot_token: str) -> Optional[str]:
    """
    Create a new public thread in a Discord channel via Bot API.

    Args:
        channel_id: Discord channel ID where thread will be created
        thread_name: Name of the thread to create
        bot_token: Discord bot token

    Returns:
        Thread ID if successful, None otherwise
    """
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/threads"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": thread_name,
            "type": 11,  # Public thread
            "auto_archive_duration": 1440  # Archive after 24 hours of inactivity
        }

        logger.info(f"Creating thread: {thread_name}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        thread_data = response.json()
        thread_id = thread_data.get('id')

        if thread_id:
            logger.info(f"✓ Thread created: ID {thread_id}")
            return thread_id
        else:
            logger.error("Thread creation response missing 'id' field")
            return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error creating thread: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        return None


def post_to_thread(thread_id: str, message: str, bot_token: str) -> bool:
    """
    Post message to a Discord thread via Bot API.

    Args:
        thread_id: Discord thread ID
        message: Message content
        bot_token: Discord bot token

    Returns:
        True if successful, False otherwise
    """
    try:
        url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }
        payload = {"content": message}

        logger.info(f"Posting message to thread {thread_id}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        logger.info("✓ Message posted to thread")
        return True

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error posting to thread: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error posting to thread: {e}")
        return False


def get_thread_name(name_format: str) -> str:
    """
    Generate thread name from format string.

    Args:
        name_format: Format string with {date} placeholder

    Returns:
        Formatted thread name with current date
    """
    date_str = datetime.now().strftime("%b %d, %Y")
    return name_format.replace("{date}", date_str)


def get_new_reviews_for_discord(telegram_links: Dict, already_posted: set) -> List[int]:
    """
    Find reviews that have both Hebrew and English Telegram links and haven't
    been posted to Discord yet. Returns reviews newer than the latest one
    already on Discord, so a transient failure (e.g. Substack down) can recover
    on a later run instead of silently aging out.

    Args:
        telegram_links: Dict from telegram_message_ids.json
        already_posted: Set of already posted review numbers

    Returns:
        List of review numbers to post (most recent first)
    """
    new_reviews = []
    max_posted = max(already_posted) if already_posted else 0

    for review_key, links in telegram_links.items():
        # Skip non-numeric keys (like "test")
        if not review_key.isdigit():
            continue

        review_num = int(review_key)

        if review_num in already_posted:
            logger.debug(f"Review_{review_num} already posted to Discord")
            continue

        # Only consider reviews newer than the latest one already on Discord —
        # avoids mass-backfill if the ledger is empty or freshly checked out.
        if review_num <= max_posted:
            logger.debug(f"Review_{review_num} older than latest posted ({max_posted}), skipping")
            continue

        has_hebrew = 'hebrew' in links and links['hebrew'].get('link')
        has_english = 'english' in links and links['english'].get('link')

        if not (has_hebrew and has_english):
            logger.debug(f"Review_{review_num} missing Telegram links (Hebrew: {has_hebrew}, English: {has_english})")
            continue

        new_reviews.append(review_num)

    return sorted(new_reviews, reverse=True)


def post_review_to_discord(review_num: int, config: DiscordConfig,
                          telegram_links: Dict, dry_run: bool = False) -> bool:
    """
    Post a single review to Discord thread.

    VALIDATION: Only posts if ALL 3 links are present:
    - Hebrew Telegram link
    - English Telegram link
    - Substack link

    Process:
    1. Validate all links exist
    2. Create thread "Daily Paper Review: {date}"
    3. Post message inside thread with all 5 links

    Args:
        review_num: Review number
        config: Discord configuration
        telegram_links: Dict with Telegram links
        dry_run: If True, only format message without posting

    Returns:
        True if successful
    """
    review_key = str(review_num)

    # Get Telegram links
    hebrew_link = telegram_links.get(review_key, {}).get('hebrew', {}).get('link')
    english_link = telegram_links.get(review_key, {}).get('english', {}).get('link')

    # VALIDATION: Ensure both Telegram links exist
    if not hebrew_link or not english_link:
        logger.error(f"Review_{review_num} missing Telegram links. Skipping.")
        logger.error(f"  Hebrew: {'✓' if hebrew_link else '✗'}")
        logger.error(f"  English: {'✓' if english_link else '✗'}")
        return False

    # Get Substack link
    substack_link = get_substack_link(config, review_num)

    # VALIDATION: Ensure Substack link exists
    if not substack_link:
        logger.warning(f"Review_{review_num} Substack link not found. Skipping this posting cycle.")
        logger.warning(f"  Will retry in next run (6:00 PM) if Substack is published by then.")
        return False

    logger.info(f"✓ All 3 links validated for Review_{review_num}")
    logger.info(f"  Hebrew Telegram: {hebrew_link[:50]}...")
    logger.info(f"  English Telegram: {english_link[:50]}...")
    logger.info(f"  Substack: {substack_link[:50]}...")

    # Get review title
    title = get_review_title(review_num)

    # Construct GitHub links
    hebrew_github_link = f"{config.github_repo_url}/blob/main/{config.hebrew_path}/Review_{review_num:03d}.md"
    english_github_link = f"{config.github_repo_url}/blob/main/{config.english_path}/Review_{review_num:03d}.md"

    # Format message
    message = format_discord_message(review_num, title, hebrew_link, english_link, substack_link,
                                     hebrew_github_link, english_github_link)

    # Generate thread name
    thread_name = get_thread_name(config.thread_name_format)

    if dry_run:
        logger.info(f"[DRY RUN] Would create thread and post to Discord:")
        logger.info(f"  Thread name: {thread_name}")
        logger.info(f"  Primary channel: {config.channel_id}")
        for extra_ch in config.additional_channels:
            logger.info(f"  + Additional channel: #{extra_ch.get('name', extra_ch.get('id'))} ({extra_ch.get('id')})")
        logger.info("")
        logger.info(message)
        logger.info("")
        return True

    # Last-second cross-machine check: pull and re-check ledger right before posting
    logger.info(f"Final ledger check before posting Review_{review_num}...")
    subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', '--rebase', '--autostash'],
                   capture_output=True, timeout=30)
    if review_num in load_discord_ledger():
        logger.info(f"Review_{review_num} appeared in ledger — skipping (other machine posted it)")
        log_discord_post(review_num, 'success')
        return True

    # Create thread
    logger.info(f"Creating thread in channel {config.channel_id}...")
    thread_id = create_thread(config.channel_id, thread_name, config.bot_token)

    if not thread_id:
        logger.error(f"Failed to create thread for Review_{review_num}")
        log_discord_post(review_num, 'failed - thread creation error')
        return False

    # Post to thread
    logger.info(f"Posting Review_{review_num} to thread {thread_id}...")
    success = post_to_thread(thread_id, message, config.bot_token)

    if success:
        log_discord_post(review_num, 'success')
        update_discord_ledger(review_num)
        logger.info(f"✓ Successfully posted Review_{review_num} to Discord thread")

        # Cross-post to additional channels
        for extra_ch in config.additional_channels:
            extra_id = extra_ch.get('id')
            extra_name = extra_ch.get('name', extra_id)
            if not extra_id:
                continue
            try:
                logger.info(f"Cross-posting Review_{review_num} to #{extra_name} ({extra_id})...")
                extra_thread_id = create_thread(extra_id, thread_name, config.bot_token)
                if extra_thread_id:
                    if post_to_thread(extra_thread_id, message, config.bot_token):
                        logger.info(f"✓ Cross-posted Review_{review_num} to #{extra_name}")
                    else:
                        logger.warning(f"Failed to post message in #{extra_name} thread")
                else:
                    logger.warning(f"Failed to create thread in #{extra_name}")
            except Exception as e:
                logger.warning(f"Error cross-posting to #{extra_name}: {e}")
    else:
        log_discord_post(review_num, 'failed - posting error')
        logger.error(f"✗ Failed to post Review_{review_num} to Discord thread")

    return success


def test_webhook(config: DiscordConfig) -> bool:
    """Test Discord webhook with a simple message (deprecated)."""
    logger.info("Testing Discord webhook...")

    test_message = f"🧪 Test message from Discord poster\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return post_to_discord(config.webhook_url, test_message)


def test_bot_token(config: DiscordConfig) -> bool:
    """Test Discord bot token by fetching bot user info."""
    logger.info("Testing Discord bot token...")

    try:
        url = "https://discord.com/api/v10/users/@me"
        headers = {
            "Authorization": f"Bot {config.bot_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        bot_data = response.json()
        bot_username = bot_data.get('username', 'Unknown')
        bot_id = bot_data.get('id', 'Unknown')

        logger.info(f"✓ Bot token valid!")
        logger.info(f"  Bot username: {bot_username}")
        logger.info(f"  Bot ID: {bot_id}")
        return True

    except Exception as e:
        logger.error(f"✗ Bot token test failed: {e}")
        return False


def test_create_thread(config: DiscordConfig) -> bool:
    """Test thread creation only (creates a test thread)."""
    logger.info("Testing thread creation...")

    test_thread_name = f"Test Thread - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    thread_id = create_thread(config.channel_id, test_thread_name, config.bot_token)

    if thread_id:
        logger.info(f"✓ Test thread created successfully: {test_thread_name}")
        logger.info(f"  Thread ID: {thread_id}")
        return True
    else:
        logger.error("✗ Failed to create test thread")
        return False


def main():
    """Main entry point for Discord poster."""

    # Parse arguments
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv
    test_webhook_only = '--test-webhook' in sys.argv
    test_bot_token_only = '--test-bot-token' in sys.argv
    test_create_thread_only = '--test-create-thread' in sys.argv
    specific_review = None
    format_only = '--format-only' in sys.argv

    if '--review' in sys.argv:
        try:
            idx = sys.argv.index('--review')
            specific_review = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            logger.error("Invalid --review argument")
            return 1

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No messages will be posted")
        logger.info("=" * 60)

    logger.info("Starting Discord review poster")
    logger.info(f"Repository: {REPO_ROOT}")

    # Load configuration
    try:
        config = DiscordConfig(CONFIG_FILE)
        logger.info("✓ Configuration loaded")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Test commands
    if test_bot_token_only:
        return 0 if test_bot_token(config) else 1

    if test_create_thread_only:
        return 0 if test_create_thread(config) else 1

    if test_webhook_only:
        return 0 if test_webhook(config) else 1

    # Deterministic startup delay based on machine_id (cross-machine race prevention)
    if not dry_run and not specific_review:
        machine_id = config.machine_id
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
    # First abort any in-progress rebase/merge that left conflict markers
    subprocess.run(['git', '-C', str(REPO_ROOT), 'rebase', '--abort'],
                   capture_output=True, text=True, timeout=10)
    subprocess.run(['git', '-C', str(REPO_ROOT), 'merge', '--abort'],
                   capture_output=True, text=True, timeout=10)
    # Then reset auto-generated files to HEAD
    for f in AUTO_GENERATED_FILES:
        subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'checkout', 'HEAD', '--', f],
            capture_output=True, text=True, timeout=10
        )

    # Pull latest from remote (critical: gets ledger from other machines).
    # Uses _git_utils.robust_git_pull to retry after laptop-wake SSH transients.
    from _git_utils import robust_git_pull
    logger.info("Pulling latest from remote (for cross-machine ledger sync)...")
    ok, err = robust_git_pull(REPO_ROOT, logger=logger)
    if not ok:
        logger.error(f"Git pull FAILED after retries: {err}")
        logger.error("Cannot proceed without a clean pull — risk of duplicate posts. Aborting.")
        return 1
    logger.info("✓ Repo up to date")

    # Load Telegram links
    telegram_links = load_telegram_links()
    if not telegram_links:
        logger.warning("No Telegram links found. Run telegram_uploader.py first.")
        return 1

    # Load already posted reviews (local log + git ledger + Discord channel history)
    already_posted = load_posted_reviews()
    already_posted = already_posted | load_discord_ledger()
    # Also check Discord channel API to prevent duplicates across machines
    channel_posted = get_discord_channel_threads(config.channel_id, config.bot_token)
    already_posted = already_posted | channel_posted

    # Get reviews to post
    if specific_review:
        if str(specific_review) not in telegram_links:
            logger.error(f"Review_{specific_review} not found in Telegram links")
            return 1
        reviews_to_post = [specific_review]
    else:
        reviews_to_post = get_new_reviews_for_discord(telegram_links, already_posted)

    if not reviews_to_post:
        logger.info("No new reviews to post to Discord")
        return 0

    logger.info(f"Found {len(reviews_to_post)} review(s) to post: {reviews_to_post}")

    # Post each review
    success_count = 0
    failed_count = 0

    for review_num in reviews_to_post:
        try:
            if post_review_to_discord(review_num, config, telegram_links, dry_run):
                success_count += 1
            else:
                failed_count += 1

            # Small delay between posts to avoid rate limiting
            if not dry_run and len(reviews_to_post) > 1:
                time.sleep(2)

        except Exception as e:
            logger.exception(f"Error posting Review_{review_num}: {e}")
            failed_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Discord Posting Summary")
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
