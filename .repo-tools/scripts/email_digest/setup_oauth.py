#!/usr/bin/env python3
"""
One-time OAuth consent flow for Gmail API.

Usage: python3 scripts/setup_oauth.py

Prerequisites:
1. Create project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth 2.0 Desktop client credentials
4. Download credentials.json to ~/.config/email-digest/credentials.json
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    credentials_path = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "~/.config/email-digest/credentials.json")).expanduser()
    token_path = Path(os.getenv("GMAIL_TOKEN_PATH", "~/.config/email-digest/token.json")).expanduser()

    if not credentials_path.exists():
        print(f"Error: credentials.json not found at {credentials_path}")
        print("Download it from Google Cloud Console > APIs & Services > Credentials")
        return 1

    token_path.parent.mkdir(parents=True, exist_ok=True)

    print("Opening browser for Google OAuth consent...")
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json())
    token_path.chmod(0o600)

    print(f"Token saved to {token_path}")
    print("Setup complete. You can now run the email digest agent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
