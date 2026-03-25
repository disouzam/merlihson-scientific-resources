"""Send paper recommendations to Telegram."""

from datetime import datetime
from typing import List

import requests

from .paper_ranker import RankedPaper


def format_message(ranked_papers: List[RankedPaper], date: datetime = None) -> str:
    """Format the top papers into a Telegram message."""
    if date is None:
        date = datetime.now()

    date_str = date.strftime("%b %d, %Y")
    lines = [f"\U0001f52c Daily Paper Picks for Mike ({date_str})\n"]

    for i, rp in enumerate(ranked_papers, 1):
        authors_str = ", ".join(rp.paper.authors)
        entry = (
            f"{i}. {rp.paper.title}\n"
            f"   Authors: {authors_str}\n"
            f"   \u2b50 \"{rp.reason}\"\n"
        )
        if rp.review:
            entry += f"\n   {rp.review}\n"
        entry += f"\n   \U0001f517 {rp.paper.link}\n"
        lines.append(entry)

    return "\n".join(lines)


def send_to_telegram(
    message: str,
    bot_token: str,
    channel_id: str,
) -> bool:
    """Send a message to a Telegram channel. Returns True on success."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Split if message exceeds Telegram's 4096 char limit
    messages = _split_message(message, max_length=4096)

    for msg in messages:
        payload = {
            "chat_id": channel_id,
            "text": msg,
            "disable_web_page_preview": True,
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                data = resp.json()
                if data.get("ok"):
                    break
                else:
                    print(f"Telegram API error: {data.get('description', 'unknown')}")
                    if attempt == 2:
                        return False
            except requests.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    return False

    return True


def _split_message(text: str, max_length: int = 4096) -> List[str]:
    """Split a message at paragraph boundaries if it exceeds max_length."""
    if len(text) <= max_length:
        return [text]

    messages = []
    current = ""

    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > max_length:
            if current:
                messages.append(current.strip())
            current = paragraph
        else:
            current = current + "\n\n" + paragraph if current else paragraph

    if current:
        messages.append(current.strip())

    return messages
