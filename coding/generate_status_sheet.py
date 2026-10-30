#!/usr/bin/env python3
"""Generate a locked, read-only Annotation Status sheet, one per language.

Collaborators (e.g. Adam) need a simple way to find current Google Sheets links
and see completion status without hunting through Drive or asking the
coordinator each time. This command builds one read-only spreadsheet per
language — `status_{lang_id}` — listing every construction from
diagnostics_{lang_id}.yaml with a completeness percentage, a color-coded
status cell, and a direct link to that construction's live tab.

The spreadsheets live in a dedicated top-level Drive folder named
"Annotation Status" — a *freestanding* folder (parent = Drive root), not a
child of the project's root folder. This is required, not incidental:
permissions on the root folder cascade to every file inside it, Google's API
refuses to remove an *inherited* permission at a child level, and annotators
hold edit access on the root (they edit the annotation sheets in it). Inside
it, a status sheet could not be made read-only. Outside it, the normal
remove/add-permission calls work. (The root folder's former "anyone with the
link" grant was removed 2026-10-12, Phase 10 unit 14; that does not change
this reasoning.)

Run from the repo root:
    python -m coding generate-status-sheet                      # dry run, all languages
    python -m coding generate-status-sheet --lang stan1293      # dry run, one language
    python -m coding generate-status-sheet --lang stan1293 --apply

Locking: each spreadsheet is shared read-only with its language's
annotator, by name, and the "Annotation Status" folder with every
language's annotator (addresses from private planars-data, via
`coding/people.py`); any "anyone with the link" permission is removed (defensive — freestanding files shouldn't have one,
but Drive occasionally adds one by default on creation). The coordinator's
OAuth identity owns every file as creator and needs no explicit permission.

The percentage for each construction is re-read from the live class sheet on
every run (so it tracks pair-row regeneration), using
``validate_coding.annotation_status`` for element-row tabs,
``pair_annotation_status`` for pair-row tabs and ``keyed_annotation_status``
for keyed-row tabs; ``restructure_sheets._get_pair_row_constructions`` /
``_get_keyed_row_constructions`` only decide which of them applies. A
spreadsheet created for a status sheet is found or made with
``drive.get_or_create_spreadsheet``. Which class sheets exist, and each
language's folder, come from the ID file (drive_config.json); a status sheet's
ID is recorded there (``drive_ids.set_status_sheet_id``) for the commands that
link to it. The daily refresh rebuilds every status
sheet after ``update-sheets``, so the percentages never lag the sheets.

Re-running with --apply overwrites the existing status_{lang_id} spreadsheet
in place (found by name within the folder) rather than minting a new URL —
unlike restructure-sheets, there is no annotation history to preserve here,
so a stable bookmarkable link is preferable. What the finished sheet must
hold (one `Status` tab, every construction of the diagnostics file in order,
nothing protected) is `sheet_spec.status_sheet_spec`, which the Drive door
checks at the end of the run. Each run cuts the tab to its new rows before
writing, so no row of a construction the language has lost survives.

A class spreadsheet that cannot be opened, or a diagnostics file that cannot
be read, leaves that language's status sheet wrong. The run finishes the
other languages, then exits non-zero naming each problem; the daily refresh
turns that into a `status-sheet-error` issue.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import (
    get_or_create_spreadsheet,
    ensure_user_permission,
    remove_anyone_permission,
    _load_drive_config,
    _save_drive_config,
)
from .drive_doorway import WorksheetNotFound, get_doorway
from . import drive_door, drive_ids
from .people import annotator_email
from .make_forms import (
    _read_diagnostics_for_language,
    resolve_keystone_active,
    resolve_keystone_na_criteria,
)
from .restructure_sheets import _get_keyed_row_constructions, _get_pair_row_constructions
from .validate_coding import (
    annotation_status, keyed_annotation_status, pair_annotation_status,
)
from .schemas import criteria_for
from .sheet_spec import STATUS_FOLDER_NAME as _STATUS_FOLDER_NAME
from .sheet_spec import STATUS_SHEET_COLUMNS
from planars.languages import get_display_name
from planars.schema_values import STATUS_TAB

# Pastel palette matching the pink/white highlighting convention already used
# by validate_coding.py's pink-cell error highlighting.
_GREEN  = {"red": 0.72, "green": 0.88, "blue": 0.72}
_YELLOW = {"red": 1.00, "green": 0.95, "blue": 0.60}
_GRAY   = {"red": 0.90, "green": 0.90, "blue": 0.90}

# The columns are the sheet spec's (sheet_spec.STATUS_SHEET_COLUMNS), which
# the Drive door checks the written sheet against.
_HEADER = list(STATUS_SHEET_COLUMNS)


# ---------------------------------------------------------------------------
# Pure logic: completeness -> status text / color (no API calls; unit tested)
# ---------------------------------------------------------------------------

def _completeness_pct(filled: int, total: int) -> Optional[float]:
    """Return percent complete, or None if there are no annotatable cells (total<=0)."""
    if total <= 0:
        return None
    return 100.0 * filled / total


def _status_color(pct: Optional[float]) -> Dict[str, float]:
    """Map a completeness percentage to a pastel background color.

    Two tiers plus gray: a construction is either fully done (100% -> green)
    or not yet done (anything below 100% -> yellow). There is no separate
    "close but not done" red tier -- the status text next to the cell already
    shows the actual percentage, so a third color wouldn't add information,
    it would just make "not 100% yet" look more alarming than it is at, say,
    95%. None (no annotatable cells, or no live sheet found) is neutral gray.
    """
    if pct is None:
        return _GRAY
    if pct >= 100:
        return _GREEN
    return _YELLOW


def _status_text(filled: int, total: int) -> str:
    """Render a human-readable completeness string, e.g. '128/142 filled (90%)'."""
    if total <= 0:
        return "0/0 filled (n/a)"
    pct = round(100.0 * filled / total)
    return f"{filled}/{total} filled ({pct}%)"


def _row_status(status: Dict[str, int]) -> Tuple[str, Dict[str, float]]:
    """Return (status_text, color) for one construction row.

    Pair-row constructions (nonpermutability's `general`, coreference's
    `reflexive_coreference`/`pronoun_coreference`/`np_coreference`) are generated
    combinatorially from element pairs rather than from positions, but each
    pair row still has the same criterion cells an element row has, so the
    same filled/total percentage applies. The caller picks which counting
    function built `status` -- annotation_status() for element rows,
    pair_annotation_status() for pair rows -- this just formats the result
    the same way for both.
    """
    text = _status_text(status.get("filled", 0), status.get("total", 0))
    color = _status_color(_completeness_pct(status.get("filled", 0), status.get("total", 0)))
    return text, color


def _missing_sheet_status() -> Tuple[str, Dict[str, float]]:
    """Status/color for a construction with no live sheet tab found."""
    return "no sheet found", _GRAY


# ---------------------------------------------------------------------------
# Row skeleton (pure logic: no API calls; unit tested)
# ---------------------------------------------------------------------------

def _build_row_skeletons(
    specs: List[Tuple[str, str, List[str], Dict[str, List[str]]]],
    pair_row_constructions: Dict[str, Set[str]],
) -> List[Dict]:
    """Return one row skeleton per (class, construction) in diagnostics YAML order.

    Pure transform of _read_diagnostics_for_language() output — no API calls —
    so it's directly unit-testable. Each skeleton carries what's needed to look
    up live sheet data next: class/construction names, expected param names/
    values, and whether the construction is a pair-row or keyed-row tab
    (decides which counting function _gather_status_rows() uses —
    annotation_status(), pair_annotation_status() or keyed_annotation_status()
    — all three feed the same percentage formula).
    """
    keyed_row_constructions = _get_keyed_row_constructions()
    skeletons = []
    for class_name, construction, param_names, param_values in specs:
        is_pair = construction in pair_row_constructions.get(class_name, set())
        skeletons.append({
            "class_name": class_name,
            "construction": construction,
            "param_names": param_names,
            "param_values": param_values,
            "is_pair": is_pair,
            # keyed_rows tabs (biuniqueness_deviations, #254) are counted by
            # keyed_annotation_status(); None for every other shape.
            "keyed": keyed_row_constructions.get(class_name, {}).get(construction),
        })
    return skeletons


# ---------------------------------------------------------------------------
# Live-sheet lookups (API calls — not unit tested; see docs/tooling-design.md)
# ---------------------------------------------------------------------------

def _construction_params(
    lang_id: str,
    class_name: str,
    construction: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    lang_setup_dir: Path,
) -> Tuple[List[str], Dict[str, List[str]], bool, List[str]]:
    """Resolve (params, values, keystone_active, keystone_na_criteria) for annotation_status().

    Each tab's criteria come from coding.schemas.criteria_for, the same rule
    validate-coding uses, so status counts agree with the pink highlighting
    annotators see. Coreference tabs don't consult the keystone settings.
    """
    param_names, param_values = criteria_for(class_name, construction, param_names,
                                             param_values, lang_id)
    if class_name == "coreference":
        return param_names, param_values, False, []
    keystone_active = resolve_keystone_active(lang_id, class_name, construction, data_dir=lang_setup_dir)
    if keystone_active is None:
        keystone_active = False
    keystone_na_criteria = resolve_keystone_na_criteria(class_name)
    return param_names, param_values, keystone_active, keystone_na_criteria


def _gather_status_rows(
    doorway,
    lang_id: str,
    sheets: Dict[str, str],
    row_skeletons: List[Dict],
    problems: List[str],
) -> List[Dict]:
    """Fill in live status/link data for each row skeleton by reading the live Sheet.

    ``sheets`` is ``{class_name: spreadsheet_id}`` from the ID file
    (``drive_ids.class_sheets``). Opens each class spreadsheet once
    (constructions share one spreadsheet) and reads each construction's tab.
    Returns row dicts with class_name, construction, is_pair, status_text, color, link.
    A spreadsheet that cannot be opened is added to ``problems``, which make
    the command exit non-zero once every language is done.
    """
    lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
    open_spreadsheets: Dict[str, Optional[object]] = {}
    rows: List[Dict] = []

    for skel in row_skeletons:
        class_name = skel["class_name"]
        construction = skel["construction"]
        sheet_id = sheets.get(class_name)

        if not sheet_id:
            text, color = _missing_sheet_status()
            rows.append({**skel, "status_text": text, "color": color, "link": None})
            continue

        if class_name not in open_spreadsheets:
            try:
                open_spreadsheets[class_name] = doorway.open_spreadsheet(sheet_id)
            except Exception as exc:
                problems.append(f"[{lang_id}] could not open the {class_name} spreadsheet: {exc}")
                open_spreadsheets[class_name] = None
        ss = open_spreadsheets[class_name]
        if ss is None:
            rows.append({**skel, "status_text": "could not open sheet", "color": _GRAY,
                         "link": None})
            continue

        try:
            ws = ss.worksheet(construction)
        except WorksheetNotFound:
            text, color = _missing_sheet_status()
            rows.append({**skel, "status_text": text, "color": color, "link": None})
            continue

        link = f"{ss.url}#gid={ws.id}"

        # Read the live sheet fresh every run, for both row shapes -- this is
        # what makes the percentage track pair-row regeneration automatically:
        # whatever pairs exist on the sheet right now are what gets counted,
        # with no stored row count to go stale.
        live_rows = ws.get_all_values()
        params, values, keystone_active, keystone_na_criteria = _construction_params(
            lang_id, class_name, construction, skel["param_names"], skel["param_values"], lang_setup_dir,
        )
        if skel.get("keyed"):
            status = keyed_annotation_status(live_rows, skel["keyed"]["columns"], params, values,
                                             skel["keyed"].get("blank_ok_when"))
        elif skel["is_pair"]:
            status = pair_annotation_status(live_rows, params, values)
        else:
            status = annotation_status(
                live_rows, params, values,
                keystone_active=keystone_active,
                keystone_na_criteria=keystone_na_criteria,
            )
        text, color = _row_status(status)
        rows.append({**skel, "status_text": text, "color": color, "link": link})

    return rows


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _lock_read_only(doorway, file_id: str, lang_ids: List[str]) -> None:
    """Remove any 'anyone' permission and give each of these languages'
    annotators read-only access, by name (`coding/people.py`).

    Uses `drive.remove_anyone_permission` / `drive.ensure_user_permission`,
    the one copy of each (this function used to inline them, with Adam's
    address typed into the code).
    """
    remove_anyone_permission(doorway, file_id)
    for email in sorted({e for e in (annotator_email(l) for l in lang_ids) if e}):
        ensure_user_permission(doorway, file_id, email, "reader")


# ---------------------------------------------------------------------------
# Spreadsheet writing
# ---------------------------------------------------------------------------

def _banner_rows(lang_id: str, folder_url: str,
                 chart_links: List[Tuple[str, str]] = ()) -> List[List[str]]:
    """Locked notice + when the counts were taken (UTC) + a link to the live
    annotation folder + a link to each contributor chart PDF already on Drive
    (``laminar_charts.chart_links``). laminar-charts, which runs after the
    daily refresh, rebuilds a language's sheet itself when it creates a PDF.

    The link's visible text is a short label (display name only, via the
    project's "Name [glottocode]" convention), not the raw URL -- showing the
    URL as text alongside the same URL as the link target is redundant, reads
    as a wall of text in a merged cell, and (per the sheet author's
    intent) that raw-URL text is itself an unlinked string Sheets can end up
    auto-detecting and adding its own preview affordance to.
    """
    display = get_display_name(lang_id)
    # The time, not just the date: the sheet is rebuilt once a day (and
    # sometimes by hand), so an annotator needs to know which of their own
    # edits the counts include.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    folder_link_text = f"📁 Annotation folder for {display}"
    return [
        [f"LOCKED — read-only status page for {display}. Do not edit; this sheet is "
         f"regenerated automatically and any edits here will be overwritten."],
        [f"Counts as of {stamp}. Rebuilt once a day, so edits made since then "
         f"aren't counted yet."],
        [f'=HYPERLINK("{folder_url}", "{folder_link_text}")'] if folder_url else [folder_link_text],
        *([f'=HYPERLINK("{url}", "📊 {label}, to check the spans your answers give")']
          for label, url in chart_links),
        [""],
    ]


def _write_status_sheet(
    ss, lang_id: str, folder_url: str, rows: List[Dict],
    chart_links: List[Tuple[str, str]] = (),
):
    """Write banner + header + data rows to ss's single worksheet, with formatting."""
    ws = ss.sheet1
    if ws.title != STATUS_TAB:
        ws.update_title(STATUS_TAB)

    banner = _banner_rows(lang_id, folder_url, chart_links)
    header_row_idx = len(banner)  # 0-based index of the header row, after banner+blank spacer

    # The construction name itself is the link (rather than a separate "Tab Link"
    # column repeating identical "Open tab" text in every row) -- each cell's
    # visible text is already distinct (the construction name), so the link
    # doesn't need its own column to read as informative.
    data_rows = []
    for r in rows:
        construction_cell = (
            f'=HYPERLINK("{r["link"]}", "{r["construction"]}")'
            if r["link"] else r["construction"]
        )
        data_rows.append([r["class_name"], construction_cell, r["status_text"]])

    all_rows = banner + [_HEADER] + data_rows
    n_cols = len(_HEADER)
    # Cut the tab to exactly this run's rows first, so no row (or status
    # colour) from a longer earlier run survives below them, then add a few
    # empty rows back. Resizing straight to len + 2 used to leave up to two
    # rows of a construction the language no longer has.
    ws.resize(rows=len(all_rows), cols=n_cols)
    ws.resize(rows=max(len(all_rows) + 2, 10))
    ws.update(all_rows, "A1", raw=False)

    requests = [
        # Start from no formatting: the rows below are set by position, and
        # when the banner changes length (the chart links, 2026-10-25) an
        # earlier run's bold header, merges and status colours would
        # otherwise stay on whatever row now sits there.
        {"unmergeCells": {"range": {"sheetId": ws.id}}},
        # backgroundColor is named in `fields` but given no value: the API
        # then clears it.
        {"repeatCell": {
            "range": {"sheetId": ws.id},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": False}}},
            "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor",
        }},
        # Freeze banner + header rows.
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": header_row_idx + 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        # Bold header row.
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": header_row_idx, "endRowIndex": header_row_idx + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        # Bold the locked-notice banner line.
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": n_cols},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        # Merge each banner row (except the trailing blank spacer) across all columns.
        *[
            {"mergeCells": {
                "range": {"sheetId": ws.id, "startRowIndex": i, "endRowIndex": i + 1,
                          "startColumnIndex": 0, "endColumnIndex": n_cols},
                "mergeType": "MERGE_ALL",
            }}
            for i in range(len(banner) - 1)
        ],
        # Column widths -- generous, plus wrap (below) as a safety net so nothing
        # gets clipped even where a value runs longer than expected (e.g. a long
        # class or construction name).
        {"updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 200}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 260}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 260}, "fields": "pixelSize",
        }},
        # Wrap text in every cell (banner + header + data) so long content never
        # gets silently clipped, regardless of the fixed widths above.
        {"repeatCell": {
            "range": {"sheetId": ws.id},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }},
    ]

    for i, r in enumerate(rows):
        row_idx = header_row_idx + 1 + i
        requests.append({
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1,
                          "startColumnIndex": 2, "endColumnIndex": 3},
                "cell": {"userEnteredFormat": {"backgroundColor": r["color"]}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    ss.batch_update({"requests": requests})
    return ws


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding generate-status-sheet`."""
    ap = argparse.ArgumentParser(
        description="Generate locked, read-only per-language Annotation Status sheets."
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="create/update sheets on Drive (default: dry run)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding generate-status-sheet`."""
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    lang_filter = args.lang

    doorway = get_doorway()
    config = _load_drive_config()
    pair_row_constructions = _get_pair_row_constructions()

    lang_ids = [lang_filter] if lang_filter else drive_ids.languages(config)
    # Anything that leaves a language's status sheet wrong or unbuilt. The run
    # carries on for the other languages, then exits non-zero naming them, so
    # the daily refresh files a status-sheet-error issue.
    problems: List[str] = []

    print(f"{'DRY RUN — ' if not apply else ''}Generating Annotation Status sheet(s)")
    if not apply:
        print("(run with --apply to create/update sheets on Drive)")

    folder_id = None
    if apply:
        folder_id = doorway.get_or_create_folder(_STATUS_FOLDER_NAME,
                                                 identity=drive_door.folder("status"))
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        _lock_read_only(doorway, folder_id,
                        drive_ids.languages(config))
        print(f"\nAnnotation Status folder: {folder_url}")

    for lang_id in lang_ids:
        if lang_id not in drive_ids.languages(config):
            print(f"\n[{lang_id}] not found in the ID file — skipping")
            continue
        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        if not lang_setup_dir.exists():
            print(f"\n[{lang_id}] no coded_data/{lang_id}/lang_setup/ found — skipping "
                  f"(coordinator must clone planars-data as coded_data/)")
            continue

        try:
            specs = _read_diagnostics_for_language(lang_id, lang_setup_dir)
        except Exception as exc:
            problems.append(f"[{lang_id}] could not read diagnostics_{lang_id}.yaml, so its "
                            f"status sheet was not rebuilt: {exc}")
            print(f"\n[{lang_id}] could not read diagnostics_{lang_id}.yaml: {exc} — skipping")
            continue

        skeletons = _build_row_skeletons(specs, pair_row_constructions)
        n_classes = len({s["class_name"] for s in skeletons})
        print(f"\n[{lang_id}] {len(skeletons)} construction(s) across {n_classes} class(es)")

        rows = _gather_status_rows(doorway, lang_id, drive_ids.class_sheets(config, lang_id),
                                   skeletons, problems)
        for r in rows:
            marker = " (pair-row tab)" if r["is_pair"] else ""
            print(f"    {r['class_name']}/{r['construction']}{marker}: {r['status_text']}")

        if not apply:
            continue

        lang_folder_id = config.get(lang_id, {}).get("folder_id")
        lang_folder_url = (f"https://drive.google.com/drive/folders/{lang_folder_id}"
                           if lang_folder_id else "")
        sheet_name = f"status_{lang_id}"
        ss, created = get_or_create_spreadsheet(
            doorway, folder_id, sheet_name,
            identity=drive_door.lang_file("status_sheet", lang_id))
        from .laminar_charts import chart_links
        _write_status_sheet(ss, lang_id, lang_folder_url, rows,
                            chart_links(config.get(lang_id, {})))
        _lock_read_only(doorway, ss.id, [lang_id])
        action = "Created" if created else "Updated"
        print(f"    {action}: {ss.url}")

        # Record it in the ID file so other commands (coding/notify.py's
        # sheet-change comments) can link to it without a live Drive search.
        if drive_ids.status_sheet_id(config, lang_id) != ss.id:
            drive_ids.set_status_sheet_id(config, lang_id, ss.id)
            _save_drive_config(config)

    if not apply:
        print("\nRun with --apply to create/update the sheet(s) on Drive.")
    else:
        print("\nDone.")

    if problems:
        print("\nERROR: some status sheets are wrong or were not rebuilt:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)


if __name__ == "__main__":
    main()
