#!/usr/bin/env python3
"""Generate Google Sheets annotation forms from planar structure and diagnostics.

Run from the repo root:
    python generate_sheets.py           # create sheets for new classes only
    python generate_sheets.py --force   # regenerate all (creates duplicates; delete old manually)

On the first run, creates one Google Sheet per analysis class with one tab per construction.
On subsequent runs, only creates sheets for classes not yet in the Drive manifest (e.g. a
newly added aspiration class). Existing sheets are left untouched.

To sync param column changes to existing sheets: python sync_params.py --apply

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
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gspread
from googleapiclient.discovery import build as google_build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

import make_forms as _mf
from make_forms import (
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
    DRIVE_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Drive manifest upload/download
# ---------------------------------------------------------------------------

def _upload_manifest_to_drive(
    drive, lang_data: Dict, folder_id: str, lang_id: str, existing_file_id: str = None
) -> str:
    """Upload manifest_{lang_id}.json to the Drive folder. Returns file ID."""
    import io
    content = json.dumps(lang_data, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
    file_name = f"manifest_{lang_id}.json"
    if existing_file_id:
        drive.files().update(fileId=existing_file_id, media_body=media).execute()
        return existing_file_id
    result = drive.files().create(
        body={"name": file_name, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return result["id"]


def _download_manifest_from_drive(drive, file_id: str) -> Dict:
    """Download and parse a manifest JSON file from Drive."""
    import io
    request = drive.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return json.loads(buffer.getvalue().decode("utf-8"))


def _load_manifest_from_drive(drive) -> Dict:
    """Load the full manifest (all languages) from Drive using drive_config.json."""
    config = _load_drive_config()
    if not config:
        raise SystemExit(
            "drive_config.json not found.\n"
            "Run: python generate_sheets.py --push-manifest\n"
            "to upload the existing sheets_manifest.json to Drive."
        )
    manifest = {}
    for lang_id, lang_config in config.items():
        file_id = lang_config.get("manifest_file_id")
        if not file_id:
            raise SystemExit(f"No manifest_file_id in drive_config.json for '{lang_id}'.")
        manifest[lang_id] = _download_manifest_from_drive(drive, file_id)
    return manifest


# ---------------------------------------------------------------------------
# Drive folder helpers
# ---------------------------------------------------------------------------

def _get_or_create_folder(drive, name: str) -> str:
    """Return the ID of a Drive folder with the given name, creating it if needed."""
    results = drive.files().list(
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
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
    """Build sorted data rows for a sheet tab."""
    items = [
        (pos, element, pos_name)
        for _, (pos, pos_name, lang, element) in element_index.items()
        if lang == lang_id
    ]
    items_sorted = sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))

    rows = []
    for pos, element, pos_name in items_sorted:
        element = element.strip()
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
    """Freeze and bold the header row; apply per-column dropdown validation."""
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
    # One validation request per param column (non-strict so NA in keystone rows is tolerated)
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
    """Create or clear a worksheet tab and populate it with data."""
    try:
        ws = spreadsheet.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=len(param_names) + 3
        )

    all_cols = param_names + _TRAILING_COLS
    header = ["Element", "Position_Name", "Position_Number"] + all_cols
    # Pad data rows with empty trailing columns
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
    force = "--force" in sys.argv

    # Find planar file
    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")
    planar_file = planar_files[0]
    planar_dir = planar_file.parent
    lang_id = _infer_language_id_from_planar_filename(planar_file.name)

    print(f"Language:    {lang_id}")
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

    # Connect to Google
    print("\nConnecting to Google APIs...")
    gc, drive = _get_clients()

    # Determine which classes already have sheets (unless --force)
    existing_lang_data: Dict = {}
    if not force:
        config = _load_drive_config()
        if config and lang_id in config:
            try:
                existing_lang_data = _download_manifest_from_drive(
                    drive, config[lang_id]["manifest_file_id"]
                )
                existing_sheets = existing_lang_data.get("sheets", {})
                new_class_names = [c for c in all_classes if c not in existing_sheets]
                if not new_class_names:
                    print(
                        "\nAll classes already have sheets in the Drive manifest.\n"
                        "  To sync param columns:      python sync_params.py --apply\n"
                        "  To update rows/columns:     python update_sheets.py --apply\n"
                        "  To regenerate from scratch: python generate_sheets.py --force"
                    )
                    return
                print(f"Existing:    {list(existing_sheets.keys())}")
                print(f"New:         {new_class_names}")
            except Exception as exc:
                print(f"Warning: could not load existing manifest ({exc}). Creating all classes.")
                existing_lang_data = {}

    classes_to_create = {
        k: v for k, v in all_classes.items()
        if k not in existing_lang_data.get("sheets", {})
    } if not force else dict(all_classes)

    # Create language folder (finds existing folder if already present)
    folder_name = f"planars \u2014 {lang_id}"
    folder_id = _get_or_create_folder(drive, folder_name)
    _share_anyone_with_link(drive, folder_id)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    print(f"Folder:      {folder_url}\n")

    # Build manifest starting from existing data (or fresh)
    lang_data: Dict = existing_lang_data or {"folder_url": folder_url, "sheets": {}}

    # Create one sheet per new analysis class
    for class_name, constructions in classes_to_create.items():
        sheet_info = _create_analysis_sheet(
            gc, drive, folder_id, lang_id, class_name, constructions, element_index
        )
        lang_data["sheets"][class_name] = sheet_info
        print(f"    URL: {sheet_info['url']}\n")

    manifest = {lang_id: lang_data}

    # Write local manifest (gitignored, kept for reference)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Local manifest written to: {MANIFEST_PATH.name}")

    # Upload manifest to Drive and update drive_config.json
    config = _load_drive_config()
    existing_file_id = config.get(lang_id, {}).get("manifest_file_id")
    manifest_file_id = _upload_manifest_to_drive(
        drive, lang_data, folder_id, lang_id, existing_file_id
    )
    config.setdefault(lang_id, {})["folder_id"] = folder_id
    config[lang_id]["manifest_file_id"] = manifest_file_id
    _save_drive_config(config)
    print(f"Manifest uploaded to Drive (file_id: {manifest_file_id})")
    print(f"drive_config.json updated.")

    print(f"\nShare this folder with your specialist:")
    print(f"  {folder_url}")


def push_manifest() -> None:
    """Upload the existing local sheets_manifest.json to Drive.

    One-time migration utility. Run with:
        python generate_sheets.py --push-manifest
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "sheets_manifest.json not found. Nothing to push.\n"
            "Run generate_sheets.py first to create sheets."
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    config = _load_drive_config()

    for lang_id, lang_data in manifest.items():
        folder_url = lang_data.get("folder_url", "")
        if not folder_url:
            print(f"  {lang_id}: no folder_url in manifest, skipping")
            continue
        folder_id = folder_url.rstrip("/").rsplit("/", 1)[-1]
        existing_file_id = config.get(lang_id, {}).get("manifest_file_id")
        file_id = _upload_manifest_to_drive(drive, lang_data, folder_id, lang_id, existing_file_id)
        config.setdefault(lang_id, {})["folder_id"] = folder_id
        config[lang_id]["manifest_file_id"] = file_id
        print(f"  {lang_id}: manifest uploaded (file_id: {file_id})")

    _save_drive_config(config)
    print(f"drive_config.json written.")


if __name__ == "__main__":
    if "--push-manifest" in sys.argv:
        push_manifest()
    else:
        main()
