# Twitter Hebrew Review Threads - Implementation Plan

**Created:** 2026-02-12
**Status:** Planning Phase
**Goal:** Post Hebrew reviews as Twitter threads automatically

---

## 🎯 Objectives

1. Post Hebrew reviews to Twitter as threaded tweets
2. Integrate with existing workflow WITHOUT modifying working automation
3. Handle Hebrew (RTL) text properly
4. Split reviews intelligently into tweet-sized chunks
5. Track posted reviews to avoid duplicates
6. Schedule posting to align with existing workflow

---

## 📊 Current State Analysis

### Review Characteristics
- **Format:** Markdown files in `mike-paper-reviews-all/split-hebrew-reviews-md/`
- **Average length:** ~5,000 characters (Review 577 example)
- **Structure:**
  - English title
  - Hebrew title + subtitle
  - Hebrew content (sections with headers)
  - ArXiv link at end
- **Language:** Hebrew (RTL text)

### Twitter Constraints
- **Character limit:** 280 characters per tweet
- **Thread limit:** 25 tweets max per thread (Twitter best practice: 10-15)
- **Rate limits:** 50 tweets/day (standard), 2,400 tweets/day (elevated)
- **API:** Twitter API v2 required

### Existing Workflow (DO NOT MODIFY)
```
5:00 AM  → Process reviews (daily_review_processor.py) ✅
11:00 AM → Telegram upload (telegram_uploader.py) ✅
12:00 PM → Discord post (discord_poster.py) ✅
6:00 PM  → Discord backup ✅
```

**NEW: Twitter posting slot**
```
2:00 PM  → Twitter thread posting (NEW - twitter_poster.py)
8:00 PM  → Twitter backup posting (if 2:00 PM failed)
```

---

## 🏗️ Architecture

### New Files (No Modifications to Existing Code)

```
.repo-tools/
├── scripts/
│   ├── twitter_poster.py               # NEW: Main Twitter posting script
│   ├── twitter_thread_builder.py       # NEW: Thread creation logic
│   └── schedule_twitter_job.sh         # NEW: LaunchAgent installer
│
├── config/
│   └── twitter_config.yaml             # NEW: Twitter API credentials
│
├── logs/
│   ├── twitter_posts.log               # NEW: Posted review tracking
│   ├── twitter_poster.log              # NEW: Execution logs
│   └── twitter_poster_error.log        # NEW: Error logs
│
├── skills/
│   └── twitter-post.md                 # NEW: Twitter posting skill
│
├── docs/
│   └── TWITTER_SETUP.md                # NEW: Setup guide
│
└── plans/
    └── TWITTER_THREADS_PLAN.md         # THIS FILE
```

---

## 🔧 Component Design

### 1. twitter_thread_builder.py

**Purpose:** Split Hebrew review into tweet-sized chunks

**Key Functions:**

```python
def load_hebrew_review(review_num: int) -> str:
    """Load Hebrew review markdown file"""

def clean_markdown(content: str) -> str:
    """Remove markdown formatting, keep text clean"""

def split_into_tweets(text: str, max_chars: int = 270) -> List[str]:
    """
    Split text into tweets intelligently
    - Respect sentence boundaries
    - Handle Hebrew RTL properly
    - Keep sections together when possible
    - Reserve 10 chars for tweet numbering (1/15, 2/15, etc.)
    """

def format_thread(tweets: List[str]) -> List[str]:
    """
    Format tweets with numbering
    - First tweet: Title + "🧵 Thread about..."
    - Middle tweets: Content with (2/15), (3/15), etc.
    - Last tweet: ArXiv link + "End of thread"
    """

def validate_thread(tweets: List[str]) -> bool:
    """Ensure all tweets are under 280 chars"""
```

**Smart Splitting Strategy:**

1. **First Tweet (Intro):**
   ```
   Review 577: A MODEL OF ERRORS IN TRANSFORMERS

   התרמודינמיקה של שגיאות טרנספורמר

   🧵 Thread with full Hebrew review ⬇️
   ```

2. **Content Tweets:**
   - Split by paragraphs first
   - If paragraph > 270 chars, split by sentences
   - If sentence > 270 chars, split at word boundaries
   - Preserve Hebrew text integrity (no mid-word breaks)

3. **Last Tweet:**
   ```
   📄 Full paper: https://arxiv.org/abs/2601.14175

   ✅ End of thread

   #MachineLearning #AI #Hebrew
   ```

### 2. twitter_poster.py

**Purpose:** Main automation script for Twitter posting

**Key Functions:**

```python
def load_config(config_path: Path) -> TwitterConfig:
    """Load Twitter API credentials from config"""

def authenticate_twitter(config: TwitterConfig) -> tweepy.Client:
    """Authenticate with Twitter API v2"""

def load_posted_reviews() -> set:
    """Load already-posted reviews from twitter_posts.log"""

def get_new_reviews() -> List[int]:
    """
    Find new reviews to post:
    - Hebrew review file exists
    - Not already posted to Twitter
    - Posted to Discord (ensures it's ready)
    - From last 24 hours
    """

def post_thread(client: tweepy.Client, tweets: List[str]) -> bool:
    """
    Post thread to Twitter
    - Post first tweet
    - Reply to it with tweet 2
    - Reply to tweet 2 with tweet 3
    - etc.
    - Handle rate limits
    - Retry on failure
    """

def log_twitter_post(review_num: int, status: str, thread_id: str):
    """Log successful post to twitter_posts.log"""

def main():
    """Main entry point"""
```

**Workflow:**
```python
1. Load config
2. Authenticate with Twitter
3. Load posted reviews log
4. Find new reviews (from last 24 hours, not yet posted)
5. For each new review:
   a. Load Hebrew review file
   b. Build thread (twitter_thread_builder.py)
   c. Validate thread
   d. Post to Twitter
   e. Log success
   f. Wait 5 seconds between reviews (rate limit buffer)
```

### 3. twitter_config.yaml

**Structure:**
```yaml
twitter:
  # Twitter API v2 credentials
  api_key: "YOUR_API_KEY"
  api_secret: "YOUR_API_SECRET"
  access_token: "YOUR_ACCESS_TOKEN"
  access_token_secret: "YOUR_ACCESS_TOKEN_SECRET"
  bearer_token: "YOUR_BEARER_TOKEN"

settings:
  # Thread formatting
  max_tweet_length: 270  # Reserve 10 for numbering
  add_hashtags: true
  hashtags: ["MachineLearning", "AI", "Hebrew"]

  # Retry settings
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 60

  # Rate limiting
  rate_limit_buffer_seconds: 5  # Wait between tweets in thread

  # Content
  include_arxiv_link: true
  thread_emoji: "🧵"
```

### 4. Scheduled Job (LaunchAgent)

**File:** `com.user.twitter-review-poster.plist`

**Schedule:**
- **2:00 PM (14:00)** - Primary run
- **8:00 PM (20:00)** - Backup run

**Configuration:**
```xml
<key>StartCalendarInterval</key>
<array>
    <dict>
        <key>Hour</key>
        <integer>14</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <dict>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</array>
```

---

## 📝 Configuration & Setup

### Twitter API Setup

**Requirements:**
1. Twitter Developer Account (free tier sufficient)
2. Create Twitter App in Developer Portal
3. Generate API keys and tokens
4. Elevated access (optional, for higher rate limits)

**Steps:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create new project and app
3. Enable OAuth 1.0a (for posting tweets)
4. Generate API Key, API Secret, Access Token, Access Token Secret
5. Copy Bearer Token
6. Save credentials in `twitter_config.yaml`

**Permissions needed:**
- ✅ Read and Write tweets
- ✅ Read users
- ❌ Direct Messages (not needed)

---

## 🔍 Thread Building Logic

### Hebrew Text Handling

**Challenges:**
- RTL (Right-to-Left) text direction
- Unicode characters
- Emoji mixing with Hebrew
- Proper word boundaries

**Solutions:**
1. Use Python's `unicodedata` for proper character handling
2. Split at word boundaries using Hebrew-aware regex
3. Test with actual Hebrew content
4. Preserve formatting (line breaks, sections)

### Intelligent Splitting

**Priority Order:**
1. **Paragraph boundaries** (double newline) - Best
2. **Sentence boundaries** (period, question mark) - Good
3. **Clause boundaries** (comma, semicolon) - Acceptable
4. **Word boundaries** (spaces) - Last resort

**Algorithm:**
```python
def split_into_tweets(text: str, max_chars: int = 270):
    tweets = []
    current_tweet = ""

    paragraphs = text.split('\n\n')

    for para in paragraphs:
        if len(current_tweet) + len(para) <= max_chars:
            current_tweet += para + "\n\n"
        else:
            if current_tweet:
                tweets.append(current_tweet.strip())

            # Para too long, split by sentences
            if len(para) > max_chars:
                sentences = split_sentences(para)
                for sent in sentences:
                    if len(current_tweet) + len(sent) <= max_chars:
                        current_tweet += sent + " "
                    else:
                        if current_tweet:
                            tweets.append(current_tweet.strip())
                        current_tweet = sent + " "
            else:
                current_tweet = para + "\n\n"

    if current_tweet:
        tweets.append(current_tweet.strip())

    return tweets
```

### Thread Numbering

**Format:** `(X/Y)` at the end of each tweet

**Example:**
```
Tweet 1: [Intro + title] (no number)
Tweet 2: [Content...] (2/15)
Tweet 3: [Content...] (3/15)
...
Tweet 15: [ArXiv link] (15/15)
```

**Alternative format (more common on Twitter):**
```
Tweet 1: [Intro]
Tweet 2: 2/ [Content...]
Tweet 3: 3/ [Content...]
...
```

---

## 🛡️ Safety & Validation

### Pre-Post Validation

**Checks:**
1. ✅ All tweets < 280 characters
2. ✅ Thread has at least 2 tweets
3. ✅ Thread has at most 25 tweets
4. ✅ No empty tweets
5. ✅ ArXiv link included in last tweet
6. ✅ Hebrew review file exists
7. ✅ Not already posted (check twitter_posts.log)

### Deduplication

**Tracking file:** `.repo-tools/logs/twitter_posts.log`

**Format:**
```
2026-02-12 14:00:15 | Review_577 | success | thread_id: 1234567890123456789
2026-02-13 14:00:20 | Review_578 | success | thread_id: 1234567890123456790
```

**Logic:**
- Load log at startup
- Check if review already posted
- Skip if already posted
- Append to log after successful post

### Error Handling

**Scenarios:**

1. **Rate Limit Exceeded:**
   - Wait and retry at backup time (8:00 PM)
   - Log warning

2. **Authentication Failed:**
   - Log error
   - Send notification (optional)
   - Don't retry (needs manual fix)

3. **Thread Posting Failed:**
   - If partial thread posted, mark as failed
   - Retry from beginning at backup time
   - Log thread_id of partial thread for cleanup

4. **Review File Not Found:**
   - Log error
   - Skip review
   - Continue with next review

---

## 📅 Integration with Existing Workflow

### Updated Daily Timeline

```
5:00 AM  → Process reviews from ReviewsInbox ✅
           (daily_review_processor.py)

11:00 AM → Upload to Telegram ✅
           (telegram_uploader.py)

12:00 PM → Post to Discord (with threads) ✅
           (discord_poster.py)

2:00 PM  → Post to Twitter (NEW) 🆕
           (twitter_poster.py)
           ├─ Load Hebrew review
           ├─ Build thread (15-20 tweets)
           ├─ Post thread
           └─ Log success

6:00 PM  → Discord backup ✅
           (discord_poster.py)

8:00 PM  → Twitter backup (NEW) 🆕
           (twitter_poster.py)
```

### Dependency Chain

```
Hebrew review exists
    ↓
Telegram uploaded (11 AM) ✅
    ↓
Discord posted (12 PM) ✅
    ↓
Twitter thread posted (2 PM) 🆕
```

**Validation:** Twitter poster checks that Discord post succeeded before posting. This ensures:
- Review is fully published
- All links are ready
- Quality check passed

---

## 🧪 Testing Strategy

### Phase 1: Thread Builder Testing

**Test Cases:**
1. Short review (~1000 chars) → 4-5 tweets
2. Medium review (~3000 chars) → 12-15 tweets
3. Long review (~5000 chars) → 18-20 tweets
4. Review with special characters, emojis
5. Review with multiple sections

**Validation:**
- All tweets < 280 chars ✅
- Hebrew text intact ✅
- No mid-word breaks ✅
- Logical content flow ✅

### Phase 2: Twitter API Testing

**Manual Tests:**
```bash
# Test 1: Authenticate
python3 twitter_poster.py --test-auth

# Test 2: Post single tweet
python3 twitter_poster.py --test-single-tweet

# Test 3: Post test thread (3 tweets)
python3 twitter_poster.py --test-thread

# Test 4: Dry run (show what would be posted)
python3 twitter_poster.py --review 577 --dry-run
```

### Phase 3: Integration Testing

**Test Workflow:**
1. Run thread builder on Review 577
2. Review generated tweets manually
3. Post to Twitter (test account first)
4. Verify thread appears correctly
5. Check Hebrew text renders properly
6. Verify ArXiv link works

### Phase 4: Automation Testing

**Test Schedule:**
```bash
# Install job
./schedule_twitter_job.sh install

# Trigger manual run
launchctl start com.user.twitter-review-poster

# Check logs
tail -f .repo-tools/logs/twitter_poster.log
```

---

## 🔐 Security Considerations

### API Keys Protection

**DO:**
- ✅ Store credentials in `twitter_config.yaml`
- ✅ Add to `.gitignore`
- ✅ Never commit to GitHub
- ✅ Use environment variables (optional enhancement)

**DON'T:**
- ❌ Hardcode in Python files
- ❌ Share publicly
- ❌ Use same credentials for multiple bots

### Rate Limiting

**Twitter Limits (Free Tier):**
- 50 tweets/24 hours
- 1 tweet/second

**Our Usage:**
- 1 review/day = ~18 tweets/thread
- Well within limits ✅

**Safety Margin:**
- Wait 5 seconds between tweets in thread
- Wait 10 seconds between reviews (if multiple)

---

## 📦 Dependencies

**New Python packages:**
```bash
pip install tweepy  # Twitter API v2
```

**Already installed:**
- pyyaml
- requests

---

## 🎛️ Manual Commands

### Post Specific Review
```bash
python3 twitter_poster.py --review 577
```

### Dry Run (Preview Thread)
```bash
python3 twitter_poster.py --review 577 --dry-run
```

### Test Authentication
```bash
python3 twitter_poster.py --test-auth
```

### View Recent Posts
```bash
tail -20 .repo-tools/logs/twitter_posts.log
```

---

## 📋 Implementation Phases

### Phase 1: Twitter API Setup (User Action)
**Duration:** 30 minutes

**Tasks:**
1. Create Twitter Developer account
2. Create app in Developer Portal
3. Generate API keys and tokens
4. Save credentials temporarily

**Deliverable:** Twitter API credentials ready

---

### Phase 2: Thread Builder (Code)
**Duration:** 2 hours

**Tasks:**
1. Create `twitter_thread_builder.py`
2. Implement smart splitting logic
3. Handle Hebrew text properly
4. Add validation
5. Test with Review 577

**Deliverable:** Working thread builder that splits reviews intelligently

---

### Phase 3: Twitter Poster (Code)
**Duration:** 2 hours

**Tasks:**
1. Create `twitter_poster.py`
2. Implement Twitter API authentication
3. Implement thread posting logic
4. Add error handling
5. Add logging
6. Create config file template

**Deliverable:** Working poster script with dry-run support

---

### Phase 4: Configuration (Code)
**Duration:** 30 minutes

**Tasks:**
1. Create `twitter_config.yaml` template
2. Update `.gitignore` to exclude config
3. Create backup mechanism
4. Document setup process

**Deliverable:** Configuration system ready

---

### Phase 5: Testing (Testing)
**Duration:** 1 hour

**Tasks:**
1. Test thread builder with multiple reviews
2. Test API authentication
3. Post test thread to Twitter
4. Verify Hebrew rendering
5. Check all edge cases

**Deliverable:** Verified working system

---

### Phase 6: Automation (Code)
**Duration:** 1 hour

**Tasks:**
1. Create LaunchAgent plist
2. Create `schedule_twitter_job.sh`
3. Install job
4. Test automated run
5. Monitor logs

**Deliverable:** Automated posting at 2:00 PM daily

---

### Phase 7: Documentation (Docs)
**Duration:** 1 hour

**Tasks:**
1. Create `TWITTER_SETUP.md`
2. Update `twitter-post.md` skill
3. Update workflow documentation
4. Add to new laptop setup guide

**Deliverable:** Complete documentation

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Posts Hebrew reviews as Twitter threads
- ✅ Threads are well-formatted and readable
- ✅ No duplicate posts
- ✅ Automated daily posting
- ✅ Error handling and retries

### Non-Functional Requirements
- ✅ No modifications to existing automation
- ✅ Hebrew text displays correctly
- ✅ All tweets under 280 characters
- ✅ Proper thread ordering
- ✅ Rate limits respected

### Integration Requirements
- ✅ Integrates with existing workflow
- ✅ Uses same review files
- ✅ Logs to consistent format
- ✅ Follows existing patterns

---

## 🚧 Potential Issues & Solutions

### Issue 1: Hebrew Text Too Long for Thread

**Problem:** Some reviews might be too long (>25 tweets)

**Solutions:**
1. Create summary for first tweet
2. Link to full review on Substack
3. Skip extremely long reviews (log warning)

### Issue 2: Twitter API Rate Limits

**Problem:** Hit rate limits during testing

**Solutions:**
1. Use dry-run mode for testing
2. Test on staging account
3. Request elevated access from Twitter

### Issue 3: Thread Posting Fails Mid-Thread

**Problem:** Network error after posting 10/20 tweets

**Solutions:**
1. Delete partial thread (Twitter API)
2. Retry from beginning at backup time
3. Log partial thread ID for manual cleanup

### Issue 4: Hebrew Rendering Issues

**Problem:** Hebrew text appears broken on Twitter

**Solutions:**
1. Test with actual Twitter app (not just API)
2. Add RTL markers if needed
3. Use Twitter's text composer for validation

---

## 🔄 Rollback Plan

**If Twitter posting fails:**

1. **Disable job:**
   ```bash
   ./schedule_twitter_job.sh uninstall
   ```

2. **Existing automation continues:**
   - Reviews still process ✅
   - Telegram still posts ✅
   - Discord still posts ✅

3. **No data loss:**
   - Reviews remain in repo
   - Can retry Twitter posting later
   - Logs preserved for debugging

**Twitter posting is completely independent of existing automation.**

---

## 📊 Monitoring & Maintenance

### Daily Checks

**Automated (via logs):**
```bash
# Check if job ran
grep "Starting Twitter poster" .repo-tools/logs/twitter_poster.log

# Check success rate
grep "success" .repo-tools/logs/twitter_posts.log | wc -l
```

**Manual (Twitter):**
- Visit Twitter profile
- Verify thread posted
- Check Hebrew text renders correctly
- Verify ArXiv link works

### Weekly Maintenance

1. Review error logs
2. Check rate limit usage
3. Verify API credentials still valid
4. Update dependencies if needed

---

## 🎓 Learning Resources

### Twitter API v2
- Docs: https://developer.twitter.com/en/docs/twitter-api
- Tweepy: https://docs.tweepy.org/

### Hebrew Text Processing
- Unicode RTL: https://unicode.org/reports/tr9/
- Python Unicode: https://docs.python.org/3/howto/unicode.html

---

## 📝 Next Steps

**Ready to implement?**

1. ✅ **User:** Set up Twitter Developer account and get API credentials
2. ✅ **Code:** Implement thread builder
3. ✅ **Code:** Implement Twitter poster
4. ✅ **Test:** Dry run with Review 577
5. ✅ **Test:** Post real thread to Twitter
6. ✅ **Deploy:** Install automation job
7. ✅ **Monitor:** Watch first automated run

---

**Plan Status:** Ready for Implementation
**Estimated Total Time:** 8-10 hours (coding + testing + deployment)
**Risk Level:** Low (no existing automation touched)

