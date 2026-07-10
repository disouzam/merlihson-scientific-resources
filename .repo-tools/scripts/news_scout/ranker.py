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
    story: str = ""     # LLM-assigned slug grouping items about the same real-world event


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

GROUP DUPLICATES: Several candidates often report the SAME real-world event under different headlines or outlets (e.g. five items about one executive resigning, or one model launch covered by five outlets). Assign every item a short lowercase-hyphenated `story` slug naming its underlying event (actor + action), so all items about the SAME event share the SAME slug and different events get different slugs.
- "Same event" = same primary actor + same action/consequence. NOT merely "same company" or "same day": "OpenAI launches GPT-5.6" and "OpenAI's CFO resigns" are DIFFERENT events (different slugs) even on the same day. Different framings of the identical fact — the launch vs. the stock reaction vs. analysis of that launch — are ONE event (same slug).
- When unsure whether two items are the same event, give them DIFFERENT slugs.
Score every item on its own merit (source_count boost included) — do NOT zero anything. The system automatically keeps only the single best-scored item per slug, so you never drop or omit an item.

Each item carries a `source_count` field: how many distinct outlets ran this same story. Treat **source_count >= 2 as a strong "real story" signal — add 8-15 points to THAT item's score**. Single-source items with no other hooks should be questioned.

Output ONLY a JSON array with ONE object for EVERY input item, in the SAME ORDER as the input — never omit an item. Like:
[
  {{"i": 0, "score": 78, "story": "openai-fidji-simo-departure", "reason_he": "סיבה תמציתית בעברית במשפט אחד"}},
  {{"i": 1, "score": 25, "story": "meta-ai-chip-production", "reason_he": "..."}},
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
            "story": str(entry.get("story", "")).strip().lower(),
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
        RankedItem(item=items[s["i"]], score=s["score"], reason=s["reason_he"], story=s["story"])
        for s in scores
    ]
    ranked.sort(key=lambda r: r.score, reverse=True)

    # Drop anything below a reasonable floor for general-public relevance
    ranked = [r for r in ranked if r.score >= 40]

    return _dedupe_by_story(ranked, top_n)


def _dedupe_by_story(ranked: List[RankedItem], top_n: int) -> List[RankedItem]:
    """Keep one item per real-world event, non-destructively (selection, never
    zeroing). Two layers: (1) the LLM's semantic `story` slug — catches reworded /
    cross-language / name-variant duplicates; (2) a lexical backstop on titles —
    catches events the model failed to group. Assumes `ranked` is score-desc."""
    selected: List[RankedItem] = []
    seen_slugs: set = set()
    for r in ranked:
        slug = (r.story or "").strip().lower()
        if slug and slug in seen_slugs:
            continue  # same event per the model
        if any(_same_story(r.item.title, s.item.title) for s in selected):
            continue  # same event per titles (backstop)
        if slug:
            seen_slugs.add(slug)
        selected.append(r)
        if len(selected) >= top_n:
            break
    return selected


# Tokens too common to signal "same story": grammar words, the big lab/company
# names (they appear across unrelated AI items), and generic news verbs/nouns that
# otherwise cause false merges ("Musk sues X" vs "Musk sues Y", "Amazon cuts jobs"
# vs "IBM cuts jobs"). This backstop is intentionally conservative — the LLM `story`
# slug is the primary, semantic dedup; missed lexical dups fall to it.
_STORY_STOP = {
    # grammar / filler
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are",
    "as", "its", "it", "after", "from", "by", "new", "says", "say", "said", "amid",
    "over", "into", "that", "this", "at", "he", "she", "his", "her", "will", "has",
    "have", "was", "were", "but", "not", "no", "up", "out", "who", "why", "how", "what",
    # big labs / companies (too common to be identity on their own)
    "openai", "google", "meta", "microsoft", "apple", "amazon", "nvidia", "anthropic",
    "chatgpt", "tech", "company", "companies", "startup", "report", "launch", "launches",
    "launched", "unveils", "announces", "model", "models", "amp",
    # generic news verbs / nouns (would false-merge distinct stories)
    "sues", "sue", "cuts", "cut", "jobs", "job", "goes", "hits", "hit", "takes", "take",
    "sees", "beats", "tops", "chips", "chip", "ban", "bans", "roles", "role", "deal",
    "deals", "adds", "gets", "set", "plans", "plan", "eyes",
}

# Keep alphanumeric identifiers whole (e.g. "gpt-5.6", "gpt-4o", "claude-3.7") instead
# of shredding them into "gpt","5","6" — that both missed same-version dups and merged
# unrelated versions ("gpt-5.6" vs "gpt-4.1" both -> "gpt").
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def _distinctive_tokens(title: str) -> set:
    out = set()
    for t in _TOKEN_RE.findall(title.lower()):
        if t in _STORY_STOP:
            continue
        if not any(c.isalpha() for c in t):
            continue  # drop pure-number tokens ("14", "000", "5") — kills the 14,000->000 bug
        if len(t) <= 2 and not any(c.isdigit() for c in t):
            continue  # drop tiny non-versioned tokens ("no", "ai")
        out.add(t)
    return out


def _same_story(a: str, b: str) -> bool:
    """Two headlines describe the same event if they share >= 2 distinctive tokens
    (e.g. a person's first+last name). Conservative on purpose: sharing a single
    token — even a whole model name — is NOT enough (the LLM story slug covers the
    rest), which avoids false merges like "OpenAI unveils Sora" vs "Sora Ventures"."""
    ta, tb = _distinctive_tokens(a), _distinctive_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) >= 2
