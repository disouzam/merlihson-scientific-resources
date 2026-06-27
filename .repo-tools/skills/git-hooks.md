---
name: git-hooks
description: Activate the repo's version-controlled git pre-commit hook on a new machine, so README stats / "Last Updated" badge / metadata auto-update on every commit. Use right after cloning the repo on a fresh machine, or if metadata stops auto-updating.
---

# Git Hooks Setup

This repo keeps its git hooks **in the repo** (`.repo-tools/hooks/`) instead of the
local, un-pushed `.git/hooks/`. That way the metadata pre-commit hook travels with
the repo and stays current.

## On a new machine (one command)

```bash
bash .repo-tools/scripts/install_git_hooks.sh
```

This runs `git config core.hooksPath .repo-tools/hooks` and makes the hooks
executable. Do this once per clone (the setting lives in the machine's local
`.git/config`, so it is per-machine).

## What the pre-commit hook does

Before each commit it runs `.repo-tools/scripts/update_metadata.py`, which
regenerates the README stats, the shields.io "Last Updated" badge, the 3 READMEs
(main / mike-paper-reviews-all / presentations), the cosmic-neural SVG header,
and the `reviews_metadata/` files — then re-stages them into the commit.

- It is **non-blocking**: if the venv is missing or the script errors, the commit
  still proceeds (the hook exits 0).
- It needs the Python venv at `.repo-tools/.venv` (Python 3.10+). If absent:
  `python3 -m venv .repo-tools/.venv && .repo-tools/.venv/bin/pip install -r .repo-tools/requirements.txt`

## Verify it's active

```bash
git config --get core.hooksPath          # → .repo-tools/hooks
ls -l .repo-tools/hooks/pre-commit        # → executable
```

## History

This replaced the old `repo_automator` framework + GitHub Action, which duplicated
the same metadata updating but delegated to `update_metadata.py` anyway and was
less complete. `update_metadata.py` + this hook is now the single source of truth.
