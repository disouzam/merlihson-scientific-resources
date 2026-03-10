"""Format and send digest to Telegram via HTTP API."""

import logging
import time
from typing import Optional

import requests

from email_digest.config import Settings

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


def send_digest(text: str, settings: Settings) -> bool:
    """Send formatted digest to Telegram. Splits if needed. Returns True on success."""
    messages = split_message(text, MAX_MESSAGE_LENGTH)

    for i, message_text in enumerate(messages, 1):
        if len(messages) > 1:
            message_text = f"({i}/{len(messages)})\n\n{message_text}"

        success = _send_message(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            message_text,
        )

        if not success:
            logger.error(f"Failed to send part {i}/{len(messages)}")
            return False

        if i < len(messages):
            time.sleep(1)

    logger.info(f"Sent digest in {len(messages)} message(s)")
    return True


def send_error_notification(error_msg: str, settings: Settings) -> bool:
    """Send error notification to Telegram."""
    text = f"<b>Email Digest Error</b>\n\n{error_msg}"
    return _send_message(settings.telegram_bot_token, settings.telegram_chat_id, text)


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into multiple messages at paragraph boundaries."""
    if len(text) <= max_length:
        return [text]

    paragraphs = text.split("\n\n")
    messages = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_length:
            if current:
                messages.append(current.strip())
                current = ""

            if len(para) > max_length:
                # Split long paragraph at sentence boundaries
                sentences = para.split(". ")
                temp = ""
                for sentence in sentences:
                    if len(temp) + len(sentence) + 2 < max_length:
                        temp += sentence + ". "
                    else:
                        if temp:
                            messages.append(temp.strip())
                        temp = sentence + ". "
                if temp:
                    current = temp
            else:
                current = para + "\n\n"
        else:
            current += para + "\n\n"

    if current:
        messages.append(current.strip())

    return messages


def _send_message(
    bot_token: str, chat_id: str, text: str, retry_count: int = 2, retry_delay: int = 5
) -> bool:
    """Send a single message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    for attempt in range(retry_count + 1):
        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", retry_delay)
                logger.warning(f"Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown')}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {e}")

        if attempt < retry_count:
            logger.info(f"Retrying in {retry_delay}s... (attempt {attempt + 1}/{retry_count})")
            time.sleep(retry_delay)

    return False
