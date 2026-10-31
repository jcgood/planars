"""One-time migration: add the "edited by" column to every language's change log.

What it does: each ``coded_data/{lang}/changes.tsv`` whose header is the old
six columns (when, file, what changed, by, why, previous version) gets a
seventh, ``edited by``, with every existing line's cell left empty.

Why: Phase 10 unit 16c (docs/plain-record-design.md § 3.3) names, on each
change-log line, who edited the Drive file it was read from. The local-file
door refuses to append to a log whose header is not
``file_door.CHANGE_LOG_COLUMNS``, so this runs before the code that writes
the column reaches the daily refresh.

Run: 2026-10-31, with unit 16c.

Usage:
    python migrations/add_edited_by_to_change_logs.py           # dry run
    python migrations/add_edited_by_to_change_logs.py --apply   # rewrite the logs

Then commit and push the logs in coded_data/.

Post-run checks:
    python -m coding integrity-check
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import file_door  # noqa: E402

OLD = ("when (UTC)", "file", "what changed", "by", "why", "previous version")


def main(apply: bool) -> None:
    for log in sorted(file_door.CODED_DATA.glob(f"*/{file_door.CHANGE_LOG_NAME}")):
        if log.parent.name.startswith("."):
            continue
        with open(log, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter="\t"))
        header = tuple(rows[0]) if rows else ()
        if header == file_door.CHANGE_LOG_COLUMNS:
            print(f"{log.parent.name}: already has the column")
            continue
        if header != OLD:
            sys.exit(f"{log}: unexpected header {list(header)}; nothing changed.")
        out = io.StringIO()
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(file_door.CHANGE_LOG_COLUMNS)
        for row in rows[1:]:
            writer.writerow(row + [""] * (len(file_door.CHANGE_LOG_COLUMNS) - len(row)))
        print(f"{log.parent.name}: {'added' if apply else 'would add'} the column "
              f"({len(rows) - 1} lines)")
        if apply:
            log.write_text(out.getvalue(), encoding="utf-8")


if __name__ == "__main__":
    main("--apply" in sys.argv)
