"""
Abstract base class for scanners.

Scanners analyze the repository and return data.
They are READ-ONLY - they never modify any files.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict
import logging


class BaseScanner(ABC):
    """
    Base class for all repository scanners.

    Scanners are READ-ONLY. They analyze files and return data
    but never modify or delete anything.
    """

    def __init__(self, repo_root: Path, config: Dict[str, Any] = None):
        """
        Initialize scanner.

        Args:
            repo_root: Path to repository root
            config: Optional configuration dict
        """
        self.repo_root = Path(repo_root).resolve()
        self.config = config or {}
        self.logger = logging.getLogger("repo_automator")

    @abstractmethod
    def scan(self) -> Dict[str, Any]:
        """
        Perform scan and return results.

        Returns:
            Dict with scanner-specific data
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner name for logging."""
        pass

    def log(self, message: str, level: int = logging.INFO):
        """Log a message with scanner name prefix."""
        self.logger.log(level, f"[{self.name}] {message}")
