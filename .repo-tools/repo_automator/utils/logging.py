"""
Timestamped logging with emoji indicators.
Follows the style from docx_splitter.py for consistency.
"""

import logging
import sys
from datetime import datetime


class EmojiFormatter(logging.Formatter):
    """Custom formatter with emoji level indicators."""

    EMOJI_MAP = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️ ",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨"
    }

    SUCCESS_EMOJI = "✅"
    SCAN_EMOJI = "📊"
    UPDATE_EMOJI = "🔄"
    WATCH_EMOJI = "👀"

    def format(self, record):
        # Use custom emoji if provided, otherwise use level-based emoji
        if hasattr(record, 'emoji') and record.emoji:
            emoji = record.emoji
        else:
            emoji = self.EMOJI_MAP.get(record.levelno, "")

        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        return f"{timestamp} {emoji} {record.getMessage()}"


def setup_logging(level=logging.INFO, use_emoji=True):
    """
    Configure logging with timestamps and optional emoji.

    Args:
        level: Logging level (default: INFO)
        use_emoji: Whether to use emoji indicators (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("repo_automator")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if use_emoji:
        formatter = EmojiFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_logger():
    """Get the repo_automator logger instance."""
    return logging.getLogger("repo_automator")


def log_success(message: str):
    """Log a success message with checkmark emoji."""
    logger = get_logger()
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.emoji = "✅"
    logger.handle(record)


def log_scan(message: str):
    """Log a scan message with chart emoji."""
    logger = get_logger()
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.emoji = "📊"
    logger.handle(record)


def log_update(message: str):
    """Log an update message with refresh emoji."""
    logger = get_logger()
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.emoji = "🔄"
    logger.handle(record)
