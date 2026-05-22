# News Scout — Setup

Two one-time steps. After this, the digest runs Tuesday + Thursday at 08:00 automatically.

```bash
cd /Users/michaelerlihson/Personal/repos/scientific_repo/.repo-tools/scripts/news_scout

# 1. Create config.yaml and paste your Anthropic key
cp config.yaml.template config.yaml
# then edit config.yaml → set anthropic_api_key

# 2. Register the launchd job (one-time)
./schedule_news_scout_job.sh
```

That's it. Telegram credentials for `review_testing_heb` are already pre-filled in the template; `machine_id: 2` is the default (use a unique integer per laptop).

## Verify

```bash
# launchd job loaded?
launchctl list | grep news-scout

# preview message without sending (works without API key only if --dry-run errors out cleanly):
cd /Users/michaelerlihson/Personal/repos/scientific_repo/.repo-tools/scripts
../.venv/bin/python3 -m news_scout.news_scout --dry-run

# force a real send right now (bypasses Mon-Fri + once-per-day guards):
../.venv/bin/python3 -m news_scout.news_scout --force --skip-delay

# follow the runtime log:
tail -f /Users/michaelerlihson/Personal/repos/scientific_repo/.repo-tools/logs/news_scout.log
```

## Schedule

- **Tuesday + Thursday, 08:00** — twice weekly (~8-9 runs/month).
- Hourly retries through 12:00 if the early slot fails (no-op once the run succeeded — `last_run.txt` guards it).
- Weekends are hard-skipped in code as a safety net.
- `lookback_hours` is 120h so the Thursday→Tuesday gap (~5 days) is fully scanned.

## Uninstall / pause

```bash
launchctl unload ~/Library/LaunchAgents/com.user.news-scout.plist
# remove permanently:
rm ~/Library/LaunchAgents/com.user.news-scout.plist
```

## File map

| File | Purpose |
|---|---|
| `config.yaml` (gitignored) | API key + Telegram creds + tunables |
| `sources.py` | The 10 English feeds + 10 Israeli domains |
| `fetcher.py` | RSS fetch + AI pre-filter + dedup |
| `coverage_checker.py` | Anthropic `web_search` against Israeli sites |
| `ranker.py` | General-public scorer + hard exclusions |
| `formatter.py` | Hebrew teasers + Telegram HTML body |
| `telegram_sender.py` | Chunked send with retries |
| `news_scout.py` | Orchestrator + dedup + Mon-Fri guard |
| `schedule_news_scout_job.sh` | One-time installer |
| `com.user.news-scout.plist.template` | launchd schedule template |
