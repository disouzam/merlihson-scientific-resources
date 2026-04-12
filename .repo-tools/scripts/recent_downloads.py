#!/usr/bin/env python3
"""
Recent Downloads CLI

Finds the N most recently committed files in a given repo folder
and downloads any that are missing from ~/Downloads/Books/.

Usage:
  python3 recent_downloads.py learning-materials/math 5
  python3 recent_downloads.py "learning-materials/machine learning" 10
  python3 recent_downloads.py learning-materials/math --list-only
"""

import argparse
import subprocess
import sys
import urllib.parse
import urllib.request
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


def check_and_download(files: list[dict], list_only: bool = False) -> None:
    """Check which files are missing from Downloads/Books and download them."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    present = []

    for f in files:
        local_path = DOWNLOADS_DIR / f['name']
        if local_path.exists():
            present.append(f)
        else:
            missing.append(f)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Recent files in repo ({len(files)} found)")
    print(f"{'='*60}\n")

    for i, f in enumerate(files, 1):
        status = "✓ exists" if f in present else "✗ missing"
        date_short = f['date'][:10] if f['date'] else '?'
        print(f"  {i}. [{date_short}] {f['name']}")
        print(f"     {status} in ~/Downloads/Books/")
        print(f"     repo: {f['path']}")
        print()

    print(f"Summary: {len(present)} already downloaded, {len(missing)} missing\n")

    if list_only:
        return

    if not missing:
        print("Nothing to download.")
        return

    print(f"Downloading {len(missing)} file(s)...\n")

    for f in missing:
        url = f"{GITHUB_RAW_BASE}/{urllib.parse.quote(f['path'])}"
        local_path = DOWNLOADS_DIR / f['name']

        print(f"  Downloading: {f['name']}")
        print(f"  From: {url[:80]}...")

        try:
            urllib.request.urlretrieve(url, str(local_path))
            size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Saved ({size_mb:.1f} MB)\n")
        except Exception as e:
            print(f"  ✗ Failed: {e}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download N most recently added files from a repo folder"
    )
    parser.add_argument('folder', help='Folder path in repo (e.g., learning-materials/math)')
    parser.add_argument('n', nargs='?', type=int, default=5, help='Number of recent files (default: 5)')
    parser.add_argument('--list-only', action='store_true', help='Only list files, do not download')

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

    print(f"Scanning: {folder} (last {args.n} files)")
    files = get_recent_files(folder, args.n)

    if not files:
        print(f"No files found in {folder}")
        return 1

    check_and_download(files, list_only=args.list_only)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
