import os
import base64
import re
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_message_body(service, msg_id: str) -> str:
    """Extract plain text body from a Gmail message."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    payload = msg.get("payload", {})
    return _extract_text(payload)


def _extract_text(payload: dict) -> str:
    """Recursively extract plain text from message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    if mime_type.startswith("multipart"):
        for part in payload.get("parts", []):
            text = _extract_text(part)
            if text:
                return text

    return ""


def fetch_meeting_transcripts(max_results: int = 10) -> list[dict]:
    """
    Fetch Google Meet transcript emails from Gmail.
    Returns list of dicts with subject, date, and body.
    """
    service = get_gmail_service()

    # Search for Google Meet transcript emails
    query = 'subject:"Notes from" "Suggested next steps"'
    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    transcripts = []

    for msg_ref in messages:
        msg_id = msg_ref["id"]

        # Get headers for subject and date
        msg_meta = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["Subject", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg_meta.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "")
        date = headers.get("Date", "")

        # Only process Google Meet transcript emails
        if "Notes from" not in subject:
            continue

        body = get_message_body(service, msg_id)
        if not body.strip():
            continue

        transcripts.append({
            "id": msg_id,
            "subject": subject,
            "date": date,
            "body": body,
        })

    return transcripts


def is_authenticated() -> bool:
    """Check if Gmail is already authenticated."""
    if not Path(TOKEN_FILE).exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds and creds.valid
    except Exception:
        return False


if __name__ == "__main__":
    print("Authenticating with Gmail...")
    transcripts = fetch_meeting_transcripts(max_results=5)
    print(f"Found {len(transcripts)} meeting transcripts")
    for t in transcripts:
        print(f"  - {t['subject']} ({t['date'][:16]})")