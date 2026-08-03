"""Shared assertions about a fake-doorway mutation log.

One rule lives here so far, and it is here because two commands got it wrong
independently. `refresh-dropdowns` wrote y/n dropdowns onto `Source` and
`Comments` (issue #272), and `update-sheets` wrote criterion descriptions onto
the same two columns (docs/data-layer-progress.md § Finding 10). Both had taken
a tab's column layout from the manifest, which is bookkeeping and goes stale,
rather than from the tab's own header.

Each command tested its own version of the check afterwards, in its own words.
Six other files in `coding/` still read `construction_params` from the manifest
and will need the same guard as they are migrated (#271), so it is written once
here instead of six more times.

The trailing columns come from `planar.yaml` via `generate_sheets`, not from a
hardcoded pair, so adding a trailing column there extends this check with it.

**This covers the wrong *column*, not the wrong *values*.** Finding 9 — adding
one row narrowing a whole tab's dropdowns from `[y, n, both, na]` to `[y, n]` —
writes to exactly the right columns and passes this check. Verified by putting
that bug back: only the per-command assertion caught it.

That split is deliberate. Checking the values would mean working out, in the
test, what each column *should* allow — which is the command's own job, so the
test would be restating the implementation and would agree with it whenever it
was wrong. The same trap as a fake that is wrong in the same way on both sides
of a before/after comparison (docs/data-layer-progress.md, 2026-08-02). So each
command asserts its own values against a case where right and wrong differ
visibly, and that stays per-command on purpose.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from coding.generate_sheets import _TRAILING_COLS


def _columns_written(payload: Dict[str, Any], header_width: int) -> range:
    """The 0-based columns a request touches. Absent bounds mean the whole row."""
    rng = payload.get("range", {})
    return range(rng.get("startColumnIndex", 0),
                 rng.get("endColumnIndex", header_width))


def _criterion_writes(mutations: List[Dict[str, Any]]):
    """Yield the requests that say "this column holds a criterion".

    Two request types make that claim: a dropdown of allowed values, and a
    hover note carrying a criterion's definition. Both belong only on criterion
    columns. Formatting requests carrying no note (freezing and bolding the
    header row) say nothing about a column's meaning and are not included.
    """
    for m in mutations:
        if m.get("op") != "batch_request":
            continue
        kind, payload = m["request_type"], m["payload"]
        if kind == "setDataValidation":
            yield m, payload, "dropdown"
        elif kind == "repeatCell" and "note" in payload.get("cell", {}):
            yield m, payload, "criterion note"


def assert_no_criterion_writes_onto_trailing_columns(doorway) -> None:
    """No dropdown and no criterion note may land on `Source` or `Comments`.

    These are the free-text columns an annotator writes prose in. A dropdown on
    one of them offers a value list where a sentence belongs; a criterion note
    on one of them describes a criterion the tab does not have.

    Writes past the end of the header are not asserted on here. They are a
    stronger form of the same mistake, but no command performs one today, so a
    rule against them would be untested — see `render_mutations.py`, which
    renders such a column as `BEYOND HEADER` for a reviewer to notice.
    """
    for m, payload, what in _criterion_writes(doorway.mutations):
        ws = (doorway.spreadsheet(m["spreadsheet"])
              ._worksheet_by_sheet_id(payload["range"]["sheetId"]))
        header = ws.row_values(1)
        for col in _columns_written(payload, len(header)):
            if col >= len(header):
                continue
            assert header[col] not in _TRAILING_COLS, (
                f"{what} written onto {header[col]!r} (column {col}) of "
                f"{ws.title!r} in {m['spreadsheet']}. That column is free text "
                f"an annotator writes prose in. Trailing columns: {_TRAILING_COLS}"
            )
