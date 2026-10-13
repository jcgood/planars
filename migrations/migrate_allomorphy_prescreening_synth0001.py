"""One-time migration: copy Adam's answers from the standalone allomorphy
prescreening sheet into the biuniqueness_deviations class sheet (synth0001).

Motivation: on 2026-10-11 allomorphy became part of the biuniqueness_deviations
class, run through the ordinary sheet pipeline (#254). The standalone sheet
(biuniqueness_allomorphy_synth0001, built by the now-frozen
generate-biuniqueness-allomorphy-sheet command) held 18 answered rows. This
copies each answer to the same (Position_Name, Element) row of the class
sheet's prescreening tab:

    has_allomorphs -> has_allomorphs
    Members        -> members
    Notes          -> Comments

A target cell that already holds a value is never overwritten (open-category
rows carry NA in has_allomorphs by design). Hyphen elements are matched in the
class sheet's bracketed form ("-n" -> "[-n]"). Also shares the class sheet with
Adam as writer, as the standalone sheet was (synth0001 has no annotator email
in languages.yaml, so generate-sheets did not); skipped if he already has it.

Run: 2026-10-11, after the class sheet was created by
     python -m coding generate-sheets --lang synth0001 --apply

Usage:
    python migrations/migrate_allomorphy_prescreening_synth0001.py           # dry run
    python migrations/migrate_allomorphy_prescreening_synth0001.py --apply   # write

Post-run checks:
    Re-read the class sheet's prescreening tab: 18 rows answered as before.
    python -m coding import-sheets --lang synth0001 --apply   (backs it up)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.biuniqueness_rows import wrap  # noqa: E402
from coding.drive import _with_retry, load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

LANG = "synth0001"
OLD_SHEET_ID = "1YEtSlw9t05OI6RKGgCtbez0u3oX1p5Xfe_6UH1dweGA"
COLUMN_MAP = {"has_allomorphs": "has_allomorphs", "Members": "members", "Notes": "Comments"}


def _table(values, first_col):
    h = next(i for i, r in enumerate(values) if r and r[0] == first_col)
    return values[h], h, values[h + 1:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    new_id = load_manifest(doorway)[LANG]["sheets"]["biuniqueness_deviations"]["spreadsheet_id"]

    old_vals = _with_retry(doorway.open_spreadsheet(OLD_SHEET_ID).worksheet("prescreening").get_all_values)
    old_header, _, old_rows = _table(old_vals, "Position_Name")
    new_ss = doorway.open_spreadsheet(new_id)
    new_ws = new_ss.worksheet("prescreening")
    new_vals = _with_retry(new_ws.get_all_values)
    new_header, header_idx, new_rows = _table(new_vals, "Element")
    where = {(r[new_header.index("Position_Name")], r[new_header.index("Element")]): i
             for i, r in enumerate(new_rows)}

    writes, missing, kept = [], [], []
    for r in old_rows:
        rec = dict(zip(old_header, r + [""] * (len(old_header) - len(r))))
        answers = {dst: rec[src].strip() for src, dst in COLUMN_MAP.items() if rec.get(src, "").strip()}
        if not answers:
            continue
        key = (rec["Position_Name"], wrap(rec["Element"]))
        if key not in where:
            missing.append(key)
            continue
        i = where[key]
        for col, value in answers.items():
            current = new_rows[i][new_header.index(col)]
            if current.strip():
                kept.append((key, col, current, value))
                continue
            # 1-based sheet coordinates: header row, then data rows after it.
            writes.append((header_idx + 2 + i, new_header.index(col) + 1, value, key, col))

    print(f"{'DRY RUN — ' if not apply else ''}{len(writes)} cell(s) to copy into {new_ss.url}")
    for _, _, value, key, col in writes:
        print(f"  {key[0]} / {key[1]}: {col} = {value!r}")
    for key, col, current, value in kept:
        print(f"  KEPT {key[0]} / {key[1]}: {col} already {current!r} (old sheet had {value!r})")
    if missing:
        raise SystemExit(f"ABORTED: no row in the class sheet for {missing}; nothing written.")

    from coding.people import email_for
    adam = email_for("Adam Tallman")
    perms = _with_retry(lambda: doorway.list_permissions(
        new_id, fields="permissions(id,type,role,emailAddress)"))
    adam_shared = any(p.get("emailAddress", "").lower() == adam and p.get("role") == "writer"
                      for p in perms)
    print(f"  Adam {'already has' if adam_shared else 'will be given'} writer access")

    if not apply:
        print("\nRun with --apply to write.")
        return
    for row, col, value, _, _ in writes:
        _with_retry(lambda r=row, c=col, v=value: new_ws.update_cell(r, c, v))
    if not adam_shared:
        _with_retry(lambda: doorway.create_permission(new_id, type="user", role="writer",
                                                      email=adam, notify=False))
    print(f"\nCopied {len(writes)} cell(s).")


if __name__ == "__main__":
    main()
