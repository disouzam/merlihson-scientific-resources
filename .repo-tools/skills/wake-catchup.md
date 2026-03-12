---
name: wake-catchup
description: Safety net automation that catches up missed pipeline steps on login
---

# Wake Catch-Up Skill

Runs on every login via launchd (`RunAtLoad`) and catches up any missed pipeline steps by checking ledgers and running scripts as needed.

## User Commands

The user can say:
- "check wake catch-up status"
- "run wake catch-up"
- "view wake catch-up logs"
- "install wake catch-up on this machine"

## What This Skill Does

### Core Functionality
1. **Wait for network** — Polls until network is available (important after wake from sleep)
2. **Sync ledgers** — `git pull` to get latest state from all machines
3. **Push unpushed commits** — If a previous run committed but failed to push (e.g. network timeout), retries push with pull+rebase (3 attempts with backoff)
4. **Check pipeline steps** — Inspects ledgers to see what's been done today
5. **Run missing steps** — Executes scripts for any incomplete steps (in dependency order)
6. **Cooldown** — Skips if last run was <10 minutes ago

### Pipeline Steps Checked (in order)
1. `daily_review_processor.py` — Are there unprocessed DOCX files in ReviewsInbox?
2. `telegram_uploader.py` — Is the latest review in the Telegram ledger?
3. `twitter_thread_auto_poster.py` — Is the latest review in the Twitter ledger? (requires Telegram done)
4. `discord_poster.py` — Is the latest review in the Discord ledger? (requires Telegram done)

## Implementation Details

### Core Files
- **Script:** `.repo-tools/scripts/wake_catchup.py`
- **Logs:** `.repo-tools/logs/wake_catchup.log` and `wake_catchup_error.log`
- **Cooldown file:** `.repo-tools/logs/wake_catchup_last_run`
- **launchd plist:** `~/Library/LaunchAgents/com.user.wake-catchup.plist`

### Trigger
- **RunAtLoad** — fires on login (not on wake-from-sleep)
- Cooldown: 600 seconds (10 minutes) between runs

### Dedup Safety
- The catch-up script only orchestrates — each script it calls has its own full dedup chain:
  - Git-tracked ledger checks
  - Machine delay slots
  - Last-second re-checks
  - Push retry 3x with backoff
  - Platform API checks

## Action Instructions

### 1. Check Status
**Trigger:** "check wake catch-up status"

```bash
launchctl list | grep wake-catchup
```

**Response:**
- If loaded: "Wake catch-up is active (runs on login)"
- If not: "Not loaded. Install with: `launchctl load ~/Library/LaunchAgents/com.user.wake-catchup.plist`"

### 2. Run Manually
**Trigger:** "run wake catch-up"

```bash
cd /Users/michaelerlihson/Personal/repos/scientific-resources
python3 .repo-tools/scripts/wake_catchup.py
```

### 3. View Logs
**Trigger:** "view wake catch-up logs"

```bash
tail -30 .repo-tools/logs/wake_catchup.log
```

### 4. Install on New Machine
**Trigger:** "install wake catch-up on this machine"

Create the plist at `~/Library/LaunchAgents/com.user.wake-catchup.plist` with:
- `ProgramArguments`: `/usr/bin/python3` + path to `wake_catchup.py`
- `WorkingDirectory`: repo root
- `RunAtLoad`: true
- `KeepAlive`: false
- Update all paths to match the machine's repo location

Then: `launchctl load ~/Library/LaunchAgents/com.user.wake-catchup.plist`

## Error Scenarios & Solutions

### Cooldown Active
**Symptom:** Log shows "Cooldown active — last run Xs ago"
**Cause:** Script ran recently (within 10 minutes)
**Solution:** Normal behavior. Wait or delete `.repo-tools/logs/wake_catchup_last_run` to force run.

### No Reviews in ReviewsInbox
**Symptom:** Log shows "No reviews found in ReviewsInbox. Nothing to do."
**Cause:** No DOCX files to process
**Solution:** Normal — nothing to catch up on.

### Git Pull Failed
**Symptom:** Log shows "Git pull issue" or "Git pull timed out"
**Cause:** Network not ready or SSH key issue
**Solution:** Check network connectivity and SSH keys (`ssh -T git@github.com`).

## Integration with Daily Workflow

```
5:00-9:00 AM (scheduled)   → daily_review_processor
11:00-3:00 PM (scheduled)  → telegram_uploader
11:35-3:35 PM (scheduled)  → twitter_thread_auto_poster
4:00-7:00 PM (scheduled)   → discord_poster
On login (RunAtLoad)        → wake_catchup (fills in anything missed above)
```

## Safety & Independence

- Does NOT modify any files directly — only calls existing scripts
- Each called script has its own dedup (safe to run multiple times)
- 10-minute cooldown prevents excessive runs
- Can be disabled without breaking anything:
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.user.wake-catchup.plist
  ```
