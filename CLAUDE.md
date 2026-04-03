# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A curated knowledge base of 597+ AI/ML paper reviews (Hebrew primary, English secondary), learning materials, and presentations. The repo is primarily a content repository with Python automation tooling for processing, metadata management, and cross-platform publishing (Telegram, Discord, Twitter/X).

## Key Architecture

### Content Pipeline
1. New DOCX reviews land in `~/ReviewsInbox/`
2. `daily_review_processor.py` runs via launchd (5/6/8/9 AM) — copies DOCX, converts to markdown, commits & pushes (auto-resolves merge conflicts in metadata files)
3. Git pre-commit hook runs `update_metadata.py` — extracts titles/links from Hebrew markdown, updates 4 metadata files + 3 READMEs (main, mike-paper-reviews-all, presentations)
4. `telegram_uploader.py` runs every 30 min from 11:00 AM to 3:00 PM — uploads to Telegram channels (stops once succeeded)
5. `twitter_thread_auto_poster.py` runs every 30 min from 11:35 AM to 3:35 PM — generates Twitter threads, posts to Telegram (stops once succeeded)
6. `discord_poster.py` runs every 30 min from 4:00 PM to 7:00 PM — creates daily threads in Discord (stops once succeeded)
7. `wake_catchup.py` runs on login via launchd (`RunAtLoad`) — catches up any missed pipeline steps by checking ledgers and running scripts as needed (10-min cooldown between runs)
8. `email_digest` runs daily at 10:00 AM + on login — fetches Gmail, summarizes with Claude, sends digest to Telegram. Config in `.repo-tools/scripts/email_digest/config.yaml` (gitignored). OAuth credentials in `~/.config/email-digest/`

### Review File Conventions
- Naming: `Review_NNN.md` / `Review_NNN.docx` (zero-padded 3 digits)
- Hebrew reviews in `mike-paper-reviews-all/split-hebrew-reviews-md/` (597 files, primary)
- English reviews in `mike-paper-reviews-all/split-english-reviews-md/` (230 files)
- DOCX sources in `mike-paper-reviews-all/split-reviews-docx/`
- Reviews contain Hebrew header, English paper title as "Review NNN: Title", paper link (arxiv/doi/etc)

### Metadata Files (auto-managed, don't edit manually)
All in `mike-paper-reviews-all/reviews_metadata/`:
- `paper_with_links.csv` — Review number, title, link
- `all_paper_titles.txt` — Numbered title list
- `clean_titles_for_search.txt` — Sanitized for search
- `reviews_from_208_titles.txt` — Titles for reviews 208+

### Automation Tooling
- `.repo-tools/scripts/` — All automation scripts (Python 3)
- `.repo-tools/repo_automator/` — Watcher-based automation framework with scanners and updaters
- `.repo-tools/config.yaml` — Defines watched paths, modifiable files whitelist, stat update patterns
- `.repo-tools/skills/` — Skill definitions for Claude Code
- Scheduling via macOS launchd (`~/Library/LaunchAgents/`)

## Commands

```bash
# Process new reviews (dry-run)
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Update metadata manually
python3 .repo-tools/scripts/update_metadata.py

# Convert DOCX to markdown
python3 .repo-tools/scripts/convert_docx_to_md.py input.docx output.md

# Telegram upload (dry-run)
python3 .repo-tools/scripts/telegram_uploader.py --dry-run

# Discord post (dry-run / test / specific review)
python3 .repo-tools/scripts/discord_poster.py --dry-run
python3 .repo-tools/scripts/discord_poster.py --test-bot-token
python3 .repo-tools/scripts/discord_poster.py --review 577

# Twitter thread generation (manual or automated)
python3 .repo-tools/scripts/twitter_thread_builder.py --review 578 --clickbait
python3 .repo-tools/scripts/twitter_thread_auto_poster.py --dry-run

# Paper recommender (hourly 8:30 AM–6:30 PM, once/day — Mon: 20 papers/3 days, Tue-Fri: 10/1 day, Sat-Sun: skip)
cd .repo-tools/scripts && python3 -m paper_recommender.recommender --dry-run    # preview picks
cd .repo-tools/scripts && python3 -m paper_recommender.recommender --force      # send to Telegram
cd .repo-tools/scripts && python3 -m paper_recommender.recommender --days 2     # custom lookback

# Email digest (daily at 10 AM + on login — fetches Gmail, summarizes, sends to Telegram)
cd .repo-tools/scripts && email_digest/venv/bin/python3 -m email_digest.scheduler --dry-run    # preview
cd .repo-tools/scripts && email_digest/venv/bin/python3 -m email_digest.scheduler --force      # force run
cd .repo-tools/scripts && email_digest/venv/bin/python3 -m email_digest.scheduler --refresh    # new emails only
cd .repo-tools/scripts && email_digest/venv/bin/python3 -m email_digest.scheduler --date 2026-03-09  # specific date
cd .repo-tools/scripts && email_digest/venv/bin/python3 email_digest/setup_oauth.py            # re-auth Gmail

# Wake catch-up (check pipeline status on login)
python3 .repo-tools/scripts/wake_catchup.py

# Check launchd jobs
launchctl list | grep "daily-review\|telegram\|discord\|twitter\|paper-recommender\|wake-catchup"

# Search papers
grep -i "transformer" mike-paper-reviews-all/reviews_metadata/all_paper_titles.txt

# Arxiv paper downloader (scans Chrome tabs, downloads PDFs sorted by date, closes tabs)
arxiv-to-repo                  # download, commit, push, close tabs
arxiv-to-repo --dry-run        # preview only
arxiv-to-repo --no-push        # commit but don't push
arxiv-to-repo --keep-tabs      # don't close Chrome tabs
arxiv-to-repo --fix-dates      # one-time: add date prefixes to existing papers

# YouTube clip cutter (download a segment from a YouTube video)
python3 .repo-tools/scripts/youtube_clip_cutter.py --url "URL" --start "27:55" --end "38:58"
python3 .repo-tools/scripts/youtube_clip_cutter.py --url "URL" --start "1:05:30" --end "1:15:00" --output ~/Desktop/
# Cut + upload to test Hebrew Telegram (≤50MB: video+caption, >50MB: text caption only)
# Claude generates caption from YouTube subtitles — see .repo-tools/skills/youtube-clip.md
python3 .repo-tools/scripts/youtube_clip_cutter.py --url "URL" --start "27:55" --end "38:58" --upload --message "caption"
```

## Session Start

**At the start of every session**, before doing any work, run `git pull --rebase --autostash` to get the latest main branch. This ensures we're always working on top of the latest automated commits (daily processor, metadata updates, etc.). Do this automatically — no need to ask Mike first.

## Multi-Machine Setup (CRITICAL)

Automations run from **multiple local computers** simultaneously. Every publishing script MUST prevent duplicate posts:

### How Cross-Machine Dedup Works
1. **Git-tracked upload ledger** (`.repo-tools/logs/telegram_upload_ledger.json`) — committed and pushed immediately after each successful upload. All machines pull before checking.
2. **Deterministic startup delays** — each machine has a unique `machine_id` in its local config (`telegram_config.yaml`, `discord_config.yaml`). Machines get non-overlapping delay slots (100s+ gap):
   - `machine_id: 1` → 0-20s delay
   - `machine_id: 2` → 120-140s delay
   - `machine_id: 3` → 240-260s delay
3. **Last-second re-check** — right before sending, pulls git again and re-checks the ledger.
4. **Push retry with backoff** — after sending, retries `git push` up to 3 times (5s, 10s backoff) with `pull --rebase` between attempts. Logs CRITICAL if all 3 fail.
5. **Startup push recovery** — both `daily_review_processor.py` and `wake_catchup.py` check for unpushed local commits on startup and retry pushing (3 attempts with pull+rebase+backoff). This ensures commits aren't stranded after network timeouts.

### When Adding a New Machine
1. Assign a unique `machine_id` (next unused integer) in ALL config files:
   - `.repo-tools/scripts/telegram_config.yaml` → `settings.machine_id`
   - `.repo-tools/config/discord_config.yaml` → `settings.machine_id`
2. Verify ledger files exist and are up to date: `git pull` and check `.repo-tools/logs/*_ledger.json`
3. Never reuse a `machine_id` from another active machine

### Ledger Files (git-tracked, DO NOT edit manually)
- `.repo-tools/logs/telegram_upload_ledger.json` — Telegram uploads (Hebrew + English)
- `.repo-tools/logs/telegram_message_ids.json` — Telegram message IDs + links (committed+pushed after each upload, used by discord_poster to build Discord messages)
- `.repo-tools/logs/discord_upload_ledger.json` — Discord thread posts
- `.repo-tools/logs/twitter_upload_ledger.json` — Twitter thread posts

### Current Dedup by Script
| Script | Method |
|--------|--------|
| `telegram_uploader.py` | Git-tracked ledger + delay slots + last-second re-check + git fetch remote ledger check + push retry 3x + local log + commits message IDs to git |
| `discord_poster.py` | Git-tracked ledger + delay slots + last-second re-check + push retry 3x + Discord API + local log |
| `twitter_thread_auto_poster.py` | Git-tracked ledger + delay slots + last-second re-check + git fetch remote ledger check + push retry 3x + Telegram API + local log |
| `daily_review_processor.py` | `git pull` before dedup check + `git pull --rebase --autostash` before push + auto-resolve merge conflicts (abort rebase → merge pull → checkout theirs → re-run update_metadata.py) + push retry 3x + startup push recovery for unpushed commits |
| `wake_catchup.py` | Git pull with auto-resolve merge conflicts (same logic as daily_review_processor) + checks each pipeline step ledger + runs missing steps + 10-min cooldown |
| `paper_recommender` | Git-tracked `last_run.txt` + git fetch remote check |

## Important Rules

- **When making system changes** (schedules, workflows, configs): you MUST update ALL related skills in `.repo-tools/skills/`, docs in `.repo-tools/docs/`, and config templates together in a single commit. See `.repo-tools/skills/README.md` for the full checklist.
- The automation tool NEVER deletes files — it only modifies files on the whitelist in `.repo-tools/config.yaml`.
- Metadata files are auto-generated by the pre-commit hook. Fix source markdown files instead of editing metadata directly.
- Config files with credentials (`telegram_config.yaml`, `discord_config.yaml`, `email_digest/config.yaml`) are gitignored — never commit them.
- SSH: use `git@github.com` for push (primary key `~/.ssh/id_ed25519`). Alternate host `github-dn` has read-only access.
- README stats (review count, categories, repo size) are auto-updated by `update_metadata.py` via pre-commit hook. Updates 3 READMEs: main, mike-paper-reviews-all, and presentations.

## Python Dependencies

```bash
cd .repo-tools && python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml requests beautifulsoup4 python-telegram-bot
```
