#!/usr/bin/env python3
"""Cut a segment from a YouTube video using yt-dlp and ffmpeg.

Usage:
    python3 .repo-tools/scripts/youtube_clip_cutter.py \
        --url "https://www.youtube.com/watch?v=..." \
        --start "27:55" --end "38:58"

    python3 .repo-tools/scripts/youtube_clip_cutter.py \
        --url "https://youtu.be/..." \
        --start "1:05:30" --end "1:15:00" \
        --output ~/Desktop/

    # Cut and upload to Telegram:
    python3 .repo-tools/scripts/youtube_clip_cutter.py \
        --url "https://youtube.com/watch?v=..." \
        --start "27:55" --end "38:58" \
        --upload --message "🔥 הקטע שכולם מדברים עליו..."
"""

import argparse
import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
CONFIG_FILE = REPO_ROOT / ".repo-tools" / "scripts" / "telegram_config.yaml"
DEFAULT_OUTPUT = Path.home() / "Downloads"
TELEGRAM_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "youtube_clip_cutter.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# YouTube URL pattern
YOUTUBE_URL_RE = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/live/)[\w\-]+'
)


def check_dependencies() -> bool:
    """Verify yt-dlp and ffmpeg are installed."""
    missing = []
    for tool in ('yt-dlp', 'ffmpeg'):
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Install with: brew install " + " ".join(missing))
        return False
    return True


def parse_time(time_str: str) -> int:
    """Parse MM:SS or HH:MM:SS to total seconds."""
    parts = time_str.strip().split(':')
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    else:
        raise ValueError(f"Invalid time format: '{time_str}'. Use MM:SS or HH:MM:SS")


def format_time(seconds: int) -> str:
    """Format seconds as HH:MM:SS for yt-dlp."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_time_filename(seconds: int) -> str:
    """Format seconds as MM.SS or HH.MM.SS for filenames."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}.{m:02d}.{s:02d}"
    return f"{m}.{s:02d}"


def get_video_duration(url: str) -> int:
    """Fetch video duration in seconds via yt-dlp."""
    logger.info("Fetching video duration...")
    result = subprocess.run(
        ['yt-dlp', '--get-duration', '--no-warnings', url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch video duration: {result.stderr.strip()}")

    duration_str = result.stdout.strip()
    # yt-dlp returns duration as H:MM:SS or MM:SS or SS
    return parse_time(duration_str)


def get_video_title(url: str) -> str:
    """Fetch video title via yt-dlp."""
    result = subprocess.run(
        ['yt-dlp', '--get-title', '--no-warnings', url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch video title: {result.stderr.strip()}")
    title = result.stdout.strip()
    # Sanitize for filename
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    title = title.strip('. ')
    # Truncate long titles
    if len(title) > 80:
        title = title[:80].rstrip()
    return title


def download_clip(url: str, start_sec: int, end_sec: int, output_dir: Path) -> Path:
    """Download the clip segment using yt-dlp --download-sections."""
    title = get_video_title(url)
    start_fmt = format_time_filename(start_sec)
    end_fmt = format_time_filename(end_sec)
    filename = f"{title}_{start_fmt}-{end_fmt}.mp4"
    output_path = output_dir / filename

    start_ts = format_time(start_sec)
    end_ts = format_time(end_sec)
    section_arg = f"*{start_ts}-{end_ts}"

    logger.info(f"Downloading clip: {start_ts} → {end_ts}")
    logger.info(f"Output: {output_path}")

    cmd = [
        'yt-dlp',
        '--download-sections', section_arg,
        '--force-keyframes-at-cuts',
        '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
        '--merge-output-format', 'mp4',
        '-o', str(output_path),
        '--no-warnings',
        '--progress',
        url
    ]

    result = subprocess.run(cmd, timeout=600)
    if result.returncode != 0:
        # Retry with browser cookies (helps with 403 errors)
        logger.info("Retrying with browser cookies...")
        cmd_retry = cmd.copy()
        cmd_retry.insert(1, '--cookies-from-browser')
        cmd_retry.insert(2, 'chrome')
        result = subprocess.run(cmd_retry, timeout=600)
        if result.returncode != 0:
            raise RuntimeError("yt-dlp download failed. Check the URL and try again.")

    if not output_path.exists():
        # yt-dlp may append format info; find the actual file
        candidates = list(output_dir.glob(f"{title}_{start_fmt}-{end_fmt}*"))
        if candidates:
            output_path = candidates[0]
        else:
            raise RuntimeError(f"Download completed but output file not found at {output_path}")

    return output_path


def load_telegram_config() -> dict:
    """Load bot token and channel ID for Hebrew channel from telegram_config.yaml."""
    import yaml

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_FILE}\n"
            f"Please create it from telegram_config.yaml.template"
        )

    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    heb = config['hebrew_channel']
    if 'YOUR_' in heb['bot_token']:
        raise ValueError("Please configure your bot token in telegram_config.yaml")

    return {
        'bot_token': heb['bot_token'],
        'channel_id': heb['channel_id'],
    }


def send_telegram_text(caption: str, bot_token: str, channel_id: str) -> bool:
    """Send a text message to Telegram channel. Returns True on success."""
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for attempt in range(3):
        try:
            logger.info(f"Sending text message to Telegram (attempt {attempt + 1}/3)...")
            response = requests.post(
                url,
                json={'chat_id': channel_id, 'text': caption},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.info("✓ Text message sent to Telegram successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Send error: {e}")

        if attempt < 2:
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)

    return False


def upload_to_telegram(video_path: Path, caption: str, bot_token: str, channel_id: str) -> bool:
    """Upload video to Telegram channel. If file > 50 MB, sends caption as text instead. Returns True on success."""
    import requests

    file_size = video_path.stat().st_size
    if file_size > TELEGRAM_MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        logger.info(
            f"File too large for video upload ({size_mb:.1f} MB > 50 MB limit). "
            f"Sending caption as text message instead — upload the video manually."
        )
        return send_telegram_text(caption, bot_token, channel_id)

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    for attempt in range(3):
        try:
            logger.info(f"Uploading to Telegram (attempt {attempt + 1}/3)...")
            with open(video_path, 'rb') as video_file:
                response = requests.post(
                    url,
                    data={'chat_id': channel_id, 'caption': caption},
                    files={'video': video_file},
                    timeout=300,
                )
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.info("✓ Video uploaded to Telegram successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Upload error: {e}")

        if attempt < 2:
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)

    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Cut a segment from a YouTube video.',
        epilog='Examples:\n'
               '  %(prog)s --url "https://youtube.com/watch?v=abc" --start 27:55 --end 38:58\n'
               '  %(prog)s --url "https://youtu.be/abc" --start 1:05:30 --end 1:15:00 --output ~/Desktop/',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--url', required=True, help='YouTube video URL')
    parser.add_argument('--start', required=True, help='Start time (MM:SS or HH:MM:SS)')
    parser.add_argument('--end', required=True, help='End time (MM:SS or HH:MM:SS)')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT),
                        help=f'Output directory (default: {DEFAULT_OUTPUT})')
    parser.add_argument('--upload', action='store_true',
                        help='Upload the clip to the test Hebrew Telegram channel')
    parser.add_argument('--message', type=str, default=None,
                        help='Caption for Telegram upload (required with --upload)')

    args = parser.parse_args()

    # Validate upload flags
    if args.upload and not args.message:
        parser.error("--message is required when using --upload")

    # Check dependencies
    if not check_dependencies():
        return 1

    # Validate URL
    if not YOUTUBE_URL_RE.search(args.url):
        logger.error(f"Invalid YouTube URL: {args.url}")
        return 1

    # Parse times
    try:
        start_sec = parse_time(args.start)
    except ValueError as e:
        logger.error(f"Invalid start time: {e}")
        return 1

    try:
        end_sec = parse_time(args.end)
    except ValueError as e:
        logger.error(f"Invalid end time: {e}")
        return 1

    if start_sec >= end_sec:
        logger.error(f"Start time ({args.start}) must be before end time ({args.end})")
        return 1

    # Validate output directory
    output_dir = Path(args.output).expanduser()
    if not output_dir.is_dir():
        logger.error(f"Output directory does not exist: {output_dir}")
        return 1

    # Check duration
    try:
        duration = get_video_duration(args.url)
        logger.info(f"Video duration: {format_time(duration)}")
        if end_sec > duration:
            logger.error(
                f"End time ({args.end} = {end_sec}s) exceeds video duration "
                f"({format_time(duration)} = {duration}s)"
            )
            return 1
    except Exception as e:
        logger.warning(f"Could not verify video duration: {e}")
        logger.info("Proceeding anyway — yt-dlp will handle out-of-range timestamps")

    # Download
    try:
        output_path = download_clip(args.url, start_sec, end_sec, output_dir)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Clip saved: {output_path} ({size_mb:.1f} MB)")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return 1

    # Upload to Telegram if requested
    if args.upload:
        try:
            tg_config = load_telegram_config()
            success = upload_to_telegram(
                output_path, args.message,
                tg_config['bot_token'], tg_config['channel_id']
            )
            if not success:
                logger.error("Telegram upload failed")
                return 1
        except Exception as e:
            logger.error(f"Telegram upload error: {e}")
            return 1

    return 0


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
