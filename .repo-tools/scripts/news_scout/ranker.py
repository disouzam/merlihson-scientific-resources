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


RANKER_SYSTEM = """You are a sharp PR strategist picking AI stories for a journalist's morning brief. You score stories on whether they would energize a TV producer, op-ed writer, or social-media editor — not on whether they would "inform" a general viewer. Boring-but-important loses to spicy-but-real every time."""


RANKER_PROMPT = """Below is a JSON array of candidate AI stories. Score each 0-100 on how COMPELLING it would be as raw material for a piece (post, op-ed, TV segment, radio bit) aimed at an Israeli audience.

SCORE HIGHER when the story has any of:
- A NAMED CHARACTER in a moment — Altman fired, Musk sues, Pichai breaks down, founder accused. Not "company X announces".
- COUNTERINTUITIVE or SURPRISING CLAIM — something that makes a reader pause, even briefly.
- CONCRETE CONSEQUENCE with numbers and names — "8,000 jobs cut at HSBC", not "banks adjusting workforce".
- VISUAL HOOK — a face, a leaked image, a deepfake, an exhibit, a viral video.
- ISRAELI PAIN OR PRIDE — anything connecting AI to Israeli security, talent, victims, exporters, competitors.
- RUNNING DRAMA or CONTROVERSY — a chapter in an unfolding saga people are already watching (OpenAI palace intrigue, X vs ChatGPT, copyright lawsuits, deepfake-in-election).
- HUMAN COST or ETHICAL EDGE — a person hurt, a child manipulated, a profession threatened, a moral line crossed.
- BIG-MONEY MOMENT with a specific name — "Anthropic raises $5B", "Nvidia loses $400B in a day".
- A QUOTE that could be the headline — boss said something punchable, regulator said something pointed.

SCORE LOWER (or zero) when the story is:
- An incremental product update ("X adds Y feature", "V4 launches"), unless paired with one of the above.
- Day-3 follow-up commentary on a story that already broke.
- A research paper, benchmark, architecture detail, fine-tuning trick, ablation, or model-card minutiae.
- A small developer-tooling release.
- A funding round below ~$500M with no broader narrative.
- Generic policy-speak ("we should be thoughtful about AI...") without a concrete actor or action.
- A press release dressed as news.

INTERESTING beats IMPORTANT. A vivid third-tier story beats a worthy first-tier story for this digest's purpose.

Each item carries a `source_count` field: how many distinct outlets ran this same story. Treat **source_count >= 2 as a strong "real story" signal — add 8-15 points**. Single-source items with no other hooks should be questioned.

Output ONLY a JSON array of objects, in the SAME ORDER as the input, like:
[
  {{"i": 0, "score": 78, "reason_he": "סיבה תמציתית בעברית במשפט אחד"}},
  {{"i": 1, "score": 25, "reason_he": "..."}},
  ...
]

The reason_he must be a single short Hebrew sentence (no more than 18 words), explaining WHY this would energize a journalist.

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
            "source_count": item.source_count,  # multi-source aggregation signal
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
