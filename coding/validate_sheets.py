#!/usr/bin/env python3
"""Re-validate annotation sheets and update cell highlighting in Google Sheets.

Run from the repo root:
    python -m coding validate-sheets                   # all languages
    python -m coding validate-sheets --lang arao1248   # one language

For each annotation sheet, reads current cell values, re-runs validation,
clears stale pink highlights, and re-highlights any remaining invalid cells.
Prints an issue summary to the terminal.

Collaborators can use this to clear pink cells as they fix errors, without
waiting for the coordinator to run import-sheets. (Closes #49)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .generate_sheets import (
    _get_clients,
    _load_manifest_from_drive,
    _open_spreadsheet,
)
from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from . import make_forms as _mf
from . import validate as _val


def _load_param_map(lang_id: str) -> Dict[str, Dict[str, dict]]:
    """Return {class_name: {construction: {params, values}}} for a language."""
    planar_files = sorted((CODED_DATA / lang_id / "planar_input").glob("planar_*.tsv"))
    if not planar_files:
        return {}
    _mf.DATA_DIR = str(planar_files[0].parent)
    inferred = _infer_language_id_from_planar_filename(planar_files[0].name)
    param_map: Dict[str, Dict[str, dict]] = {}
    for class_name, construction, param_names, param_values in _read_diagnostics_for_language(inferred):
        param_map.setdefault(class_name, {})[construction] = {
            "params": param_names,
            "values": param_values,
        }
    return param_map


def main() -> None:
    args = sys.argv[1:]
    lang_filter = args[args.index("--lang") + 1] if "--lang" in args else None

    # Warn if pending destructive changes exist
    pending = ROOT / "pending_changes.json"
    if pending.exists() and pending.stat().st_size > 2:
        print("WARNING: Pending destructive changes require coordinator approval.")
        print("         Run: python -m coding apply-pending\n")

    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)
    if not manifest:
        raise SystemExit("No manifest found. Run generate-sheets first.")

    total_issues = 0
    total_sheets = 0

    for lang_id, lang_data in sorted(manifest.items()):
        if lang_filter and lang_id != lang_filter:
            continue

        param_map = _load_param_map(lang_id)
        if not param_map:
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue

        print(f"\n{lang_id}")

        # Validate planar structure.
        planar_files = sorted((CODED_DATA / lang_id / "planar_input").glob("planar_*.tsv"))
        if planar_files:
            planar_df = pd.read_csv(planar_files[0], sep="\t")
            planar_issues = _val.validate_planar_df(planar_df)
            if planar_issues:
                print(f"  Planar validation ({len(planar_issues)} issue(s)):")
                for issue in planar_issues:
                    print(f"    {issue}")
        for class_name, sheet_info in sorted(lang_data.get("sheets", {}).items()):
            sid = sheet_info.get("spreadsheet_id") or sheet_info.get("id")
            if not sid:
                continue
            try:
                ss = _open_spreadsheet(gc, sid)
            except Exception as e:
                print(f"  [{class_name}] could not open spreadsheet: {e}")
                continue

            for ws in ss.worksheets():
                construction = ws.title
                info = param_map.get(class_name, {}).get(construction, {})
                issues = _val.revalidate_sheet(
                    ws,
                    info.get("params", []),
                    info.get("values", {}),
                )
                total_sheets += 1
                total_issues += len(issues)
                if issues:
                    print(f"  [{class_name}/{construction}] {len(issues)} issue(s):")
                    for issue in issues:
                        print(f"    {issue}")
                else:
                    print(f"  [{class_name}/{construction}] no issues")

    print(f"\n{'─' * 50}")
    print(f"Validated {total_sheets} sheet(s).  Total issues: {total_issues}")
    if total_issues:
        print("Cell highlighting updated in Google Sheets.")
    else:
        print("All highlights cleared.")


if __name__ == "__main__":
    main()
