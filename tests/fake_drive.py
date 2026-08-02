"""In-memory fake for the Drive doorway, seeded from recorded fixtures.

Implements ``coding.drive_doorway.DriveDoorway`` (and the spreadsheet/worksheet
handle protocols) with no network, so every command can be exercised
end-to-end in tests. Phase 0a of docs/data-layer-implementation-plan.md.

**Built from recorded responses, not from the gspread documentation.** The
fixtures under ``tests/fixtures/drive_state/`` are raw captures of what the
live API actually returned (``python -m coding capture-drive-state``). The
behaviours below that look like guesses are not: each is stated in
docs/drive-protocol-surface.md § "Subtleties most likely to be guessed wrong",
and the central one — how ``get_all_values()`` shapes its response — is proved
against all 80 captured tabs by ``test_drive_doorway.py``'s replay test.

What the capture settled
------------------------
- Responses are **rectangular, never ragged**. An earlier, careful, plausible
  hypothesis said partially-filled annotation tabs come back ragged. All 80
  captured tabs contradict it. The fake does not synthesise raggedness.
- ``get_all_values()`` pads to the **used range**, which can be **narrower
  than the declared ``col_count``** — true of 10 of the 80 tabs. So
  ``generate_sheets``'s ``len(row) >= N`` guards defend against *short*
  responses, which are real, not ragged ones, which are not.
- Tab order is live UI order and is never sorted.

Deliberate fidelity limits (all loud, none silent)
--------------------------------------------------
- **Formulas are not evaluated.** A cell written with ``raw=False`` keeps its
  literal ``=HYPERLINK(...)`` text and is flagged ``formula=True``; a real
  Sheet would return the computed display value on read-back. Nothing in the
  codebase reads those cells back today (the status sheets are write-only), so
  this gap is recorded rather than modelled.
- **Unknown ``batch_update`` request types raise.** Silently ignoring an
  unmodelled request would make a snapshot pass while the real API did something
  the fake never did. If a new request type appears, this file must learn it.
- **Wrong-shaped bodies raise.** ``batch_update`` given ``{"data": ...}`` or
  ``values_batch_update`` given ``{"requests": ...}`` is an error, not a
  silently-accepted no-op. These are two different API endpoints and conflating
  them is the single most likely way a fake diverges from reality.
- **Writes past the declared grid are allowed but recorded.** The live API's
  exact behaviour here (auto-expand vs. 400) was not captured, so the fake
  expands and flags ``exceeded_grid`` in the mutation log rather than guessing
  a rejection that might fail writes production performs fine.

Mutation log
------------
Every write appends a JSON-serialisable record to ``doorway.mutations``. That
log is what the plan's per-file procedure has a human review before it becomes
a snapshot — write paths have no pre-migration baseline to diff against, so the
review is the only barrier between a migration bug and its enshrinement.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import gspread
import requests

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "drive_state"

_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_FOLDER_MIME = "application/vnd.google-apps.folder"
_DOC_MIME = "application/vnd.google-apps.document"

# Stable IDs for the two Drive objects every command bootstraps from. Real IDs
# live in the gitignored drive_config.json; tests patch _load_drive_config to
# return FakeDriveDoorway.drive_config(), which names these.
MANIFEST_FILE_ID = "fake_manifest_file"
ROOT_FOLDER_ID = "fake_root_folder"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def api_error(code: int, message: str, status: str = "INVALID_ARGUMENT") -> gspread.exceptions.APIError:
    """Build a real ``gspread.APIError`` so callers' except clauses still match.

    ``drive._with_retry`` inspects ``e.response.status_code``, so the fake must
    raise something that carries one — a bespoke exception class would slip
    past every retry and error-handling path the commands already have.
    """
    response = requests.Response()
    response.status_code = code
    response._content = json.dumps(
        {"error": {"code": code, "message": message, "status": status}}
    ).encode("utf-8")
    return gspread.exceptions.APIError(response)


# ---------------------------------------------------------------------------
# Cell model
# ---------------------------------------------------------------------------

@dataclass
class _Cell:
    """One cell's value and the formatting state the commands actually set."""
    value: str = ""
    formula: bool = False
    note: Optional[str] = None
    background: Optional[Dict[str, float]] = None
    bold: Optional[bool] = None
    wrap_strategy: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None

    def is_empty(self) -> bool:
        return (
            self.value == ""
            and self.note is None
            and self.background is None
            and self.bold is None
            and self.wrap_strategy is None
            and self.validation is None
        )


def _a1_anchor(range_name: str) -> Tuple[int, int]:
    """Return the 0-based (row, col) of a range's top-left cell.

    Accepts ``"A1"`` (every call site but one) and ``"A1:D5"``.
    """
    first = range_name.split("!")[-1].split(":")[0]
    row, col = gspread.utils.a1_to_rowcol(first)
    return row - 1, col - 1


def _sheet_prefix(range_name: str) -> Optional[str]:
    """Return the sheet-name part of an A1 range, or None if unprefixed.

    Unprefixed matters: the Sheets values API resolves a bare ``"D5"`` against
    the **first sheet** of the spreadsheet, not against whichever tab the
    caller had in hand. ``restructure_sheets._cascade_rename_pair_tab`` builds
    exactly such bare ranges, so the fake reproduces that resolution rather
    than helpfully routing the write to the tab the caller meant.
    """
    if "!" not in range_name:
        return None
    prefix = range_name.rsplit("!", 1)[0]
    return prefix.strip("'")


# ---------------------------------------------------------------------------
# Worksheet
# ---------------------------------------------------------------------------

class FakeWorksheet:
    """One tab. Method names, argument order, and index bases mirror gspread."""

    def __init__(self, spreadsheet: "FakeSpreadsheet", sheet_id: int, title: str,
                 row_count: int, col_count: int) -> None:
        self.spreadsheet = spreadsheet
        self.id = sheet_id
        self.title = title
        self.row_count = row_count
        self.col_count = col_count
        self._cells: Dict[Tuple[int, int], _Cell] = {}
        self.frozen_rows = 0
        self.merges: List[Dict[str, int]] = []
        self.dimension_pixel_sizes: Dict[Tuple[str, int], int] = {}

    # -- internals ----------------------------------------------------------
    def _record(self, op: str, **kw) -> None:
        self.spreadsheet._record(op, worksheet=self.title, **kw)

    def _cell(self, r: int, c: int) -> _Cell:
        cell = self._cells.get((r, c))
        if cell is None:
            cell = _Cell()
            self._cells[(r, c)] = cell
        return cell

    def _prune(self, r: int, c: int) -> None:
        cell = self._cells.get((r, c))
        if cell is not None and cell.is_empty():
            del self._cells[(r, c)]

    def _used_range(self) -> Tuple[int, int]:
        """(rows, cols) of the used range — driven by values only, not formats.

        Formatting a blank cell does not extend what ``get_all_values()``
        returns; only a non-empty value does.
        """
        rows = cols = 0
        for (r, c), cell in self._cells.items():
            if cell.value != "":
                rows = max(rows, r + 1)
                cols = max(cols, c + 1)
        return rows, cols

    def _value(self, r: int, c: int) -> str:
        cell = self._cells.get((r, c))
        return cell.value if cell else ""

    def _shift_cells(self, axis: str, start: int, delta: int) -> None:
        """Shift cells at or after ``start`` along ``axis`` by ``delta``.

        Used by insert/delete of rows and columns. Cells shifted off the
        negative side (a delete) are dropped, matching the API.
        """
        moved: Dict[Tuple[int, int], _Cell] = {}
        for (r, c), cell in self._cells.items():
            idx = r if axis == "ROWS" else c
            if idx < start:
                moved[(r, c)] = cell
                continue
            if delta < 0 and idx < start - delta:
                continue  # deleted outright
            if axis == "ROWS":
                moved[(r + delta, c)] = cell
            else:
                moved[(r, c + delta)] = cell
        self._cells = moved

    def _write(self, r: int, c: int, value: Any, raw: bool) -> None:
        text = "" if value is None else str(value)
        cell = self._cell(r, c)
        cell.value = text
        cell.formula = (not raw) and text.startswith("=")
        self._prune(r, c)

    def _grow_to(self, rows: int, cols: int, op: str) -> bool:
        """Expand the declared grid to fit a write. Returns True if it had to."""
        exceeded = rows > self.row_count or cols > self.col_count
        if exceeded:
            self.row_count = max(self.row_count, rows)
            self.col_count = max(self.col_count, cols)
        return exceeded

    # -- reads --------------------------------------------------------------
    def get_all_values(self) -> List[List[str]]:
        rows, cols = self._used_range()
        if rows == 0:
            return []
        return [[self._value(r, c) for c in range(cols)] for r in range(rows)]

    def row_values(self, row: int) -> List[str]:
        """``row`` is 1-based. Trimmed at this row's own last non-empty cell.

        No padding to the used width: gspread fetches a single-row range, so
        the response is only as wide as the row itself. (Unobservable in the
        captured fixtures — every captured header row is already the full used
        width — so this follows gspread's implementation rather than a
        recording.)
        """
        r = row - 1
        last = 0
        for (rr, c), cell in self._cells.items():
            if rr == r and cell.value != "":
                last = max(last, c + 1)
        return [self._value(r, c) for c in range(last)]

    # -- writes -------------------------------------------------------------
    def update(self, values: Sequence[Sequence[Any]], range_name: str = "A1",
               raw: bool = True) -> Dict[str, Any]:
        r0, c0 = _a1_anchor(range_name)
        max_r, max_c = r0, c0
        for i, row in enumerate(values):
            for j, value in enumerate(row):
                self._write(r0 + i, c0 + j, value, raw)
                max_r, max_c = max(max_r, r0 + i), max(max_c, c0 + j)
        exceeded = self._grow_to(max_r + 1, max_c + 1, "update")
        self._record(
            "update", range=range_name, raw=raw,
            rows=len(values), cols=max((len(r) for r in values), default=0),
            values=[[("" if v is None else str(v)) for v in row] for row in values],
            exceeded_grid=exceeded,
        )
        return {}

    def update_cell(self, row: int, col: int, value: Any) -> Dict[str, Any]:
        self._write(row - 1, col - 1, value, raw=True)
        self._grow_to(row, col, "update_cell")
        self._record("update_cell", row=row, col=col, value=str(value))
        return {}

    def insert_cols(self, values: Sequence[Sequence[Any]], col: int = 1) -> Dict[str, Any]:
        n = len(values)
        start = col - 1
        self._shift_cells("COLUMNS", start, n)
        for j, column in enumerate(values):
            for i, value in enumerate(column):
                self._write(i, start + j, value, raw=True)
        self.col_count += n
        self._record("insert_cols", col=col, n_columns=n,
                     values=[[str(v) for v in column] for column in values])
        return {}

    def append_rows(self, values: Sequence[Sequence[Any]],
                    value_input_option: str = "RAW") -> Dict[str, Any]:
        start, _ = self._used_range()
        for i, row in enumerate(values):
            for j, value in enumerate(row):
                self._write(start + i, j, value, raw=(value_input_option == "RAW"))
        exceeded = self._grow_to(
            start + len(values),
            max((len(r) for r in values), default=0),
            "append_rows",
        )
        self._record("append_rows", start_row=start + 1, n_rows=len(values),
                     value_input_option=value_input_option,
                     values=[[str(v) for v in row] for row in values],
                     exceeded_grid=exceeded)
        return {}

    def clear(self) -> Dict[str, Any]:
        """Values only. Formatting, notes, validation, and grid size survive."""
        for key in list(self._cells):
            self._cells[key].value = ""
            self._cells[key].formula = False
            self._prune(*key)
        self._record("clear")
        return {}

    def resize(self, rows: Optional[int] = None, cols: Optional[int] = None) -> Dict[str, Any]:
        if rows is not None:
            self.row_count = rows
        if cols is not None:
            self.col_count = cols
        for (r, c) in list(self._cells):
            if r >= self.row_count or c >= self.col_count:
                del self._cells[(r, c)]
        self._record("resize", rows=rows, cols=cols)
        return {}

    def update_title(self, title: str) -> Dict[str, Any]:
        if any(ws is not self and ws.title == title
               for ws in self.spreadsheet._worksheets):
            raise api_error(400, f'A sheet with the name "{title}" already exists.')
        old, self.title = self.title, title
        self.spreadsheet._record("update_title", worksheet=old, new_title=title)
        return {}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FakeWorksheet {self.spreadsheet.id}/{self.title!r} id={self.id}>"


# ---------------------------------------------------------------------------
# Spreadsheet
# ---------------------------------------------------------------------------

class FakeSpreadsheet:
    """One spreadsheet file, holding its tabs in live order."""

    def __init__(self, doorway: "FakeDriveDoorway", spreadsheet_id: str, title: str) -> None:
        self._doorway = doorway
        self.id = spreadsheet_id
        self.title = title
        self._worksheets: List[FakeWorksheet] = []

    @property
    def url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.id}"

    def _record(self, op: str, **kw) -> None:
        self._doorway._record(op, spreadsheet=self.id, **kw)

    def _next_sheet_id(self) -> int:
        return max((ws.id for ws in self._worksheets), default=-1) + 1

    # -- tabs ---------------------------------------------------------------
    @property
    def sheet1(self) -> FakeWorksheet:
        if not self._worksheets:
            raise api_error(400, "Spreadsheet has no sheets.")
        return self._worksheets[0]

    def worksheets(self) -> List[FakeWorksheet]:
        """Live tab order. Never sorted — reorder-detection depends on it."""
        return list(self._worksheets)

    def worksheet(self, title: str) -> FakeWorksheet:
        for ws in self._worksheets:
            if ws.title == title:
                return ws
        raise gspread.exceptions.WorksheetNotFound(title)

    def add_worksheet(self, title: str, rows: int, cols: int,
                      index: Optional[int] = None) -> FakeWorksheet:
        if any(ws.title == title for ws in self._worksheets):
            raise api_error(400, f'A sheet with the name "{title}" already exists.')
        ws = FakeWorksheet(self, self._next_sheet_id(), title, rows, cols)
        if index is None:
            self._worksheets.append(ws)
        else:
            self._worksheets.insert(index, ws)
        self._record("add_worksheet", worksheet=title, rows=rows, cols=cols,
                     index=index, sheet_id=ws.id)
        return ws

    def del_worksheet(self, worksheet: FakeWorksheet) -> None:
        self._worksheets = [ws for ws in self._worksheets if ws.id != worksheet.id]
        self._record("del_worksheet", worksheet=worksheet.title)

    def reorder_worksheets(self, worksheets_in_desired_order: Sequence[FakeWorksheet]) -> None:
        desired = list(worksheets_in_desired_order)
        if {ws.id for ws in desired} != {ws.id for ws in self._worksheets}:
            raise api_error(
                400, "reorder_worksheets requires every sheet of this spreadsheet exactly once.")
        self._worksheets = desired
        self._record("reorder_worksheets", order=[ws.title for ws in desired])

    def _worksheet_by_sheet_id(self, sheet_id: int) -> FakeWorksheet:
        for ws in self._worksheets:
            if ws.id == sheet_id:
                return ws
        raise api_error(400, f"No sheet with id: {sheet_id}")

    # -- batch endpoints ----------------------------------------------------
    def batch_update(self, body: Mapping[str, Any]) -> Dict[str, Any]:
        """``spreadsheets.batchUpdate`` — structural/formatting requests."""
        if "requests" not in body:
            raise api_error(
                400,
                "batch_update expects {'requests': [...]} (spreadsheets.batchUpdate). "
                "A body with 'data' belongs to values_batch_update — a different endpoint.",
            )
        for request in body["requests"]:
            self._apply_request(request)
        return {"replies": [{} for _ in body["requests"]]}

    def values_batch_update(self, body: Mapping[str, Any]) -> Dict[str, Any]:
        """``spreadsheets.values.batchUpdate`` — cell values by A1 range."""
        if "data" not in body:
            raise api_error(
                400,
                "values_batch_update expects {'valueInputOption': ..., 'data': [...]} "
                "(spreadsheets.values.batchUpdate). A body with 'requests' belongs to "
                "batch_update — a different endpoint.",
            )
        raw = body.get("valueInputOption", "RAW") == "RAW"
        for entry in body["data"]:
            range_name = entry["range"]
            prefix = _sheet_prefix(range_name)
            # An unprefixed range resolves against the FIRST sheet, not the tab
            # the caller was holding. Faithful, and a live oddity — see the
            # module docstring for _sheet_prefix.
            ws = self.worksheet(prefix) if prefix else self.sheet1
            r0, c0 = _a1_anchor(range_name)
            for i, row in enumerate(entry["values"]):
                for j, value in enumerate(row):
                    ws._write(r0 + i, c0 + j, value, raw)
            ws._grow_to(r0 + len(entry["values"]), c0 + 1, "values_batch_update")
        self._record("values_batch_update",
                     value_input_option=body.get("valueInputOption", "RAW"),
                     data=[{"range": e["range"], "values": e["values"]} for e in body["data"]])
        return {}

    # -- request dispatch ---------------------------------------------------
    def _apply_request(self, request: Mapping[str, Any]) -> None:
        if len(request) != 1:
            raise api_error(400, f"Each request must name exactly one operation: {request!r}")
        (kind, payload), = request.items()
        handler = getattr(self, f"_req_{kind}", None)
        if handler is None:
            raise NotImplementedError(
                f"FakeSpreadsheet does not model the {kind!r} batch_update request. "
                "Add it here rather than letting it pass silently — an unmodelled "
                "request makes snapshots agree with a fake that did nothing. "
                f"Modelled: {sorted(m[5:] for m in dir(self) if m.startswith('_req_'))}."
            )
        handler(payload)
        self._record("batch_request", request_type=kind, payload=payload)

    def _range_cells(self, grid_range: Mapping[str, Any]) -> Tuple[FakeWorksheet, range, range]:
        """Resolve a GridRange to (worksheet, rows, cols). Indices are 0-based.

        Omitted bounds mean "unbounded" in the API, which resolves to the whole
        declared grid — not to the used range.
        """
        ws = self._worksheet_by_sheet_id(grid_range["sheetId"])
        rows = range(grid_range.get("startRowIndex", 0),
                     grid_range.get("endRowIndex", ws.row_count))
        cols = range(grid_range.get("startColumnIndex", 0),
                     grid_range.get("endColumnIndex", ws.col_count))
        return ws, rows, cols

    @staticmethod
    def _apply_cell_format(cell: _Cell, spec: Mapping[str, Any], fields: str) -> None:
        """Apply a CellData spec, honouring the request's ``fields`` mask."""
        wanted = [f.strip() for f in fields.split(",")] if fields else ["*"]

        def selected(path: str) -> bool:
            return any(f == "*" or path == f or path.startswith(f + ".") or f.startswith(path + ".")
                       for f in wanted)

        fmt = spec.get("userEnteredFormat", {})
        if selected("userEnteredFormat.backgroundColor") and "backgroundColor" in fmt:
            cell.background = fmt["backgroundColor"]
        if selected("userEnteredFormat.textFormat.bold") and "bold" in fmt.get("textFormat", {}):
            cell.bold = fmt["textFormat"]["bold"]
        if selected("userEnteredFormat.wrapStrategy") and "wrapStrategy" in fmt:
            cell.wrap_strategy = fmt["wrapStrategy"]
        if selected("note") and "note" in spec:
            cell.note = spec["note"]

    # Each _req_* below models one request type actually used by coding/.
    def _req_updateSheetProperties(self, payload: Mapping[str, Any]) -> None:
        props = payload["properties"]
        ws = self._worksheet_by_sheet_id(props["sheetId"])
        fields = payload.get("fields", "*")
        grid = props.get("gridProperties", {})
        if "frozenRowCount" in grid and ("*" in fields or "frozenRowCount" in fields):
            ws.frozen_rows = grid["frozenRowCount"]
        if "rowCount" in grid and ("*" in fields or "rowCount" in fields):
            ws.row_count = grid["rowCount"]
        if "columnCount" in grid and ("*" in fields or "columnCount" in fields):
            ws.col_count = grid["columnCount"]
        if "title" in props and ("*" in fields or "title" in fields):
            ws.title = props["title"]

    def _req_repeatCell(self, payload: Mapping[str, Any]) -> None:
        ws, rows, cols = self._range_cells(payload["range"])
        for r in rows:
            for c in cols:
                self._apply_cell_format(ws._cell(r, c), payload.get("cell", {}),
                                        payload.get("fields", "*"))
                ws._prune(r, c)

    def _req_updateCells(self, payload: Mapping[str, Any]) -> None:
        ws, rows, cols = self._range_cells(payload["range"])
        fields = payload.get("fields", "*")
        for i, r in enumerate(rows):
            row_spec = payload.get("rows", [])
            values = row_spec[i]["values"] if i < len(row_spec) else []
            for j, c in enumerate(cols):
                if j >= len(values):
                    continue
                cell_spec = values[j]
                self._apply_cell_format(ws._cell(r, c), cell_spec, fields)
                if "userEnteredValue" in cell_spec and ("*" in fields or "userEnteredValue" in fields):
                    entered = cell_spec["userEnteredValue"]
                    ws._cell(r, c).value = str(
                        entered.get("stringValue", entered.get("formulaValue", "")))
                ws._prune(r, c)

    def _req_setDataValidation(self, payload: Mapping[str, Any]) -> None:
        ws, rows, cols = self._range_cells(payload["range"])
        rule = payload.get("rule")
        for r in rows:
            for c in cols:
                ws._cell(r, c).validation = rule
                ws._prune(r, c)

    def _req_insertDimension(self, payload: Mapping[str, Any]) -> None:
        rng = payload["range"]
        ws = self._worksheet_by_sheet_id(rng["sheetId"])
        n = rng["endIndex"] - rng["startIndex"]
        ws._shift_cells(rng["dimension"], rng["startIndex"], n)
        if rng["dimension"] == "ROWS":
            ws.row_count += n
        else:
            ws.col_count += n

    def _req_deleteDimension(self, payload: Mapping[str, Any]) -> None:
        rng = payload["range"]
        ws = self._worksheet_by_sheet_id(rng["sheetId"])
        n = rng["endIndex"] - rng["startIndex"]
        ws._shift_cells(rng["dimension"], rng["startIndex"], -n)
        if rng["dimension"] == "ROWS":
            ws.row_count = max(ws.row_count - n, 1)
        else:
            ws.col_count = max(ws.col_count - n, 1)

    def _req_updateDimensionProperties(self, payload: Mapping[str, Any]) -> None:
        rng = payload["range"]
        ws = self._worksheet_by_sheet_id(rng["sheetId"])
        size = payload.get("properties", {}).get("pixelSize")
        for idx in range(rng["startIndex"], rng["endIndex"]):
            ws.dimension_pixel_sizes[(rng["dimension"], idx)] = size

    def _req_mergeCells(self, payload: Mapping[str, Any]) -> None:
        rng = payload["range"]
        ws = self._worksheet_by_sheet_id(rng["sheetId"])
        merge = {k: v for k, v in rng.items() if k != "sheetId"}
        # mergeType is a sibling of "range" in the request, not part of it.
        merge["mergeType"] = payload.get("mergeType", "MERGE_ALL")
        ws.merges.append(merge)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FakeSpreadsheet {self.id} {self.title!r} tabs={len(self._worksheets)}>"


# ---------------------------------------------------------------------------
# Drive query parsing
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^name\s*=\s*'(?P<v>.*)'$")
_MIME_RE = re.compile(r"^mimeType\s*=\s*'(?P<v>.*)'$")
_TRASHED_RE = re.compile(r"^trashed\s*=\s*(?P<v>true|false)$")
_PARENT_RE = re.compile(r"^'(?P<v>[^']*)'\s+in\s+parents$")


def _parse_query(q: str) -> Dict[str, Any]:
    """Parse the Drive ``q`` strings this codebase builds. Raises on anything else.

    Every query in ``coding/`` is a conjunction of at most four clause types.
    An unrecognised clause raises rather than being ignored, so a fake never
    silently returns "no match" for a query it did not understand.
    """
    parsed: Dict[str, Any] = {}
    for clause in [c.strip() for c in q.split(" and ")]:
        if not clause:
            continue
        for key, pattern in (("name", _NAME_RE), ("mimeType", _MIME_RE),
                             ("trashed", _TRASHED_RE), ("parent", _PARENT_RE)):
            match = pattern.match(clause)
            if match:
                parsed[key] = match.group("v")
                break
        else:
            raise NotImplementedError(
                f"FakeDriveDoorway cannot parse Drive query clause {clause!r} "
                f"(from q={q!r}). Teach _parse_query about it rather than "
                "letting the query silently match nothing."
            )
    return parsed


# ---------------------------------------------------------------------------
# Doorway
# ---------------------------------------------------------------------------

@dataclass
class _DriveFile:
    id: str
    name: str
    mimetype: str
    parents: List[str] = field(default_factory=list)
    content: Optional[bytes] = None
    trashed: bool = False
    # RFC 3339, as Drive returns it. Not captured by capture-drive-state, so
    # it is None unless a test sets it — and then get_file omits the field
    # entirely, which is what a real response does for a field never asked for.
    # prune_manifest reads it to warn before archiving a recently-edited sheet;
    # without it here that warning could not be exercised at all.
    modified_time: Optional[str] = None


class FakeDriveDoorway:
    """In-memory ``DriveDoorway``. Deterministic IDs; records every mutation."""

    def __init__(self) -> None:
        self.mutations: List[Dict[str, Any]] = []
        self._spreadsheets: Dict[str, FakeSpreadsheet] = {}
        self._files: Dict[str, _DriveFile] = {}
        self._permissions: Dict[str, List[Dict[str, Any]]] = {}
        self._docs: Dict[str, str] = {}
        self._counter = 0

    # -- construction -------------------------------------------------------
    @classmethod
    def from_fixtures(cls, fixture_dir: Path = FIXTURE_DIR,
                      langs: Optional[Sequence[str]] = None) -> "FakeDriveDoorway":
        """Seed from ``capture-drive-state`` output, per its ``index.json``.

        Loads the recorded spreadsheets, the recorded ``manifest.json`` (as a
        downloadable Drive file under a root folder), and a folder per language
        at the ``folder_id`` the manifest names — enough Drive shape for a
        command to bootstrap exactly as it does live.
        """
        doorway = cls()
        doorway.seed_folder("planars", file_id=ROOT_FOLDER_ID)
        index = json.loads((fixture_dir / "index.json").read_text(encoding="utf-8"))
        for entry in index["spreadsheets"]:
            if langs is not None and entry["lang_id"] not in langs:
                continue
            path = ROOT / entry["path"]
            doorway.seed_spreadsheet(json.loads(path.read_text(encoding="utf-8")))

        manifest_path = fixture_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if langs is not None:
                manifest = {k: v for k, v in manifest.items() if k in langs}
            doorway.seed_json_file("manifest.json", manifest, [ROOT_FOLDER_ID],
                                   file_id=MANIFEST_FILE_ID)
            for lang_id, entry in manifest.items():
                if isinstance(entry, dict) and entry.get("folder_id"):
                    doorway.seed_folder(lang_id, ROOT_FOLDER_ID,
                                        file_id=entry["folder_id"])
        return doorway

    @staticmethod
    def drive_config() -> Dict[str, str]:
        """The bootstrap dict commands read from drive_config.json."""
        return {"_root_folder_id": ROOT_FOLDER_ID,
                "_planars_config_file_id": MANIFEST_FILE_ID}

    def seed_spreadsheet(self, data: Mapping[str, Any]) -> FakeSpreadsheet:
        """Load one captured spreadsheet exactly as recorded. No tidying."""
        ss = FakeSpreadsheet(self, data["spreadsheet_id"], data["title"])
        for tab in data["worksheets"]:
            ws = FakeWorksheet(ss, tab["sheet_id"], tab["title"],
                               tab["row_count"], tab["col_count"])
            for r, row in enumerate(tab["values"]):
                for c, value in enumerate(row):
                    if value != "":
                        ws._cell(r, c).value = value
            ss._worksheets.append(ws)
        self._spreadsheets[ss.id] = ss
        self._files[ss.id] = _DriveFile(ss.id, ss.title, _SPREADSHEET_MIME)
        return ss

    def seed_file(self, name: str, mimetype: str, parents: Sequence[str] = (),
                  content: Optional[bytes] = None,
                  file_id: Optional[str] = None,
                  modified_time: Optional[str] = None) -> str:
        file_id = file_id or self._new_id("file")
        self._files[file_id] = _DriveFile(file_id, name, mimetype, list(parents),
                                          content, modified_time=modified_time)
        return file_id

    def seed_folder(self, name: str, parent_id: Optional[str] = None,
                    file_id: Optional[str] = None) -> str:
        return self.seed_file(name, _FOLDER_MIME,
                              [parent_id] if parent_id else [], file_id=file_id)

    def seed_json_file(self, name: str, data: Any, parents: Sequence[str] = (),
                       file_id: Optional[str] = None) -> str:
        return self.seed_file(name, "application/json", parents,
                              json.dumps(data).encode("utf-8"), file_id)

    def seed_doc(self, name: str, text: str = "", parent_id: Optional[str] = None,
                 file_id: Optional[str] = None) -> str:
        doc_id = self.seed_file(name, _DOC_MIME,
                                [parent_id] if parent_id else [], file_id=file_id)
        self._docs[doc_id] = text
        return doc_id

    # -- inspection ---------------------------------------------------------
    def spreadsheet(self, spreadsheet_id: str) -> FakeSpreadsheet:
        """Direct state access for assertions (not part of the protocol)."""
        return self._spreadsheets[spreadsheet_id]

    def file(self, file_id: str) -> _DriveFile:
        return self._files[file_id]

    def mutations_of(self, op: str) -> List[Dict[str, Any]]:
        return [m for m in self.mutations if m["op"] == op]

    def clear_mutations(self) -> None:
        self.mutations.clear()

    # -- internals ----------------------------------------------------------
    def _new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"fake_{prefix}_{self._counter:04d}"

    def _record(self, op: str, **kw) -> None:
        self.mutations.append({"op": op, **kw})

    def _require_file(self, file_id: str) -> _DriveFile:
        try:
            return self._files[file_id]
        except KeyError:
            raise api_error(404, f"File not found: {file_id}.", "NOT_FOUND") from None

    # -- spreadsheets -------------------------------------------------------
    def create_spreadsheet(self, title: str) -> FakeSpreadsheet:
        ss = FakeSpreadsheet(self, self._new_id("ss"), title)
        # A new Google spreadsheet arrives with one 1000x26 tab called Sheet1,
        # sheetId 0 — several callers delete it once their own tabs exist.
        ss._worksheets.append(FakeWorksheet(ss, 0, "Sheet1", 1000, 26))
        self._spreadsheets[ss.id] = ss
        self._files[ss.id] = _DriveFile(ss.id, title, _SPREADSHEET_MIME)
        self._record("create_spreadsheet", spreadsheet=ss.id, title=title)
        return ss

    def open_spreadsheet(self, spreadsheet_id: str) -> FakeSpreadsheet:
        try:
            return self._spreadsheets[spreadsheet_id]
        except KeyError:
            raise gspread.exceptions.SpreadsheetNotFound(
                f"fake doorway has no spreadsheet {spreadsheet_id}") from None

    # -- Drive files --------------------------------------------------------
    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict[str, Any]]:
        parsed = _parse_query(q)
        matches = []
        for f in self._files.values():
            if "name" in parsed and f.name != parsed["name"]:
                continue
            if "mimeType" in parsed and f.mimetype != parsed["mimeType"]:
                continue
            if "trashed" in parsed and f.trashed != (parsed["trashed"] == "true"):
                continue
            if "parent" in parsed and parsed["parent"] not in f.parents:
                continue
            matches.append({"id": f.id, "name": f.name})
        return matches[:page_size] if page_size else matches

    def get_file(self, file_id: str, fields: str = "id",
                 supports_all_drives: bool = False) -> Dict[str, Any]:
        """Metadata. ``supports_all_drives`` is accepted and ignored.

        Ignoring it is right rather than lazy: the fake has no shared drives,
        so every file is reachable either way, and modelling a refusal would
        invent a failure the recording never showed.
        """
        f = self._require_file(file_id)
        meta = {"id": f.id, "name": f.name, "parents": list(f.parents),
                "trashed": f.trashed, "mimeType": f.mimetype}
        if f.modified_time is not None:
            meta["modifiedTime"] = f.modified_time
        return meta

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> str:
        file_id = self._new_id("file")
        self._files[file_id] = _DriveFile(
            file_id, name, mimetype or "application/octet-stream",
            list(parents or []), content)
        self._record("create_file", file_id=file_id, name=name,
                     parents=list(parents or []), mimetype=mimetype,
                     bytes=len(content) if content is not None else None)
        return file_id

    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> None:
        f = self._require_file(file_id)
        if name is not None:
            f.name = name
            if file_id in self._spreadsheets:
                self._spreadsheets[file_id].title = name
        if content is not None:
            f.content = content
            if mimetype:
                f.mimetype = mimetype
        self._record("update_file", file_id=file_id, name=name,
                     bytes=len(content) if content is not None else None)

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        f = self._require_file(file_id)
        previous = list(f.parents)
        f.parents = [new_parent_id]
        self._record("move_file", file_id=file_id, from_parents=previous,
                     to_parent=new_parent_id)

    def download_file_json(self, file_id: str) -> Any:
        f = self._require_file(file_id)
        if f.content is None:
            raise api_error(400, f"File {file_id} has no downloadable content.")
        return json.loads(f.content.decode("utf-8"))

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        parent_clause = f" and '{parent_id}' in parents" if parent_id else ""
        found = self.list_files(
            f"name='{name}' and mimeType='{_FOLDER_MIME}' and trashed=false{parent_clause}")
        if found:
            return found[0]["id"]
        # One Drive call, one entry in the log. Creating a folder *is* creating
        # a file with the folder mimetype — Drive has no separate endpoint — so
        # create_file above has already recorded it. A second "create_folder"
        # entry made one call look like two, which is exactly the wrong thing
        # for a log whose whole job is to say what changed.
        return self.create_file(name, [parent_id] if parent_id else [],
                                mimetype=_FOLDER_MIME)

    # -- permissions --------------------------------------------------------
    def list_permissions(self, file_id: str,
                         fields: str = "permissions(id,type)") -> List[Dict[str, Any]]:
        self._require_file(file_id)
        return [dict(p) for p in self._permissions.get(file_id, [])]

    def create_permission(self, file_id: str, type: str, role: str,
                          email: Optional[str] = None,
                          notify: bool = False) -> str:
        self._require_file(file_id)
        perm_id = self._new_id("perm")
        perm = {"id": perm_id, "type": type, "role": role}
        if email:
            perm["emailAddress"] = email
        self._permissions.setdefault(file_id, []).append(perm)
        self._record("create_permission", file_id=file_id, type=type, role=role,
                     email=email, notify=notify)
        return perm_id

    def delete_permission(self, file_id: str, permission_id: str) -> None:
        self._permissions[file_id] = [
            p for p in self._permissions.get(file_id, []) if p["id"] != permission_id]
        self._record("delete_permission", file_id=file_id, permission_id=permission_id)

    # -- docs ---------------------------------------------------------------
    def create_doc(self, name: str, parent_id: str) -> str:
        doc_id = self.create_file(name, [parent_id], mimetype=_DOC_MIME)
        self._docs[doc_id] = ""
        self._record("create_doc", file_id=doc_id, name=name, parent=parent_id)
        return doc_id

    def get_doc_text(self, doc_id: str) -> str:
        if doc_id not in self._docs:
            raise api_error(404, f"Document not found: {doc_id}.", "NOT_FOUND")
        return self._docs[doc_id]

    def append_doc_text(self, doc_id: str, text: str) -> None:
        current = self.get_doc_text(doc_id)
        self._docs[doc_id] = current + "\n" + text
        self._record("append_doc_text", file_id=doc_id, text=text)
