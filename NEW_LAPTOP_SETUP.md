# New Machine Setup

Minimal checklist to bring this repo's automations up on a fresh Mac. Configs hold
secrets and are gitignored — they don't come with the clone.

## 1. Clone
```bash
git clone git@github.com:merlihson/scientific-resources.git ~/personal/repos/scientific-resources
```
`--depth 1` is fine for working; run `git fetch --unshallow` later if you want full history.

## 2. Python venv (needs 3.10+)
```bash
brew install python@3.12
cd .repo-tools && /opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
# extras not pinned in requirements.txt:
.venv/bin/pip install anthropic feedparser arxiv pymupdf html2text \
  google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## 3. Git hooks (metadata auto-update on commit)
```bash
bash .repo-tools/scripts/install_git_hooks.sh
```

## 4. Configs — copy each template, fill secrets, set a UNIQUE machine_id
```
.repo-tools/scripts/telegram_config.yaml          # Hebrew+English bot tokens + channel IDs
.repo-tools/config/discord_config.yaml            # bot token, channel_id, substack base_url
.repo-tools/scripts/news_scout/config.yaml        # anthropic key + telegram (test channel)
.repo-tools/scripts/paper_recommender/config.yaml # anthropic key + telegram (test channel)
.repo-tools/scripts/email_digest/config.yaml      # anthropic key + telegram chat_id
```
Get Telegram channel IDs via `https://api.telegram.org/bot<TOKEN>/getUpdates` after posting in the channel.

## 5. Gmail OAuth (email_digest only)
Put the Google OAuth client at `~/.config/email-digest/credentials.json`, then:
```bash
cd .repo-tools/scripts && ../.venv/bin/python -m email_digest.setup_oauth   # browser consent → token.json
```

## 6. Schedule the launchd jobs (install the ones you want)
```bash
cd .repo-tools/scripts
./schedule_daily_job.sh; ./schedule_telegram_job.sh; ./schedule_discord_job.sh   # review pipeline
./news_scout/schedule_news_scout_job.sh                                          # news scout
# paper_recommender / twitter / email-digest / wake-catchup: load their plist templates
# into ~/Library/LaunchAgents (substitute paths; ProgramArguments must use .repo-tools/.venv/bin/python3)
launchctl list | grep -E "daily-review|telegram|discord|twitter|news-scout|paper-recommender|email-digest|wake-catchup"
```

## Notes
- **machine_id** must be unique per machine (cross-machine dedup). Solo = `1`.
- Plists must point at `.repo-tools/.venv/bin/python3` (Python 3.12), not system `/usr/bin/python3`.
- Push uses SSH. For a non-default GitHub account, add a host alias in `~/.ssh/config` and point the remote at it.
