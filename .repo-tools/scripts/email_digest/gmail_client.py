"""Gmail API client with OAuth2, pagination, and batch fetching."""

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest

from email_digest.config import Settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_REQUEST_TIMEOUT = 60  # seconds per HTTP call; fail fast instead of hanging


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
    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=GMAIL_REQUEST_TIMEOUT))
    service = build("gmail", "v1", http=http, cache_discovery=False)

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
        list_request = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=500
        )
        result = _execute_with_retry(list_request.execute)

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


def _is_transient_error(e: Exception) -> bool:
    """Return True for errors worth retrying: rate limits, timeouts, transient network."""
    if isinstance(e, (TimeoutError, ConnectionError, OSError)):
        return True
    msg = str(e)
    return "429" in msg or "timed out" in msg.lower() or "timeout" in msg.lower()


def _execute_with_retry(call, max_retries: int = 3):
    """Execute a callable with exponential backoff on rate limits / timeouts."""
    for attempt in range(max_retries):
        try:
            return call()
        except Exception as e:
            if _is_transient_error(e) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Transient error ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _execute_batch_with_retry(batch: BatchHttpRequest, max_retries: int = 3):
    """Execute batch request with exponential backoff on rate limits / timeouts."""
    _execute_with_retry(batch.execute, max_retries=max_retries)
