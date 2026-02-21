"""Use Claude Haiku to rank papers by relevance to Mike's interests."""

import json
import re
from dataclasses import dataclass
from typing import List

import anthropic

from .arxiv_fetcher import ArxivPaper


@dataclass
class RankedPaper:
    paper: ArxivPaper
    score: float
    reason: str


def rank_papers(
    papers: List[ArxivPaper],
    interest_profile: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
    top_k: int = 10,
    batch_size: int = 25,
) -> List[RankedPaper]:
    """Rank papers using Claude Haiku and return top_k most relevant.

    Papers are sent in batches to stay within context limits.
    Each batch returns scored papers; final results are merged and sorted.
    """
    client = anthropic.Anthropic(api_key=api_key)
    all_scored: List[RankedPaper] = []

    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        scored = _rank_batch(client, model, batch, interest_profile)
        all_scored.extend(scored)

    # Sort by score descending, return top_k
    all_scored.sort(key=lambda x: x.score, reverse=True)
    return all_scored[:top_k]


def _rank_batch(
    client: anthropic.Anthropic,
    model: str,
    papers: List[ArxivPaper],
    interest_profile: str,
) -> List[RankedPaper]:
    """Score a batch of papers using the LLM."""

    papers_text = ""
    for idx, p in enumerate(papers):
        papers_text += f"\n[{idx}] {p.title}\nAbstract: {p.abstract[:500]}\n"

    prompt = f"""You are a research paper recommender. Score each paper for relevance to Mike's interests.

{interest_profile}

---

Papers to score:

{papers_text}

---

For each paper, output a JSON array with objects having these fields:
- "index": the paper index number
- "score": relevance score from 1-10 (10 = perfect match)
- "reason": one brief sentence explaining why Mike would or wouldn't find this interesting

Output ONLY the JSON array, no other text."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()
    scored = _parse_scores(response_text, papers)
    return scored


def _parse_scores(response_text: str, papers: List[ArxivPaper]) -> List[RankedPaper]:
    """Parse the LLM's JSON response into RankedPaper objects."""
    # Extract JSON array from response (handle markdown code blocks)
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if not json_match:
        return []

    try:
        scores = json.loads(json_match.group())
    except json.JSONDecodeError:
        return []

    results = []
    for entry in scores:
        try:
            idx = int(entry["index"])
            if 0 <= idx < len(papers):
                results.append(RankedPaper(
                    paper=papers[idx],
                    score=float(entry.get("score", 0)),
                    reason=str(entry.get("reason", "")),
                ))
        except (KeyError, ValueError, IndexError):
            continue

    return results
