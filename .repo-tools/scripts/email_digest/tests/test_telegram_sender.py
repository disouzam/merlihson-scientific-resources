"""Tests for telegram_sender module."""

from unittest.mock import patch, MagicMock

from email_digest.config import Settings
from email_digest.telegram_sender import split_message, send_digest


def test_split_message_short():
    text = "Hello world"
    result = split_message(text, 4096)
    assert result == ["Hello world"]


def test_split_message_exact_limit():
    text = "A" * 4096
    result = split_message(text, 4096)
    assert result == [text]


def test_split_message_over_limit():
    para1 = "A" * 2000
    para2 = "B" * 2000
    para3 = "C" * 2000
    text = f"{para1}\n\n{para2}\n\n{para3}"

    result = split_message(text, 4096)
    assert len(result) >= 2
    # Verify no part exceeds limit
    for part in result:
        assert len(part) <= 4096


def test_split_message_preserves_paragraph_boundaries():
    paragraphs = [f"Paragraph {i}: " + "x" * 100 for i in range(20)]
    text = "\n\n".join(paragraphs)

    result = split_message(text, 500)
    assert len(result) > 1

    # Each message should contain complete paragraphs
    for part in result:
        assert "Paragraph" in part


def test_split_message_handles_long_paragraph():
    long_para = "Word. " * 1000  # ~6000 chars, single paragraph
    result = split_message(long_para, 4096)
    assert len(result) >= 2
    for part in result:
        assert len(part) <= 4096


@patch("email_digest.telegram_sender._send_message")
def test_send_digest_single_message(mock_send):
    mock_send.return_value = True
    settings = MagicMock()
    settings.telegram_bot_token = "token"
    settings.telegram_chat_id = "chat_id"

    result = send_digest("Short message", settings)
    assert result is True
    assert mock_send.call_count == 1


@patch("email_digest.telegram_sender._send_message")
def test_send_digest_multi_part(mock_send):
    mock_send.return_value = True
    settings = MagicMock()
    settings.telegram_bot_token = "token"
    settings.telegram_chat_id = "chat_id"

    long_text = "\n\n".join(["A" * 2000 for _ in range(5)])
    result = send_digest(long_text, settings)
    assert result is True
    assert mock_send.call_count > 1


@patch("email_digest.telegram_sender._send_message")
def test_send_digest_failure(mock_send):
    mock_send.return_value = False
    settings = MagicMock()
    settings.telegram_bot_token = "token"
    settings.telegram_chat_id = "chat_id"

    result = send_digest("Test", settings)
    assert result is False
