---
name: discord-post
description: Post paper reviews to Discord or manage Discord posting automation
---

# Discord Review Posting Skill

Post paper review links (Telegram Hebrew, Telegram English, and Substack) to Discord.

## User Commands

The user can say:
- "post review 574 to discord"
- "discord post review 574"
- "test discord posting"
- "check discord posts"
- "show recent discord posts"
- "test discord webhook"
- "check discord automation status"
- "view discord logs"
- "why didn't review 575 post to discord?"

## What This Skill Does

### Posting Actions
1. **Post specific review** - Posts one review to Discord immediately
2. **Post all new reviews** - Posts all reviews from last 24 hours
3. **Dry-run test** - Shows what would be posted without actually posting
4. **Test webhook** - Sends test message to verify Discord connection

### Status & Debugging
5. **Check automation status** - Shows if scheduled job is running
6. **View recent posts** - Lists recently posted reviews
7. **View logs** - Shows execution logs
8. **Troubleshoot** - Diagnoses why a review wasn't posted

## Implementation Details

### Core Files
- **Script:** `.repo-tools/scripts/discord_poster.py`
- **Config:** `.repo-tools/config/discord_config.yaml`
- **Logs:** `.repo-tools/logs/discord_posts.log`
- **Scheduler:** `.repo-tools/scripts/schedule_discord_job.sh`

### Safety Features
✅ **No duplicates** - Each review posted only once (tracked in log)
✅ **Complete validation** - Requires ALL 3 links (Hebrew, English, Substack)
✅ **Time-based** - Only posts reviews from last 24 hours
✅ **Most recent first** - Prioritizes newest reviews
✅ **Error handling** - Logs failures, retries at next scheduled time

### Automated Schedule
- **12:00 PM (Noon)** - Primary run (1 hour after Telegram upload at 11 AM)
- **6:00 PM** - Backup run (catches reviews if Substack wasn't ready)

### Message Format
```
📢 New paper review published:
📄 Review 574: Scaling Embedding Outperforms Scaling Experts


🇮🇱 Hebrew: https://t.me/review_testing_heb/904

🇬🇧 English: https://t.me/review_testing_eng/7

📝 Substack: https://aiwithmike.substack.com/p/review-574

```

## Action Instructions

When invoked, parse user intent and execute:

### 1. Post Specific Review
**Trigger:** "post review 574 to discord"

```bash
cd /Users/michaelerlihson/Personal/Projects/scientific_repo
source .repo-tools/.venv/bin/activate
python3 .repo-tools/scripts/discord_poster.py --review 574
```

**Expected output:**
- Success: "✓ Successfully posted Review_574 to Discord"
- Missing links: "Review_574 missing Telegram links" or "Substack link not found"
- Already posted: "Review_574 already posted to Discord"

**Response to user:**
- On success: "✓ Posted Review 574 to Discord with Hebrew Telegram, English Telegram, and Substack links"
- On failure: Explain what's missing and suggest next steps

### 2. Post All New Reviews
**Trigger:** "post new reviews to discord" or "discord post all"

```bash
python3 .repo-tools/scripts/discord_poster.py
```

**Response:** "Posted {count} review(s) to Discord: Review_574, Review_575"

### 3. Dry-Run Test
**Trigger:** "test discord posting"

```bash
python3 .repo-tools/scripts/discord_poster.py --dry-run
```

**Response:** Show formatted message preview and confirm which reviews would be posted

### 4. Test Webhook
**Trigger:** "test discord webhook"

```bash
python3 .repo-tools/scripts/discord_poster.py --test-webhook
```

**Response:** "✓ Webhook test successful - check your Discord channel for test message"

### 5. Check Automation Status
**Trigger:** "check discord automation" or "is discord posting working?"

```bash
.repo-tools/scripts/schedule_discord_job.sh status
```

**Response:**
- If active: "✓ Discord posting job is active. Next run: 12:00 PM and 6:00 PM daily"
- If not active: "⚠️ Job not loaded. Run: `.repo-tools/scripts/schedule_discord_job.sh install`"

### 6. View Recent Posts
**Trigger:** "show recent discord posts" or "what was posted to discord?"

```bash
tail -20 .repo-tools/logs/discord_posts.log
```

**Response:** Format and show recent posts in human-readable format

### 7. View Logs
**Trigger:** "show discord logs" or "discord poster logs"

```bash
.repo-tools/scripts/schedule_discord_job.sh logs
```

**Response:** Show last 20 lines of logs, highlight any errors

### 8. Troubleshoot Missing Post
**Trigger:** "why didn't review 575 post to discord?"

**Steps:**
1. Check if review exists in telegram_message_ids.json
2. Check if Substack link exists
3. Check if already posted in discord_posts.log
4. Check if within 24-hour window

```bash
# Check Telegram links
cat .repo-tools/logs/telegram_message_ids.json | grep "575"

# Check if already posted
grep "Review_575" .repo-tools/logs/discord_posts.log

# Test specific review
python3 .repo-tools/scripts/discord_poster.py --review 575 --dry-run
```

**Response:** Provide specific diagnosis:
- "Review 575 hasn't been uploaded to Telegram yet"
- "Review 575 is missing Substack link - publish to Substack first"
- "Review 575 was already posted on [date/time]"
- "Review 575 is older than 24 hours"

## Error Scenarios & Solutions

### Missing Telegram Links
**Symptom:** "Review_XXX missing Telegram links"
**Cause:** Telegram upload hasn't completed or failed
**Solution:**
1. Check telegram_uploads.log
2. Wait for 11 AM Telegram upload
3. Re-run discord poster at 6 PM (automatic)

### Missing Substack Link
**Symptom:** "Substack link not found"
**Cause:** Review not yet published to Substack
**Solution:**
1. Publish review to Substack
2. Wait for 6 PM automatic retry
3. Or manually post: `python3 discord_poster.py --review XXX`

### Already Posted
**Symptom:** "Review_XXX already posted to Discord"
**Cause:** Deduplication working correctly
**Solution:** No action needed (this is expected behavior)

### Webhook Error
**Symptom:** "Error posting to Discord"
**Cause:** Invalid webhook URL or Discord API issue
**Solution:**
1. Check webhook URL in discord_config.yaml
2. Test webhook: `python3 discord_poster.py --test-webhook`
3. Verify webhook still exists in Discord channel settings

### Old Review (>24 hours)
**Symptom:** Review not posted despite having all links
**Cause:** Review older than 24 hours
**Solution:**
1. This is by design (only posts recent reviews)
2. To post old review: `python3 discord_poster.py --review XXX`

## Response Templates

### Success
```
✓ Successfully posted Review_{num} to Discord!

Message includes:
  📢 "New paper review published"
  📄 Review title
  🇮🇱 Hebrew Telegram link
  🇬🇧 English Telegram link
  📝 Substack link

The review is now visible in your Discord channel.
```

### Dry-Run
```
Dry-run complete! Here's what would be posted:

Review 574: Scaling Embedding Outperforms Scaling Experts

Links verified:
  ✓ Hebrew Telegram
  ✓ English Telegram
  ✓ Substack

Run without --dry-run to actually post.
```

### Missing Link
```
Cannot post Review_{num} - missing required links:

Status:
  🇮🇱 Hebrew Telegram: {✓ or ✗}
  🇬🇧 English Telegram: {✓ or ✗}
  📝 Substack: {✓ or ✗}

Next steps:
  {specific action needed}

The system will automatically retry at 6:00 PM.
```

### Already Posted
```
Review_{num} was already posted to Discord on {date} at {time}.

To see the message, check your Discord channel around that time.

Note: The system prevents duplicate posts automatically.
```

## Integration with Daily Workflow

```
 5:00 AM → Reviews processed from Downloads
11:00 AM → Telegram upload (captures message IDs)
12:00 PM → Discord Post #1 ✅ (Primary - 1 hour buffer for Substack)
 6:00 PM → Discord Post #2 ✅ (Backup - catches late Substack posts)
```

## Configuration

### Discord Config
Location: `.repo-tools/config/discord_config.yaml`
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

### Telegram Config
Location: `.repo-tools/scripts/telegram_config.yaml`
```yaml
hebrew_channel:
  username: "review_testing_heb"  # Public channel
english_channel:
  username: "review_testing_eng"  # Public channel
```

## Monitoring & Maintenance

### Health Checks
```bash
# Job status
.repo-tools/scripts/schedule_discord_job.sh status

# Recent activity
tail .repo-tools/logs/discord_posts.log

# Error log (should be empty)
cat .repo-tools/logs/discord_poster_error.log
```

### Manual Operations
```bash
# Reinstall job
.repo-tools/scripts/schedule_discord_job.sh install

# Uninstall job
.repo-tools/scripts/schedule_discord_job.sh uninstall

# Manual post (bypasses 24-hour check)
python3 .repo-tools/scripts/discord_poster.py --review 574

# Test without posting
python3 .repo-tools/scripts/discord_poster.py --dry-run
```

## Key Features Summary

✅ **Fully Automated** - Runs at 12 PM and 6 PM daily
✅ **Safe** - No duplicates, validates all links
✅ **Smart** - Only posts reviews from last 24 hours
✅ **Complete** - Requires all 3 links before posting
✅ **Reliable** - Error handling and automatic retries
✅ **Trackable** - Full logging of all operations
✅ **Public Links** - Anyone in Discord can access Telegram links

## Notes for Assistant

- Always check logs when troubleshooting
- Provide specific, actionable solutions
- Show command outputs when relevant
- Explain what the system is doing and why
- If uncertain, suggest checking logs first
- Remember: System is designed to be self-healing (retries at 6 PM)
