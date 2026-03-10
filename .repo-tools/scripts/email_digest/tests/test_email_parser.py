"""Tests for email_parser module."""

import json
from pathlib import Path

from email_digest.email_parser import (
    Category,
    Email,
    group_by_thread,
    parse_and_categorize,
    parse_message,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixtures():
    with open(FIXTURES_DIR / "sample_gmail_messages.json") as f:
        return json.load(f)


def test_parse_message_plain_text():
    raw = _load_fixtures()[0]  # Alice's PR review
    email = parse_message(raw)

    assert email.sender == "Alice Chen <alice@example.com>"
    assert email.subject == "PR review needed - auth-service"
    assert email.thread_id == "thread001"
    assert email.message_id == "msg001"
    assert "review" in email.body.lower()


def test_parse_message_multipart():
    raw = _load_fixtures()[6]  # HR multipart message
    email = parse_message(raw)

    assert email.sender == "HR Team <hr@company.com>"
    assert "benefits enrollment" in email.body.lower()


def test_categorize_actionable_by_label():
    raw = _load_fixtures()[0]  # Has IMPORTANT label
    email = parse_message(raw)
    assert email.category == Category.ACTIONABLE


def test_categorize_actionable_by_keyword():
    raw = _load_fixtures()[6]  # "Action required" in subject
    email = parse_message(raw)
    assert email.category == Category.ACTIONABLE


def test_categorize_marketing():
    raw = _load_fixtures()[1]  # CATEGORY_PROMOTIONS
    email = parse_message(raw)
    assert email.category == Category.MARKETING


def test_categorize_social():
    raw = _load_fixtures()[2]  # CATEGORY_SOCIAL
    email = parse_message(raw)
    assert email.category == Category.SOCIAL


def test_categorize_newsletter():
    raw = _load_fixtures()[3]  # CATEGORY_UPDATES + List-Unsubscribe
    email = parse_message(raw)
    assert email.category == Category.NEWSLETTER


def test_categorize_personal():
    raw = _load_fixtures()[4]  # Plain INBOX, no special labels
    email = parse_message(raw)
    assert email.category == Category.PERSONAL


def test_group_by_thread():
    fixtures = _load_fixtures()
    emails = [parse_message(msg) for msg in fixtures]
    threads = group_by_thread(emails)

    # msg005 and msg006 share thread005
    assert "thread005" in threads
    assert len(threads["thread005"]) == 2

    # Other threads have 1 message each
    assert len(threads["thread001"]) == 1


def test_parse_and_categorize_all():
    fixtures = _load_fixtures()
    emails = parse_and_categorize(fixtures)
    assert len(emails) == len(fixtures)

    categories = {e.category for e in emails}
    assert Category.ACTIONABLE in categories
    assert Category.MARKETING in categories
    assert Category.SOCIAL in categories


def test_empty_input():
    emails = parse_and_categorize([])
    assert emails == []


def test_body_truncation():
    raw = _load_fixtures()[0]
    # Simulate very long body by repeating data
    import base64
    long_text = "A" * 5000
    raw["payload"]["body"]["data"] = base64.urlsafe_b64encode(long_text.encode()).decode()

    email = parse_message(raw)
    assert len(email.body) <= 4004  # 4000 + "..."
