from __future__ import annotations

import base64
import os.path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.auth.credentials import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes for Docs and Drive
DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# Scopes for Gmail
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]

# Combined scopes (for single token file)
ALL_SCOPES = DOCS_SCOPES + GMAIL_SCOPES

# For backwards compatibility
SCOPES = DOCS_SCOPES


def _config_dir() -> str:
    """Return the config directory, creating it if needed."""
    config = os.path.join(os.path.expanduser("~"), ".config", "edutools")
    os.makedirs(config, exist_ok=True)
    return config


def _get_oauth_path() -> str:
    """Resolve the OAuth client secrets file path."""
    path = os.getenv("GOOGLE_OAUTH_PATH")
    if path and os.path.exists(path):
        return path
    default = os.path.join(_config_dir(), "client_secret.json")
    if os.path.exists(default):
        return default
    raise ValueError(
        "Google OAuth client secrets not found. Either set GOOGLE_OAUTH_PATH "
        "or place client_secret.json in ~/.config/edutools/"
    )


def _get_credentials() -> Credentials:
    GOOGLE_TOKEN_PATH = os.path.join(_config_dir(), "google_token.json")
    GOOGLE_OAUTH_PATH = _get_oauth_path()

    creds: Optional[Credentials] = None
    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = OAuthCredentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    if not creds:
        raise ValueError("Failed to obtain credentials.")
    return creds


def _docs_service():
    creds = _get_credentials()
    return build("docs", "v1", credentials=creds)


def _drive_service():
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds)


def create_doc(title: str, folder_id: Optional[str] = None) -> str:
    """
    Create a Google Doc and optionally place it in a folder.

    Args:
        title: Document title
        folder_id: Optional Google Drive folder ID to place the document in

    Returns:
        The document ID
    """
    service = _docs_service()
    body = {"title": title}

    doc = service.documents().create(body=body).execute()
    doc_id = doc["documentId"]

    # Move to folder if specified
    if folder_id:
        drive = _drive_service()
        drive.files().update(
            fileId=doc_id, addParents=folder_id, fields="id, parents"
        ).execute()

    return doc_id


def insert_text(document_id: str, text: str, index: int = 1) -> None:
    """
    Insert text at a given character index.
    Index 1 is usually right after the start of the document body.
    """
    service = _docs_service()
    requests: List[Dict[str, Any]] = [
        {
            "insertText": {
                "location": {"index": index},
                "text": text,
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=document_id, body={"requests": requests}
    ).execute()


def replace_all_text(
    document_id: str, old: str, new: str, match_case: bool = True
) -> int:
    service = _docs_service()
    requests: List[Dict[str, Any]] = [
        {
            "replaceAllText": {
                "containsText": {"text": old, "matchCase": match_case},
                "replaceText": new,
            }
        }
    ]
    resp = (
        service.documents()
        .batchUpdate(documentId=document_id, body={"requests": requests})
        .execute()
    )
    # replies may be empty; replaceAllText returns an empty reply in many cases
    # so we just return 0 if we can't infer counts.
    return 0


# ============================================================================
# Gmail Functions
# ============================================================================

def _get_gmail_credentials() -> Credentials:
    """Get credentials with Gmail scope."""
    GOOGLE_OAUTH_PATH = _get_oauth_path()

    # Use a separate token file for Gmail to avoid scope conflicts
    gmail_token_path = os.path.join(_config_dir(), "google_token_gmail.json")

    creds: Optional[Credentials] = None
    if os.path.exists(gmail_token_path):
        creds = OAuthCredentials.from_authorized_user_file(gmail_token_path, GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

        with open(gmail_token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    if not creds:
        raise ValueError("Failed to obtain Gmail credentials.")
    return creds


def _gmail_service():
    """Get Gmail API service."""
    creds = _get_gmail_credentials()
    return build("gmail", "v1", credentials=creds)


def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    sender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an email using Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject
        body_text: Plain text body
        body_html: Optional HTML body
        sender: Optional sender address (defaults to authenticated user)

    Returns:
        Gmail API response dict with message id
    """
    service = _gmail_service()

    if body_html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))
    else:
        message = MIMEText(body_text, "plain")

    message["to"] = to
    message["subject"] = subject
    if sender:
        message["from"] = sender

    # Encode the message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()
        return {"success": True, "message_id": result.get("id"), "error": None}
    except Exception as e:
        return {"success": False, "message_id": None, "error": str(e)}
