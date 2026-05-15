"""Smoke tests for fetcher's pure helpers (no network)."""

from datetime import datetime, timezone

from news_scout.fetcher import NewsItem, _dedup, _is_ai_related, _strip_html


def make(title: str, url: str) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="test",
        summary="",
        published=datetime.now(timezone.utc),
    )


def test_dedup_collapses_same_url():
    items = [make("A", "https://x.com/1"), make("B", "https://x.com/1")]
    assert len(_dedup(items)) == 1


def test_dedup_collapses_same_normalized_title():
    # Same title, different casing/punctuation, different URLs
    items = [
        make("OpenAI Launches GPT-5!", "https://a.com/1"),
        make("openai launches gpt-5", "https://b.com/2"),
    ]
    assert len(_dedup(items)) == 1


def test_dedup_keeps_distinct():
    items = [
        make("OpenAI launches GPT-5", "https://a.com/1"),
        make("Anthropic releases Claude Opus 4.7", "https://b.com/2"),
    ]
    assert len(_dedup(items)) == 2


def test_ai_keyword_detection():
    assert _is_ai_related("Apple unveils new ChatGPT-style assistant", "")
    assert _is_ai_related("", "Anthropic released Claude Opus")
    assert not _is_ai_related("Apple unveils new MacBook Pro", "Bigger battery, faster M5 chip")


def test_strip_html():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello  world"
    assert _strip_html(None or "") == ""


def test_item_id_is_stable():
    a = make("title", "https://example.com/x")
    b = make("title", "https://example.com/x")
    assert a.item_id == b.item_id


if __name__ == "__main__":
    test_dedup_collapses_same_url()
    test_dedup_collapses_same_normalized_title()
    test_dedup_keeps_distinct()
    test_ai_keyword_detection()
    test_strip_html()
    test_item_id_is_stable()
    print("OK — all fetcher tests passed")
