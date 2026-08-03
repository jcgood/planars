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
child of the project's existing root folder. This is required, not
incidental: the existing root folder (from `setup-root-folder`) has an
"anyone with the link = editor" permission that cascades to every file
inside it, and Google's API refuses to remove an *inherited* permission at
a child level. Creating this folder outside that hierarchy gives it a clean
permission slate so the normal remove/add-permission calls actually work.
Do not nest this folder inside the existing root folder, and do not attempt
to fix the existing root folder's inherited permission here — that is a
separate, unresolved problem being handled independently.

Run from the repo root:
    python -m coding generate-status-sheet                      # dry run, all languages
    python -m coding generate-status-sheet --lang stan1293      # dry run, one language
    python -m coding generate-status-sheet --lang stan1293 --apply

Locking: the "Annotation Status" folder and each spreadsheet are shared
read-only with adamjamesrosstallman@gmail.com and have any "anyone with the
link" permission removed (defensive — freestanding files shouldn't have one,
but Drive occasionally adds one by default on creation). The coordinator's
OAuth identity owns every file as creator and needs no explicit permission.

Re-running with --apply overwrites the existing status_{lang_id} spreadsheet
in place (found by name within the folder) rather than minting a new URL —
unlike restructure-sheets, there is no annotation history to preserve here,
so a stable bookmarkable link is preferable.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
MANIFEST_PATH = ROOT / "sheets_manifest.json"

from .drive import (
    load_manifest,
    upload_manifest,
    _with_retry,
    _load_drive_config,
    _save_drive_config,
)
from .drive_doorway import WorksheetNotFound, get_doorway
from .make_forms import (
    _read_diagnostics_for_language,
    resolve_keystone_active,
    resolve_keystone_na_criteria,
)
from .restructure_sheets import _get_pair_row_constructions
from .validate_coding import annotation_status, _COREFERENCE_CONSTRUCTION_PARAMS
from planars.languages import get_display_name

_STATUS_FOLDER_NAME = "Annotation Status"
_ADAM_EMAIL = "adamjamesrosstallman@gmail.com"

# Pastel palette matching the pink/white highlighting convention already used
# by validate_coding.py's pink-cell error highlighting.
_GREEN  = {"red": 0.72, "green": 0.88, "blue": 0.72}
_YELLOW = {"red": 1.00, "green": 0.95, "blue": 0.60}
_GRAY   = {"red": 0.90, "green": 0.90, "blue": 0.90}

_HEADER = ["Class", "Construction", "Status"]


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


def _row_status(is_pair: bool, status: Dict[str, int]) -> Tuple[str, Dict[str, float]]:
    """Return (status_text, color) for one construction row.

    Pair-row constructions (nonpermutability's `general`, coreference's
    `reflexivization`/`pronominalization`/`np_reference`) are generated
    combinatorially from element pairs rather than counted 1:1 against expected
    criterion cells the way element-row constructions are, so a completeness
    percentage isn't meaningful for them — they get a neutral note instead.
    """
    if is_pair:
        return "pair-row tab", _GRAY
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
    values, and whether the construction is a pair-row tab (skipped from the
    percentage computation; see _row_status).
    """
    skeletons = []
    for class_name, construction, param_names, param_values in specs:
        is_pair = construction in pair_row_constructions.get(class_name, set())
        skeletons.append({
            "class_name": class_name,
            "construction": construction,
            "param_names": param_names,
            "param_values": param_values,
            "is_pair": is_pair,
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

    Mirrors the special-cased lookups in validate_coding.py's revalidate_sheets()
    (coreference constructions each use their own single criterion, not the
    class-level criteria dict) so status counts agree with the sheet-validation
    pink highlighting that annotators already see.
    """
    if class_name == "coreference" and construction in _COREFERENCE_CONSTRUCTION_PARAMS:
        info = _COREFERENCE_CONSTRUCTION_PARAMS[construction]
        return info["params"], info["values"], False, []
    keystone_active = resolve_keystone_active(lang_id, class_name, construction, data_dir=lang_setup_dir)
    if keystone_active is None:
        keystone_active = False
    keystone_na_criteria = resolve_keystone_na_criteria(class_name)
    return param_names, param_values, keystone_active, keystone_na_criteria


def _gather_status_rows(
    doorway,
    lang_id: str,
    lang_data: Dict,
    row_skeletons: List[Dict],
) -> List[Dict]:
    """Fill in live status/link data for each row skeleton by reading the live Sheet.

    Opens each class spreadsheet once (constructions share one spreadsheet, keyed
    by class_name in the manifest) and reads each construction's tab.
    Returns row dicts with class_name, construction, is_pair, status_text, color, link.
    """
    lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
    sheets = lang_data.get("sheets", {})
    open_spreadsheets: Dict[str, Optional[object]] = {}
    rows: List[Dict] = []

    for skel in row_skeletons:
        class_name = skel["class_name"]
        construction = skel["construction"]
        sheet_info = sheets.get(class_name)

        if not sheet_info:
            text, color = _missing_sheet_status()
            rows.append({**skel, "status_text": text, "color": color, "link": None})
            continue

        if class_name not in open_spreadsheets:
            try:
                open_spreadsheets[class_name] = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
            except Exception as exc:
                print(f"    WARNING: could not open {class_name} spreadsheet for {lang_id}: {exc}")
                open_spreadsheets[class_name] = None
        ss = open_spreadsheets[class_name]
        if ss is None:
            text, color = _missing_sheet_status()
            rows.append({**skel, "status_text": text, "color": color, "link": None})
            continue

        try:
            ws = _with_retry(lambda c=construction: ss.worksheet(c))
        except WorksheetNotFound:
            text, color = _missing_sheet_status()
            rows.append({**skel, "status_text": text, "color": color, "link": None})
            continue

        link = f"{ss.url}#gid={ws.id}"

        if skel["is_pair"]:
            text, color = _row_status(True, {"total": 0, "filled": 0})
            rows.append({**skel, "status_text": text, "color": color, "link": link})
            continue

        live_rows = _with_retry(lambda w=ws: w.get_all_values())
        params, values, keystone_active, keystone_na_criteria = _construction_params(
            lang_id, class_name, construction, skel["param_names"], skel["param_values"], lang_setup_dir,
        )
        status = annotation_status(
            live_rows, params, values,
            keystone_active=keystone_active,
            keystone_na_criteria=keystone_na_criteria,
        )
        text, color = _row_status(False, status)
        rows.append({**skel, "status_text": text, "color": color, "link": link})

    return rows


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _get_or_create_status_spreadsheet(
    doorway, folder_id: str, name: str
) -> Tuple[object, bool]:
    """Find or create the status spreadsheet by name inside folder_id.

    Reused on re-runs so the URL stays stable across regenerations. Returns
    (spreadsheet, created).
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


def _already_shared(doorway, file_id: str, email: str) -> bool:
    """Return True if email already holds any permission on file_id.

    Avoids piling up duplicate permission entries on repeated --apply runs.
    """
    perms = doorway.list_permissions(file_id, fields="permissions(emailAddress)")
    return any((p.get("emailAddress") or "").lower() == email.lower() for p in perms)


def _lock_read_only(doorway, file_id: str) -> None:
    """Remove any 'anyone' permission and ensure Adam has read-only access.

    No doorway-level convenience for removing the 'anyone' grant (unlike
    `drive._remove_anyone_permission`, which every unmigrated caller still
    uses) -- inlined here from the same two doorway primitives.
    """
    for p in doorway.list_permissions(file_id, fields="permissions(id,type)"):
        if p.get("type") == "anyone":
            doorway.delete_permission(file_id, p["id"])
    if not _already_shared(doorway, file_id, _ADAM_EMAIL):
        doorway.create_permission(file_id, type="user", role="reader",
                                  email=_ADAM_EMAIL, notify=False)


# ---------------------------------------------------------------------------
# Spreadsheet writing
# ---------------------------------------------------------------------------

def _banner_rows(lang_id: str, folder_url: str) -> List[List[str]]:
    """Locked notice + last-regenerated date + a link to the live annotation folder.

    The link's visible text is a short label (display name only, via the
    project's "Name [glottocode]" convention), not the raw URL -- showing the
    URL as text alongside the same URL as the link target is redundant, reads
    as a wall of text in a merged cell, and (per the sheet author's
    intent) that raw-URL text is itself an unlinked string Sheets can end up
    auto-detecting and adding its own preview affordance to.
    """
    display = get_display_name(lang_id)
    today = date.today().isoformat()
    folder_link_text = f"📁 Annotation folder for {display}"
    return [
        [f"LOCKED — read-only status page for {display}. Do not edit; this sheet is "
         f"regenerated automatically and any edits here will be overwritten."],
        [f"Last regenerated: {today}"],
        [f'=HYPERLINK("{folder_url}", "{folder_link_text}")'] if folder_url else [folder_link_text],
        [""],
    ]


def _write_status_sheet(
    ss, lang_id: str, folder_url: str, rows: List[Dict]
):
    """Write banner + header + data rows to ss's single worksheet, with formatting."""
    ws = _with_retry(lambda: ss.sheet1)
    if ws.title != "Status":
        _with_retry(lambda: ws.update_title("Status"))

    banner = _banner_rows(lang_id, folder_url)
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
    _with_retry(lambda: ws.resize(rows=max(len(all_rows) + 2, 10), cols=n_cols))
    _with_retry(lambda: ws.update(all_rows, "A1", raw=False))

    requests = [
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

    _with_retry(lambda: ss.batch_update({"requests": requests}))
    return ws


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding generate-status-sheet`."""
    apply = "--apply" in sys.argv
    lang_filter = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        lang_filter = sys.argv[idx + 1]

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    pair_row_constructions = _get_pair_row_constructions()
    manifest_dirty = False

    lang_ids = [lang_filter] if lang_filter else sorted(manifest.keys())

    print(f"{'DRY RUN — ' if not apply else ''}Generating Annotation Status sheet(s)")
    if not apply:
        print("(run with --apply to create/update sheets on Drive)")

    folder_id = None
    if apply:
        folder_id = doorway.get_or_create_folder(_STATUS_FOLDER_NAME)
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        _lock_read_only(doorway, folder_id)
        print(f"\nAnnotation Status folder: {folder_url}")

    for lang_id in lang_ids:
        lang_data = manifest.get(lang_id)
        if not lang_data:
            print(f"\n[{lang_id}] not found in manifest — skipping")
            continue
        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        if not lang_setup_dir.exists():
            print(f"\n[{lang_id}] no coded_data/{lang_id}/lang_setup/ found — skipping "
                  f"(coordinator must clone planars-data as coded_data/)")
            continue

        try:
            specs = _read_diagnostics_for_language(lang_id, lang_setup_dir)
        except Exception as exc:
            print(f"\n[{lang_id}] could not read diagnostics_{lang_id}.yaml: {exc} — skipping")
            continue

        skeletons = _build_row_skeletons(specs, pair_row_constructions)
        n_classes = len({s["class_name"] for s in skeletons})
        print(f"\n[{lang_id}] {len(skeletons)} construction(s) across {n_classes} class(es)")

        rows = _gather_status_rows(doorway, lang_id, lang_data, skeletons)
        for r in rows:
            marker = " (pair-row tab)" if r["is_pair"] else ""
            print(f"    {r['class_name']}/{r['construction']}{marker}: {r['status_text']}")

        if not apply:
            continue

        lang_folder_url = lang_data.get("folder_url", "")
        sheet_name = f"status_{lang_id}"
        ss, created = _get_or_create_status_spreadsheet(doorway, folder_id, sheet_name)
        _write_status_sheet(ss, lang_id, lang_folder_url, rows)
        _lock_read_only(doorway, ss.id)
        action = "Created" if created else "Updated"
        print(f"    {action}: {ss.url}")

        # Persist so other commands (coding/notify.py's sheet-change comments)
        # can link to this without a live Drive search each time.
        if lang_data.get("status_sheet_url") != ss.url:
            lang_data["status_sheet_url"] = ss.url
            manifest_dirty = True

    if not apply:
        print("\nRun with --apply to create/update the sheet(s) on Drive.")
    else:
        print("\nDone.")
        if manifest_dirty:
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            config = _load_drive_config()
            existing_file_id = config.get("_planars_config_file_id")
            root_folder_id = config.get("_root_folder_id")
            file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
            config["_planars_config_file_id"] = file_id
            _save_drive_config(config)
            print("Manifest updated on Drive (status_sheet_url).")


if __name__ == "__main__":
    main()
