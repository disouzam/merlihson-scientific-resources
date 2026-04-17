---
name: recent-books
description: Download recent or random books from learning-materials/ into ~/Downloads/Books
---

# Recent / Random Book Fetch Skill

## User Commands

- "download the last N books from [folder]"
- "pick me N random books from [folder]"
- "give me something to read from [subject]"
- "run recent-books for [folder]"

## The CLI

Shell alias (`~/.zshrc`): `recent-books` → `python3 .repo-tools/scripts/recent_downloads.py`

```bash
# N most recently committed files in a folder
recent-books learning-materials/math 5

# N random files picked from files added in last M days
recent-books learning-materials/math 7 --random --days 60

# Preview only (no download)
recent-books learning-materials/math --list-only

# Control how many extra sampling batches to try when some files 404
recent-books learning-materials/math 7 --random --days 60 --max-extra-batches 10
```

## What It Does

1. `git log` inside the scientific_repo to find files matching the query (recent or within `--days` window).
2. In `--random` mode, shuffles the candidate pool and draws N.
3. Checks `~/Downloads/Books/` — files already there count as successes.
4. Downloads the rest via GitHub raw URLs.
5. **If any download 404s, picks more random files from the pool to compensate** (target N successful files), up to `--max-extra-batches` rounds.
6. Prints a final tally with the names of any skipped files.

## Why 404s Happen

Some learning-materials PDFs exceed GitHub's 100MB file limit and are stored **local-only**, never staged. These raw-content fetches return 404. The compensation loop hides this from the user — you get N actual files, not "N minus the local-only count."

The list of >50MB local-only files is maintained in `.repo-tools/skills/book-download.md`.

## Output Contract

- Exit code `0` if N successes were reached (or `--list-only`), `1` if pool was exhausted first.
- Prints every attempt inline with `✓` / `✗` markers and the date the file was committed.
- Failed downloads remove any partial file from `~/Downloads/Books/` to avoid empty stubs.

## Maintenance Notes

- Alias lives in `~/.zshrc` — must be added manually on each machine (not tracked in repo).
- Script path: `.repo-tools/scripts/recent_downloads.py`
- If GitHub ever rate-limits raw fetches, consider switching to `git archive` or shallow clone.
- When new large files are added to learning-materials, no code change is needed — the compensation loop handles them automatically.
