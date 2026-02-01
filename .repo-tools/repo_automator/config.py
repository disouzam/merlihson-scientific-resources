"""
Configuration loader for repo_automator.

Loads and validates config.yaml settings.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class Config:
    """
    Configuration manager for repo_automator.

    Loads settings from config.yaml and provides typed access.
    """

    DEFAULT_CONFIG = {
        "watched_paths": {
            "reviews": "mike-paper-reviews-all/split-reviews-docx",
            "learning_materials": "learning-materials",
            "presentations": "presentations",
        },
        "file_extensions": {
            "documents": [".pdf", ".docx", ".pptx"],
            "images": [".png", ".jpg", ".jpeg", ".gif", ".svg"],
        },
        "modifiable_files": {
            "readme_patterns": ["README.md", "readme.md"],
            "metadata_patterns": ["*.txt", "*.csv"],
            "svg_files": ["cosmic-neural-header.svg"],
        },
        "debounce": {
            "wait_seconds": 2,
            "max_wait_seconds": 10,
        },
        "logging": {
            "level": "INFO",
            "use_emoji": True,
        },
    }

    def __init__(self, config_path: Optional[Path] = None, repo_root: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config.yaml (auto-detected if None)
            repo_root: Repository root path (auto-detected if None)
        """
        self._config: Dict[str, Any] = {}
        self._repo_root: Optional[Path] = None

        # Find repo root
        if repo_root:
            self._repo_root = Path(repo_root).resolve()
        else:
            self._repo_root = self._find_repo_root()

        # Load config
        if config_path:
            self._load_config(Path(config_path))
        else:
            self._load_config(self._find_config_file())

    def _find_repo_root(self) -> Path:
        """Find repository root by looking for .git directory."""
        current = Path(__file__).resolve().parent

        # Walk up to find .git
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent

        # Fallback: assume we're in .repo-tools/repo_automator
        return current.parent.parent

    def _find_config_file(self) -> Optional[Path]:
        """Find config.yaml in .repo-tools directory."""
        if self._repo_root:
            config_path = self._repo_root / ".repo-tools" / "config.yaml"
            if config_path.exists():
                return config_path
        return None

    def _load_config(self, config_path: Optional[Path]) -> None:
        """Load configuration from YAML file."""
        # Start with defaults
        self._config = self.DEFAULT_CONFIG.copy()

        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}

                # Deep merge with defaults
                self._config = self._deep_merge(self._config, file_config)
            except (yaml.YAMLError, IOError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @property
    def repo_root(self) -> Path:
        """Get repository root path."""
        return self._repo_root

    @property
    def watched_paths(self) -> Dict[str, str]:
        """Get watched paths configuration."""
        return self._config.get("watched_paths", {})

    @property
    def file_extensions(self) -> Dict[str, List[str]]:
        """Get file extension configurations."""
        return self._config.get("file_extensions", {})

    @property
    def modifiable_files(self) -> Dict[str, List[str]]:
        """Get modifiable file patterns."""
        return self._config.get("modifiable_files", {})

    @property
    def debounce_wait(self) -> float:
        """Get debounce wait time in seconds."""
        return self._config.get("debounce", {}).get("wait_seconds", 2)

    @property
    def debounce_max_wait(self) -> float:
        """Get maximum debounce wait time in seconds."""
        return self._config.get("debounce", {}).get("max_wait_seconds", 10)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config.get("logging", {}).get("level", "INFO")

    @property
    def use_emoji(self) -> bool:
        """Get emoji usage preference."""
        return self._config.get("logging", {}).get("use_emoji", True)

    def get_watched_path(self, name: str) -> Optional[Path]:
        """
        Get absolute path for a watched directory.

        Args:
            name: Name of watched path (e.g., 'reviews', 'learning_materials')

        Returns:
            Absolute Path or None if not configured
        """
        rel_path = self.watched_paths.get(name)
        if rel_path and self._repo_root:
            return self._repo_root / rel_path
        return None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._config.get(key, default)

    def __repr__(self) -> str:
        return f"Config(repo_root={self._repo_root})"
