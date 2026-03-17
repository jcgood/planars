#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python import_sheets.py           # skip files that already exist
    python import_sheets.py --force   # overwrite existing files

Reads the manifest from Drive (via drive_config.json), downloads each sheet
tab, validates values, and writes {construction}_filled.tsv to
coded_data/{lang_id}/{class_name}/.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent

import gspread

from generate_sheets import _get_clients, _load_manifest_from_drive

ERROR_DIR = ROOT / "import_errors"

_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}
_TRAILING_COLS = {"Comments"}   # free-text; never validated for blank or allowed values
_DEFAULT_EXPECTED = {"y", "n", "na", "?"}


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """Return the output TSV path under coded_data/, creating directories as needed."""
    folder = ROOT / "coded_data" / lang_id / class_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{construction}_filled.tsv"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
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
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]

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

            allowed = (
                {v.lower() for v in (param_values or {}).get(param, [])} | {"na", "?"}
                if param_values and param in param_values
                else _DEFAULT_EXPECTED
            )

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
                elif val not in allowed:
                    warnings.append(
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}': "
                        f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})"
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
            ss = gc.open_by_key(sheet_info["spreadsheet_id"])

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

                records, warnings = _validate_tab(rows, expected_params, construction, param_values)

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

                blank_count = sum(
                    1 for r in records
                    if r.get("Position_Name", "").lower() != "v:verbroot"
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
