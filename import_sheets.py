#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python import_sheets.py           # skip files that already exist
    python import_sheets.py --force   # overwrite existing files

Reads sheets_manifest.json, downloads each sheet tab, validates values,
and writes {class}_{lang}_{construction}_filled.tsv to the appropriate
numbered output folder (e.g. 02_ciscategorial_output/).

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "01_planar_input"))

import gspread

MANIFEST_PATH = ROOT / "sheets_manifest.json"
_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"

_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}
_EXPECTED_VALUES = {"y", "n", "na", "?"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_client() -> gspread.Client:
    creds_path = Path(
        os.environ.get("PLANARS_OAUTH_CREDENTIALS", str(_DEFAULT_OAUTH_PATH))
    )
    if not creds_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {creds_path}\n"
            "See generate_sheets.py for setup instructions."
        )
    return gspread.oauth(
        credentials_filename=str(creds_path),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ],
    )


# ---------------------------------------------------------------------------
# Output folder
# ---------------------------------------------------------------------------

def _find_output_folder(class_name: str) -> Path:
    """Find the numbered output folder for a class, or create one."""
    matches = sorted(p for p in ROOT.iterdir() if p.is_dir() and class_name in p.name)
    if matches:
        return matches[0]
    folder = ROOT / f"{class_name}_output"
    folder.mkdir(exist_ok=True)
    print(f"    Created output folder: {folder.name}/")
    return folder


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
) -> Tuple[List[Dict], List[str]]:
    """Validate sheet rows and return (records, warnings).

    records: list of dicts ready to write as TSV rows
    warnings: list of human-readable issue strings
    """
    warnings: List[str] = []

    if not rows:
        return [], [f"{tab_name}: sheet is empty"]

    header = rows[0]
    data_rows = rows[1:]

    # Check structural columns
    for col in ("Element", "Position_Name", "Position_Number"):
        if col not in header:
            warnings.append(f"{tab_name}: missing structural column '{col}'")

    # Check parameter columns match expected
    actual_params = [c for c in header if c not in _STRUCTURAL_COLS]
    if actual_params != expected_params:
        warnings.append(
            f"{tab_name}: parameter columns differ from manifest. "
            f"Expected {expected_params}, got {actual_params}"
        )

    col_index = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS]

    records = []
    for row_num, row in enumerate(data_rows, start=2):  # 2 = first data row in sheet
        # Pad short rows
        while len(row) < len(header):
            row.append("")

        record = {col: row[col_index[col]] for col in header if col in col_index}
        pos_name = record.get("Position_Name", "").strip()
        is_keystone = pos_name.lower() == "v:verbroot"

        for param in param_cols:
            val = record.get(param, "").strip().lower()
            record[param] = val  # normalize in-place

            if is_keystone:
                # Keystone rows should be NA; fill if blank
                if val == "":
                    record[param] = "na"
            else:
                if val == "":
                    warnings.append(
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}': "
                        f"blank value in '{param}'"
                    )
                elif val not in _EXPECTED_VALUES:
                    warnings.append(
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}': "
                        f"unexpected value '{val}' in '{param}'"
                    )

        records.append(record)

    return records, warnings


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _write_tsv(path: Path, header: List[str], records: List[Dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, delimiter="\t",
            extrasaction="ignore", quoting=csv.QUOTE_NONE,
        )
        writer.writeheader()
        writer.writerows(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    force = "--force" in sys.argv

    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"sheets_manifest.json not found at {MANIFEST_PATH}.\n"
            "Run generate_sheets.py first."
        )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    print("Connecting to Google...")
    gc = _get_client()

    total_files = 0
    total_warnings = 0

    for lang_id, lang_data in manifest.items():
        print(f"\nLanguage: {lang_id}")

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = gc.open_by_key(sheet_info["spreadsheet_id"])
            out_folder = _find_output_folder(class_name)

            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    print(f"    [{construction}] WARNING: tab not found in sheet, skipping")
                    continue

                rows = ws.get_all_values()

                # Determine expected params from header row (skip structural cols)
                expected_params = (
                    [c for c in rows[0] if c not in _STRUCTURAL_COLS] if rows else []
                )
                header = rows[0] if rows else []

                records, warnings = _validate_tab(rows, expected_params, construction)

                for w in warnings:
                    print(f"    WARNING: {w}")
                total_warnings += len(warnings)

                out_name = f"{class_name}_{lang_id}_{construction}_filled.tsv"
                out_path = out_folder / out_name

                if out_path.exists() and not force:
                    print(f"    [{construction}] SKIPPED (file exists, use --force to overwrite) → {out_folder.name}/{out_name}")
                    continue

                _write_tsv(out_path, header, records)

                blank_count = sum(
                    1 for r in records
                    if r.get("Position_Name", "").lower() != "v:verbroot"
                    and any(r.get(p, "") == "" for p in expected_params)
                )
                status = f"{len(records)} rows"
                if blank_count:
                    status += f", {blank_count} blank param cells"
                print(f"    [{construction}] {status} → {out_folder.name}/{out_name}")
                total_files += 1

    print(f"\nDone. {total_files} file(s) written, {total_warnings} warning(s).")


if __name__ == "__main__":
    main()
