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
import sys
from datetime import datetime
from pathlib import Path

import yaml

from .arxiv_fetcher import fetch_recent_papers
from .interest_profile import build_interest_profile
from .paper_ranker import rank_papers
from .telegram_sender import format_message, send_to_telegram

SCRIPT_DIR = Path(__file__).resolve().parent
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

    # Check if already ran today
    if not args.force and not args.dry_run and already_ran_today():
        print("Already ran today. Use --force to run again.")
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

    # Step 1: Fetch recent papers
    print(f"Fetching papers from arXiv ({', '.join(categories)})...")
    papers = fetch_recent_papers(categories, days_back=args.days)
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
        print("Done! Message sent successfully.")
    else:
        print("Failed to send message to Telegram.")
        sys.exit(1)


if __name__ == "__main__":
    main()
