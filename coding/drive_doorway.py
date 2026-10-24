"""The Drive doorway: one protocol, two implementations.

Phase 0a of the data layer plan (docs/data-layer-implementation-plan.md). This
module defines the *only* interface through which ``coding/`` commands should
reach Google Drive, Sheets, and Docs. It exists so every command can be run
end-to-end with no network — against ``tests/fake_drive.FakeDriveDoorway``,
which replays the fixtures recorded by ``python -m coding capture-drive-state``.

Two implementations:

- ``GspreadDoorway`` — the real one. Delegates to ``gspread`` and the
  ``googleapiclient`` Drive/Docs services, via the helpers in ``drive.py``.
- ``FakeDriveDoorway`` (in ``tests/fake_drive.py``) — in-memory, seeded from
  recorded fixtures, records every mutation for assertion.

Design notes (from docs/drive-protocol-surface.md § "Proposed method
signatures", accepted 2026-08-01)
--------------------------------------------------------------------------
**Handles are objects, not IDs.** ``open_spreadsheet`` returns a spreadsheet
handle that callers hold across many operations; a worksheet handle exposes
``.spreadsheet`` back to its parent. Several commands (``sync_params``,
``restructure_sheets``, ``update_sheets``) read, mutate, and re-read the same
handle in one sequence and would otherwise have to re-thread IDs they hold.

**Mutations must be visible to the next read on the same handle.**
``update_sheets.py`` writes (``_add_trailing_columns``) then immediately
re-reads the tab (``ws.get_all_values()``) specifically to see its own write.
Any implementation must honour that without
requiring a fresh ``open_spreadsheet``.

**Handle method names mirror gspread exactly.** This is a deliberate deviation
from the reviewed proposal, which suggested renaming ``batch_update`` →
``apply_sheet_requests`` and ``values_batch_update`` → ``write_value_ranges``.
The rename was rejected for one reason: the migration proceeds *one file at a
time* (plan Phase 0b/1), and several helpers are shared across migrated and
unmigrated files — ``generate_sheets._format_and_validate`` is called by four
of the eleven. Mirroring gspread's names means such a helper works unchanged
whether it is handed a real ``gspread.Worksheet`` or a fake handle, so
migration stays the mechanical call-site substitution the plan requires rather
than a cross-file rewrite. ``GspreadDoorway`` returns raw gspread objects as
handles; commands never hold them, because the Drive door wraps them
(design: docs/drive-door-design.md § 2.2, reversing the 2026-08-01 choice).

The disambiguation the proposal was protecting is preserved by other means:

- ``batch_update(body)``        → ``spreadsheets.batchUpdate``
  (structural/formatting *requests*: ``{"requests": [...]}``)
- ``values_batch_update(body)`` → ``spreadsheets.values.batchUpdate``
  (cell *values* by range: ``{"valueInputOption": ..., "data": [...]}``)

These are **different API endpoints with incompatible request shapes**, and
merging them is the single most likely way a fake silently diverges from
reality. ``FakeDriveDoorway`` therefore rejects a body of the wrong shape on
either method, turning the hazard into a loud failure instead of a silent one.

**Retry, and every check on a write, live in the Drive door**
(``coding/drive_door.py``), which ``get_doorway()`` wraps around whichever
implementation is installed. Nothing here retries: the door retries every
call, once, for both implementations.

**Every command that touches Drive goes through the doorway**;
``tests/test_doorway_coverage.py`` derives the list of files that still reach
Drive another way and checks it is empty.

**Testing against the fake.** ``tests/fake_drive.py`` is seeded from
``coded_data/.test_fixtures/drive_state/`` (recorded by ``capture-drive-state``;
in planars-data because it is real annotation content). Command tests read
local files from the matching frozen copy, ``coded_data/.test_fixtures/coded_data/``
(``fake_drive.FROZEN_CODED_DATA``, or ``use_frozen_coded_data()`` to redirect
every module's ``CODED_DATA`` to a private copy of it; a harness that builds its
own copy uses ``point_coded_data_at()``, never one module's ``CODED_DATA`` alone,
since the Drive door reads its own), never from the live language folders,
which change whenever an annotator works. ``tests/render_mutations.py`` renders
the fake's mutation log as a digest with tab titles and column headers instead
of raw IDs; use it for human review. It cannot resolve headers for a
spreadsheet created within the same test run, so a digest of a creation-heavy
command (generate-sheets, restructure-sheets) shows ``BEYOND HEADER``
throughout: a rendering gap, not a bug. ``tests/mutation_checks.py`` holds
assertions shared across commands, e.g.
``assert_no_criterion_writes_onto_trailing_columns``: no dropdown and no
criterion note may land on ``Source`` or ``Comments``.

**Indexing has no single rule.** gspread's convenience methods are 1-based
(``row_values``, ``update_cell``, ``insert_cols``); raw Sheets API request
objects inside ``batch_update`` are 0-based (``startRowIndex``,
``startColumnIndex``). Both conventions are carried through unchanged. See
docs/drive-protocol-surface.md § "Subtleties most likely to be guessed wrong"
item 5 for the table.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

import gspread

from .drive import (
    _download_file_json,
    _get_clients,
    _get_docs_client,
    _get_or_create_folder,
    _move_to_folder,
    _read_notes_doc_text,
    _append_to_notes_doc,
)

# Re-exported so callers and the fake agree on one exception vocabulary. Call
# sites already catch gspread.WorksheetNotFound; the fake raises the same class
# so the try/except idiom in ~15 places needs no edit during migration.
WorksheetNotFound = gspread.exceptions.WorksheetNotFound
APIError = gspread.exceptions.APIError

# open_spreadsheet raises these two for "no such spreadsheet" and "you are not
# shared on it". They come from gspread, not from us: open_by_key turns a 404
# into SpreadsheetNotFound and a 403 into Python's own PermissionError, so a
# caller that wants to tell those apart from a dropped connection catches them
# by name. Named here so that stays true of the fake as well.
SpreadsheetNotFound = gspread.exceptions.SpreadsheetNotFound
NoAccess = PermissionError


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

@runtime_checkable
class WorksheetHandle(Protocol):
    """One tab. Method names and index bases mirror gspread exactly."""

    # Cached properties, not calls. row_count/col_count are the *declared*
    # grid size, which is not the same as the used range: 10 of the 80
    # captured tabs have a used range narrower than their declared width.
    id: int
    title: str
    row_count: int
    col_count: int
    spreadsheet: "SpreadsheetHandle"

    def get_all_values(self) -> List[List[str]]:
        """All values in the used range, every row padded to the used width.

        The used range runs to the last non-empty row and the last non-empty
        column, and can be narrower than ``col_count``. Rows come back
        rectangular — the live capture of all 80 tabs found no ragged
        responses, correcting an earlier hypothesis. Returns ``[]`` for an
        entirely empty sheet.
        """

    def row_values(self, row: int) -> List[str]:
        """One row, ``row`` **1-based**, trimmed at its own last non-empty cell.

        Unlike ``get_all_values``, no padding to the used width: gspread
        fetches a single-row range, so the row is only as wide as itself.
        """

    def update(self, values: Sequence[Sequence[Any]], range_name: str = "A1",
               raw: bool = True) -> Any:
        """Write ``values`` with their top-left corner at ``range_name``.

        Writes only the cells covered by ``values`` — it does not clear the
        rest of the sheet. Most call sites use ``"A1"`` (whole-body replace);
        ``sync_params.py`` uses a computed anchor (``start_cell``) to write just
        the columns it inserted.

        ``raw=False`` (``generate_status_sheet.py``) makes Sheets *parse* the
        values, so an embedded ``=HYPERLINK(...)`` becomes a formula rather
        than literal text. That is a change in what the write means, not in
        how it displays.
        """

    def update_cell(self, row: int, col: int, value: Any) -> Any:
        """Single cell. ``row`` and ``col`` are both **1-based**."""

    def insert_cols(self, values: Sequence[Sequence[Any]], col: int = 1) -> Any:
        """Insert columns before ``col`` (**1-based**).

        ``values`` is a list of whole columns, each ``[header, v, v, ...]``.
        """

    def append_rows(self, values: Sequence[Sequence[Any]],
                    value_input_option: str = "RAW") -> Any:
        """Append after the last non-empty row, growing the grid if needed."""

    def clear(self) -> Any:
        """Clear **values only** — not formatting, not the grid size.

        This is real Sheets behaviour and two call sites depend on it:
        ``generate_sheets._reset_worksheet`` clears *and* reformats precisely
        because ``clear()`` alone leaves background colour and grid size
        intact, while ``restructure_sheets`` relies on the cheaper bare
        ``clear()`` on tabs it is about to fully overwrite anyway.
        """

    def resize(self, rows: Optional[int] = None, cols: Optional[int] = None) -> Any:
        """Change the declared grid size. Shrinking discards out-of-bounds cells."""

    def update_title(self, title: str) -> Any:
        """Rename the tab in place."""


@runtime_checkable
class SpreadsheetHandle(Protocol):
    """One spreadsheet file."""

    id: str
    title: str
    url: str

    @property
    def sheet1(self) -> WorksheetHandle:
        """The first tab in current tab order."""

    def worksheets(self) -> List[WorksheetHandle]:
        """All tabs in **live tab order** — the order they appear in the UI.

        Order is load-bearing: ``locked_tabs.reorder_tabs`` and
        ``_move_status_tab_to_end`` detect drift from it, and both failure
        modes (falsely reordering, falsely not reordering) are silent. Never
        sort this.
        """

    def worksheet(self, title: str) -> WorksheetHandle:
        """Tab by title. Raises ``WorksheetNotFound`` if absent.

        The not-found signal must stay narrow enough for callers to keep
        distinguishing "tab genuinely absent" from "transient API error" —
        ``refresh_dropdowns.py`` currently catches bare ``Exception`` here and
        conflates the two.
        """

    def add_worksheet(self, title: str, rows: int, cols: int,
                      index: Optional[int] = None) -> WorksheetHandle:
        """Create a tab, appended last unless ``index`` says otherwise."""

    def del_worksheet(self, worksheet: WorksheetHandle) -> Any:
        """Delete a tab."""

    def reorder_worksheets(self, worksheets_in_desired_order: Sequence[WorksheetHandle]) -> Any:
        """Set tab order from a full ordered list of this file's tabs."""

    def batch_update(self, body: Mapping[str, Any]) -> Any:
        """``spreadsheets.batchUpdate`` — structural and formatting *requests*.

        Body is ``{"requests": [...]}``. Request dicts pass through verbatim;
        the doorway routes them, it does not interpret them. Request types used
        across the eleven callers: ``updateSheetProperties``, ``repeatCell``,
        ``setDataValidation``, ``insertDimension``, ``deleteDimension``,
        ``updateDimensionProperties``, ``updateCells``, ``mergeCells``,
        ``addProtectedRange`` (``coding/locked_tabs.py``).

        **Not** the same endpoint as ``values_batch_update``.
        """

    def list_protected_ranges(self, sheetid: int) -> List[Dict[str, Any]]:
        """The protections on one tab (``ProtectedRange`` dicts), by sheet id.
        Read by ``coding/locked_tabs.py`` so a rebuild protects a tab once."""

    def fetch_sheet_metadata(self, params: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        """``spreadsheets.get`` without cell data. The Drive door asks for
        ``sheets(properties(sheetId,title),developerMetadata)`` to read each
        tab's identity labels (written with ``createDeveloperMetadata``), and
        for each tab's index and protected ranges besides, to check a class
        sheet's shape at the end of a command (rule 6)."""

    def values_batch_get(self, ranges: List[str],
                         params: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        """``spreadsheets.values.batchGet`` — several A1 ranges in one read.

        Returns ``{"valueRanges": [{"range", "values"?}, ...]}`` in the order
        asked; a range with no values has no ``"values"`` key, and each row is
        trimmed at its last non-empty cell. Name the tab in every range
        (``gspread.utils.absolute_range_name``): a bare range reads the first
        tab. ``sync_params.py`` reads every tab's header row this way, one read
        per spreadsheet instead of one per tab (Google allows about 60 reads a
        minute).
        """

    def values_batch_update(self, body: Mapping[str, Any]) -> Any:
        """``spreadsheets.values.batchUpdate`` — cell *values* by A1 range.

        Body is ``{"valueInputOption": ..., "data": [{"range", "values"}, ...]}``.
        One caller: ``restructure_sheets._cascade_rename_pair_tab``, which
        names the tab in every range (a bare range goes to the first tab).

        **Not** the same endpoint as ``batch_update``.
        """


class DriveDoorway(Protocol):
    """Session-level operations: spreadsheet lifecycle, Drive files, Docs."""

    # -- Spreadsheets -------------------------------------------------------
    def create_spreadsheet(self, title: str) -> SpreadsheetHandle:
        """A new spreadsheet. Through the Drive door, a command also says what
        it is (``identity=drive_door.class_sheet(lang, class)``), so the door
        can check what is written to it."""

    def open_spreadsheet(self, spreadsheet_id: str) -> SpreadsheetHandle:
        """Open by ID. Raises ``SpreadsheetNotFound`` or ``NoAccess``."""

    # -- Drive files --------------------------------------------------------
    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict]:
        """Raw Drive query. Returns the ``files`` list: every match, read page
        by page, unless ``page_size`` asks for one page of that size.

        ``q`` is passed through unescaped, as today. Current callers build it
        by f-string interpolation of names and IDs; that is injection-shaped
        but not a live risk, since every interpolated value is internally
        generated. Flagged, not fixed — see the protocol surface doc.
        """

    def get_file(self, file_id: str, fields: str = "id",
                 supports_all_drives: bool = False) -> Dict:
        """File metadata. ``fields`` is the raw Drive field mask.

        ``supports_all_drives`` reaches files on a shared drive rather than in
        My Drive. Exactly one caller sets it (``prune_manifest``, reading a
        sheet's name and modified time), and it is carried through rather than
        dropped — even though nothing else in the codebase sends it, including
        ``move_file``, which ``prune_manifest`` calls on the same file moments
        later. So a sheet on a shared drive can be read but not moved. That
        inconsistency is recorded, not resolved, here.
        """

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None,
                    properties: Optional[Mapping[str, str]] = None) -> str:
        """Create a Drive file; returns its ID.

        Covers both the metadata-only form (folders, Docs — pass a Google
        mimetype and no content) and the media-upload form (manifest.json,
        notebooks, PDFs). ``properties`` are the file's Drive properties: the
        Drive door's identity labels (``planars_kind`` and so on). Public
        properties, not ``appProperties``, which only the OAuth client that
        wrote them can read; a second coordinator's client must see them too.
        """

    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None,
                    properties: Optional[Mapping[str, Optional[str]]] = None) -> None:
        """Update content and/or rename and/or set Drive properties
        (merged into the file's own; a key set to None is removed).

        ``name`` is deliberately independent of ``content``: callers differ on
        whether an update renames (the manifest upload does not;
        ``drive.create_or_update_shared_file``, for notebooks and reports,
        does), and ``restructure_sheets`` renames without touching content at
        all. The doorway lets each caller choose rather than picking one as
        canonical.
        """

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        """Reparent a file (internally a get-parents then update)."""

    def trash_file(self, file_id: str) -> None:
        """Move a file to Drive's trash, where it stays restorable for 30
        days; never a permanent delete."""

    def download_file_json(self, file_id: str) -> Dict: ...

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Find-or-create by name; returns the folder ID. Idempotent.

        ``parent_id=None`` searches and creates at Drive root — used once, by
        ``generate_status_sheet``, deliberately: a status sheet nested under
        the project root folder would inherit an "anyone" permission that
        Google's API refuses to remove at the child level.
        """

    # -- Permissions --------------------------------------------------------
    def list_permissions(self, file_id: str,
                         fields: str = "permissions(id,type)") -> List[Dict]: ...

    def create_permission(self, file_id: str, type: str, role: str,
                          email: Optional[str] = None,
                          notify: bool = False) -> str: ...

    def delete_permission(self, file_id: str, permission_id: str) -> None: ...

    def update_permission(self, file_id: str, permission_id: str, role: str) -> None: ...

    # -- Comments (telling an annotator about problems, #309) ----------------
    def list_comments(self, file_id: str) -> List[Dict]:
        """The file's comments, each ``{"id", "content"}``, oldest first."""

    def create_comment(self, file_id: str, content: str) -> str:
        """Add a comment to the file (not anchored to a cell); returns its id.
        A ``+address`` in ``content`` mentions that person, and Google emails
        them — the way an annotator without GitHub hears about problems."""

    # -- Google Docs (collaborator notes) -----------------------------------
    def create_doc(self, name: str, parent_id: str,
                   properties: Optional[Mapping[str, str]] = None) -> str: ...

    def get_doc_text(self, doc_id: str) -> str: ...

    def append_doc_text(self, doc_id: str, text: str) -> None: ...


# ---------------------------------------------------------------------------
# The live doorway
# ---------------------------------------------------------------------------

class GspreadDoorway:
    """The live doorway. Delegates to gspread / googleapiclient.

    Returns raw ``gspread.Spreadsheet`` and ``gspread.Worksheet`` objects as
    handles — they already satisfy ``SpreadsheetHandle``/``WorksheetHandle``,
    since the protocols were written to mirror gspread. Commands never hold
    them: ``get_doorway()`` wraps this in the Drive door, which checks and
    retries every call.

    Clients are built lazily so that constructing a doorway (e.g. at import
    time, or in a dry run that turns out to need nothing) performs no OAuth.
    """

    def __init__(self, gc=None, drive=None, docs=None) -> None:
        self._gc = gc
        self._drive = drive
        self._docs = docs

    # -- lazy clients -------------------------------------------------------
    def _clients(self):
        if self._gc is None or self._drive is None:
            self._gc, self._drive = _get_clients()
        return self._gc, self._drive

    @property
    def gc(self):
        return self._clients()[0]

    @property
    def drive(self):
        return self._clients()[1]

    @property
    def docs(self):
        if self._docs is None:
            self._docs = _get_docs_client(self.gc)
        return self._docs

    # -- spreadsheets -------------------------------------------------------
    def create_spreadsheet(self, title: str):
        return self.gc.create(title)

    def open_spreadsheet(self, spreadsheet_id: str):
        return self.gc.open_by_key(spreadsheet_id)

    # -- Drive files --------------------------------------------------------
    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict]:
        if page_size is not None:
            return self.drive.files().list(q=q, fields=fields, pageSize=page_size
                                           ).execute().get("files", [])
        # Every page: Drive returns at most 100 files a page by default, and a
        # listing that stopped there would look complete.
        files: List[Dict] = []
        token = None
        while True:
            kwargs: Dict[str, Any] = {"q": q, "fields": f"nextPageToken, {fields}",
                                      "pageSize": 1000}
            if token:
                kwargs["pageToken"] = token
            response = self.drive.files().list(**kwargs).execute()
            files += response.get("files", [])
            token = response.get("nextPageToken")
            if not token:
                return files

    def get_file(self, file_id: str, fields: str = "id",
                 supports_all_drives: bool = False) -> Dict:
        kwargs: Dict[str, Any] = {"fileId": file_id, "fields": fields}
        if supports_all_drives:
            kwargs["supportsAllDrives"] = True
        return self.drive.files().get(**kwargs).execute()

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None,
                    properties: Optional[Mapping[str, str]] = None) -> str:
        body: Dict[str, Any] = {"name": name}
        if parents:
            body["parents"] = list(parents)
        if properties:
            body["properties"] = dict(properties)
        if mimetype and content is None:
            # Metadata-only create (folder, Doc): the mimetype *is* the file type.
            body["mimeType"] = mimetype
        kwargs: Dict[str, Any] = {"body": body, "fields": "id"}
        if content is not None:
            kwargs["media_body"] = self._media(content, mimetype)
        return self.drive.files().create(**kwargs).execute()["id"]

    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None,
                    properties: Optional[Mapping[str, Optional[str]]] = None) -> None:
        kwargs: Dict[str, Any] = {"fileId": file_id}
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if properties:
            body["properties"] = dict(properties)
        if body:
            kwargs["body"] = body
        if content is not None:
            kwargs["media_body"] = self._media(content, mimetype)
        self.drive.files().update(**kwargs).execute()

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        _move_to_folder(self.drive, file_id, new_parent_id)

    def trash_file(self, file_id: str) -> None:
        self.drive.files().update(fileId=file_id, body={"trashed": True}).execute()

    def download_file_json(self, file_id: str) -> Dict:
        return _download_file_json(self.drive, file_id)

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        return _get_or_create_folder(self.drive, name, parent_id)

    # -- permissions --------------------------------------------------------
    def list_permissions(self, file_id: str,
                         fields: str = "permissions(id,type)") -> List[Dict]:
        return (self.drive.permissions()
                .list(fileId=file_id, fields=fields).execute()
                .get("permissions", []))

    def create_permission(self, file_id: str, type: str, role: str,
                          email: Optional[str] = None,
                          notify: bool = False) -> str:
        body: Dict[str, Any] = {"type": type, "role": role}
        if email:
            body["emailAddress"] = email
        kwargs: Dict[str, Any] = {"fileId": file_id, "body": body, "fields": "id"}
        if type == "user":
            # sendNotificationEmail is only meaningful for a named user; Drive
            # rejects it on an "anyone" grant.
            kwargs["sendNotificationEmail"] = notify
        return self.drive.permissions().create(**kwargs).execute()["id"]

    def delete_permission(self, file_id: str, permission_id: str) -> None:
        self.drive.permissions().delete(
            fileId=file_id, permissionId=permission_id).execute()

    def update_permission(self, file_id: str, permission_id: str, role: str) -> None:
        # Changing the role in place, rather than delete-and-recreate: Google
        # refuses to delete a person's grant on a file that also inherits one
        # for them from its folder (checked live 2026-10-13).
        self.drive.permissions().update(
            fileId=file_id, permissionId=permission_id, body={"role": role}).execute()

    # -- comments -----------------------------------------------------------
    def list_comments(self, file_id: str) -> List[Dict]:
        comments: List[Dict] = []
        token = None
        while True:
            kwargs: Dict[str, Any] = {"fileId": file_id,
                                      "fields": "nextPageToken,comments(id,content)"}
            if token:
                kwargs["pageToken"] = token
            page = self.drive.comments().list(**kwargs).execute()
            comments += page.get("comments", [])
            token = page.get("nextPageToken")
            if not token:
                return comments

    def create_comment(self, file_id: str, content: str) -> str:
        return self.drive.comments().create(
            fileId=file_id, body={"content": content}, fields="id").execute()["id"]

    # -- docs ---------------------------------------------------------------
    def create_doc(self, name: str, parent_id: str,
                   properties: Optional[Mapping[str, str]] = None) -> str:
        body: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [parent_id],
        }
        if properties:
            body["properties"] = dict(properties)
        return self.drive.files().create(body=body, fields="id").execute()["id"]

    def get_doc_text(self, doc_id: str) -> str:
        return _read_notes_doc_text(self.docs, doc_id)

    def append_doc_text(self, doc_id: str, text: str) -> None:
        _append_to_notes_doc(self.docs, doc_id, text)

    # -- internals ----------------------------------------------------------
    @staticmethod
    def _media(content: bytes, mimetype: Optional[str]):
        import io

        from googleapiclient.http import MediaIoBaseUpload

        return MediaIoBaseUpload(
            io.BytesIO(content), mimetype=mimetype or "application/octet-stream")


# ---------------------------------------------------------------------------
# Doorway selection
# ---------------------------------------------------------------------------
#
# Commands call get_doorway(); tests call set_doorway(FakeDriveDoorway(...)).
# A module-level override is deliberately the whole mechanism: threading a
# doorway argument through eleven command mains would be exactly the
# call-site rewrite the migration is meant to avoid.

#
# Either way the command gets the Drive door (coding/drive_door.py) wrapped
# around it, so the tests run exactly the checks that run live.

_doorway: Optional[DriveDoorway] = None


def get_doorway() -> DriveDoorway:
    """Return the active doorway, creating the real one on first use."""
    global _doorway
    if _doorway is None:
        from .drive_door import CheckedDoorway
        _doorway = CheckedDoorway(GspreadDoorway())
    return _doorway


def set_doorway(doorway: Optional[DriveDoorway]) -> None:
    """Install a doorway (or ``None`` to reset to the real one). Tests only.

    A plain doorway (the fake) is wrapped in the Drive door in enforce mode:
    a test that breaks a rule fails."""
    global _doorway
    from .drive_door import ENFORCE, CheckedDoorway
    if doorway is not None and not isinstance(doorway, CheckedDoorway):
        doorway = CheckedDoorway(doorway, mode=ENFORCE)
    _doorway = doorway


def reset_doorway() -> None:
    """Drop the cached doorway so the next get_doorway() rebuilds it."""
    set_doorway(None)
