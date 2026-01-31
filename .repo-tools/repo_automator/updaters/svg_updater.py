"""
Update SVG header statistics.

This updater modifies ONLY the cosmic-neural-header.svg file.
It updates the embedded stat boxes (papers, categories, size, coverage).
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .base import BaseUpdater


class SvgUpdater(BaseUpdater):
    """
    Update statistics embedded in SVG header.

    SAFETY: Only modifies cosmic-neural-header.svg file.
    """

    name = "svg_updater"

    def update(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update SVG header with current stats.

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

        # Get stats
        stats = {
            "reviews": scan_results.get("reviews", {}).get("total", 0),
            "categories": scan_results.get("categories", {}).get("total", 0),
            "size_gb": scan_results.get("repo_size_gb", 0),
        }

        # Find SVG file
        svg_path = self.repo_root / "images" / "cosmic-neural-header.svg"

        if not svg_path.exists():
            self.log(f"SVG header not found: {svg_path}", level=30)
            results["errors"].append(f"SVG not found: {svg_path}")
            return results

        # Update SVG
        updated, changes = self._update_svg(svg_path, stats)

        if updated:
            results["files_updated"].append("images/cosmic-neural-header.svg")
            results["changes"] = changes
        else:
            self.log("ℹ️  SVG header already up to date")

        return results

    def _update_svg(
        self,
        svg_path: Path,
        stats: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Update SVG file with stats.

        The SVG has stat boxes with patterns like:
        <text ... fill="#58a6ff">569+</text>
        <text ... >PAPER REVIEWS</text>

        Returns:
            Tuple of (was_updated, list_of_changes)
        """
        try:
            content = svg_path.read_text(encoding='utf-8')
        except IOError as e:
            self.log(f"Error reading {svg_path}: {e}", level=40)
            return False, []

        original_content = content
        changes = []

        # Patterns for SVG stat boxes
        # Based on the actual cosmic-neural-header.svg structure
        patterns = [
            # Papers count (blue box) - matches the exact structure
            (
                r'(font-weight="700" fill="#58a6ff">)\d+\+?(<\/text>)',
                f'\\g<1>{stats["reviews"]}+\\2',
                "svg_papers"
            ),
            # Categories count (purple box)
            (
                r'(font-weight="700" fill="#a371f7">)\d+(<\/text>)',
                f'\\g<1>{stats["categories"]}\\2',
                "svg_categories"
            ),
            # Size (green box)
            (
                r'(font-weight="700" fill="#3fb950">)[\d.]+( GB<\/text>)',
                f'\\g<1>{stats["size_gb"]:.1f}\\2',
                "svg_size"
            ),
        ]

        for pattern, replacement, change_name in patterns:
            new_content, count = re.subn(pattern, replacement, content)

            if count > 0 and new_content != content:
                changes.append(change_name)
                content = new_content

        # Write if changed
        if content != original_content:
            if self._write_file(svg_path, content):
                return True, changes

        return False, []
