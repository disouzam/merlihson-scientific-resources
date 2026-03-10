"""
Telegram bot responder -- "Show Full Email" feature.

Long-polls getUpdates and matches user queries against cached emails
via case-insensitive substring on sender + subject.

Run: python -m email_digest.bot_responder
"""

import json
import logging
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from email_digest.config import Settings
from email_digest.telegram_sender import split_message

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".config" / "email-digest" / "cache"
POLL_INTERVAL = 30
AUTHORIZED_CHAT_ID = "403971339"


def load_cached_emails() -> list[dict]:
    """Load all cached emails from last 3 days."""
    emails = []
    if not CACHE_DIR.exists():
        return emails
    cutoff = date.today() - timedelta(days=3)
    for f in sorted(CACHE_DIR.glob("*.json")):
        try:
            file_date = date.fromisoformat(f.stem)
            if file_date < cutoff:
                continue
        except ValueError:
            continue
        try:
            entries = json.loads(f.read_text())
            for entry in entries:
                entry["_cache_date"] = f.stem
            emails.extend(entries)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache {f}: {e}")
    return emails


def _normalize(text: str) -> str:
    """Strip punctuation and collapse whitespace for fuzzy matching."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def find_matches(query: str, emails: list[dict]) -> list[dict]:
    """Find emails matching query against sender + subject.

    Matching strategy:
    1. Split query into words (punctuation stripped).
    2. An email matches if ALL query words appear in (sender + subject).
    This handles "Napkin AI?", "alice budget", partial names, etc.
    """
    words = _normalize(query).split()
    if not words:
        return []
    results = []
    for e in emails:
        haystack = _normalize(e["sender"] + " " + e["subject"])
        if all(w in haystack for w in words):
            results.append(e)
    return results


_NOISE_URL_PATTERNS = re.compile(
    r"(unsub|track|click\.|beacon|pixel|open\.|list-manage|email\.mg\.|"
    r"convertkit-mail)",
    re.IGNORECASE,
)

_NOISE_PATH_PATTERNS = re.compile(
    r"\.(gif|png|jpg|jpeg|bmp|webp)(\?|$|])",
    re.IGNORECASE,
)

_TRACKING_PARAMS = {
    "trk", "trkEmail", "midToken", "midSig", "eid", "lipi",
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "ref_", "mc_cid", "mc_eid", "s", "ss",
}


def _clean_url(url: str) -> str:
    """Strip tracking query params from a URL."""
    url = url.rstrip("])")
    if "?" not in url:
        return url
    base, query = url.split("?", 1)
    params = query.split("&")
    kept = [p for p in params if p.split("=")[0] not in _TRACKING_PARAMS]
    if not kept:
        return base
    return base + "?" + "&".join(kept)


def _is_noise_url(url: str) -> bool:
    """Check if a URL is purely tracking/image junk that shouldn't be shown."""
    return bool(_NOISE_URL_PATTERNS.search(url)) or bool(_NOISE_PATH_PATTERNS.search(url))


def _clean_body(body: str) -> str:
    """Clean up email body for readable Telegram display.

    Preserves meaningful links as placeholders that get converted to
    HTML <a> tags after escaping. Placeholder format: \x00LINK\x01url:text\x00
    """
    # Remove image markers
    body = re.sub(r"^Image\s*$", "", body, flags=re.MULTILINE)
    # Remove "View image:", "Follow image link:", "Caption:" prefixes
    body = re.sub(r"^(View image|Follow image link|Caption):?\s*", "", body, flags=re.MULTILINE)

    # Convert markdown-style links [text](url) -> placeholder or just text
    def _replace_md_link(m):
        text, url = m.group(1), m.group(2)
        if _is_noise_url(url):
            return text
        return f"\x00LINK\x01{_clean_url(url)}\x01{text}\x00"
    body = re.sub(r"\[([^\]]+)\]\s*\(\s*(https?://[^)]*)\)", _replace_md_link, body)

    # Convert "text (url)" or standalone "(url)" -> placeholder or remove
    def _replace_paren_url(m):
        url = m.group(1).strip()
        if _is_noise_url(url):
            return ""
        return f" \x00LINK\x01{_clean_url(url)}\x01link\x00"
    body = re.sub(r"\(\s*(https?://[^)]+)\)", _replace_paren_url, body)

    # Convert remaining bare URLs -> placeholder or remove
    def _replace_bare_url(m):
        url = m.group(0)
        if _is_noise_url(url):
            return ""
        return f"\x00LINK\x01{_clean_url(url)}\x01link\x00"
    body = re.sub(r"https?://\S+", _replace_bare_url, body)

    # Remove link reference markers like [1], [2]
    body = re.sub(r"\[(\d+)\]", "", body)
    # Clean up orphaned parentheses/artifacts: "( )" or empty parens
    body = re.sub(r"\(\s*\)", "", body)
    # Break long runs of text into paragraphs at sentence boundaries.
    # Split on ". " followed by an uppercase letter (likely a new sentence/topic).
    # Only do this for lines longer than 200 chars (i.e. wall-of-text paragraphs).
    lines = body.split("\n")
    rebuilt = []
    for line in lines:
        if len(line) > 200:
            # Insert paragraph breaks at sentence boundaries
            line = re.sub(r"(?<=\.)\s+(?=[A-Z\(\[])", "\n\n", line)
        rebuilt.append(line)
    body = "\n".join(rebuilt)
    # Collapse 3+ newlines into 2
    body = re.sub(r"\n{3,}", "\n\n", body)
    # Collapse lines that are just dashes/underscores (separators)
    body = re.sub(r"^[-_=]{3,}\s*$", "—", body, flags=re.MULTILINE)
    # Remove duplicate/boilerplate lines (e.g. repeated author names)
    seen = set()
    deduped = []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped and stripped in seen and len(stripped) < 80:
            continue
        seen.add(stripped)
        deduped.append(line)
    body = "\n".join(deduped)
    # Strip leading/trailing whitespace
    body = body.strip()
    return body


def _restore_links(escaped_text: str) -> str:
    """Convert \x00LINK\x01url:text\x00 placeholders to HTML <a> tags."""
    def _to_html_link(m):
        url = m.group(1)
        text = m.group(2)
        if text == "link":
            # Show a shortened URL as display text
            display = re.sub(r"https?://(www\.)?", "", url)
            display = display.split("?")[0].rstrip("/")
            if len(display) > 50:
                display = display[:47] + "..."
            return f'<a href="{url}">{display}</a>'
        return f'<a href="{url}">{text}</a>'
    return re.sub(r"\x00LINK\x01(.*?)\x01(.*?)\x00", _to_html_link, escaped_text)


def format_email(email: dict) -> str:
    """Format a single email for display."""
    body = _clean_body(email.get("body", "(no body)"))
    escaped_body = _escape(body)
    body_with_links = _restore_links(escaped_body)
    lines = [
        f"<b>From:</b> {_escape(email['sender'])}",
        f"<b>Subject:</b> {_escape(email['subject'])}",
        f"<b>Date:</b> {_escape(email.get('date', ''))}",
        "",
        body_with_links,
    ]
    return "\n".join(lines)


def format_match_list(matches: list[dict]) -> str:
    """Format numbered list of matching emails."""
    lines = ["<b>Multiple matches found. Reply with a number:</b>\n"]
    for i, e in enumerate(matches, 1):
        lines.append(f"{i}. {_escape(e['sender'])} — {_escape(e['subject'])}")
    return "\n".join(lines)


def format_all_subjects(emails: list[dict]) -> str:
    """Format all cached email subjects."""
    if not emails:
        return "No cached emails found."
    lines = [f"<b>Cached emails ({len(emails)}):</b>\n"]
    for i, e in enumerate(emails, 1):
        lines.append(f"{i}. [{e.get('_cache_date', '')}] {_escape(e['sender'])} — {_escape(e['subject'])}")
    return "\n".join(lines)


HELP_TEXT = (
    "<b>Email Lookup Bot</b>\n\n"
    "Reply with a sender name or subject keyword to see the full email.\n\n"
    "<b>Commands:</b>\n"
    "• <code>list</code> — show all cached email subjects\n"
    "• <code>help</code> — show this message\n\n"
    "Searches the last 3 days of digests."
)


def _escape(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_reply(bot_token: str, chat_id: str, text: str):
    """Send a reply, splitting if necessary."""
    messages = split_message(text)
    for msg in messages:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                time.sleep(retry_after)
                requests.post(url, json=payload, timeout=30)
            elif not resp.json().get("ok"):
                logger.error(f"Telegram error: {resp.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send reply: {e}")
        time.sleep(0.5)


def handle_message(text: str, bot_token: str, chat_id: str, pending_selections: dict):
    """Process a single incoming message and send response."""
    text = text.strip()
    lower = text.lower()

    if lower == "help":
        send_reply(bot_token, chat_id, HELP_TEXT)
        return

    emails = load_cached_emails()

    if lower == "list":
        send_reply(bot_token, chat_id, format_all_subjects(emails))
        return

    # Check if user is picking from a numbered list
    if chat_id in pending_selections and text.isdigit():
        idx = int(text) - 1
        matches = pending_selections[chat_id]
        if 0 <= idx < len(matches):
            send_reply(bot_token, chat_id, format_email(matches[idx]))
            del pending_selections[chat_id]
            return
        else:
            send_reply(bot_token, chat_id, f"Invalid number. Pick 1-{len(matches)}.")
            return

    # Search
    matches = find_matches(text, emails)

    if not matches:
        send_reply(bot_token, chat_id, "No matching email found.")
    elif len(matches) == 1:
        send_reply(bot_token, chat_id, format_email(matches[0]))
        pending_selections.pop(chat_id, None)
    else:
        send_reply(bot_token, chat_id, format_match_list(matches))
        pending_selections[chat_id] = matches


def refresh_today_cache(settings: Settings):
    """Fetch and cache today's emails (no summarize/send)."""
    from datetime import date
    today = date.today()
    cache_file = CACHE_DIR / f"{today.isoformat()}.json"
    if cache_file.exists():
        logger.info(f"Today's cache already exists: {cache_file.name}")
        return

    logger.info(f"Fetching today's emails for cache ({today})...")
    try:
        from email_digest.gmail_client import fetch_emails
        from email_digest.email_parser import parse_and_categorize
        from email_digest.scheduler import save_email_cache

        raw_messages = fetch_emails(settings, today)
        if raw_messages:
            emails = parse_and_categorize(raw_messages)
            save_email_cache(emails, today)
            logger.info(f"Cached {len(emails)} emails for {today}")
        else:
            logger.info(f"No emails found for {today}")
    except Exception as e:
        logger.error(f"Failed to refresh today's cache: {e}")


def poll_loop(settings: Settings):
    """Main long-polling loop."""
    refresh_today_cache(settings)

    bot_token = settings.telegram_bot_token
    offset = 0
    pending_selections: dict[str, list[dict]] = {}

    logger.info("Bot responder started. Polling for messages...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": offset, "timeout": POLL_INTERVAL}
            resp = requests.get(url, params=params, timeout=POLL_INTERVAL + 10)
            data = resp.json()

            if not data.get("ok"):
                logger.error(f"getUpdates error: {data}")
                time.sleep(10)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")

                if not text or not chat_id:
                    continue

                if chat_id != AUTHORIZED_CHAT_ID:
                    logger.warning(f"Ignoring message from unauthorized chat: {chat_id}")
                    continue

                logger.info(f"Received query: {text[:50]}")
                handle_message(text, bot_token, chat_id, pending_selections)

        except requests.exceptions.RequestException as e:
            logger.error(f"Polling error: {e}")
            time.sleep(10)
        except Exception as e:
            logger.exception(f"Unexpected error in poll loop: {e}")
            time.sleep(10)


def main() -> int:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        settings = Settings.from_env(env_path if env_path.exists() else None)
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1

    log_file = settings.log_file.parent / "bot_responder.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

    poll_loop(settings)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
        sys.exit(0)
