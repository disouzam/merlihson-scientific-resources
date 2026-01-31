"""
Count files in directories and generate statistics.

This scanner is READ-ONLY. It only counts and reports.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseScanner


class FileCounterScanner(BaseScanner):
    """
    Count files by type and directory.

    READ-ONLY: Only scans and reports, never modifies files.
    """

    name = "file_counter"

    def scan(self) -> Dict[str, Any]:
        """
        Scan repository and count files.

        Returns:
            Dict with counts for reviews, categories, size, presentations
        """
        results = {
            "reviews": self._count_reviews(),
            "categories": self._count_categories(),
            "repo_size_gb": self._calculate_repo_size(),
            "presentations": self._count_presentations(),
        }

        self.log(
            f"Scan complete: {results['reviews']['total']} reviews, "
            f"{results['categories']['total']} categories, "
            f"{results['repo_size_gb']:.2f} GB"
        )

        return results

    def _count_reviews(self) -> Dict[str, Any]:
        """Count DOCX review files."""
        reviews_path = self.repo_root / "mike-paper-reviews-all" / "split-reviews-docx"

        if not reviews_path.exists():
            self.log(f"Reviews path not found: {reviews_path}", level=30)
            return {"total": 0, "highest_number": 0}

        # Count all review files (including typos like "Reveiw_")
        docx_files = list(reviews_path.glob("*eview_*.docx"))

        # Extract review numbers to find highest
        numbers = []
        for f in docx_files:
            match = re.search(r'_(\d+)', f.stem)
            if match:
                numbers.append(int(match.group(1)))

        return {
            "total": len(docx_files),
            "highest_number": max(numbers) if numbers else 0,
            "files": [f.name for f in sorted(docx_files)[:5]]  # First 5 for preview
        }

    def _count_categories(self) -> Dict[str, Any]:
        """Count learning material categories."""
        lm_path = self.repo_root / "learning materials"

        if not lm_path.exists():
            self.log(f"Learning materials path not found: {lm_path}", level=30)
            return {"total": 0, "names": []}

        # Count directories (categories)
        categories = [
            d.name for d in lm_path.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        return {
            "total": len(categories),
            "names": sorted(categories)
        }

    def _calculate_repo_size(self) -> float:
        """
        Calculate total repository size in GB.

        Excludes .git directory and hidden files.
        """
        total_bytes = 0

        for f in self.repo_root.rglob("*"):
            # Skip hidden files and .git
            if any(part.startswith('.') for part in f.parts):
                continue

            if f.is_file():
                try:
                    total_bytes += f.stat().st_size
                except OSError:
                    pass

        return total_bytes / (1024 ** 3)

    def _count_presentations(self) -> Dict[str, Any]:
        """Count presentation files."""
        pres_path = self.repo_root / "presentations"

        if not pres_path.exists():
            return {"total": 0, "files": []}

        # Count PDF and PPTX files
        presentations = [
            f for f in pres_path.iterdir()
            if f.is_file() and f.suffix.lower() in ['.pdf', '.pptx']
            and not f.name.startswith('.')
        ]

        return {
            "total": len(presentations),
            "files": [f.name for f in sorted(presentations)]
        }

    def get_category_file_counts(self) -> Dict[str, int]:
        """
        Get file counts for each learning material category.

        Returns:
            Dict mapping category name -> file count
        """
        lm_path = self.repo_root / "learning materials"
        counts = {}

        if not lm_path.exists():
            return counts

        for category_dir in lm_path.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.'):
                continue

            # Count files recursively
            file_count = sum(
                1 for f in category_dir.rglob("*")
                if f.is_file() and not f.name.startswith('.')
            )
            counts[category_dir.name] = file_count

        return counts
