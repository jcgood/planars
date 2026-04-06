"""Google Drive and Sheets client helpers shared across coding/ modules.

All OAuth2 authentication, Drive config I/O, manifest upload/download, and
rate-limit retry logic lives here so that individual command modules stay
focused on their own logic.

Authentication (OAuth2):
    Credentials JSON at PLANARS_OAUTH_CREDENTIALS env var, or
    ~/.config/planars/oauth_credentials.json by default.
    Token cached at ~/.config/gspread/authorized_user.json after first run.
"""
from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, TypeVar

import gspread
from googleapiclient.discovery import build as google_build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

ROOT = Path(__file__).resolve().parent.parent
DRIVE_CONFIG_PATH = ROOT / "drive_config.json"
_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"

_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# Rate-limit retry helper
# ---------------------------------------------------------------------------

def _with_retry(fn: Callable[[], _T], retries: int = 5) -> _T:
    """Call fn() with exponential backoff on retryable API errors (429, 503)."""
    for attempt in range(retries):
        try:
            return fn()
        except gspread.exceptions.APIError as e:
            if e.response.status_code in (429, 503) and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    (API error {e.response.status_code} — waiting {wait}s before retry {attempt + 2}/{retries})")
                time.sleep(wait)
            else:
                raise
    return fn()  # final attempt — let it raise


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_clients():
    """Return (gspread.Client, drive_service) using OAuth2 user credentials."""
    creds_path = Path(
        os.environ.get("PLANARS_OAUTH_CREDENTIALS", str(_DEFAULT_OAUTH_PATH))
    )
    if not creds_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {creds_path}\n"
            "Download an OAuth2 Desktop App credential from Google Cloud Console\n"
            "and save it to that path (or set PLANARS_OAUTH_CREDENTIALS)."
        )
    gc = gspread.oauth(
        credentials_filename=str(creds_path),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/documents",
        ],
    )
    # Reuse the refreshed credentials from gspread for the Drive API client
    drive = google_build("drive", "v3", credentials=gc.http_client.auth)
    return gc, drive


def _get_docs_client(gc):
    """Build a Google Docs API client from existing gspread credentials."""
    return google_build("docs", "v1", credentials=gc.http_client.auth)


# ---------------------------------------------------------------------------
# Drive config (local bootstrap)
# ---------------------------------------------------------------------------

def _load_drive_config() -> Dict:
    """Load drive_config.json if it exists, otherwise return empty dict."""
    if DRIVE_CONFIG_PATH.exists():
        return json.loads(DRIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _save_drive_config(config: Dict) -> None:
    """Write drive_config.json with updated folder/file IDs."""
    DRIVE_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Drive manifest upload/download
# ---------------------------------------------------------------------------

def _download_file_json(drive, file_id: str) -> Dict:
    """Download and parse a JSON file from Drive by file ID."""
    request = drive.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return json.loads(buffer.getvalue().decode("utf-8"))



def _upload_planars_config(
    drive, full_config: Dict, root_folder_id: str, existing_file_id: str = None
) -> str:
    """Upload the merged manifest.json to Drive. Returns the file ID.

    The merged config has the structure::

        {lang_id: {folder_id, folder_url, sheets: {...}, ...}, ...}

    This replaces the old per-language ``manifest_{lang_id}.json`` files with a
    single file that notebooks and all sheet scripts read.

    Args:
        drive: Drive API service.
        full_config: complete merged config dict covering all languages.
        root_folder_id: Drive folder for first-time file creation.
        existing_file_id: ID of an existing manifest.json to update in place.

    Returns:
        The Drive file ID of manifest.json.
    """
    # Reorder each language entry so human-readable metadata comes first.
    _KEY_ORDER = [
        "glottolog", "meta",
        "folder_id", "folder_url",
        "notes_doc_id",
        "planar_spreadsheet_id", "planar_spreadsheet_url",
        "diagnostics_spreadsheet_id", "diagnostics_spreadsheet_url",
        "sheets",
    ]
    ordered = {}
    for lid, entry in full_config.items():
        if isinstance(entry, dict):
            ordered[lid] = {k: entry[k] for k in _KEY_ORDER if k in entry}
            ordered[lid].update({k: v for k, v in entry.items() if k not in _KEY_ORDER})
        else:
            ordered[lid] = entry
    content = json.dumps(ordered, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
    if existing_file_id:
        try:
            drive.files().update(fileId=existing_file_id, media_body=media).execute()
            return existing_file_id
        except Exception as e:
            print(f"  WARNING: could not update existing manifest.json ({e}); creating new file.")
    result = drive.files().create(
        body={"name": "manifest.json", "parents": [root_folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return result["id"]


def _load_manifest_from_drive(drive) -> Dict:
    """Load the full manifest (all languages) from Drive.

    Tries the new merged manifest.json first. Falls back to reading the
    old per-language ``manifest_{lang_id}.json`` files if the merged format is
    not yet in place (migration path for setups predating issue #30).

    Returns:
        Dict mapping lang_id to lang_data, where lang_data contains at minimum
        ``folder_id``, ``folder_url``, and ``sheets``.
    """
    config = _load_drive_config()
    if not config:
        raise SystemExit(
            "drive_config.json not found. Run: python -m coding generate-sheets"
        )

    # New merged format: single manifest.json with full manifest data.
    file_id = config.get("_planars_config_file_id")
    if file_id:
        try:
            full_config = _download_file_json(drive, file_id)
            # Distinguish new format (has 'sheets' per language) from old (just folder_id).
            if any("sheets" in v for v in full_config.values() if isinstance(v, dict)):
                return full_config
        except Exception as exc:
            print(f"  Warning: could not load merged config ({exc}), falling back.")

    # Old format fallback: per-language manifest_{lang_id}.json files.
    print("  Note: loading per-language manifests (pre-#30 format).")
    print("  Run python -m coding generate-sheets to upgrade to merged manifest.json.")
    manifest: Dict = {}
    for lang_id, lang_config in config.items():
        if lang_id.startswith("_") or not isinstance(lang_config, dict):
            continue
        mfid = lang_config.get("manifest_file_id")
        if not mfid:
            continue
        lang_data = _download_file_json(drive, mfid)
        lang_data.setdefault("folder_id", lang_config.get("folder_id", ""))
        manifest[lang_id] = lang_data
    if not manifest:
        raise SystemExit(
            "No manifest data found in drive_config.json. "
            "Run python -m coding generate-sheets first."
        )
    return manifest


# ---------------------------------------------------------------------------
# Spreadsheet helper
# ---------------------------------------------------------------------------

def _open_spreadsheet(gc: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    """Open a spreadsheet by ID, retrying on 429 quota errors with backoff."""
    return _with_retry(lambda: gc.open_by_key(spreadsheet_id))


# ---------------------------------------------------------------------------
# Drive folder / permission helpers
# ---------------------------------------------------------------------------

def _get_or_create_folder(drive, name: str, parent_id: str = None) -> str:
    """Return the ID of a Drive folder with the given name, creating it if needed.

    If parent_id is given, searches within that parent and creates inside it.
    If parent_id is None, searches all of Drive (top-level My Drive behaviour).
    """
    parent_clause = f" and '{parent_id}' in parents" if parent_id else ""
    results = drive.files().list(
        q=(
            f"name='{name}'"
            " and mimeType='application/vnd.google-apps.folder'"
            " and trashed=false"
            f"{parent_clause}"
        ),
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    body: dict = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    folder = drive.files().create(body=body, fields="id").execute()
    return folder["id"]


def _share_anyone_with_link(drive, file_id: str) -> None:
    """Share a file or folder with anyone who has the link as editor."""
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "writer"},
        fields="id",
    ).execute()


def _move_to_folder(drive, file_id: str, folder_id: str) -> None:
    """Move a Drive file into a folder."""
    file = drive.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents", []))
    drive.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


# ---------------------------------------------------------------------------
# Google Docs helpers (collaborator notes)
# ---------------------------------------------------------------------------

_ACK_PREFIX = "Notes transferred to coordinator"


def _create_notes_doc(drive, lang_id: str, folder_id: str, display_name: str = "") -> str:
    """Create a Google Doc for collaborator notes in the language folder.

    The doc is named "{display_name} — Annotation Notes" (e.g. "Araona [arao1248]
    — Annotation Notes"), falling back to "notes_{lang_id}" if display_name is
    not provided.

    Returns the new document's file ID.
    """
    doc_name = f"{display_name} — Annotation Notes" if display_name else f"notes_{lang_id}"
    result = drive.files().create(
        body={
            "name": doc_name,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [folder_id],
        },
        fields="id",
    ).execute()
    doc_id = result["id"]
    _share_anyone_with_link(drive, doc_id)
    return doc_id


def _read_notes_doc_text(docs, doc_id: str) -> str:
    """Return the full plain-text content of a Google Doc."""
    doc = docs.documents().get(documentId=doc_id).execute()
    parts: list[str] = []
    for block in doc.get("body", {}).get("content", []):
        if "paragraph" in block:
            for element in block["paragraph"].get("elements", []):
                if "textRun" in element:
                    parts.append(element["textRun"]["content"])
    return "".join(parts)


def _strip_acknowledgment_lines(text: str) -> str:
    """Strip system-written acknowledgment lines before hashing.

    Removes lines containing our transfer marker so that write-backs we
    append to the doc don't register as new collaborator content on the
    next daily run.
    """
    return "\n".join(
        line for line in text.splitlines()
        if _ACK_PREFIX not in line
    )


def _append_to_notes_doc(docs, doc_id: str, text: str) -> None:
    """Append text to the end of a Google Doc."""
    doc = docs.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    end_index = content[-1]["endIndex"] - 1 if content else 1
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": end_index},
                        "text": "\n" + text,
                    }
                }
            ]
        },
    ).execute()
