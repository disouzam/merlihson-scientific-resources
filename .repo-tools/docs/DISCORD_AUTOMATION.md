# Discord Automation - Complete Guide

## Overview

Automated system that posts paper review links to Discord daily at 12:00 PM.

Each Discord post includes:
- 📢 Header: "New paper review published"
- 📄 Review title
- 🇮🇱 Hebrew Telegram link
- 🇬🇧 English Telegram link
- 📝 Substack post link

---

## Daily Workflow

```
5:00 AM   → Process new reviews from Downloads (Primary)
            Convert DOCX → Markdown
            Commit to GitHub

6:00 AM   → Process reviews (Backup #1)
            Catches any missed reviews

8:00 AM   → Process reviews (Backup #2)
            Additional safety net

9:00 AM   → Process reviews (Backup #3)
            Final check before Telegram

11:00 AM  → Upload to Telegram channels (Hebrew + English)
            ✨ Message IDs automatically captured
            Saved to: telegram_message_ids.json

12:00 PM  → Post to Discord 🎯 (THIS IS NEW!)
            ├─ Load Telegram links from JSON
            ├─ Scrape Substack for latest post
            ├─ Format message with all 3 links
            ├─ Post to Discord webhook
            └─ Log to discord_posts.log

6:00 PM   → Backup Discord post (if 12:00 PM failed)
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

### 3. **discord_poster.py** (New)
- Main automation script
- Loads Telegram links from JSON
- Calls Substack scraper to get post URL
- Formats Discord message with rich text
- Posts via webhook
- Tracks posted reviews (deduplication)

### 4. **Scheduled Job** (New)
- LaunchAgent: `com.user.discord-review-poster`
- Runs at 12:00 PM and 12:30 PM daily
- Location: `~/Library/LaunchAgents/`

---

## Configuration Files

### `.repo-tools/config/discord_config.yaml`
```yaml
discord:
  webhook_url: "https://discord.com/api/webhooks/..."

substack:
  base_url: "https://aiwithmike.substack.com"

settings:
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 30
```

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
cd /Users/michaelerlihson/Personal/Projects/scientific_repo
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

### Test Discord Webhook
```bash
python3 .repo-tools/scripts/discord_poster.py --test-webhook
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

## Discord Message Format

```
📢 New paper review published:
📄 Review 574: Scaling Embedding Outperforms Scaling Experts in Language Models


🇮🇱 Hebrew: https://t.me/review_testing_heb/904

🇬🇧 English: https://t.me/review_testing_eng/7

📝 Substack: https://aiwithmike.substack.com/p/who-wins-at-scale-n-gram-embedding

```

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

**Issue**: Discord post shows "Substack: (pending)"
**Reason**: Review not yet published to Substack

**Solutions:**
1. Wait and run backup at 12:30 PM
2. Manually post after publishing to Substack:
   ```bash
   python3 .repo-tools/scripts/discord_poster.py --review 574
   ```

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
- **Threading**: Post each review in a thread
- **Reactions**: Auto-add emoji reactions for feedback

---

## Support

For issues or questions:
1. Check logs: `.repo-tools/scripts/schedule_discord_job.sh logs`
2. Test manually: `.repo-tools/scripts/schedule_discord_job.sh test`
3. Check job status: `.repo-tools/scripts/schedule_discord_job.sh status`

---

**System Status**: ✅ Fully Automated

**Last Updated**: 2026-02-07
