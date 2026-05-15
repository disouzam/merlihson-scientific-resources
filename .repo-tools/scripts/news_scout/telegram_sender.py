"""Post the Hebrew news digest to Telegram, with safe splitting and retries."""

from __future__ import annotations

from typing import List

import requests

TELEGRAM_MAX = 4096


def _split(text: str, limit: int = TELEGRAM_MAX) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    current = ""
    for para in text.split("\n\n"):
        # +2 for the rejoin separator
        if len(current) + len(para) + 2 > limit:
            if current:
                chunks.append(current)
                current = ""
            # Very long single paragraph — split hard
            while len(para) > limit:
                chunks.append(para[:limit])
                para = para[limit:]
        if current:
            current += "\n\n" + para
        else:
            current = para
    if current:
        chunks.append(current)
    return chunks


def send(
    message: str,
    bot_token: str,
    channel_id: str,
    parse_mode: str = "HTML",
) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chunk in _split(message):
        payload = {
            "chat_id": channel_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        ok = False
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                data = resp.json()
                if data.get("ok"):
                    ok = True
                    break
                print(f"[telegram] API error: {data.get('description', 'unknown')}")
            except requests.RequestException as exc:
                print(f"[telegram] request failed (attempt {attempt + 1}): {exc}")
        if not ok:
            return False
    return True
