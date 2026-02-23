# 🖥️ New Laptop Setup Guide

Complete setup instructions for getting the scientific_repo automation running on a new laptop.

## 📋 Prerequisites

Before starting, ensure you have:
- macOS (for launchd automation)
- Python 3.8 or higher
- Git
- GitHub access (SSH key or credentials configured)

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Clone Repository

```bash
cd ~/Personal/repos  # or your preferred location
git clone git@github.com:merlihson/scientific-resources.git
cd scientific-resources
```

### Step 2: Install Automation Tools

```bash
cd .repo-tools
./install.sh
```

The installer will:
1. ✅ Create Python virtual environment
2. ✅ Install dependencies
3. ✅ Set up `repo-auto` command
4. ✅ Ask if you want to enable daily automation (choose **yes**)

When prompted: **"Set up daily automation? (y/n)"** → Type `y` and press Enter

### Step 3: Verify Installation

```bash
# Test the daily processor (dry-run mode)
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Check launchd job is loaded
launchctl list | grep daily-review

# Test metadata updater
python3 .repo-tools/scripts/update_metadata.py
```

You should see:
- ✅ Processor finds existing reviews
- ✅ Job listed in launchctl
- ✅ Metadata extracted successfully

### Step 4: Test Pre-Commit Hook

The pre-commit hook is already installed in the repository. Test it:

```bash
# Make a small change
echo "# Test" >> test.txt
git add test.txt
git commit -m "Test commit"
# Hook should run and show "✓ No review changes detected"

# Clean up
git reset HEAD~1
rm test.txt
```

---

## ✅ You're Done!

The system is now set up and will automatically:
- **Every day at 5:00 AM**: Check ~/ReviewsInbox for new Review_XXX.docx files
- **Process them**: Convert to markdown, commit, and push to GitHub
- **Update metadata**: Automatically via pre-commit hook

---

## 📱 Optional: Telegram Channel Automation

Want reviews automatically uploaded to your Telegram channels at 3:00 PM?

### Quick Setup (20 minutes):

1. **Create Telegram bots** via @BotFather (2 bots: Hebrew + English)
2. **Add bots** to your channels as admins
3. **Get channel IDs** using Bot API
4. **Configure script:**
   ```bash
   cd .repo-tools/scripts
   cp telegram_config.yaml.template telegram_config.yaml
   nano telegram_config.yaml  # Fill in bot tokens and channel IDs
   ```
5. **Set unique machine_id** in `telegram_config.yaml` → `settings.machine_id`:
   - Each machine MUST have a different ID (1, 2, 3, ...)
   - This prevents duplicate posts when multiple machines run at the same time
   - Check existing machines first — never reuse an active machine's ID
6. **Install automation:**
   ```bash
   ./schedule_telegram_job.sh
   ```

**Full instructions:** [.repo-tools/docs/TELEGRAM_SETUP.md](.repo-tools/docs/TELEGRAM_SETUP.md)

**What it does:**
- Checks git log for reviews added in last 24 hours
- Uploads Hebrew reviews → Hebrew channel
- Uploads English reviews → English channel
- Automatically splits long messages
- Prevents duplicates (local log + git-tracked upload ledger, safe across multiple machines)

---

## 💬 Optional: Discord Channel Automation

Want reviews automatically posted to your Discord server at 7:00 PM?

### Quick Setup (20 minutes):

1. **Create Discord Bot** via [Discord Developer Portal](https://discord.com/developers/applications)
2. **Invite bot** to your server with permissions: Send Messages, Create Public Threads, Send Messages in Threads
3. **Get channel ID** (right-click channel → Copy Channel ID, requires Developer Mode)
4. **Configure script:**
   ```bash
   cd .repo-tools/config
   cp discord_config.yaml.template discord_config.yaml
   nano discord_config.yaml  # Fill in bot token and channel ID
   ```
5. **Install automation:**
   ```bash
   .repo-tools/scripts/schedule_discord_job.sh install
   ```

**Full instructions:** [.repo-tools/DISCORD_BOT_SETUP.md](.repo-tools/DISCORD_BOT_SETUP.md)

**What it does:**
- Creates daily threads ("Daily Paper Review: Feb 14, 2026")
- Posts review with Hebrew Telegram, English Telegram, Substack, and GitHub links
- Finds Substack links automatically (with fallback for unnumbered posts)
- Prevents duplicate posts (git-tracked ledger + delay slots + Discord API, safe across multiple machines)
- Requires all links present before posting

**Timeline:**
- 5:00 AM → Reviews processed and pushed to GitHub
- 10:30 AM → Paper recommender (Mon: 20 papers/3 days, Tue-Fri: 10/1 day, skip weekends)
- 3/4/5 PM → Reviews uploaded to Telegram channels
- 3:05/4:05/5:05 PM → Twitter thread generated
- 7:00 PM → Discord post

---

## 📖 Daily Workflow

### Option 1: Fully Automatic (Recommended)

1. Save new review files to `~/ReviewsInbox/`:
   - `Review_574.docx` (Hebrew)
   - `Review_574_english.docx` (English, optional)

2. Go to sleep 😴

3. Wake up - reviews are already processed and pushed to GitHub! ☕

### Option 2: Manual Processing

```bash
# Process immediately (don't wait for 5 AM)
python3 .repo-tools/scripts/daily_review_processor.py

# Or use launchd to trigger the job now
launchctl start com.user.daily-review-processor
```

---

## 🔍 Monitoring & Logs

### View Logs

```bash
# Live monitoring
tail -f .repo-tools/logs/daily_processor.log

# View errors
cat .repo-tools/logs/daily_processor_error.log

# Check recent activity
tail -50 .repo-tools/logs/daily_processor.log
```

### Check Job Status

```bash
# Is the job loaded?
launchctl list | grep daily-review

# When will it run next?
launchctl list com.user.daily-review-processor
```

---

## 🛠️ Management Commands

### Daily Automation

```bash
# Enable (if disabled)
cd .repo-tools/scripts
./schedule_daily_job.sh

# Disable temporarily
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Re-enable
launchctl load ~/Library/LaunchAgents/com.user.daily-review-processor.plist

# Uninstall completely
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist
rm ~/Library/LaunchAgents/com.user.daily-review-processor.plist
```

### Test Commands

```bash
# Dry run (see what would happen)
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Process now
python3 .repo-tools/scripts/daily_review_processor.py

# Update metadata manually
python3 .repo-tools/scripts/update_metadata.py

# Run repo-auto tool
./repo-auto run
```

---

## 🔧 Troubleshooting

### Job Not Running

**Problem:** Job doesn't process files at 5 AM

**Solution:**
```bash
# 1. Check if job is loaded
launchctl list | grep daily-review

# 2. Check logs for errors
cat .repo-tools/logs/daily_processor_error.log

# 3. Test manually
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# 4. Reinstall job
cd .repo-tools/scripts
./schedule_daily_job.sh
```

### Git Push Fails

**Problem:** Files are committed but not pushed

**Solution:**
```bash
# 1. Check SSH key works
ssh -T git@github.com

# 2. Push manually
git push

# 3. If SSH key missing, add it:
# Generate new key (if needed)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub:
cat ~/.ssh/id_ed25519.pub
# Copy and paste to: https://github.com/settings/keys
```

### Conversion Fails

**Problem:** DOCX files don't convert to markdown

**Solution:**
```bash
# 1. Test converter manually
python3 .repo-tools/scripts/convert_docx_to_md.py ~/ReviewsInbox/Review_XXX.docx /tmp/test.md

# 2. Check DOCX file is valid
# Open in Microsoft Word to verify

# 3. Check Python dependencies
python3 -c "import zipfile, xml.etree.ElementTree; print('OK')"
```

### Duplicates Being Processed

**Problem:** Same review processed multiple times

**Solution:**
This shouldn't happen - the script checks for duplicates automatically.

```bash
# Verify deduplication works
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Should show: "Review_XXX already exists in repo, skipping"
```

### Pre-Commit Hook Not Working

**Problem:** Metadata doesn't update on commit

**Solution:**
```bash
# 1. Check hook exists
ls -la .git/hooks/pre-commit

# 2. Check it's executable
chmod +x .git/hooks/pre-commit

# 3. Test manually
python3 .repo-tools/scripts/update_metadata.py

# 4. Check hook syntax
bash -n .git/hooks/pre-commit
```

---

## 📂 File Locations Reference

```
~/Personal/repos/scientific-resources/
├── .repo-tools/
│   ├── scripts/
│   │   ├── daily_review_processor.py    # Main automation
│   │   ├── update_metadata.py           # Metadata updater
│   │   ├── convert_docx_to_md.py        # DOCX converter
│   │   ├── telegram_uploader.py         # Telegram upload
│   │   ├── discord_poster.py            # Discord posting
│   │   ├── substack_scraper.py          # Substack link finder
│   │   ├── paper_recommender/           # Daily arXiv paper recommender
│   │   ├── schedule_daily_job.sh        # Daily job scheduler
│   │   ├── schedule_telegram_job.sh     # Telegram job scheduler
│   │   ├── schedule_discord_job.sh      # Discord job scheduler
│   │   ├── README.md                     # Full docs
│   │   └── QUICKSTART.md                 # Quick reference
│   ├── config/
│   │   ├── discord_config.yaml          # Discord config (gitignored)
│   │   └── telegram_config.yaml         # Telegram config (gitignored)
│   ├── logs/
│   │   ├── daily_processor.log           # Main log
│   │   ├── telegram_uploads.log          # Telegram log
│   │   ├── discord_posts.log             # Discord log
│   │   └── daily_processor_error.log     # Error log
│   └── install.sh                        # Main installer
├── .git/hooks/
│   └── pre-commit                        # Auto-metadata update
├── mike-paper-reviews-all/
│   ├── split-reviews-docx/              # Source DOCX files
│   ├── split-hebrew-reviews-md/         # Hebrew markdown
│   ├── split-english-reviews-md/        # English markdown
│   └── reviews_metadata/                # Auto-generated metadata
└── ~/Library/LaunchAgents/
    ├── com.user.daily-review-processor.plist   # Daily processing
    ├── com.user.telegram-review-uploader.plist # Telegram upload
    ├── com.user.discord-review-poster.plist    # Discord posting
    └── com.user.paper-recommender.plist        # Paper recommender (on wake)
```

---

## 🎯 What Gets Automated

### Pre-Commit Hook (Always Active)
When you commit Hebrew review markdown files:
- ✅ Extracts paper titles and links
- ✅ Updates `paper_with_links.csv`
- ✅ Updates `all_paper_titles.txt`
- ✅ Updates `clean_titles_for_search.txt`
- ✅ Updates `reviews_from_208_titles.txt`
- ✅ Updates README.md statistics
- ✅ Adds all metadata files to the same commit

### Daily Job (5:00 AM)
Every morning at 5 AM:
- ✅ Scans ~/ReviewsInbox for new Review_XXX.docx files
- ✅ Checks for duplicates (skips existing reviews)
- ✅ Copies Hebrew DOCX to repo
- ✅ Converts Hebrew DOCX → Markdown
- ✅ Converts English DOCX → Markdown (if exists)
- ✅ Adds "Review XXX: TITLE" header
- ✅ Git commit with descriptive message
- ✅ Metadata auto-updates (via pre-commit hook)
- ✅ Git pull --rebase --autostash (syncs with other machines first)
- ✅ Git push to GitHub
- ✅ Logs everything

### GitHub Actions (On Push)
When you push to main branch:
- ✅ Runs repo-auto tool
- ✅ Updates README statistics
- ✅ Updates cosmic-neural-header.svg
- ✅ Commits and pushes changes

### Telegram Upload Job (3:00/4:00/5:00 PM) - Optional
If configured, uploads reviews to Telegram channels:
- ✅ Checks git log for reviews added in last 24 hours
- ✅ Reads markdown from repo
- ✅ Checks for duplicates (local log + git-tracked upload ledger, safe across multiple machines)
- ✅ Splits long messages at paragraph boundaries
- ✅ Uploads Hebrew reviews → Hebrew channel
- ✅ Uploads English reviews → English channel
- ✅ Supports Telegram markdown formatting
- ✅ Logs all uploads

**Setup:** See [.repo-tools/docs/TELEGRAM_SETUP.md](.repo-tools/docs/TELEGRAM_SETUP.md)

### Discord Posting Job (7:00 PM) - Optional
If configured, posts reviews to Discord in daily threads:
- ✅ Creates daily thread ("Daily Paper Review: Feb 14, 2026")
- ✅ Posts with all links: Telegram (Hebrew + English), Substack, GitHub
- ✅ Finds Substack links automatically via API (with fallback for unnumbered posts)
- ✅ Prevents duplicate posts (git-tracked ledger + delay slots + Discord API, safe across multiple machines)
- ✅ Requires all links present before posting
- ✅ Backup run at 6 PM catches late Substack posts

**Setup:** See [.repo-tools/DISCORD_BOT_SETUP.md](.repo-tools/DISCORD_BOT_SETUP.md)

### Paper Recommender (On Wake, Once Per Day) - Optional
Daily arXiv paper recommender — picks top 10 papers matching Mike's interests:
- ✅ Fetches recent papers from arXiv (cs.LG, cs.CL, cs.AI, cs.CV, stat.ML)
- ✅ Ranks by relevance using Claude Haiku (~$0.07/run, ~$2/month)
- ✅ Sends top 10 picks to review_testing_eng Telegram channel
- ✅ Cross-machine dedup via git-tracked `last_run.txt` (safe across multiple machines)
- ✅ Runs on first Mac wake via launchd `RunAtLoad`

**Setup:**
```bash
cd .repo-tools/scripts/paper_recommender
cp config.yaml.template config.yaml
# Edit config.yaml — add Anthropic API key (or set ANTHROPIC_API_KEY env var)
# Telegram bot token and channel ID are pre-filled for review_testing_eng

# Install launchd job
cp com.user.paper-recommender.plist.template ~/Library/LaunchAgents/com.user.paper-recommender.plist
launchctl load ~/Library/LaunchAgents/com.user.paper-recommender.plist

# Test
cd .repo-tools/scripts
python3 -m paper_recommender.recommender --dry-run
```

---

## 📝 File Naming Requirements

For automatic processing, files in ~/ReviewsInbox must follow this pattern:

✅ **Correct:**
- `Review_574.docx` (Hebrew)
- `Review_574_english.docx` (English)
- `Review_575.docx`
- `review_576.docx` (lowercase works too)

❌ **Incorrect:**
- `Review574.docx` (missing underscore)
- `Review_574_v2.docx` (extra text)
- `Paper_574.docx` (wrong prefix)

---

## 🔐 Security Notes

- **Git credentials:** Ensure SSH key or credential helper is configured for push access
- **File permissions:** All scripts are executable by owner only
- **launchd permissions:** Runs as user-level LaunchAgent (no sudo needed)
- **Data safety:** Script never deletes files, only copies and creates

---

## 📚 Additional Resources

- **Quick Reference:** `.repo-tools/scripts/QUICKSTART.md`
- **Full Documentation:** `.repo-tools/scripts/README.md`
- **Main README:** `README.md` (Daily Review Automation section)
- **Configuration:** `.repo-tools/config.yaml`

---

## ✨ Tips & Best Practices

1. **Leave files in ReviewsInbox** - The script won't delete them, safe to keep
2. **Check logs regularly** - Catch issues early
3. **Test with dry-run first** - When unsure, use `--dry-run` flag
4. **Monitor first few days** - Ensure automation works as expected
5. **Keep laptop plugged in** - Ensure it runs the 5 AM job
6. **Don't disable sleep completely** - launchd will wake the system if needed (on some macOS configurations)

---

## 🎉 Success Indicators

You'll know everything is working when:
- ✅ New DOCX files appear in `split-reviews-docx/`
- ✅ Markdown files created in `split-hebrew-reviews-md/`
- ✅ Git commits appear in history with "automated daily processing"
- ✅ GitHub shows recent pushes from your laptop
- ✅ Logs show successful processing
- ✅ Metadata files stay up-to-date

---

## 🆘 Need Help?

If you encounter issues:
1. Check logs: `tail -f .repo-tools/logs/daily_processor.log`
2. Run dry-run: `python3 .repo-tools/scripts/daily_review_processor.py --dry-run`
3. Review troubleshooting section above
4. Check `.repo-tools/scripts/README.md` for detailed docs

---

**Last Updated:** February 2026
**Repository:** https://github.com/merlihson/scientific-resources
**System:** macOS with launchd
