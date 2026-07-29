"""Build the Markdown digest (full) and a short Telegram version."""

from __future__ import annotations

from datetime import datetime, timezone

BUCKET_TITLES = {
    "core": "🎯 Core — CL-relevant, depth-first",
    "emerging": "🌱 Emerging — early / near-but-unnamed (lower confidence)",
    "viral": "🔥 Viral — loud right now, weakly related",
}


def _why(item: dict) -> str:
    hits = item["topic_hits"]
    parts = []
    if hits["core"]:
        parts.append("core: " + ", ".join(hits["core"][:3]))
    if hits["emerging"]:
        parts.append("emerging: " + ", ".join(hits["emerging"][:3]))
    if hits["adjacent"]:
        parts.append("adj: " + ", ".join(hits["adjacent"][:3]))
    return "; ".join(parts)


def _metrics_str(item: dict) -> str:
    m = item.get("metrics", {})
    bits = [f"{v} {k}" for k, v in m.items() if v]
    if item.get("velocity"):
        bits.append(f"vel {item['velocity']}")
    return " · ".join(bits)


def build_markdown(buckets: dict, people: dict, stats: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# CL Tracker digest",
        f"*{now} · scanned {stats['fetched']} items from {stats['sources']} sources · "
        f"{stats['kept']} passed the topic gate*",
        "",
    ]
    for bucket, title in BUCKET_TITLES.items():
        items = buckets.get(bucket, [])
        lines.append(f"## {title}")
        if not items:
            lines.append("*(nothing this run)*")
        for i, item in enumerate(items, 1):
            src = item["source"].replace("blog:", "")
            date = (item["ts"] or "")[:10]
            lines.append(f"**{i}. [{item['title']}]({item['url']})**  ")
            meta = f"   {src} · {date}"
            metrics = _metrics_str(item)
            if metrics:
                meta += f" · {metrics}"
            lines.append(meta + "  ")
            lines.append(f"   *why:* {_why(item)} · score {item['score']}")
            if item["kind"] == "paper" and item["summary"]:
                lines.append(f"   > {item['summary'][:280]}…")
            lines.append("")
        lines.append("")

    lines.append("## 👤 People — recurring authors this run")
    if people.get("rising"):
        for p in people["rising"]:
            lines.append(f"- **{p['name']}** ({p['count']} items) — e.g. [{p['example']}]({p['url']})")
    else:
        lines.append("*(no recurring authors this run)*")
    lines.append("")
    return "\n".join(lines)


def build_telegram(buckets: dict, stats: dict) -> str:
    """Short plain-text version for Telegram (top items only)."""
    lines = [f"📡 CL Tracker — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
             f"({stats['kept']} relevant / {stats['fetched']} scanned)", ""]
    caps = {"core": 5, "emerging": 3, "viral": 3}
    labels = {"core": "🎯 Core", "emerging": "🌱 Emerging", "viral": "🔥 Viral"}
    for bucket in ("core", "emerging", "viral"):
        items = buckets.get(bucket, [])[: caps[bucket]]
        if not items:
            continue
        lines.append(labels[bucket] + ":")
        for item in items:
            lines.append(f"• {item['title']}\n  {item['url']}")
        lines.append("")
    return "\n".join(lines).strip()
