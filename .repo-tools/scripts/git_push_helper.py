#!/usr/bin/env python3
"""
Git Push Helper - Robust git operations with conflict handling

Handles the common workflow:
1. Stage specified files
2. Commit with message
3. Pull with rebase (handle conflicts by resetting)
4. Push to remote

Usage:
    from git_push_helper import git_commit_and_push

    success = git_commit_and_push(
        files=['path/to/file1.md', 'path/to/file2.py'],
        commit_message="Fix something",
        repo_root=Path('/path/to/repo')
    )
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_git_command(cmd: List[str], repo_root: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the specified repository."""
    full_cmd = ['git', '-C', str(repo_root)] + cmd
    result = subprocess.run(
        full_cmd,
        capture_output=True,
        text=True,
        check=False
    )

    if check and result.returncode != 0:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Error: {result.stderr}")
        if not check:
            return result
        raise subprocess.CalledProcessError(result.returncode, full_cmd, result.stdout, result.stderr)

    return result


def git_commit_and_push(
    files: List[str],
    commit_message: str,
    repo_root: Path,
    auto_resolve_conflicts: bool = True
) -> bool:
    """
    Stage files, commit, pull with rebase, and push.

    Args:
        files: List of file paths relative to repo root
        commit_message: Commit message
        repo_root: Path to repository root
        auto_resolve_conflicts: If True, reset to origin/main on conflicts and retry

    Returns:
        True if successful, False otherwise
    """
    try:
        # Stage files
        print(f"📝 Staging {len(files)} file(s)...")
        for file in files:
            result = run_git_command(['add', file], repo_root, check=False)
            if result.returncode != 0:
                print(f"⚠️  Warning: Could not stage {file}")

        # Check if there are changes to commit
        result = run_git_command(['diff', '--cached', '--quiet'], repo_root, check=False)
        if result.returncode == 0:
            print("ℹ️  No changes to commit")
            return True

        # Commit
        print("💾 Committing changes...")
        run_git_command(['commit', '-m', commit_message], repo_root)
        print("✓ Committed successfully")

        # Try to push
        print("🚀 Pushing to remote...")
        result = run_git_command(['push', 'origin', 'main'], repo_root, check=False)

        if result.returncode == 0:
            print("✓ Pushed successfully")
            return True

        # Push failed - likely need to pull first
        if 'rejected' in result.stderr or 'fetch first' in result.stderr:
            print("⚠️  Remote has new changes, pulling with rebase...")

            # Try pull with rebase
            result = run_git_command(['pull', '--rebase', 'origin', 'main'], repo_root, check=False)

            if result.returncode == 0:
                # Rebase succeeded, try push again
                print("✓ Rebase successful, pushing...")
                result = run_git_command(['push', 'origin', 'main'], repo_root, check=False)
                if result.returncode == 0:
                    print("✓ Pushed successfully")
                    return True
                else:
                    print(f"✗ Push failed: {result.stderr}")
                    return False
            else:
                # Rebase failed (likely conflicts)
                print("⚠️  Rebase failed (conflicts detected)")

                if auto_resolve_conflicts:
                    print("🔄 Auto-resolving: aborting rebase and resetting to origin/main...")

                    # Abort rebase
                    run_git_command(['rebase', '--abort'], repo_root, check=False)

                    # Reset to origin/main
                    run_git_command(['reset', '--hard', 'origin/main'], repo_root)
                    print("✓ Reset to origin/main")

                    # Stage and commit again
                    print("📝 Re-staging and committing...")
                    for file in files:
                        run_git_command(['add', file], repo_root, check=False)

                    run_git_command(['commit', '-m', commit_message], repo_root)

                    # Push
                    result = run_git_command(['push', 'origin', 'main'], repo_root, check=False)
                    if result.returncode == 0:
                        print("✓ Pushed successfully after reset")
                        return True
                    else:
                        print(f"✗ Push still failed: {result.stderr}")
                        return False
                else:
                    print("✗ Rebase conflicts - manual resolution required")
                    return False
        else:
            print(f"✗ Push failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ Error during git operations: {e}")
        return False


def main():
    """CLI interface for testing."""
    if len(sys.argv) < 3:
        print("Usage: git_push_helper.py <file1> [file2 ...] --message 'commit message'")
        sys.exit(1)

    # Parse arguments
    files = []
    commit_msg = None

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ['-m', '--message']:
            commit_msg = sys.argv[i + 1]
            i += 2
        else:
            files.append(sys.argv[i])
            i += 1

    if not commit_msg:
        print("Error: --message is required")
        sys.exit(1)

    repo_root = Path.cwd()

    success = git_commit_and_push(files, commit_msg, repo_root)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
