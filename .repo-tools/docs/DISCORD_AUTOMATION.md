# Discord Automation - Complete Guide

## Overview

Automated system that posts paper review links to Discord in organized daily threads at 7:00 PM.

**NEW: Thread-Based Organization**
- Creates daily thread: "Daily Paper Review: {date}"
- Posts review message inside the thread
- Keeps channel organized with one thread per day

Each Discord post includes:
- 📢 Header: "New paper review published"
- 📄 Review title
- 🇮🇱 Hebrew Telegram link
- 🇬🇧 English Telegram link
- 📝 Substack post link
- 📖 GitHub links (Hebrew & English)

---

## Daily Workflow

```
5:00 AM   → Process new reviews from ReviewsInbox (Primary)
            Convert DOCX → Markdown
            Commit to GitHub

6:00 AM   → Process reviews (Backup #1)
            Catches any missed reviews

8:00 AM   → Process reviews (Backup #2)
            Additional safety net

9:00 AM   → Process reviews (Backup #3)
            Final check before Telegram

3:00 PM   → Upload to Telegram channels (Hebrew + English) (Primary)
            ✨ Message IDs automatically captured
            Saved to: telegram_message_ids.json

3:05 PM   → Twitter Thread Generation (Primary)
            Generate thread content
            Post to Telegram for manual Twitter posting

4:00 PM   → Upload to Telegram (Backup #1)
            Same process, catches any missed reviews

4:05 PM   → Twitter Thread Generation (Backup #1)
            Same process

5:00 PM   → Upload to Telegram (Backup #2)
            Same process

5:05 PM   → Twitter Thread Generation (Backup #2)
            Same process

7:00 PM   → Post to Discord 🎯
            ├─ Load Telegram links from JSON
            ├─ Scrape Substack for latest post
            ├─ Create daily thread "Daily Paper Review: {date}"
            ├─ Format message with all 5 links
            ├─ Post to thread via Discord Bot API
            └─ Log to discord_posts.log
```

---

## System Components

### 1. **telegram_uploader.py** (Modified)
- Uploads reviews to Telegram at 11:00 AM
- **NEW**: Captures message_id from Telegram API response
- **NEW**: Saves message IDs to `telegram_message_ids.json`
- **NEW**: Supports public channel links (`https://t.me/username/message_id`)

### 2. **substack_scraper.py** (New)
- Fetches your Substack homepage via API
- Searches for "Review XXX" pattern in titles/subtitles
- Returns the canonical URL for matching posts

### 3. **discord_poster.py** (Updated)
- Main automation script using Discord Bot API
- Creates daily threads for organized posting
- Loads Telegram links from JSON
- Calls Substack scraper to get post URL
- Formats Discord message with rich text (5 links total)
- Posts via Discord Bot API to thread
- Tracks posted reviews (deduplication via local log + Discord channel API check, safe across multiple machines)
- Includes validation and error handling

### 4. **Scheduled Job**
- LaunchAgent: `com.user.discord-review-poster`
- Runs at 7:00 PM daily
- Location: `~/Library/LaunchAgents/`

---

## Configuration Files

### `.repo-tools/config/discord_config.yaml`
```yaml
discord:
  # Bot configuration (required for thread creation)
  bot_token: "YOUR_BOT_TOKEN_HERE"
  channel_id: "YOUR_CHANNEL_ID_HERE"
  thread_name_format: "Daily Paper Review: {date}"

  # Deprecated (kept for backward compatibility)
  webhook_url: "https://discord.com/api/webhooks/..."

substack:
  base_url: "https://aiwithmike.substack.com"

github:
  repo_url: "https://github.com/merlihson/scientific-resources"
  hebrew_path: "mike-paper-reviews-all/split-hebrew-reviews-md"
  english_path: "mike-paper-reviews-all/split-english-reviews-md"

settings:
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 30
```

**Note:** `discord_config.yaml` is in `.gitignore` (contains secrets). See `.repo-tools/DISCORD_BOT_SETUP.md` for setup instructions.

### `.repo-tools/scripts/telegram_config.yaml`
```yaml
hebrew_channel:
  bot_token: "..."
  channel_id: "-1003714004500"
  username: "review_testing_heb"  # NEW: Public channel

english_channel:
  bot_token: "..."
  channel_id: "-1003744896293"
  username: "review_testing_eng"  # NEW: Public channel
```

---

## Data Files

### `.repo-tools/logs/telegram_message_ids.json`
**Automatically created by telegram_uploader.py**

Format:
```json
{
  "574": {
    "hebrew": {
      "message_id": 904,
      "username": "review_testing_heb",
      "link": "https://t.me/review_testing_heb/904",
      "timestamp": "2026-02-07T11:00:00"
    },
    "english": {
      "message_id": 7,
      "username": "review_testing_eng",
      "link": "https://t.me/review_testing_eng/7",
      "timestamp": "2026-02-07T11:00:05"
    }
  }
}
```

### `.repo-tools/logs/discord_posts.log`
**Tracks which reviews have been posted to Discord**

Format:
```
2026-02-07 12:00:15 | Review_574 | success
2026-02-07 12:00:45 | Review_575 | success
```

---

## Managing the Scheduled Job

### Check Status
```bash
cd /Users/michaelerlihson/Personal/repos/scientific_repo
.repo-tools/scripts/schedule_discord_job.sh status
```

### View Logs
```bash
.repo-tools/scripts/schedule_discord_job.sh logs
```

### Test (Dry Run)
```bash
.repo-tools/scripts/schedule_discord_job.sh test
```

### Uninstall
```bash
.repo-tools/scripts/schedule_discord_job.sh uninstall
```

### Reinstall
```bash
.repo-tools/scripts/schedule_discord_job.sh install
```

---

## Manual Commands

### Post Specific Review to Discord
```bash
source .repo-tools/.venv/bin/activate
python3 .repo-tools/scripts/discord_poster.py --review 574
```

### Dry Run (Shows What Would Be Posted)
```bash
python3 .repo-tools/scripts/discord_poster.py --dry-run
```

### Test Discord Bot Token
```bash
python3 .repo-tools/scripts/discord_poster.py --test-bot-token
```

### Test Thread Creation
```bash
python3 .repo-tools/scripts/discord_poster.py --test-create-thread
```

### Find Latest Substack Post
```bash
python3 .repo-tools/scripts/substack_scraper.py --find-latest
```

### Find Specific Review on Substack
```bash
python3 .repo-tools/scripts/substack_scraper.py --review 574
```

---

## Telegram Channel Setup

### Public vs Private Channels

**PUBLIC channels** (Recommended - Current Setup):
- ✅ Anyone can access message links
- ✅ Links work for all Discord users
- ✅ Format: `https://t.me/username/message_id`
- ✅ Simpler and more reliable

**Current usernames:**
- Hebrew: `review_testing_heb`
- English: `review_testing_eng`

**To change usernames:**
1. Open Telegram → Channel settings → Edit
2. Change username
3. Update `telegram_config.yaml` with new username
4. Restart scheduled job: `./schedule_discord_job.sh install`

---

## Discord Thread & Message Format

**Thread Name:**
```
Daily Paper Review: Feb 12, 2026
```

**Message inside thread:**
```
📢 New paper review published:
📄 Review 574: Scaling Embedding Outperforms Scaling Experts in Language Models

🇮🇱 Hebrew: https://t.me/review_testing_heb/904
🇬🇧 English: https://t.me/review_testing_eng/7
📝 Substack: https://aiwithmike.substack.com/p/review-574

📖 Review Files (GitHub):
🇮🇱 Hebrew: https://github.com/merlihson/scientific-resources/.../Review_574.md
🇬🇧 English: https://github.com/merlihson/scientific-resources/.../Review_574.md
```

**Benefits of Thread-Based Posting:**
- ✅ Organized by date - easy to find specific day's review
- ✅ Keeps main channel clean
- ✅ Discussions stay contained within thread
- ✅ Better for community engagement

---

## Troubleshooting

### Discord Post Didn't Appear

**Check 1: Is the job running?**
```bash
.repo-tools/scripts/schedule_discord_job.sh status
```

**Check 2: View logs**
```bash
.repo-tools/scripts/schedule_discord_job.sh logs
```

**Check 3: Test manually**
```bash
python3 .repo-tools/scripts/discord_poster.py --dry-run
```

### Telegram Links Not Working

**Issue**: Links show "member-only" error
**Solution**: Make sure channels are PUBLIC with usernames set

**Verify in telegram_config.yaml:**
```yaml
hebrew_channel:
  username: "review_testing_heb"  # Must be set
```

### Substack Link Not Found

**Issue**: Discord post not created, log shows "Substack link not found"
**Reason**: Review not yet published to Substack

**Solutions:**
1. Wait for Substack to be published, then run again at 7:00 PM
2. Manually post after publishing to Substack:
   ```bash
   python3 .repo-tools/scripts/discord_poster.py --review 574
   ```

### Thread Creation Failed

**Issue**: Log shows "Failed to create thread"
**Reason**: Bot missing permissions or invalid channel ID

**Solutions:**
1. Test bot token: `python3 discord_poster.py --test-bot-token`
2. Test thread creation: `python3 discord_poster.py --test-create-thread`
3. Verify bot has permissions:
   - Send Messages
   - Create Public Threads
   - Send Messages in Threads
   - Embed Links
4. Check bot is still in the server
5. Verify channel_id in `discord_config.yaml`

### Duplicate Posts

**Issue**: Same review posted multiple times
**Solution**: The system tracks posted reviews in `discord_posts.log`

To reset:
```bash
rm .repo-tools/logs/discord_posts.log
```

---

## Key Files Reference

```
.repo-tools/
├── config/
│   ├── discord_config.yaml          # Discord webhook + Substack URL
│   └── telegram_config.yaml         # Telegram tokens + usernames
│
├── scripts/
│   ├── discord_poster.py            # Main Discord posting script
│   ├── substack_scraper.py          # Scrapes Substack for post links
│   ├── telegram_uploader.py         # Modified: captures message IDs
│   ├── schedule_discord_job.sh      # Job management script
│   └── com.user.discord-review-poster.plist.template
│
├── logs/
│   ├── telegram_message_ids.json    # Captured Telegram links
│   ├── discord_posts.log            # Discord posting history
│   ├── discord_poster.log           # Main execution logs
│   └── discord_poster_error.log     # Error logs
│
└── docs/
    └── DISCORD_AUTOMATION.md         # This file
```

---

## Dependencies

All dependencies are in `.repo-tools/.venv/`:
- `requests` - HTTP requests (Telegram, Discord, Substack)
- `PyYAML` - Config file parsing
- `beautifulsoup4` - HTML parsing (Substack fallback)

---

## Testing the Complete Workflow

### 1. Upload Test Review to Telegram
```bash
# Modify a review file to trigger git log detection
touch mike-paper-reviews-all/split-hebrew-reviews-md/Review_999.md

# Upload to Telegram (captures message IDs)
python3 .repo-tools/scripts/telegram_uploader.py --hours 1
```

### 2. Verify Message IDs Captured
```bash
cat .repo-tools/logs/telegram_message_ids.json
# Should show Review_999 with links
```

### 3. Test Discord Post (Dry Run)
```bash
python3 .repo-tools/scripts/discord_poster.py --review 999 --dry-run
```

### 4. Real Discord Post
```bash
python3 .repo-tools/scripts/discord_poster.py --review 999
```

### 5. Verify in Discord
- Check Discord channel for the message
- Click all 3 links to verify they work

---

## Future Enhancements (Optional)

- **Rich embeds**: Use Discord embeds instead of plain text
- **Thumbnails**: Include paper preview images
- **Mentions**: Tag specific Discord roles for notifications
- **Reactions**: Auto-add emoji reactions for feedback
- ~~**Threading**: Post each review in a thread~~ ✅ **IMPLEMENTED**

---

## Support

For issues or questions:
1. Check logs: `.repo-tools/scripts/schedule_discord_job.sh logs`
2. Test manually: `.repo-tools/scripts/schedule_discord_job.sh test`
3. Check job status: `.repo-tools/scripts/schedule_discord_job.sh status`

---

**System Status**: ✅ Fully Automated with Thread-Based Posting

**Last Updated**: 2026-02-12 (Added Discord Bot API and thread creation)
