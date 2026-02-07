#!/usr/bin/env python3
"""
Discord Review Poster

Posts paper review links to Discord community channel.
Combines Telegram links (Hebrew + English) + Substack link in one message.

How it works:
1. Load Telegram message links from telegram_message_ids.json
2. For each new review (not yet posted to Discord):
   a. Get Substack link via substack_scraper.py
   b. Get review title from markdown file
   c. Format Discord message with all 3 links
   d. Post to Discord webhook
   e. Log success to discord_posts.log

Run manually:
  python3 discord_poster.py --dry-run          # Show what would be posted
  python3 discord_poster.py --test-webhook     # Test webhook only
  python3 discord_poster.py --review 574       # Post specific review
  python3 discord_poster.py                    # Post all new reviews

Scheduled: Runs at 12:00 PM and 12:30 PM (primary + backup)
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

        self.webhook_url = config.get('discord', {}).get('webhook_url')
        self.substack_url = config.get('substack', {}).get('base_url')

        if not self.webhook_url or 'YOUR_' in self.webhook_url:
            raise ValueError("Please configure 'discord.webhook_url' in discord_config.yaml")

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
                          substack_link: Optional[str]) -> str:
    """
    Format the Discord message with all links.

    Format:
      📢 New paper review published:
      📄 Review 574: Paper Title

      🇮🇱 Hebrew: https://t.me/c/.../12345
      🇬🇧 English: https://t.me/c/.../12346
      📝 Substack: https://yoursubstack.com/p/review-574
    """
    lines = [
        "📢 **New paper review published:**",
        f"📄 **Review {review_num}: {title}**",
        "",
        ""
    ]

    # All links are required - validated before calling this function
    lines.append(f"🇮🇱 **Hebrew:** {hebrew_link}")
    lines.append("")

    lines.append(f"🇬🇧 **English:** {english_link}")
    lines.append("")

    lines.append(f"📝 **Substack:** {substack_link}")
    lines.append("")

    return "\n".join(lines)


def post_to_discord(webhook_url: str, message: str) -> bool:
    """
    Post message to Discord via webhook.

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
    Post a single review to Discord.

    VALIDATION: Only posts if ALL 3 links are present:
    - Hebrew Telegram link
    - English Telegram link
    - Substack link

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
        logger.warning(f"  Will retry in next run (5:00 PM) if Substack is published by then.")
        return False

    logger.info(f"✓ All 3 links validated for Review_{review_num}")
    logger.info(f"  Hebrew Telegram: {hebrew_link[:50]}...")
    logger.info(f"  English Telegram: {english_link[:50]}...")
    logger.info(f"  Substack: {substack_link[:50]}...")

    # Get review title
    title = get_review_title(review_num)

    # Format message
    message = format_discord_message(review_num, title, hebrew_link, english_link, substack_link)

    if dry_run:
        logger.info(f"[DRY RUN] Would post to Discord:")
        logger.info("")
        logger.info(message)
        logger.info("")
        return True

    # Post to Discord
    logger.info(f"Posting Review_{review_num} to Discord...")
    success = post_to_discord(config.webhook_url, message)

    if success:
        log_discord_post(review_num, 'success')
        logger.info(f"✓ Successfully posted Review_{review_num} to Discord")
    else:
        log_discord_post(review_num, 'failed')
        logger.error(f"✗ Failed to post Review_{review_num} to Discord")

    return success


def test_webhook(config: DiscordConfig) -> bool:
    """Test Discord webhook with a simple message."""
    logger.info("Testing Discord webhook...")

    test_message = f"🧪 Test message from Discord poster\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return post_to_discord(config.webhook_url, test_message)


def main():
    """Main entry point for Discord poster."""

    # Parse arguments
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv
    test_webhook_only = '--test-webhook' in sys.argv
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

    # Test webhook only
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
