#!/usr/bin/env python3
"""One-time migration: rename v:verbroot → v:verbstem in all Google Sheets.

Run from the repo root:
    python migrate_verbroot_to_verbstem.py           # dry run (lists affected sheets)
    python migrate_verbroot_to_verbstem.py --apply   # apply changes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from coding.generate_sheets import _get_clients, _load_manifest_from_drive
from googleapiclient.discovery import build as google_build

DRY_RUN = "--apply" not in sys.argv


def find_replace_in_sheet(sheets_service, spreadsheet_id: str, dry_run: bool) -> int:
    """Replace v:verbroot with v:verbstem in all cells of a spreadsheet.

    Returns the number of replacements made (or that would be made).
    """
    if dry_run:
        # Use findReplace in dry-run mode to count matches without changing anything
        result = sheets_service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=["A:Z"],
            valueRenderOption="FORMATTED_VALUE",
        ).execute()
        count = 0
        for vr in result.get("valueRanges", []):
            for row in vr.get("values", []):
                for cell in row:
                    if "v:verbroot" in str(cell):
                        count += 1
        return count
    else:
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [{
                    "findReplace": {
                        "find": "v:verbroot",
                        "replacement": "v:verbstem",
                        "matchCase": False,
                        "searchByRegex": False,
                        "allSheets": True,
                    }
                }]
            },
        ).execute()
        replies = result.get("replies", [{}])
        fr = replies[0].get("findReplace", {}) if replies else {}
        return fr.get("occurrencesChanged", 0)


def main():
    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    sheets_service = google_build("sheets", "v4", credentials=gc.http_client.auth)

    manifest = _load_manifest_from_drive(drive)
    if not manifest:
        raise SystemExit("No manifest found. Run generate-sheets first.")

    total = 0
    for lang_id, lang_data in sorted(manifest.items()):
        sheets = lang_data.get("sheets", {})
        for class_name, sheet_info in sorted(sheets.items()):
            sid = sheet_info.get("spreadsheet_id") or sheet_info.get("id")
            if not sid:
                print(f"  [{lang_id}/{class_name}] no spreadsheet_id — skipping")
                continue
            count = find_replace_in_sheet(sheets_service, sid, DRY_RUN)
            label = f"{'would change' if DRY_RUN else 'changed'}"
            if count:
                print(f"  [{lang_id}/{class_name}] {label} {count} cell(s)  ({sheet_info.get('url','')})")
                total += count
            else:
                print(f"  [{lang_id}/{class_name}] no occurrences")

    if DRY_RUN:
        print(f"\nDry run: {total} cell(s) would be updated. Re-run with --apply to apply.")
    else:
        print(f"\nDone: {total} cell(s) updated across all sheets.")


if __name__ == "__main__":
    main()
