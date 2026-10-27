"""One-time migration: put English's phrasal_accent sheet back in the shape
the tooling reads, keeping Adam's new answers.

Motivation: on 2026-10-27 (10:58-11:47 UTC, Drive revision history) Adam,
working with his Claude to fill the 2,268-row pair tab, left the sheet with
its `prescreening` and `general` tabs gone, a tab `general_filled` holding
the pairs with 1,417 new joint_accent answers, the Example column split into
`Example-shared` and `Example-independent`, and the sheet shared with
anyone who has the link (writer). The daily import then skipped both tabs
(#328), and integrity-check flagged the link share (#330). Jeff approved the
repair, 2026-10-27.

What it does (each step is skipped if already done):
  1. renames `general_filled` to `general`;
  2. folds the two Example columns into the one `Example` column the schema
     has (schemas/planar.yaml trailing_columns): where a row has both, the
     cell reads "shared: ... | independent: ..."; where it has only the
     shared one, that text is kept as it is. Nothing is dropped;
  3. rebuilds `prescreening` with the same builder update-sheets uses for a
     new tab, then fills its answers, Example, Source and Comments from
     coded_data/stan1293/phrasal_accent/prescreening.tsv (last imported
     2026-10-23, unchanged on the sheet since);
  4. puts the tabs in the diagnostics file's order;
  5. takes the link share off (named people keep their access).
Run: 2026-10-27 (three passes: the door first refused the Example fold
until it was declared with drive_door.replacing, then the tab order, which
reorder_tabs got wrong for a rebuilt tab until it took the order to use).

Usage:
    python migrations/repair_phrasal_accent_stan1293.py           # dry run
    python migrations/repair_phrasal_accent_stan1293.py --apply   # repair

Post-run checks:
    python -m coding set-tab-status --lang stan1293 --class phrasal_accent \
        --construction prescreening --status ready-for-review --apply
    python -m coding import-sheets --apply --lang stan1293
    python -m coding integrity-check
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive_door  # noqa: E402
from coding.drive import load_manifest, remove_anyone_permission  # noqa: E402
from coding.drive_doorway import WorksheetNotFound, get_doorway  # noqa: E402
from coding.generate_sheets import (  # noqa: E402
    CODED_DATA,
    _add_constructions_to_existing_sheet,
)
from coding.locked_tabs import reorder_tabs  # noqa: E402
from coding.make_forms import (  # noqa: E402
    _read_diagnostics_for_language,
    build_element_index,
)

LANG, CLASS = "stan1293", "phrasal_accent"
SHARED, INDEPENDENT = "Example-shared", "Example-independent"


def _col_letter(n: int) -> str:
    """1 -> A, 27 -> AA."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def fix_general(ss, apply: bool) -> None:
    titles = [w.title for w in ss.worksheets()]
    if "general" not in titles:
        if "general_filled" not in titles:
            raise SystemExit("neither general nor general_filled is on the sheet")
        print(f"  {'renaming' if apply else 'would rename'} general_filled -> general")
        ws = ss.worksheet("general_filled")
        if apply:
            ws.update_title("general")
    else:
        ws = ss.worksheet("general")

    rows = ws.get_all_values()
    header = rows[0]
    if SHARED not in header:
        print("  general: one Example column already")
        return
    si, ii = header.index(SHARED), header.index(INDEPENDENT)
    if ii != si + 1:
        raise SystemExit(f"unexpected column order: {header}")
    merged = []
    for r in rows[1:]:
        r = r + [""] * (len(header) - len(r))
        s, i = r[si].strip(), r[ii].strip()
        merged.append([f"shared: {s} | independent: {i}" if (s and i) else (s or i)])
    both = sum(1 for m in merged if m[0].startswith("shared: "))
    print(f"  {'folding' if apply else 'would fold'} {SHARED}/{INDEPENDENT} into Example "
          f"({both} rows with both, {len(merged)} rows)")
    if not apply:
        return
    col = _col_letter(si + 1)
    sheet_id = next(s["properties"]["sheetId"]
                    for s in ss.fetch_sheet_metadata()["sheets"]
                    if s["properties"]["title"] == "general")
    with drive_door.replacing(
            ws, "Example-shared and Example-independent folded into the one "
                "Example column, text kept (Jeff, 2026-10-27)"):
        ws.update([["Example"]] + merged, range_name=f"{col}1:{col}{len(rows)}")
        ss.batch_update({"requests": [{"deleteDimension": {"range": {
            "sheetId": sheet_id, "dimension": "COLUMNS",
            "startIndex": ii, "endIndex": ii + 1}}}]})


def fix_prescreening(ss, apply: bool) -> None:
    try:
        ss.worksheet("prescreening")
        print("  prescreening: present")
        return
    except WorksheetNotFound:
        pass
    tsv = CODED_DATA / LANG / CLASS / "prescreening.tsv"
    with tsv.open(encoding="utf-8") as f:
        saved = list(csv.reader(f, delimiter="\t"))
    print(f"  {'rebuilding' if apply else 'would rebuild'} prescreening "
          f"and fill {len(saved) - 1} rows from {tsv.name}")
    if not apply:
        return
    setup = CODED_DATA / LANG / "lang_setup"
    planar_path = setup / f"planar_{LANG}.tsv"
    names, values = next((n, v) for c, con, n, v in
                         _read_diagnostics_for_language(LANG, setup)
                         if c == CLASS and con == "prescreening")
    _add_constructions_to_existing_sheet(
        ss, CLASS, [("prescreening", names, values)], LANG,
        build_element_index(planar_path.name, setup), planar_path)

    ws = ss.worksheet("prescreening")
    built = ws.get_all_values()
    if built[0] != saved[0]:
        raise SystemExit(f"rebuilt header {built[0]} differs from the saved one {saved[0]}")
    key = lambda r: (r[0], r[1])  # noqa: E731  Element, Position_Name
    by_key = {key(r): r for r in saved[1:]}
    if set(by_key) != {key(r) for r in built[1:]}:
        raise SystemExit("rebuilt rows differ from the saved ones; stopping before writing")
    filled = [by_key[key(r)] + [""] * (len(saved[0]) - len(by_key[key(r)]))
              for r in built[1:]]
    ws.update(filled, range_name=f"A2:{_col_letter(len(saved[0]))}{len(filled) + 1}")


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    sheet_id = load_manifest(doorway)[LANG]["sheets"][CLASS]["spreadsheet_id"]
    ss = doorway.open_spreadsheet(sheet_id)
    print(f"{CLASS}_{LANG}: tabs {[w.title for w in ss.worksheets()]}")
    fix_general(ss, apply)
    fix_prescreening(ss, apply)
    order = [con for cls, con, _n, _v in _read_diagnostics_for_language(
        LANG, CODED_DATA / LANG / "lang_setup") if cls == CLASS]
    if apply:
        reorder_tabs(ss, order)
    links = [g for g in doorway.list_permissions(sheet_id, fields="permissions(id,type,role)")
             if g.get("type") == "anyone"]
    if links:
        print(f"  {'removing' if apply else 'would remove'} the link share")
        if apply:
            remove_anyone_permission(doorway, sheet_id)
    if apply:
        print(f"  tabs now {[w.title for w in ss.worksheets()]}")


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration repair_phrasal_accent_stan1293",
                            may_write="--apply" in sys.argv):
        main()
