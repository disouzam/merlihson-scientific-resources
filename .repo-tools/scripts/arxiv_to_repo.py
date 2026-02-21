#!/usr/bin/env python3
"""
arxiv-to-repo: Scans Chrome tabs for arxiv papers, downloads PDFs,
and adds them to the scientific-resources repo.

Usage:
    arxiv-to-repo          # download, commit and push
    arxiv-to-repo --dry-run  # show what would be downloaded without doing it
    arxiv-to-repo --no-push  # download and commit but don't push
    arxiv-to-repo --keep-tabs  # don't close Chrome tabs after downloading
"""

import argparse
import os
import re
import subprocess
import sys
import urllib.request
from html import unescape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEST_DIR = REPO_ROOT / "arxiv-papers"

ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)")


def get_chrome_tabs():
    """Get all URLs from Chrome tabs via AppleScript."""
    script = '''
    set tabList to ""
    tell application "Google Chrome"
        set windowCount to count of windows
        repeat with w from 1 to windowCount
            set tabCount to count of tabs of window w
            repeat with t from 1 to tabCount
                set tabURL to URL of tab t of window w
                set tabList to tabList & tabURL & linefeed
            end repeat
        end repeat
    end tell
    return tabList
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().split("\n")
    except Exception as e:
        print(f"Error reading Chrome tabs: {e}", file=sys.stderr)
        return []


def extract_arxiv_ids(urls):
    """Extract unique arxiv IDs from a list of URLs."""
    ids = set()
    for url in urls:
        match = ARXIV_ID_RE.search(url)
        if match:
            # Strip version suffix for dedup
            arxiv_id = re.sub(r"v\d+$", "", match.group(1))
            ids.add(arxiv_id)
    return sorted(ids)


def fetch_title_and_date(arxiv_id):
    """Fetch the paper title and submission date from the arxiv abstract page.

    Returns (title, date_str) where date_str is 'YYYY-MM-DD' or None.
    """
    url = f"https://arxiv.org/abs/{arxiv_id}"
    title = None
    date_str = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "arxiv-to-repo/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract title from <title> tag: "[ID] Title"
        m = re.search(r"<title>\[.*?\]\s*(.*?)</title>", html)
        if m:
            title = unescape(m.group(1)).strip()
            title = sanitize_filename(title)
        # Extract submission date (first date on the page, typically "[Submitted on DD Mon YYYY]")
        dm = re.search(r"\[Submitted on\s+(\d{1,2})\s+(\w{3})\s+(\d{4})", html)
        if dm:
            day, mon, year = dm.group(1), dm.group(2), dm.group(3)
            months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                      'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
            if mon in months:
                date_str = f"{year}-{months[mon]}-{int(day):02d}"
    except Exception as e:
        print(f"  Warning: could not fetch title for {arxiv_id}: {e}", file=sys.stderr)
    return title, date_str


def sanitize_filename(name):
    """Remove or replace characters that are problematic in filenames."""
    # Replace colons, slashes, and other problematic chars
    name = re.sub(r'[:/\\<>"|?*]', " -", name)
    # Collapse multiple spaces/dashes
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"-\s*-+", "-", name)
    return name


def get_existing_ids():
    """Get arxiv IDs already in the destination folder."""
    ids = set()
    if DEST_DIR.exists():
        for f in DEST_DIR.iterdir():
            m = re.search(r"\[(\d{4}\.\d{4,5})\]", f.name)
            if m:
                ids.add(m.group(1))
    return ids


def invert_date(date_str):
    """Convert YYYY-MM-DD to an inverted sort key so newest dates sort first alphabetically."""
    y, m, d = date_str.split("-")
    return f"{9999 - int(y):04d}-{12 - int(m):02d}-{31 - int(d):02d}"


def download_pdf(arxiv_id, title, date_str=None):
    """Download the PDF from arxiv."""
    if date_str:
        sort_key = invert_date(date_str)
        filename = f"{sort_key} {date_str} [{arxiv_id}] {title}.pdf"
    else:
        filename = f"[{arxiv_id}] {title}.pdf"
    filepath = DEST_DIR / filename
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "arxiv-to-repo/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        filepath.write_bytes(data)
        size_mb = len(data) / (1024 * 1024)
        return filepath, size_mb
    except Exception as e:
        print(f"  Error downloading {arxiv_id}: {e}", file=sys.stderr)
        return None, 0


def close_arxiv_tabs(saved_ids):
    """Close Chrome tabs whose arxiv ID is already saved in the repo."""
    # Build AppleScript that iterates tabs in reverse and closes matching ones
    ids_pattern = "|".join(re.escape(aid) for aid in saved_ids)
    script = f'''
    tell application "Google Chrome"
        set windowCount to count of windows
        repeat with w from 1 to windowCount
            set tabCount to count of tabs of window w
            repeat with t from tabCount to 1 by -1
                set tabURL to URL of tab t of window w
                if tabURL contains "arxiv.org" then
                    repeat with aid in {{{", ".join('"' + aid + '"' for aid in saved_ids)}}}
                        if tabURL contains aid then
                            close tab t of window w
                            exit repeat
                        end if
                    end repeat
                end if
            end repeat
        end repeat
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        print(f"Closed Chrome tabs for {len(saved_ids)} arxiv paper(s).")
    except Exception as e:
        print(f"Warning: could not close tabs: {e}", file=sys.stderr)


def git_commit_and_push(files, push=True):
    """Stage, commit, and optionally push the new papers."""
    os.chdir(REPO_ROOT)
    for f in files:
        subprocess.run(["git", "add", str(f)], check=True)

    count = len(files)
    msg = f"Add {count} arxiv paper{'s' if count != 1 else ''} from Chrome tabs"
    subprocess.run(["git", "commit", "-m", msg], check=True)

    if push:
        print("Pulling remote changes...")
        pull = subprocess.run(
            ["git", "pull", "--rebase", "--autostash"],
            capture_output=True, text=True
        )
        if pull.returncode != 0:
            print(f"  Pull warning: {pull.stderr.strip()}")
            # Fallback to merge
            subprocess.run(["git", "rebase", "--abort"], capture_output=True)
            subprocess.run(["git", "pull", "--autostash"], check=True)
        print("Pushing to remote...")
        subprocess.run(["git", "push"], check=True)
        print("Pushed.")
    else:
        print("Committed locally (--no-push).")


def rename_existing_papers():
    """One-time migration: add/update date sort prefix on existing papers."""
    if not DEST_DIR.exists():
        return 0

    renamed = 0
    for f in sorted(DEST_DIR.iterdir()):
        if not f.name.endswith(".pdf"):
            continue
        m = re.search(r"\[(\d{4}\.\d{4,5})\]", f.name)
        if not m:
            continue
        arxiv_id = m.group(1)

        # Check if file already has the inverted sort key + real date prefix
        if re.match(r"\d{4}-\d{2}-\d{2}\s+\d{4}-\d{2}-\d{2}\s+\[", f.name):
            continue

        # Strip any old-format date prefix (just YYYY-MM-DD without sort key)
        base_name = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", f.name)

        # Extract existing date from old prefix, or fetch from arxiv
        old_date = re.match(r"(\d{4}-\d{2}-\d{2})\s+\[", f.name)
        if old_date:
            date_str = old_date.group(1)
            print(f"  [{arxiv_id}] Reusing date {date_str}")
        else:
            print(f"  [{arxiv_id}] Fetching date...")
            _, date_str = fetch_title_and_date(arxiv_id)

        if date_str:
            sort_key = invert_date(date_str)
            new_name = f"{sort_key} {date_str} {base_name}"
            f.rename(f.parent / new_name)
            print(f"    -> {new_name}")
            renamed += 1
        else:
            print(f"    -> Could not determine date, skipping")

    return renamed


def main():
    parser = argparse.ArgumentParser(description="Download arxiv papers from Chrome tabs to repo")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--no-push", action="store_true", help="Commit but don't push")
    parser.add_argument("--keep-tabs", action="store_true", help="Don't close Chrome tabs after downloading")
    parser.add_argument("--fix-dates", action="store_true", help="Add date prefix to existing papers that lack one")
    args = parser.parse_args()

    # Handle --fix-dates mode (one-time migration)
    if args.fix_dates:
        print("Adding date prefixes to existing papers...")
        renamed = rename_existing_papers()
        if renamed:
            print(f"\nRenamed {renamed} paper(s). Committing changes...")
            os.chdir(REPO_ROOT)
            subprocess.run(["git", "add", str(DEST_DIR)], check=True)
            subprocess.run(["git", "commit", "-m", f"Add date prefix to {renamed} arxiv paper(s)"], check=True)
            print("Committed. Push manually or use --no-push to skip.")
        else:
            print("No papers needed renaming.")
        return

    print("Scanning Chrome tabs for arxiv papers...")
    urls = get_chrome_tabs()
    arxiv_ids = extract_arxiv_ids(urls)

    if not arxiv_ids:
        print("No arxiv tabs found in Chrome.")
        return

    print(f"Found {len(arxiv_ids)} unique arxiv paper(s).")

    existing = get_existing_ids()
    new_ids = [aid for aid in arxiv_ids if aid not in existing]

    already_in_repo = [aid for aid in arxiv_ids if aid in existing]

    if not new_ids:
        print("All papers are already in the repo. Nothing to download.")
        if already_in_repo and not args.keep_tabs and not args.dry_run:
            close_arxiv_tabs(already_in_repo)
        return

    skipped = len(arxiv_ids) - len(new_ids)
    if skipped:
        print(f"Skipping {skipped} paper(s) already in repo.")

    print(f"Processing {len(new_ids)} new paper(s)...\n")

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []

    # Fetch metadata for all papers first, then sort by date
    papers = []
    for arxiv_id in new_ids:
        print(f"  [{arxiv_id}] Fetching title...")
        title, date_str = fetch_title_and_date(arxiv_id)
        if not title:
            title = f"arxiv-{arxiv_id}"
            print(f"    Using fallback title: {title}")
        else:
            print(f"    Title: {title}")
        if date_str:
            print(f"    Date: {date_str}")
        papers.append((arxiv_id, title, date_str))

    # Sort by publication date (newest first), papers without date go last
    papers.sort(key=lambda p: p[2] or "0000-00-00", reverse=True)
    print(f"\nSorted {len(papers)} papers by publication date.\n")

    for arxiv_id, title, date_str in papers:
        if args.dry_run:
            prefix = f"{date_str} " if date_str else ""
            print(f"    -> Would download to: {prefix}[{arxiv_id}] {title}.pdf")
            continue

        print(f"  [{arxiv_id}] Downloading PDF...")
        filepath, size_mb = download_pdf(arxiv_id, title, date_str)
        if filepath:
            print(f"    -> Saved: {filepath.name} ({size_mb:.1f} MB)\n")
            downloaded.append(filepath)
        else:
            print(f"    -> FAILED\n")

    if args.dry_run:
        print(f"Dry run complete. {len(new_ids)} paper(s) would be downloaded.")
        return

    if downloaded:
        print(f"\nDownloaded {len(downloaded)} paper(s).")
        git_commit_and_push(downloaded, push=not args.no_push)
        # Close tabs for all papers now in the repo (newly downloaded + already existing)
        if not args.keep_tabs:
            all_saved_ids = already_in_repo + [
                re.search(r"\[(\d{4}\.\d{4,5})\]", f.name).group(1)
                for f in downloaded
            ]
            close_arxiv_tabs(all_saved_ids)
    else:
        print("No papers were downloaded.")


if __name__ == "__main__":
    main()
