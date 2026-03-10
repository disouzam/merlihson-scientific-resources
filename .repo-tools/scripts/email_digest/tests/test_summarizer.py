"""Tests for summarizer module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_digest.config import Settings
from email_digest.email_parser import Category, Email, parse_and_categorize
from email_digest.summarizer import (
    _build_prompt,
    _build_stats,
    summarize,
    summarize_fallback,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_emails():
    with open(FIXTURES_DIR / "sample_gmail_messages.json") as f:
        raw = json.load(f)
    return parse_and_categorize(raw)


def _mock_settings():
    return Settings(
        gmail_credentials_path=Path("/tmp/creds.json"),
        gmail_token_path=Path("/tmp/token.json"),
        anthropic_api_key="test-key",
        telegram_bot_token="test-bot",
        telegram_chat_id="test-chat",
    )


def test_build_prompt_contains_all_categories():
    emails = _load_emails()
    from collections import defaultdict
    by_cat = defaultdict(list)
    for e in emails:
        by_cat[e.category].append(e)

    prompt = _build_prompt(emails, by_cat, "2026-02-19")

    assert "ACTIONABLE" in prompt
    assert "MARKETING" in prompt
    assert "SOCIAL" in prompt
    assert "NEWSLETTER" in prompt
    assert "PERSONAL" in prompt


def test_build_prompt_includes_thread_info():
    emails = _load_emails()
    from collections import defaultdict
    by_cat = defaultdict(list)
    for e in emails:
        by_cat[e.category].append(e)

    prompt = _build_prompt(emails, by_cat, "2026-02-19")
    assert "Thread: 2 messages" in prompt


def test_build_stats():
    from collections import defaultdict
    by_cat = defaultdict(list)
    by_cat[Category.ACTIONABLE] = [MagicMock()] * 2
    by_cat[Category.PERSONAL] = [MagicMock()] * 3
    by_cat[Category.MARKETING] = [MagicMock()] * 5

    stats = _build_stats(by_cat)
    assert "2 actionable" in stats
    assert "3 personal" in stats
    assert "5 marketing" in stats


def test_summarize_fallback():
    emails = _load_emails()
    result = summarize_fallback(emails, "2026-02-19")

    assert "Daily Email Digest" in result
    assert "summarization unavailable" in result
    assert "Alice Chen" in result


def test_summarize_empty_emails():
    settings = _mock_settings()
    result = summarize([], settings, "2026-02-19")

    assert "0 emails processed" in result
    assert "No emails received" in result


@patch("email_digest.summarizer._call_claude")
def test_summarize_calls_claude(mock_claude):
    mock_claude.return_value = "<b>Action Required</b>\n• Test summary"

    emails = _load_emails()
    settings = _mock_settings()

    result = summarize(emails, settings, "2026-02-19")

    assert mock_claude.called
    assert "Daily Email Digest" in result
    assert "emails processed" in result
