#!/usr/bin/env python3
"""
Test script to verify message_id capture functionality.

This sends a test message to verify that message IDs are being captured correctly.
"""

import sys
import json
from pathlib import Path
import yaml
import requests
from datetime import datetime

# Script configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = REPO_ROOT / ".repo-tools" / "scripts" / "telegram_config.yaml"
LOG_DIR = REPO_ROOT / ".repo-tools" / "logs"
MESSAGE_IDS_FILE = LOG_DIR / "telegram_message_ids.json"

# Load config
with open(CONFIG_FILE, 'r') as f:
    config = yaml.safe_load(f)

hebrew_bot_token = config['hebrew_channel']['bot_token']
hebrew_channel_id = config['hebrew_channel']['channel_id']

# Test message
test_message = f"🧪 Test message to capture message_id\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# Send test message
url = f"https://api.telegram.org/bot{hebrew_bot_token}/sendMessage"
payload = {
    "chat_id": hebrew_channel_id,
    "text": test_message,
    "parse_mode": "HTML"
}

print("Sending test message to Hebrew channel...")
response = requests.post(url, json=payload, timeout=30)
result = response.json()

if result.get('ok'):
    message_id = result.get('result', {}).get('message_id')
    print(f"✓ Success! Message ID: {message_id}")

    # Construct link
    clean_chat_id = hebrew_channel_id.replace("-100", "")
    link = f"https://t.me/c/{clean_chat_id}/{message_id}"
    print(f"  Link: {link}")

    # Save to JSON
    if MESSAGE_IDS_FILE.exists():
        with open(MESSAGE_IDS_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    data['test'] = {
        'hebrew': {
            'message_id': message_id,
            'chat_id': hebrew_channel_id,
            'link': link,
            'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }
    }

    MESSAGE_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MESSAGE_IDS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to {MESSAGE_IDS_FILE}")

    # Read it back to verify
    print("\nVerifying saved data...")
    with open(MESSAGE_IDS_FILE, 'r') as f:
        saved_data = json.load(f)
    print(json.dumps(saved_data, indent=2))

else:
    print(f"✗ Failed: {result.get('description', 'Unknown error')}")
    sys.exit(1)
