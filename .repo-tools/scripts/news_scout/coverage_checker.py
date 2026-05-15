"""Check whether each candidate story has been covered in Hebrew on Israeli sites.

Uses Anthropic's web_search tool, which lets Claude run real-time searches.
We constrain searches to the 10 Israeli domains in sources.py.

Default behavior on uncertainty: keep the item (treat as not covered). Better
to occasionally include something already covered than to silently drop news.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass
from typing import List, Optional

import anthropic

from .fetcher import NewsItem
from .sources import ISRAELI_SITE_DOMAINS

# Web search tool spec — restricts Claude's queries to Israeli domains only.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
    "allowed_domains": ISRAELI_SITE_DOMAINS,
}


COVERAGE_PROMPT = """You are checking whether Israeli Hebrew news outlets have already covered a specific AI/tech story.

The story (in English):
TITLE: {title}
SOURCE: {source}
SUMMARY: {summary}

Use the web_search tool to look for Hebrew-language coverage of THIS SPECIFIC story (same event/announcement/finding) on Israeli news sites. The search is already restricted to these domains: {domains}.

Run 1–3 Hebrew-language searches. Useful query patterns:
- Translate key entities/products into Hebrew if relevant (e.g., "OpenAI", "ChatGPT", "אנתרופיק").
- Combine with Hebrew AI terms: "בינה מלאכותית", "מודל שפה", "צ'אטבוט", "סוכן AI".
- Use a 24–48h time hint when supported.

Then output ONLY a single JSON object (no prose, no markdown) on the LAST line of your reply:
{{"covered": <true|false>, "confidence": <"high"|"medium"|"low">, "evidence_url": <string or null>}}

Rules:
- "covered" = true only if you found a Hebrew article on an Israeli site about the SAME event (not just a related background article from days/weeks ago).
- If unsure or searches return nothing relevant, output covered=false with confidence="low".
- evidence_url should be the most relevant Hebrew article URL, or null if none found.
"""


@dataclass
class CoverageVerdict:
    item: NewsItem
    covered: bool
    confidence: str  # "high" | "medium" | "low"
    evidence_url: Optional[str]


def _parse_verdict(text: str) -> Optional[dict]:
    # Try to grab the last JSON-looking object in the reply.
    matches = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    for m in reversed(matches):
        try:
            obj = json.loads(m)
            if "covered" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _check_one(client: anthropic.Anthropic, item: NewsItem, model: str) -> CoverageVerdict:
    prompt = COVERAGE_PROMPT.format(
        title=item.title,
        source=item.source,
        summary=item.summary[:400],
        domains=", ".join(ISRAELI_SITE_DOMAINS),
    )

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        print(f"[coverage] '{item.title[:60]}': API error {exc}; treating as not covered")
        return CoverageVerdict(item, covered=False, confidence="low", evidence_url=None)

    # Concatenate text blocks from the final assistant turn
    text_chunks: List[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_chunks.append(block.text)
    full_text = "\n".join(text_chunks)

    verdict_json = _parse_verdict(full_text)
    if not verdict_json:
        print(f"[coverage] '{item.title[:60]}': no parseable verdict; defaulting to not covered")
        return CoverageVerdict(item, covered=False, confidence="low", evidence_url=None)

    return CoverageVerdict(
        item=item,
        covered=bool(verdict_json.get("covered", False)),
        confidence=str(verdict_json.get("confidence", "low")),
        evidence_url=verdict_json.get("evidence_url"),
    )


def filter_uncovered(
    items: List[NewsItem],
    api_key: str,
    model: str,
    max_check: int = 25,
    max_workers: int = 4,
) -> List[NewsItem]:
    """Return only items NOT yet covered by Israeli Hebrew press.

    Caps at max_check inputs to control cost — caller should pre-rank or trim.
    """
    if not items:
        return []

    client = anthropic.Anthropic(api_key=api_key)
    to_check = items[:max_check]

    verdicts: List[CoverageVerdict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_check_one, client, item, model) for item in to_check]
        for fut in concurrent.futures.as_completed(futures):
            try:
                verdicts.append(fut.result())
            except Exception as exc:
                print(f"[coverage] worker crashed: {exc}")

    # Only drop items we're confident are covered. "low" confidence covered=true → keep.
    uncovered = [
        v.item for v in verdicts
        if not (v.covered and v.confidence in ("high", "medium"))
    ]

    n_covered = len(to_check) - len(uncovered)
    print(f"[coverage] {n_covered}/{len(to_check)} dropped as already-covered in Hebrew")
    # Preserve original ordering (newest first)
    keep = {item.item_id for item in uncovered}
    return [item for item in items if item.item_id in keep]
