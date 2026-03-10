"""Parse Gmail API messages, categorize, and group threads."""

import base64
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import html2text


class Category(str, Enum):
    ACTIONABLE = "actionable"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    MARKETING = "marketing"
    PERSONAL = "personal"


@dataclass
class Email:
    sender: str
    subject: str
    body: str
    date: str
    labels: list[str]
    thread_id: str
    message_id: str
    category: Category = Category.PERSONAL


ACTIONABLE_KEYWORDS = re.compile(
    r"\b(urgent|action required|action needed|deadline|please review|asap|"
    r"immediate|time.sensitive|respond by|due date|expir)\b",
    re.IGNORECASE,
)

NEWSLETTER_DOMAINS = {
    "substack.com", "newsletter.", "mail.beehiiv.com", "email.mg.",
    "mailchimp.com", "convertkit.com", "sendinblue.com",
}

_h2t = html2text.HTML2Text()
_h2t.ignore_links = True
_h2t.ignore_images = True
_h2t.body_width = 0


def parse_message(raw: dict) -> Email:
    """Parse a raw Gmail API message dict into an Email dataclass."""
    headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
    labels = raw.get("labelIds", [])

    sender = headers.get("from", "Unknown")
    subject = headers.get("subject", "(no subject)")
    date_str = headers.get("date", "")

    body = _extract_body(raw.get("payload", {}))
    if len(body) > 4000:
        body = body[:4000] + "..."

    has_unsubscribe = "list-unsubscribe" in headers

    category = _categorize(labels, sender, subject, body, has_unsubscribe)

    return Email(
        sender=sender,
        subject=subject,
        body=body,
        date=date_str,
        labels=labels,
        thread_id=raw.get("threadId", ""),
        message_id=raw.get("id", ""),
        category=category,
    )


def _extract_body(payload: dict) -> str:
    """Extract text body from Gmail payload, preferring plain text."""
    mime_type = payload.get("mimeType", "")

    # Direct body
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            return _h2t.handle(html).strip()

    # Multipart: recurse into parts
    parts = payload.get("parts", [])
    # Prefer text/plain
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Fallback to text/html
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                return _h2t.handle(html).strip()

    # Recurse into nested multipart
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


def _categorize(
    labels: list[str], sender: str, subject: str, body: str, has_unsubscribe: bool
) -> Category:
    """Categorize email based on labels, sender, and content."""
    label_set = set(labels)

    # Actionable: starred/important labels or urgency keywords
    if label_set & {"IMPORTANT", "STARRED"}:
        return Category.ACTIONABLE
    if ACTIONABLE_KEYWORDS.search(subject) or ACTIONABLE_KEYWORDS.search(body[:500]):
        return Category.ACTIONABLE

    # Social
    if "CATEGORY_SOCIAL" in label_set:
        return Category.SOCIAL

    # Marketing / Promotions
    if "CATEGORY_PROMOTIONS" in label_set:
        return Category.MARKETING

    # Newsletter
    if label_set & {"CATEGORY_UPDATES", "CATEGORY_FORUMS"}:
        return Category.NEWSLETTER
    if has_unsubscribe:
        sender_lower = sender.lower()
        if any(domain in sender_lower for domain in NEWSLETTER_DOMAINS):
            return Category.NEWSLETTER
        # Unsubscribe header + not personal => newsletter
        return Category.NEWSLETTER

    # Everything else in INBOX is personal
    return Category.PERSONAL


def group_by_thread(emails: list[Email]) -> dict[str, list[Email]]:
    """Group emails by thread_id, sorted by date within each thread."""
    threads: dict[str, list[Email]] = {}
    for email in emails:
        threads.setdefault(email.thread_id, []).append(email)

    # Sort each thread by date
    for thread_emails in threads.values():
        thread_emails.sort(key=lambda e: e.date)

    return threads


def parse_and_categorize(raw_messages: list[dict]) -> list[Email]:
    """Parse all raw messages and return categorized Email list."""
    return [parse_message(msg) for msg in raw_messages]
