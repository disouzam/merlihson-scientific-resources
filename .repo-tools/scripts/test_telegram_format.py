#!/usr/bin/env python3
"""
Test Telegram Message Formatting

Simulates exactly how telegram_uploader.py processes and formats messages
to identify spacing issues before actually sending to Telegram.
"""

import html
import sys
from pathlib import Path
from typing import List

# Configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENGLISH_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-english-reviews-md"
MAX_MESSAGE_LENGTH = 4096


def read_markdown_file(file_path: Path) -> str:
    """Read markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Split text into multiple messages (same as telegram_uploader.py)."""
    if len(text) <= max_length:
        return [text]

    paragraphs = text.split('\n\n')
    messages = []
    current_message = ""

    for para in paragraphs:
        if len(current_message) + len(para) + 2 > max_length:
            if current_message:
                messages.append(current_message.strip())  # ← THE STRIP!
                current_message = ""

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

    if current_message:
        messages.append(current_message.strip())  # ← THE STRIP!

    return messages


def escape_for_telegram_html(text: str) -> str:
    """Escape text for Telegram HTML mode."""
    return html.escape(text, quote=True)


def test_review(review_num: int):
    """Test formatting for a specific review."""
    file_path = ENGLISH_MD_DIR / f"Review_{review_num:03d}.md"

    if not file_path.exists():
        print(f"✗ Review_{review_num} not found")
        return

    print("=" * 70)
    print(f"Testing Review_{review_num} Telegram Formatting")
    print("=" * 70)
    print()

    # Read content
    content = read_markdown_file(file_path)
    print(f"Original file length: {len(content)} characters")
    print()

    # Split into messages
    messages = split_message(content)
    print(f"Split into {len(messages)} message(s)")
    print()

    # Show each message
    for i, message_text in enumerate(messages, 1):
        print("=" * 70)
        print(f"MESSAGE {i}/{len(messages)}")
        print("=" * 70)
        print()

        # Show what would be sent (with part indicator)
        if len(messages) > 1:
            part_indicator = f"({i}/{len(messages)})\n\n"
            final_text = part_indicator + escape_for_telegram_html(message_text)
        else:
            final_text = escape_for_telegram_html(message_text)

        print("TELEGRAM OUTPUT:")
        print("-" * 70)
        print(final_text)
        print("-" * 70)
        print()
        print(f"Length: {len(final_text)} characters")
        print()

        # Check for spacing issues
        if "Review " in final_text:
            # Find lines containing "Review XXX"
            for line in final_text.split('\n'):
                if "Review " in line and any(c.isdigit() for c in line):
                    # Check if there's a capital letter immediately after the number
                    import re
                    issue = re.search(r'Review \d+[A-Z]', line)
                    if issue:
                        print("⚠️  SPACING ISSUE DETECTED:")
                        print(f"   {line[:80]}")
                        print(f"   Problem: No space after review number")
                        print()

    print("=" * 70)
    print("Analysis Complete")
    print("=" * 70)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 test_telegram_format.py <review_number>")
        print("Example: python3 test_telegram_format.py 574")
        return 1

    try:
        review_num = int(sys.argv[1])
        test_review(review_num)
        return 0
    except ValueError:
        print("Error: Review number must be an integer")
        return 1


if __name__ == "__main__":
    sys.exit(main())
