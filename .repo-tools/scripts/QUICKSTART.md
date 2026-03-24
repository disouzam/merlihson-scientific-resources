# Quick Start Guide - Daily Review Automation

## 🚀 Setup (First Time)

```bash
# 1. Install the daily job (runs at 5:00 AM)
cd .repo-tools/scripts
./schedule_daily_job.sh

# 2. Verify it's loaded
launchctl list | grep daily-review
```

## ✅ Verify Everything Works

```bash
# Test the processor without making changes
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Test the metadata updater
python3 .repo-tools/scripts/update_metadata.py

# Check pre-commit hook
cat .git/hooks/pre-commit
```

## 📋 Daily Usage

**Automatic (recommended):**
- Just drop `Review_XXX.docx` and `Review_XXX_english.docx` in ~/Downloads
- At 5:00 AM, the system will automatically process, commit, and push

**Manual:**
```bash
# Process new reviews now (don't wait for 5 AM)
python3 .repo-tools/scripts/daily_review_processor.py
```

## 🔍 Monitoring

```bash
# View recent activity
tail -f .repo-tools/logs/daily_processor.log

# View errors only
cat .repo-tools/logs/daily_processor_error.log

# Run immediately (don't wait for scheduled time)
launchctl start com.user.daily-review-processor
```

## 🛠 Management

```bash
# Check if job is running
launchctl list | grep daily-review

# Stop the job
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Start the job again
launchctl load ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Remove completely
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist
rm ~/Library/LaunchAgents/com.user.daily-review-processor.plist
```

## 📁 What Happens Automatically

For each new `Review_XXX.docx` in Downloads:

1. ✅ Copy to `split-reviews-docx/Review_XXX.docx`
2. ✅ Convert to `split-hebrew-reviews-md/Review_XXX.md`
3. ✅ Add "Review XXX: TITLE" header
4. ✅ Convert English (if exists) to `split-english-reviews-md/Review_XXX.md`
5. ✅ Git commit with descriptive message
6. ✅ Pre-commit hook updates all metadata files automatically
7. ✅ Git push to GitHub

## ⚠️ Important Notes

- **Deduplication:** Reviews already in the repo are automatically skipped
- **No cleanup:** Files in Downloads are left alone (not deleted)
- **Network issues:** If push fails, files are committed locally — the next scheduled run or wake_catchup on login will automatically retry the push
- **Merge conflicts:** Auto-resolved — if `git pull --rebase` conflicts on auto-generated files (readme stats, metadata), the script falls back to merge, accepts remote, re-runs `update_metadata.py`, and continues
- **Error handling:** Errors are logged but don't stop processing of other reviews

## 🔧 Troubleshooting

**Job not running?**
```bash
# Reinstall
./schedule_daily_job.sh
```

**Want to test without waiting for 5 AM?**
```bash
launchctl start com.user.daily-review-processor
```

**Need to see what would happen?**
```bash
python3 daily_review_processor.py --dry-run
```

## 📚 Full Documentation

See [README.md](README.md) for complete documentation.
