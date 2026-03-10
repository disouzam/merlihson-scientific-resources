"""Tests for bot_responder module."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from email_digest.bot_responder import (
    _normalize,
    find_matches,
    format_email,
    format_match_list,
    format_all_subjects,
    handle_message,
    load_cached_emails,
    _escape,
    AUTHORIZED_CHAT_ID,
)


SAMPLE_EMAILS = [
    {
        "sender": "Alice Smith <alice@example.com>",
        "subject": "Q1 Budget Review",
        "body": "Please review the attached budget for Q1.",
        "date": "Mon, 17 Feb 2026 09:00:00 +0000",
        "category": "actionable",
        "message_id": "msg001",
    },
    {
        "sender": "Bob Jones <bob@corp.com>",
        "subject": "Benefits Enrollment Reminder",
        "body": "Open enrollment ends Friday. Please submit your selections.",
        "date": "Mon, 17 Feb 2026 10:30:00 +0000",
        "category": "actionable",
        "message_id": "msg002",
    },
    {
        "sender": "Newsletter <news@techdigest.com>",
        "subject": "Weekly Tech Roundup",
        "body": "This week in tech: AI advances, new frameworks released...",
        "date": "Mon, 17 Feb 2026 06:00:00 +0000",
        "category": "newsletter",
        "message_id": "msg003",
    },
]


class TestFindMatches:
    def test_match_by_sender_name(self):
        matches = find_matches("alice", SAMPLE_EMAILS)
        assert len(matches) == 1
        assert matches[0]["message_id"] == "msg001"

    def test_match_by_subject(self):
        matches = find_matches("benefits", SAMPLE_EMAILS)
        assert len(matches) == 1
        assert matches[0]["message_id"] == "msg002"

    def test_case_insensitive(self):
        matches = find_matches("ALICE", SAMPLE_EMAILS)
        assert len(matches) == 1

    def test_no_match(self):
        matches = find_matches("nonexistent", SAMPLE_EMAILS)
        assert len(matches) == 0

    def test_multiple_matches(self):
        # Both Alice and Bob emails are from .com domains but let's match on a common term
        matches = find_matches("mon", SAMPLE_EMAILS)
        # "mon" doesn't appear in sender/subject, so 0 matches
        assert len(matches) == 0

    def test_partial_subject_match(self):
        matches = find_matches("budget", SAMPLE_EMAILS)
        assert len(matches) == 1
        assert matches[0]["subject"] == "Q1 Budget Review"

    def test_whitespace_stripped(self):
        matches = find_matches("  alice  ", SAMPLE_EMAILS)
        assert len(matches) == 1

    def test_punctuation_ignored(self):
        matches = find_matches("alice?", SAMPLE_EMAILS)
        assert len(matches) == 1

    def test_multi_word_query(self):
        matches = find_matches("alice budget", SAMPLE_EMAILS)
        assert len(matches) == 1
        assert matches[0]["message_id"] == "msg001"

    def test_multi_word_no_match(self):
        matches = find_matches("alice benefits", SAMPLE_EMAILS)
        assert len(matches) == 0


class TestFormatEmail:
    def test_basic_format(self):
        result = format_email(SAMPLE_EMAILS[0])
        assert "<b>From:</b>" in result
        assert "Alice Smith" in result
        assert "Q1 Budget Review" in result
        assert "Please review" in result

    def test_html_escaping(self):
        email = {
            "sender": "Test <test@example.com>",
            "subject": "A & B <C>",
            "body": "x < y & z",
            "date": "",
            "category": "personal",
        }
        result = format_email(email)
        assert "&lt;test@example.com&gt;" in result
        assert "A &amp; B &lt;C&gt;" in result


class TestFormatMatchList:
    def test_numbered_list(self):
        result = format_match_list(SAMPLE_EMAILS[:2])
        assert "1." in result
        assert "2." in result
        assert "Alice" in result
        assert "Bob" in result


class TestFormatAllSubjects:
    def test_empty(self):
        result = format_all_subjects([])
        assert "No cached emails" in result

    def test_lists_all(self):
        result = format_all_subjects(SAMPLE_EMAILS)
        assert f"({len(SAMPLE_EMAILS)})" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "Newsletter" in result


class TestHandleMessage:
    def setup_method(self):
        self.sent_messages = []
        self.pending = {}

    def _mock_send(self, bot_token, chat_id, text):
        self.sent_messages.append(text)

    @patch("email_digest.bot_responder.load_cached_emails", return_value=SAMPLE_EMAILS)
    @patch("email_digest.bot_responder.send_reply")
    def test_help_command(self, mock_send, mock_load):
        handle_message("help", "token", "123", self.pending)
        mock_send.assert_called_once()
        assert "Email Lookup Bot" in mock_send.call_args[0][2]

    @patch("email_digest.bot_responder.load_cached_emails", return_value=SAMPLE_EMAILS)
    @patch("email_digest.bot_responder.send_reply")
    def test_list_command(self, mock_send, mock_load):
        handle_message("list", "token", "123", self.pending)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][2]
        assert "Alice" in text
        assert "Bob" in text

    @patch("email_digest.bot_responder.load_cached_emails", return_value=SAMPLE_EMAILS)
    @patch("email_digest.bot_responder.send_reply")
    def test_single_match(self, mock_send, mock_load):
        handle_message("alice", "token", "123", self.pending)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][2]
        assert "Q1 Budget Review" in text
        assert "Please review" in text

    @patch("email_digest.bot_responder.load_cached_emails", return_value=SAMPLE_EMAILS)
    @patch("email_digest.bot_responder.send_reply")
    def test_no_match(self, mock_send, mock_load):
        handle_message("zzzzz", "token", "123", self.pending)
        mock_send.assert_called_once()
        assert "No matching email" in mock_send.call_args[0][2]

    @patch("email_digest.bot_responder.load_cached_emails", return_value=SAMPLE_EMAILS)
    @patch("email_digest.bot_responder.send_reply")
    def test_multiple_matches_then_pick(self, mock_send, mock_load):
        # Both have ".com" in sender
        emails_with_common = SAMPLE_EMAILS[:2]
        mock_load.return_value = [
            {**SAMPLE_EMAILS[0], "subject": "Review Meeting"},
            {**SAMPLE_EMAILS[1], "subject": "Review Budget"},
        ]
        handle_message("review", "token", "123", self.pending)
        text = mock_send.call_args[0][2]
        assert "Multiple matches" in text
        assert "123" in self.pending

        # Now pick number 1
        mock_send.reset_mock()
        handle_message("1", "token", "123", self.pending)
        text = mock_send.call_args[0][2]
        assert "Review Meeting" in text
        assert "123" not in self.pending  # cleared after selection


class TestLoadCachedEmails:
    def test_loads_from_cache_dir(self, tmp_path):
        from datetime import date, timedelta
        today = date.today()
        cache_file = tmp_path / f"{today.isoformat()}.json"
        cache_file.write_text(json.dumps(SAMPLE_EMAILS[:1]))

        with patch("email_digest.bot_responder.CACHE_DIR", tmp_path):
            result = load_cached_emails()
        assert len(result) == 1
        assert result[0]["sender"] == "Alice Smith <alice@example.com>"

    def test_skips_old_files(self, tmp_path):
        from datetime import date, timedelta
        old_date = date.today() - timedelta(days=5)
        cache_file = tmp_path / f"{old_date.isoformat()}.json"
        cache_file.write_text(json.dumps(SAMPLE_EMAILS[:1]))

        with patch("email_digest.bot_responder.CACHE_DIR", tmp_path):
            result = load_cached_emails()
        assert len(result) == 0

    def test_missing_dir(self, tmp_path):
        with patch("email_digest.bot_responder.CACHE_DIR", tmp_path / "nope"):
            result = load_cached_emails()
        assert result == []


class TestNormalize:
    def test_strips_punctuation(self):
        assert _normalize("Napkin AI?") == "napkin ai"

    def test_collapses_whitespace(self):
        assert _normalize("  hello   world  ") == "hello world"

    def test_lowercases(self):
        assert _normalize("Alice Smith") == "alice smith"


class TestEscape:
    def test_escapes_html(self):
        assert _escape("<b>test&</b>") == "&lt;b&gt;test&amp;&lt;/b&gt;"
