---
name: twitter-threads
description: Generate and post Twitter threads from Hebrew reviews to Telegram
---

# Twitter Thread Generator Skill

Automatically generates clickbait-style Twitter threads from Hebrew reviews and posts them to Telegram for manual Twitter posting.

## User Commands

The user can say:
- "generate twitter thread for review 577"
- "post twitter threads to telegram"
- "test twitter thread builder"
- "check twitter thread automation"
- "view twitter thread logs"

## What This Skill Does

### Core Functionality
1. **Generate Twitter threads** - Converts Hebrew reviews to 500-char tweet threads
2. **Clickbait optimization** - Adds engaging hooks, emojis, CTAs
3. **Auto-post to Telegram** - Posts threads to Hebrew test channel
4. **Manual Twitter posting** - User copies from Telegram to Twitter

### Features
- ✅ **500 chars/tweet** - Optimized for Twitter Premium
- ✅ **~10-12 tweets/thread** - Manageable size
- ✅ **Clickbait hooks** - "Mind-blowing insights", "Game-changing paper"
- ✅ **Strategic emojis** - 🤖 models, ⚠️ errors, 🎯 accuracy
- ✅ **Strong CTAs** - "RT if you learned something"
- ✅ **Image generation** - Optional title cards (not used in automation)

## Implementation Details

### Core Files
- **Script:** `.repo-tools/scripts/twitter_thread_builder.py`
- **Auto-poster:** `.repo-tools/scripts/twitter_thread_auto_poster.py`
- **Image gen:** `.repo-tools/scripts/twitter_image_generator.py`
- **Plan:** `.repo-tools/plans/TWITTER_THREADS_PLAN.md`
- **Logs:** `.repo-tools/logs/twitter_threads_posted.log`

### Automated Schedule
- **3:00/4:00/5:00 PM** - Review uploads to Telegram
- **3:05/4:05/5:05 PM** - Twitter thread auto-generates and posts to Telegram

### Thread Format (500 chars/tweet)

**Example thread structure:**
```
Tweet 1 (Hook):
🧠 Mind-blowing insights on LLM failures 🧵
📄 Review 577: A MODEL OF ERRORS IN TRANSFORMERS
🇮🇱 Full Hebrew review below ⬇️
#AI #MachineLearning

Tweet 2 (Intro):
סקירה 577 - למה הפוסט הזה חשוב? 🤔
➡️ תובנות מהפכניות על LLMs
➡️ פיזיקה של שגיאות
➡️ פתרונות מעשיים
בואו נצלול פנימה 🏊‍♂️

Tweets 3-10 (Content with emojis):
📊 [Full paragraph content - up to 500 chars]

Tweet 11 (CTA):
🎓 רוצים לקרוא את המחקר המלא?
📄 Paper: https://arxiv.org/abs/...
💬 מה דעתכם? כתבו בתגובות!
🔄 RT אם למדתם משהו חדש
✅ סוף Thread
```

## Action Instructions

### 1. Generate Thread for Specific Review
**Trigger:** "generate twitter thread for review 577"

```bash
cd /Users/michaelerlihson/Personal/repos/scientific_repo
python3 .repo-tools/scripts/twitter_thread_builder.py --review 577 --clickbait
```

**Expected output:**
- Thread built: 10-12 tweets
- All tweets under 500 characters
- Formatted output ready to copy

### 2. Post Thread to Telegram
**Trigger:** "post twitter thread to telegram"

```bash
python3 .repo-tools/scripts/twitter_thread_auto_poster.py --review 577
```

**Expected output:**
- Thread posted to Hebrew Telegram channel
- Ready for manual copy/paste to Twitter

### 3. Dry Run (Preview)
**Trigger:** "test twitter thread builder"

```bash
python3 .repo-tools/scripts/twitter_thread_auto_poster.py --dry-run --review 577
```

**Response:** Show what would be posted without actually posting

### 4. Check Automation Status
**Trigger:** "check twitter thread automation"

```bash
launchctl list | grep twitter-thread
```

**Response:**
- If active: "✓ Twitter thread job is active. Next run: 3:05 PM daily"
- If not active: "⚠️ Job not loaded. Reinstall with: launchctl load ~/Library/LaunchAgents/com.user.twitter-thread-poster.plist"

### 5. View Logs
**Trigger:** "show twitter thread logs"

```bash
tail -20 .repo-tools/logs/twitter_thread_auto_poster.log
```

**Response:** Show recent thread generations

### 6. Manual Twitter Posting Instructions
**Trigger:** "how do I post the thread to twitter?"

**Response:**
```
1. Open Telegram → Hebrew test channel
2. Find the Twitter thread (posted automatically)
3. Copy Tweet 1 → Post on Twitter
4. Click "Reply" → Copy Tweet 2 → Post
5. Repeat for all ~11 tweets

OR use Twitter's thread composer (faster):
- Start new tweet
- Click "+" to add to thread
- Paste all 11 tweets
- Post entire thread with one click
```

## Integration with Daily Workflow

```
5:00 AM      → Process reviews from ReviewsInbox ✅
3/4/5 PM     → Upload to Telegram (Hebrew + English) ✅
3:05/4:05/5:05 PM → Generate Twitter thread → Post to Telegram ✅
7:00 PM      → Post to Discord threads ✅
```

## Error Scenarios & Solutions

### Thread Not Generated
**Symptom:** No thread in Telegram after 3:05 PM
**Cause:** Review not uploaded or automation not running
**Solution:**
1. Check if review uploaded: `grep "Review_XXX" .repo-tools/logs/telegram_message_ids.json`
2. Check automation: `launchctl list | grep twitter-thread`
3. Check logs: `tail .repo-tools/logs/twitter_thread_auto_poster.log`
4. Manual run: `python3 .repo-tools/scripts/twitter_thread_auto_poster.py --review XXX`

### Thread Too Long
**Symptom:** Thread has >15 tweets
**Cause:** Review is very long
**Solution:**
- This is normal for comprehensive reviews
- Consider summarizing key points manually
- Current limit: 500 chars/tweet (optimized for Premium)

### Telegram Posting Failed
**Symptom:** Log shows "Failed to post"
**Cause:** Telegram API issue or config problem
**Solution:**
1. Test Telegram config: Check `.repo-tools/scripts/telegram_config.yaml`
2. Manual test: `python3 .repo-tools/scripts/twitter_thread_auto_poster.py --review XXX`
3. Check Telegram bot token is valid

### Missing Emojis or Formatting
**Symptom:** Thread looks plain, missing clickbait elements
**Cause:** Using simple mode instead of clickbait mode
**Solution:**
- Automation uses clickbait mode by default
- Manual: Use `--clickbait` flag (default)
- Simple mode: Use `--simple` flag

## Configuration

### Tweet Length
**Default:** 500 characters (optimized for Twitter Premium)

**To change:**
Edit `.repo-tools/scripts/twitter_thread_builder.py`:
```python
# Line ~163
def split_into_tweets(text: str, max_chars: int = 500):  # Change 500 to desired length
```

**Recommended values:**
- 270 chars - Standard Twitter (no Premium)
- 500 chars - Premium sweet spot (current) ✅
- 800 chars - Longer tweets, fewer in thread
- 4000 chars - Max Premium (not recommended, kills engagement)

### Clickbait Hooks
**Location:** `.repo-tools/scripts/twitter_thread_builder.py` line ~179

```python
hooks = [
    "🔥 Thread about transformers you NEED to read",
    "🧠 Mind-blowing insights on LLM failures",
    # Add more hooks here
]
```

## Manual Commands

### Generate thread (manual)
```bash
python3 .repo-tools/scripts/twitter_thread_builder.py --review 577 --output thread.txt
```

### Generate with images
```bash
python3 .repo-tools/scripts/twitter_thread_builder.py --review 577 --images
# Images saved to: /tmp/twitter_images/
```

### Post to Telegram (manual)
```bash
python3 .repo-tools/scripts/twitter_thread_auto_poster.py --review 577
```

### Force repost (even if already posted)
```bash
python3 .repo-tools/scripts/twitter_thread_auto_poster.py --review 577 --force
```

## Key Features Summary

✅ **Automatic generation** - Runs 5 min after Telegram upload
✅ **Clickbait optimized** - Engaging hooks and formatting
✅ **Premium optimized** - 500 chars/tweet sweet spot
✅ **Easy to post** - Copy/paste from Telegram to Twitter
✅ **No working code touched** - Completely separate system
✅ **Manual control** - User chooses when to post to Twitter

## Response Templates

### Success
```
✓ Twitter thread generated for Review_{num}!

Thread posted to Telegram (Hebrew channel):
  📊 11 tweets total
  📝 500 chars max per tweet
  🔥 Clickbait-optimized

Ready to copy/paste to Twitter!
```

### Dry Run
```
Dry-run complete! Thread preview:

Review 577: 11 tweets
Total characters: 3,467

Would post to Telegram Hebrew channel.
Run without --dry-run to actually post.
```

### Already Posted
```
Review_{num} thread was already posted to Telegram on {date} at {time}.
(Checked git-tracked ledger + delay slots + Telegram channel history + local log — safe across multiple machines)

To repost anyway: python3 twitter_thread_auto_poster.py --review {num} --force
```

## Monitoring & Maintenance

### Daily Check (Automated)
```bash
# Check if automation ran
grep "Twitter Thread Posting Summary" .repo-tools/logs/twitter_thread_auto_poster.log | tail -5
```

### Weekly Check
```bash
# Count threads posted this week
grep "success" .repo-tools/logs/twitter_threads_posted.log | wc -l
```

## Notes for Assistant

- System is completely independent of existing automation
- NO modifications were made to telegram_uploader.py, discord_poster.py, or daily_review_processor.py
- User has Twitter Premium (4000 char limit) but uses 500 chars for optimal engagement
- Threads are posted to Telegram for manual Twitter posting (not automated to Twitter)
- Free tier alternative available (no Twitter API needed)

## Safety & Independence

✅ **No changes to working code:**
- daily_review_processor.py - Untouched
- telegram_uploader.py - Untouched
- discord_poster.py - Untouched

✅ **Can be disabled without breaking anything:**
```bash
launchctl unload ~/Library/LaunchAgents/com.user.twitter-thread-poster.plist
```

✅ **Rollback available:**
- Simply remove new files
- Existing automation continues working
