"""One-time migration: set English's stress_domain keystone 'independence' back to 'na'.

Motivation: the keystone row (v:verbstem) of metrical/stress_domain in the
English class sheet held 'n' in 'independence' from about 2026-10-14 (the
daily import of 2026-10-15 brought it in; it had been 'na' since April).
'independence' asks whether an element's stress is independent of the
keystone, so on the keystone's own row it can only be 'na'; validation has
reported it as an error since 2026-10-19 (#316). Spans were unaffected: the
module blocks only on 'y'. Jeff decided (2026-11-07) to correct it himself
rather than wait for the annotator. The cell is written through the Drive
door as replacing the annotator's value (snapshot saved, reason in the
provenance log); nothing else on the tab changes.
Run: 2026-11-07.

Usage:
    python migrations/fix_keystone_independence_stan1293.py           # dry run
    python migrations/fix_keystone_independence_stan1293.py --apply   # write

Post-run checks:
    python -m coding import-sheets --apply --lang stan1293
    python -m coding validate-coding --lang stan1293
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive, drive_door, drive_ids  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

LANG, CLASS, TAB = "stan1293", "metrical", "stress_domain"
ELEMENT, POSITION, CRITERION = "KEYSTONE", "v:verbstem", "independence"
OLD, NEW = "n", "na"
REASON = ("keystone 'independence' compares the keystone with itself, so it is "
          "'na' (Jeff, 2026-11-07, #316)")


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    sheet_id = drive_ids.class_sheets(drive._load_drive_config(), LANG)[CLASS]
    ws = doorway.open_spreadsheet(sheet_id).worksheet(TAB)
    rows = ws.get_all_values()
    header = [h.strip() for h in rows[0]]
    ei, pi, ci = header.index("Element"), header.index("Position_Name"), header.index(CRITERION)
    found = [(r, row) for r, row in enumerate(rows[1:], start=2)
             if row[ei].strip() == ELEMENT and row[pi].strip() == POSITION]
    if len(found) != 1:
        sys.exit(f"Expected one {ELEMENT} row at {POSITION}; found {len(found)}.")
    r, row = found[0]
    current = row[ci].strip() if ci < len(row) else ""
    where = f"{CLASS}_{LANG}/{TAB} row {r} ({ELEMENT}), '{CRITERION}'"
    if current == NEW:
        print(f"{where} is already '{NEW}'; nothing to do.")
        return
    if current != OLD:
        sys.exit(f"{where} is '{current}', not '{OLD}'; someone changed it. Look before writing.")
    if not apply:
        print(f"Would set {where}: '{OLD}' -> '{NEW}'. Add --apply to write it.")
        return
    with drive_door.replacing(ws, REASON):
        ws.update_cell(r, ci + 1, NEW)
    print(f"Set {where}: '{OLD}' -> '{NEW}'.")


if __name__ == "__main__":
    with drive_door.running("migration fix_keystone_independence_stan1293",
                            may_write="--apply" in sys.argv):
        main()
