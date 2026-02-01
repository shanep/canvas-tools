from __future__ import annotations

import os.path
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.auth.credentials import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes:
# - documents: lets you read/write Docs content
# - drive.file (optional): lets you view/manage files created/opened by your app
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_credentials() -> Credentials:
    load_dotenv()
    GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH")
    GOOGLE_OAUTH_PATH = os.getenv("GOOGLE_OAUTH_PATH")
    if not GOOGLE_TOKEN_PATH or not GOOGLE_OAUTH_PATH:
        raise ValueError(
            "GOOGLE_TOKEN_PATH and GOOGLE_OAUTH_PATH must be set in environment variables."
        )

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
