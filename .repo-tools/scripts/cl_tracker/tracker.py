"""CL Tracker — Phase 1: listen -> score -> 3-bucket digest.

Usage (from .repo-tools/scripts):
    python3 -m cl_tracker.tracker --dry-run        # fetch+score, print digest, send nothing
    python3 -m cl_tracker.tracker                  # full run: file + Telegram (if enabled)
    python3 -m cl_tracker.tracker --lookback 72    # custom lookback hours
    python3 -m cl_tracker.tracker --force          # ignore last_run ledger
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from . import fetchers, scorer, digest as digest_mod

PKG_DIR = Path(__file__).resolve().parent
CONFIG_FILE = PKG_DIR / "config.yaml"
LAST_RUN = PKG_DIR / "last_run.txt"
DIGEST_DIR = PKG_DIR / "digests"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print digest, send nothing")
    ap.add_argument("--force", action="store_true", help="ignore last_run ledger")
    ap.add_argument("--lookback", type=int, default=None, help="hours to look back")
    args = ap.parse_args()

    cfg = load_yaml(CONFIG_FILE) if CONFIG_FILE.exists() else {}
    topics = load_yaml(PKG_DIR / "topics.yaml")
    feeds_cfg = load_yaml(PKG_DIR / "feeds.yaml")

    if not args.force and not args.dry_run and LAST_RUN.exists() \
            and LAST_RUN.read_text().strip() == date.today().isoformat():
        print("Already ran today. Use --force to re-run.")
        return 0

    lookback = args.lookback or cfg.get("lookback_hours", 168)
    print(f"[1/4] Fetching (lookback {lookback}h)...")

    # Search phrases: core drives the paper searches; a couple of emerging
    # framings widen the net for the `emerging` bucket.
    search_core = topics["core"][:12]
    search_wide = search_core + topics["emerging_framings"][:6]

    items: list[dict] = []
    items += fetchers.fetch_arxiv(search_wide, lookback)
    items += fetchers.fetch_hf_papers(lookback)
    items += fetchers.fetch_semantic_scholar(["continual learning", "catastrophic forgetting",
                                              "loss of plasticity", "test-time adaptation"], lookback)
    items += fetchers.fetch_openreview(["continual learning", "catastrophic forgetting"])
    items += fetchers.fetch_hn(["continual learning", "catastrophic forgetting", "fine-tuning",
                                "test-time training"], lookback)
    items += fetchers.fetch_reddit(lookback)
    items += fetchers.fetch_github(["continual-learning", "catastrophic-forgetting",
                                    "test-time-adaptation"], lookback)
    items += fetchers.fetch_rss_feeds(feeds_cfg["feeds"], lookback * 2)  # blogs post slower

    n_sources = len({i["source"].split(":")[0] for i in items})
    print(f"[2/4] Scoring {len(items)} items...")
    scored = scorer.score_items(items, topics, feeds_cfg.get("tiers", {}))
    buckets = scorer.bucketize(scored, cfg.get("caps", {"core": 10, "emerging": 6, "viral": 5}))
    people = scorer.extract_people(scored)
    stats = {"fetched": len(items), "kept": len(scored), "sources": n_sources}
    print(f"      kept {len(scored)}: core {len(buckets['core'])}, "
          f"emerging {len(buckets['emerging'])}, viral {len(buckets['viral'])}")

    print("[3/4] Building digest...")
    md = digest_mod.build_markdown(buckets, people, stats)
    if args.dry_run:
        print("\n" + md)
        return 0

    DIGEST_DIR.mkdir(exist_ok=True)
    out_file = DIGEST_DIR / f"{date.today().isoformat()}.md"
    out_file.write_text(md)
    print(f"      wrote {out_file}")

    print("[4/4] Delivering...")
    tg = cfg.get("telegram", {})
    if tg.get("enabled"):
        sys.path.insert(0, str(PKG_DIR.parent))
        from news_scout import telegram_sender
        ok = telegram_sender.send(digest_mod.build_telegram(buckets, stats),
                                  tg["bot_token"], tg["channel_id"], parse_mode="")
        print(f"      telegram: {'sent' if ok else 'FAILED'}")
    else:
        print("      telegram: disabled")
    # Email delivery: wire to email_digest sender in Phase 1.5 (config: email.enabled)

    LAST_RUN.write_text(date.today().isoformat())
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
