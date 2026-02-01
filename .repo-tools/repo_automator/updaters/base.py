"""
Abstract base class for updaters.

Updaters modify specific files (READMEs, metadata, SVG).
They have a WHITELIST of files they can modify - nothing else.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List
import logging


class BaseUpdater(ABC):
    """
    Base class for all repository updaters.

    SAFETY: Updaters can ONLY modify whitelisted files:
    - README.md / readme.md files
    - Metadata .txt and .csv files
    - SVG header file

    They will NEVER modify or delete content files (PDFs, DOCX, images, etc.)
    """

    # Whitelist of file patterns that can be modified
    ALLOWED_PATTERNS = [
        "README.md",
        "readme.md",
        "*.txt",
        "*.csv",
        "cosmic-neural-header.svg",
    ]

    # Directories where modifications are allowed
    ALLOWED_DIRECTORIES = [
        ".",  # Root README
        "mike-paper-reviews-all",
        "mike-paper-reviews-all/reviews_metadata",
        "learning-materials",
        "images",
    ]

    def __init__(
        self,
        repo_root: Path,
        config: Dict[str, Any] = None,
        dry_run: bool = False
    ):
        """
        Initialize updater.

        Args:
            repo_root: Path to repository root
            config: Optional configuration dict
            dry_run: If True, preview changes without applying
        """
        self.repo_root = Path(repo_root).resolve()
        self.config = config or {}
        self.dry_run = dry_run
        self.logger = logging.getLogger("repo_automator")

    @abstractmethod
    def update(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform update based on scan results.

        Args:
            scan_results: Data from scanners

        Returns:
            Dict with update details
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Updater name for logging."""
        pass

    def _is_allowed_file(self, path: Path) -> bool:
        """
        Check if file is in the whitelist and can be modified.

        Args:
            path: Path to check

        Returns:
            True if file can be modified, False otherwise
        """
        # Must be within repo
        try:
            rel_path = path.relative_to(self.repo_root)
        except ValueError:
            return False

        # Check file name against allowed patterns
        filename = path.name
        allowed_name = any(
            filename == pattern or
            (pattern.startswith("*") and filename.endswith(pattern[1:]))
            for pattern in self.ALLOWED_PATTERNS
        )

        if not allowed_name:
            return False

        # Check directory against allowed directories
        parent = str(rel_path.parent)
        if parent == ".":
            return True  # Root directory

        # Check if any part of the path matches allowed directories
        for allowed_dir in self.ALLOWED_DIRECTORIES:
            if parent == allowed_dir or parent.startswith(allowed_dir + "/"):
                return True

        # Also allow any learning-materials subdirectory (for their READMEs)
        if "learning-materials" in parent:
            return True

        return False

    def _write_file(self, path: Path, content: str) -> bool:
        """
        Write file with safety checks and dry-run support.

        Args:
            path: Path to write
            content: Content to write

        Returns:
            True if file was written, False if dry-run or not allowed
        """
        path = Path(path).resolve()

        # Safety check
        if not self._is_allowed_file(path):
            self.logger.error(
                f"❌ BLOCKED: Cannot modify {path} - not in whitelist"
            )
            return False

        if self.dry_run:
            self.logger.info(f"🔄 [DRY-RUN] Would update: {path.name}")
            return False

        try:
            path.write_text(content, encoding='utf-8')
            self.logger.info(f"✅ Updated: {path.name}")
            return True
        except IOError as e:
            self.logger.error(f"❌ Failed to write {path}: {e}")
            return False

    def log(self, message: str, level: int = logging.INFO):
        """Log a message with updater name prefix."""
        self.logger.log(level, f"[{self.name}] {message}")
