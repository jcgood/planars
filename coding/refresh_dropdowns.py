"""Make every class sheet's dropdowns match the codebook, without touching data.

Reads each sheet's real dropdowns and compares each column with its spec
(``sheet_spec.class_sheet_spec``: a criterion's allowed values from the
diagnostics YAML, no dropdown on the row columns, Example/Source/Comments, or
a criterion whose values include a placeholder such as <position_number>,
``schemas.dropdown_values``; the Status column's values on the Status tab).
A column whose dropdown differs on any data row is rewritten whole, or its
dropdown removed. Runs daily in the refresh, so a sheet can't keep offering a
list the codebook has moved past (#322: the English sheets still offered the
y/n default list removed 2026-10-12, so annotators couldn't pick both, na or
unclear, and a typed position number showed as invalid). Until 2026-10-23
this command compared a copy of the values kept in the manifest with the
YAML and never looked at the sheet; that copy is gone, and this command
writes only dropdowns. The sheets to check are the ones in the ID file.

Run from the repo root:
    python -m coding refresh-dropdowns           # dry run: list what differs
    python -m coding refresh-dropdowns --apply   # fix it
    python -m coding refresh-dropdowns --lang stan1293 --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from . import drive, drive_ids
from .drive_doorway import get_doorway
from .generate_sheets import dropdown_request
from .sheet_spec import STATUS, ClassSheetSpec, class_sheet_spec


_DROPDOWN_FIELDS = ("sheets(properties(title,sheetId,gridProperties(rowCount)),"
                    "data(rowData(values(formattedValue,dataValidation))))")


def _offered(cell: dict) -> Optional[Tuple[str, ...]]:
    """The values a cell's dropdown offers, None when it has none."""
    rule = cell.get("dataValidation")
    if not rule:
        return None
    return tuple(v.get("userEnteredValue", "")
                 for v in rule.get("condition", {}).get("values", []))


def _describe(values: Optional[Tuple[str, ...]]) -> str:
    return ", ".join(values) if values else "no dropdown"


def wrong_dropdowns(ss, spec: ClassSheetSpec) -> List[Tuple[str, dict]]:
    """Each column of ``ss`` whose dropdown differs from ``spec`` on any row
    with something in its first column: ``(message, request)``, the request
    rewriting the whole column. One read per spreadsheet."""
    meta = ss.fetch_sheet_metadata(params={"includeGridData": "true",
                                           "fields": _DROPDOWN_FIELDS})
    by_title = {t.title: t for t in spec.tabs if t.columns}
    out = []
    for sheet in meta.get("sheets", []):
        props = sheet["properties"]
        tab = by_title.get(props["title"])
        if tab is None:
            continue
        rows = (sheet.get("data") or [{}])[0].get("rowData", [])
        if len(rows) < 2:
            continue
        header = [c.get("formattedValue", "") for c in rows[0].get("values", [])]
        data = [r.get("values", []) for r in rows[1:]
                if r.get("values") and r["values"][0].get("formattedValue", "")]
        end_row = props.get("gridProperties", {}).get("rowCount", len(rows))
        for col in tab.columns:
            if col.name not in header:
                continue  # a missing or extra column is the door's and sheet-drift's to report
            c = header.index(col.name)
            seen = {_offered(r[c] if c < len(r) else {}) for r in data}
            if not seen or seen == {col.allowed}:
                continue
            now = " / ".join(sorted(_describe(v) for v in seen))
            request = dropdown_request(props["sheetId"], c, end_row, col.allowed,
                                       strict=tab.kind == STATUS)
            out.append((f"{tab.title} '{col.name}': {now} → {_describe(col.allowed)}", request))
    return out


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding refresh-dropdowns`."""
    ap = argparse.ArgumentParser(
        description="Refresh criterion dropdown validation on existing sheets."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="push updated dropdowns (default: dry run)",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    lang_filter = args.lang

    doorway = get_doorway()
    config = drive._load_drive_config()

    print(f"{'DRY RUN — ' if not apply else ''}Refreshing sheet dropdowns")
    if not apply:
        print("(run with --apply to push changes)\n")

    any_changes = False
    failed: List[str] = []

    for lang_id in drive_ids.languages(config):
        if lang_filter and lang_id != lang_filter:
            continue
        sheets = drive_ids.class_sheets(config, lang_id)
        if not sheets:
            continue

        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        if not list(lang_setup_dir.glob("planar_*.tsv")):
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue

        for class_name, spreadsheet_id in sheets.items():
            print(f"\n  [{lang_id}] {class_name}")
            try:
                spec = class_sheet_spec(lang_id, class_name, CODED_DATA)
            except Exception as e:
                print(f"    No spec for this sheet ({e})")
                failed.append(f"{lang_id}/{class_name}")
                continue
            try:
                ss = doorway.open_spreadsheet(spreadsheet_id)
            except Exception as e:
                print(f"    Could not open spreadsheet: {e}")
                failed.append(f"{lang_id}/{class_name}")
                continue

            fixes = wrong_dropdowns(ss, spec)
            for message, _ in fixes:
                print(f"    {message}")
            if not fixes:
                print("    dropdowns match")
            any_changes = any_changes or bool(fixes)
            if apply and fixes:
                ss.batch_update({"requests": [request for _, request in fixes]})

    if not apply:
        if any_changes:
            print("\nRun with --apply to fix these dropdowns.")
        else:
            print("\nAll dropdowns match the codebook.")

    if failed:
        print(f"\nNot checked: {', '.join(failed)}")
        sys.exit(1)
    print("\nDone.")
