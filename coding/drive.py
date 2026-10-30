"""Google Drive and Sheets client helpers shared across coding/ modules.

All OAuth2 authentication and Drive config I/O live here so that individual
command modules stay focused on their own logic. Retrying on a rate limit is
the Drive door's (coding/drive_door.py), not this module's.

Drive config: coded_data/drive_config.json (private planars-data; the ID
file, ``state_files.ID_FILE``, written only through the local-file door) is
the one record of where every Drive file the tooling made is — the root
folder (_root_folder_id) and each language's folder, sheets, notes Doc and
the rest; its class sheets, status sheet and notification issue are read
and written through ``drive_ids.py`` (unit 11c). Until unit 11c-5
(2026-10-29) a copy of it, the manifest (manifest.json on Drive), was
uploaded for the Colab notebooks; they now find their sheets by label.

Sharing: project data is shared with named people only. Helpers (all take the
doorway): ``ensure_user_permission`` (at least ``role``), ``set_user_role``
(exactly ``role``, up or down), ``remove_anyone_permission`` (a link share),
``make_read_only`` (link share removed, every named editor lowered to reader;
prune-manifest's). Generated notebooks and PDF reports are the one exception
and keep "anyone with the link": ``ensure_anyone_permission`` and
``create_or_update_shared_file`` (used by generate_notebooks.py and
generate_reports.py). Other shared helpers: ``get_or_create_spreadsheet``
(generate_status_sheet.py), ``create_notes_doc`` and ``acknowledgment_line``
(the only text the tooling appends to a notes Doc, the Drive door's rule 8).

``_check_coded_data_clean`` (abort if ``coded_data/`` has uncommitted changes
to files with given extensions, so a command never acts on a half-written or
reverted state) is called only by preconditions.py, which runs it for every
command whose operations.yaml record declares ``coded_data_clean_tree``.
Committing what a command wrote is the local-file door's (file_door.py).

Authentication (OAuth2):
    Credentials JSON at PLANARS_OAUTH_CREDENTIALS env var, or
    ~/.config/planars/oauth_credentials.json by default.
    Token cached at ~/.config/gspread/authorized_user.json after first run.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gspread
from googleapiclient.discovery import build as google_build

from . import drive_door

ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"

# Retry on a transient Google error happens in the Drive door (coding/drive_door.py), which
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
    """Load drive_config.json (``state_files.ID_FILE``, in private
    planars-data since Phase 10 unit 14) if it exists, otherwise return an
    empty dict."""
    from .state_files import ID_FILE    # read now: tests move it
    if ID_FILE.exists():
        return json.loads(ID_FILE.read_text(encoding="utf-8"))
    return {}


def _save_drive_config(config: Dict) -> None:
    """Write drive_config.json with updated folder/file IDs, through the
    local-file door, which commits it when the command ends."""
    from . import file_door
    file_door.write_state(file_door.id_file(), json.dumps(config, indent=2))


# ---------------------------------------------------------------------------
# Spreadsheet helper
# ---------------------------------------------------------------------------

def _open_spreadsheet(gc: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    """Open a spreadsheet by ID, retrying on 429 quota errors with backoff."""
    from .drive_door import _retry
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
    have silently too.
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
    folder_id: str,
    existing_file_id: Optional[str] = None,
    role: str = "reader",
    *,
    identity,
) -> str:
    """Create-or-update a Drive file, renaming on update, reasserting an
    'anyone' share every run via ensure_anyone_permission. Returns the file ID.
    ``identity`` (a ``drive_door.Identity``) labels the file when it is
    created, and gives its name and type (``sheet_spec.file_spec``).

    Shared by generate_notebooks.py's notebook uploads and generate_reports.py's
    PDF uploads — both are rename-on-update, create-if-missing, and (per issue
    #276) reshare on every run, so their per-file duplicate implementations
    collapse into this one function once the sharing timing is unified.
    """
    file_id = create_or_update_file(doorway, content, folder_id, existing_file_id,
                                    identity=identity)
    ensure_anyone_permission(doorway, file_id, role=role)
    return file_id


def create_or_update_file(doorway, content: bytes, folder_id: str,
                          existing_file_id: Optional[str] = None, *, identity) -> str:
    """Create-or-update a Drive file, renaming on update, with no sharing of
    its own (it has its folder's). Returns the file ID. ``identity`` labels
    the file when it is created and gives its name and type
    (``sheet_spec.file_spec``). Contributor charts (laminar-charts) use it;
    create_or_update_shared_file adds the link share."""
    from .sheet_spec import file_spec
    spec = file_spec(identity)
    if existing_file_id:
        doorway.update_file(existing_file_id, name=spec.name,
                            content=content, mimetype=spec.mimetype)
        return existing_file_id
    return doorway.create_file(spec.name, parents=[folder_id], content=content,
                               mimetype=spec.mimetype, identity=identity)


def get_or_create_spreadsheet(doorway, folder_id: str, name: str, *,
                              identity) -> Tuple[object, bool]:
    """Find a spreadsheet by name inside folder_id, or create one there,
    labelled ``identity`` (a ``drive_door.Identity``).

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
    ss = doorway.create_spreadsheet(name, identity=identity)
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


def acknowledgment_line(day: str) -> str:
    """The line check-notes appends to a notes Doc once it has passed the
    notes on (``day`` as YYYY-MM-DD). The only text the tooling ever adds to
    a notes Doc (the Drive door's rule, ``sheet_spec.appended_text_problems``)."""
    return f"[{day}] {_ACK_PREFIX}. Please consult with them for an update."


def create_notes_doc(doorway, lang_id: str, folder_id: str) -> str:
    """Create a Google Doc for collaborator notes in the language folder.

    The doc is named as ``sheet_spec.file_spec`` says (e.g. "Araona
    [arao1248] — Annotation Notes"). The language's annotator (from
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
    from .sheet_spec import file_spec
    identity = drive_door.lang_file("notes_doc", lang_id)
    doc_id = doorway.create_doc(file_spec(identity).name, folder_id, identity=identity)
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


def is_acknowledgment_line(line: str) -> bool:
    """Whether ``line`` is one the tooling wrote (``acknowledgment_line``)."""
    return bool(_ACK_LINE_RE.match(line))


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
        if not is_acknowledgment_line(line)
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
    acting on a partially-written or reverted state — e.g. a commit of what
    an earlier command wrote (since Phase 10 unit 6a, the local-file door's,
    file_door.finish) failing partway through a run and leaving a stale
    planar_{lang_id}.tsv on disk for later
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


