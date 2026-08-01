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
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeVar

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
    """Call fn() with exponential backoff on retryable API errors (429, 500, 503)."""
    for attempt in range(retries):
        try:
            return fn()
        except gspread.exceptions.APIError as e:
            if e.response.status_code in (429, 500, 503) and attempt < retries - 1:
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
            "drive_config.json not found. Run: python -m coding generate-sheets --apply"
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
    print("  Run python -m coding generate-sheets --apply to upgrade to merged manifest.json.")
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
            "Run python -m coding generate-sheets --apply first."
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
    """Share a file or folder with anyone who has the link as editor.

    Used only for content meant to be open to any collaborator without an
    invite (e.g. the freeform Notes doc). Annotation sheets and language
    folders use _share_with_person instead — see that function's docstring.
    """
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "writer"},
        fields="id",
    ).execute()


def _share_with_person(drive, file_id: str, email: str, role: str = "writer") -> None:
    """Share a file or folder with one specific person, no 'anyone' grant involved.

    Used for annotation sheets, planar/diagnostics reference sheets, and language
    folders — these carry unpublished research data, so access is restricted to
    named individuals rather than "anyone with the link" (a link is not access
    control: it can leak via a forwarded message, a public comment, a screenshot).
    role is "writer" for content someone needs to edit (live annotation sheets)
    or "reader" for content they only need to view (archived sheets, folders).
    """
    drive.permissions().create(
        fileId=file_id,
        body={"type": "user", "role": role, "emailAddress": email},
        fields="id",
        sendNotificationEmail=False,
    ).execute()


def _remove_anyone_permission(drive, file_id: str) -> None:
    """Remove the 'anyone with the link' permission from a file or folder, if present.

    Safe to call on a file that never had one — silently does nothing.
    """
    perms = drive.permissions().list(fileId=file_id, fields="permissions(id,type)").execute()
    for p in perms.get("permissions", []):
        if p.get("type") == "anyone":
            drive.permissions().delete(fileId=file_id, permissionId=p["id"]).execute()


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


_ACK_LINE_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2}\] " + re.escape(_ACK_PREFIX))


def _strip_acknowledgment_lines(text: str) -> str:
    """Strip system-written acknowledgment lines before hashing.

    Removes lines that match the system acknowledgment pattern
    (date-prefixed transfer marker) so that write-backs we append to the
    doc don't register as new collaborator content on the next daily run.
    Uses an anchored regex rather than a substring match to avoid
    stripping legitimate collaborator notes that happen to quote the
    marker text.
    """
    return "\n".join(
        line for line in text.splitlines()
        if not _ACK_LINE_RE.match(line)
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


# ---------------------------------------------------------------------------
# planars-data git helper
# ---------------------------------------------------------------------------

CODED_DATA = ROOT / "coded_data"


def _check_coded_data_clean(coded_data_dir: Optional[Path] = None, extensions: tuple = (".tsv",)) -> None:
    """Abort if the coded_data/ git repo has uncommitted changes to matching files.

    Protects any command that reads coded_data/ as its source of truth from
    acting on a partially-written or reverted state — e.g. import-planar's
    inline auto-commit (_autocommit_data, below) silently failing partway
    through a run and leaving a stale planar_{lang_id}.tsv on disk for later
    steps to read (see issue #248 and the stray-row cleanup that followed it:
    update-sheets --apply ran against exactly such a leftover reverted planar
    and wrote bogus rows to 16 live sheets because it had no such guard).

    Originally import-sheets-only; centralized here so any command reading
    coded_data/ can call it. Silently skips if coded_data/ is not a git repo
    (e.g. CI environments that check out the data separately).

    coded_data_dir: override path for testing (defaults to CODED_DATA).
    extensions: only uncommitted paths ending in one of these count as dirty.
    """
    coded_data = coded_data_dir or CODED_DATA
    if not (coded_data / ".git").exists():
        return
    result = subprocess.run(
        ["git", "-C", str(coded_data), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return  # git not available or not a repo; skip check
    dirty_lines = [
        line for line in result.stdout.splitlines()
        if line.strip() and line[3:].strip().endswith(extensions)
    ]
    if dirty_lines:
        print("ERROR: coded_data/ has uncommitted changes:")
        for line in dirty_lines:
            print(f"  {line}")
        print("Commit or stash these changes before running this command.")
        raise SystemExit(1)


def _autocommit_data(paths: List[Path], message: str) -> None:
    """Stage the given paths in coded_data/, commit, and push to planars-data.

    Called by import-planar and restructure-sheets after writing local TSVs
    so that planars-data stays in sync and the pre-push hook on planars passes.

    Raises SystemExit if `add` or `commit` fails (excluding the harmless
    "nothing to commit" case) — a write that reached disk but not git leaves
    coded_data/ exactly as dirty as a partial revert, which is what let
    update-sheets write bogus rows to 16 live sheets on 2026-07-29 (issue
    #248's stray-row incident): this function's commit silently failed
    (git identity wasn't configured yet in that run), printed a WARNING
    nobody was watching, and returned as if nothing had gone wrong. A push
    failure, by contrast, does NOT raise — the commit already succeeded
    locally, so coded_data/ is clean by every check that matters (git status
    doesn't care about ahead/behind vs. the remote); only the remote lags
    until someone retries `git push` by hand.
    """
    if not paths:
        return
    rel_paths = [str(p.relative_to(CODED_DATA)) for p in paths]
    print(f"\n--- Committing {len(paths)} file(s) to planars-data ---")

    add = subprocess.run(
        ["git", "-C", str(CODED_DATA), "add"] + rel_paths,
        capture_output=True, text=True,
    )
    if add.returncode != 0:
        print(f"ERROR: git add failed in coded_data/: {add.stderr.strip()}")
        print("Local files were written to disk but NOT staged for commit.")
        raise SystemExit(1)

    commit = subprocess.run(
        ["git", "-C", str(CODED_DATA), "commit", "-m", message],
        capture_output=True, text=True,
    )
    if commit.returncode != 0:
        if "nothing to commit" in commit.stdout:
            print("  files unchanged — nothing to commit.")
            return
        print(f"ERROR: git commit failed in coded_data/: {commit.stderr.strip()}")
        print("Local files were written to disk but NOT committed — coded_data/ is now dirty.")
        raise SystemExit(1)
    print(f"  {commit.stdout.splitlines()[0]}")

    push = subprocess.run(
        ["git", "-C", str(CODED_DATA), "push"],
        capture_output=True, text=True,
    )
    if push.returncode != 0:
        print(f"  WARNING: git push failed: {push.stderr.strip()}")
    else:
        print("  pushed planars-data")
