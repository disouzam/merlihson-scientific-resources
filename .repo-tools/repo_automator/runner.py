"""
Runner that orchestrates scanners and updaters.

This is the main execution engine that:
1. Runs scanners to collect repository data
2. Passes results to updaters to modify READMEs and metadata
3. Provides summary of all changes

SAFETY: Runner enforces read-only scanning and whitelist-only updates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .config import Config
from .scanners.base import BaseScanner
from .scanners.file_counter import FileCounterScanner
from .scanners.duplicate_detector import DuplicateDetectorScanner
from .updaters.base import BaseUpdater
from .updaters.readme_updater import ReadmeUpdater
from .updaters.svg_updater import SvgUpdater
from .updaters.metadata_updater import MetadataUpdater
from .utils.logging import get_logger, log_scan, log_update, log_success


class Runner:
    """
    Orchestrates scanning and updating operations.

    SAFETY GUARANTEES:
    - Scanners are READ-ONLY
    - Updaters can ONLY modify whitelisted files
    - Never deletes any files
    """

    # Available scanners
    SCANNER_CLASSES: List[Type[BaseScanner]] = [
        FileCounterScanner,
        DuplicateDetectorScanner,
    ]

    # Available updaters
    UPDATER_CLASSES: List[Type[BaseUpdater]] = [
        ReadmeUpdater,
        SvgUpdater,
        MetadataUpdater,
    ]

    def __init__(
        self,
        config: Optional[Config] = None,
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize runner.

        Args:
            config: Configuration object (auto-created if None)
            dry_run: If True, preview changes without applying
            verbose: If True, enable verbose output
        """
        self.config = config or Config()
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = get_logger()

        # Set log level
        if verbose:
            self.logger.setLevel(logging.DEBUG)

    def scan(
        self,
        scanners: Optional[List[str]] = None,
        duplicates_only: bool = False
    ) -> Dict[str, Any]:
        """
        Run scanners to collect repository data.

        Args:
            scanners: List of scanner names to run (all if None)
            duplicates_only: If True, only run duplicate detection

        Returns:
            Combined results from all scanners
        """
        results: Dict[str, Any] = {}

        # Determine which scanners to run
        scanner_classes = self._get_scanner_classes(scanners, duplicates_only)

        log_scan(f"Running {len(scanner_classes)} scanner(s)...")

        for scanner_cls in scanner_classes:
            scanner = scanner_cls(self.config.repo_root)
            scanner_name = scanner.name

            if self.verbose:
                self.logger.debug(f"Running scanner: {scanner_name}")

            try:
                scanner_results = scanner.scan()
                results.update(scanner_results)

                if self.verbose:
                    self.logger.debug(f"Scanner {scanner_name} completed")

            except Exception as e:
                self.logger.error(f"Scanner {scanner_name} failed: {e}")
                results[f"{scanner_name}_error"] = str(e)

        return results

    def update(
        self,
        scan_results: Dict[str, Any],
        updaters: Optional[List[str]] = None,
        readme_only: bool = False,
        svg_only: bool = False
    ) -> Dict[str, Any]:
        """
        Run updaters to modify repository files.

        Args:
            scan_results: Results from scanning phase
            updaters: List of updater names to run (all if None)
            readme_only: If True, only update README files
            svg_only: If True, only update SVG header

        Returns:
            Combined results from all updaters
        """
        results: Dict[str, Any] = {
            "files_updated": [],
            "changes": [],
            "errors": [],
        }

        # Determine which updaters to run
        updater_classes = self._get_updater_classes(updaters, readme_only, svg_only)

        log_update(f"Running {len(updater_classes)} updater(s)...")

        if self.dry_run:
            self.logger.info("🔄 DRY-RUN MODE - No files will be modified")

        for updater_cls in updater_classes:
            updater = updater_cls(
                self.config.repo_root,
                dry_run=self.dry_run
            )
            updater_name = updater.name

            if self.verbose:
                self.logger.debug(f"Running updater: {updater_name}")

            try:
                updater_results = updater.update(scan_results)

                # Aggregate results
                results["files_updated"].extend(
                    updater_results.get("files_updated", [])
                )
                results["changes"].extend(
                    updater_results.get("changes", [])
                )
                results["errors"].extend(
                    updater_results.get("errors", [])
                )

            except Exception as e:
                self.logger.error(f"Updater {updater_name} failed: {e}")
                results["errors"].append(f"{updater_name}: {str(e)}")

        return results

    def run(
        self,
        scanners: Optional[List[str]] = None,
        updaters: Optional[List[str]] = None,
        duplicates_only: bool = False,
        readme_only: bool = False,
        svg_only: bool = False,
        scan_only: bool = False
    ) -> Dict[str, Any]:
        """
        Run full automation pipeline.

        Args:
            scanners: List of scanner names to run
            updaters: List of updater names to run
            duplicates_only: Only run duplicate detection
            readme_only: Only update README files
            svg_only: Only update SVG header
            scan_only: Only scan, don't update

        Returns:
            Combined results from scanning and updating
        """
        self.logger.info("=" * 50)
        self.logger.info("🚀 Repository Automator")
        self.logger.info("=" * 50)

        # Phase 1: Scan
        scan_results = self.scan(
            scanners=scanners,
            duplicates_only=duplicates_only
        )

        # Log scan summary
        self._log_scan_summary(scan_results)

        if scan_only:
            return {"scan_results": scan_results}

        # Phase 2: Update
        update_results = self.update(
            scan_results,
            updaters=updaters,
            readme_only=readme_only,
            svg_only=svg_only
        )

        # Log update summary
        self._log_update_summary(update_results)

        return {
            "scan_results": scan_results,
            "update_results": update_results
        }

    def _get_scanner_classes(
        self,
        names: Optional[List[str]],
        duplicates_only: bool
    ) -> List[Type[BaseScanner]]:
        """Get scanner classes to run based on filters."""
        if duplicates_only:
            return [DuplicateDetectorScanner]

        if names:
            return [
                cls for cls in self.SCANNER_CLASSES
                if cls.__name__.lower().replace("scanner", "") in [n.lower() for n in names]
            ]

        return self.SCANNER_CLASSES

    def _get_updater_classes(
        self,
        names: Optional[List[str]],
        readme_only: bool,
        svg_only: bool
    ) -> List[Type[BaseUpdater]]:
        """Get updater classes to run based on filters."""
        if readme_only:
            return [ReadmeUpdater]

        if svg_only:
            return [SvgUpdater]

        if names:
            return [
                cls for cls in self.UPDATER_CLASSES
                if cls.__name__.lower().replace("updater", "") in [n.lower() for n in names]
            ]

        return self.UPDATER_CLASSES

    def _log_scan_summary(self, results: Dict[str, Any]) -> None:
        """Log summary of scan results."""
        self.logger.info("")
        self.logger.info("📊 Scan Results:")

        # Reviews
        reviews = results.get("reviews", {})
        if reviews:
            self.logger.info(f"   📄 Reviews: {reviews.get('total', 0)}")

        # Categories
        categories = results.get("categories", {})
        if categories:
            self.logger.info(f"   📚 Categories: {categories.get('total', 0)}")

        # Repo size
        size = results.get("repo_size_gb", 0)
        if size:
            self.logger.info(f"   💾 Repo Size: {size:.1f} GB")

        # Duplicates
        duplicates = results.get("duplicates", {})
        if duplicates:
            dup_count = duplicates.get("total_duplicate_sets", 0)
            if dup_count > 0:
                self.logger.info(f"   ⚠️  Duplicates Found: {dup_count} sets")
                self.logger.info("      (Run with --verbose for details)")

    def _log_update_summary(self, results: Dict[str, Any]) -> None:
        """Log summary of update results."""
        self.logger.info("")

        files_updated = results.get("files_updated", [])
        errors = results.get("errors", [])

        if files_updated:
            log_success(f"Updated {len(files_updated)} file(s):")
            for f in files_updated:
                self.logger.info(f"   ✅ {f}")
        else:
            self.logger.info("ℹ️  No files needed updating")

        if errors:
            self.logger.error(f"❌ {len(errors)} error(s) occurred:")
            for e in errors:
                self.logger.error(f"   {e}")

        self.logger.info("")
        self.logger.info("=" * 50)
