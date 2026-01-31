"""
File watcher for automatic repository updates.

Uses watchdog to monitor file system changes and triggers
updates when files are added, modified, or removed.

SAFETY: Only triggers updates to whitelisted files.
Never deletes any content files.
"""

import time
from pathlib import Path
from threading import Thread
from typing import Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileDeletedEvent,
        FileModifiedEvent,
        FileMovedEvent,
        DirCreatedEvent,
        DirDeletedEvent,
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

from .config import Config
from .runner import Runner
from .utils.debounce import Debouncer
from .utils.logging import get_logger


class RepoEventHandler(FileSystemEventHandler):
    """
    Handle file system events in the repository.

    Filters events to only trigger on relevant file changes
    and debounces rapid changes.
    """

    # File extensions to watch
    WATCHED_EXTENSIONS = {
        '.pdf', '.docx', '.pptx',
        '.png', '.jpg', '.jpeg', '.gif',
        '.md', '.txt', '.csv',
    }

    # Directories to ignore
    IGNORED_DIRS = {
        '.git', '.repo-tools', '__pycache__',
        '.venv', 'venv', 'node_modules',
        '.idea', '.vscode',
    }

    def __init__(
        self,
        config: Config,
        runner: Runner,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize event handler.

        Args:
            config: Configuration object
            runner: Runner to execute updates
            debounce_seconds: Time to wait for batch operations
        """
        super().__init__()
        self.config = config
        self.runner = runner
        self.logger = get_logger()

        # Debouncer to batch rapid changes
        self.debouncer = Debouncer(
            delay=debounce_seconds,
            callback=self._trigger_update
        )

        # Track pending changes
        self._pending_changes: Set[str] = set()

    def _should_process(self, path: str) -> bool:
        """Check if this path should trigger an update."""
        path_obj = Path(path)

        # Ignore hidden files and directories
        if any(part.startswith('.') for part in path_obj.parts):
            return False

        # Ignore specific directories
        if any(ignored in path_obj.parts for ignored in self.IGNORED_DIRS):
            return False

        # Check extension for files
        if path_obj.is_file() or not path_obj.exists():
            suffix = path_obj.suffix.lower()
            if suffix and suffix not in self.WATCHED_EXTENSIONS:
                return False

        return True

    def _handle_event(self, event_type: str, path: str) -> None:
        """Handle a file system event."""
        if not self._should_process(path):
            return

        self.logger.debug(f"📁 {event_type}: {Path(path).name}")
        self._pending_changes.add(event_type)

        # Trigger debounced update
        self.debouncer.call()

    def _trigger_update(self) -> None:
        """Execute update after debounce period."""
        if not self._pending_changes:
            return

        changes = self._pending_changes.copy()
        self._pending_changes.clear()

        self.logger.info(f"🔄 Detected {len(changes)} change(s), updating...")

        try:
            # Run the full pipeline
            self.runner.run()
        except Exception as e:
            self.logger.error(f"❌ Update failed: {e}")

    # Watchdog event handlers
    def on_created(self, event):
        """Handle file/directory creation."""
        self._handle_event("created", event.src_path)

    def on_deleted(self, event):
        """Handle file/directory deletion."""
        self._handle_event("deleted", event.src_path)

    def on_modified(self, event):
        """Handle file modification."""
        # Skip directory modifications (just metadata changes)
        if event.is_directory:
            return
        self._handle_event("modified", event.src_path)

    def on_moved(self, event):
        """Handle file/directory move."""
        self._handle_event("moved", event.src_path)
        self._handle_event("moved_to", event.dest_path)


class FileWatcher:
    """
    File system watcher that triggers repository updates.

    Monitors watched directories and runs the automation
    pipeline when relevant changes are detected.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        dry_run: bool = False,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize file watcher.

        Args:
            config: Configuration object
            dry_run: If True, don't actually modify files
            debounce_seconds: Time to wait for batch operations
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install it with: pip install watchdog"
            )

        self.config = config or Config()
        self.dry_run = dry_run
        self.debounce_seconds = debounce_seconds
        self.logger = get_logger()

        # Create runner
        self.runner = Runner(
            config=self.config,
            dry_run=self.dry_run,
        )

        # Watchdog observer
        self._observer: Optional[Observer] = None
        self._running = False

    def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            self.logger.warning("Watcher already running")
            return

        # Create observer
        self._observer = Observer()

        # Create event handler
        handler = RepoEventHandler(
            config=self.config,
            runner=self.runner,
            debounce_seconds=self.debounce_seconds,
        )

        # Watch repository root
        repo_root = str(self.config.repo_root)
        self._observer.schedule(handler, repo_root, recursive=True)

        # Start observer
        self._observer.start()
        self._running = True

        self.logger.info(f"👀 Watching: {repo_root}")

        # Log watched paths
        for name, rel_path in self.config.watched_paths.items():
            path = self.config.repo_root / rel_path
            if path.exists():
                self.logger.info(f"   📂 {name}: {rel_path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if not self._running or not self._observer:
            return

        self._observer.stop()
        self._observer.join(timeout=5)
        self._running = False

        self.logger.info("👋 Watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
