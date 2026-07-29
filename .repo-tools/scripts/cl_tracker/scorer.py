"""Score + bucket normalized items.

Track A (depth-first): topic relevance from the taxonomy -> `core` bucket.
Emerging: weak-but-real topic signal on fresh, low-visibility papers -> `emerging`.
Track B (viral-but-weakly-related): weak topic hit + high velocity -> `viral`.

Deterministic (no LLM) in Phase 1 — cheap, reproducible, debuggable.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

CORE_W, ADJ_W, EMERG_W = 3.0, 1.5, 2.0

# kind -> depth multiplier (papers/repos > blogs > forum posts)
DEPTH = {"paper": 1.5, "repo": 1.3, "blog": 1.2, "post": 1.0}


def _hits(text: str, phrases: list[str]) -> list[str]:
    found = []
    for p in phrases:
        # word-boundary match so "lora" doesn't hit "explore"
        if re.search(rf"(?<![a-z0-9]){re.escape(p.lower())}(?![a-z0-9])", text):
            found.append(p)
    return found


def _age_hours(ts: str | None) -> float:
    if not ts:
        return 72.0  # unknown age -> neutral-ish
    try:
        dt = datetime.fromisoformat(ts)
        return max(0.5, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
    except ValueError:
        return 72.0


def _velocity(item: dict) -> float:
    """Engagement per hour, log-scaled. 0 for sources without metrics."""
    m = item.get("metrics", {})
    engagement = (m.get("points", 0) + m.get("comments", 0) * 2
                  + m.get("upvotes", 0) + m.get("stars", 0) * 0.2)
    if engagement <= 0:
        return 0.0
    return math.log1p(engagement) / math.log1p(_age_hours(item["ts"]))


def score_items(items: list[dict], topics: dict, tier_weights: dict) -> list[dict]:
    """Annotate each item with topic hits, scores, and a bucket (or None)."""
    seen_titles: set[str] = set()
    scored = []
    for item in items:
        # dedupe on normalized title
        key = re.sub(r"\W+", "", item["title"].lower())[:80]
        if not key or key in seen_titles:
            continue
        seen_titles.add(key)

        text = f"{item['title']} {item['summary']}".lower()
        core = _hits(text, topics["core"])
        adj = _hits(text, topics["adjacent"])
        emerg = _hits(text, topics["emerging_framings"])

        topic_score = CORE_W * len(core) + ADJ_W * len(adj) + EMERG_W * len(emerg)
        if topic_score == 0:
            continue  # hard topic gate — nothing fully off-topic gets in

        tier = item.get("feed_tier")
        tier_mult = tier_weights.get(tier, 1.0) if tier else 1.0
        depth = DEPTH.get(item["kind"], 1.0)
        vel = _velocity(item)
        freshness = 1.0 / math.log1p(_age_hours(item["ts"]) / 24 + 1)

        item["topic_hits"] = {"core": core, "adjacent": adj, "emerging": emerg}
        item["topic_score"] = round(topic_score, 2)
        item["velocity"] = round(vel, 2)
        item["score"] = round(topic_score * tier_mult * depth * (1 + 0.5 * vel) * (0.5 + freshness), 2)

        # ---- bucket assignment ----
        m = item.get("metrics", {})
        low_visibility = (m.get("citations", 0) < 5 and m.get("points", 0) < 20
                          and m.get("upvotes", 0) < 20)
        # A repo with almost no stars isn't core-worthy however on-topic its
        # name is — dampen it and route to emerging at best.
        tiny_repo = item["kind"] == "repo" and m.get("stars", 0) < 15
        if tiny_repo:
            item["score"] = round(item["score"] * 0.4, 2)
        if core and not tiny_repo:
            item["bucket"] = "core"
        elif core and tiny_repo:
            item["bucket"] = "emerging"
        elif emerg and item["kind"] == "paper" and low_visibility and _age_hours(item["ts"]) < 21 * 24:
            item["bucket"] = "emerging"     # early: unnamed-but-near, fresh, not yet visible
        elif vel >= 1.0 and (adj or emerg):
            item["bucket"] = "viral"        # loud + weakly related
        elif emerg:
            item["bucket"] = "emerging"
        else:
            item["bucket"] = "core" if item["score"] >= 6 else None  # strong adjacent-only
        if item["bucket"]:
            scored.append(item)
    return scored


def bucketize(scored: list[dict], caps: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"core": [], "emerging": [], "viral": []}
    for item in scored:
        out[item["bucket"]].append(item)
    out["core"].sort(key=lambda i: -i["score"])
    out["emerging"].sort(key=lambda i: (-i["topic_score"], _age_hours(i["ts"])))
    out["viral"].sort(key=lambda i: -i["velocity"])
    return {b: lst[: caps.get(b, 10)] for b, lst in out.items()}


def extract_people(scored: list[dict], top_n: int = 12) -> dict:
    """Early people-tracker: recurring + notable authors across scored items."""
    counts: Counter = Counter()
    example: dict[str, dict] = {}
    for item in scored:
        if item["kind"] not in ("paper", "blog"):
            continue
        for name in item["authors"]:
            name = name.strip()
            if not name or len(name) < 4:
                continue
            counts[name] += 1
            best = example.get(name)
            if not best or item["score"] > best["score"]:
                example[name] = item
    rising = [{"name": n, "count": c, "example": example[n]["title"], "url": example[n]["url"]}
              for n, c in counts.most_common(top_n) if c >= 2]
    return {"rising": rising}
