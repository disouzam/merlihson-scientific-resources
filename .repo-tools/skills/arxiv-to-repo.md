---
name: arxiv-to-repo
description: Download arxiv papers from Chrome tabs into the repo
---

# Arxiv-to-Repo Skill

Scans Chrome browser tabs for arxiv papers, downloads their PDFs, saves them to the repo with clean naming, closes processed tabs, and commits/pushes.

## User Commands

The user can say:
- "download my arxiv tabs"
- "arxiv to repo"
- "save arxiv papers from chrome"
- "grab my arxiv papers"
- "run arxiv-to-repo"
- "what arxiv tabs do I have open?"

## What This Skill Does

1. **Scans Chrome** — reads all open tabs via AppleScript
2. **Extracts arxiv IDs** — matches `arxiv.org/abs/`, `/pdf/`, `/html/` URLs, deduplicates
3. **Skips existing** — checks `arxiv-papers/` for already-downloaded papers
4. **Fetches titles & dates** — gets the paper title and submission date from the arxiv abstract page
5. **Sorts by date** — newest papers first
6. **Downloads PDFs** — saves with inverted date sort key so newest appear first
6. **Closes tabs** — closes all Chrome tabs for papers now in the repo
7. **Commits & pushes** — stages, commits, and pushes to GitHub

## Implementation Details

- **Script**: `.repo-tools/scripts/arxiv_to_repo.py`
- **CLI alias**: `arxiv-to-repo` (defined in `~/.zshrc`)
- **Destination**: `arxiv-papers/`
- **Naming**: `SORT-KEY YYYY-MM-DD [YYMM.NNNNN] Paper Title.pdf` (inverted date sort key + real date, newest first alphabetically)
- **Dependencies**: Python 3 standard library only (no pip packages needed)
- **Platform**: macOS only (uses AppleScript for Chrome interaction)

## Action Instructions

### Run from terminal
```bash
arxiv-to-repo              # full run: download, commit, push, close tabs
arxiv-to-repo --dry-run    # preview what would be downloaded
arxiv-to-repo --no-push    # download and commit locally, don't push
arxiv-to-repo --keep-tabs  # don't close Chrome tabs after downloading
arxiv-to-repo --fix-dates  # one-time: add date prefixes to existing papers
```

### Run from Claude Code
```bash
python3 .repo-tools/scripts/arxiv_to_repo.py --dry-run
python3 .repo-tools/scripts/arxiv_to_repo.py
```

## Error Scenarios & Solutions

| Issue | Solution |
|-------|---------|
| "No arxiv tabs found" | Open some arxiv papers in Chrome first |
| Chrome permission denied | Grant terminal/osascript access in System Settings > Privacy > Automation |
| Download fails for a paper | Script continues with remaining papers, reports failures |
| GitHub push rejected | Script auto-pulls with `--rebase --autostash` before push |
| Large file warning (>50MB) | GitHub warns but allows up to 100MB; consider Git LFS for very large papers |

## Integration

- Papers land in `arxiv-papers/` alongside other learning materials
- No overlap with `mike-paper-reviews-all/` (those are reviewed papers with Hebrew/English summaries)
- The script is idempotent — running it multiple times only downloads new papers

---

**Last Updated:** 2026-02-21
