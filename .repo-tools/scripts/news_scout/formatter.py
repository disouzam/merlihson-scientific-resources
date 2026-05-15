"""Generate the Hebrew Telegram digest from the top-ranked items.

For each item we ask Claude to write:
  - A short Hebrew headline (RTL)
  - 1-2 sentence Hebrew teaser (general-audience tone)
  - One-line 'why this matters for Israeli media' angle

Then we lay them out as plain-text/HTML message for Telegram.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List

import anthropic

from .ranker import RankedItem


@dataclass
class FormattedItem:
    headline_he: str
    teaser_he: str
    angle_he: str        # why an Israeli journalist should care
    source: str
    url: str


FORMATTER_PROMPT = """Below is a JSON array of AI/tech news items selected for an Israeli general-public audience.
For EACH item produce: a Hebrew headline, a 1-2 sentence Hebrew teaser, and a one-line "Israeli angle" (also in Hebrew) explaining why this is worth a TV mention / op-ed / radio segment for an Israeli audience.

REQUIREMENTS:
- Write everything in fluent, natural Hebrew (no transliteration unless the term is genuinely untranslatable).
- Translate company / product names that have established Hebrew forms; keep recognizable brand names in Latin script (e.g., OpenAI, ChatGPT).
- Tone: serious news, accessible, NO hype, NO emoji.
- Headline: max 12 words.
- Teaser: 1-2 sentences, max 45 words total. Include the WHAT and WHY in plain language.
- Angle: a single sentence, max 20 words, framed for an Israeli editor.
- Do NOT include the source URL in any field.

Output ONLY a JSON array, same order as input:
[
  {{"i": 0, "headline_he": "...", "teaser_he": "...", "angle_he": "..."}},
  ...
]

Items:
{items_json}
"""


def _serialize(items: List[RankedItem]) -> str:
    payload = [
        {
            "i": idx,
            "title_en": r.item.title,
            "summary_en": r.item.summary[:500],
            "source": r.item.source,
        }
        for idx, r in enumerate(items)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_formatted(text: str, n: int) -> List[dict]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("formatter: no JSON array in response")
    arr = json.loads(text[start : end + 1])
    if not isinstance(arr, list):
        raise ValueError("formatter: top-level is not an array")
    out: List[dict] = []
    seen = set()
    for entry in arr:
        i = int(entry.get("i", -1))
        if i < 0 or i >= n or i in seen:
            continue
        seen.add(i)
        out.append({
            "i": i,
            "headline_he": str(entry.get("headline_he", "")).strip(),
            "teaser_he": str(entry.get("teaser_he", "")).strip(),
            "angle_he": str(entry.get("angle_he", "")).strip(),
        })
    return out


def format_items(
    ranked: List[RankedItem],
    api_key: str,
    model: str,
) -> List[FormattedItem]:
    if not ranked:
        return []

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": FORMATTER_PROMPT.format(items_json=_serialize(ranked))}],
    )

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    rows = _parse_formatted(text, len(ranked))
    # Re-align to original order
    by_i = {r["i"]: r for r in rows}

    formatted: List[FormattedItem] = []
    for idx, r in enumerate(ranked):
        row = by_i.get(idx)
        if not row:
            continue
        formatted.append(FormattedItem(
            headline_he=row["headline_he"],
            teaser_he=row["teaser_he"],
            angle_he=row["angle_he"],
            source=r.item.source,
            url=r.item.url,
        ))
    return formatted


def build_telegram_message(formatted: List[FormattedItem], today: datetime) -> str:
    """Build the final Telegram message body (HTML mode)."""
    date_str = today.strftime("%d/%m/%Y")
    header = (
        f"<b>חדשות AI שטרם סוקרו בעברית — {date_str}</b>\n"
        f"מבחר של {len(formatted)} סיפורים שפורסמו השעות האחרונות במקורות בעולם "
        f"ועדיין לא הגיעו לתקשורת הישראלית.\n"
    )
    blocks: List[str] = [header]
    for i, fi in enumerate(formatted, 1):
        block = (
            f"\n<b>{i}. {_escape(fi.headline_he)}</b>\n"
            f"{_escape(fi.teaser_he)}\n"
            f"<i>זווית ישראלית:</i> {_escape(fi.angle_he)}\n"
            f"<i>מקור:</i> {_escape(fi.source)} — <a href=\"{fi.url}\">קישור</a>"
        )
        blocks.append(block)
    return "\n".join(blocks)


def _escape(text: str) -> str:
    # Telegram HTML mode requires escaping <, >, &
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )
