"""Fetch recent items from curated English-language feeds.

Pipeline:
  1. Pull all RSS feeds in parallel
  2. Drop items older than lookback_hours
  3. Drop items not matching AI keywords (for non-AI-specific feeds)
  4. Dedup by URL + by normalized title
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser

from .sources import AI_KEYWORDS, ENGLISH_SOURCES, EnglishSource

USER_AGENT = "NewsScout/1.0 (+https://github.com/merlihson/scientific-resources)"


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    summary: str
    published: datetime
    item_id: str = field(default="")  # stable hash for dedup

    def __post_init__(self):
        if not self.item_id:
            self.item_id = hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]


def _parse_published(entry) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " ").strip()


# Pre-compile keyword patterns with boundary checks. Naive substring matching
# made "AI" match "said"/"aid"/"again", letting non-AI stories slip through.
# Right boundary is skipped for keywords already ending in a non-alphanumeric
# char (e.g. "GPT-" must still match "GPT-4", "A.I." must still match "A.I.").
_AI_KEYWORD_PATTERNS = [
    re.compile(
        rf'(?<![A-Za-z0-9]){re.escape(kw.lower())}'
        + (r'(?![A-Za-z0-9])' if kw[-1:].isalnum() else '')
    )
    for kw in AI_KEYWORDS
]


def _is_ai_related(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(p.search(blob) for p in _AI_KEYWORD_PATTERNS)


def _fetch_one(source: EnglishSource, cutoff: datetime) -> List[NewsItem]:
    try:
        # feedparser respects this UA when passed via agent kwarg
        parsed = feedparser.parse(source.feed_url, agent=USER_AGENT)
    except Exception as exc:
        print(f"[fetcher] {source.name}: parse error: {exc}")
        return []

    if parsed.bozo and not parsed.entries:
        print(f"[fetcher] {source.name}: feed unreadable ({parsed.get('bozo_exception')})")
        return []

    items: List[NewsItem] = []
    for entry in parsed.entries:
        published = _parse_published(entry)
        if published is None or published < cutoff:
            continue

        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue

        summary = _strip_html(entry.get("summary") or entry.get("description") or "")[:600]

        # Always apply the keyword filter, even on "AI-specific" feeds. Google News
        # site-search for "AI OR artificial intelligence" returns plenty of items
        # that only tangentially mention AI (e.g. Trump/Iran, sports, Ebola) — the
        # is_ai_specific flag is no longer trusted on its own.
        if not _is_ai_related(title, summary):
            continue

        items.append(NewsItem(
            title=title,
            url=url,
            source=source.name,
            summary=summary,
            published=published,
        ))
    return items


def _dedup(items: List[NewsItem]) -> List[NewsItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: List[NewsItem] = []
    for item in items:
        norm_title = re.sub(r"[^\w\s]", "", item.title.lower()).strip()
        norm_title = re.sub(r"\s+", " ", norm_title)
        if item.url in seen_urls or norm_title in seen_titles:
            continue
        seen_urls.add(item.url)
        seen_titles.add(norm_title)
        out.append(item)
    return out


def fetch_recent(lookback_hours: int = 36) -> List[NewsItem]:
    """Fetch all sources in parallel, return AI-relevant items within lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    all_items: List[NewsItem] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one, src, cutoff): src for src in ENGLISH_SOURCES}
        for fut in concurrent.futures.as_completed(futures):
            src = futures[fut]
            try:
                items = fut.result()
                print(f"[fetcher] {src.name}: {len(items)} items")
                all_items.extend(items)
            except Exception as exc:
                print(f"[fetcher] {src.name}: failed ({exc})")

    deduped = _dedup(all_items)
    # Newest first
    deduped.sort(key=lambda i: i.published, reverse=True)
    print(f"[fetcher] total candidates after dedup: {len(deduped)}")
    return deduped
