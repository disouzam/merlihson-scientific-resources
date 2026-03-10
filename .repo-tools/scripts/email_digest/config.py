"""Settings loaded from config.yaml (or environment variables as fallback)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"


@dataclass
class Settings:
    gmail_credentials_path: Path
    gmail_token_path: Path
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    claude_model: str = "claude-sonnet-4-20250514"
    max_emails_per_batch: int = 50
    log_file: Path = field(default_factory=lambda: Path.home() / ".config" / "email-digest" / "email_digest.log")

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> "Settings":
        config_path = config_path or CONFIG_FILE
        cfg = {}
        if config_path.exists():
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}

        def get(key: str, env_key: str, default: str | None = None) -> str | None:
            return cfg.get(key) or os.getenv(env_key) or default

        required = {
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
            "telegram_chat_id": "TELEGRAM_CHAT_ID",
        }
        missing = [env for key, env in required.items() if not get(key, env)]
        if missing:
            raise ValueError(f"Missing required config/env: {', '.join(missing)}")

        return cls(
            gmail_credentials_path=Path(get("gmail_credentials_path", "GMAIL_CREDENTIALS_PATH", "~/.config/email-digest/credentials.json")).expanduser(),
            gmail_token_path=Path(get("gmail_token_path", "GMAIL_TOKEN_PATH", "~/.config/email-digest/token.json")).expanduser(),
            anthropic_api_key=get("anthropic_api_key", "ANTHROPIC_API_KEY"),
            telegram_bot_token=get("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=get("telegram_chat_id", "TELEGRAM_CHAT_ID"),
            claude_model=get("claude_model", "CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            max_emails_per_batch=int(get("max_emails_per_batch", "MAX_EMAILS_PER_BATCH", "50")),
            log_file=Path(get("log_file", "LOG_FILE", "~/.config/email-digest/email_digest.log")).expanduser(),
        )

    # Keep backward compat alias
    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "Settings":
        return cls.from_yaml()
