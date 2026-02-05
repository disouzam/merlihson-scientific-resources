# Plan: Telegram Channel Automation

## Overview
Automate uploading paper reviews to Telegram channels at 11:00 AM daily. Hebrew and English reviews go to separate channels. Includes duplicate detection and automatic message splitting.

---

## Requirements Summary

### User Requirements
1. ✅ **Upload time:** 11:00 AM daily (only if new reviews in Downloads)
2. ✅ **Format:** Text messages with review content (as in DOCX)
3. ✅ **Channels:** Two separate channels (Hebrew + English)
4. ✅ **Message splitting:** Auto-split if review > 4096 characters
5. ✅ **Duplicate prevention:** Check channel history AND local log
6. ✅ **Formatting:** Keep paragraphs separated as in original DOCX
7. ✅ **Portability:** All code in repo for use on other Macs
8. ✅ **No bot setup yet:** Need to create Telegram bots

### Technical Requirements
- Telegram Bot API for posting messages
- Two bot tokens (Hebrew channel + English channel)
- Channel IDs for both channels
- Secure credential storage (not hardcoded)
- Message splitting algorithm (respect 4096 char limit)
- Duplicate detection (dual method)
- Logging of uploads
- launchd scheduler for 11:00 AM

---

## Architecture

### Components

```
.repo-tools/
├── scripts/
│   ├── telegram_uploader.py          # Main upload script
│   ├── schedule_telegram_job.sh      # Setup 11 AM job
│   └── telegram_config.yaml          # User's config (gitignored)
├── logs/
│   ├── telegram_uploads.log          # Local upload history
│   └── telegram_uploader.log         # Execution log
└── docs/
    └── TELEGRAM_SETUP.md              # Complete setup guide
```

### Configuration Files

```
~/Library/LaunchAgents/
└── com.user.telegram-review-uploader.plist  # 11 AM scheduler
```

---

## Implementation Plan

### Phase 1: Telegram Bot Setup (User Task)

#### Step 1.1: Create Hebrew Channel Bot
1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Name: "Hebrew Reviews Bot" (or your choice)
4. Username: `hebrew_reviews_bot` (must end in 'bot')
5. **Save the bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Step 1.2: Create English Channel Bot
1. Message @BotFather again
2. Send `/newbot`
3. Name: "English Reviews Bot"
4. Username: `english_reviews_bot`
5. **Save the bot token**

#### Step 1.3: Get Channel IDs

**For Hebrew Channel:**
1. Add the Hebrew bot as admin to your Hebrew channel
2. Send a test message to the channel
3. Visit: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   (Replace `<BOT_TOKEN>` with your actual token)
4. Find the `"chat":{"id":-1001234567890}` - that's your channel ID
5. **Save the channel ID** (usually negative number)

**For English Channel:**
1. Repeat steps for English bot and English channel

#### Step 1.4: Verify Bot Permissions
- Both bots must be **administrators** in their respective channels
- Required permissions: "Post Messages"

---

### Phase 2: Script Development

#### Script 2.1: `telegram_uploader.py`

**Purpose:** Main automation script that uploads reviews to Telegram

**Functionality:**

1. **Scan Downloads:**
   - Find new `Review_XXX.docx` and `Review_XXX_english.docx` files
   - Determine which reviews are new (not processed yet)

2. **Duplicate Detection (Dual Method):**
   ```python
   def is_already_uploaded(review_num, channel_type):
       # Method 1: Check local log file
       if review_num in read_local_log(channel_type):
           return True

       # Method 2: Check channel history (last 100 messages)
       if review_num in check_channel_history(channel_type):
           return True

       return False
   ```

3. **Extract Text from DOCX:**
   - Reuse `convert_docx_to_md.py` logic
   - Extract paragraphs with proper spacing
   - Preserve line breaks between paragraphs

4. **Message Splitting:**
   ```python
   def split_message(text, max_length=4096):
       """Split text at paragraph boundaries"""
       paragraphs = text.split('\n\n')
       messages = []
       current = ""

       for para in paragraphs:
           if len(current) + len(para) + 2 < max_length:
               current += para + "\n\n"
           else:
               if current:
                   messages.append(current.strip())
               current = para + "\n\n"

       if current:
           messages.append(current.strip())

       return messages
   ```

5. **Upload to Channel:**
   ```python
   def upload_review(review_num, docx_path, bot_token, channel_id, channel_type):
       # Extract text
       text = extract_text_from_docx(docx_path)

       # Check duplicates
       if is_already_uploaded(review_num, channel_type):
           log(f"Review {review_num} already on {channel_type} channel, skipping")
           return False

       # Split if needed
       messages = split_message(text)

       # Add part numbers if multiple messages
       if len(messages) > 1:
           for i, msg in enumerate(messages, 1):
               header = f"📄 Review {review_num} ({i}/{len(messages)})\n\n"
               send_telegram_message(bot_token, channel_id, header + msg)
       else:
           send_telegram_message(bot_token, channel_id, messages[0])

       # Log successful upload
       log_upload(review_num, channel_type)
       return True
   ```

6. **Telegram API Integration:**
   ```python
   def send_telegram_message(bot_token, chat_id, text):
       """Send message via Telegram Bot API"""
       url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
       payload = {
           "chat_id": chat_id,
           "text": text,
           "parse_mode": "Markdown"  # Optional: support markdown formatting
       }
       response = requests.post(url, json=payload)
       return response.json()
   ```

7. **Logging:**
   - Log all uploads to `.repo-tools/logs/telegram_uploads.log`
   - Format: `2026-02-05 11:00:00 | Review_574 | hebrew | success`
   - Execution log: `.repo-tools/logs/telegram_uploader.log`

**Configuration Loading:**
```python
def load_config():
    """Load Telegram credentials from config file"""
    config_path = Path(".repo-tools/scripts/telegram_config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config
```

**Error Handling:**
- Network failures: Log error, retry once, then skip
- DOCX read errors: Log error, skip file
- API errors: Log with error code, skip upload
- Missing config: Exit with helpful error message

---

#### Script 2.2: `telegram_config.yaml.template`

**Purpose:** Template for user configuration (actual file is gitignored)

```yaml
# Telegram Bot Configuration
# Copy this file to telegram_config.yaml and fill in your credentials
# DO NOT commit telegram_config.yaml to git (it's in .gitignore)

hebrew_channel:
  bot_token: "YOUR_HEBREW_BOT_TOKEN_HERE"
  channel_id: "YOUR_HEBREW_CHANNEL_ID_HERE"  # Usually negative number like -1001234567890

english_channel:
  bot_token: "YOUR_ENGLISH_BOT_TOKEN_HERE"
  channel_id: "YOUR_ENGLISH_CHANNEL_ID_HERE"

settings:
  max_message_length: 4096  # Telegram limit
  check_history_depth: 100  # How many recent messages to check for duplicates
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 5
```

---

#### Script 2.3: `schedule_telegram_job.sh`

**Purpose:** Install 11 AM daily job

```bash
#!/bin/bash
# Schedule Telegram Review Uploader
# Runs daily at 11:00 AM

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_NAME="com.user.telegram-review-uploader.plist"
PLIST_TEMPLATE="$REPO_ROOT/.repo-tools/scripts/$PLIST_NAME.template"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "📱 Setting up Telegram review uploader..."
echo ""
echo "Repository: $REPO_ROOT"
echo "Schedule: Every day at 11:00 AM"
echo ""

# Check if config exists
if [ ! -f "$REPO_ROOT/.repo-tools/scripts/telegram_config.yaml" ]; then
    echo "❌ Error: telegram_config.yaml not found!"
    echo ""
    echo "Please create the config file first:"
    echo "  1. cd .repo-tools/scripts"
    echo "  2. cp telegram_config.yaml.template telegram_config.yaml"
    echo "  3. Edit telegram_config.yaml with your bot tokens and channel IDs"
    echo ""
    echo "See .repo-tools/docs/TELEGRAM_SETUP.md for detailed instructions"
    exit 1
fi

# Check Python dependencies
if ! python3 -c "import requests, yaml" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install requests pyyaml
fi

# Unload existing job if present
if launchctl list | grep -q "telegram-review-uploader"; then
    echo "⚠️  Existing job found, unloading..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Create plist from template
sed "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"

# Load job
launchctl load "$PLIST_DEST"

echo ""
echo "✅ Telegram uploader scheduled successfully!"
echo ""
echo "Details:"
echo "  • Runs every day at 11:00 AM"
echo "  • Uploads new reviews to Telegram channels"
echo "  • Hebrew → Hebrew channel, English → English channel"
echo ""
echo "Logs:"
echo "  • Execution: $REPO_ROOT/.repo-tools/logs/telegram_uploader.log"
echo "  • Upload history: $REPO_ROOT/.repo-tools/logs/telegram_uploads.log"
echo ""
echo "Management:"
echo "  • Test now:    launchctl start com.user.telegram-review-uploader"
echo "  • View status: launchctl list | grep telegram"
echo "  • Uninstall:   launchctl unload $PLIST_DEST"
echo ""
```

---

#### Script 2.4: `com.user.telegram-review-uploader.plist.template`

**Purpose:** launchd configuration for 11 AM job

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.telegram-review-uploader</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>REPO_ROOT_PLACEHOLDER/.repo-tools/scripts/telegram_uploader.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>11</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>REPO_ROOT_PLACEHOLDER/.repo-tools/logs/telegram_uploader.log</string>

    <key>StandardErrorPath</key>
    <string>REPO_ROOT_PLACEHOLDER/.repo-tools/logs/telegram_uploader_error.log</string>

    <key>RunAtLoad</key>
    <false/>

    <key>WorkingDirectory</key>
    <string>REPO_ROOT_PLACEHOLDER</string>
</dict>
</plist>
```

---

### Phase 3: Documentation

#### Doc 3.1: `TELEGRAM_SETUP.md`

Complete guide covering:
1. Creating Telegram bots
2. Getting channel IDs
3. Setting up configuration file
4. Installing the automation
5. Testing
6. Troubleshooting
7. Security best practices

---

### Phase 4: Integration with Existing System

#### Update `.gitignore`
```
.repo-tools/scripts/telegram_config.yaml
.repo-tools/logs/telegram_*.log
```

#### Update `install.sh`
Add optional Telegram setup:
```bash
echo ""
echo "Setup Telegram channel automation? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    echo "See .repo-tools/docs/TELEGRAM_SETUP.md for bot setup instructions"
    echo "After setting up bots, run: .repo-tools/scripts/schedule_telegram_job.sh"
fi
```

#### Update `NEW_LAPTOP_SETUP.md`
Add section on Telegram automation setup

---

## Workflow

### Daily Workflow (After Implementation)

**5:00 AM:**
- Daily processor runs
- New reviews processed and pushed to GitHub

**11:00 AM:**
- Telegram uploader runs
- Checks Downloads for new Review_XXX.docx files
- For each new review:
  - Check if already uploaded (local log + channel history)
  - Extract text from DOCX
  - Split message if needed
  - Upload to appropriate channel (Hebrew or English)
  - Log the upload

**User experience:**
- Drop Review_574.docx in Downloads at any time
- 5 AM: Processed and pushed to GitHub
- 11 AM: Uploaded to Telegram Hebrew channel
- Drop Review_574_english.docx
- Next 11 AM: Uploaded to Telegram English channel

---

## Duplicate Detection Logic

### Dual Method for Safety

**Method 1: Local Log File**
- File: `.repo-tools/logs/telegram_uploads.log`
- Format: `timestamp | Review_XXX | hebrew/english | success/failure`
- Check: Linear search through log file
- Fast and always available

**Method 2: Channel History**
- Query last 100 messages from channel via Bot API
- Search for "Review XXX" pattern in message text
- Slower but catches uploads from other sources
- Fallback if log file is lost

**Combined Logic:**
```python
def is_duplicate(review_num, channel_type):
    # Check local log first (fast)
    if in_local_log(review_num, channel_type):
        return True

    # Check channel history (slow but thorough)
    if in_channel_history(review_num, channel_type):
        # Update local log for consistency
        add_to_local_log(review_num, channel_type)
        return True

    return False
```

---

## Message Splitting Algorithm

### Strategy: Split at Paragraph Boundaries

Telegram limit: 4096 characters per message

**Algorithm:**
1. Split text into paragraphs (by `\n\n`)
2. Build messages by adding paragraphs until near limit
3. Never split mid-paragraph (preserves readability)
4. If single paragraph > 4096 chars, split at sentence boundaries
5. Add part numbers: "Review 574 (1/3)", "Review 574 (2/3)", etc.

**Example:**
```
Review 574 (1/2)

[First part of review text with complete paragraphs...]

---

Review 574 (2/2)

[Remaining paragraphs...]
```

---

## Security Considerations

### Credential Storage
- ✅ Bot tokens stored in `telegram_config.yaml` (gitignored)
- ✅ Never commit credentials to git
- ✅ File permissions: `chmod 600 telegram_config.yaml`
- ✅ Template file committed, actual config excluded

### API Security
- ✅ Use HTTPS for all Telegram API calls
- ✅ Validate responses from Telegram API
- ✅ Rate limiting: Max 30 messages/second (Telegram limit)
- ✅ Error handling for failed requests

### Channel Privacy
- ✅ Bots only need "Post Messages" permission
- ✅ No read access required
- ✅ Channel IDs are private (not in code comments)

---

## Testing Strategy

### Unit Tests
1. Test message splitting with various lengths
2. Test duplicate detection with mock log file
3. Test DOCX text extraction
4. Test config loading

### Integration Tests
1. Upload test message to private test channel
2. Verify message splitting works with real Telegram API
3. Test duplicate detection with real channel history
4. Test error handling (invalid token, network failure)

### Manual Testing Checklist
- [ ] Create test bots
- [ ] Create test channels
- [ ] Upload single short review
- [ ] Upload long review (verify splitting)
- [ ] Upload duplicate (verify skipped)
- [ ] Test Hebrew and English separately
- [ ] Test manual trigger
- [ ] Test scheduled job (11 AM)
- [ ] Verify logs written correctly
- [ ] Test on clean repo clone (portability)

---

## Error Handling

### Scenario 1: Network Failure
- **Action:** Log error, retry 2 times with 5 second delay
- **If still fails:** Log failure, continue with next review
- **Recovery:** Next run will retry (duplicate detection prevents re-upload)

### Scenario 2: Invalid Bot Token
- **Action:** Log error with helpful message
- **Exit:** Stop execution, don't process any reviews
- **User action required:** Fix `telegram_config.yaml`

### Scenario 3: Channel Not Found
- **Action:** Log error "Bot is not admin of channel"
- **Exit:** Stop execution
- **User action required:** Add bot as admin to channel

### Scenario 4: DOCX Read Error
- **Action:** Log error for that specific file
- **Continue:** Process next review
- **Log:** Note which file failed for manual investigation

### Scenario 5: Message Too Long (Even After Splitting)
- **Action:** Log warning "Review XXX requires special handling"
- **Fallback:** Upload as multiple messages with smaller chunks
- **Max parts:** 10 messages (if review is EXTREMELY long)

---

## Dependencies

### Python Packages
```
requests>=2.31.0  # Telegram Bot API
pyyaml>=6.0       # Config file parsing
```

Add to `.repo-tools/requirements.txt`

### System Requirements
- macOS (for launchd)
- Python 3.8+
- Internet connection
- Telegram account with channel admin access

---

## File Structure After Implementation

```
scientific_repo/
├── .repo-tools/
│   ├── scripts/
│   │   ├── telegram_uploader.py                    # NEW: Main uploader
│   │   ├── telegram_config.yaml.template           # NEW: Config template
│   │   ├── telegram_config.yaml                    # NEW: User config (gitignored)
│   │   ├── schedule_telegram_job.sh                # NEW: Setup script
│   │   ├── com.user.telegram-review-uploader.plist.template  # NEW: launchd config
│   │   ├── daily_review_processor.py               # Existing
│   │   └── ...
│   │
│   ├── logs/
│   │   ├── telegram_uploader.log                   # NEW: Execution log
│   │   ├── telegram_uploader_error.log             # NEW: Error log
│   │   ├── telegram_uploads.log                    # NEW: Upload history
│   │   └── ...
│   │
│   ├── docs/
│   │   └── TELEGRAM_SETUP.md                       # NEW: Setup guide
│   │
│   └── requirements.txt                             # Updated with new deps
│
├── .gitignore                                       # Updated
├── NEW_LAPTOP_SETUP.md                              # Updated
└── ...
```

---

## Implementation Timeline

### Phase 1: Bot Setup (User Task - 15 minutes)
- Create bots via @BotFather
- Get bot tokens
- Add bots to channels
- Get channel IDs

### Phase 2: Core Script Development (2-3 hours)
- `telegram_uploader.py` - Main logic
- Message splitting algorithm
- Duplicate detection (dual method)
- DOCX text extraction
- Telegram API integration
- Error handling
- Logging

### Phase 3: Configuration & Setup Scripts (1 hour)
- `telegram_config.yaml.template`
- `schedule_telegram_job.sh`
- launchd plist template
- Update `.gitignore`

### Phase 4: Documentation (1 hour)
- `TELEGRAM_SETUP.md` - Complete guide
- Update `NEW_LAPTOP_SETUP.md`
- Update `install.sh`
- Code comments

### Phase 5: Testing (1-2 hours)
- Unit tests
- Integration tests with test channels
- Manual testing checklist
- Dry-run mode testing

### Phase 6: Deployment & Verification (30 minutes)
- Commit to repo
- Push to GitHub
- Test on current laptop
- Document for next laptop

**Total Estimated Time:** 6-8 hours

---

## Success Criteria

✅ Hebrew reviews automatically upload to Hebrew channel
✅ English reviews automatically upload to English channel
✅ Long reviews split correctly at paragraph boundaries
✅ Duplicates prevented via dual detection
✅ Runs at 11:00 AM daily via launchd
✅ All code portable (lives in repo)
✅ Secure credential storage
✅ Comprehensive logging
✅ Error handling for all scenarios
✅ Works on fresh laptop clone
✅ Clear setup documentation

---

## Future Enhancements (Optional)

1. **Rich formatting:** Use Telegram markdown for headers, bold, italics
2. **GitHub links:** Add link to review on GitHub in message
3. **Retry queue:** Save failed uploads and retry later
4. **Analytics:** Track upload success rate, channel engagement
5. **Multiple languages:** Support more language channels
6. **Preview mode:** Send to private channel first for approval
7. **Webhook trigger:** Upload immediately when file appears (instead of waiting for 11 AM)

---

## Questions for User (Before Implementation)

Before I start implementing, please confirm:

1. ✅ Upload time: 11:00 AM daily - **Confirmed**
2. ✅ Format: Text messages - **Confirmed**
3. ✅ Splitting: Auto-split long reviews - **Confirmed**
4. ✅ Channels: Hebrew + English separate - **Confirmed**
5. ✅ Duplicate check: Both methods - **Confirmed**
6. ✅ Bot setup: Need to create - **Confirmed**

**Additional questions:**
- Should I include the review number in each message (e.g., "📄 Review 574" at the top)?
- Do you want any formatting (bold, italics) or just plain text?
- Should it only check Downloads, or also process files already in the repo?
- Any other preferences for message format or behavior?

---

**Ready to proceed with implementation?**
