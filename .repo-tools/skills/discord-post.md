---
name: discord-post
description: Post paper reviews to Discord or manage Discord posting automation
---

# Discord Review Posting Skill

Post paper review links (Telegram Hebrew, Telegram English, and Substack) to Discord in organized daily threads.

## User Commands

The user can say:
- "post review 574 to discord"
- "discord post review 574"
- "test discord posting"
- "check discord posts"
- "show recent discord posts"
- "test discord bot token"
- "test discord thread creation"
- "check discord automation status"
- "view discord logs"
- "why didn't review 575 post to discord?"

## What This Skill Does

### Posting Actions
1. **Post specific review** - Creates daily thread and posts review inside it
2. **Post all new reviews** - Posts all reviews newer than the latest one already on Discord (each in daily thread)
3. **Dry-run test** - Shows what would be posted without actually posting
4. **Test bot token** - Verifies Discord bot authentication
5. **Test thread creation** - Creates a test thread to verify permissions

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
✅ **No duplicates** - Git-tracked ledger + delay slots + last-second re-check + Discord API + local log (safe across multiple machines)
✅ **Complete validation** - Requires ALL 3 links (Hebrew, English, Substack)
✅ **Forward-only** - Posts reviews with number > max(already_posted), so transient failures (Substack down, network) recover on later runs instead of aging out
✅ **Most recent first** - Prioritizes newest reviews
✅ **Error handling** - Logs failures, retries at next scheduled time

### Automated Schedule
- **Every 30 min from 4:00 PM to 7:00 PM** - Retries until it succeeds (after Telegram uploads at 11:00 AM-3:00 PM)

### Thread & Message Format

**Thread Name:** `Daily Paper Review: Feb 12, 2026`

**Message inside thread:**
```
📢 New paper review published:

📄 Review 574: Scaling Embedding Outperforms Scaling Experts

✈️ Telegram:
🇮🇱 Hebrew: https://t.me/MathyAIwithMike/123
🇬🇧 English: https://t.me/review_testing_eng/7

📝 Substack: https://aiwithmike.substack.com/p/review-574

📖 Review Files (GitHub):
🇮🇱 Hebrew: https://github.com/merlihson/scientific-resources/.../Review_574.md
🇬🇧 English: https://github.com/merlihson/scientific-resources/.../Review_574.md
```

## Action Instructions

When invoked, parse user intent and execute:

### 1. Post Specific Review
**Trigger:** "post review 574 to discord"

```bash
cd /Users/michaelerlihson/Personal/repos/scientific_repo
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

### 4. Test Bot Token
**Trigger:** "test discord bot token"

```bash
python3 .repo-tools/scripts/discord_poster.py --test-bot-token
```

**Response:** "✓ Bot token valid - Bot username: Paper Review Bot"

### 5. Test Thread Creation
**Trigger:** "test discord thread creation"

```bash
python3 .repo-tools/scripts/discord_poster.py --test-create-thread
```

**Response:** "✓ Test thread created successfully - check your Discord channel"

### 6. Check Automation Status
**Trigger:** "check discord automation" or "is discord posting working?"

```bash
.repo-tools/scripts/schedule_discord_job.sh status
```

**Response:**
- If active: "✓ Discord posting job is active. Runs every 30 min from 4:00-7:00 PM daily"
- If not active: "⚠️ Job not loaded. Run: `.repo-tools/scripts/schedule_discord_job.sh install`"

### 7. View Recent Posts
**Trigger:** "show recent discord posts" or "what was posted to discord?"

```bash
tail -20 .repo-tools/logs/discord_posts.log
```

**Response:** Format and show recent posts in human-readable format

### 8. View Logs
**Trigger:** "show discord logs" or "discord poster logs"

```bash
.repo-tools/scripts/schedule_discord_job.sh logs
```

**Response:** Show last 20 lines of logs, highlight any errors

### 9. Troubleshoot Missing Post
**Trigger:** "why didn't review 575 post to discord?"

**Steps:**
1. Check if review exists in telegram_message_ids.json
2. Check if Substack link exists
3. Check if already posted in discord_posts.log
4. Check if review_num > max(already_posted) — older reviews are skipped to avoid backfill

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
- "Review 575 is older than the latest already-posted review (skipped to avoid backfill — force with --review 575)"

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

### Bot Token or Permission Error
**Symptom:** "Error creating thread" or "Error posting to Discord"
**Cause:** Invalid bot token, missing permissions, or Discord API issue
**Solution:**
1. Test bot token: `python3 discord_poster.py --test-bot-token`
2. Test thread creation: `python3 discord_poster.py --test-create-thread`
3. Verify bot has required permissions: Send Messages, Create Public Threads, Send Messages in Threads
4. Check bot is still in the server

### Older Than Latest Posted
**Symptom:** Review not posted despite having all links
**Cause:** Review number is below max(already_posted) — skipped to prevent backfilling old reviews after a fresh ledger / clone
**Solution:**
1. To post anyway: `python3 discord_poster.py --review XXX`

## Response Templates

### Success
```
✓ Successfully posted Review_{num} to Discord thread!

Thread created: "Daily Paper Review: {date}"

Message includes:
  📢 "New paper review published"
  📄 Review title
  🇮🇱 Hebrew Telegram link
  🇬🇧 English Telegram link
  📝 Substack link
  📖 GitHub links (Hebrew & English)

The review is now visible in your Discord channel inside today's thread.
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

The system will automatically retry at the next scheduled run.
```

### Already Posted
```
Review_{num} was already posted to Discord on {date} at {time}.

To see the message, check your Discord channel around that time.

Note: The system prevents duplicate posts automatically (checks both local log and Discord channel threads via API, safe across multiple machines). Telegram message IDs are committed+pushed to git after each upload, so Discord can find them from any machine.
```

## Integration with Daily Workflow

```
 5:00 AM → Reviews processed from ReviewsInbox (Primary)
 6:00 AM → Reviews processed from ReviewsInbox (Backup #1)
 8:00 AM → Reviews processed from ReviewsInbox (Backup #2)
 9:00 AM → Reviews processed from ReviewsInbox (Backup #3)
 11:00 AM-3:00 PM (every 30 min) → Telegram upload (captures message IDs, commits+pushes to git)
 4:00-7:00 PM (every 30 min)    → Discord Post (pulls git first, reads Telegram links) ✅
```

## Configuration

### Discord Config
Location: `.repo-tools/config/discord_config.yaml`
```yaml
discord:
  # Bot configuration (required for thread creation)
  bot_token: "YOUR_BOT_TOKEN_HERE"
  channel_id: "YOUR_CHANNEL_ID_HERE"
  thread_name_format: "Daily Paper Review: {date}"

  # Additional channels to cross-post to (optional)
  additional_channels:
    - id: "CHANNEL_ID"
      name: "paper-discussions"

  # Deprecated (kept for backward compatibility)
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
  username: "MathyAIwithMike"  # Real Hebrew channel
english_channel:
  username: "science_and_ai_with_mike_english"  # Real English channel
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

# Manual post (bypasses the forward-only filter)
python3 .repo-tools/scripts/discord_poster.py --review 574

# Test without posting
python3 .repo-tools/scripts/discord_poster.py --dry-run
```

## Key Features Summary

✅ **Thread-Based** - Creates organized daily threads for each review
✅ **Fully Automated** - Runs at 12 PM and 6 PM daily
✅ **Safe** - No duplicates (git-tracked ledger + delay slots + Discord API), validates all links
✅ **Smart** - Only posts reviews newer than the latest one already on Discord (transient failures recover on later runs)
✅ **Complete** - Requires all 5 links before posting (Telegram Hebrew, Telegram English, Substack, GitHub Hebrew, GitHub English)
✅ **Reliable** - Error handling and automatic retries
✅ **Trackable** - Full logging of all operations
✅ **Public Links** - Anyone in Discord can access all links
✅ **Bot-Powered** - Uses Discord Bot API for thread creation

## Notes for Assistant

- Always check logs when troubleshooting
- Provide specific, actionable solutions
- Show command outputs when relevant
- Explain what the system is doing and why
- If uncertain, suggest checking logs first
- Remember: System is designed to be self-healing (retries at 6 PM)
