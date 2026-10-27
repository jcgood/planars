"""One-time migration: fill the Status tab's new Marked by column for the
tabs the tooling or the coordinator marked ready-for-review before the
column existed.

Motivation: Jeff asked (2026-10-26) to track which tabs an annotator marked
ready-for-review by hand and which were marked for them. From now on the
tooling writes Marked by whenever it marks a tab, and the daily check writes
'annotator' beside any ready tab it didn't mark (validate_coding
.record_marked_by). Tabs marked before the column existed would all read as
the annotator's, so this records the ones that weren't:
  - coordinator: stan1293 biuniqueness_deviations/elements (migration
    mark_biuniqueness_elements_ready_stan1293, 2026-10-22); morphemes and
    phrasal_accent/prescreening (set-tab-status, 2026-10-26);
  - check: the eight tabs the daily check marked on 2026-10-26.
Run after `update-sheets --apply` adds the column, before the next
validate-coding. Run: 2026-10-26.

Usage:
    python migrations/backfill_marked_by.py           # dry run
    python migrations/backfill_marked_by.py --apply   # write it

Post-run checks:
    python -m coding validate-coding   # fills 'annotator' beside the other ready tabs
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive_door  # noqa: E402
from coding.drive import load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.validate_coding import marked_by_text, read_status_tab  # noqa: E402
from planars.schema_values import (  # noqa: E402
    MARKED_BY_CHECK, MARKED_BY_COORDINATOR, STATUS_CONSTRUCTION_COLUMN,
    STATUS_MARKED_BY_COLUMN, STATUS_READY, STATUS_STATUS_COLUMN,
)

D22, D26 = datetime.date(2026, 10, 22), datetime.date(2026, 10, 26)
MARKS = {  # (lang, class): {construction: (by, date)}
    ("stan1293", "biuniqueness_deviations"): {
        "elements": (MARKED_BY_COORDINATOR, D22), "morphemes": (MARKED_BY_COORDINATOR, D26)},
    ("stan1293", "phrasal_accent"): {"prescreening": (MARKED_BY_COORDINATOR, D26)},
    ("stan1293", "ciscategorial"): {"general": (MARKED_BY_CHECK, D26)},
    ("stan1293", "coreference"): {c: (MARKED_BY_CHECK, D26) for c in (
        "prescreening", "reflexive_coreference", "pronoun_coreference", "np_coreference")},
    ("stan1293", "nonpermutability"): {"general": (MARKED_BY_CHECK, D26)},
    ("stan1293", "proform"): {"do_so_substitution": (MARKED_BY_CHECK, D26)},
    ("arao1248", "subspanrepetition"): {c: (MARKED_BY_CHECK, D26) for c in (
        "auxiliary_construction", "tso_clause_linkage")},
}


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    manifest = load_manifest(doorway)
    for (lang, class_name), tabs in MARKS.items():
        ss = doorway.open_spreadsheet(manifest[lang]["sheets"][class_name]["spreadsheet_id"])
        ws, rows = read_status_tab(ss)
        header = [h.strip() for h in rows[0]] if rows else []
        if STATUS_MARKED_BY_COLUMN not in header:
            raise SystemExit(f"{lang} {class_name}: no '{STATUS_MARKED_BY_COLUMN}' column; "
                             f"run python -m coding update-sheets --apply first")
        ci, si, mi = (header.index(c) for c in (
            STATUS_CONSTRUCTION_COLUMN, STATUS_STATUS_COLUMN, STATUS_MARKED_BY_COLUMN))
        for r, row in enumerate(rows[1:], start=2):
            name = row[ci].strip() if ci < len(row) else ""
            if name not in tabs:
                continue
            status = row[si].strip() if si < len(row) else ""
            current = row[mi].strip() if mi < len(row) else ""
            want = marked_by_text(*tabs[name])
            if status != STATUS_READY:
                print(f"{lang} {class_name}/{name}: now {status!r}, left alone")
                continue
            if current == want:
                continue
            print(f"{lang} {class_name}/{name}: Marked by {current!r} -> {want!r}")
            if apply:
                ws.update_cell(r, mi + 1, want)


if __name__ == "__main__":
    with drive_door.running("migration backfill_marked_by", may_write="--apply" in sys.argv):
        main()
