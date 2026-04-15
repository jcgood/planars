#!/usr/bin/env python3
"""Generate Google Sheets annotation forms from planar structure and diagnostics.

Run from the repo root:
    python -m coding generate-sheets           # create sheets for new classes only
    python -m coding generate-sheets --force   # blocked with a hard error if annotation sheets already exist

On the first run, creates one Google Sheet per analysis class with one tab per construction.
On subsequent runs, only creates sheets for classes not yet in the Drive manifest (e.g. a
newly added aspiration class). Existing sheets are left untouched.

To sync param column changes to existing sheets: python -m coding sync-params --apply

Requires:
    pip install gspread google-auth google-api-python-client

Authentication (OAuth2 — recommended for personal Google accounts):
    1. In Google Cloud Console, create an OAuth2 Desktop App credential.
    2. Download the JSON and save it to PLANARS_OAUTH_CREDENTIALS path
       (default: ~/.config/planars/oauth_credentials.json).
    3. On first run a browser window opens for authorization; the token is
       cached at ~/.config/gspread/authorized_user.json for subsequent runs.

    Optional env vars:
        PLANARS_OAUTH_CREDENTIALS  path to the OAuth client-secret JSON
                                   (default: ~/.config/planars/oauth_credentials.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

import pandas as pd

from . import validate_planar as _val_planar
from . import validate_diagnostics as _val_diag
from .drive import (
    _get_clients,
    _load_drive_config,
    _save_drive_config,
    _open_spreadsheet,
    _upload_planars_config,
    _download_file_json,
    _get_or_create_folder,
    _share_anyone_with_link,
    _move_to_folder,
    _with_retry,
    _get_docs_client,
    _create_notes_doc,
    DRIVE_CONFIG_PATH,
)
from .glottolog import cached_entry as _cached_glottolog, get_metadata as _fetch_glottolog
from planars.languages import get_display_name as _get_display_name
from .schemas import load_planar_schema
from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    resolve_keystone_active,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"

# Columns appended after param columns on every tab; no dropdown validation.
# Source of truth: schemas/planar.yaml trailing_columns.
_TRAILING_COLS = load_planar_schema().get("trailing_columns", ["Source", "Comments"])
_STATUS_TAB = "Status"
_STATUS_VALUES = ["in-progress", "ready-for-review"]


def _create_or_update_tsv_sheet(
    gc: gspread.Client,
    drive,
    folder_id: str,
    name: str,
    tsv_path: Path,
    existing_id: str = None,
) -> Tuple[str, str]:
    """Create or overwrite a Google Sheet with the contents of a TSV file.

    If existing_id is given, clears and rewrites that sheet; otherwise creates a new one,
    moves it to folder_id, and shares it with anyone-with-link as editor.

    Returns (spreadsheet_id, url).
    """
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    all_rows = [list(df.columns)] + [list(row) for _, row in df.iterrows()]

    if existing_id:
        ss = _open_spreadsheet(gc, existing_id)
        ws = ss.sheet1
        ws.clear()
    else:
        ss = gc.create(name)
        _move_to_folder(drive, ss.id, folder_id)
        _share_anyone_with_link(drive, ss.id)
        ws = ss.sheet1

    ws.update(all_rows, "A1")

    # Bold and freeze the header row.
    ss.batch_update({"requests": [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": ws.id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
    ]})

    return ss.id, ss.url


def _upload_lang_setup_as_sheets(
    gc: gspread.Client,
    drive,
    planar_dir: Path,
    lang_id: str,
    folder_id: str,
    existing_lang_data: Dict,
    force: bool = False,
) -> Dict:
    """Upload planar_*.tsv and diagnostics_{lang_id}.tsv as editable Google Sheets.

    Google Sheets is the source of truth for planar structure and diagnostics; local TSVs
    are downstream copies produced by import-sheets. This function pushes the current local
    TSV state to Sheets on initial setup, or on --force to propagate intentional edits.

    Skips a file if its sheet ID is already in existing_lang_data and force=False.

    Returns a dict with planar_spreadsheet_id/url and diagnostics_spreadsheet_id/url
    for any sheets that were created or updated (only keys present if the file exists).
    """
    result: Dict = {}

    planar_files = sorted(planar_dir.glob("planar_*.tsv"))
    if planar_files:
        planar_path = planar_files[-1]   # most recent
        existing_id = existing_lang_data.get("planar_spreadsheet_id")
        if existing_id and not force:
            print(f"  Planar sheet exists — skipping (use --force to overwrite)")
            result["planar_spreadsheet_id"]  = existing_id
            result["planar_spreadsheet_url"] = existing_lang_data.get("planar_spreadsheet_url", "")
        else:
            sheet_id, url = _create_or_update_tsv_sheet(
                gc, drive, folder_id,
                name=f"planar_{lang_id}",
                tsv_path=planar_path,
                existing_id=existing_id,
            )
            result["planar_spreadsheet_id"]  = sheet_id
            result["planar_spreadsheet_url"] = url
            action = "Updated" if existing_id else "Created"
            print(f"  {action} planar sheet: {url}")

    diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
    if diag_path.exists():
        existing_id = existing_lang_data.get("diagnostics_spreadsheet_id")
        if existing_id and not force:
            print(f"  Diagnostics sheet exists — skipping (use --force to overwrite)")
            result["diagnostics_spreadsheet_id"]  = existing_id
            result["diagnostics_spreadsheet_url"] = existing_lang_data.get("diagnostics_spreadsheet_url", "")
        else:
            sheet_id, url = _create_or_update_tsv_sheet(
                gc, drive, folder_id,
                name=f"diagnostics_{lang_id}",
                tsv_path=diag_path,
                existing_id=existing_id,
            )
            result["diagnostics_spreadsheet_id"]  = sheet_id
            result["diagnostics_spreadsheet_url"] = url
            action = "Updated" if existing_id else "Created"
            print(f"  {action} diagnostics sheet: {url}")

    return result


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def _build_rows(
    element_index, lang_id: str, param_names: List[str], keystone_active: bool = False
) -> List[List[object]]:
    """Build sorted data rows for a sheet tab.

    Rows are sorted by (position_number, element_name) so annotators see the
    planar structure in order. Elements with leading/trailing hyphens are wrapped
    in brackets to prevent Excel/Sheets from interpreting them as formulas.
    Keystone (v:verbstem) rows get 'NA' in all param columns when keystone_active
    is False (default); when True they get '' so annotators fill in real values.

    Args:
        element_index: ElementIndex from build_element_index.
        lang_id: language ID to filter the index.
        param_names: ordered list of criterion column names.
        keystone_active: if True, keystone rows start blank like all other rows.

    Returns:
        List of rows (without the header), each a list:
        [element, position_name, position_number, *criterion_values].
    """
    items = [
        (pos, element, pos_name)
        for _, (pos, pos_name, lang, element) in element_index.items()
        if lang == lang_id
    ]
    items_sorted = sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))

    rows = []
    for pos, element, pos_name in items_sorted:
        element = element.strip()
        # Wrap hyphen-prefixed/suffixed elements to prevent Sheets formula parsing.
        if element.startswith("-") or element.endswith("-"):
            element = f"[{element}]"
        if pos_name.strip().lower() == "v:verbstem" and not keystone_active:
            rows.append([element, pos_name, pos] + ["NA"] * len(param_names))
        else:
            rows.append([element, pos_name, pos] + [""] * len(param_names))
    return rows


# ---------------------------------------------------------------------------
# Status tab
# ---------------------------------------------------------------------------

def _move_status_tab_to_end(spreadsheet: gspread.Spreadsheet) -> None:
    """Ensure the Status tab is the last worksheet in the spreadsheet."""
    worksheets = _with_retry(spreadsheet.worksheets)
    if not worksheets or worksheets[-1].title == _STATUS_TAB:
        return
    status_ws = next((w for w in worksheets if w.title == _STATUS_TAB), None)
    if status_ws is None:
        return
    ordered = [w for w in worksheets if w.title != _STATUS_TAB] + [status_ws]
    spreadsheet.reorder_worksheets(ordered)


def _create_status_tab(
    spreadsheet: gspread.Spreadsheet,
    construction_names: List[str],
) -> None:
    """Add a Status tab to a spreadsheet, or update an existing one.

    The tab has two columns: Construction and Status. Each construction gets
    one row with an 'in-progress' default and a dropdown for Status.
    If the tab already exists, adds any missing construction rows and moves
    the tab to the last position.
    """
    existing = {ws.title: ws for ws in _with_retry(spreadsheet.worksheets)}

    if _STATUS_TAB in existing:
        ws = existing[_STATUS_TAB]
        rows = ws.get_all_values()
        current_constructions = {r[0] for r in rows[1:] if r} if len(rows) > 1 else set()
        missing = [c for c in construction_names if c not in current_constructions]
        if missing:
            ws.append_rows([[c, "in-progress"] for c in missing], value_input_option="RAW")
        _move_status_tab_to_end(spreadsheet)
        return

    ws = spreadsheet.add_worksheet(title=_STATUS_TAB, rows=len(construction_names) + 2, cols=2)
    header = [["Construction", "Status"]]
    data = [[c, "in-progress"] for c in construction_names]
    ws.update(header + data, "A1")

    sheet_id = ws.id
    num_rows = len(construction_names)
    spreadsheet.batch_update({"requests": [
        # Freeze + bold header
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        # Dropdown on Status column (col B = index 1)
        {"setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1, "endRowIndex": 1 + num_rows,
                "startColumnIndex": 1, "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in _STATUS_VALUES],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }},
    ]})
    _move_status_tab_to_end(spreadsheet)
    print(f"    Status tab created ({len(construction_names)} construction(s))")


# ---------------------------------------------------------------------------
# Sheet formatting and validation
# ---------------------------------------------------------------------------

def _format_and_validate(
    worksheet: gspread.Worksheet,
    num_data_rows: int,
    param_values: List[List[str]],
) -> None:
    """Freeze and bold the header row; apply per-column dropdown validation.

    Sends a single batch_update to the Sheets API containing:
    - a freeze request for the header row
    - a bold request for the header row
    - one dropdown validation rule per param column

    Validation is non-strict (showCustomUi=True, strict=False) so annotators
    can also type 'NA' in keystone rows without triggering a validation error.

    Args:
        worksheet: the gspread Worksheet to format.
        num_data_rows: number of data rows (excluding header) to validate.
        param_values: list of allowed-value lists, one entry per param column,
            in the same order as the columns (starting at column index 3).
    """
    sheet_id = worksheet.id
    requests = [
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Bold header row
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {"textFormat": {"bold": True}}
                },
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
    ]
    # One validation request per param column (non-strict so NA in keystone rows is tolerated).
    # Columns 0–2 are structural (Element, Position_Name, Position_Number); params start at 3.
    for col_offset, values in enumerate(param_values):
        col_idx = 3 + col_offset
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + num_data_rows,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in values],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })
    worksheet.spreadsheet.batch_update({"requests": requests})


# ---------------------------------------------------------------------------
# Tab population
# ---------------------------------------------------------------------------

def _populate_tab(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[List[object]],
) -> gspread.Worksheet:
    """Create or clear a worksheet tab and populate it with data.

    If a tab named tab_name already exists it is cleared and rewritten;
    otherwise a new worksheet is created. Trailing columns (_TRAILING_COLS)
    are appended after the criterion columns with empty values.

    Args:
        spreadsheet: the parent gspread Spreadsheet.
        tab_name: worksheet title to create or clear.
        param_names: ordered list of criterion column names.
        param_values: dict mapping criterion name to list of allowed values.
        rows: data rows from _build_rows (no header).

    Returns:
        The populated gspread Worksheet.
    """
    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(tab_name))
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=len(param_names) + 3
        )

    all_cols = param_names + _TRAILING_COLS
    header = ["Element", "Position_Name", "Position_Number"] + all_cols
    # Pad data rows with empty trailing columns (e.g. Comments).
    all_rows = [header] + [[str(v) for v in row] + [""] * len(_TRAILING_COLS) for row in rows]
    ws.update(all_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    _format_and_validate(ws, len(rows), per_col_values)
    return ws


# ---------------------------------------------------------------------------
# Analysis sheet creation
# ---------------------------------------------------------------------------

def _create_analysis_sheet(
    gc: gspread.Client,
    drive,
    folder_id: str,
    lang_id: str,
    class_name: str,
    constructions: List[Tuple[str, List[str], Dict[str, List[str]]]],
    element_index,
) -> Dict:
    """Create a Google Sheet for one analysis class with one tab per construction."""
    sheet_title = f"{class_name}_{lang_id}"
    print(f"  Creating: {sheet_title}")

    spreadsheet = gc.create(sheet_title)
    _move_to_folder(drive, spreadsheet.id, folder_id)
    _share_anyone_with_link(drive, spreadsheet.id)

    default_ws = spreadsheet.sheet1
    tab_names = []

    for construction, param_names, param_values in constructions:
        ka = resolve_keystone_active(lang_id, class_name, construction, data_dir=planar_dir) or False
        rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
        _populate_tab(spreadsheet, construction, param_names, param_values, rows)
        tab_names.append(construction)
        print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")

    # Remove the default empty sheet if it wasn't one of our tabs
    if default_ws.title not in tab_names:
        spreadsheet.del_worksheet(default_ws)

    # Add Status tab last
    _create_status_tab(spreadsheet, tab_names)

    # Build per-construction param_values map for the manifest
    construction_params = {
        construction: {"param_names": pn, "param_values": pv}
        for construction, pn, pv in constructions
    }

    return {
        "spreadsheet_id": spreadsheet.id,
        "url": spreadsheet.url,
        "constructions": tab_names,
        "construction_params": construction_params,
    }


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

def _check_force_against_existing_sheets(
    lang_id: str, force: bool, existing_lang_data: Dict
) -> None:
    """Raise SystemExit if --force is attempted on a language with existing annotation sheets.

    Annotation data is irreplaceable. --force must never recreate sheets that
    already have IDs in the manifest, as that would orphan the filled sheets.
    """
    if force and existing_lang_data.get("sheets"):
        existing_sheet_classes = list(existing_lang_data["sheets"].keys())
        print(
            f"\nERROR: --force refused for {lang_id}.\n"
            f"  Existing annotation sheets: {existing_sheet_classes}\n"
            "  Destroying annotation sheets is not allowed. Annotated data is\n"
            "  irreplaceable. If you need to restructure sheets, use:\n"
            "    python -m coding restructure-sheets --apply\n"
            "  To add new classes only (no destruction), omit --force."
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding generate-sheets`.

    Iterates over all planar_*.tsv files in coded_data/*/lang_setup/ and for each language:
    - Creates planar_*.tsv and diagnostics_{lang_id}.tsv as editable Google Sheets (source of
      truth). Skips files whose sheet IDs are already in the manifest unless --force.
    - Creates one annotation Google Sheet per analysis class (skipping existing ones unless
      --force). Each sheet has one tab per construction with dropdown validation.
    - Uploads the merged manifest.json manifest to Drive after each language.
    - Regenerates contributor notebooks at the end.
    """
    force = "--force" in sys.argv

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    # Connect to Google once for all languages
    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    docs = _get_docs_client(gc)
    config = _load_drive_config()
    root_folder_id = config.get("_root_folder_id")

    # Load the existing merged config from Drive (if present) so we can update
    # it incrementally as each language is processed, preserving other languages.
    existing_config_file_id = config.get("_planars_config_file_id")
    if existing_config_file_id:
        try:
            merged_config: Dict = _download_file_json(drive, existing_config_file_id)
            # Back up the raw downloaded manifest before any mutations so it can
            # be used for recovery if something goes wrong during this run.
            _manifest_backup = ROOT / "manifest_backup.json"
            _manifest_backup.write_text(json.dumps(merged_config, indent=2), encoding="utf-8")
            print(f"Manifest backed up to manifest_backup.json ({len(merged_config)} language(s))")
            # If it's old-format (just folder_ids, no sheets), start fresh.
            if not any("sheets" in v for v in merged_config.values() if isinstance(v, dict)):
                merged_config = {}
        except Exception:
            merged_config = {}
    else:
        merged_config = {}

    full_manifest: Dict = {}

    for planar_file in planar_files:
        planar_dir = planar_file.parent
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        print(f"\nLanguage:    {lang_id}")
        print(f"Planar file: {planar_file.name}")

        element_index = build_element_index(planar_file.name, planar_dir)

        # Validate planar structure; warn but do not block sheet generation.
        planar_df = pd.read_csv(planar_file, sep="\t")
        planar_issues = _val_planar.validate_planar_df(planar_df)
        if planar_issues:
            print(f"  Planar validation ({len(planar_issues)} issue(s)):")
            for issue in planar_issues:
                print(f"    {issue}")

        # Validate diagnostics_{lang_id}.tsv; warn but do not block sheet generation.
        diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
        if diag_path.exists():
            diag_df = pd.read_csv(diag_path, sep="\t")
            diag_issues = _val_diag.validate_diagnostics_df(diag_df, lang_id)
            if diag_issues:
                print(f"  Diagnostics validation ({len(diag_issues)} issue(s)):")
                for issue in diag_issues:
                    print(f"    {issue}")

        specs = _read_diagnostics_for_language(lang_id, planar_dir)

        # Group specs by class_name -> [(construction, param_names, param_values), ...]
        all_classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            all_classes.setdefault(class_name, []).append((construction, param_names, param_values))

        print(f"Classes:     {list(all_classes.keys())}")

        # Resolve/create Drive folder.
        folder_id = _get_or_create_folder(drive, lang_id, parent_id=root_folder_id)
        try:
            _share_anyone_with_link(drive, folder_id)
        except Exception as _share_err:
            print(f"  [WARNING] Could not share folder for {lang_id}: {_share_err}")
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder:      {folder_url}")

        # Create collaborator notes doc if not already in the manifest.
        # _get_display_name reads glottolog_cache.json — run `lookup-lang <lang_id>`
        # first if the cache is empty (doc will fall back to notes_{lang_id} otherwise).
        existing_notes_doc_id = merged_config.get(lang_id, {}).get("notes_doc_id") or config.get(lang_id, {}).get("notes_doc_id")
        if not existing_notes_doc_id:
            try:
                existing_notes_doc_id = _create_notes_doc(drive, lang_id, folder_id, _get_display_name(lang_id))
                print(f"Notes doc:   https://docs.google.com/document/d/{existing_notes_doc_id}")
            except Exception as _notes_err:
                print(f"  [WARNING] Could not create notes doc for {lang_id}: {_notes_err}")
                existing_notes_doc_id = None
        else:
            print(f"Notes doc:   (existing) https://docs.google.com/document/d/{existing_notes_doc_id}")

        # Load existing data early so we can look up existing planar/diagnostics sheet IDs.
        existing_lang_data: Dict = merged_config.get(lang_id, {})
        if not existing_lang_data and lang_id in config:
            # Migration: try old-format per-language manifest file
            old_fid = config[lang_id].get("manifest_file_id")
            if old_fid:
                try:
                    existing_lang_data = _download_file_json(drive, old_fid)
                except Exception:
                    pass

        # Safety check: if the manifest has no entry for this language but
        # drive_config.json shows it was previously set up (has a folder_id),
        # the manifest is almost certainly stale — not a genuinely new language.
        # Creating sheets now would produce empty sheets that overwrite annotation data.
        # Abort unless --force is explicitly passed.
        if not existing_lang_data and not force:
            established = config.get(lang_id, {})
            if established.get("folder_id"):
                raise SystemExit(
                    f"\nERROR: The Drive manifest has no entry for '{lang_id}', but "
                    f"drive_config.json records it as an established language "
                    f"(folder_id: {established['folder_id']}).\n"
                    f"This almost certainly means the manifest is stale or was accidentally "
                    f"replaced with an empty file — NOT that the sheets are genuinely new.\n"
                    f"\nCreating sheets now would produce empty sheets and destroy annotation data.\n"
                    f"\nTo recover: check manifest_backup.json (written at the start of this run)\n"
                    f"or inspect the Drive manifest directly (file id: {existing_config_file_id}).\n"
                    f"\nTo force recreation of all sheets (DESTRUCTIVE — data will be lost): "
                    f"use --force."
                )

        def _sync_language_metadata(lang_data: dict, lid: str) -> None:
            """Copy glottolog + meta blocks from languages.yaml into the Drive manifest entry.

            languages.yaml is the source of truth.  The Drive manifest carries a
            copy so the data lives near the annotation sheets.  If the language is
            not yet in languages.yaml, falls back to glottolog_cache.json and warns.

            Reads languages.yaml directly by path (not via coding.schemas cached
            loader) because lookup-lang may write a new entry earlier in the same
            session and we need the just-written state, not a cached snapshot.
            """
            import yaml as _yaml
            _lang_yaml = ROOT / "schemas" / "languages.yaml"
            _langs = {}
            if _lang_yaml.exists():
                with open(_lang_yaml, encoding="utf-8") as _f:
                    _langs = _yaml.safe_load(_f) or {}
            entry = _langs.get(lid)
            if entry:
                if "glottolog" in entry:
                    lang_data["glottolog"] = entry["glottolog"]
                if "meta" in entry:
                    lang_data["meta"] = entry["meta"]
                # Warn if key meta fields are blank — display names will be wrong
                # in Drive folders and notebooks until they are filled in.
                meta = entry.get("meta") or {}
                glottolog = entry.get("glottolog") or {}
                missing = [f for f in ("source", "author") if not meta.get(f)]
                no_name = not glottolog.get("name")
                if missing or no_name:
                    problems = (["name (run lookup-lang first)"] if no_name else []) + missing
                    print(
                        f"  [{lid}] WARNING: languages.yaml meta incomplete "
                        f"(missing: {', '.join(problems)}).\n"
                        f"    Display names may be incorrect in Drive folders and notebooks.\n"
                        f"    Fill in the meta block and commit before sharing notebooks with contributors."
                    )
            else:
                print(
                    f"  [{lid}] WARNING: not found in schemas/languages.yaml. "
                    f"Run 'python -m coding lookup-lang {lid}' before running generate-sheets."
                )
                glotto = _cached_glottolog(lid)
                if not glotto:
                    try:
                        glotto = _fetch_glottolog(lid)
                    except Exception as exc:
                        print(f"  [{lid}] WARNING: Could not fetch Glottolog metadata: {exc}")
                if glotto:
                    lang_data["glottolog"] = {
                        "name":      glotto["name"],
                        "iso639_3":  glotto["iso639_3"],
                        "family":    glotto["classification"][0]["name"] if glotto["classification"] else None,
                        "latitude":  glotto["latitude"],
                        "longitude": glotto["longitude"],
                    }

        # Upload planar and diagnostics as editable Google Sheets (source of truth).
        # Skips files whose sheet IDs are already in the manifest unless --force.
        input_sheet_info = _upload_lang_setup_as_sheets(
            gc, drive, planar_dir, lang_id, folder_id, existing_lang_data, force=force
        )

        if not force and existing_lang_data:
            existing_sheets = existing_lang_data.get("sheets", {})
            new_class_names = [c for c in all_classes if c not in existing_sheets]
            if not new_class_names:
                print(
                    f"  All classes already have sheets. Skipping {lang_id}.\n"
                    "  (use --force to regenerate)"
                )
                existing_lang_data["folder_id"] = folder_id
                if existing_notes_doc_id:
                    existing_lang_data["notes_doc_id"] = existing_notes_doc_id
                existing_lang_data.update(input_sheet_info)
                _sync_language_metadata(existing_lang_data, lang_id)
                config.setdefault(lang_id, {})["folder_id"] = folder_id
                if existing_notes_doc_id:
                    config[lang_id]["notes_doc_id"] = existing_notes_doc_id
                _save_drive_config(config)
                full_manifest[lang_id] = existing_lang_data
                merged_config[lang_id] = existing_lang_data
                continue
            print(f"Existing:    {list(existing_sheets.keys())}")
            print(f"New:         {new_class_names}")

        _check_force_against_existing_sheets(lang_id, force, existing_lang_data)

        classes_to_create = {
            k: v for k, v in all_classes.items()
            if k not in existing_lang_data.get("sheets", {})
        }

        # Build lang_data starting from existing data (or fresh), always include folder_id.
        lang_data: Dict = existing_lang_data or {"folder_url": folder_url, "sheets": {}}
        lang_data["folder_id"] = folder_id
        if existing_notes_doc_id:
            lang_data["notes_doc_id"] = existing_notes_doc_id
        lang_data.update(input_sheet_info)  # store planar/diagnostics spreadsheet IDs

        _sync_language_metadata(lang_data, lang_id)

        # Create one sheet per new analysis class
        for class_name, constructions in classes_to_create.items():
            sheet_info = _create_analysis_sheet(
                gc, drive, folder_id, lang_id, class_name, constructions, element_index
            )
            lang_data["sheets"][class_name] = sheet_info
            print(f"    URL: {sheet_info['url']}\n")

        full_manifest[lang_id] = lang_data
        merged_config[lang_id] = lang_data

        # Upload the full merged config to Drive after each language so partial
        # progress is saved even if a later language fails.
        existing_config_file_id = _upload_planars_config(
            drive, merged_config, root_folder_id, existing_config_file_id
        )
        config["_planars_config_file_id"] = existing_config_file_id
        config.setdefault(lang_id, {})["folder_id"] = folder_id
        # Mirror planar/diagnostics sheet IDs into drive_config.json so they are
        # available locally without fetching the full manifest from Drive.
        for key in ("planar_spreadsheet_id", "planar_spreadsheet_url",
                    "diagnostics_spreadsheet_id", "diagnostics_spreadsheet_url"):
            if key in input_sheet_info:
                config[lang_id][key] = input_sheet_info[key]
        if existing_notes_doc_id:
            config[lang_id]["notes_doc_id"] = existing_notes_doc_id
        # Remove stale per-language manifest_file_id (superseded by merged config).
        config[lang_id].pop("manifest_file_id", None)
        _save_drive_config(config)
        print(f"manifest.json updated on Drive (id: {existing_config_file_id})")

    # Upload merged config once more after the loop to capture any skipped languages
    # that were added to merged_config but didn't trigger an in-loop upload.
    final_file_id = _upload_planars_config(
        drive, merged_config, root_folder_id, existing_config_file_id
    )
    config["_planars_config_file_id"] = final_file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {final_file_id})")

    # Write local manifest with all languages (gitignored, kept for reference)
    MANIFEST_PATH.write_text(json.dumps(full_manifest, indent=2), encoding="utf-8")
    print(f"\nLocal manifest written to: {MANIFEST_PATH.name}")
    print(f"drive_config.json written.")

    print(f"\nShare each language folder with your specialist (see folder URLs above).")

    print(
        "\n⚠  drive_config.json was updated. If you have the scheduled sheet-validation\n"
        "   workflow enabled, update the PLANARS_DRIVE_CONFIG GitHub secret with the\n"
        "   new contents of drive_config.json:\n"
        "   GitHub → Settings → Secrets and variables → Actions → PLANARS_DRIVE_CONFIG"
    )

    from .generate_notebooks import regenerate_notebooks
    regenerate_notebooks()


def push_manifest() -> None:
    """Upload the existing local sheets_manifest.json to Drive as merged manifest.json.

    One-time migration utility. Run with:
        python -m coding generate-sheets --push-manifest
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "sheets_manifest.json not found. Nothing to push.\n"
            "Run python -m coding generate-sheets first to create sheets."
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print("Connecting to Google APIs...")
    _, drive = _get_clients()
    config = _load_drive_config()

    # Enrich manifest with folder_id from drive_config before uploading.
    merged_config: Dict = {}
    for lang_id, lang_data in manifest.items():
        entry = dict(lang_data)
        folder_url = entry.get("folder_url", "")
        folder_id = config.get(lang_id, {}).get("folder_id") or (
            folder_url.rstrip("/").rsplit("/", 1)[-1] if folder_url else ""
        )
        entry["folder_id"] = folder_id
        config.setdefault(lang_id, {})["folder_id"] = folder_id
        config[lang_id].pop("manifest_file_id", None)
        merged_config[lang_id] = entry

    root_folder_id = config.get("_root_folder_id")
    existing_file_id = config.get("_planars_config_file_id")
    file_id = _upload_planars_config(drive, merged_config, root_folder_id, existing_file_id)
    config["_planars_config_file_id"] = file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {file_id})")
    print(f"drive_config.json written.")


if __name__ == "__main__":
    if "--push-manifest" in sys.argv:
        push_manifest()
    else:
        main()
