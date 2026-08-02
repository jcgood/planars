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
``update_sheets.py`` writes then immediately re-reads (``:391`` → ``:393``)
specifically to see its own write. Any implementation must honour that without
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
than a cross-file rewrite. It also means ``GspreadDoorway`` can return raw
gspread objects as handles, adding no wrapper code — and so no wrapper bugs —
on the path that touches live data.

The disambiguation the proposal was protecting is preserved by other means:

- ``batch_update(body)``        → ``spreadsheets.batchUpdate``
  (structural/formatting *requests*: ``{"requests": [...]}``)
- ``values_batch_update(body)`` → ``spreadsheets.values.batchUpdate``
  (cell *values* by range: ``{"valueInputOption": ..., "data": [...]}``)

These are **different API endpoints with incompatible request shapes**, and
merging them is the single most likely way a fake silently diverges from
reality. ``FakeDriveDoorway`` therefore rejects a body of the wrong shape on
either method, turning the hazard into a loud failure instead of a silent one.

**Retry.** Only ``open_spreadsheet`` retries internally, matching
``drive._open_spreadsheet``, which is what most call sites already use. Every
other method passes through, so call sites that wrap themselves in
``_with_retry`` keep exactly the semantics they have today — the migration's
non-goal is "no behaviour changes", and this is where that bites. The
inconsistent retry coverage catalogued in docs/drive-protocol-surface.md
(``_verify_manifest_sheet_ids`` misreporting a 429 as a stale sheet ID, for
instance) is a real finding, but fixing it is Phase 3 work, not the doorway's.

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
    _open_spreadsheet,
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
        rest of the sheet. Every call site but one uses ``"A1"`` (whole-body
        replace); ``sync_params.py:258`` uses a computed anchor to write just
        the columns it inserted.

        ``raw=False`` (``generate_status_sheet.py``,
        ``generate_biuniqueness_stage1_sheet.py``) makes Sheets *parse* the
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

        Order is load-bearing: ``generate_sheets._reorder_system_tabs`` and
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
        ``updateDimensionProperties``, ``updateCells``, ``mergeCells``.

        **Not** the same endpoint as ``values_batch_update``.
        """

    def values_batch_update(self, body: Mapping[str, Any]) -> Any:
        """``spreadsheets.values.batchUpdate`` — cell *values* by A1 range.

        Body is ``{"valueInputOption": ..., "data": [{"range", "values"}, ...]}``.
        One caller: ``restructure_sheets._cascade_rename_pair_tab``.

        **Not** the same endpoint as ``batch_update``.
        """


class DriveDoorway(Protocol):
    """Session-level operations: spreadsheet lifecycle, Drive files, Docs."""

    # -- Spreadsheets -------------------------------------------------------
    def create_spreadsheet(self, title: str) -> SpreadsheetHandle: ...

    def open_spreadsheet(self, spreadsheet_id: str) -> SpreadsheetHandle:
        """Open by ID. **Always retried** (the one method that retries itself).

        This collapses the three inconsistently-retried open idioms found in
        the inventory (``_open_spreadsheet``, bare ``gc.open_by_key``, and
        ``refresh_dropdowns``'s bare-open-inside-``except Exception``) onto one
        always-retried path. Safe to unify because opening is an idempotent
        read.
        """

    # -- Drive files --------------------------------------------------------
    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict]:
        """Raw Drive query. Returns the ``files`` list.

        ``q`` is passed through unescaped, as today. Current callers build it
        by f-string interpolation of names and IDs; that is injection-shaped
        but not a live risk, since every interpolated value is internally
        generated. Flagged, not fixed — see the protocol surface doc.
        """

    def get_file(self, file_id: str, fields: str = "id") -> Dict: ...

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> str:
        """Create a Drive file; returns its ID.

        Covers both the metadata-only form (folders, Docs — pass a Google
        mimetype and no content) and the media-upload form (manifest.json,
        notebooks, PDFs).
        """

    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> None:
        """Update content and/or rename.

        ``name`` is deliberately independent of ``content``: the four existing
        "create-or-update a Drive file" implementations disagree on whether an
        update renames (``_upload_planars_config`` does not; the notebook and
        report uploaders do), and ``restructure_sheets`` renames without
        touching content at all. The doorway lets each caller choose rather than
        picking one as canonical — collapsing those four is deferred until
        after the migration, when snapshots exist to prove the collapse is safe.
        """

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        """Reparent a file (internally a get-parents then update)."""

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

    # -- Google Docs (collaborator notes) -----------------------------------
    def create_doc(self, name: str, parent_id: str) -> str: ...

    def get_doc_text(self, doc_id: str) -> str: ...

    def append_doc_text(self, doc_id: str, text: str) -> None: ...


# ---------------------------------------------------------------------------
# The live doorway
# ---------------------------------------------------------------------------

class GspreadDoorway:
    """The live doorway. Delegates to gspread / googleapiclient.

    Returns raw ``gspread.Spreadsheet`` and ``gspread.Worksheet`` objects as
    handles — they already satisfy ``SpreadsheetHandle``/``WorksheetHandle``,
    since the protocols were written to mirror gspread. No wrapper classes on
    the live path means no wrapper bugs on the live path.

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
        return _open_spreadsheet(self.gc, spreadsheet_id)

    # -- Drive files --------------------------------------------------------
    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict]:
        kwargs: Dict[str, Any] = {"q": q, "fields": fields}
        if page_size is not None:
            kwargs["pageSize"] = page_size
        return self.drive.files().list(**kwargs).execute().get("files", [])

    def get_file(self, file_id: str, fields: str = "id") -> Dict:
        return self.drive.files().get(fileId=file_id, fields=fields).execute()

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> str:
        body: Dict[str, Any] = {"name": name}
        if parents:
            body["parents"] = list(parents)
        if mimetype and content is None:
            # Metadata-only create (folder, Doc): the mimetype *is* the file type.
            body["mimeType"] = mimetype
        kwargs: Dict[str, Any] = {"body": body, "fields": "id"}
        if content is not None:
            kwargs["media_body"] = self._media(content, mimetype)
        return self.drive.files().create(**kwargs).execute()["id"]

    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> None:
        kwargs: Dict[str, Any] = {"fileId": file_id}
        if name is not None:
            kwargs["body"] = {"name": name}
        if content is not None:
            kwargs["media_body"] = self._media(content, mimetype)
        self.drive.files().update(**kwargs).execute()

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        _move_to_folder(self.drive, file_id, new_parent_id)

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

    # -- docs ---------------------------------------------------------------
    def create_doc(self, name: str, parent_id: str) -> str:
        return self.drive.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [parent_id],
            },
            fields="id",
        ).execute()["id"]

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

_doorway: Optional[DriveDoorway] = None


def get_doorway() -> DriveDoorway:
    """Return the active doorway, creating the real one on first use."""
    global _doorway
    if _doorway is None:
        _doorway = GspreadDoorway()
    return _doorway


def set_doorway(doorway: Optional[DriveDoorway]) -> None:
    """Install a doorway (or ``None`` to reset to the real one). Tests only."""
    global _doorway
    _doorway = doorway


def reset_doorway() -> None:
    """Drop the cached doorway so the next get_doorway() rebuilds it."""
    set_doorway(None)
