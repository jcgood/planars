"""One-time migration: mark English's biuniqueness_deviations `elements` tab
ready-for-review in the sheet's Status tab.

Motivation: the morphemes tab is generated from the elements tab's answers,
and the daily refresh (generate-sheets --regen-dependents) fills an empty
dependent tab only once its source is marked ready-for-review. Adam has
filled elements (co_exponents included, #318 point 13) but not marked it.
Jeff asked for the morphemes tab to be built now (2026-10-22), with
elements marked ready-for-review so the sheet doesn't show a generated tab
next to a source still "in-progress". Status cells are the annotator's, so
the write goes through the Drive door's replacing(). Then
`generate-sheets --regen-dependents` built morphemes (18 rows).
Run: 2026-10-22.

Usage:
    python migrations/mark_biuniqueness_elements_ready_stan1293.py           # dry run
    python migrations/mark_biuniqueness_elements_ready_stan1293.py --apply   # write it

Then:
    python -m coding generate-sheets --regen-dependents   # fills morphemes
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gspread.utils import rowcol_to_a1  # noqa: E402

from coding import drive_door  # noqa: E402
from coding.drive_door import ARCHIVED, STATE_LABEL  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.validate_coding import read_status_tab  # noqa: E402
from planars.schema_values import STATUS_READY  # noqa: E402

LANG, CLASS, TAB = "stan1293", "biuniqueness_deviations", "elements"


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    found = doorway.list_files(
        q=f"properties has {{ key='planars_lang' and value='{LANG}' }} and "
          f"properties has {{ key='planars_class' and value='{CLASS}' }} and trashed=false",
        fields="files(id,name,properties)")
    found = [f for f in found if (f.get("properties") or {}).get(STATE_LABEL) != ARCHIVED]
    if len(found) != 1:
        raise SystemExit(f"expected one {CLASS}_{LANG} sheet, found {len(found)}")
    ss = doorway.open_spreadsheet(found[0]["id"])
    ws, rows = read_status_tab(ss)
    if ws is None:
        raise SystemExit("the sheet has no Status tab")
    r = next((i for i, row in enumerate(rows) if row and row[0] == TAB), None)
    if r is None:
        raise SystemExit(f"the Status tab has no {TAB} row")
    current = rows[r][1] if len(rows[r]) > 1 else ""
    print(f"{ss.title} / Status / {TAB}: {current!r} -> {STATUS_READY!r}")
    if current == STATUS_READY or not apply:
        return
    with drive_door.replacing(ws, "Jeff marked elements ready-for-review so its "
                                  "morphemes tab can be built (2026-10-22, #318)"):
        ws.update([[STATUS_READY]], rowcol_to_a1(r + 1, 2))
    print("  written")


if __name__ == "__main__":
    with drive_door.running("migration mark_biuniqueness_elements_ready_stan1293",
                            may_write="--apply" in sys.argv):
        main()
