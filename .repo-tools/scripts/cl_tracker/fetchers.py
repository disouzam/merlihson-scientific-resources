"""Fetchers for all CL-tracker sources. Each returns a list of normalized items:

    {id, source, kind, title, url, summary, authors[], ts (iso or None),
     metrics {points, comments, stars, citations, upvotes}, feed_tier}

Every fetcher fails soft (logs + returns []) so one dead source never kills a run.
Note: Papers-with-Code was sunset in 2025 — HF Daily Papers replaces it.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests

UA = {"User-Agent": "cl-tracker/0.1 (research digest; contact: erlihson@gmail.com)"}
TIMEOUT = 30


def _log(msg: str) -> None:
    print(f"[fetch] {msg}", flush=True)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def _item(source: str, kind: str, title: str, url: str, summary: str = "",
          authors: Optional[list] = None, ts: Optional[str] = None,
          metrics: Optional[dict] = None, feed_tier: Optional[int] = None) -> dict:
    return {
        "id": f"{source}:{url}",
        "source": source,
        "kind": kind,          # paper | post | repo | blog
        "title": title.strip(),
        "url": url,
        "summary": (summary or "")[:2000],
        "authors": authors or [],
        "ts": ts,
        "metrics": metrics or {},
        "feed_tier": feed_tier,
    }


# ---------------------------------------------------------------- arXiv

ARXIV_API = "http://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


def fetch_arxiv(phrases: list[str], lookback_hours: int, max_results: int = 150) -> list[dict]:
    """Query arXiv for recent papers matching any of the given phrases."""
    # arXiv query: (all:"phrase1" OR all:"phrase2" ...) AND cat filter
    quoted = " OR ".join(f'all:"{p}"' for p in phrases)
    query = f"({quoted}) AND (cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.AI OR cat:cs.NE)"
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    try:
        resp = requests.get(ARXIV_API, params=params, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        _log(f"arxiv failed: {exc}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items = []
    for entry in root.iter(f"{_ATOM}entry"):
        try:
            published = datetime.fromisoformat(entry.findtext(f"{_ATOM}published").replace("Z", "+00:00"))
            if published < cutoff:
                continue
            title = " ".join(entry.findtext(f"{_ATOM}title", "").split())
            url = next((l.get("href") for l in entry.iter(f"{_ATOM}link")
                        if l.get("type") == "text/html"), entry.findtext(f"{_ATOM}id", ""))
            summary = " ".join(entry.findtext(f"{_ATOM}summary", "").split())
            authors = [a.findtext(f"{_ATOM}name", "") for a in entry.iter(f"{_ATOM}author")]
            items.append(_item("arxiv", "paper", title, url, summary, authors, _iso(published)))
        except Exception:
            continue
    _log(f"arxiv: {len(items)} recent papers")
    return items


# ---------------------------------------------------- Semantic Scholar

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"


def fetch_semantic_scholar(queries: list[str], lookback_hours: int) -> list[dict]:
    """Recent papers per query via Semantic Scholar (unauth, rate-limited)."""
    year = datetime.now(timezone.utc).year
    items = []
    for q in queries:
        try:
            resp = None
            for attempt in range(3):  # retry through 429s — unauth quota is tight
                resp = requests.get(S2_API, params={
                    "query": q,
                    "fields": "title,abstract,url,year,citationCount,authors,publicationDate",
                    "year": f"{year - 1}-{year}",
                    "limit": 25,
                }, headers=UA, timeout=TIMEOUT)
                if resp.status_code != 429:
                    break
                _log(f"s2 rate-limited on '{q}', backing off {10 * (attempt + 1)}s")
                time.sleep(10 * (attempt + 1))
            if resp is None or resp.status_code == 429:
                continue
            resp.raise_for_status()
            for p in resp.json().get("data", []):
                ts = None
                if p.get("publicationDate"):
                    try:
                        ts = _iso(datetime.fromisoformat(p["publicationDate"]).replace(tzinfo=timezone.utc))
                    except ValueError:
                        pass
                items.append(_item(
                    "semantic_scholar", "paper", p.get("title", ""), p.get("url", ""),
                    p.get("abstract") or "",
                    [a.get("name", "") for a in (p.get("authors") or [])],
                    ts, {"citations": p.get("citationCount", 0)},
                ))
            time.sleep(1.5)  # be polite, unauth quota is tight
        except Exception as exc:
            _log(f"s2 '{q}' failed: {exc}")
    _log(f"semantic_scholar: {len(items)} papers")
    return items


# ---------------------------------------------------------- OpenReview

OR_API = "https://api2.openreview.net/notes/search"


def fetch_openreview(queries: list[str]) -> list[dict]:
    items = []
    for q in queries:
        try:
            resp = requests.get(OR_API, params={"query": q, "limit": 20},
                                headers=UA, timeout=TIMEOUT)
            resp.raise_for_status()
            for note in resp.json().get("notes", []):
                content = note.get("content", {})

                def _val(key):
                    v = content.get(key, "")
                    return v.get("value", "") if isinstance(v, dict) else v

                title = _val("title")
                if not title:
                    continue
                ts = None
                if note.get("pdate") or note.get("cdate"):
                    ts = _iso(datetime.fromtimestamp((note.get("pdate") or note["cdate"]) / 1000, tz=timezone.utc))
                items.append(_item(
                    "openreview", "paper", title,
                    f"https://openreview.net/forum?id={note.get('forum', note.get('id', ''))}",
                    _val("abstract"), [], ts,
                ))
        except Exception as exc:
            _log(f"openreview '{q}' failed: {exc}")
    _log(f"openreview: {len(items)} notes")
    return items


# --------------------------------------------------------- HN (Algolia)

HN_API = "https://hn.algolia.com/api/v1/search_by_date"


def fetch_hn(queries: list[str], lookback_hours: int) -> list[dict]:
    since = int(time.time()) - lookback_hours * 3600
    items = []
    for q in queries:
        try:
            resp = requests.get(HN_API, params={
                "query": q, "tags": "story",
                "numericFilters": f"created_at_i>{since}",
                "hitsPerPage": 30,
            }, headers=UA, timeout=TIMEOUT)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                title = hit.get("title") or ""
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                items.append(_item(
                    "hackernews", "post", title, url, hit.get("story_text") or "",
                    [hit.get("author", "")],
                    _iso(datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)),
                    {"points": hit.get("points") or 0, "comments": hit.get("num_comments") or 0},
                ))
        except Exception as exc:
            _log(f"hn '{q}' failed: {exc}")
    _log(f"hackernews: {len(items)} stories")
    return items


# -------------------------------------------------------------- Reddit

SUBREDDITS = ["MachineLearning", "LocalLLaMA"]


def fetch_reddit(lookback_hours: int) -> list[dict]:
    cutoff = time.time() - lookback_hours * 3600
    items = []
    for sub in SUBREDDITS:
        try:
            resp = requests.get(f"https://www.reddit.com/r/{sub}/new.json",
                                params={"limit": 100}, headers=UA, timeout=TIMEOUT)
            resp.raise_for_status()
            for child in resp.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                if d.get("created_utc", 0) < cutoff:
                    continue
                items.append(_item(
                    "reddit", "post", d.get("title", ""),
                    f"https://www.reddit.com{d.get('permalink', '')}",
                    d.get("selftext", "")[:2000], [d.get("author", "")],
                    _iso(datetime.fromtimestamp(d["created_utc"], tz=timezone.utc)),
                    {"points": d.get("score", 0), "comments": d.get("num_comments", 0)},
                ))
        except Exception as exc:
            _log(f"reddit r/{sub} failed: {exc}")
    _log(f"reddit: {len(items)} posts")
    return items


# -------------------------------------------------------------- GitHub

GH_API = "https://api.github.com/search/repositories"


def fetch_github(queries: list[str], lookback_hours: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours * 4)).date()  # wider window; repos move slower
    items = []
    for q in queries[:3]:  # unauth quota: 10 req/min
        try:
            resp = requests.get(GH_API, params={
                "q": f'"{q}" pushed:>{since}', "sort": "updated", "per_page": 15,
            }, headers={**UA, "Accept": "application/vnd.github+json"}, timeout=TIMEOUT)
            resp.raise_for_status()
            for repo in resp.json().get("items", []):
                items.append(_item(
                    "github", "repo", repo.get("full_name", ""), repo.get("html_url", ""),
                    repo.get("description") or "", [repo.get("owner", {}).get("login", "")],
                    repo.get("pushed_at"), {"stars": repo.get("stargazers_count", 0)},
                ))
            time.sleep(7)
        except Exception as exc:
            _log(f"github '{q}' failed: {exc}")
    _log(f"github: {len(items)} repos")
    return items


# ------------------------------------------------- HF Daily Papers

HF_API = "https://huggingface.co/api/daily_papers"


def fetch_hf_papers(lookback_hours: int) -> list[dict]:
    try:
        resp = requests.get(HF_API, params={"limit": 100}, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        _log(f"hf_papers failed: {exc}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items = []
    for entry in data:
        try:
            paper = entry.get("paper", {})
            ts_raw = entry.get("publishedAt") or paper.get("publishedAt")
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
            if ts and ts < cutoff:
                continue
            items.append(_item(
                "hf_papers", "paper", paper.get("title", ""),
                f"https://huggingface.co/papers/{paper.get('id', '')}",
                paper.get("summary", ""),
                [a.get("name", "") for a in (paper.get("authors") or [])],
                _iso(ts), {"upvotes": paper.get("upvotes", 0)},
            ))
        except Exception:
            continue
    _log(f"hf_papers: {len(items)} papers")
    return items


# ----------------------------------------------------------- RSS feeds

def fetch_rss_feeds(feeds: list[dict], lookback_hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"], request_headers=UA)
            count = 0
            for entry in parsed.entries[:20]:
                ts = None
                for key in ("published_parsed", "updated_parsed"):
                    if entry.get(key):
                        ts = datetime.fromtimestamp(time.mktime(entry[key]), tz=timezone.utc)
                        break
                if ts and ts < cutoff:
                    continue
                summary = entry.get("summary", "") or ""
                # crude de-HTML
                import re
                summary = re.sub(r"<[^>]+>", " ", summary)
                items.append(_item(
                    f"blog:{feed['name']}", "blog", entry.get("title", ""),
                    entry.get("link", ""), summary,
                    [entry.get("author", "")] if entry.get("author") else [],
                    _iso(ts), feed_tier=feed.get("tier"),
                ))
                count += 1
            if count:
                _log(f"rss {feed['name']}: {count} items")
        except Exception as exc:
            _log(f"rss {feed['name']} failed: {exc}")
    _log(f"rss total: {len(items)} items")
    return items
