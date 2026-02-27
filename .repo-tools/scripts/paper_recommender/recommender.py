#!/usr/bin/env python3
"""Daily Paper Recommender — main entry point.

Fetches recent arXiv papers, ranks them by relevance to Mike's interests
using Claude Haiku, and sends the top picks to Telegram.

Usage:
    python3 -m paper_recommender.recommender              # Normal run (skips if already ran today)
    python3 -m paper_recommender.recommender --dry-run     # Print to console, don't send
    python3 -m paper_recommender.recommender --force       # Ignore last_run check
    python3 -m paper_recommender.recommender --days 2      # Look back 2 days
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from .arxiv_fetcher import fetch_recent_papers
from .interest_profile import build_interest_profile
from .paper_ranker import rank_papers
from .telegram_sender import format_message, send_to_telegram

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
LAST_RUN_FILE = SCRIPT_DIR / "last_run.txt"
CONFIG_FILE = SCRIPT_DIR / "config.yaml"


def load_config() -> dict:
    """Load configuration from config.yaml."""
    if not CONFIG_FILE.exists():
        print(f"Error: Config file not found at {CONFIG_FILE}")
        print("Copy config.yaml.template to config.yaml and fill in your credentials.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def wait_for_network(max_wait: int = 120) -> bool:
    """Wait up to max_wait seconds for network connectivity.

    Checks by resolving a DNS name. Returns True if network is available.
    """
    start = time.time()
    while time.time() - start < max_wait:
        try:
            socket.getaddrinfo("export.arxiv.org", 443)
            return True
        except socket.gaierror:
            time.sleep(10)
    return False


def check_remote_last_run() -> bool:
    """Check if the remote repo's last_run.txt has today's date.

    Uses git fetch + git show to read the remote file without needing
    a clean working tree (avoids conflicts with local changes).
    Returns True if another machine already ran today.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    rel_path = LAST_RUN_FILE.relative_to(REPO_ROOT)
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=REPO_ROOT, capture_output=True, timeout=60,
        )
        result = subprocess.run(
            ["git", "show", f"origin/main:{rel_path}"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
        )
        remote_date = result.stdout.strip()
        if remote_date == today:
            return True
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Warning: git fetch failed ({e}), proceeding with local state.")
    return False


def git_push_last_run() -> None:
    """Commit and push last_run.txt so other machines see today's run."""
    try:
        rel_path = LAST_RUN_FILE.relative_to(REPO_ROOT)
        subprocess.run(
            ["git", "add", str(rel_path)],
            cwd=REPO_ROOT, capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", "paper recommender: mark daily run"],
            cwd=REPO_ROOT, capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "push", "--quiet"],
            cwd=REPO_ROOT, capture_output=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Warning: git push of last_run.txt failed ({e}). Second machine may re-send.")


def already_ran_today() -> bool:
    """Check if the recommender already ran today."""
    if not LAST_RUN_FILE.exists():
        return False
    last_run = LAST_RUN_FILE.read_text().strip()
    return last_run == datetime.now().strftime("%Y-%m-%d")


def mark_ran_today() -> None:
    """Record that we ran today."""
    LAST_RUN_FILE.write_text(datetime.now().strftime("%Y-%m-%d"))


def main():
    parser = argparse.ArgumentParser(description="Daily Paper Recommender")
    parser.add_argument("--dry-run", action="store_true", help="Print to console instead of sending to Telegram")
    parser.add_argument("--force", action="store_true", help="Run even if already ran today")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back (default: 1)")
    args = parser.parse_args()

    # Skip weekends — arXiv doesn't publish on Sat/Sun
    if datetime.now().weekday() in (5, 6) and not args.force and not args.dry_run:
        print("Weekend — arXiv doesn't publish. Skipping.")
        return

    # Check if already ran today — local file first, then remote
    if not args.force and not args.dry_run:
        if already_ran_today():
            print("Already ran today. Use --force to run again.")
            return

    # Wait for network before proceeding (handles wake-from-sleep with no network yet)
    if not args.dry_run:
        print("Checking network connectivity...")
        if not wait_for_network():
            print("No network after 2 minutes. Will retry on next scheduled run.")
            sys.exit(1)

    # Check remote after network is confirmed
    if not args.force and not args.dry_run:
        if check_remote_last_run():
            print("Today's picks were already sent by another machine. Skipping.")
            mark_ran_today()
            return

    config = load_config()

    # Get API key from config or environment
    api_key = config.get("anthropic_api_key", "")
    if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY_HERE":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: No Anthropic API key found. Set it in config.yaml or ANTHROPIC_API_KEY env var.")
        sys.exit(1)

    categories = config.get("arxiv_categories", ["cs.LG", "cs.CL", "cs.AI", "cs.CV", "stat.ML"])
    max_papers = config.get("max_papers_to_send", 10)
    model = config.get("model", "claude-haiku-4-5-20251001")

    # Monday: cover Sat+Sun+Mon (3 days, 20 papers). Other weekdays: 1 day, 10 papers.
    is_monday = datetime.now().weekday() == 0
    days_back = args.days if args.days != 1 else (3 if is_monday else 1)
    if is_monday:
        max_papers = 20

    # Step 1: Fetch recent papers
    print(f"Fetching papers from arXiv ({', '.join(categories)})...")
    papers = fetch_recent_papers(categories, days_back=days_back)
    print(f"Found {len(papers)} recent papers.")

    if not papers:
        print("No papers found. This can happen on weekends or holidays.")
        return

    # Step 2: Build interest profile
    print("Building interest profile...")
    profile = build_interest_profile()

    # Step 3: Rank papers
    print(f"Ranking papers using {model}...")
    top_papers = rank_papers(papers, profile, api_key, model=model, top_k=max_papers)
    print(f"Selected top {len(top_papers)} papers.")

    if not top_papers:
        print("No papers scored. Something may be wrong with the ranking.")
        return

    # Step 4: Format message
    message = format_message(top_papers)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — would send this message:")
        print("=" * 60)
        print(message)
        print("=" * 60)
        return

    # Step 5: Send to Telegram
    bot_token = config.get("telegram_bot_token", "")
    channel_id = config.get("telegram_channel_id", "")
    if not bot_token or not channel_id:
        print("Error: Telegram bot_token and channel_id must be set in config.yaml")
        sys.exit(1)

    print("Sending to Telegram...")
    success = send_to_telegram(message, bot_token, channel_id)

    if success:
        mark_ran_today()
        git_push_last_run()
        print("Done! Message sent successfully.")
    else:
        print("Failed to send message to Telegram.")
        sys.exit(1)


if __name__ == "__main__":
    main()
