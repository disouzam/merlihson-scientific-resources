# 📱 Telegram Channel Automation Setup

Complete guide for setting up automated review uploads to Telegram channels.

---

## Overview

This automation uploads paper reviews to your Telegram channels every 30 min from 11:00 AM to 3:00 PM daily (stops once succeeded):
- Hebrew reviews → Hebrew channel
- English reviews → English channel
- Automatically splits long messages
- Prevents duplicates
- Markdown formatting support

---

## 🚀 Quick Setup (20 minutes)

### Prerequisites
- Telegram account
- Two Telegram channels (Hebrew + English)
- macOS with Python 3.8+

---

## Step 1: Create Telegram Bots (5 minutes)

You need two bots: one for Hebrew channel, one for English channel.

### Create Hebrew Bot

1. **Open Telegram** and search for [@BotFather](https://t.me/botfather)

2. **Start conversation** and send:
   ```
   /newbot
   ```

3. **Choose a name** (shown to users):
   ```
   Hebrew Reviews Bot
   ```
   *(or any name you prefer)*

4. **Choose a username** (must end in 'bot'):
   ```
   hebrew_reviews_bot
   ```
   *(must be unique globally)*

5. **Save the bot token** - BotFather will reply with:
   ```
   Done! Your bot is ready. Use this token to access the HTTP API:
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567

   Keep your token secure and store it safely, it can be used by anyone to control your bot.
   ```

   **⚠️ IMPORTANT:** Copy this token somewhere safe! You'll need it later.

### Create English Bot

Repeat the same process:
1. Send `/newbot` to @BotFather again
2. Name: `English Reviews Bot` (or your choice)
3. Username: `english_reviews_bot` (must be unique)
4. **Save this token too!**

✅ **You now have 2 bot tokens**

---

## Step 2: Add Bots to Your Channels (3 minutes)

### For Hebrew Channel:

1. **Open your Hebrew channel** in Telegram
2. **Tap channel name** → Administrators → Add Administrator
3. **Search for** your Hebrew bot username (`@hebrew_reviews_bot`)
4. **Add bot as admin**
5. **Set permissions:**
   - ✅ Post Messages (required)
   - ❌ Everything else (not needed)
6. **Save**

### For English Channel:

Repeat for English channel:
1. Open English channel
2. Add your English bot as administrator
3. Enable "Post Messages" permission only

✅ **Both bots are now admins**

---

## Step 3: Get Channel IDs (5 minutes)

Telegram channels have numeric IDs (usually negative numbers like `-1001234567890`).

### Get Hebrew Channel ID:

1. **Send a test message** to your Hebrew channel
   - Type anything, e.g., "test"

2. **Open your browser** and visit:
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
   Replace `<BOT_TOKEN>` with your Hebrew bot token (the full token from Step 1)

   Example:
   ```
   https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/getUpdates
   ```

3. **Find the channel ID** in the JSON response:
   ```json
   {
     "ok": true,
     "result": [{
       "channel_post": {
         "chat": {
           "id": -1001234567890,
           "title": "My Hebrew Channel",
           "type": "channel"
         },
         "text": "test"
       }
     }]
   }
   ```

4. **Copy the ID number**: `-1001234567890`

### Get English Channel ID:

Repeat the same process:
1. Send test message to English channel
2. Visit: `https://api.telegram.org/bot<ENGLISH_BOT_TOKEN>/getUpdates`
3. Find and copy the channel ID

✅ **You now have:**
- 2 bot tokens
- 2 channel IDs

---

## Step 4: Configure the Script (5 minutes)

### Create Config File:

```bash
cd /Users/michaelerlihson/Personal/repos/scientific-resources/.repo-tools/scripts

# Copy template
cp telegram_config.yaml.template telegram_config.yaml
```

### Edit Config File:

Open `telegram_config.yaml` in your editor:

```bash
nano telegram_config.yaml
# or
code telegram_config.yaml
# or
open -a TextEdit telegram_config.yaml
```

### Fill in Your Credentials:

Replace the placeholders with your actual values:

```yaml
hebrew_channel:
  bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  channel_id: "-1001234567890"

english_channel:
  bot_token: "987654321:XYZabcDEFghiJKLmno"
  channel_id: "-1009876543210"

settings:
  max_message_length: 4096
  check_history_depth: 100
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 5
```

**⚠️ Important:**
- Keep the quotes around tokens and IDs
- Channel IDs are usually negative numbers
- Don't commit this file to git (it's in .gitignore)

**Save and close** the file.

---

## Step 5: Install Automation (2 minutes)

### Run Setup Script:

```bash
cd /Users/michaelerlihson/Personal/repos/scientific-resources/.repo-tools/scripts
./schedule_telegram_job.sh
```

The script will:
- ✅ Check your config file
- ✅ Install Python dependencies
- ✅ Test the uploader
- ✅ Schedule the every 30 min from 11:00 AM to 3:00 PM daily jobs

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📱 Telegram Review Uploader Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Repository: /Users/michaelerlihson/Personal/repos/scientific-resources
Schedule: Every 30 min from 11:00 AM to 3:00 PM

🔍 Checking Python dependencies...
✓ Dependencies already installed

🧪 Testing script...
✓ Script test passed

📝 Creating launchd configuration...
✓ Configuration created

🚀 Loading job into launchd...
✓ Job loaded successfully

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ✅ Telegram uploader scheduled successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ✅ Setup Complete!

Your automation is now active and will run every 30 min from 11:00 AM to 3:00 PM daily (stops once succeeded).

---

## 🧪 Testing

### Test in Dry-Run Mode:

```bash
python3 .repo-tools/scripts/telegram_uploader.py --dry-run
```

This will:
- Check git log for recent reviews
- Show what would be uploaded
- **NOT** actually send messages

**Expected output:**
```
2026-02-05 15:00:00 - INFO - Starting Telegram review uploader
2026-02-05 15:00:00 - INFO - Repository: /Users/michaelerlihson/Personal/repos/scientific-resources
2026-02-05 15:00:00 - INFO - Checking reviews from last 24 hours
2026-02-05 15:00:01 - INFO - Found 1 new Hebrew reviews, 1 new English reviews (last 24 hours)
2026-02-05 15:00:01 - INFO - [DRY RUN] Would upload Review_574 to hebrew channel
2026-02-05 15:00:01 - INFO - [DRY RUN]   Content length: 3245 characters
2026-02-05 15:00:01 - INFO - [DRY RUN]   Would split into 1 message(s)
```

### Test for Real (Optional):

```bash
# Upload reviews from last 24 hours
python3 .repo-tools/scripts/telegram_uploader.py

# Or check last 48 hours
python3 .repo-tools/scripts/telegram_uploader.py --hours 48
```

### Trigger the Job Immediately:

```bash
# Don't wait for scheduled time - run now
launchctl start com.user.telegram-review-uploader
```

### Check Logs:

```bash
# View execution log
tail -f .repo-tools/logs/telegram_uploader.log

# View upload history
cat .repo-tools/logs/telegram_uploads.log
```

---

## 📅 Daily Workflow

Once set up, your workflow is:

**5:00 AM** → Daily processor commits reviews to repo (Primary)
**6:00 AM** → Daily processor backup run #1
**8:00 AM** → Daily processor backup run #2
**9:00 AM** → Daily processor backup run #3
**11:00 AM-3:00 PM (every 30 min)** → Telegram uploader reads from repo and posts to channels (stops once succeeded)
**4:00 PM** → Telegram uploader backup run #1
**5:00 PM** → Telegram uploader backup run #2

**You do nothing!** Just drop DOCX files in ReviewsInbox anytime. ☕

---

## 🔧 Management Commands

### Check Job Status:

```bash
# Is the job loaded?
launchctl list | grep telegram-review-uploader
```

### View Logs:

```bash
# Live monitoring
tail -f .repo-tools/logs/telegram_uploader.log

# Upload history
cat .repo-tools/logs/telegram_uploads.log

# Errors only
cat .repo-tools/logs/telegram_uploader_error.log
```

### Run Manually:

```bash
# Dry-run (safe, no messages sent)
python3 .repo-tools/scripts/telegram_uploader.py --dry-run

# Run for real
python3 .repo-tools/scripts/telegram_uploader.py

# Check specific time range
python3 .repo-tools/scripts/telegram_uploader.py --hours 48
```

### Disable/Enable Job:

```bash
# Disable (stop automatic uploads)
launchctl unload ~/Library/LaunchAgents/com.user.telegram-review-uploader.plist

# Enable (start automatic uploads)
launchctl load ~/Library/LaunchAgents/com.user.telegram-review-uploader.plist
```

### Uninstall:

```bash
launchctl unload ~/Library/LaunchAgents/com.user.telegram-review-uploader.plist
rm ~/Library/LaunchAgents/com.user.telegram-review-uploader.plist
```

---

## 🐛 Troubleshooting

### Problem: "Config file not found"

**Solution:**
```bash
cd .repo-tools/scripts
cp telegram_config.yaml.template telegram_config.yaml
# Edit telegram_config.yaml with your credentials
```

### Problem: "Config contains placeholder values"

**Solution:**
Edit `telegram_config.yaml` and replace all `YOUR_*_HERE` with actual values.

### Problem: "Bot is not admin of channel"

**Solution:**
1. Open your Telegram channel
2. Go to Administrators
3. Add your bot as administrator
4. Enable "Post Messages" permission

### Problem: "Invalid bot token"

**Solution:**
- Check your bot token in telegram_config.yaml
- Ensure it's copied correctly from @BotFather
- No extra spaces or quotes
- Format should be: `123456789:ABCdef...`

### Problem: "Channel not found"

**Solution:**
- Verify channel ID is correct (usually negative: `-1001234567890`)
- Make sure bot is admin of the channel
- Try getting the channel ID again using getUpdates

### Problem: "No new reviews found"

This is normal! It means:
- No reviews were added to repo in last 24 hours
- Or all reviews were already uploaded

**To test with older reviews:**
```bash
python3 telegram_uploader.py --hours 168  # Check last week
```

### Problem: Messages not uploading

**Check:**
1. **Bot permissions:** Is bot admin with "Post Messages"?
2. **Network:** Is internet working?
3. **Logs:** Check `.repo-tools/logs/telegram_uploader_error.log`
4. **Config:** Verify bot tokens and channel IDs

**Test manually:**
```bash
python3 telegram_uploader.py --dry-run
# Should show what would be uploaded
```

### Problem: Messages split incorrectly

Long reviews are automatically split at paragraph boundaries. This is normal for reviews over 4096 characters.

**Each part gets numbered:** `(1/3)`, `(2/3)`, `(3/3)`

---

## 🔐 Security Best Practices

### Protect Your Credentials:

✅ **DO:**
- Keep `telegram_config.yaml` private
- Never commit it to git (it's in .gitignore)
- Use `chmod 600 telegram_config.yaml` to restrict access
- Regenerate tokens if compromised

❌ **DON'T:**
- Share your bot tokens publicly
- Commit credentials to GitHub
- Take screenshots showing bot tokens
- Post tokens in Slack/Discord/etc.

### Bot Permissions:

- Only give bots "Post Messages" permission
- Don't give admin rights beyond what's needed
- Separate bots for Hebrew/English (not required but safer)

---

## 📊 How It Works

### Workflow:

1. **every 30 min from 11:00 AM to 3:00 PM daily** → launchd triggers script
2. **Check git log** → Find reviews added in last 24 hours
3. **Read markdown files** → From `split-hebrew-reviews-md/` and `split-english-reviews-md/`
4. **Duplicate check (per-channel, 3 methods):**
   - Check local log (`.repo-tools/logs/telegram_uploads.log`)
   - Check git-tracked ledger for the specific channel (cross-machine)
   - Check Telegram API getUpdates (best-effort fallback)
5. **Split if needed** → Messages over 4096 chars split at paragraphs
6. **Upload** → Send to appropriate channel via Telegram Bot API
7. **Log** → Record upload in local log

### Duplicate Detection:

**Multi-layer safety (per-channel):**
- **Layer 1:** Local log file (fast, machine-local)
- **Layer 2:** Git-tracked ledger for the specific channel (cross-machine, authoritative)
- **Layer 3:** Telegram API getUpdates (best-effort fallback for uploads not yet in ledger)
- **Layer 4:** Last-second git pull + ledger re-check right before sending
- **Layer 5:** Push retry 3x with backoff (5s, 10s) after sending — ensures ledger is locked on remote

Each layer checks only the relevant channel (Hebrew or English). If any layer detects a duplicate, upload is skipped.

### Message Splitting:

Telegram limit: 4096 characters per message

**Algorithm:**
1. Split review into paragraphs (`\n\n`)
2. Combine paragraphs until near limit
3. Never split mid-paragraph
4. Add part numbers: `(1/3)`, `(2/3)`, etc.

---

## 📁 File Locations

```
scientific-resources/
├── .repo-tools/
│   ├── scripts/
│   │   ├── telegram_uploader.py              # Main script
│   │   ├── telegram_config.yaml              # YOUR CONFIG (gitignored)
│   │   ├── telegram_config.yaml.template     # Template
│   │   ├── schedule_telegram_job.sh          # Setup script
│   │   └── com.user.telegram-review-uploader.plist.template
│   ├── logs/
│   │   ├── telegram_uploader.log             # Execution log
│   │   ├── telegram_uploader_error.log       # Error log
│   │   └── telegram_uploads.log              # Upload history
│   └── docs/
│       └── TELEGRAM_SETUP.md                 # This file
└── ~/Library/LaunchAgents/
    └── com.user.telegram-review-uploader.plist  # launchd job
```

---

## 🆕 Setup on New Laptop

When you get a new laptop:

```bash
# 1. Clone repo
git clone git@github.com:merlihson/scientific-resources.git
cd scientific-resources

# 2. Create config file
cd .repo-tools/scripts
cp telegram_config.yaml.template telegram_config.yaml

# 3. Fill in your credentials
nano telegram_config.yaml
# (Use same bot tokens and channel IDs as before)

# 4. Run setup
./schedule_telegram_job.sh

# 5. Done!
```

**Your bot tokens and channel IDs stay the same** - just copy them from your old laptop or password manager.

---

## ❓ FAQ

**Q: Do I need to create new bots for each laptop?**
A: No! Use the same bot tokens on all your laptops.

**Q: Can I have multiple channels?**
A: Yes, create more bots and add them to `telegram_config.yaml`.

**Q: What if I delete a message from the channel?**
A: The script checks the git-tracked ledger (primary) and local log. If the review is in the ledger, it won't re-upload even if the message is deleted from the channel. To force re-upload, remove the review number from the ledger JSON file.

**Q: Can I change the upload time?**
A: Yes, edit the plist file and change Hour from 11 to your preferred hour.

**Q: What happens if my laptop is off every 30 min from 11:00 AM-3:00 PM?**
A: The job won't run. Run manually when laptop is on, or it will catch up next day.

**Q: Can I upload old reviews?**
A: Yes! Use `--hours` flag: `python3 telegram_uploader.py --hours 720` (30 days)

**Q: Does it upload DOCX files or text?**
A: It uploads the text content as messages, not files.

**Q: What if a review has special formatting?**
A: Markdown formatting is preserved (bold, italic, links).

**Q: Can I test without actually posting?**
A: Yes! Use `--dry-run` flag.

---

## 🎉 Success Indicators

You'll know it's working when:

✅ Script runs successfully in dry-run mode
✅ Manual upload test works
✅ Messages appear in your channels
✅ Duplicates are properly skipped
✅ Long reviews split correctly
✅ Logs show successful uploads
✅ Job runs automatically every 30 min from 11:00 AM-3:00 PM

---

## 📞 Need Help?

If you're stuck:

1. **Check logs:** `.repo-tools/logs/telegram_uploader_error.log`
2. **Test manually:** `python3 telegram_uploader.py --dry-run`
3. **Verify config:** Check bot tokens and channel IDs
4. **Test bot connection:** Send message to channel manually as bot

---

**Last Updated:** February 2026
**Repository:** https://github.com/merlihson/scientific-resources
