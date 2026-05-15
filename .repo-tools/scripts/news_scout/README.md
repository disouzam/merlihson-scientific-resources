# News Scout

Daily AI news digest in Hebrew, posted to the Telegram channel **review_testing_heb** ("Mike's Test Hebrew Reviews"). Surfaces the 7 most interesting AI stories that **have not yet been covered by Israeli Hebrew press** — raw material for posts, op-eds, and TV/radio segments.

## How it works

1. **Fetch** — pulls the last ~36h from 10 curated English-language feeds (Reuters, AP, BBC, NYT, Guardian, The Verge, CNBC, Wired, Axios, MIT Tech Review). AI-keyword pre-filter on the generic-tech feeds.
2. **Coverage check** — for each remaining candidate, Claude uses the `web_search` tool to check whether the same story has been covered in Hebrew on 10 Israeli sites (Ynet, N12/Mako, Walla, Israel Hayom, Maariv, Haaretz, TheMarker, Calcalist, Globes, Geektime).
3. **Rank** — Claude scores 0–100 on "interestingness for general Israeli public" with hard exclusions for research-paper / benchmark / dev-tooling minutiae.
4. **Format** — Hebrew headline + 1–2 sentence teaser + "Israeli angle" line per item.
5. **Post** — single HTML-formatted message to the test Hebrew channel.

## Schedule

`08:00` Monday through Friday. Hourly retries until `12:00` in case the early slot fails — the `last_run.txt` guard makes retries instant no-ops once the day's digest has shipped. Saturday and Sunday are skipped. **Monday** uses a 72h lookback (`monday_lookback_hours` in config) so it absorbs Sat+Sun.

## Multi-machine dedup (5 layers)

1. `last_run.txt` (git-tracked) — one digest per calendar day, max.
2. `news_scout_ledger.json` (in `.repo-tools/logs/`, git-tracked) — never repost the same URL.
3. Machine-staggered delay — `(machine_id - 1) * 120s + jitter` before any work.
4. Last-second `git pull` + re-check of remote `last_run.txt` after the stagger.
5. Local launchd log at `.repo-tools/logs/news_scout.log` for diagnostics.

## Setup

```bash
cd .repo-tools/scripts/news_scout
cp config.yaml.template config.yaml
# edit config.yaml and set anthropic_api_key
./schedule_news_scout_job.sh
```

## Manual run

```bash
cd .repo-tools/scripts
# preview only:
../.venv/bin/python3 -m news_scout.news_scout --dry-run
# real run, bypassing one-per-day guard:
../.venv/bin/python3 -m news_scout.news_scout --force --skip-delay
```

## Files

- `sources.py` — the 10 English feeds + 10 Israeli domains + AI keyword list. Edit here to add/remove sources.
- `fetcher.py` — parallel RSS fetch, lookback window, AI pre-filter, dedup.
- `coverage_checker.py` — Anthropic `web_search` against Israeli domains.
- `ranker.py` — general-public scorer + hard exclusions.
- `formatter.py` — Hebrew teasers + Telegram HTML message body.
- `telegram_sender.py` — chunked send with retries.
- `news_scout.py` — orchestrator + dedup machinery.
