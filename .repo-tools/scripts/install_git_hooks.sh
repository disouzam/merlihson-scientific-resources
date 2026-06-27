#!/bin/bash
# Activate this repo's version-controlled git hooks on a new machine.
# Run once after cloning:  bash .repo-tools/scripts/install_git_hooks.sh
#
# Points git at .repo-tools/hooks/ (tracked) instead of the local .git/hooks/,
# so the pre-commit metadata hook travels with the repo and stays up to date.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
git config core.hooksPath .repo-tools/hooks
chmod +x .repo-tools/hooks/* 2>/dev/null || true
echo "✓ core.hooksPath set to .repo-tools/hooks"
echo "✓ pre-commit hook active (auto-updates README stats via update_metadata.py)"
echo
echo "Note: the hook needs the Python venv at .repo-tools/.venv (Python 3.10+)."
echo "If missing: python3 -m venv .repo-tools/.venv && .repo-tools/.venv/bin/pip install -r .repo-tools/requirements.txt"
