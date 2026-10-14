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
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import gspread
from googleapiclient.discovery import build as google_build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

ROOT = Path(__file__).resolve().parent.parent
# In private planars-data, not the public planars repo (moved 2026-10-12,
# Phase 10 unit 14): it lists every folder and sheet ID. Living in coded_data/
# also means the daily refresh's commit there keeps IDs that CI runs record.
DRIVE_CONFIG_PATH = ROOT / "coded_data" / "drive_config.json"
_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"

# Retry on 429/500/503 happens in the Drive door (coding/drive_door.py), which
# wraps every doorway call.


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



def _ordered_manifest_bytes(full_config: Dict) -> bytes:
    """The manifest as it is written to Drive, with each language's keys ordered.

    Human-readable metadata comes first, so anyone opening manifest.json sees
    the language before the machinery.
    """
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
    return json.dumps(ordered, indent=2).encode("utf-8")


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
    content = _ordered_manifest_bytes(full_config)

    def update(file_id: str) -> None:
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
        drive.files().update(fileId=file_id, media_body=media).execute()

    def create() -> str:
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
        return drive.files().create(
            body={"name": "manifest.json", "parents": [root_folder_id]},
            media_body=media,
            fields="id",
        ).execute()["id"]

    return _upload_manifest_with(update, create, existing_file_id)


def upload_manifest(doorway, full_config: Dict, root_folder_id: str,
                    existing_file_id: str = None) -> str:
    """``_upload_planars_config`` through a ``drive_doorway.DriveDoorway``.

    Same key reordering and same update-then-create fallback; both share one
    body, so the manifest-writing rules exist in exactly one place. (There are
    still three *other* independent manifest writers elsewhere in the codebase
    — that is issue #276, not this.)

    Checks ``full_config`` against ``manifest_contract.check()`` first and
    prints a warning if it finds anything — but writes regardless. Phase 6
    boundary 4 (issue #271); see ``manifest_contract.py``'s module docstring
    for why this is deliberately non-blocking. ``integrity-check`` runs the
    same check against the currently-loaded manifest and *does* let it drive
    a trackable issue — this local warning is only the in-the-moment signal.
    """
    from . import manifest_contract
    problems = manifest_contract.check(full_config)
    if problems:
        print(f"  WARNING: manifest being written doesn't match the expected shape ({len(problems)} issue(s)):")
        for p in problems[:5]:
            print(f"    {p}")

    content = _ordered_manifest_bytes(full_config)
    return _upload_manifest_with(
        lambda file_id: doorway.update_file(file_id, content=content,
                                            mimetype="application/json"),
        lambda: doorway.create_file("manifest.json", [root_folder_id],
                                    content=content, mimetype="application/json"),
        existing_file_id,
    )


def _upload_manifest_with(update, create, existing_file_id: str = None) -> str:
    """Update manifest.json in place if we know its ID, else create it.

    The fallback matters: a failed update used to mean the manifest silently
    stopped being written. Creating a second one is not ideal either, but it is
    visible.
    """
    if existing_file_id:
        try:
            update(existing_file_id)
            return existing_file_id
        except Exception as e:
            print(f"  WARNING: could not update existing manifest.json ({e}); creating new file.")
    return create()


def _load_manifest_from_drive(drive) -> Dict:
    """Load the full manifest (all languages) from Drive.

    Kept for callers that still hold a raw Drive service. Files migrated to
    the doorway call ``load_manifest(doorway)`` instead; both share one body, so
    the manifest-loading rules exist in exactly one place.
    """
    return _load_manifest_with(lambda file_id: _download_file_json(drive, file_id))


def load_manifest(doorway) -> Dict:
    """Load the full manifest through a ``drive_doorway.DriveDoorway``."""
    return _load_manifest_with(doorway.download_file_json)


def _load_manifest_with(download_json: Callable[[str], Dict]) -> Dict:
    """Load the full manifest, given a way to download a JSON file by ID.

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
            full_config = download_json(file_id)
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
        lang_data = download_json(mfid)
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
    from .drive_door import _retry  # lazy: drive_door imports from this package
    return _retry(lambda: gc.open_by_key(spreadsheet_id))


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


def ensure_anyone_permission(doorway, file_id: str, role: str = "reader") -> None:
    """Grant 'anyone with the link' access to file_id, unless it already has one.

    Used only for generated notebooks and PDF reports — outputs meant to be
    passed around; project data is shared by name (`ensure_user_permission`).
    The single mechanism behind both of issue #276's decisions: called
    unconditionally on every run from both sharing call sites
    (generate_notebooks.py and generate_reports.py, via
    `create_or_update_shared_file`; setup_root_folder.py used it too until
    2026-10-12, when the root folder stopped being link-shared), it
    both restores a manually-revoked share (a run always checks, so a missing
    grant gets recreated) and never piles up duplicates (an existing grant is
    left alone rather than re-created). Doing this unconditionally without the
    existence check first is exactly the bug setup_root_folder.py had before
    this fix, and generate_notebooks.py's repeat regeneration turned out to
    have silently too (see that command's CLAUDE.md note).
    """
    existing = doorway.list_permissions(file_id, fields="permissions(type)")
    if any(p.get("type") == "anyone" for p in existing):
        return
    doorway.create_permission(file_id, type="anyone", role=role)


def remove_anyone_permission(doorway, file_id: str) -> bool:
    """Remove every 'anyone with the link' grant from file_id. True if any was removed.

    Project data is shared with named people only (decided 2026-10-12, Phase
    10 unit 14); only generated notebooks and PDF reports keep a link share
    (`ensure_anyone_permission`). The one copy of a sequence that used to be
    inlined separately in restructure_sheets, generate_status_sheet and
    setup_root_folder.

    A grant *inherited* from a parent folder cannot be removed here (Google
    answers "Permission not found"); it goes when the parent's goes, so it is
    skipped. Note the tooling's OAuth scope reaches only files it created:
    Google also refuses the change on a folder that holds any file made some
    other way (`appNotAuthorizedToChild`), which only a person can then fix.
    """
    removed = False
    perms = doorway.list_permissions(
        file_id, fields="permissions(id,type,permissionDetails)")
    for p in perms:
        if p.get("type") != "anyone":
            continue
        details = p.get("permissionDetails") or []
        if details and all(d.get("inherited") for d in details):
            continue
        doorway.delete_permission(file_id, p["id"])
        removed = True
    return removed


_ROLE_RANK = {"reader": 1, "commenter": 2, "writer": 3, "owner": 4}


def ensure_user_permission(doorway, file_id: str, email: str, role: str) -> bool:
    """Give the named person at least `role` on file_id. True if a grant was made.

    Checks first, so re-running never piles up duplicate grants, and a person
    who already holds this role or a higher one is left alone.
    """
    perms = doorway.list_permissions(
        file_id, fields="permissions(emailAddress,role)")
    held = [_ROLE_RANK.get(p.get("role"), 0) for p in perms
            if (p.get("emailAddress") or "").lower() == email.lower()]
    if held and max(held) >= _ROLE_RANK[role]:
        return False
    doorway.create_permission(file_id, type="user", role=role,
                              email=email, notify=False)
    return True


def set_user_role(doorway, file_id: str, email: str, role: str) -> bool:
    """Make the named person's own grant on file_id exactly `role`, up or
    down. True if anything changed.

    Unlike ensure_user_permission, this can lower access, which archiving
    needs: creating a reader grant for someone who already holds writer
    leaves them a writer (Google keeps the higher role; checked live
    2026-10-13), so an archived sheet "locked" that way was never read-only
    for its annotator. The role is changed in place: Google refuses to
    delete a grant on a file that also inherits one for the same person from
    its folder, which is every language sheet. An owner is never changed.
    """
    perms = doorway.list_permissions(
        file_id, fields="permissions(id,type,role,emailAddress)")
    own = [p for p in perms if p.get("type") == "user"
           and (p.get("emailAddress") or "").lower() == email.lower()]
    if not own:
        doorway.create_permission(file_id, type="user", role=role,
                                  email=email, notify=False)
        return True
    p = own[0]
    if p.get("role") in (role, "owner"):
        return False
    doorway.update_permission(file_id, p["id"], role)
    return True


def make_read_only(doorway, file_id: str) -> List[str]:
    """Leave file_id readable but editable by nobody except its owner: remove
    any link share, and lower every named person's own grant to reader.
    Returns the addresses lowered. For a retired sheet (prune-manifest),
    which no one should keep answering in by habit."""
    remove_anyone_permission(doorway, file_id)
    perms = doorway.list_permissions(
        file_id, fields="permissions(type,role,emailAddress)")
    lowered = []
    for p in perms:
        email = p.get("emailAddress") or ""
        if (p.get("type") == "user" and email and p.get("role") in ("writer", "commenter")
                and set_user_role(doorway, file_id, email, "reader")):
            lowered.append(email)
    return lowered


def create_or_update_shared_file(
    doorway,
    content: bytes,
    filename: str,
    mimetype: str,
    folder_id: str,
    existing_file_id: Optional[str] = None,
    role: str = "reader",
) -> str:
    """Create-or-update a Drive file, renaming on update, reasserting an
    'anyone' share every run via ensure_anyone_permission. Returns the file ID.

    Shared by generate_notebooks.py's notebook uploads and generate_reports.py's
    PDF uploads — both are rename-on-update, create-if-missing, and (per issue
    #276) reshare on every run, so their per-file duplicate implementations
    collapse into this one function once the sharing timing is unified.
    """
    if existing_file_id:
        doorway.update_file(existing_file_id, name=filename,
                            content=content, mimetype=mimetype)
        file_id = existing_file_id
    else:
        file_id = doorway.create_file(filename, parents=[folder_id],
                                      content=content, mimetype=mimetype)
    ensure_anyone_permission(doorway, file_id, role=role)
    return file_id


def get_or_create_spreadsheet(doorway, folder_id: str, name: str) -> Tuple[object, bool]:
    """Find a spreadsheet by name inside folder_id, or create one there.

    Used by generate_status_sheet.py (and, until its retirement on
    2026-10-11, generate_biuniqueness_allomorphy_sheet.py, whose identical
    copy issue #276 collapsed into this one). Returns (spreadsheet, created);
    reused on re-runs so the URL stays stable across regenerations.
    """
    existing = doorway.list_files(
        q=(
            f"name='{name}' and '{folder_id}' in parents"
            " and mimeType='application/vnd.google-apps.spreadsheet'"
            " and trashed=false"
        ),
        fields="files(id)",
    )
    if existing:
        return doorway.open_spreadsheet(existing[0]["id"]), False
    ss = doorway.create_spreadsheet(name)
    doorway.move_file(ss.id, folder_id)
    return ss, True


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


def _notes_doc_name(lang_id: str, display_name: str = "") -> str:
    """What a language's notes doc is called on Drive."""
    return f"{display_name} — Annotation Notes" if display_name else f"notes_{lang_id}"


def create_notes_doc(doorway, lang_id: str, folder_id: str,
                     display_name: str = "") -> str:
    """Create a Google Doc for collaborator notes in the language folder.

    The doc is named "{display_name} — Annotation Notes" (e.g. "Araona
    [arao1248] — Annotation Notes"), falling back to "notes_{lang_id}" if
    display_name is not provided. The language's annotator (from
    `languages.yaml`) gets **edit** access by name, since the doc is where
    they write notes to the coordinator; nobody gets link access. Until
    2026-10-12 this granted "anyone with the link" edit access instead, in
    case a collaborator had no Google account — but the live docs had lost
    that grant and left the annotator view-only, unable to write notes at
    all (Phase 10 unit 14: data is shared with named people only). The grant
    stays beside the creation call rather than being left to the caller to
    remember.

    Returns the new document's file ID.
    """
    from .people import annotator_email
    doc_id = doorway.create_doc(_notes_doc_name(lang_id, display_name), folder_id)
    email = annotator_email(lang_id)
    if email:
        ensure_user_permission(doorway, doc_id, email, "writer")
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
