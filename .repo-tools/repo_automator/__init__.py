"""
Repository Automation Tool

A portable tool that automatically updates READMEs and metadata
when files are added or modified in the repository.

SAFETY: This tool NEVER deletes files. It only modifies:
- README.md / readme.md files
- Metadata text files (.txt, .csv)
- SVG header stats
"""

__version__ = "1.0.0"
__author__ = "Scientific Resources Hub"

from .config import Config
from .runner import Runner
from .cli import main

__all__ = ["Config", "Runner", "main", "__version__"]
