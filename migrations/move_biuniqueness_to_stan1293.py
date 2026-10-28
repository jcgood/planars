"""One-time migration: move the biuniqueness_deviations class from synth0001
to English (stan1293), renaming its first tab prescreening -> elements.

Motivation: Phase 10 unit 1 (issue #271; #254). The class was built and
tried out on synth0001, the synthetic copy of English, and Adam answered its
first tab there. synth0001 is test data, so the class moves to the real
language: English gets the class sheet, Adam's answers come with it, and
synth0001's copy is retired. The tab rename rides along because a new sheet
can be created with the new name, so no live tab is ever renamed.

Two steps, run with the ordinary commands between them:

  backfill  (Undone later the same day: the Biuniqueness_Scope column was
            deleted from every planar, the scope being computed from
            Elements. Do not re-run this step.) Write the column into
            coded_data/stan1293/lang_setup/planar_stan1293.tsv, computed by
            coding.make_forms.classify_biuniqueness_scope (the same classifier
            as migrations/backfill_biuniqueness_scope_synth0001.py). The two
            planars are identical, so the result equals synth0001's column;
            the step checks that and refuses if not.
  copy      Copy every answer on synth0001's prescreening tab (each criterion,
            Source and Comments) into the same (Position_Name, Element) row of
            English's elements tab, and the tab's Status value. A target cell
            that already holds a value is left alone and reported. Aborts,
            writing nothing, if an answered row has no matching row.
  lock      Make the archived synth0001 sheet read-only (drive.make_read_only).
            prune-manifest now does this itself, but it was archived the
            moment before that fix: Adam was still a writer there.

Run: 2026-10-13, in this order:
    python migrations/move_biuniqueness_to_stan1293.py backfill --apply
    import-planar --to-sheet --lang stan1293 --apply
        (since 2026-10-24: python -m coding sync-planar --lang stan1293 --apply)
    (add the class to diagnostics_stan1293.yaml)
    python -m coding sync-diagnostics-yaml --lang stan1293 --apply
        (then the same with the Sheet flag, retired 2026-10-27: the
        command now does only the Sheet, and there is no TSV copy)
    python -m coding generate-sheets --lang stan1293 --apply
    python migrations/move_biuniqueness_to_stan1293.py copy --apply
    (remove the class from diagnostics_synth0001.yaml, sync it the same way)
    python -m coding prune-manifest --apply
    python migrations/move_biuniqueness_to_stan1293.py lock --apply

Usage (each step dry-runs without --apply):
    python migrations/move_biuniqueness_to_stan1293.py backfill [--apply]
    python migrations/move_biuniqueness_to_stan1293.py copy [--apply]
    python migrations/move_biuniqueness_to_stan1293.py lock [--apply]

Post-run checks:
    Re-read English's elements tab: the same answered rows as synth0001's.
    python -m coding import-sheets --lang stan1293 --apply   (backs it up)
    python -m coding integrity-check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from coding.biuniqueness_rows import CLASS_NAME, ELEMENTS  # noqa: E402
from coding.drive import load_manifest, make_read_only  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.make_forms import classify_biuniqueness_scope  # noqa: E402
from coding.validate_planar import _tokenize_elements, validate_planar_df  # noqa: E402
from planars.schema_values import STATUS_TAB  # noqa: E402

LANG = "stan1293"
# synth0001's class sheet, recorded here because prune-manifest removes it
# from the manifest once the class is retired.
OLD_SHEET_ID = "1Z3CkzA4_QDLNDAp0hexL5To-reulXn5Or0th2UiYVio"
OLD_TAB = "prescreening"
STRUCTURAL = ("Element", "Position_Name", "Position_Number")


def _planar(lang: str) -> Path:
    return ROOT / "coded_data" / lang / "lang_setup" / f"planar_{lang}.tsv"


def backfill(apply: bool) -> None:
    df = pd.read_csv(_planar(LANG), sep="\t", dtype=str, keep_default_na=False)
    if "Biuniqueness_Scope" in df.columns:
        raise SystemExit(f"planar_{LANG}.tsv already has Biuniqueness_Scope; nothing to do.")
    computed = []
    for _, row in df.iterrows():
        tokens = _tokenize_elements(str(row["Elements"]).strip())
        scopes = [classify_biuniqueness_scope(t) for t in tokens]
        if "unknown" in scopes:
            raise SystemExit(f"{row['Position_Name']}: unregistered ALL CAPS label(s) "
                             f"{[t for t, s in zip(tokens, scopes) if s == 'unknown']} — "
                             f"register them in schemas/planar.yaml first")
        computed.append(", ".join(scopes))

    synth = pd.read_csv(_planar("synth0001"), sep="\t", dtype=str, keep_default_na=False)
    if list(synth["Biuniqueness_Scope"]) != computed:
        raise SystemExit("The computed column differs from synth0001's, so Adam's answers "
                         "would not line up; nothing written.")
    print(f"Biuniqueness_Scope for {len(computed)} positions matches synth0001's column.")
    if not apply:
        print("Dry run: run with --apply to write.")
        return
    df["Biuniqueness_Scope"] = computed
    errors = [i for i in validate_planar_df(df) if i.level == "error"]
    if errors:
        raise SystemExit("Planar validation failed after backfill; nothing written:\n"
                         + "\n".join(f"  {e.location}: {e.message}" for e in errors))
    df.to_csv(_planar(LANG), sep="\t", index=False)
    print(f"Wrote {_planar(LANG)}")


def _table(values):
    header = values[0]
    return header, [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in values[1:]]


def copy(apply: bool) -> None:
    doorway = get_doorway()
    new_id = load_manifest(doorway)[LANG]["sheets"][CLASS_NAME]["spreadsheet_id"]
    old_ss = doorway.open_spreadsheet(OLD_SHEET_ID)
    new_ss = doorway.open_spreadsheet(new_id)

    old_header, old_rows = _table(old_ss.worksheet(OLD_TAB).get_all_values())
    new_ws = new_ss.worksheet(ELEMENTS)
    new_vals = new_ws.get_all_values()
    new_header, new_rows = _table(new_vals)
    if [c for c in old_header if c not in STRUCTURAL] != [c for c in new_header if c not in STRUCTURAL]:
        raise SystemExit(f"Columns differ: {old_header} vs {new_header}; nothing written.")
    where = {(r["Position_Name"], r["Element"]): i for i, r in enumerate(new_rows)}

    writes, kept, missing = [], [], []
    for r in old_rows:
        key = (r["Position_Name"], r["Element"])
        answers = {c: r[c].strip() for c in old_header if c not in STRUCTURAL and r[c].strip()}
        if not answers:
            continue
        if key not in where:
            missing.append(key)
            continue
        i = where[key]
        for col, value in answers.items():
            current = new_rows[i][col].strip()
            if current == value:
                continue
            if current:
                kept.append((key, col, current, value))
                continue
            # 1-based sheet coordinates: header is row 1.
            writes.append((i + 2, new_header.index(col) + 1, value, key, col))

    old_status = dict(r[:2] for r in old_ss.worksheet(STATUS_TAB).get_all_values()[1:])
    status_ws = new_ss.worksheet(STATUS_TAB)
    status_rows = status_ws.get_all_values()
    status_row = next(n for n, r in enumerate(status_rows, 1) if r and r[0] == ELEMENTS)
    status_change = old_status.get(OLD_TAB) != status_rows[status_row - 1][1]

    print(f"{'' if apply else 'DRY RUN — '}{len(writes)} cell(s) to copy into {new_ss.url}")
    for _, _, value, key, col in writes:
        print(f"  {key[0]} / {key[1]}: {col} = {value!r}")
    for key, col, current, value in kept:
        print(f"  KEPT {key[0]} / {key[1]}: {col} already {current!r} (synth0001 had {value!r})")
    print(f"  Status of {ELEMENTS}: {old_status.get(OLD_TAB)!r}"
          f"{'' if status_change else ' (already)'}")
    if missing:
        raise SystemExit(f"ABORTED: no row in English's {ELEMENTS} tab for {missing}; nothing written.")
    if not apply:
        print("\nRun with --apply to write.")
        return
    for row, col, value, _, _ in writes:
        new_ws.update_cell(row, col, value)
    if status_change:
        status_ws.update_cell(status_row, 2, old_status[OLD_TAB])
    print(f"\nCopied {len(writes)} cell(s).")


def lock(apply: bool) -> None:
    doorway = get_doorway()
    perms = doorway.list_permissions(
        OLD_SHEET_ID, fields="permissions(type,role,emailAddress)")
    print("Now:", [(p.get("emailAddress") or p.get("type"), p.get("role")) for p in perms])
    if not apply:
        print("Dry run: run with --apply to make it read-only.")
        return
    print("Lowered to reader:", make_read_only(doorway, OLD_SHEET_ID))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=["backfill", "copy", "lock"])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = ap.parse_args()
    {"backfill": backfill, "copy": copy, "lock": lock}[args.step](args.apply)


if __name__ == "__main__":
    import sys

    from coding import drive_door
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration move_biuniqueness_to_stan1293",
                            may_write="--apply" in sys.argv):
        main()
