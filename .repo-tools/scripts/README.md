# Automation Scripts

This directory contains automation scripts for the scientific_repo repository.

## Overview

The automation system provides:

1. **Daily review processing** - Automatically processes new review files from ReviewsInbox
2. **Metadata management** - Auto-updates metadata files when reviews are committed
3. **DOCX to Markdown conversion** - Converts Word documents to markdown format

## Scripts

### `daily_review_processor.py`

Main automation script that runs daily to process new review files.

**What it does:**
- Scans `~/ReviewsInbox/` for new `Review_XXX.docx` files
- Checks for duplicates (skips reviews already in repo)
- Copies Hebrew DOCX to `split-reviews-docx/`
- Converts Hebrew DOCX to markdown
- Converts English DOCX (if exists) to markdown
- Commits and pushes changes to GitHub
- Logs all actions

**Usage:**

```bash
# Test without making changes
python3 daily_review_processor.py --dry-run

# Process new reviews manually
python3 daily_review_processor.py
```

**Scheduling:**
- Runs automatically at 5:00 AM, 6:00 AM, 8:00 AM, and 9:00 AM daily via launchd
- Primary run at 5:00 AM, with three backup runs for reliability
- If earlier run succeeds, later runs find no new files and exit quickly
- Multiple runs ensure reviews are processed even if early runs have timing issues
- Setup: `./schedule_daily_job.sh`

### `update_metadata.py`

Updates metadata files and README statistics from review markdown files.

**What it does:**
- Extracts paper titles and links from all Hebrew review markdown files
- Updates `paper_with_links.csv`
- Updates `all_paper_titles.txt`
- Updates `clean_titles_for_search.txt`
- Updates `reviews_from_208_titles.txt`
- Updates README.md with current statistics

**Usage:**

```bash
# Run manually
python3 update_metadata.py

# Automatically runs via pre-commit hook when review markdown files are committed
```

### `convert_docx_to_md.py`

Converts DOCX files to Markdown format.

**Usage:**

```bash
python3 convert_docx_to_md.py input.docx output.md
```

### `telegram_uploader.py`

Uploads new reviews to Telegram test channels.

**What it does:**
- Checks for new reviews not yet uploaded to Telegram
- Uploads Hebrew reviews to Hebrew channel
- Uploads English reviews to English channel
- Splits long messages (max 4096 chars per Telegram message)
- Uses HTML parse mode (handles scientific notation, parentheses)
- Tracks uploaded reviews to avoid duplicates (git-tracked upload ledger + deterministic delay slots per machine_id + last-second re-check + git fetch remote ledger check + push retry 3x with backoff + local log, safe across multiple machines)

**Usage:**

```bash
# Test without uploading
python3 telegram_uploader.py --dry-run

# Upload new reviews manually
python3 telegram_uploader.py
```

**Scheduling:**
- Runs every 30 min from 11:00 AM to 3:00 PM via launchd (stops once succeeded)
- Script checks ledger and skips instantly if already uploaded
- Ensures resilience: if early slots fail (no network, git conflict), later slots retry
- Setup: `./schedule_telegram_job.sh`

### `discord_poster.py`

Posts paper reviews to Discord channel in organized daily threads.

**What it does:**
- Creates daily thread "Daily Paper Review: {date}"
- Posts review inside thread with all links:
  - Hebrew Telegram link
  - English Telegram link
  - Substack link
  - Hebrew GitHub link
  - English GitHub link
- Validates all links exist before posting
- Tracks posted reviews to avoid duplicates (git-tracked ledger + delay slots + Discord API + push retry 3x with backoff + local log, safe across multiple machines)
- Only posts reviews from last 24 hours

**Usage:**

```bash
# Test without posting
python3 discord_poster.py --dry-run

# Test bot token
python3 discord_poster.py --test-bot-token

# Test thread creation
python3 discord_poster.py --test-create-thread

# Post specific review manually
python3 discord_poster.py --review 577

# Post all new reviews
python3 discord_poster.py
```

**Scheduling:**
- Runs automatically at 12:00 PM (noon) and 6:00 PM daily via launchd
- 12:00 PM: Primary run (1 hour after Telegram upload)
- 6:00 PM: Backup run (catches reviews if Substack wasn't ready at noon)
- Setup: Automatic via `com.user.discord-review-poster.plist` LaunchAgent

**Configuration:**
- Requires Discord bot token and channel ID
- See `.repo-tools/DISCORD_BOT_SETUP.md` for setup instructions

### `paper_recommender/` (package)

Daily arXiv paper recommender bot. Fetches recent papers, ranks them by relevance to Mike's interests using Claude Haiku, and sends top 10 picks to Telegram.

**What it does:**
- Fetches recent papers from arXiv (cs.LG, cs.CL, cs.AI, cs.CV, stat.ML)
- Builds interest profile from 580+ reviewed papers in `paper_with_links.csv`
- Ranks papers using Claude Haiku (~$0.07/run)
- Sends top picks to review_testing_eng Telegram channel (Mon: 20 papers/3 days, Tue-Fri: 10/1 day, skip weekends)
- Cross-machine dedup via git-tracked `last_run.txt` (git fetch + git show)

**Usage:**

```bash
cd .repo-tools/scripts

# Preview top 10 picks (no Telegram send)
python3 -m paper_recommender.recommender --dry-run

# Send to Telegram (force, ignoring last_run check)
python3 -m paper_recommender.recommender --force

# Look back 2 days
python3 -m paper_recommender.recommender --days 2
```

**Scheduling:**
- Runs hourly 8:30 AM – 6:30 PM via launchd + on wake/login (RunAtLoad)
- Waits up to 2 minutes for network connectivity before proceeding
- `last_run.txt` ensures once-per-day execution (cross-machine dedup via git)
- Skips weekends (arXiv doesn't publish Sat/Sun)
- If a run fails (no network), retries on the next hourly slot
- Setup: copy `com.user.paper-recommender.plist.template` to `~/Library/LaunchAgents/`

**Configuration:**
- Copy `config.yaml.template` → `config.yaml` (gitignored)
- Set Anthropic API key (or `ANTHROPIC_API_KEY` env var)
- Telegram bot token and channel ID pre-filled for review_testing_eng

### `email_digest/` (package)

Daily Gmail digest agent. Fetches yesterday's emails via Gmail API, summarizes with Claude Sonnet, sends digest to personal Telegram chat.

**What it does:**
- Fetches emails via Gmail API (OAuth)
- Categorizes and summarizes using Claude Sonnet
- Sends digest to personal Telegram chat
- Catches up missed days automatically
- Refresh mode for mid-day new email summaries
- 60s HTTP timeout + 3x retry on transient Gmail errors (timeout/429/network) — fails fast instead of hanging when the Mac wakes with flaky network

**Usage:**

```bash
# Dry run (preview, don't send)
cd .repo-tools/scripts
email_digest/venv/bin/python3 -m email_digest.scheduler --dry-run

# Force run
email_digest/venv/bin/python3 -m email_digest.scheduler --force

# Specific date
email_digest/venv/bin/python3 -m email_digest.scheduler --date 2026-03-09

# Refresh (new emails only)
email_digest/venv/bin/python3 -m email_digest.scheduler --refresh

# Re-authenticate Gmail OAuth
email_digest/venv/bin/python3 email_digest/setup_oauth.py
```

**Scheduling:**
- Runs daily at 10:00 AM + on login (RunAtLoad) via launchd
- Once per day via `~/.config/email-digest/last_run.txt`
- Setup: copy `com.user.email-digest.plist.template` to `~/Library/LaunchAgents/`

**Configuration:**
- Copy `config.yaml.template` → `config.yaml` (gitignored)
- Set Anthropic API key, Telegram bot token & chat ID
- Gmail OAuth: place `credentials.json` in `~/.config/email-digest/`, run `setup_oauth.py` once

### `wake_catchup.py`

Safety net that runs on login (via launchd `RunAtLoad`) and catches up any missed pipeline steps.

**What it does:**
- Pulls latest git to sync ledgers from other machines
- Checks if today's reviews were processed (daily_review_processor)
- Checks if Telegram upload happened (telegram_uploader)
- Checks if Twitter thread was posted (twitter_thread_auto_poster)
- Checks if Discord thread was posted (discord_poster)
- Runs any missing steps in dependency order
- 10-minute cooldown between runs to avoid spam

**Usage:**

```bash
# Run manually
python3 wake_catchup.py

# Check launchd job
launchctl list | grep wake-catchup
```

**Scheduling:**
- Runs on login via launchd `RunAtLoad` (`com.user.wake-catchup.plist`)
- Does NOT trigger on wake-from-sleep (only login/restart)
- Cooldown: skips if last run was <10 minutes ago

**Dedup safety:**
- Only checks ledger status — the scripts it calls have their own full dedup chain
- Git pull before every check ensures cross-machine awareness
- Auto-resolves merge conflicts on pull (same logic as daily_review_processor: abort rebase → merge pull → accept theirs → re-run update_metadata.py)

### `schedule_daily_job.sh`

Installs the daily processing job as a launchd service.

**Usage:**

```bash
# Install daily job (runs at 5:00 AM)
./schedule_daily_job.sh
```

## Setup on New Laptop

When setting up on a new laptop:

### 1. Clone Repository
```bash
git clone https://github.com/merlihson/scientific-resources.git
cd scientific-resources
```

### 2. Install Python Dependencies
```bash
cd .repo-tools
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml requests beautifulsoup4 python-telegram-bot
```

### 3. Configure Telegram
```bash
# Create telegram config from template
cp scripts/telegram_config.yaml.template scripts/telegram_config.yaml
# Edit telegram_config.yaml and add your credentials
```

See `.repo-tools/docs/TELEGRAM_SETUP.md` for detailed Telegram setup instructions.

### 4. Configure Discord Bot
**IMPORTANT:** Discord posting now uses a bot (not webhook) to create organized daily threads.

```bash
# The config template is already in place
# You need to:
# 1. Create Discord bot in Developer Portal
# 2. Get bot token and channel ID
# 3. Update discord_config.yaml
```

**Follow the complete guide:** `.repo-tools/DISCORD_BOT_SETUP.md`

Quick summary:
- Go to https://discord.com/developers/applications
- Create bot application
- Copy bot token
- Invite bot to server
- Copy channel ID (enable Developer Mode in Discord)
- Update `.repo-tools/config/discord_config.yaml`:
  ```yaml
  discord:
    bot_token: "YOUR_BOT_TOKEN"
    channel_id: "YOUR_CHANNEL_ID"
  ```

### 5. Set Up Automation Jobs
```bash
cd .repo-tools/scripts
./schedule_daily_job.sh      # Daily review processing
./schedule_telegram_job.sh   # Telegram uploads
# Discord job is auto-loaded via LaunchAgent
```

### 6. Verify Setup
```bash
# Test daily processor
python3 daily_review_processor.py --dry-run

# Test Telegram uploader
python3 telegram_uploader.py --dry-run

# Test Discord bot
python3 discord_poster.py --test-bot-token
python3 discord_poster.py --test-create-thread
python3 discord_poster.py --dry-run

# Test paper recommender
cd .repo-tools/scripts
python3 -m paper_recommender.recommender --dry-run

# Check all launchd jobs are loaded
launchctl list | grep "daily-review\|telegram\|discord\|paper-recommender\|email-digest\|wake-catchup"
```

## Logs

All logs are stored in `.repo-tools/logs/`:

- `daily_processor.log` - Main output log
- `daily_processor_error.log` - Error log

**View logs:**

```bash
# View recent activity
tail -f .repo-tools/logs/daily_processor.log

# View errors
tail -f .repo-tools/logs/daily_processor_error.log

# View full log
less .repo-tools/logs/daily_processor.log
```

## Management Commands

### Daily Job

```bash
# View status
launchctl list | grep daily-review

# Run immediately (don't wait for 5 AM)
launchctl start com.user.daily-review-processor

# Unload (disable) job
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Reload (re-enable) job
launchctl load ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Uninstall completely
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist
rm ~/Library/LaunchAgents/com.user.daily-review-processor.plist
```

### Git Hooks

The pre-commit hook automatically runs `update_metadata.py` when Hebrew review markdown files are committed.

```bash
# View pre-commit hook
cat ../.git/hooks/pre-commit

# Test manually
git add mike-paper-reviews-all/split-hebrew-reviews-md/Review_XXX.md
git commit -m "Test commit"
# Hook will run automatically
```

## Troubleshooting

### Daily job not running

1. **Check if job is loaded:**
   ```bash
   launchctl list | grep daily-review
   ```

2. **Check logs for errors:**
   ```bash
   cat .repo-tools/logs/daily_processor_error.log
   ```

3. **Test manually:**
   ```bash
   python3 .repo-tools/scripts/daily_review_processor.py --dry-run
   ```

4. **Reinstall job:**
   ```bash
   ./schedule_daily_job.sh
   ```

### Git push fails

**Note:** Both `daily_review_processor.py` and `wake_catchup.py` now auto-resolve merge conflicts (common with auto-generated metadata files). If `git pull --rebase` hits a conflict, the script aborts the rebase, does a merge pull, accepts the remote version of conflicted files, re-runs `update_metadata.py` to regenerate correct stats, and completes the merge. This is fully automatic.

If the job can commit but can't push (network issues, auth problems):

1. **Check commit was created:**
   ```bash
   cd /Users/michaelerlihson/Personal/repos/scientific_repo
   git log -1
   ```

2. **Push manually:**
   ```bash
   git push
   ```

3. **Check SSH keys:**
   ```bash
   ssh -T git@github.com
   ```

### Conversion fails

If DOCX conversion fails:

1. **Check DOCX file is valid:**
   - Open in Word to verify it's not corrupted

2. **Test converter manually:**
   ```bash
   python3 convert_docx_to_md.py ~/ReviewsInbox/Review_XXX.docx /tmp/test.md
   ```

3. **Check dependencies:**
   ```bash
   python3 -c "import zipfile, xml.etree.ElementTree"
   ```

### Duplicates being processed

If reviews are being processed multiple times:

1. **Check existing reviews:**
   ```bash
   ls mike-paper-reviews-all/split-reviews-docx/Review_*.docx
   ```

2. **Run with dry-run to see what would be processed:**
   ```bash
   python3 daily_review_processor.py --dry-run
   ```

3. **The script checks for duplicates automatically** - if a Review_XXX already exists in `split-reviews-docx/`, it won't be reprocessed

## File Naming Conventions

The script expects files in ReviewsInbox to follow this naming:

- **Hebrew reviews:** `Review_XXX.docx` (e.g., `Review_574.docx`)
- **English reviews:** `Review_XXX_english.docx` (e.g., `Review_574_english.docx`)

The script is case-insensitive for the `_english` part.

## How It Works

### Processing Flow

1. **Discovery:**
   - Scan `~/ReviewsInbox/` for `Review_*.docx` files
   - Get highest existing review number from repo
   - Identify new reviews (not in repo)

2. **Processing:**
   - Copy Hebrew DOCX → `split-reviews-docx/Review_XXX.docx`
   - Convert Hebrew DOCX → `split-hebrew-reviews-md/Review_XXX.md`
   - Extract title from markdown
   - Prepend "Review XXX: TITLE" to first line
   - If English DOCX exists, convert → `split-english-reviews-md/Review_XXX.md`

3. **Commit:**
   - Stage all new files
   - Create commit with descriptive message
   - Pre-commit hook runs automatically and updates metadata
   - Metadata files are added to the same commit

4. **Push:**
   - Pull remote changes first (`git pull --rebase --autostash`) to avoid conflicts with other machines
   - Push commit to GitHub
   - If rebase conflicts occur (typically in auto-generated files like readme.md stats):
     1. Aborts the rebase (`git rebase --abort`)
     2. Falls back to merge pull (`git pull` without rebase)
     3. Auto-resolves conflicts by accepting remote version (`git checkout --theirs`)
     4. Re-runs `update_metadata.py` to regenerate correct stats from local content
     5. Completes the merge commit
     6. Continues with push
   - Push retries up to 3 times with backoff (5s, 10s) and pull --rebase between attempts
   - If all retries fail, files remain committed locally — **the next run (6/8/9 AM or wake_catchup on login) will automatically detect unpushed commits and retry the push**

### Deduplication Logic

The script uses this logic to avoid reprocessing:

```python
# Get all existing review numbers from repo
existing = {1, 2, 3, ..., 573}

# For each file in ReviewsInbox
for file in ReviewsInbox:
    review_num = extract_number(file)  # e.g., 574
    if review_num in existing:
        skip  # Already in repo
    else:
        process  # New review
```

This ensures that even if you leave DOCX files in ReviewsInbox, they won't be reprocessed.

## Security Notes

- **Git credentials:** The script requires push access to GitHub. Ensure SSH keys or credential helper is configured.
- **File permissions:** Scripts are executable by owner only (`chmod +x`)
- **launchd permissions:** Runs as user-level LaunchAgent (no special permissions needed)

## Error Handling

The script handles various error scenarios:

- **No new reviews:** Logs and exits gracefully
- **DOCX conversion fails:** Logs error, continues with next file
- **Git push fails:** Pulls with rebase first; if rebase conflicts (e.g., in auto-generated metadata), auto-resolves by accepting remote + re-running `update_metadata.py`; retries up to 3 times with backoff; if still fails, leaves files committed locally — next run automatically retries the push
- **Missing English file:** Processes Hebrew only, logs info message
- **Network timeout:** Logs error, leaves files committed locally

All errors are logged to `daily_processor_error.log`.
