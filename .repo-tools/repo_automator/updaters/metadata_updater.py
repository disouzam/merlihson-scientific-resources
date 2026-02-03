"""
Metadata Updater - Syncs review metadata from markdown files.

This updater:
1. Scans all Hebrew review markdown files (Review_XXX.md)
2. Extracts paper titles and arxiv links
3. Updates metadata CSV and TXT files
4. Maintains separate title lists for reviews 1-207 and 208+

READ SOURCE: split-hebrew-reviews-md/*.md
WRITE TARGET: reviews_metadata/*.{csv,txt}
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from .base import BaseUpdater


class MetadataUpdater(BaseUpdater):
    """
    Sync metadata files from review markdown files.

    Updates:
    - paper_with_links.csv
    - all_paper_titles.txt
    - clean_titles_for_search.txt
    - reviews_1_207_titles.txt
    - reviews_from_208_titles.txt
    """

    name = "metadata"

    def update(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from markdown files and update all metadata files.

        Args:
            scan_results: Results from scanning phase

        Returns:
            Dict with update results
        """
        results = {
            "files_updated": [],
            "changes": [],
            "errors": []
        }

        self.log("Extracting metadata from Hebrew review files...")

        # Extract metadata from all review files
        reviews_data = self._extract_all_reviews()

        if not reviews_data:
            self.log("No review data extracted", level=30)
            return results

        self.log(f"Extracted {len(reviews_data)} reviews")

        # Update each metadata file
        self._update_paper_with_links(reviews_data, results)
        self._update_all_paper_titles(reviews_data, results)
        self._update_clean_titles(reviews_data, results)
        self._update_reviews_1_207_titles(reviews_data, results)
        self._update_reviews_from_208_titles(reviews_data, results)

        return results

    def _extract_all_reviews(self) -> List[Dict[str, Any]]:
        """
        Extract title and arxiv link from all Hebrew review markdown files.

        Returns:
            List of dicts with keys: review_num, title, link, file_path
        """
        reviews_path = self.repo_root / "mike-paper-reviews-all" / "split-hebrew-reviews-md"

        if not reviews_path.exists():
            self.log(f"Reviews path not found: {reviews_path}", level=40)
            return []

        reviews_data = []
        review_files = sorted(reviews_path.glob("Review_*.md"))

        for review_file in review_files:
            # Extract review number from filename
            match = re.search(r'Review_(\d+)\.md$', review_file.name)
            if not match:
                continue

            review_num = int(match.group(1))

            # Extract title and link from file content
            title, link = self._extract_title_and_link(review_file)

            if title:
                reviews_data.append({
                    "review_num": review_num,
                    "title": title,
                    "link": link or "",
                    "file_path": review_file
                })

        return reviews_data

    def _clean_title(self, title: str) -> str:
        """
        Clean extracted title by removing unwanted elements.

        - Remove emojis
        - Remove "[Short]" or "[short]" markers
        - Normalize whitespace

        Args:
            title: Raw extracted title

        Returns:
            Cleaned title string
        """
        # Remove [Short] or [short] markers
        title = re.sub(r'\[[Ss]hort\]\s*:?\s*', '', title)

        # Remove emojis (match emoji unicode ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        title = emoji_pattern.sub('', title)

        # Normalize whitespace
        title = re.sub(r'\s+', ' ', title).strip()

        return title

    def _extract_title_and_link(self, file_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract paper title and arxiv link from a review markdown file.

        Supports multiple formats:
        Format 1: "Review X: Title" (line 1)
        Format 2: Hebrew header, then English title (within first 10 lines)

        Args:
            file_path: Path to review markdown file

        Returns:
            Tuple of (title, arxiv_link) or (None, None) if extraction fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines()]

            title = None
            arxiv_link = None

            # Strategy 1: Check if first line has "Review X: Title" format
            if lines and lines[0]:
                first_line = lines[0]
                review_match = re.match(r'^Review\s+\d+[ab]?:\s*(.+)$', first_line, re.IGNORECASE)
                if review_match:
                    title = review_match.group(1).strip()

            # Strategy 1b: Check if first line has Hebrew date format with English title concatenated
            # Format: "סקירת המאמר היומית של מייק: DD.MM.YY סקירה XXX YYY סקירות עד 1024 Title"
            # or "המאמר היומי של מייק - DD.MM.YY:Title"
            if not title and lines and lines[0]:
                first_line = lines[0]

                # First check if there's Hebrew header followed by English title
                # Look for pattern like "סקירה XXX YYY סקירות עד 1024" followed by English
                hebrew_pattern = re.search(r'סקירות עד \d+\s+(.+)$', first_line)
                if hebrew_pattern:
                    potential_title = hebrew_pattern.group(1).strip()
                    if re.search(r'[A-Za-z]', potential_title):
                        ascii_ratio = sum(1 for c in potential_title if ord(c) < 128) / len(potential_title)
                        if ascii_ratio > 0.7:  # Stricter check
                            title = potential_title

                # Otherwise look for date followed by English title (with or without colon/space)
                if not title:
                    # Pattern 1: Date with colon/space: "DD.MM.YY: Title" or "DD.MM.YY Title"
                    date_title_match = re.search(r'\d{2}\.\d{2}\.\d{2}[:\s]+(.+)$', first_line)
                    if date_title_match:
                        potential_title = date_title_match.group(1).strip()
                        # Verify it's mostly English
                        if re.search(r'[A-Za-z]', potential_title):
                            ascii_ratio = sum(1 for c in potential_title if ord(c) < 128) / len(potential_title)
                            if ascii_ratio > 0.7:
                                title = potential_title

                    # Pattern 2: Date without separator: "DD.MM.YYTitle" (common in 376-425 range)
                    if not title:
                        date_no_sep_match = re.search(r'\d{2}\.\d{2}\.\d{2}([A-Z].+)$', first_line)
                        if date_no_sep_match:
                            potential_title = date_no_sep_match.group(1).strip()
                            if re.search(r'[A-Za-z]', potential_title):
                                ascii_ratio = sum(1 for c in potential_title if ord(c) < 128) / len(potential_title)
                                if ascii_ratio > 0.7:
                                    title = potential_title

            # Strategy 2: If no title yet, look for English title in first 15 lines
            if not title:
                for i, line in enumerate(lines[:15]):
                    if not line or len(line) < 10:
                        continue

                    # Skip lines that start with known Hebrew/metadata patterns (but not ones with mixed content)
                    if re.match(r'^(Review|Paper:|v\d+$|תחום|מושגים)', line):
                        continue

                    # If line has Hebrew header, try to extract just English part
                    if 'סקירה' in line or 'המאמר' in line or 'סקירת' in line:
                        # Pattern 1: "...סקירות עד XXX Title"
                        hebrew_match = re.search(r'סקירות עד \d+\s+(.+)$', line)
                        if hebrew_match:
                            potential_title = hebrew_match.group(1).strip()
                            if re.search(r'[A-Za-z]', potential_title):
                                ascii_ratio = sum(1 for c in potential_title if ord(c) < 128) / len(potential_title)
                                if ascii_ratio > 0.7:
                                    title = potential_title
                                    break

                        # Pattern 2: "סקירת...DD.MM.YY TITLE" - extract after date
                        date_after_hebrew = re.search(r'\d{2}\.\d{2}\.\d{2}\s+([A-Z].+)$', line)
                        if date_after_hebrew:
                            potential_title = date_after_hebrew.group(1).strip()
                            if re.search(r'[A-Za-z]', potential_title):
                                ascii_ratio = sum(1 for c in potential_title if ord(c) < 128) / len(potential_title)
                                if ascii_ratio > 0.95:  # Very strict for mixed lines
                                    title = potential_title
                                    break

                        # If no good extraction, skip this line
                        continue

                    # Check if line has significant English content
                    if re.search(r'[A-Za-z]', line):
                        ascii_count = sum(1 for c in line if ord(c) < 128)
                        ascii_ratio = ascii_count / len(line)

                        # If mostly ASCII/English, it's likely the paper title
                        if ascii_ratio > 0.7 and len(line) > 10:
                            title = line
                            break

            # Look for arxiv link (can appear anywhere in the file)
            for line in lines:
                if 'arxiv.org' in line.lower():
                    # Extract the arxiv URL
                    arxiv_match = re.search(
                        r'https?://arxiv\.org/(?:abs|pdf)/[\d.]+(?:v\d+)?',
                        line,
                        re.IGNORECASE
                    )
                    if arxiv_match:
                        arxiv_link = arxiv_match.group(0)
                        # Normalize to abs format and remove version if in URL
                        arxiv_link = arxiv_link.replace('/pdf/', '/abs/')
                        # Keep version in URL (it's informative)
                        break

            # Clean the title if found
            if title:
                title = self._clean_title(title)

            return title, arxiv_link

        except Exception as e:
            self.log(f"Error extracting from {file_path.name}: {e}", level=40)
            return None, None

    def _update_paper_with_links(
        self,
        reviews_data: List[Dict[str, Any]],
        results: Dict[str, Any]
    ) -> None:
        """Update paper_with_links.csv file."""
        csv_path = self.repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "paper_with_links.csv"

        if self.dry_run:
            self.log(f"[DRY-RUN] Would update {csv_path}")
            return

        try:
            import csv as csv_module

            csv_path.parent.mkdir(parents=True, exist_ok=True)

            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv_module.writer(f)
                writer.writerow(['review_number', 'title', 'link'])

                for review in reviews_data:
                    review_id = f"Review_{review['review_num']:03d}"
                    # Clean title: normalize whitespace, keep commas
                    title = re.sub(r'\s+', ' ', review['title']).strip()
                    link = review['link']
                    writer.writerow([review_id, title, link])

            results["files_updated"].append(str(csv_path.relative_to(self.repo_root)))
            results["changes"].append(f"Updated {csv_path.name} with {len(reviews_data)} entries")
            self.log(f"✅ Updated {csv_path.name}")

        except Exception as e:
            error_msg = f"Failed to update {csv_path.name}: {e}"
            results["errors"].append(error_msg)
            self.log(error_msg, level=40)

    def _update_all_paper_titles(
        self,
        reviews_data: List[Dict[str, Any]],
        results: Dict[str, Any]
    ) -> None:
        """Update all_paper_titles.txt file."""
        txt_path = self.repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "all_paper_titles.txt"

        if self.dry_run:
            self.log(f"[DRY-RUN] Would update {txt_path}")
            return

        try:
            lines = []

            for review in reviews_data:
                # Format: XXX. Title (clean whitespace)
                num = review['review_num']
                title = re.sub(r'\s+', ' ', review['title']).strip()
                lines.append(f"{num:03d}. {title}")

            txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

            results["files_updated"].append(str(txt_path.relative_to(self.repo_root)))
            results["changes"].append(f"Updated {txt_path.name} with {len(reviews_data)} titles")
            self.log(f"✅ Updated {txt_path.name}")

        except Exception as e:
            error_msg = f"Failed to update {txt_path.name}: {e}"
            results["errors"].append(error_msg)
            self.log(error_msg, level=40)

    def _update_clean_titles(
        self,
        reviews_data: List[Dict[str, Any]],
        results: Dict[str, Any]
    ) -> None:
        """Update clean_titles_for_search.txt file."""
        txt_path = self.repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "clean_titles_for_search.txt"

        if self.dry_run:
            self.log(f"[DRY-RUN] Would update {txt_path}")
            return

        try:
            lines = []

            for review in reviews_data:
                title = review['title']
                # Clean: lowercase, remove special chars, collapse spaces
                clean_title = title.lower()
                clean_title = re.sub(r'[^a-z0-9 ]', ' ', clean_title)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                lines.append(clean_title)

            txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

            results["files_updated"].append(str(txt_path.relative_to(self.repo_root)))
            results["changes"].append(f"Updated {txt_path.name} with {len(reviews_data)} clean titles")
            self.log(f"✅ Updated {txt_path.name}")

        except Exception as e:
            error_msg = f"Failed to update {txt_path.name}: {e}"
            results["errors"].append(error_msg)
            self.log(error_msg, level=40)

    def _update_reviews_1_207_titles(
        self,
        reviews_data: List[Dict[str, Any]],
        results: Dict[str, Any]
    ) -> None:
        """Update reviews_1_207_titles.txt file (reviews 1-207)."""
        txt_path = self.repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "reviews_1_207_titles.txt"

        if self.dry_run:
            self.log(f"[DRY-RUN] Would update {txt_path}")
            return

        try:
            # Filter reviews 1-207
            reviews_1_207 = [r for r in reviews_data if r['review_num'] <= 207]

            lines = [
                "# 📚 Paper Titles from Reviews 1-207 (Auto-generated)",
                f"# Successfully extracted: {len(reviews_1_207)} titles",
                ""
            ]

            for i, review in enumerate(reviews_1_207, start=1):
                title = re.sub(r'\s+', ' ', review['title']).strip()
                lines.append(f"{i:3d}. {title}")

            txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

            results["files_updated"].append(str(txt_path.relative_to(self.repo_root)))
            results["changes"].append(f"Updated {txt_path.name} with {len(reviews_1_207)} titles")
            self.log(f"✅ Updated {txt_path.name}")

        except Exception as e:
            error_msg = f"Failed to update {txt_path.name}: {e}"
            results["errors"].append(error_msg)
            self.log(error_msg, level=40)

    def _update_reviews_from_208_titles(
        self,
        reviews_data: List[Dict[str, Any]],
        results: Dict[str, Any]
    ) -> None:
        """Update reviews_from_208_titles.txt file (reviews 208+)."""
        txt_path = self.repo_root / "mike-paper-reviews-all" / "reviews_metadata" / "reviews_from_208_titles.txt"

        if self.dry_run:
            self.log(f"[DRY-RUN] Would update {txt_path}")
            return

        try:
            # Filter reviews 208+
            reviews_208_plus = [r for r in reviews_data if r['review_num'] >= 208]

            lines = [
                "# 📚 Paper Titles from Reviews 208+ (Auto-generated)",
                f"# Successfully extracted: {len(reviews_208_plus)} titles",
                ""
            ]

            for i, review in enumerate(reviews_208_plus, start=1):
                title = re.sub(r'\s+', ' ', review['title']).strip()
                lines.append(f"{i:3d}. {title}")

            txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

            results["files_updated"].append(str(txt_path.relative_to(self.repo_root)))
            results["changes"].append(f"Updated {txt_path.name} with {len(reviews_208_plus)} titles")
            self.log(f"✅ Updated {txt_path.name}")

        except Exception as e:
            error_msg = f"Failed to update {txt_path.name}: {e}"
            results["errors"].append(error_msg)
            self.log(error_msg, level=40)
