"""Rank candidate stories by 'interestingness for the Israeli general public'.

Two stages:
  1. Local hard-exclusion filter (regex-style) to drop obvious researcher-only items.
  2. Single Claude call ranks the rest 0-100 against general-public criteria.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List

import anthropic

from .fetcher import NewsItem


@dataclass
class RankedItem:
    item: NewsItem
    score: int          # 0-100
    reason: str         # one-line Hebrew rationale for the top picks


RANKER_SYSTEM = """You are a senior news editor at an Israeli prime-time TV news desk.
You score AI/tech stories on whether they would be interesting and intelligible to a GENERAL Israeli audience — viewers, not engineers."""


RANKER_PROMPT = """Below is a JSON array of candidate AI/tech stories from English-language sources.
For EACH item (by its index), output a score 0-100 reflecting how interesting AND comprehensible it would be to a general Israeli audience watching prime-time TV or reading a popular news site.

SCORE HIGHER when the story:
- Affects ordinary people's jobs, money, privacy, safety, education, or daily life.
- Has a clear human-interest angle, a recognizable company (OpenAI, Google, Meta, NVIDIA, Tesla, xAI, etc.), or a well-known controversy.
- Can be summarized in two sentences without jargon.
- Carries a regulatory / political / geopolitical dimension (Israel, US, EU, China).
- Touches consumer products people already use (ChatGPT, Gemini, Copilot, Sora, etc.).

SCORE LOWER (or zero) when the story is:
- A research paper, benchmark result, architecture detail, fine-tuning trick, ablation, or model-card minutiae.
- A small developer-tooling release or library update.
- A funding round below ~$500M with no broader implication.
- Inside-baseball industry analysis only practitioners would care about.

Output ONLY a JSON array of objects, in the SAME ORDER as the input, like:
[
  {{"i": 0, "score": 78, "reason_he": "סיבה תמציתית בעברית במשפט אחד"}},
  {{"i": 1, "score": 25, "reason_he": "..."}},
  ...
]

The reason_he must be a single short Hebrew sentence (no more than 18 words), explaining why this matters to an Israeli viewer.

Candidates:
{candidates_json}
"""


def _apply_hard_exclusions(items: List[NewsItem], patterns: List[str]) -> List[NewsItem]:
    if not patterns:
        return items
    compiled = [re.compile(re.escape(p), re.IGNORECASE) for p in patterns]
    kept: List[NewsItem] = []
    dropped = 0
    for item in items:
        blob = f"{item.title} {item.summary}"
        if any(rx.search(blob) for rx in compiled):
            dropped += 1
            continue
        kept.append(item)
    if dropped:
        print(f"[ranker] hard-exclusions dropped {dropped}")
    return kept


def _serialize_candidates(items: List[NewsItem]) -> str:
    payload = [
        {
            "i": idx,
            "title": item.title,
            "source": item.source,
            "summary": item.summary[:400],
        }
        for idx, item in enumerate(items)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_scores(text: str, n: int) -> List[dict]:
    # Find the first top-level JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("ranker: no JSON array in response")
    obj = json.loads(text[start : end + 1])
    if not isinstance(obj, list):
        raise ValueError("ranker: top-level is not an array")
    # Normalize and sort by i so the caller gets stable alignment
    out = []
    seen = set()
    for entry in obj:
        i = int(entry.get("i", -1))
        if i < 0 or i >= n or i in seen:
            continue
        seen.add(i)
        out.append({
            "i": i,
            "score": int(entry.get("score", 0)),
            "reason_he": str(entry.get("reason_he", "")).strip(),
        })
    return out


def rank(
    items: List[NewsItem],
    api_key: str,
    model: str,
    top_n: int,
    hard_exclusions: List[str],
) -> List[RankedItem]:
    items = _apply_hard_exclusions(items, hard_exclusions)
    if not items:
        return []

    client = anthropic.Anthropic(api_key=api_key)
    prompt = RANKER_PROMPT.format(candidates_json=_serialize_candidates(items))

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=RANKER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    scores = _parse_scores(text, len(items))

    ranked = [
        RankedItem(item=items[s["i"]], score=s["score"], reason=s["reason_he"])
        for s in scores
    ]
    ranked.sort(key=lambda r: r.score, reverse=True)

    # Drop anything below a reasonable floor for general-public relevance
    ranked = [r for r in ranked if r.score >= 40]

    return ranked[:top_n]
