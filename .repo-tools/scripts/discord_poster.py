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
from pathlib import Path
from typing import Optional, Dict, List
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

        # Optional settings
        settings = config.get('settings', {})
        self.retry_on_failure = settings.get('retry_on_failure', True)
        self.retry_count = settings.get('retry_count', 2)
        self.retry_delay_seconds = settings.get('retry_delay_seconds', 30)


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


def log_discord_post(review_num: int, status: str):
    """Append Discord post record to log file."""
    try:
        DISCORD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DISCORD_LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | Review_{review_num:03d} | {status}\n")
    except Exception as e:
        logger.error(f"Error writing to Discord log: {e}")


def get_review_title(review_num: int) -> str:
    """
    Extract review title from markdown file.

    Tries Hebrew first, then English.
    Returns "Paper Title" or a default if not found.
    """
    # Try Hebrew first
    hebrew_file = HEBREW_MD_DIR / f"Review_{review_num:03d}.md"
    english_file = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"

    for file_path in [hebrew_file, english_file]:
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
        f"📄 **Review {review_num}: {title}**",
        ""
    ]

    # Telegram links
    lines.append(f"🇮🇱 **Hebrew:** {hebrew_link}")
    lines.append(f"🇬🇧 **English:** {english_link}")
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
    Find reviews that:
    1. Have both Hebrew and English Telegram links
    2. Were uploaded in the last 24 hours
    3. Haven't been posted to Discord yet

    Args:
        telegram_links: Dict from telegram_message_ids.json
        already_posted: Set of already posted review numbers

    Returns:
        List of review numbers to post (most recent first)
    """
    from datetime import datetime, timedelta

    new_reviews = []
    cutoff_time = datetime.now() - timedelta(hours=24)

    for review_key, links in telegram_links.items():
        # Skip non-numeric keys (like "test")
        if not review_key.isdigit():
            continue

        review_num = int(review_key)

        # Skip if already posted
        if review_num in already_posted:
            logger.debug(f"Review_{review_num} already posted to Discord")
            continue

        # Check if both Hebrew and English links exist
        has_hebrew = 'hebrew' in links and links['hebrew'].get('link')
        has_english = 'english' in links and links['english'].get('link')

        if not (has_hebrew and has_english):
            logger.debug(f"Review_{review_num} missing Telegram links (Hebrew: {has_hebrew}, English: {has_english})")
            continue

        # Check if uploaded in last 24 hours
        hebrew_timestamp = links.get('hebrew', {}).get('timestamp', '')
        english_timestamp = links.get('english', {}).get('timestamp', '')

        try:
            # Parse timestamp (format: "2026-02-07T11:00:00")
            upload_time = None
            for ts in [hebrew_timestamp, english_timestamp]:
                if ts:
                    upload_time = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
                    break

            if upload_time and upload_time >= cutoff_time:
                new_reviews.append(review_num)
                logger.debug(f"Review_{review_num} uploaded at {upload_time}, eligible for posting")
            else:
                logger.debug(f"Review_{review_num} too old (uploaded: {upload_time})")

        except ValueError as e:
            # If timestamp parsing fails, include it anyway (backward compatibility)
            logger.warning(f"Could not parse timestamp for Review_{review_num}: {e}")
            new_reviews.append(review_num)

    # Return most recent reviews first (highest numbers)
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
        logger.info("")
        logger.info(message)
        logger.info("")
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
        logger.info(f"✓ Successfully posted Review_{review_num} to Discord thread")
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

    # Load Telegram links
    telegram_links = load_telegram_links()
    if not telegram_links:
        logger.warning("No Telegram links found. Run telegram_uploader.py first.")
        return 1

    # Load already posted reviews
    already_posted = load_posted_reviews()

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
                import time
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
