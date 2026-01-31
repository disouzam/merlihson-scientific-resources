"""
Command-line interface for repo_automator.

Provides commands:
- scan: Scan repository for stats and issues
- update: Update README and metadata files
- run: Full scan + update pipeline
- watch: Start file watcher daemon
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .config import Config
from .runner import Runner
from .utils.logging import setup_logging, get_logger


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands."""
    # Create parent parser with common options
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    common_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    common_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )
    common_parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml (default: auto-detect)",
    )
    common_parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root path (default: auto-detect)",
    )

    # Main parser
    parser = argparse.ArgumentParser(
        prog="repo-auto",
        description="Repository automation tool - keeps READMEs and stats in sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  repo-auto run                    Run full automation
  repo-auto run --dry-run          Preview changes without applying
  repo-auto scan                   Just scan, don't update
  repo-auto scan --duplicates-only Check for duplicates
  repo-auto update --readme-only   Only update README files
  repo-auto watch                  Start file watcher daemon

SAFETY: This tool NEVER deletes files. It can only modify:
  - README.md / readme.md files
  - Metadata .txt and .csv files
  - cosmic-neural-header.svg
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan repository for stats and issues (read-only)",
        parents=[common_parser],
    )
    scan_parser.add_argument(
        "--duplicates-only",
        action="store_true",
        help="Only check for duplicate files",
    )

    # update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update README and metadata files",
        parents=[common_parser],
    )
    update_parser.add_argument(
        "--readme-only",
        action="store_true",
        help="Only update README files",
    )
    update_parser.add_argument(
        "--svg-only",
        action="store_true",
        help="Only update SVG header",
    )

    # run command (scan + update)
    run_parser = subparsers.add_parser(
        "run",
        help="Run full automation (scan + update)",
        parents=[common_parser],
    )
    run_parser.add_argument(
        "--duplicates-only",
        action="store_true",
        help="Only check for duplicates (no updates)",
    )
    run_parser.add_argument(
        "--readme-only",
        action="store_true",
        help="Only update README files",
    )
    run_parser.add_argument(
        "--svg-only",
        action="store_true",
        help="Only update SVG header",
    )
    run_parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan, don't update files",
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Start file watcher daemon",
        parents=[common_parser],
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        help="Debounce wait time in seconds (default: 2.0)",
    )

    return parser


def cmd_scan(args: argparse.Namespace, config: Config) -> int:
    """Handle scan command."""
    runner = Runner(
        config=config,
        dry_run=True,  # Scan is always read-only
        verbose=args.verbose,
    )

    results = runner.scan(duplicates_only=args.duplicates_only)

    # If duplicates found, show detailed report
    if args.duplicates_only and results.get("duplicates"):
        duplicates = results["duplicates"]
        if duplicates.get("total_duplicate_sets", 0) > 0:
            logger = get_logger()
            logger.info("\n" + duplicates.get("report", ""))

    return 0


def cmd_update(args: argparse.Namespace, config: Config) -> int:
    """Handle update command."""
    # First scan to get current stats
    runner = Runner(
        config=config,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    scan_results = runner.scan()
    update_results = runner.update(
        scan_results,
        readme_only=args.readme_only,
        svg_only=args.svg_only,
    )

    if update_results.get("errors"):
        return 1

    return 0


def cmd_run(args: argparse.Namespace, config: Config) -> int:
    """Handle run command (full pipeline)."""
    runner = Runner(
        config=config,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    results = runner.run(
        duplicates_only=args.duplicates_only,
        readme_only=getattr(args, 'readme_only', False),
        svg_only=getattr(args, 'svg_only', False),
        scan_only=getattr(args, 'scan_only', False),
    )

    # Check for errors
    update_results = results.get("update_results", {})
    if update_results.get("errors"):
        return 1

    return 0


def cmd_watch(args: argparse.Namespace, config: Config) -> int:
    """Handle watch command."""
    try:
        from .watcher import FileWatcher
    except ImportError:
        logger = get_logger()
        logger.error("File watcher not available. Install watchdog: pip install watchdog")
        return 1

    logger = get_logger()
    logger.info("🔍 Starting file watcher...")
    logger.info("   Press Ctrl+C to stop")

    watcher = FileWatcher(
        config=config,
        dry_run=args.dry_run,
        debounce_seconds=args.debounce,
    )

    try:
        watcher.start()
        # Block until interrupted
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n👋 Stopping watcher...")
        watcher.stop()

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    if args.quiet:
        setup_logging(level="ERROR")
    elif args.verbose:
        setup_logging(level="DEBUG")
    else:
        setup_logging(level="INFO")

    # Load config
    config = Config(
        config_path=args.config,
        repo_root=args.repo_root,
    )

    # Default to 'run' if no command specified
    if not args.command:
        args.command = "run"
        args.duplicates_only = False
        args.readme_only = False
        args.svg_only = False
        args.scan_only = False

    # Dispatch to command handler
    handlers = {
        "scan": cmd_scan,
        "update": cmd_update,
        "run": cmd_run,
        "watch": cmd_watch,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args, config)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
