"""
Debouncing utility to wait for file operations to settle.

When multiple files are added/modified in quick succession (e.g., drag-and-drop),
this ensures we only trigger the automation once after all operations complete.
"""

import threading
from typing import Callable, List, Set
from datetime import datetime


class Debouncer:
    """
    Debounce rapid file events into a single callback.
    Waits for events to settle before triggering action.

    Example:
        debouncer = Debouncer(wait_seconds=2.0)

        # These rapid calls will be batched
        debouncer.call(callback, "/path/to/file1.pdf")
        debouncer.call(callback, "/path/to/file2.pdf")
        debouncer.call(callback, "/path/to/file3.pdf")

        # After 2 seconds of no new calls, callback is invoked once
        # with all accumulated paths
    """

    def __init__(self, wait_seconds: float = 2.0, max_wait_seconds: float = 10.0):
        """
        Initialize debouncer.

        Args:
            wait_seconds: Seconds to wait after last event before triggering
            max_wait_seconds: Maximum seconds to wait before forcing trigger
        """
        self.wait_seconds = wait_seconds
        self.max_wait_seconds = max_wait_seconds
        self._timer = None
        self._first_event_time = None
        self._lock = threading.Lock()
        self._pending_paths: Set[str] = set()
        self._pending_callback = None

    def call(self, callback: Callable[[List[str]], None], path: str):
        """
        Schedule callback with debouncing.

        Args:
            callback: Function to call with list of paths
            path: File path that triggered this call
        """
        with self._lock:
            self._pending_paths.add(path)
            self._pending_callback = callback

            now = datetime.now()

            # Record first event time
            if self._first_event_time is None:
                self._first_event_time = now

            # Cancel existing timer
            if self._timer is not None:
                self._timer.cancel()

            # Check if max wait exceeded - force execution
            elapsed = (now - self._first_event_time).total_seconds()
            if elapsed >= self.max_wait_seconds:
                self._execute_locked()
                return

            # Schedule new timer
            self._timer = threading.Timer(
                self.wait_seconds,
                self._execute
            )
            self._timer.daemon = True
            self._timer.start()

    def _execute(self):
        """Execute callback (called from timer thread)."""
        with self._lock:
            self._execute_locked()

    def _execute_locked(self):
        """Execute callback (must hold lock)."""
        if not self._pending_paths or not self._pending_callback:
            return

        # Get and clear pending state
        paths = list(self._pending_paths)
        callback = self._pending_callback

        self._pending_paths.clear()
        self._pending_callback = None
        self._first_event_time = None
        self._timer = None

        # Execute callback outside lock
        try:
            callback(paths)
        except Exception as e:
            import logging
            logging.getLogger("repo_automator").error(f"Debounced callback error: {e}")

    def cancel(self):
        """Cancel any pending callback."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._pending_paths.clear()
            self._pending_callback = None
            self._first_event_time = None

    @property
    def pending_count(self) -> int:
        """Number of pending paths."""
        with self._lock:
            return len(self._pending_paths)
