# Automation Scripts

This directory contains automation scripts for the scientific_repo repository.

## Overview

The automation system provides:

1. **Daily review processing** - Automatically processes new review files from Downloads
2. **Metadata management** - Auto-updates metadata files when reviews are committed
3. **DOCX to Markdown conversion** - Converts Word documents to markdown format

## Scripts

### `daily_review_processor.py`

Main automation script that runs daily to process new review files.

**What it does:**
- Scans `~/Downloads/` for new `Review_XXX.docx` files
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
- Runs automatically every day at 5:00 AM via launchd
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

### `schedule_daily_job.sh`

Installs the daily processing job as a launchd service.

**Usage:**

```bash
# Install daily job (runs at 5:00 AM)
./schedule_daily_job.sh
```

## Setup on New Laptop

When setting up on a new laptop:

1. **Clone repository:**
   ```bash
   git clone https://github.com/merlihson/scientific-resources.git
   cd scientific-resources
   ```

2. **Run installation script:**
   ```bash
   cd .repo-tools
   ./install.sh
   # Follow prompts to set up daily job
   ```

3. **Or manually set up daily job:**
   ```bash
   cd .repo-tools/scripts
   ./schedule_daily_job.sh
   ```

4. **Verify setup:**
   ```bash
   # Test the processor
   python3 daily_review_processor.py --dry-run

   # Check launchd job is loaded
   launchctl list | grep daily-review
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
   cd /Users/michaelerlihson/Personal/Projects/scientific_repo
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
   python3 convert_docx_to_md.py ~/Downloads/Review_XXX.docx /tmp/test.md
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

The script expects files in Downloads to follow this naming:

- **Hebrew reviews:** `Review_XXX.docx` (e.g., `Review_574.docx`)
- **English reviews:** `Review_XXX_english.docx` (e.g., `Review_574_english.docx`)

The script is case-insensitive for the `_english` part.

## How It Works

### Processing Flow

1. **Discovery:**
   - Scan `~/Downloads/` for `Review_*.docx` files
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
   - Push commit to GitHub
   - If push fails (network issue), files remain committed locally

### Deduplication Logic

The script uses this logic to avoid reprocessing:

```python
# Get all existing review numbers from repo
existing = {1, 2, 3, ..., 573}

# For each file in Downloads
for file in Downloads:
    review_num = extract_number(file)  # e.g., 574
    if review_num in existing:
        skip  # Already in repo
    else:
        process  # New review
```

This ensures that even if you leave DOCX files in Downloads, they won't be reprocessed.

## Security Notes

- **Git credentials:** The script requires push access to GitHub. Ensure SSH keys or credential helper is configured.
- **File permissions:** Scripts are executable by owner only (`chmod +x`)
- **launchd permissions:** Runs as user-level LaunchAgent (no special permissions needed)

## Error Handling

The script handles various error scenarios:

- **No new reviews:** Logs and exits gracefully
- **DOCX conversion fails:** Logs error, continues with next file
- **Git push fails:** Logs error, leaves files committed locally for manual push
- **Missing English file:** Processes Hebrew only, logs info message
- **Network timeout:** Logs error, leaves files committed locally

All errors are logged to `daily_processor_error.log`.
