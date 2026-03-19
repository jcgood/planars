#!/usr/bin/env python3
"""One-time script to populate Google Sheets with data from existing filled TSVs.

Run from the repo root:
    python -m coding populate-sheets

For each construction in sheets_manifest.json, searches numbered output folders
for a matching filled TSV (any suffix: _filled, _fill, _full) and uploads its
parameter values to the corresponding sheet tab. Picks the TSV with the fewest
blank parameter cells when multiple candidates exist.

Skips constructions where no TSV is found or all candidates are fully blank.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

MANIFEST_PATH = ROOT / "sheets_manifest.json"
_DEFAULT_OAUTH_PATH = Path.home() / ".config" / "planars" / "oauth_credentials.json"
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}
_FILLED_SUFFIXES = ["filled", "fill", "full"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_client() -> gspread.Client:
    """Return an authenticated gspread.Client using OAuth2 user credentials."""
    creds_path = Path(
        os.environ.get("PLANARS_OAUTH_CREDENTIALS", str(_DEFAULT_OAUTH_PATH))
    )
    if not creds_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {creds_path}\n"
            "See coding/generate_sheets.py for setup instructions."
        )
    return gspread.oauth(
        credentials_filename=str(creds_path),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ],
    )


# ---------------------------------------------------------------------------
# TSV candidate search
# ---------------------------------------------------------------------------

def _count_param_cells(path: Path) -> Tuple[int, int]:
    """Return (unannotated_count, total_count) for parameter cells (cols 4+), excluding header.

    Cells that are blank or 'na' (keystone auto-fill) are counted as unannotated.
    """
    unannotated = 0
    total = 0
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, [])
        param_indices = [i for i, c in enumerate(header) if c and c not in _STRUCTURAL_COLS]
        for row in reader:
            for i in param_indices:
                total += 1
                val = row[i].strip().lower() if i < len(row) else ""
                if val in ("", "na"):
                    unannotated += 1
    return unannotated, total


def _find_best_tsv(class_name: str, lang_id: str, construction: str) -> Optional[Tuple[Path, int, int]]:
    """Find the TSV candidate with the fewest blank parameter cells.

    Returns (path, blank_count, total_count) or None if no candidates found.
    """
    candidates = []
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir() or class_name not in folder.name:
            continue
        for suffix in _FILLED_SUFFIXES:
            tsv = folder / f"{class_name}_{lang_id}_{construction}_{suffix}.tsv"
            if tsv.exists():
                candidates.append(tsv)

    if not candidates:
        return None

    scored = [(p, *_count_param_cells(p)) for p in candidates]
    scored.sort(key=lambda t: t[1])
    return scored[0]


# ---------------------------------------------------------------------------
# Sheet upload
# ---------------------------------------------------------------------------

def _upload_tsv_to_tab(ws: gspread.Worksheet, tsv_path: Path) -> int:
    """Replace parameter values in a sheet tab with data from a TSV.

    Matches rows by (Element, Position_Number). Returns count of rows updated.
    Unnamed trailing columns are concatenated with ' | ' into the Comments column.
    """
    # Read TSV into a lookup: (element, pos_num) -> {param: value}
    tsv_data: Dict[Tuple[str, str], Dict[str, str]] = {}
    with tsv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, [])
        named_cols = [c for c in header if c and c not in _STRUCTURAL_COLS]
        unnamed_indices = [i for i, c in enumerate(header) if not c]
        for row in reader:
            while len(row) < len(header):
                row.append("")
            element = row[header.index("Element")].strip() if "Element" in header else ""
            pos_num = str(row[header.index("Position_Number")]).strip() if "Position_Number" in header else ""
            key = (element, pos_num)
            record = {c: row[header.index(c)].strip() for c in named_cols if c in header}
            # Concatenate unnamed trailing columns into Comments
            unnamed_vals = [row[i].strip() for i in unnamed_indices if i < len(row) and row[i].strip()]
            if unnamed_vals:
                record["Comments"] = " | ".join(unnamed_vals)
            tsv_data[key] = record

    # Read current sheet
    sheet_rows = ws.get_all_values()
    if not sheet_rows:
        return 0
    header = sheet_rows[0]
    param_cols = [c for c in header if c and c not in _STRUCTURAL_COLS]
    if not param_cols:
        return 0

    col_index = {name: i for i, name in enumerate(header)}

    # Build update: list of (row_idx, col_idx, value) — 1-based for gspread
    updates = []
    updated_rows = 0
    for row_idx, row in enumerate(sheet_rows[1:], start=2):
        while len(row) < len(header):
            row.append("")
        element = row[col_index.get("Element", 0)].strip() if "Element" in col_index else ""
        pos_num = row[col_index.get("Position_Number", 2)].strip() if "Position_Number" in col_index else ""
        key = (element, pos_num)
        tsv_row = tsv_data.get(key)
        if tsv_row is None:
            continue
        for param in param_cols:
            val = tsv_row.get(param, "").strip()
            if val:
                col_idx = col_index.get(param)
                if col_idx is not None:
                    updates.append(gspread.Cell(row_idx, col_idx + 1, val))
        updated_rows += 1

    if updates:
        ws.update_cells(updates)

    return updated_rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding populate-sheets` (one-time legacy upload).

    Reads sheets_manifest.json, searches numbered output folders for filled TSVs
    matching each construction, selects the candidate with the fewest blank cells,
    and uploads parameter values to the corresponding sheet tab.
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"sheets_manifest.json not found at {MANIFEST_PATH}.\n"
            "Run python -m coding generate-sheets first."
        )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    print("Connecting to Google...")
    gc = _get_client()

    for lang_id, lang_data in manifest.items():
        print(f"\nLanguage: {lang_id}")

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = gc.open_by_key(sheet_info["spreadsheet_id"])

            for construction in sheet_info["constructions"]:
                result = _find_best_tsv(class_name, lang_id, construction)
                if result is None:
                    print(f"    [{construction}] no TSV found, skipping")
                    continue

                tsv_path, blank_count, total_count = result

                if blank_count == total_count:
                    print(f"    [{construction}] {tsv_path.name} is fully blank — no annotation data to upload, skipping")
                    continue

                if blank_count > 0:
                    print(f"    [{construction}] {tsv_path.name} ({blank_count}/{total_count} param cells blank)")
                else:
                    print(f"    [{construction}] {tsv_path.name} (complete)")

                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    print(f"    [{construction}] WARNING: tab '{construction}' not found in sheet — check that the tab was not left as 'Sheet1' or renamed")
                    continue

                updated = _upload_tsv_to_tab(ws, tsv_path)
                print(f"    [{construction}] uploaded {updated} rows → {sheet_info['url']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
