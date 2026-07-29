# CL Tracker — continual-learning content & people tracker (Phase 1)

Implements Phase 1 of `~/Downloads/AI-Lab-CL-Tracker-Implementation-Plan.md`:
listen → score → 3-bucket digest for continual learning & adjacent topics.

## Run

```bash
cd .repo-tools/scripts
../.venv/bin/python3 -m cl_tracker.tracker --dry-run     # print digest, send nothing
../.venv/bin/python3 -m cl_tracker.tracker               # write digests/YYYY-MM-DD.md (+ Telegram if enabled)
../.venv/bin/python3 -m cl_tracker.tracker --force       # ignore the once-a-day ledger
../.venv/bin/python3 -m cl_tracker.tracker --lookback 72 # custom window (hours)
```

## Pieces

| File | Role |
|------|------|
| `topics.yaml` | Topic taxonomy: `core` / `adjacent` / `emerging_framings` phrases (the topic gate) |
| `feeds.yaml` | Curated blogs/newsletters, tiered 1–5 with score weights |
| `fetchers.py` | arXiv, HF Daily Papers, Semantic Scholar, OpenReview, HN, GitHub, RSS (all fail soft) |
| `scorer.py` | Deterministic scoring → buckets `core` / `emerging` / `viral` + recurring-author extraction |
| `digest.py` | Markdown digest (full) + short Telegram text |
| `tracker.py` | Orchestrator (`python3 -m cl_tracker.tracker`) |
| `config.yaml` | Local, gitignored: lookback, bucket caps, Telegram/email delivery |

## Buckets

- **core** — squarely CL-relevant (a `core` phrase hit), depth-first (papers > repos > blogs > posts).
- **emerging** — early/near-but-unnamed: `emerging_framings` hits on fresh, low-visibility papers; tiny on-topic repos.
- **viral** — high engagement velocity + only weak topic connection (reactive-add candidates).

## Known gaps (Phase 1.5+)

- **Reddit**: blocks all unauthenticated access (403) — needs an OAuth app to enable.
- **Semantic Scholar**: unauth quota is tight; retries help but a free API key would fix it.
- **Email delivery**: config stub exists, but `email_digest` only *reads* Gmail (no send
  machinery exists in the repo) — needs Gmail send-scope OAuth or an SMTP app password first.
- **X/Twitter**: skipped by decision (research-first); Phase 2.
- **LLM synthesis + drafter + rigor gate**: Phases 3–4 in the plan.
- **Scheduling**: `com.user.cl-tracker.plist.template` provided; install like the other jobs
  (see `schedule_news_scout_job.sh` for the pattern).
