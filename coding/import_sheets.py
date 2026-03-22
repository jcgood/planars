#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python -m coding import-sheets           # skip files that already exist
    python -m coding import-sheets --force   # overwrite existing files

Reads the manifest from Drive (via drive_config.json), downloads each sheet
tab, validates values, and writes {construction}.tsv to
coded_data/{lang_id}/{class_name}/.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from .generate_sheets import _get_clients, _load_manifest_from_drive, _open_spreadsheet
from . import validate_coding as _val

ERROR_DIR = ROOT / "import_errors"

# Re-export constants so external code that imported them directly still works.
_STRUCTURAL_COLS  = _val._STRUCTURAL_COLS
_TRAILING_COLS    = _val._TRAILING_COLS
_DEFAULT_EXPECTED = _val._DEFAULT_EXPECTED


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """Return the output TSV path under coded_data/, creating directories as needed."""
    folder = ROOT / "coded_data" / lang_id / class_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{construction}.tsv"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _highlight_invalid_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Delegate to validate.highlight_cells (kept for backwards compatibility)."""
    _val.highlight_cells(ws, bad_cells)


def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
) -> Tuple[List[Dict], List[str], List[Tuple[int, int]]]:
    """Delegate to validate.validate_annotation_rows (kept for backwards compatibility).

    Returns (records, warnings, bad_cells) in the original format.
    """
    records, issues = _val.validate_annotation_rows(
        rows, expected_params, tab_name, param_values
    )
    warnings  = [str(i) for i in issues]
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, warnings, bad_cells


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _write_tsv(path: Path, header: List[str], records: List[Dict]) -> None:
    """Write records to a tab-separated file with the given header order.

    Extra keys in records beyond the header are silently ignored
    (extrasaction='ignore').
    """
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, delimiter="\t",
            extrasaction="ignore", quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_error_report(lang_id: str, lines: List[str], timestamp: str) -> Path:
    """Write warning lines to import_errors/{lang_id}_{timestamp}.txt."""
    ERROR_DIR.mkdir(exist_ok=True)
    report_path = ERROR_DIR / f"{lang_id}_{timestamp}.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> None:
    """Entry point for `python -m coding import-sheets`.

    Loads the manifest from Drive, downloads each construction tab, validates
    values, and writes filled TSVs under coded_data/{lang_id}/{class_name}/.
    Skips existing files unless --force is passed. Writes an error report to
    import_errors/ if any warnings are generated.
    """
    force = "--force" in sys.argv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("Connecting to Google...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    total_files = 0
    total_warnings = 0

    for lang_id, lang_data in manifest.items():
        print(f"\nLanguage: {lang_id}")
        lang_warning_lines: List[str] = []

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    msg = f"[{class_name}/{construction}] tab not found in sheet, skipping"
                    print(f"    WARNING: {msg}")
                    lang_warning_lines.append(f"WARNING: {msg}")
                    total_warnings += 1
                    continue

                rows = ws.get_all_values()

                # Determine expected params from header row (skip structural cols)
                expected_params = (
                    [c for c in rows[0] if c not in _STRUCTURAL_COLS] if rows else []
                )
                header = rows[0] if rows else []

                # Per-param allowed values from manifest (if present)
                construction_params = sheet_info.get("construction_params", {})
                param_values = construction_params.get(construction, {}).get("param_values")

                records, warnings, bad_cells = _validate_tab(rows, expected_params, construction, param_values)

                if bad_cells:
                    try:
                        _highlight_invalid_cells(ws, bad_cells)
                    except Exception as e:
                        print(f"    WARNING: could not highlight cells: {e}")

                for w in warnings:
                    print(f"    WARNING: {w}")
                    lang_warning_lines.append(f"[{class_name}/{construction}] {w}")
                total_warnings += len(warnings)

                out_path = _get_output_path(lang_id, class_name, construction)
                out_name = out_path.name

                if out_path.exists() and not force:
                    print(f"    [{construction}] SKIPPED (file exists, use --force to overwrite) → coded_data/{lang_id}/{class_name}/{out_name}")
                    continue

                _write_tsv(out_path, header, records)

                # Count non-keystone rows that still have at least one blank param cell,
                # so the status line can warn the user about incomplete annotations.
                blank_count = sum(
                    1 for r in records
                    if r.get("Position_Name", "").lower() != "v:verbstem"
                    and any(r.get(p, "") == "" for p in expected_params)
                )
                status = f"{len(records)} rows"
                if blank_count:
                    status += f", {blank_count} blank param cells"
                print(f"    [{construction}] {status} → coded_data/{lang_id}/{class_name}/{out_name}")
                total_files += 1

        if lang_warning_lines:
            report_path = _write_error_report(lang_id, lang_warning_lines, timestamp)
            print(f"\n  Error report: {report_path.relative_to(ROOT)}")

    print(f"\nDone. {total_files} file(s) written, {total_warnings} warning(s).")


if __name__ == "__main__":
    main()
