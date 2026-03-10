"""Gmail API client with OAuth2, pagination, and batch fetching."""

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest

from email_digest.config import Settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate(settings: Settings) -> Credentials:
    """Load and refresh OAuth2 credentials."""
    token_path = settings.gmail_token_path

    if not token_path.exists():
        raise FileNotFoundError(
            f"Token not found at {token_path}. Run scripts/setup_oauth.py first."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds.expired and creds.refresh_token:
        logger.info("Refreshing expired OAuth token...")
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            token_path.chmod(0o600)
            logger.info("Token refreshed successfully")
        except Exception as e:
            raise RuntimeError(
                f"Failed to refresh OAuth token: {e}. Run scripts/setup_oauth.py to re-authenticate."
            )

    return creds


def fetch_emails(
    settings: Settings, target_date: date | None = None
) -> list[dict]:
    """
    Fetch all emails from target_date (defaults to yesterday).

    Returns list of raw Gmail API message dicts with full payload.
    """
    creds = authenticate(settings)
    service = build("gmail", "v1", credentials=creds)

    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    next_date = target_date + timedelta(days=1)
    query = (
        f"after:{target_date.strftime('%Y/%m/%d')} "
        f"before:{next_date.strftime('%Y/%m/%d')} "
        f"-in:spam -in:trash -category:promotions -category:social"
    )

    logger.info(f"Fetching emails with query: {query}")

    # Paginate to get all message IDs
    message_ids = []
    page_token = None

    while True:
        result = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=500
        ).execute()

        messages = result.get("messages", [])
        message_ids.extend(msg["id"] for msg in messages)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Found {len(message_ids)} message IDs")

    if not message_ids:
        return []

    # Batch-fetch full messages (10 at a time to avoid concurrent request limits)
    all_messages = []
    batch_size = min(settings.max_emails_per_batch, 10)

    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i : i + batch_size]
        batch_messages = []

        def callback(request_id, response, exception):
            if exception:
                logger.warning(f"Error fetching message {request_id}: {exception}")
            else:
                batch_messages.append(response)

        batch = service.new_batch_http_request(callback=callback)
        for msg_id in batch_ids:
            batch.add(
                service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                )
            )

        _execute_batch_with_retry(batch)
        all_messages.extend(batch_messages)

        if i + batch_size < len(message_ids):
            time.sleep(0.1)

    logger.info(f"Fetched {len(all_messages)} full messages")
    return all_messages


def _execute_batch_with_retry(batch: BatchHttpRequest, max_retries: int = 3):
    """Execute batch request with exponential backoff on 429."""
    for attempt in range(max_retries):
        try:
            batch.execute()
            return
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
