"""
Update README.md statistics.

This updater modifies ONLY README files.
It updates stats like paper counts, category counts, and repo size.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .base import BaseUpdater


class ReadmeUpdater(BaseUpdater):
    """
    Update statistics in README.md files.

    SAFETY: Only modifies README.md and readme.md files.
    """

    name = "readme_updater"

    # Patterns to find and replace in main README
    UPDATE_PATTERNS = [
        # Highlights table stats (HTML format)
        (
            r'(<h3>📄 )\d+\+?(</h3>)',
            r'\g<1>{reviews}+\2',
            "papers_highlight"
        ),
        (
            r'(<h3>📚 )\d+(</h3>)',
            r'\g<1>{categories}\2',
            "categories_highlight"
        ),
        (
            r'(<h3>🎯 )[\d.]+( GB</h3>)',
            r'\g<1>{size_gb:.1f}\2',
            "size_highlight"
        ),
        # Text mentions
        (
            r'(\*\*)\d+( comprehensive paper reviews)',
            r'\g<1>{reviews}\2',
            "papers_text"
        ),
        (
            r'(\*\*)\d+( learning categories)',
            r'\g<1>{categories}\2',
            "categories_text"
        ),
        # Collection Statistics table
        (
            r'(\| \*\*Total Paper Reviews\*\* \| )\d+',
            r'\g<1>{reviews}',
            "stats_table_papers"
        ),
        (
            r'(\| \*\*Learning Categories\*\* \| )\d+',
            r'\g<1>{categories}',
            "stats_table_categories"
        ),
        (
            r'(\| \*\*Total Repository Size\*\* \| )[\d.]+( GB)',
            r'\g<1>{size_gb:.1f}\2',
            "stats_table_size"
        ),
        (
            r'(\| \*\*Presentations\*\* \| )\d+',
            r'\g<1>{presentations}',
            "stats_table_presentations"
        ),
    ]

    def update(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update main README with current stats.

        Args:
            scan_results: Results from FileCounterScanner

        Returns:
            Dict with update details
        """
        results = {
            "files_updated": [],
            "changes": [],
            "errors": []
        }

        # Get stats from scan results
        stats = {
            "reviews": scan_results.get("reviews", {}).get("total", 0),
            "categories": scan_results.get("categories", {}).get("total", 0),
            "size_gb": scan_results.get("repo_size_gb", 0),
            "presentations": scan_results.get("presentations", {}).get("total", 0),
        }

        # Update main README
        main_readme = self.repo_root / "README.md"
        if main_readme.exists():
            updated, changes = self._update_readme(main_readme, stats)
            if updated:
                results["files_updated"].append(str(main_readme.name))
                results["changes"].extend(changes)

        # Update mike-paper-reviews-all README if exists
        reviews_readme = self.repo_root / "mike-paper-reviews-all" / "readme.md"
        if reviews_readme.exists():
            updated, changes = self._update_reviews_readme(reviews_readme, stats)
            if updated:
                results["files_updated"].append("mike-paper-reviews-all/readme.md")
                results["changes"].extend(changes)

        if not results["files_updated"]:
            self.log("ℹ️  All READMEs already up to date")

        return results

    def _update_readme(
        self,
        readme_path: Path,
        stats: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Update a README file with stats.

        Returns:
            Tuple of (was_updated, list_of_changes)
        """
        try:
            content = readme_path.read_text(encoding='utf-8')
        except IOError as e:
            self.log(f"Error reading {readme_path}: {e}", level=40)
            return False, []

        original_content = content
        changes = []

        for pattern, replacement, change_name in self.UPDATE_PATTERNS:
            # Format replacement with stats
            formatted_replacement = replacement.format(**stats)

            # Apply replacement
            new_content, count = re.subn(pattern, formatted_replacement, content)

            if count > 0 and new_content != content:
                changes.append(change_name)
                content = new_content

        # Write if changed
        if content != original_content:
            if self._write_file(readme_path, content):
                return True, changes

        return False, []

    def _update_reviews_readme(
        self,
        readme_path: Path,
        stats: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Update the mike-paper-reviews-all README.

        Returns:
            Tuple of (was_updated, list_of_changes)
        """
        try:
            content = readme_path.read_text(encoding='utf-8')
        except IOError as e:
            self.log(f"Error reading {readme_path}: {e}", level=40)
            return False, []

        original_content = content
        changes = []

        # Patterns specific to reviews README
        patterns = [
            (
                r'(\*\*)\d+( Individual Files\*\*)',
                r'\g<1>{reviews}\2'.format(**stats),
                "reviews_individual_count"
            ),
            (
                r'(Reviews 1-)\d+',
                r'\g<1>{reviews}'.format(**stats),
                "reviews_range"
            ),
        ]

        for pattern, replacement, change_name in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0 and new_content != content:
                changes.append(change_name)
                content = new_content

        if content != original_content:
            if self._write_file(readme_path, content):
                return True, changes

        return False, []
