#!/usr/bin/env python3
"""
Telegram Message Link Retriever (DEPRECATED - Now handled by telegram_uploader.py)

NOTE: This script is no longer needed! The telegram_uploader.py now automatically
captures message IDs and saves them to telegram_message_ids.json during upload.

This file is kept for reference and potential future utility functions.

The message links are now stored in:
  .repo-tools/logs/telegram_message_ids.json

Format:
{
  "574": {
    "hebrew": {
      "message_id": 909,
      "chat_id": "-1003714004500",
      "link": "https://t.me/c/3714004500/909",
      "timestamp": "2026-02-07T11:05:23"
    },
    "english": {
      "message_id": 910,
      "chat_id": "-1003744896293",
      "link": "https://t.me/c/3744896293/910",
      "timestamp": "2026-02-07T11:06:45"
    }
  }
}
"""

import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MESSAGE_IDS_FILE = REPO_ROOT / ".repo-tools" / "logs" / "telegram_message_ids.json"


def load_message_links():
    """Load message links from JSON file."""
    if not MESSAGE_IDS_FILE.exists():
        print(f"No message links file found: {MESSAGE_IDS_FILE}")
        return {}

    with open(MESSAGE_IDS_FILE, 'r') as f:
        return json.load(f)


def get_review_links(review_num: int):
    """Get Telegram links for a specific review."""
    links = load_message_links()
    review_key = str(review_num)

    if review_key not in links:
        print(f"Review_{review_num} not found in message links")
        return None

    return links[review_key]


if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Message Links")
    print("=" * 60)
    print()
    print("NOTE: Message IDs are now captured automatically by")
    print("      telegram_uploader.py during upload.")
    print()

    if '--review' in sys.argv:
        try:
            idx = sys.argv.index('--review')
            review_num = int(sys.argv[idx + 1])

            links = get_review_links(review_num)
            if links:
                print(f"Review_{review_num} Telegram Links:")
                print()
                if 'hebrew' in links:
                    print(f"  Hebrew:  {links['hebrew']['link']}")
                if 'english' in links:
                    print(f"  English: {links['english']['link']}")
            else:
                print(f"No links found for Review_{review_num}")
                sys.exit(1)

        except (IndexError, ValueError):
            print("Usage: python3 telegram_link_retriever.py --review <number>")
            sys.exit(1)
    else:
        # Show all links
        links = load_message_links()
        if links:
            print(f"Found {len(links)} reviews with Telegram links:")
            print()
            for review_num in sorted(links.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                print(f"Review_{review_num}:")
                if 'hebrew' in links[review_num]:
                    print(f"  🇮🇱 {links[review_num]['hebrew']['link']}")
                if 'english' in links[review_num]:
                    print(f"  🇬🇧 {links[review_num]['english']['link']}")
                print()
        else:
            print("No message links found.")
            print()
            print("Message links will be created automatically when")
            print("telegram_uploader.py uploads new reviews.")
