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
- Tracks uploaded reviews to avoid duplicates (git-tracked upload ledger + deterministic delay slots per machine_id + last-second re-check + local log, safe across multiple machines)

**Usage:**

```bash
# Test without uploading
python3 telegram_uploader.py --dry-run

# Upload new reviews manually
python3 telegram_uploader.py
```

**Scheduling:**
- Runs automatically at 11:00 AM and 11:30 AM (backup) daily via launchd
- If 11:00 AM run succeeds, 11:30 AM run finds no new reviews and exits
- If 11:00 AM run fails, 11:30 AM run uploads the reviews
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
- Tracks posted reviews to avoid duplicates (git-tracked ledger + delay slots + Discord API + local log, safe across multiple machines)
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
- Sends top 10 to review_testing_eng Telegram channel
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
- Runs on first Mac wake via launchd `RunAtLoad`
- `last_run.txt` ensures once-per-day execution
- Setup: copy `com.user.paper-recommender.plist.template` to `~/Library/LaunchAgents/`

**Configuration:**
- Copy `config.yaml.template` → `config.yaml` (gitignored)
- Set Anthropic API key (or `ANTHROPIC_API_KEY` env var)
- Telegram bot token and channel ID pre-filled for review_testing_eng

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
launchctl list | grep "daily-review\|telegram\|discord\|paper-recommender"
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
   - If rebase conflicts occur, falls back to merge pull
   - If push still fails (network issue), files remain committed locally

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
- **Git push fails:** Pulls with rebase first, retries; if still fails, leaves files committed locally for manual push
- **Missing English file:** Processes Hebrew only, logs info message
- **Network timeout:** Logs error, leaves files committed locally

All errors are logged to `daily_processor_error.log`.
