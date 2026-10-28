"""One-time migration: record in Source that English's phrasal_accent pair
answers of 2026-10-27 were drafted with Claude.

Motivation: Adam filled the 2,268-row phrasal_accent/general tab with his
Claude's help on 2026-10-27 (a week's work by hand, he said); every pair got
an invented example sentence, and nothing on the sheet told those answers
apart from his own judgments. Jeff decided (2026-10-27) to mark them in
Source and ask Adam, on #318, to replace the note with his own source on any
answer he has checked. Only rows with an answer and an empty Source are
marked; nothing else changes.
Run: 2026-10-27.

Usage:
    python migrations/mark_phrasal_accent_drafts_stan1293.py           # dry run
    python migrations/mark_phrasal_accent_drafts_stan1293.py --apply   # write

Post-run checks:
    python -m coding import-sheets --apply --lang stan1293
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive import load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

LANG, CLASS, TAB = "stan1293", "phrasal_accent", "general"
NOTE = "Claude draft (Adam, 2026-10-27)"


def _col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    sheet_id = load_manifest(doorway)[LANG]["sheets"][CLASS]["spreadsheet_id"]
    ws = doorway.open_spreadsheet(sheet_id).worksheet(TAB)
    rows = ws.get_all_values()
    header = rows[0]
    ai, si = header.index("joint_accent"), header.index("Source")
    column, marked = [], 0
    for r in rows[1:]:
        r = r + [""] * (len(header) - len(r))
        if r[ai].strip() and not r[si].strip():
            column.append([NOTE])
            marked += 1
        else:
            column.append([r[si]])
    print(f"{CLASS}_{LANG}/{TAB}: {'marking' if apply else 'would mark'} {marked} "
          f"of {len(rows) - 1} rows")
    if apply and marked:
        col = _col_letter(si + 1)
        ws.update(column, range_name=f"{col}2:{col}{len(rows)}")


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration mark_phrasal_accent_drafts_stan1293",
                            may_write="--apply" in sys.argv):
        main()
