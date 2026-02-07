#!/usr/bin/env python3
"""
Substack Post Scraper

Scrapes user's Substack to find the latest review post link.

How it works:
1. Fetches Substack homepage HTML
2. Parses post links using BeautifulSoup
3. Searches for posts matching "Review XXX" pattern
4. Returns URL of most recent matching post

Run manually:
  python3 substack_scraper.py --url https://yourname.substack.com --test-connection
  python3 substack_scraper.py --url https://yourname.substack.com --find-latest
  python3 substack_scraper.py --review 574

Scheduled: Called by discord_poster.py at 12:00 PM
"""

import sys
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yaml

# Script configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
CONFIG_DIR = REPO_ROOT / ".repo-tools" / "config"
CONFIG_FILE = CONFIG_DIR / "discord_config.yaml"

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "substack_scraper.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SubstackConfig:
    """Configuration holder for Substack settings."""

    def __init__(self, config_path: Path):
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create it with your Substack URL."
            )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.base_url = config.get('substack', {}).get('base_url')

        if not self.base_url:
            raise ValueError("Please configure 'substack.base_url' in discord_config.yaml")

        # Remove trailing slash
        self.base_url = self.base_url.rstrip('/')


def extract_review_number(text: str) -> Optional[int]:
    """
    Extract review number from text.

    Handles formats:
    - "Review 574: Title"
    - "Review_574"
    - "review-574-title"
    - "סקירה 574" (Hebrew)
    """
    patterns = [
        r'Review[_\s-](\d+)',     # Review 574, Review_574, Review-574
        r'review-(\d+)',           # review-574
        r'סקירה[_\s-]?(\d+)',     # Hebrew
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def fetch_substack_posts_api(base_url: str, limit: int = 20) -> Optional[List[Dict]]:
    """
    Fetch recent posts from Substack API.

    Args:
        base_url: Base Substack URL (e.g., "https://yourname.substack.com")
        limit: Number of posts to fetch (default: 20)

    Returns:
        List of post dicts or None if failed
    """
    try:
        api_url = f"{base_url}/api/v1/archive?sort=new&limit={limit}"
        logger.info(f"Fetching Substack posts via API: {api_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()

        posts = response.json()
        logger.info(f"✓ Fetched {len(posts)} posts from API")
        return posts

    except Exception as e:
        logger.error(f"Error fetching Substack API: {e}")
        return None


def fetch_substack_homepage(base_url: str) -> Optional[str]:
    """
    Fetch Substack homepage HTML (fallback method).

    Args:
        base_url: Base Substack URL (e.g., "https://yourname.substack.com")

    Returns:
        HTML content or None if failed
    """
    try:
        logger.info(f"Fetching Substack homepage: {base_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()

        logger.info(f"✓ Fetched {len(response.text)} bytes")
        return response.text

    except Exception as e:
        logger.error(f"Error fetching Substack: {e}")
        return None


def parse_substack_posts(html: str) -> List[Dict]:
    """
    Parse Substack HTML to extract post information.

    Args:
        html: Substack homepage HTML

    Returns:
        List of dicts with 'title', 'url', 'review_num' keys
    """
    soup = BeautifulSoup(html, 'html.parser')
    posts = []

    # Substack HTML structure (typical):
    # <div class="post-preview">
    #   <a href="/p/review-574-paper-title">
    #     <h3>Review 574: Paper Title</h3>
    #   </a>
    # </div>

    # Try multiple selectors for robustness
    selectors = [
        'a.post-preview-title',           # Modern Substack
        'a[class*="post"]',                # Flexible class matching
        'article a[href*="/p/"]',          # Article links
        'div[class*="post"] a[href*="/p/"]',  # Post div links
    ]

    for selector in selectors:
        links = soup.select(selector)
        if links:
            logger.debug(f"Found {len(links)} links with selector: {selector}")
            break
    else:
        # Fallback: find all links containing "/p/"
        links = soup.find_all('a', href=re.compile(r'/p/'))
        logger.debug(f"Fallback: Found {len(links)} /p/ links")

    for link in links:
        href = link.get('href', '')
        title = link.get_text(strip=True)

        # Construct full URL if relative
        if href.startswith('/'):
            # Will be completed by caller
            pass
        elif not href.startswith('http'):
            continue

        # Extract review number
        review_num = extract_review_number(title) or extract_review_number(href)

        if review_num:
            posts.append({
                'title': title,
                'url': href,
                'review_num': review_num
            })
            logger.debug(f"Found: Review_{review_num} - {title[:50]}...")

    logger.info(f"Parsed {len(posts)} review posts")
    return posts


def get_latest_review_post(base_url: str, review_num: Optional[int] = None) -> Optional[str]:
    """
    Get the latest review post URL from Substack.

    Args:
        base_url: Substack base URL
        review_num: Specific review number to find (optional)

    Returns:
        Full post URL or None if not found
    """
    # Try API first (much more reliable)
    posts_data = fetch_substack_posts_api(base_url, limit=30)

    if posts_data:
        # Parse API response
        review_posts = []

        for post in posts_data:
            # Check title and subtitle for review number
            title = post.get('title', '')
            subtitle = post.get('subtitle', '') or post.get('description', '')
            combined_text = f"{title} {subtitle}"

            # Extract review number
            post_review_num = extract_review_number(combined_text)

            if post_review_num:
                review_posts.append({
                    'review_num': post_review_num,
                    'url': post.get('canonical_url'),
                    'title': title
                })
                logger.debug(f"Found Review_{post_review_num}: {title[:50]}...")

        if not review_posts:
            logger.warning("No review posts found in Substack API response")
            return None

        # Filter by review number if specified
        if review_num:
            matching = [p for p in review_posts if p['review_num'] == review_num]
            if not matching:
                logger.warning(f"Review_{review_num} not found on Substack")
                return None
            post = matching[0]
        else:
            # Get the latest (highest number)
            post = max(review_posts, key=lambda p: p['review_num'])

        url = post['url']
        logger.info(f"✓ Found Review_{post['review_num']}: {url}")
        return url

    else:
        # Fallback to HTML parsing
        logger.info("API fetch failed, trying HTML parsing...")

        html = fetch_substack_homepage(base_url)
        if not html:
            return None

        posts = parse_substack_posts(html)
        if not posts:
            logger.warning("No review posts found on Substack homepage")
            return None

        # Filter by review number if specified
        if review_num:
            matching = [p for p in posts if p['review_num'] == review_num]
            if not matching:
                logger.warning(f"Review_{review_num} not found on Substack")
                return None
            post = matching[0]
        else:
            # Get the latest (highest number)
            post = max(posts, key=lambda p: p['review_num'])

        # Construct full URL
        url = post['url']
        if url.startswith('/'):
            url = base_url + url

        logger.info(f"✓ Found Review_{post['review_num']}: {url}")
        return url


def test_connection(base_url: str) -> bool:
    """
    Test Substack connection via API.

    Args:
        base_url: Substack base URL

    Returns:
        True if successful
    """
    print(f"Testing connection to: {base_url}")
    print()

    # Test API
    posts_data = fetch_substack_posts_api(base_url, limit=20)
    if not posts_data:
        print("✗ Failed to fetch from Substack API")
        return False

    print("✓ Successfully fetched from Substack API")
    print()

    # Parse for review posts
    review_posts = []
    for post in posts_data:
        title = post.get('title', '')
        subtitle = post.get('subtitle', '') or post.get('description', '')
        combined_text = f"{title} {subtitle}"

        post_review_num = extract_review_number(combined_text)
        if post_review_num:
            review_posts.append({
                'review_num': post_review_num,
                'title': title,
                'url': post.get('canonical_url')
            })

    if not review_posts:
        print("⚠️  No review posts found in recent posts.")
        print()
        print(f"DEBUG: Found {len(posts_data)} total posts")
        if posts_data:
            print("Sample titles:")
            for post in posts_data[:3]:
                print(f"  - {post.get('title', 'No title')}")
        print()
        return False

    print(f"✓ Found {len(review_posts)} review posts:")
    print()
    for post in sorted(review_posts, key=lambda p: p['review_num'], reverse=True)[:10]:
        print(f"  Review_{post['review_num']:03d}: {post['title'][:70]}")
        print(f"    {post['url']}")
        print()

    return True


def main():
    """Main entry point for Substack scraper."""

    # Parse arguments
    test_mode = '--test-connection' in sys.argv
    find_latest = '--find-latest' in sys.argv
    review_num = None
    base_url = None

    # Get custom URL if specified
    if '--url' in sys.argv:
        try:
            idx = sys.argv.index('--url')
            base_url = sys.argv[idx + 1]
        except IndexError:
            print("Error: --url requires a URL argument")
            return 1

    # Get specific review number
    if '--review' in sys.argv:
        try:
            idx = sys.argv.index('--review')
            review_num = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Error: --review requires a review number")
            return 1

    # Load config if URL not provided
    if not base_url:
        try:
            config = SubstackConfig(CONFIG_FILE)
            base_url = config.base_url
            logger.info(f"Loaded Substack URL from config: {base_url}")
        except Exception as e:
            print(f"Error loading config: {e}")
            print()
            print("Usage:")
            print("  python3 substack_scraper.py --url https://yourname.substack.com --test-connection")
            print("  python3 substack_scraper.py --url https://yourname.substack.com --find-latest")
            print("  python3 substack_scraper.py --review 574")
            return 1

    # Test connection mode
    if test_mode:
        return 0 if test_connection(base_url) else 1

    # Find latest or specific review
    logger.info("=" * 60)
    logger.info("Substack Post Scraper")
    logger.info("=" * 60)

    if review_num:
        logger.info(f"Searching for Review_{review_num}...")
    else:
        logger.info("Finding latest review post...")

    url = get_latest_review_post(base_url, review_num)

    if url:
        print()
        print("=" * 60)
        print("Result:")
        print("=" * 60)
        print(url)
        print()
        return 0
    else:
        print()
        print("✗ No review post found")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
