# Discord Bot Setup Guide

## ✅ Completed Steps

1. **Backups Created:**
   - `discord_poster.py.webhook-backup` - Original working script
   - `discord_config.yaml.backup` - Original config

2. **Code Updated:**
   - Added bot API functions (create_thread, post_to_thread)
   - Updated DiscordConfig to load bot_token and channel_id
   - Modified post_review_to_discord() to create threads
   - Added test functions for bot token and thread creation

3. **Configuration Template Updated:**
   - Added bot_token field
   - Added channel_id field
   - Added thread_name_format field
   - Kept webhook_url for backward compatibility

---

## 🎯 Next Steps: What YOU Need to Do

### Step 1: Create Discord Bot (15 minutes)

**Go to:** https://discord.com/developers/applications

1. **Create Application:**
   - Click "New Application"
   - Name: `Paper Review Bot` (or any name)
   - Click "Create"

2. **Create Bot:**
   - Left sidebar → "Bot"
   - Click "Add Bot"
   - Confirm: "Yes, do it!"

3. **Configure Bot:**
   - **Username:** `Paper Review Bot`
   - **Public Bot:** ❌ Disable (uncheck it)
   - **Privileged Gateway Intents:** All disabled (we don't need them)

4. **Copy Bot Token** (CRITICAL):
   - Click "Reset Token" (or "Copy" if first time)
   - **SAVE THIS TOKEN** - You'll need it in Step 3
   - Format: Long alphanumeric string (about 70+ characters)

### Step 2: Set Permissions & Invite Bot

**Still in Developer Portal:**

1. **OAuth2 → URL Generator:**
   - **Scopes:**
     - ✅ `bot`

   - **Bot Permissions:**
     - ✅ Send Messages
     - ✅ Create Public Threads
     - ✅ Send Messages in Threads
     - ✅ Embed Links

2. **Copy OAuth URL** (bottom of page)

3. **Invite Bot to Server:**
   - Paste OAuth URL in browser
   - Select your server
   - Click "Authorize"
   - Complete CAPTCHA

4. **Verify Bot Joined:**
   - Go to Discord server
   - Check member list
   - Bot shows as "Offline" (normal - not running yet)

### Step 3: Get Channel ID

**In Discord:**

1. **Enable Developer Mode** (if not already):
   - Discord Settings → App Settings → Advanced
   - ✅ Enable "Developer Mode"

2. **Copy Channel ID:**
   - Right-click `#paper-reviews` channel
   - Click "Copy Channel ID" (bottom of menu)
   - **SAVE THIS ID** - You'll need it next
   - Format: `1234567890123456789` (18-19 digits)

### Step 4: Update Configuration File

**Edit:** `/Users/mike_erlihson/personal/repos/scientific-resources/.repo-tools/config/discord_config.yaml`

Replace these values:
```yaml
discord:
  # Replace with your bot token from Step 1
  bot_token: "YOUR_BOT_TOKEN_HERE"

  # Replace with your channel ID from Step 3
  channel_id: "YOUR_CHANNEL_ID_HERE"
```

**Example:**
```yaml
discord:
  bot_token: "YOUR_ACTUAL_BOT_TOKEN_FROM_DISCORD_DEVELOPER_PORTAL"
  channel_id: "1234567890123456789"
  thread_name_format: "Daily Paper Review: {date}"
```

---

## 🧪 Testing (After Configuration)

Once you've updated the config file, run these tests:

### Test 1: Bot Token Validation
```bash
cd /Users/mike_erlihson/personal/repos/scientific-resources/.repo-tools/scripts
python3 discord_poster.py --test-bot-token
```

**Expected output:**
```
✓ Bot token valid!
  Bot username: Paper Review Bot
  Bot ID: 1234567890
```

### Test 2: Thread Creation
```bash
python3 discord_poster.py --test-create-thread
```

**Expected output:**
```
✓ Test thread created successfully: Test Thread - 2026-02-12 12:00:00
  Thread ID: 1234567890123456789
```

**Check Discord:** You should see a new test thread in your channel.

### Test 3: Dry Run (Full Workflow)
```bash
python3 discord_poster.py --dry-run
```

**Expected output:**
```
[DRY RUN] Would create thread and post to Discord:
  Thread name: Daily Paper Review: Feb 12, 2026

📢 New paper review published:
...
```

### Test 4: Post Specific Review
```bash
python3 discord_poster.py --review 577
```

**Expected:**
- Creates thread "Daily Paper Review: Feb 12, 2026"
- Posts Review 577 inside thread
- Check Discord to verify

---

## 🔧 Rollback (If Something Goes Wrong)

If bot approach fails, restore original files:

```bash
cd /Users/mike_erlihson/personal/repos/scientific-resources/.repo-tools/scripts
cp discord_poster.py.webhook-backup discord_poster.py

cd ../config
cp discord_config.yaml.backup discord_config.yaml

# Test webhook still works
python3 /Users/mike_erlihson/personal/repos/scientific-resources/.repo-tools/scripts/discord_poster.py --test-webhook
```

---

## 📋 What Changed

### discord_poster.py
- **Added functions:**
  - `create_thread()` - Creates Discord thread via bot API
  - `post_to_thread()` - Posts message to thread
  - `get_thread_name()` - Generates thread name with date
  - `test_bot_token()` - Validates bot token
  - `test_create_thread()` - Tests thread creation

- **Modified functions:**
  - `DiscordConfig.__init__()` - Now loads bot_token, channel_id, thread_name_format
  - `post_review_to_discord()` - Creates thread first, then posts inside it
  - `main()` - Added test flags (--test-bot-token, --test-create-thread)

### discord_config.yaml
- **New required fields:**
  - `bot_token` - Discord bot token
  - `channel_id` - Channel where threads will be created
  - `thread_name_format` - Template for thread names (default: "Daily Paper Review: {date}")

- **Deprecated field:**
  - `webhook_url` - Kept for backward compatibility, can be removed after testing

---

## 🔒 Security Notes

- ✅ Bot token is like a password - never share it
- ✅ Config file is already in `.gitignore` - won't be committed
- ✅ If token is exposed, regenerate it in Developer Portal
- ✅ Bot only has minimal permissions needed

---

## 📅 Expected Behavior

### Before (Webhook):
```
#paper-reviews channel:
├─ 📢 Review 574: Title... (direct message)
├─ 📢 Review 575: Title... (direct message)
├─ 📢 Review 576: Title... (direct message)
```

### After (Bot with Threads):
```
#paper-reviews channel:
├─ 🧵 Daily Paper Review: Feb 10, 2026
│   └─ 📢 Review 574: Title...
├─ 🧵 Daily Paper Review: Feb 11, 2026
│   └─ 📢 Review 575: Title...
├─ 🧵 Daily Paper Review: Feb 12, 2026
│   └─ 📢 Review 576: Title...
```

---

## ❓ Troubleshooting

### "Bot token invalid"
- Check token is copied correctly (no spaces)
- Regenerate token in Developer Portal if needed

### "Missing Access" error when creating thread
- Verify bot has "Create Public Threads" permission
- Check bot was invited with correct OAuth URL
- Verify channel_id is correct

### "Cannot send messages in a thread"
- Verify bot has "Send Messages in Threads" permission
- Check bot is still in the server

### Thread created but message not posted
- Check bot token is valid
- Verify bot has "Send Messages in Threads" permission
- Check logs for error details

---

## 📞 Ready for Next Steps?

Once you've completed Steps 1-4 above and have:
- ✅ Bot token
- ✅ Channel ID
- ✅ Updated discord_config.yaml

Let me know and we can run the tests together!
