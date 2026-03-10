#!/usr/bin/env python3
"""
Email Digest Agent -- Main entrypoint.

Orchestrates: Gmail fetch -> parse/categorize -> Claude summarize -> Telegram send.

Run manually: python -m email_digest.scheduler [--dry-run] [--date YYYY-MM-DD] [--refresh]
Scheduled: Runs on Mac wake via launchd (RunAtLoad), once per day.

Tracks last successful run date in ~/.config/email-digest/last_run.txt.
On each run, covers all days since last run. Skips if already ran today.
"""

import json
import subprocess
import sys
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from email_digest.config import Settings

logger = logging.getLogger(__name__)

LAST_RUN_FILE = Path.home() / ".config" / "email-digest" / "last_run.txt"
CACHE_DIR = Path.home() / ".config" / "email-digest" / "cache"


def wait_for_network(timeout: int = 60) -> bool:
    """Wait for network after wake from sleep."""
    logger.info("Checking network connectivity...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("Network is available")
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass

        logger.info("Waiting for network...")
        time.sleep(5)

    logger.warning(f"Network timeout after {timeout}s, proceeding anyway")
    return False


def get_last_run_date() -> date | None:
    """Read the last successful run date."""
    if not LAST_RUN_FILE.exists():
        return None
    try:
        text = LAST_RUN_FILE.read_text().strip()
        return date.fromisoformat(text)
    except (ValueError, OSError):
        return None


def save_last_run_date(d: date):
    """Save today as the last successful run date."""
    LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_FILE.write_text(d.isoformat())


def get_dates_to_cover() -> list[date]:
    """
    Determine which dates need to be covered.

    Returns list of dates from (last_run_date + 1) through yesterday.
    If no previous run, covers yesterday only.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_run = get_last_run_date()

    if last_run is None:
        return [yesterday]

    if last_run >= today:
        # Already ran today
        return []

    # Cover all days from day after last run through yesterday
    start = last_run + timedelta(days=1)
    if start > yesterday:
        # Last run was yesterday, cover yesterday again? No -- already covered.
        # But last_run stores the date OF the run, not the date covered.
        # If last run was yesterday, we need to cover yesterday's emails.
        # Actually, last_run stores the date when we ran, and we covered up to
        # the day before that run. So if last_run == yesterday, we covered
        # day-before-yesterday. We still need yesterday.
        # Let's simplify: last_run_file stores the last date whose emails we processed.
        return [yesterday] if last_run < yesterday else []

    dates = []
    current = start
    while current <= yesterday:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def save_email_cache(emails, target_date: date, append: bool = False):
    """Save parsed emails to cache file for bot_responder lookups.

    When append=True, merges new emails with existing cache entries (dedup by message_id).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{target_date.isoformat()}.json"

    existing = []
    if append and cache_file.exists():
        try:
            existing = json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []

    existing_ids = {e["message_id"] for e in existing}

    new_entries = []
    for e in emails:
        if e.message_id not in existing_ids:
            new_entries.append({
                "sender": e.sender,
                "subject": e.subject,
                "body": e.body[:8000],
                "date": e.date,
                "category": e.category.value,
                "message_id": e.message_id,
            })

    all_entries = existing + new_entries
    cache_file.write_text(json.dumps(all_entries, ensure_ascii=False, indent=2))
    logger.info(f"Cached {len(all_entries)} emails to {cache_file} ({len(new_entries)} new)")


def cleanup_old_caches(max_age_days: int = 3):
    """Delete cache files older than max_age_days."""
    if not CACHE_DIR.exists():
        return
    cutoff = date.today() - timedelta(days=max_age_days)
    for f in CACHE_DIR.glob("*.json"):
        try:
            file_date = date.fromisoformat(f.stem)
            if file_date < cutoff:
                f.unlink()
                logger.info(f"Deleted old cache: {f.name}")
        except ValueError:
            pass


def run_for_date(target_date: date, settings: Settings, dry_run: bool) -> bool:
    """Run the digest pipeline for a single date. Returns True on success."""
    from email_digest.gmail_client import fetch_emails
    from email_digest.email_parser import parse_and_categorize
    from email_digest.summarizer import summarize, summarize_fallback
    from email_digest.telegram_sender import send_digest, send_error_notification

    logger.info(f"Processing emails for {target_date}")

    # Fetch emails
    try:
        raw_messages = fetch_emails(settings, target_date)
    except FileNotFoundError as e:
        error_msg = str(e)
        logger.error(error_msg)
        if not dry_run:
            send_error_notification(error_msg, settings)
        return False
    except RuntimeError as e:
        error_msg = f"Gmail auth failed: {e}"
        logger.error(error_msg)
        if not dry_run:
            send_error_notification("Gmail re-authentication needed. Run: cd .repo-tools/scripts && email_digest/venv/bin/python3 email_digest/setup_oauth.py", settings)
        return False
    except Exception as e:
        error_msg = f"Gmail fetch failed: {e}"
        logger.error(error_msg)
        if not dry_run:
            send_error_notification(error_msg, settings)
        return False

    logger.info(f"Fetched {len(raw_messages)} emails for {target_date}")

    # Handle zero emails
    if not raw_messages:
        msg = f"📬 <b>Daily Email Digest — {target_date}</b>\n\nNo emails received."
        logger.info(f"No emails found for {target_date}")
        if dry_run:
            print(msg)
        else:
            send_digest(msg, settings)
        return True

    # Parse and categorize
    emails = parse_and_categorize(raw_messages)
    logger.info(f"Parsed {len(emails)} emails")

    # Cache emails for bot_responder lookups
    save_email_cache(emails, target_date)
    cleanup_old_caches(max_age_days=3)

    # Summarize
    try:
        summary = summarize(emails, settings, str(target_date))
    except Exception as e:
        logger.error(f"Claude API failed after retries: {e}")
        summary = summarize_fallback(emails, str(target_date))

    # Deliver
    if dry_run:
        print("\n" + "=" * 60)
        print(summary)
        print("=" * 60)
    else:
        success = send_digest(summary, settings)
        if not success:
            logger.error("Telegram delivery failed, saving summary to log")
            fallback_path = settings.log_file.parent / f"digest_{target_date}.txt"
            fallback_path.write_text(summary)
            logger.info(f"Summary saved to {fallback_path}")
            return False

    return True


def load_cached_message_ids(target_date: date) -> set[str]:
    """Load message IDs from an existing cache file."""
    cache_file = CACHE_DIR / f"{target_date.isoformat()}.json"
    if not cache_file.exists():
        return set()
    try:
        entries = json.loads(cache_file.read_text())
        return {e["message_id"] for e in entries}
    except (json.JSONDecodeError, OSError, KeyError):
        return set()


def run_refresh(settings: Settings, dry_run: bool) -> bool:
    """Fetch today's emails and process only those not already in cache."""
    from email_digest.gmail_client import fetch_emails
    from email_digest.email_parser import parse_and_categorize
    from email_digest.summarizer import summarize, summarize_fallback
    from email_digest.telegram_sender import send_digest, send_error_notification

    today = date.today()
    logger.info(f"Refresh: checking for new emails on {today}")

    # Fetch all of today's emails
    try:
        raw_messages = fetch_emails(settings, today)
    except FileNotFoundError as e:
        logger.error(str(e))
        if not dry_run:
            send_error_notification(str(e), settings)
        return False
    except RuntimeError as e:
        logger.error(f"Gmail auth failed: {e}")
        if not dry_run:
            send_error_notification("Gmail re-authentication needed. Run: cd .repo-tools/scripts && email_digest/venv/bin/python3 email_digest/setup_oauth.py", settings)
        return False
    except Exception as e:
        logger.error(f"Gmail fetch failed: {e}")
        if not dry_run:
            send_error_notification(f"Gmail fetch failed: {e}", settings)
        return False

    # Filter out already-seen messages
    seen_ids = load_cached_message_ids(today)
    new_messages = [m for m in raw_messages if m.get("id") not in seen_ids]

    logger.info(f"Refresh: {len(raw_messages)} total, {len(seen_ids)} cached, {len(new_messages)} new")

    if not new_messages:
        msg = f"📬 <b>Email Refresh — {today}</b>\n\nNo new emails since last digest."
        logger.info("No new emails found")
        if dry_run:
            print(msg)
        else:
            send_digest(msg, settings)
        return True

    # Parse and categorize new emails only
    emails = parse_and_categorize(new_messages)
    logger.info(f"Parsed {len(emails)} new emails")

    # Append new emails to cache
    save_email_cache(emails, today, append=True)

    # Summarize
    try:
        summary = summarize(emails, settings, f"{today} (refresh)")
    except Exception as e:
        logger.error(f"Claude API failed after retries: {e}")
        summary = summarize_fallback(emails, f"{today} (refresh)")

    # Deliver
    if dry_run:
        print("\n" + "=" * 60)
        print(summary)
        print("=" * 60)
    else:
        success = send_digest(summary, settings)
        if not success:
            logger.error("Telegram delivery failed")
            return False

    return True


def main() -> int:
    """Main entry point for email digest agent."""
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    refresh = "--refresh" in sys.argv

    # Manual date override
    manual_date = None
    if "--date" in sys.argv:
        try:
            idx = sys.argv.index("--date")
            manual_date = date.fromisoformat(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Invalid --date argument. Use YYYY-MM-DD format.")
            return 1

    # Load settings
    try:
        settings = Settings.from_yaml()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1

    # Setup logging
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(),
        ],
    )

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No messages will be sent to Telegram")
        logger.info("=" * 60)

    # Refresh mode: fetch only new emails since last digest
    if refresh:
        logger.info("Running in refresh mode")
        wait_for_network(timeout=60)
        success = run_refresh(settings, dry_run)
        return 0 if success else 1

    # Determine dates to process
    if manual_date:
        dates_to_cover = [manual_date]
        logger.info(f"Manual date override: {manual_date}")
    else:
        # Check if already ran today
        last_run = get_last_run_date()
        if last_run == date.today() and not force and not dry_run:
            logger.info(f"Already ran today ({last_run}). Skipping. Use --force to override.")
            return 0

        dates_to_cover = get_dates_to_cover()
        if not dates_to_cover:
            logger.info("No dates to cover. Already up to date.")
            return 0

        logger.info(f"Dates to cover: {[str(d) for d in dates_to_cover]}")

    # Wait for network
    wait_for_network(timeout=60)

    # Process each date
    all_success = True
    for target_date in dates_to_cover:
        success = run_for_date(target_date, settings, dry_run)
        if success and not dry_run:
            save_last_run_date(target_date)
        if not success:
            all_success = False

        # Small delay between multi-day digests
        if len(dates_to_cover) > 1:
            time.sleep(2)

    if all_success:
        if not dry_run and not manual_date:
            save_last_run_date(date.today())
        logger.info("Email digest completed successfully")
        return 0
    else:
        logger.error("Email digest completed with errors")
        return 1


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
