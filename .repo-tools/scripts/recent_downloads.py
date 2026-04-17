#!/usr/bin/env python3
"""
Recent Downloads CLI

Finds files in a given repo folder and downloads any missing from ~/Downloads/Books/.

Modes:
  recent  - N most recently committed files (default)
  random  - N random files committed in the last M days; if some 404 (local-only
            >100MB files not in git), extra random batches are drawn from the pool
            until N successes are reached or --max-extra-batches is exhausted.

Usage:
  python3 recent_downloads.py learning-materials/math 5
  python3 recent_downloads.py "learning-materials/machine learning" 10
  python3 recent_downloads.py learning-materials/math --list-only
  python3 recent_downloads.py learning-materials/math 3 --random --days 30
  python3 recent_downloads.py learning-materials/math 7 --random --days 60 --max-extra-batches 10
"""

import argparse
import random
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = Path.home() / "Downloads" / "Books"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/merlihson/scientific-resources/main"


def get_recent_files(folder: str, n: int) -> list[dict]:
    """Find N most recently committed files in a repo folder using git log."""
    # Get all commits that added files in the folder, newest first
    result = subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'log', '--diff-filter=A', '--name-only',
         '--pretty=format:%H %aI', '--', f'{folder}/*'],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        print(f"Error running git log: {result.stderr}")
        return []

    files = []
    seen = set()
    current_commit = None
    current_date = None

    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Commit line: hash + date
        if ' ' in line and len(line.split()[0]) == 40:
            parts = line.split(' ', 1)
            current_commit = parts[0]
            current_date = parts[1]
            continue

        # File path line
        file_path = line
        if file_path in seen:
            continue
        if not file_path.startswith(folder):
            continue
        # Skip directories and non-files
        full_path = REPO_ROOT / file_path
        if full_path.is_dir():
            continue

        seen.add(file_path)
        files.append({
            'path': file_path,
            'name': Path(file_path).name,
            'date': current_date,
            'commit': current_commit,
        })

        if len(files) >= n:
            break

    return files


def get_files_from_last_days(folder: str, days: int) -> list[dict]:
    """Find all files committed in the last M days in a repo folder."""
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    result = subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'log', f'--since={since_date}',
         '--diff-filter=A', '--name-only', '--pretty=format:%H %aI', '--', f'{folder}/*'],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        print(f"Error running git log: {result.stderr}")
        return []

    files = []
    seen = set()
    current_commit = None
    current_date = None

    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if ' ' in line and len(line.split()[0]) == 40:
            parts = line.split(' ', 1)
            current_commit = parts[0]
            current_date = parts[1]
            continue

        file_path = line
        if file_path in seen:
            continue
        if not file_path.startswith(folder):
            continue
        full_path = REPO_ROOT / file_path
        if full_path.is_dir():
            continue

        seen.add(file_path)
        files.append({
            'path': file_path,
            'name': Path(file_path).name,
            'date': current_date,
            'commit': current_commit,
        })

    return files


def try_download(files: list[dict], list_only: bool = False) -> tuple[list[dict], list[dict]]:
    """Check which files are missing from Downloads/Books and download them.

    Returns (successes, failures): files now present in ~/Downloads/Books/ and
    those that 404'd (typically local-only >100MB files excluded from git).
    """
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    successes: list[dict] = []
    failures: list[dict] = []

    for f in files:
        local_path = DOWNLOADS_DIR / f['name']
        date_short = f['date'][:10] if f['date'] else '?'

        if local_path.exists():
            print(f"  ✓ [{date_short}] {f['name']} (already present)")
            successes.append(f)
            continue

        if list_only:
            print(f"  · [{date_short}] {f['name']} (missing — would download)")
            continue

        url = f"{GITHUB_RAW_BASE}/{urllib.parse.quote(f['path'])}"
        try:
            urllib.request.urlretrieve(url, str(local_path))
            size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ [{date_short}] {f['name']} → saved ({size_mb:.1f} MB)")
            successes.append(f)
        except Exception as e:
            print(f"  ✗ [{date_short}] {f['name']} → {e}")
            local_path.unlink(missing_ok=True)
            failures.append(f)

    return successes, failures


def main():
    parser = argparse.ArgumentParser(
        description="Download N most recently added files from a repo folder"
    )
    parser.add_argument('folder', help='Folder path in repo (e.g., learning-materials/math)')
    parser.add_argument('n', nargs='?', type=int, default=5, help='Number of files (default: 5)')
    parser.add_argument('--list-only', action='store_true', help='Only list files, do not download')
    parser.add_argument('--random', action='store_true', help='Pick N random files from last --days')
    parser.add_argument('--days', type=int, default=30, help='Lookback window for --random (default: 30)')
    parser.add_argument('--max-extra-batches', type=int, default=5,
                        help='In --random mode, max extra sampling batches to compensate for 404s (default: 5)')

    args = parser.parse_args()

    # Strip trailing slash
    folder = args.folder.rstrip('/')

    # Verify folder exists in repo
    folder_path = REPO_ROOT / folder
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        print(f"Available top-level folders in learning-materials/:")
        for d in sorted((REPO_ROOT / "learning-materials").iterdir()):
            if d.is_dir() and not d.name.startswith('.'):
                print(f"  {d.relative_to(REPO_ROOT)}")
        return 1

    if args.random:
        all_files = get_files_from_last_days(folder, args.days)
        if not all_files:
            print(f"No files added to {folder} in the last {args.days} days")
            return 1

        print(f"Scanning: {folder} (random {args.n} from last {args.days} days, pool: {len(all_files)})\n")

        # Shuffle once, then draw from the head of the pool as needed.
        pool = list(all_files)
        random.shuffle(pool)

        target = args.n
        successes: list[dict] = []
        failures: list[dict] = []
        batch_num = 0

        while len(successes) < target and pool and batch_num <= args.max_extra_batches:
            needed = target - len(successes)
            batch = pool[:needed]
            pool = pool[needed:]
            batch_num += 1

            if batch_num == 1:
                print(f"--- Picking {len(batch)} file(s) ---")
            else:
                print(f"--- Compensating (batch {batch_num}): picking {len(batch)} replacement(s) for 404s ---")
            batch_successes, batch_failures = try_download(batch, args.list_only)
            successes.extend(batch_successes)
            failures.extend(batch_failures)
            print()

            if args.list_only:
                break  # no retries in list-only mode

        print("=" * 60)
        print(f"Final: {len(successes)}/{target} available in ~/Downloads/Books/")
        if failures:
            print(f"Skipped {len(failures)} (likely local-only >100MB files not in git):")
            for f in failures:
                print(f"  - {f['name']}")
        if len(successes) < target and not pool:
            print(f"Pool exhausted — widen window with --days or choose a bigger folder.")
        print("=" * 60)
        return 0 if len(successes) >= target or args.list_only else 1

    # Recent mode (no retry: user asked for the N most-recent specifically)
    print(f"Scanning: {folder} (last {args.n} files)\n")
    files = get_recent_files(folder, args.n)
    if not files:
        print(f"No files found in {folder}")
        return 1
    try_download(files, args.list_only)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
