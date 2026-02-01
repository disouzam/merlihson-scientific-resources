"""
Detect duplicate files using MD5 hashing.

IMPORTANT: This scanner ONLY REPORTS duplicates.
It NEVER deletes or modifies any files.
Users must manually review and handle duplicates.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base import BaseScanner
from ..utils.hashing import find_duplicates, format_duplicates_report


class DuplicateDetectorScanner(BaseScanner):
    """
    Detect duplicate files across the repository.

    ⚠️  READ-ONLY: This scanner ONLY REPORTS duplicates.
    It will NEVER delete or modify any files.
    """

    name = "duplicate_detector"

    def scan(self) -> Dict[str, Any]:
        """
        Scan for duplicate files.

        Returns:
            Dict with duplicate information (for reporting only)
        """
        results = {
            "duplicates_found": [],
            "total_duplicate_sets": 0,
            "total_wasted_bytes": 0,
            "scanned_directories": []
        }

        # Scan learning-materials directory
        lm_path = self.repo_root / "learning-materials"
        if lm_path.exists():
            lm_dupes = self._scan_directory(lm_path, "*.pdf")
            results["scanned_directories"].append("learning-materials")
            self._add_duplicates(results, lm_dupes, lm_path)

        # Log summary
        if results["total_duplicate_sets"] > 0:
            wasted_mb = results["total_wasted_bytes"] / (1024 * 1024)
            self.log(
                f"⚠️  Found {results['total_duplicate_sets']} duplicate file sets "
                f"(~{wasted_mb:.1f} MB wasted). "
                f"Review manually - NO FILES WILL BE DELETED.",
                level=30
            )
        else:
            self.log("✅ No duplicate files detected")

        return results

    def _scan_directory(
        self,
        directory: Path,
        pattern: str = "*"
    ) -> Dict[str, List[Path]]:
        """Scan a directory for duplicates."""
        return find_duplicates(
            directory,
            pattern=pattern,
            recursive=True,
            ignore_patterns=[
                ".DS_Store",
                "*.tmp",
                "*.swp",
                "~*",
                "readme.md",
                "README.md",
                "*.txt"
            ]
        )

    def _add_duplicates(
        self,
        results: Dict[str, Any],
        duplicates: Dict[str, List[Path]],
        base_path: Path
    ):
        """Add duplicates to results."""
        for hash_val, files in duplicates.items():
            # Calculate wasted space (all copies except first)
            try:
                file_size = files[0].stat().st_size
                wasted = file_size * (len(files) - 1)
            except OSError:
                wasted = 0

            results["duplicates_found"].append({
                "hash": hash_val[:12],  # Shortened hash for display
                "files": [
                    str(f.relative_to(self.repo_root))
                    for f in files
                ],
                "count": len(files),
                "wasted_bytes": wasted
            })
            results["total_wasted_bytes"] += wasted

        results["total_duplicate_sets"] = len(results["duplicates_found"])

    def get_report(self) -> str:
        """
        Generate human-readable duplicate report.

        Returns:
            Formatted report string
        """
        scan_results = self.scan()

        if not scan_results["duplicates_found"]:
            return "✅ No duplicate files found in the repository."

        lines = [
            "=" * 60,
            "DUPLICATE FILES REPORT",
            "⚠️  These are reported for MANUAL REVIEW ONLY",
            "⚠️  The automation tool will NEVER delete files",
            "=" * 60,
            ""
        ]

        for i, dupe in enumerate(scan_results["duplicates_found"], 1):
            wasted_mb = dupe["wasted_bytes"] / (1024 * 1024)
            lines.append(f"\n{i}. Duplicate set ({dupe['count']} files, ~{wasted_mb:.2f} MB wasted):")
            for f in dupe["files"]:
                lines.append(f"   - {f}")

        lines.append("")
        lines.append("=" * 60)
        total_wasted_mb = scan_results["total_wasted_bytes"] / (1024 * 1024)
        lines.append(f"Total: {scan_results['total_duplicate_sets']} duplicate sets, ~{total_wasted_mb:.1f} MB wasted")
        lines.append("=" * 60)

        return "\n".join(lines)
