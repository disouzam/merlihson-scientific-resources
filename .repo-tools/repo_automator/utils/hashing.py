"""
MD5 hash utilities for duplicate detection.

NOTE: This module only DETECTS duplicates. It NEVER deletes files.
Duplicates are reported to the console for user review.
"""

import hashlib
from pathlib import Path
from typing import Dict, List


def compute_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute MD5 hash of a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read (default: 8KB)

    Returns:
        MD5 hash as hexadecimal string
    """
    md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except (IOError, OSError):
        return ""


def find_duplicates(
    directory: Path,
    pattern: str = "*",
    recursive: bool = True,
    ignore_patterns: List[str] = None
) -> Dict[str, List[Path]]:
    """
    Find duplicate files by MD5 hash.

    NOTE: This function only REPORTS duplicates. It NEVER deletes anything.

    Args:
        directory: Directory to scan
        pattern: Glob pattern for files (default: "*")
        recursive: Whether to search recursively (default: True)
        ignore_patterns: Patterns to ignore (e.g., [".DS_Store", "*.tmp"])

    Returns:
        Dict mapping hash -> list of files with that hash.
        Only includes entries where len(files) > 1.
    """
    if ignore_patterns is None:
        ignore_patterns = [".DS_Store", "*.tmp", "*.swp", "~*"]

    hash_to_files: Dict[str, List[Path]] = {}

    # Get files based on pattern
    if recursive:
        files = directory.rglob(pattern)
    else:
        files = directory.glob(pattern)

    for file_path in files:
        # Skip if not a file
        if not file_path.is_file():
            continue

        # Skip ignored patterns
        skip = False
        for ignore in ignore_patterns:
            if file_path.match(ignore):
                skip = True
                break
        if skip:
            continue

        # Compute hash
        file_hash = compute_md5(file_path)
        if not file_hash:
            continue

        # Add to mapping
        if file_hash not in hash_to_files:
            hash_to_files[file_hash] = []
        hash_to_files[file_hash].append(file_path)

    # Filter to only duplicates (more than one file with same hash)
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}

    return duplicates


def format_duplicates_report(duplicates: Dict[str, List[Path]], repo_root: Path = None) -> str:
    """
    Format duplicates into a human-readable report.

    Args:
        duplicates: Dict from find_duplicates()
        repo_root: If provided, show paths relative to this root

    Returns:
        Formatted string report
    """
    if not duplicates:
        return "No duplicate files found."

    lines = [f"Found {len(duplicates)} sets of duplicate files:\n"]

    for i, (hash_val, files) in enumerate(duplicates.items(), 1):
        # Calculate wasted space
        if files:
            try:
                file_size = files[0].stat().st_size
                wasted = file_size * (len(files) - 1)
                wasted_str = _format_size(wasted)
            except OSError:
                wasted_str = "unknown"
        else:
            wasted_str = "unknown"

        lines.append(f"\n{i}. Duplicate set (wasted: {wasted_str}):")
        for f in files:
            if repo_root:
                try:
                    display_path = f.relative_to(repo_root)
                except ValueError:
                    display_path = f
            else:
                display_path = f
            lines.append(f"   - {display_path}")

    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
