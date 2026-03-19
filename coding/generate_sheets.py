#!/usr/bin/env python3
"""Generate Google Sheets annotation forms from planar structure and diagnostics.

Run from the repo root:
    python -m coding generate-sheets           # create sheets for new classes only
    python -m coding generate-sheets --force   # regenerate all (creates duplicates; delete old manually)

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
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread
from googleapiclient.discovery import build as google_build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from . import make_forms as _mf
from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
DRIVE_CONFIG_PATH = ROOT / "drive_config.json"
CODED_DATA = ROOT / "coded_data"

# Columns appended after param columns on every tab; no dropdown validation
_TRAILING_COLS = ["Comments"]

_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"


# ---------------------------------------------------------------------------
# Rate-limit retry helper
# ---------------------------------------------------------------------------

def _open_spreadsheet(gc: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    """Open a spreadsheet by ID, retrying on 429 quota errors with backoff."""
    for attempt in range(5):
        try:
            return gc.open_by_key(spreadsheet_id)
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429 and attempt < 4:
                wait = 15 * (attempt + 1)
                print(f"    [rate limit] quota exceeded, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


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
        ],
    )
    # Reuse the refreshed credentials from gspread for the Drive API client
    drive = google_build("drive", "v3", credentials=gc.http_client.auth)
    return gc, drive


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
    import io
    request = drive.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return json.loads(buffer.getvalue().decode("utf-8"))


# Backward-compatible alias used by restructure_sheets internals
_download_manifest_from_drive = _download_file_json


def _upload_planars_config(
    drive, full_config: Dict, root_folder_id: str, existing_file_id: str = None
) -> str:
    """Upload the merged planars_config.json to Drive. Returns the file ID.

    The merged config has the structure::

        {lang_id: {folder_id, folder_url, sheets: {...}, ...}, ...}

    This replaces the old per-language ``manifest_{lang_id}.json`` files with a
    single file that notebooks and all sheet scripts read.

    Args:
        drive: Drive API service.
        full_config: complete merged config dict covering all languages.
        root_folder_id: Drive folder for first-time file creation.
        existing_file_id: ID of an existing planars_config.json to update in place.

    Returns:
        The Drive file ID of planars_config.json.
    """
    import io
    content = json.dumps(full_config, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
    if existing_file_id:
        drive.files().update(fileId=existing_file_id, media_body=media).execute()
        return existing_file_id
    result = drive.files().create(
        body={"name": "planars_config.json", "parents": [root_folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return result["id"]


def _load_manifest_from_drive(drive) -> Dict:
    """Load the full manifest (all languages) from Drive.

    Tries the new merged planars_config.json first. Falls back to reading the
    old per-language ``manifest_{lang_id}.json`` files if the merged format is
    not yet in place (migration path for setups predating issue #30).

    Returns:
        Dict mapping lang_id to lang_data, where lang_data contains at minimum
        ``folder_id``, ``folder_url``, and ``sheets``.
    """
    config = _load_drive_config()
    if not config:
        raise SystemExit(
            "drive_config.json not found. Run: python -m coding generate-sheets"
        )

    # New merged format: single planars_config.json with full manifest data.
    file_id = config.get("_planars_config_file_id")
    if file_id:
        try:
            full_config = _download_file_json(drive, file_id)
            # Distinguish new format (has 'sheets' per language) from old (just folder_id).
            if any("sheets" in v for v in full_config.values() if isinstance(v, dict)):
                return full_config
        except Exception as exc:
            print(f"  Warning: could not load merged config ({exc}), falling back.")

    # Old format fallback: per-language manifest_{lang_id}.json files.
    print("  Note: loading per-language manifests (pre-#30 format).")
    print("  Run python -m coding generate-sheets to upgrade to merged planars_config.json.")
    manifest: Dict = {}
    for lang_id, lang_config in config.items():
        if lang_id.startswith("_") or not isinstance(lang_config, dict):
            continue
        mfid = lang_config.get("manifest_file_id")
        if not mfid:
            continue
        lang_data = _download_file_json(drive, mfid)
        lang_data.setdefault("folder_id", lang_config.get("folder_id", ""))
        manifest[lang_id] = lang_data
    if not manifest:
        raise SystemExit(
            "No manifest data found in drive_config.json. "
            "Run python -m coding generate-sheets first."
        )
    return manifest


# ---------------------------------------------------------------------------
# Drive folder helpers
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


def _share_anyone_with_link(drive, file_id: str) -> None:
    """Share a file or folder with anyone who has the link as editor."""
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "writer"},
        fields="id",
    ).execute()


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
# Row building
# ---------------------------------------------------------------------------

def _build_rows(
    element_index, lang_id: str, param_names: List[str]
) -> List[List[object]]:
    """Build sorted data rows for a sheet tab.

    Rows are sorted by (position_number, element_name) so annotators see the
    planar structure in order. Elements with leading/trailing hyphens are wrapped
    in brackets to prevent Excel/Sheets from interpreting them as formulas.
    Keystone (v:verbroot) rows get 'NA' in all param columns; others get ''.

    Args:
        element_index: ElementIndex from build_element_index.
        lang_id: language ID to filter the index.
        param_names: ordered list of parameter column names.

    Returns:
        List of rows (without the header), each a list:
        [element, position_name, position_number, *param_values].
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
        if pos_name.strip().lower() == "v:verbroot":
            rows.append([element, pos_name, pos] + ["NA"] * len(param_names))
        else:
            rows.append([element, pos_name, pos] + [""] * len(param_names))
    return rows


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
    are appended after the param columns with empty values.

    Args:
        spreadsheet: the parent gspread Spreadsheet.
        tab_name: worksheet title to create or clear.
        param_names: ordered list of parameter column names.
        param_values: dict mapping param name to list of allowed values.
        rows: data rows from _build_rows (no header).

    Returns:
        The populated gspread Worksheet.
    """
    try:
        ws = spreadsheet.worksheet(tab_name)
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
        rows = _build_rows(element_index, lang_id, param_names)
        _populate_tab(spreadsheet, construction, param_names, param_values, rows)
        tab_names.append(construction)
        print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")

    # Remove the default empty sheet if it wasn't one of our tabs
    if default_ws.title not in tab_names:
        spreadsheet.del_worksheet(default_ws)

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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding generate-sheets`.

    Iterates over all planar_*.tsv files in coded_data/*/planar_input/, creates
    one Google Sheet per analysis class (skipping existing ones unless --force),
    uploads per-language manifests to Drive, and regenerates contributor notebooks.
    """
    force = "--force" in sys.argv

    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")

    # Connect to Google once for all languages
    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    config = _load_drive_config()
    root_folder_id = config.get("_root_folder_id")

    # Load the existing merged config from Drive (if present) so we can update
    # it incrementally as each language is processed, preserving other languages.
    existing_config_file_id = config.get("_planars_config_file_id")
    if existing_config_file_id:
        try:
            merged_config: Dict = _download_file_json(drive, existing_config_file_id)
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

        # Set DATA_DIR so make_forms resolves files relative to the planar_input folder
        _mf.DATA_DIR = str(planar_dir)
        element_index = build_element_index(planar_file.name)
        specs = _read_diagnostics_for_language(lang_id)

        # Group specs by class_name -> [(construction, param_names, param_values), ...]
        all_classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            all_classes.setdefault(class_name, []).append((construction, param_names, param_values))

        print(f"Classes:     {list(all_classes.keys())}")

        # Load existing data for this language from the merged config or old per-language file.
        existing_lang_data: Dict = merged_config.get(lang_id, {})
        if not existing_lang_data and lang_id in config:
            # Migration: try old-format per-language manifest file
            old_fid = config[lang_id].get("manifest_file_id")
            if old_fid:
                try:
                    existing_lang_data = _download_file_json(drive, old_fid)
                except Exception:
                    pass

        if not force and existing_lang_data:
            existing_sheets = existing_lang_data.get("sheets", {})
            new_class_names = [c for c in all_classes if c not in existing_sheets]
            if not new_class_names:
                print(
                    f"  All classes already have sheets. Skipping {lang_id}.\n"
                    "  (use --force to regenerate)"
                )
                full_manifest[lang_id] = existing_lang_data
                merged_config[lang_id] = existing_lang_data
                continue
            print(f"Existing:    {list(existing_sheets.keys())}")
            print(f"New:         {new_class_names}")

        classes_to_create = {
            k: v for k, v in all_classes.items()
            if k not in existing_lang_data.get("sheets", {})
        } if not force else dict(all_classes)

        # Create language folder inside root folder (if configured), or at Drive root.
        folder_id = _get_or_create_folder(drive, lang_id, parent_id=root_folder_id)
        _share_anyone_with_link(drive, folder_id)
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder:      {folder_url}\n")

        # Build lang_data starting from existing data (or fresh), always include folder_id.
        lang_data: Dict = existing_lang_data or {"folder_url": folder_url, "sheets": {}}
        lang_data["folder_id"] = folder_id

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
        # Remove stale per-language manifest_file_id (superseded by merged config).
        config[lang_id].pop("manifest_file_id", None)
        _save_drive_config(config)
        print(f"planars_config.json updated on Drive (id: {existing_config_file_id})")

    # Write local manifest with all languages (gitignored, kept for reference)
    MANIFEST_PATH.write_text(json.dumps(full_manifest, indent=2), encoding="utf-8")
    print(f"\nLocal manifest written to: {MANIFEST_PATH.name}")
    print(f"drive_config.json updated.")

    print(f"\nShare this folder with your specialist:")
    print(f"  {folder_url}")

    from .generate_notebooks import regenerate_notebooks
    regenerate_notebooks()


def push_manifest() -> None:
    """Upload the existing local sheets_manifest.json to Drive as merged planars_config.json.

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
    print(f"planars_config.json uploaded (id: {file_id})")
    print(f"drive_config.json written.")


if __name__ == "__main__":
    if "--push-manifest" in sys.argv:
        push_manifest()
    else:
        main()
