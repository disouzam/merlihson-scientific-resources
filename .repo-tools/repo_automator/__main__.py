"""
Entry point for repo_automator.

Allows running as: python -m repo_automator
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
