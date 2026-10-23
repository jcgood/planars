"""Locked tabs: the tabs on a class sheet that the tooling writes and nobody edits.

Phase 10 unit 2 (issue #271). Which tabs these are, where they sit and which
classes carry them is the `locked_tabs` registry in `schemas/planar.yaml`;
this module runs from it. Each tab is rebuilt from its source (the schemas,
the language's planar TSV) by `rebuild_locked_tabs`, which every command that
creates or reshapes a class sheet calls, and which `update-sheets --apply`
calls daily for every sheet in the manifest — so a tab is current within a
day of its source changing, whichever command changed it.

A rebuild writes only what differs (it reads the tab and compares first), so
the daily run makes no writes on a sheet that is already current. Every
locked tab is protected so that only the sheet's owner — the account the
tooling runs as — can edit it; an annotator who tries is told the tab is
generated. Before this (2026-10-12) the Planar Structure tab had been called
"read-only" since 2026-05-01 without ever being locked, and only some
commands refreshed it.

`locked_tab_contents` is the build itself (Instructions from the class's
schema entry, Planar Structure from the planar TSV), which `sheet_spec.py`
also reads. A rebuild removes a tab the class no longer carries.
`reorder_tabs` puts first-placed locked tabs first, then the constructions,
then last-placed locked tabs, then Status; `system_tab_titles()` is the one
list of non-construction tabs. Called by generate-sheets (creating a sheet and
adding constructions), restructure-sheets (both rebuild paths) and, daily, by
`update-sheets --apply`.

Adding a locked tab is one registry entry, plus a builder below if its
content is new. An unknown builder name, place or include rule hard-fails.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd

from planars.schema_values import STATUS_TAB

from .drive_doorway import SpreadsheetHandle
from .schemas import load_diagnostic_classes, load_planar_schema

# Shown to anyone who tries to edit a locked tab, and how a rebuild recognises
# a protection as its own.
PROTECTION_DESCRIPTION = (
    "Written by the planars tooling and rebuilt every day; "
    "edits here would be overwritten."
)

_PLACES = ("first", "last")
_INCLUDES = ("always", "opt_in")


def locked_tab_specs() -> List[Dict]:
    """The `locked_tabs` registry, checked. Raises ValueError on anything it
    cannot place, rather than guessing."""
    specs = load_planar_schema().get("locked_tabs")
    if not specs:
        raise ValueError("schemas/planar.yaml has no locked_tabs registry")
    titles = set()
    for spec in specs:
        title = spec.get("title")
        if not title or title in titles or title == STATUS_TAB:
            raise ValueError(f"locked_tabs: missing, repeated or reserved title {title!r}")
        titles.add(title)
        if spec.get("builder") not in _BUILDERS:
            raise ValueError(f"locked_tabs {title!r}: unknown builder {spec.get('builder')!r} "
                             f"(known: {', '.join(sorted(_BUILDERS))})")
        if spec.get("place") not in _PLACES:
            raise ValueError(f"locked_tabs {title!r}: place must be one of {_PLACES}")
        if spec.get("include") not in _INCLUDES:
            raise ValueError(f"locked_tabs {title!r}: include must be one of {_INCLUDES}")
        if spec["include"] == "opt_in" and not spec.get("opt_in_field"):
            raise ValueError(f"locked_tabs {title!r}: include: opt_in needs opt_in_field")
    return specs


def locked_tab_titles() -> List[str]:
    return [s["title"] for s in locked_tab_specs()]


def system_tab_titles() -> List[str]:
    """Every tab on a class sheet that is not a construction tab."""
    return locked_tab_titles() + [STATUS_TAB]


def _class_entry(class_name: str) -> Dict:
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    return classes.get(class_name, {})


def _included(spec: Dict, class_entry: Dict) -> bool:
    if spec["include"] == "always":
        return True
    return bool(class_entry.get(spec["opt_in_field"]))


# ---------------------------------------------------------------------------
# Builders: (class_entry, lang_id, planar_path) -> (rows, format(sheet_id, rows))
# ---------------------------------------------------------------------------

_INSTRUCTIONS_HEADINGS = ("DETAILS", "WHAT THIS TESTS", "HOW TO ANNOTATE")


def _instructions_rows(class_entry: Dict, lang_id: str, planar_path: Path) -> List[List[str]]:
    """What this class tests and how to annotate it.

    Every class gets one (issue #242: annotators need an unmissable place for
    "what does this tab want from me", not just a per-column hover note).
    Classes with a multi-stage depends_on workflow (nonpermutability,
    coreference, biuniqueness_deviations) get the staged how-to. Most classes
    have one implicit construction and no `constructions` entry at all — for
    those, WHAT THIS TESTS / HOW TO ANNOTATE (from applicability_conditions
    and required/optional_criteria) is the content, plus whatever
    sheet_instructions the coordinator wrote for the class.
    """
    display_name = class_entry.get("display_name", class_entry.get("name", "")).upper()
    sheet_instructions = class_entry.get("sheet_instructions", "").strip()
    applicability = class_entry.get("applicability_conditions", "").strip()
    required_criteria = class_entry.get("required_criteria") or []
    optional_criteria = class_entry.get("optional_criteria") or []
    constructions_schema = class_entry.get("constructions", [])

    rows: List[List[str]] = []
    rows.append([f"{display_name} — ANNOTATION INSTRUCTIONS"])
    rows.append([""])

    if applicability:
        rows.append(["WHAT THIS TESTS"])
        for line in applicability.splitlines():
            if line.strip():
                rows.append([f"  {line.strip()}"])
        rows.append([""])

    if not constructions_schema and (required_criteria or optional_criteria):
        rows.append(["HOW TO ANNOTATE"])
        rows.append([f"  Fill in each criterion column for every element row: {', '.join(required_criteria)}"])
        if optional_criteria:
            rows.append([f"  Optional, fill in only if relevant: {', '.join(optional_criteria)}"])
        rows.append(["  Leave a cell blank if unsure — mark 'na' only when the criterion genuinely does not apply."])
        rows.append([""])

    # Per-construction dependency-order section (multi-stage workflows only)
    for step, c in enumerate(constructions_schema, start=1):
        name = c.get("name", "")
        depends_on = c.get("depends_on")
        row_type = c.get("row_type", "element")

        rows.append([f"STEP {step} — {name}"])
        if row_type in ("pair_rows", "keyed_rows") and depends_on:
            rows.append([f"  This tab is generated after {depends_on} is imported."])
            rows.append([f"  Do NOT annotate it until the coordinator confirms regeneration is complete."])
        else:
            rows.append([f"  Annotate each element row in this tab."])
        # A tab another tab is generated from (the middle of a chain too, e.g.
        # biuniqueness_deviations' morphemes) has to be marked finished.
        if any(cc.get("depends_on") == name for cc in constructions_schema):
            rows.append([f"  When finished: mark '{name}' as 'ready-for-review' in the Status tab."])
            rows.append([f"  The coordinator will then regenerate the dependent tab."])
        rows.append([""])

    if sheet_instructions:
        rows.append(["DETAILS"])
        rows.append([""])
        for line in sheet_instructions.splitlines():
            rows.append([line])
    return rows


def _instructions_format(sheet_id: int, rows: List[List[str]]) -> List[Dict]:
    bold_rows = [0] + [
        i for i, r in enumerate(rows)
        if r and (r[0].startswith("STEP ") or r[0] in _INSTRUCTIONS_HEADINGS)
    ]
    return [
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r, "endRowIndex": r + 1,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }}
        for r in bold_rows
    ] + [
        {"repeatCell": {
            "range": {"sheetId": sheet_id},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 620},
            "fields": "pixelSize",
        }},
    ]


_PLANAR_REFERENCE_COLUMNS = ["Position", "Position_Name", "Position_Type", "Elements"]


def _planar_reference_rows(class_entry: Dict, lang_id: str, planar_path: Path) -> List[List[str]]:
    """Position number, name, type and elements, so annotators can look a
    position up without leaving the spreadsheet."""
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id]
    df = df.sort_values("Position", key=lambda s: pd.to_numeric(s, errors="coerce"))
    return [_PLANAR_REFERENCE_COLUMNS] + [
        [row.get(col, "") for col in _PLANAR_REFERENCE_COLUMNS] for _, row in df.iterrows()
    ]


def _planar_reference_format(sheet_id: int, rows: List[List[str]]) -> List[Dict]:
    return [
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
    ]


_Builder = Tuple[Callable[[Dict, str, Path], List[List[str]]],
                 Callable[[int, List[List[str]]], List[Dict]]]
_BUILDERS: Dict[str, _Builder] = {
    "instructions": (_instructions_rows, _instructions_format),
    "planar_reference": (_planar_reference_rows, _planar_reference_format),
}


# ---------------------------------------------------------------------------
# Rebuild
# ---------------------------------------------------------------------------

def _normalise(rows: List[List[str]]) -> List[List[str]]:
    """Rows as Sheets returns them: trailing blank cells and rows dropped."""
    out = []
    for row in rows:
        row = [str(v) for v in row]
        while row and row[-1] == "":
            row.pop()
        out.append(row)
    while out and not out[-1]:
        out.pop()
    return out


def _is_ours(protection: Dict, sheet_id: int) -> bool:
    rng = protection.get("range", {})
    whole_tab = set(rng) <= {"sheetId"} and rng.get("sheetId") == sheet_id
    return whole_tab and not protection.get("warningOnly") \
        and protection.get("description") == PROTECTION_DESCRIPTION


def locked_tab_contents(class_name: str, lang_id: str,
                        planar_path: Path) -> List[Tuple[Dict, List[List[str]]]]:
    """(registry entry, rows) for each locked tab this class carries, in
    registry order: what each tab should hold right now. The sheet spec reads
    this; rebuild_locked_tabs writes it."""
    class_entry = _class_entry(class_name)
    return [(spec, _BUILDERS[spec["builder"]][0](class_entry, lang_id, planar_path))
            for spec in locked_tab_specs() if _included(spec, class_entry)]


def rebuild_locked_tabs(
    spreadsheet: SpreadsheetHandle,
    class_name: str,
    lang_id: str,
    planar_path: Path,
    apply: bool = True,
) -> List[str]:
    """Bring every locked tab on one class sheet up to date and protected.

    Creates a tab that is missing, rewrites one whose content differs from
    what its builder produces now, deletes one this class no longer carries,
    and protects any that is not yet protected. Returns one line per change
    (made, or that would be made when ``apply`` is False); an empty list means
    the sheet was already current. Tab order is ``reorder_tabs``' job.
    """
    contents = {spec["title"]: rows
                for spec, rows in locked_tab_contents(class_name, lang_id, planar_path)}
    existing = {ws.title: ws for ws in spreadsheet.worksheets()}
    changes: List[str] = []
    for spec in locked_tab_specs():
        title = spec["title"]
        ws = existing.get(title)
        if title not in contents:
            if ws is not None:
                changes.append(f"{title}: remove (this class no longer carries it)")
                if apply:
                    spreadsheet.del_worksheet(ws)
            continue

        rows = contents[title]
        build_format = _BUILDERS[spec["builder"]][1]
        if ws is None:
            changes.append(f"{title}: create")
            if apply:
                width = max(len(r) for r in rows)
                ws = spreadsheet.add_worksheet(
                    title=title, rows=len(rows) + 2, cols=width + 1)
                _write(spreadsheet, ws, rows, build_format)
        elif _normalise(ws.get_all_values()) != _normalise(rows):
            changes.append(f"{title}: refresh (its source has changed)")
            if apply:
                ws.clear()
                _write(spreadsheet, ws, rows, build_format)

        if ws is None:
            changes.append(f"{title}: protect")  # dry run of a tab not yet created
            continue
        protections = spreadsheet.list_protected_ranges(ws.id)
        if not any(_is_ours(p, ws.id) for p in protections):
            changes.append(f"{title}: protect")
            if apply:
                spreadsheet.batch_update({"requests": [
                    {"addProtectedRange": {"protectedRange": {
                        "range": {"sheetId": ws.id},
                        "description": PROTECTION_DESCRIPTION,
                        "warningOnly": False,
                    }}}]})
    return changes


def _write(spreadsheet: SpreadsheetHandle, ws, rows: List[List[str]], build_format) -> None:
    width = max(len(r) for r in rows)
    padded = [list(r) + [""] * (width - len(r)) for r in rows]
    ws.update(padded, "A1")
    spreadsheet.batch_update({"requests": build_format(ws.id, rows)})


def reorder_tabs(spreadsheet: SpreadsheetHandle) -> None:
    """Locked tabs placed `first` lead (Instructions is the annotator's landing
    tab, easy to miss if buried at the end); then the construction tabs; then
    the locked tabs placed `last`; then Status. Each group in registry order."""
    all_ws = spreadsheet.worksheets()
    by_title = {ws.title: ws for ws in all_ws}
    specs = locked_tab_specs()
    first = [s["title"] for s in specs if s["place"] == "first"]
    last = [s["title"] for s in specs if s["place"] == "last"] + [STATUS_TAB]
    system = set(first) | set(last)
    ordered = ([by_title[t] for t in first if t in by_title]
               + [ws for ws in all_ws if ws.title not in system]
               + [by_title[t] for t in last if t in by_title])
    if [ws.title for ws in all_ws] != [ws.title for ws in ordered]:
        spreadsheet.reorder_worksheets(ordered)
