"""import-planar — sync the planar spreadsheet between Drive and local TSV.

Run from the repo root:
    # Sheet -> TSV (default direction): download and sync locally
    python -m coding import-planar              # dry run: show what would change
    python -m coding import-planar --apply      # write updated planar TSVs
    python -m coding import-planar --lang LANG  # restrict to one language

    # TSV -> Sheet: push local planar TSV changes up to the Drive spreadsheet
    python -m coding import-planar --to-sheet             # dry run (all languages)
    python -m coding import-planar --to-sheet --apply     # upload to Sheet
    python -m coding import-planar --to-sheet --lang LANG

Sheet -> TSV (default):
    Reads the planar spreadsheet for each language (identified by
    planar_spreadsheet_id in drive_config.json), compares to the local
    planar_{lang_id}.tsv, and writes updated TSVs when content has changed,
    through the local-file door (coding/file_door.py): the old file is
    archived, the change logged in the language's changes.tsv, and the file
    committed and pushed in planars-data when the command ends.

    The Sheet is the source of truth here, so a column added in the Sheet is
    carried down into the TSV. A column the Sheet no longer has is the one
    exception: that language is skipped rather than imported, because writing
    would erase every value in it, and an absent column is far more likely to
    be a mistake in the Sheet than an instruction to delete data.

    When --apply is used and changes are found, writes PLANAR_CHANGES_PATH
    with structured diff information used by the data-refresh workflow to build
    the planar-changed issue body. Positions are compared by name
    (_diff_positions).

    Annotators may answer some criteria with position numbers
    (planars/position_cells.py). When positions move, are removed or are
    renamed, those numbers would silently point at other positions, so before
    the planar file is written every class sheet's position cells are
    rewritten to the new numbering (_renumber_class_sheets), and each change,
    and each number whose position is gone, goes into the planar-changed
    issue. If that fails the planar file is not written and the command exits
    non-zero, so the next run tries again.

TSV -> Sheet (--to-sheet):
    The mirror direction, for when planar_{lang_id}.tsv is edited locally (e.g.
    by restructure-sheets --split-element/--rename-map/--rename-class, which
    read the local TSV as their source of truth). Uploads local content to the
    Drive spreadsheet so it doesn't go stale and get silently reverted by the
    next scheduled import-planar --apply (see issue #248 — that's exactly what
    happened to the #236 pronoun split). restructure-sheets --apply calls this
    automatically; run it by hand only if you edited the planar TSV some other
    way. The push replaces the whole Sheet, including any edit the annotator
    made since the last import, so it goes through the Drive door's
    ``replacing()``: the Sheet is saved to ``state_files.SNAPSHOT_DIR`` first and the
    reason logged.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from . import file_door

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

# Where --apply leaves the structured diff for the data-refresh workflow, which
# reads this exact path to build the planar-changed issue body. Named rather
# than written inline so a test can point it somewhere harmless — a test suite
# that clobbers the real file would hand the workflow a diff nobody made.
PLANAR_CHANGES_PATH = Path("/tmp/planar_changes.json")


# ---------------------------------------------------------------------------
# Sheet reading
# ---------------------------------------------------------------------------

def _read_tsv(path: Path) -> pd.DataFrame:
    """The planar file as text. Without ``keep_default_na=False`` pandas reads
    a cell holding ``NA``, ``null`` or ``None`` as missing, and the push
    would write it to the Sheet as a blank."""
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def _read_sheet_df(ws) -> pd.DataFrame:
    """The planar sheet as a frame, with the columns the Sheet itself has.

    It used to be reshaped here to whatever columns the local TSV already had,
    which meant a column added in the Sheet never arrived and a column removed
    from the Sheet came back as a frame full of blanks. Deciding the Sheet's
    columns from the local copy is the same mistake as #248. The callers
    compare the two column lists themselves and say what differs.

    A column with a blank header is dropped: the used range can run past the
    last named column, and an unnamed column is not a column.
    """
    rows = ws.get_all_values()
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    df = pd.DataFrame(data, columns=headers, dtype=str).fillna("")
    return df[[c for c in df.columns if str(c).strip()]]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda col: col.str.strip() if col.dtype == object else col).fillna("")


# ---------------------------------------------------------------------------
# Diff analysis
# ---------------------------------------------------------------------------

def _diff_positions(old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    """Compare the positions of two planars, by name.

    renamed: a number whose name changed where neither name is anywhere in
    the other planar (probably one position renamed). added / deleted: the
    other names only one planar has. remaps: (old number, new number) for a
    name whose number changed. Until 2026-10-22 added, deleted and renamed
    compared numbers, so a position inserted in the middle was reported as
    the last position added and every later position renamed.
    """
    old = _numbering(old_df)
    new = _numbering(new_df)
    old_by_name = {v: k for k, v in old.items()}
    new_by_name = {v: k for k, v in new.items()}

    renamed = {n: (old[n], new[n]) for n in sorted(set(old) & set(new))
               if old[n] != new[n] and old[n] not in new_by_name
               and new[n] not in old_by_name}
    renamed_old = {o for o, _ in renamed.values()}
    renamed_new = {n for _, n in renamed.values()}
    added = {n: name for n, name in sorted(new.items())
             if name not in old_by_name and name not in renamed_new}
    deleted = {n: name for n, name in sorted(old.items())
               if name not in new_by_name and name not in renamed_old}
    remaps = sorted((old_by_name[name], new_by_name[name]) for name in old_by_name
                    if name in new_by_name and old_by_name[name] != new_by_name[name])

    return {
        "added": {str(k): v for k, v in added.items()},
        "deleted": {str(k): v for k, v in deleted.items()},
        "renamed": {str(k): list(v) for k, v in renamed.items()},
        "remaps": [[o, n] for o, n in remaps],
        "columns_added": [c for c in new_df.columns if c not in old_df.columns],
    }


def _numbering(df: pd.DataFrame) -> dict:
    """{position number: position name} for a planar frame."""
    result = {}
    for _, row in df.iterrows():
        raw = str(row.get("Position", "")).strip()
        if raw.isdigit():
            result[int(raw)] = str(row.get("Position_Name", "")).strip()
    return result


def _recommend(diff: dict, lang_id: str) -> str:
    if diff["deleted"] or diff["renamed"] or diff["remaps"]:
        # Positions that only changed number need no flag: restructure-sheets
        # carries answers over by position name. Until 2026-10-22 this
        # suggested `--rename-map OLD_NUMBER:NEW_NUMBER`, which takes names
        # and so did nothing. A renamed position does need one.
        renames = list(diff["renamed"].values())
        cmd = f"python -m coding restructure-sheets --lang {lang_id}"
        cmd += "".join(f" --rename-map {o}:{n}" for o, n in renames)
        cmd += " --apply"
        if renames:
            cmd += "  # check each --rename-map is the same position renamed"
        return cmd
    elif diff["added"]:
        return "python -m coding update-sheets --apply"
    elif diff["columns_added"]:
        # A planar column is not a criterion column: it feeds validation and
        # the forms built from the planar, not the annotation tabs themselves.
        return "(new planar column — no sheet structural updates needed)"
    else:
        return "(content-only changes — no sheet structural updates needed)"


# ---------------------------------------------------------------------------
# Renumbering the position cells of the class sheets
# ---------------------------------------------------------------------------

def _renumbering_needed(diff: dict) -> bool:
    """A number in a position cell can change meaning: a position moved to
    another number, or the position a number named is gone or renamed."""
    return bool(diff["remaps"] or diff["deleted"] or diff["renamed"])


def _load_renumbering() -> dict:
    path = file_door.renumbering().path
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_renumbering(record: dict) -> None:
    if record:
        file_door.write_state(file_door.renumbering(),
                              json.dumps(record, indent=2, sort_keys=True) + "\n")
    else:
        file_door.remove_state(file_door.renumbering())


def _row_label(row: list, first_criterion: int) -> str:
    """Which row, in the sheet's own words: its cells before the first
    position criterion (the row columns, e.g. Element / Position_Name)."""
    parts = [v for v in row[:min(first_criterion, 3)] if str(v).strip()]
    return " / ".join(parts) if parts else "?"


def _renumber_class_sheets(lang_id: str, old_df: pd.DataFrame, new_df: pd.DataFrame,
                           apply: bool) -> dict:
    """Carry a new planar's numbering into every position cell of the
    language's class sheets (planars.position_cells; the cells are the
    criteria coding.schemas.position_criteria names). Returns
    {"changed": [...], "unresolved": [...]}, one line per cell, for the
    planar-changed issue.

    Must finish before planar_{lang_id}.tsv is written: the old numbering is
    read from that file. Each spreadsheet is rewritten in one write. The
    state file (file_door.renumbering) records, per sheet, the numbering its
    cells use once done, and, just before its write, the cells about to
    change; a later run finds out from the cells whether an interrupted write
    landed. So a run that stops anywhere starts each sheet from the numbering
    it really has and never renumbers one twice. Raises if a sheet cannot be
    read or written, or if an interrupted write's cells were edited since;
    the caller then leaves the planar file alone, and the next run tries
    again.
    """
    from contextlib import ExitStack

    from gspread.utils import rowcol_to_a1

    from . import drive_door
    from .drive import load_manifest
    from .drive_doorway import get_doorway
    from .locked_tabs import system_tab_titles
    from .schemas import position_criteria
    from planars.position_cells import renumber

    old_numbering = _numbering(old_df)
    new_numbering = _numbering(new_df)
    new_by_name = {name: n for n, name in new_numbering.items()}
    criteria = position_criteria()
    system_tabs = set(system_tab_titles())

    doorway = get_doorway()
    try:
        manifest = load_manifest(doorway)
    except SystemExit as exc:   # no manifest at all: no class sheets made yet
        print(f"  no class sheets to renumber ({exc})")
        manifest = {}
    sheets = (manifest or {}).get(lang_id, {}).get("sheets", {})
    record = _load_renumbering()
    done = record.get(lang_id, {})
    changed, unresolved = [], []

    def as_numbering(d: dict) -> dict:
        return {int(k): v for k, v in d.items()}

    def save(sid: str, entry: dict) -> None:
        done[sid] = entry
        record[lang_id] = done
        _save_renumbering(record)

    for class_name, info in sorted(sheets.items()):
        sid = info.get("spreadsheet_id") or info.get("id")
        if not sid:
            continue
        entry = done.get(sid, {})
        ss = doorway.open_spreadsheet(sid)
        if apply and "pending" in entry:
            # A run stopped around this sheet's write: see whether it landed.
            pending = entry["pending"]
            landed = _pending_landed(ss, pending["cells"])
            if landed is None:
                raise RuntimeError(
                    f"{class_name}: a renumbering write was interrupted and its cells "
                    f"now hold neither the old nor the new numbers; check them by hand "
                    f"against {file_door.renumbering().relpath}, then remove its "
                    f"{lang_id} entry")
            entry = ({"numbering": pending["numbering"]} if landed
                     else {k: v for k, v in entry.items() if k != "pending"})
            save(sid, entry)
        source = (as_numbering(entry["numbering"]) if "numbering" in entry
                  else old_numbering)
        if source == new_numbering:
            continue
        writes = []   # (tab, range, new value)
        for ws in ss.worksheets():
            if ws.title in system_tabs:
                continue
            rows = ws.get_all_values()
            if not rows:
                continue
            header = rows[0]
            cols = [i for i, h in enumerate(header) if h in criteria]
            for r, row in enumerate(rows[1:], start=2):
                for c in cols:
                    value = row[c] if c < len(row) else ""
                    if not value.strip():
                        continue
                    new_value, lost = renumber(value, source, new_by_name)
                    where = (f"{class_name} / {ws.title}, row {r} "
                             f"({_row_label(row, cols[0])}), {header[c]}")
                    if new_value != value:
                        writes.append((ws, rowcol_to_a1(r, c + 1), value, new_value))
                        changed.append(f"{where}: {value} → {new_value}")
                    for n in lost:
                        gone = source.get(n)
                        unresolved.append(
                            f"{where}: {n} — "
                            + (f"position {n} ({gone}) is not in the new planar"
                               if gone else f"there was no position {n}")
                            + "; left as typed")

        if not apply:
            continue
        new_entry = {"numbering": {str(n): name for n, name in new_numbering.items()}}
        if writes:
            # Recorded before the write, so a run stopped around it can tell
            # afterwards whether it landed (above) instead of renumbering twice.
            save(sid, dict(entry, pending=dict(
                new_entry, cells=[[ws.title, a1, old, new] for ws, a1, old, new in writes])))
            reason = (f"planar_{lang_id} renumbered: position numbers in "
                      f"{class_name} answers carried over to the new numbering")
            with ExitStack() as stack:
                for ws in {ws.title: ws for ws, _, _, _ in writes}.values():
                    stack.enter_context(drive_door.replacing(ws, reason))
                ss.values_batch_update({
                    "valueInputOption": "RAW",
                    "data": [{"range": f"{_quoted(ws.title)}!{a1}", "values": [[new]]}
                             for ws, a1, _, new in writes]})
        save(sid, new_entry)

    return {"changed": changed, "unresolved": unresolved}


def _quoted(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def _pending_landed(ss, cells: list):
    """True if every cell of an interrupted renumbering write holds its new
    value, False if every one still holds its old value, None otherwise
    (someone has edited them since; a person must look)."""
    values = {}
    for title in {t for t, _, _, _ in cells}:
        values[title] = ss.worksheet(title).get_all_values()
    from gspread.utils import a1_to_rowcol
    now = []
    for title, a1, old, new in cells:
        r, c = a1_to_rowcol(a1)
        rows = values[title]
        cur = rows[r - 1][c - 1] if r - 1 < len(rows) and c - 1 < len(rows[r - 1]) else ""
        now.append((cur, old, new))
    if all(cur == new for cur, _, new in now):
        return True
    if all(cur == old for cur, old, _ in now):
        return False
    return None


def _finish_renumbering(lang_id: str) -> None:
    """The planar file now holds the new numbering, so every sheet agrees
    with it: the record of sheets done is no longer needed."""
    record = _load_renumbering()
    if record.pop(lang_id, None) is not None:
        _save_renumbering(record)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def import_planar(lang_ids: list[str] | None = None, apply: bool = False) -> list[str]:
    """Download planar spreadsheets from Drive and sync to local TSVs.

    Returns list of language IDs whose planars changed.
    """
    from .drive import _load_drive_config
    from .drive_doorway import get_doorway

    cfg = _load_drive_config()

    all_changes: dict[str, dict] = {}
    failed: list[str] = []

    for lang_id, lang_cfg in cfg.items():
        if lang_id.startswith("_"):
            continue
        if lang_ids and lang_id not in lang_ids:
            continue

        sheet_id = lang_cfg.get("planar_spreadsheet_id")
        if not sheet_id:
            # Said out loud, not passed over in silence: a language that has
            # dropped out of drive_config.json otherwise looks exactly like a
            # language that was never in it.
            print(f"\n{lang_id}: no planar_spreadsheet_id in drive_config.json"
                  " — skipping")
            continue

        tsv_path = file_door.planar(lang_id).path
        if not tsv_path.exists():
            print(f"\n{lang_id}: no local planar TSV — skipping")
            continue

        print(f"\n{lang_id}", flush=True)

        try:
            ss = get_doorway().open_spreadsheet(sheet_id)
            ws = ss.sheet1
            old_df = _read_tsv(tsv_path)
            new_df = _read_sheet_df(ws)
        except Exception as exc:
            print(f"  ERROR reading planar sheet: {exc}")
            continue

        if new_df.empty:
            print("  planar sheet is empty — skipping")
            continue

        # A column the Sheet no longer has is never taken as an instruction to
        # erase it locally — same reasoning as the empty sheet just above. The
        # coordinator is told which it is and given both ways out.
        missing = [c for c in old_df.columns if c not in new_df.columns]
        if missing:
            many = len(missing) > 1
            print(f"  the planar Sheet has no {', '.join(missing)} "
                  f"column{'s' if many else ''}, but planar_{lang_id}.tsv "
                  f"does — skipping, since importing would erase "
                  f"{'them' if many else 'it'}")
            print(f"  → restore {'them' if many else 'it'} in the Sheet, or "
                  f"delete {'them' if many else 'it'} from "
                  f"planar_{lang_id}.tsv and run: python -m coding "
                  f"import-planar --to-sheet --lang {lang_id} --apply")
            continue

        # Local column order is kept and anything new goes on the end, so a
        # column reordered in the Sheet is not a change to the file.
        new_df = new_df.reindex(
            columns=list(old_df.columns)
            + [c for c in new_df.columns if c not in old_df.columns])

        if _normalize(old_df).equals(_normalize(new_df)):
            print("  up to date")
            continue

        diff = _diff_positions(old_df, new_df)
        rec = _recommend(diff, lang_id)

        for n, name in diff["added"].items():
            print(f"  + position {n} ({name})")
        for n, name in diff["deleted"].items():
            print(f"  - position {n} ({name})")
        for n, (old_name, new_name) in diff["renamed"].items():
            print(f"  ~ position {n}: {old_name} → {new_name}")
        for o, n in diff["remaps"]:
            print(f"  ↷ position {o} is now {n}")
        for col in diff["columns_added"]:
            print(f"  + column {col}")
        if not any([diff["added"], diff["deleted"], diff["renamed"],
                    diff["remaps"], diff["columns_added"]]):
            print("  (content-only changes)")
        print(f"  → {rec}")

        all_changes[lang_id] = {"diff": diff, "recommendation": rec}

        if _renumbering_needed(diff):
            # Before the planar file is written: it holds the old numbering.
            try:
                cells = _renumber_class_sheets(lang_id, old_df, new_df, apply)
            except Exception as exc:
                print(f"  ERROR renumbering the position cells of the class sheets: {exc}")
                print("  planar file left as it was, so the next run tries again")
                failed.append(lang_id)
                del all_changes[lang_id]
                continue
            all_changes[lang_id]["position_cells"] = cells
            verb = "renumbered" if apply else "would renumber"
            for line in cells["changed"]:
                print(f"  {verb}: {line}")
            for line in cells["unresolved"]:
                print(f"  CHECK: {line}")

        if apply:
            # The door keeps the previous version in archive/lang_setup/,
            # logs the change, and commits it when the command ends.
            file_door.write(file_door.planar(lang_id), file_door.frame_text(new_df),
                            why=f"imported from the planar Sheet; next: {rec}")
            print(f"  wrote planar_{lang_id}.tsv")
            _finish_renumbering(lang_id)

    if apply and all_changes:
        PLANAR_CHANGES_PATH.write_text(json.dumps(all_changes, indent=2))
    elif not apply and all_changes:
        print("\nDry run — rerun with --apply to write changes.")

    if failed:
        raise SystemExit(f"import-planar: could not renumber the class sheets of "
                         f"{', '.join(failed)}; see ERROR above")
    return list(all_changes.keys())


# ---------------------------------------------------------------------------
# TSV -> Sheet (push local planar changes up to Drive)
# ---------------------------------------------------------------------------

def push_planar_to_sheet(lang_id: str, cfg: dict, apply: bool) -> bool:
    """Push local planar_{lang_id}.tsv to the Drive planar spreadsheet.

    Mirror of the download direction in import_planar(): reads the local TSV,
    diffs it against the live Sheet, and on apply clears+rewrites the Sheet to
    match. Returns True if a change was made (or would be, in dry-run).
    """
    from .drive_doorway import get_doorway

    lang_cfg = cfg.get(lang_id, {})
    sheet_id = lang_cfg.get("planar_spreadsheet_id")
    if not sheet_id:
        print(f"  [{lang_id}] No planar_spreadsheet_id in drive_config.json — skipping")
        return False

    tsv_path = file_door.planar(lang_id).path
    if not tsv_path.exists():
        print(f"  [{lang_id}] No local planar TSV — skipping")
        return False

    local_df = _read_tsv(tsv_path)

    try:
        ss = get_doorway().open_spreadsheet(sheet_id)
        ws = ss.sheet1
        sheet_df = _read_sheet_df(ws)
    except Exception as exc:
        print(f"  [{lang_id}] ERROR reading planar sheet: {exc}")
        return False

    if _normalize(local_df).equals(_normalize(sheet_df)):
        print(f"  [{lang_id}] Sheet already up to date")
        return False

    diff = _diff_positions(sheet_df, local_df)
    dropped_cols = [c for c in sheet_df.columns if c not in local_df.columns]
    for n, name in diff["added"].items():
        print(f"  [{lang_id}]   + position {n} ({name})")
    for n, name in diff["deleted"].items():
        print(f"  [{lang_id}]   - position {n} ({name})")
    for n, (old_name, new_name) in diff["renamed"].items():
        print(f"  [{lang_id}]   ~ position {n}: {old_name} -> {new_name}")
    for col in diff["columns_added"]:
        print(f"  [{lang_id}]   + column {col}")
    # This direction rewrites the Sheet from the TSV, so a column only the
    # Sheet has goes. Named before it happens, not after.
    for col in dropped_cols:
        print(f"  [{lang_id}]   - column {col}")
    if not any([diff["added"], diff["deleted"], diff["renamed"],
                diff["columns_added"], dropped_cols]):
        print(f"  [{lang_id}]   (content-only changes)")

    if apply:
        from . import drive_door
        new_rows = [list(local_df.columns)] + [list(row) for _, row in local_df.iterrows()]
        # The Sheet is the annotator's to edit until unit 11 locks it, so this
        # replaces whatever they changed since the last import too: the door
        # saves the Sheet first (state_files.SNAPSHOT_DIR) and logs the reason.
        with drive_door.replacing(ws, f"planar_{lang_id}.tsv pushed to the planar Sheet"):
            ws.clear()
            ws.update(new_rows, "A1")
        print(f"  [{lang_id}] Updated -> planar Sheet")
    else:
        print(f"  [{lang_id}] Would update -> planar Sheet (use --apply to write)")

    return True


def push_planars_to_sheets(lang_ids: list[str] | None = None, apply: bool = False) -> list[str]:
    """Push local planar TSVs to their Drive spreadsheets for all (or selected) languages.

    Returns list of language IDs whose Sheet changed (or would change).
    """
    from .drive import _load_drive_config

    cfg = _load_drive_config()

    changed = []
    for lang_id in cfg:
        if lang_id.startswith("_"):
            continue
        if lang_ids and lang_id not in lang_ids:
            continue
        print(f"\n{lang_id}", flush=True)
        if push_planar_to_sheet(lang_id, cfg, apply):
            changed.append(lang_id)

    if not apply and changed:
        print("\nDry run — rerun with --apply to write changes.")

    return changed


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding import-planar`."""
    ap = argparse.ArgumentParser(
        description="Sync the planar spreadsheet between Drive and local TSV."
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", action="append", dest="langs",
        help="restrict to this language (repeatable)",
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
    )
    ap.add_argument(
        "--to-sheet", action="store_true",
        help="push local planar TSV changes up to the Drive spreadsheet "
             "(default direction is Sheet -> TSV)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    if args.to_sheet:
        push_planars_to_sheets(lang_ids=args.langs, apply=args.apply)
    else:
        import_planar(lang_ids=args.langs, apply=args.apply)
    sys.exit(0)
