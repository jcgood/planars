"""sync-planar — bring each language's planar Sheet up to date with its planar file.

Run from the repo root:
    python -m coding sync-planar                # dry run: show what would change
    python -m coding sync-planar --apply        # update the Sheets
    python -m coding sync-planar --lang LANG    # restrict to one language

``planar_{lang_id}.tsv`` in planars-data is the planar's one editable home.
The coordinator edits it (by hand, or with ``accept-proposal`` from the
language's proposal sheet); the planar Sheet is a read-only copy for the
annotator (Phase 10 unit 11b, docs/ownership-design.md § 3.1), rebuilt from
the file by this command: daily in the refresh, and at the end of
``restructure-sheets --apply``. Nothing is ever read back from the Sheet.

The Sheet still holds the planar as it was last pushed, so the difference
between the two is what changed since. Positions are compared by name
(``_diff_positions``), and with ``--apply`` the changes are written to
``PLANAR_CHANGES_PATH``, which the daily refresh turns into the
``planar-changed`` issue naming the command that carries them into the class
sheets (``_recommend``).

Annotators may answer some criteria with position numbers
(planars/position_cells.py). When positions move, are removed or are renamed,
those numbers would silently point at other positions, so before the Sheet is
updated every class sheet's position cells are rewritten to the new numbering
(``_renumber_class_sheets``), and each change, and each number whose position
is gone, goes into the planar-changed issue. This covers every way the file
changes, since every change reaches the Sheet here. If renumbering fails the
Sheet is left as it was and the command exits non-zero, so the next run
starts again from the same old numbering.
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

# Where --apply leaves the structured diff for the daily refresh, which reads
# this exact path to build the planar-changed issue body. Named rather than
# written inline so a test can point it somewhere harmless — a test suite that
# clobbers the real file would hand the refresh a diff nobody made.
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
    """The planar Sheet as a frame, with the columns the Sheet itself has (the
    planar as last pushed). A column with a blank header is dropped: the used
    range can run past the last named column."""
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
        "columns_removed": [c for c in old_df.columns if c not in new_df.columns],
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
    elif diff["columns_added"] or diff.get("columns_removed"):
        # A planar column is not a criterion column: it feeds validation and
        # the forms built from the planar, not the annotation tabs themselves.
        return "(planar column added or removed — no sheet structural updates needed)"
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

    Must finish before the planar Sheet is updated: the old numbering is
    read from it. Each spreadsheet is rewritten in one write. The
    state file (file_door.renumbering) records, per sheet, the numbering its
    cells use once done, and, just before its write, the cells about to
    change; a later run finds out from the cells whether an interrupted write
    landed. So a run that stops anywhere starts each sheet from the numbering
    it really has and never renumbers one twice. Raises if a sheet cannot be
    read or written, or if an interrupted write's cells were edited since;
    the caller then leaves the planar Sheet alone, and the next run tries
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
    """The planar Sheet now holds the new numbering, so every class sheet
    agrees with it: the record of sheets done is no longer needed."""
    record = _load_renumbering()
    if record.pop(lang_id, None) is not None:
        _save_renumbering(record)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def _sync_one(lang_id: str, sheet_id: str, apply: bool, all_changes: dict) -> bool:
    """Bring one language's planar Sheet up to date with its planar file.
    Returns False if the class sheets could not be renumbered (the Sheet is
    then left as it was)."""
    from .drive_doorway import get_doorway
    from .locked_tabs import protect

    tsv_path = file_door.planar(lang_id).path
    if not tsv_path.exists():
        print(f"  no planar file (planar_{lang_id}.tsv) — skipping")
        return True
    new_df = _read_tsv(tsv_path)
    try:
        ss = get_doorway().open_spreadsheet(sheet_id)
        ws = ss.sheet1
        old_df = _read_sheet_df(ws)
    except Exception as exc:
        print(f"  ERROR reading the planar Sheet: {exc}")
        return True

    # Read-only for everyone but its owner, coordinators included (they are
    # writers on the root folder); checked every run, so a Sheet made before
    # unit 11b is protected by the next one.
    if protect(ss, ws, apply):
        print(f"  {'protected' if apply else 'would protect'} the planar Sheet")

    if _normalize(old_df).equals(_normalize(new_df)):
        print("  up to date")
        return True

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
    for col in diff["columns_removed"]:
        print(f"  - column {col}")
    if not any([diff["added"], diff["deleted"], diff["renamed"], diff["remaps"],
                diff["columns_added"], diff["columns_removed"]]):
        print("  (content-only changes)")
    print(f"  → {rec}")
    all_changes[lang_id] = {"diff": diff, "recommendation": rec}

    if _renumbering_needed(diff):
        # Before the Sheet is updated: it holds the old numbering.
        try:
            cells = _renumber_class_sheets(lang_id, old_df, new_df, apply)
        except Exception as exc:
            print(f"  ERROR renumbering the position cells of the class sheets: {exc}")
            print("  planar Sheet left as it was, so the next run tries again")
            del all_changes[lang_id]
            return False
        all_changes[lang_id]["position_cells"] = cells
        verb = "renumbered" if apply else "would renumber"
        for line in cells["changed"]:
            print(f"  {verb}: {line}")
        for line in cells["unresolved"]:
            print(f"  CHECK: {line}")

    if apply:
        # The Sheet is the tooling's (annotators read it), so nothing on it
        # is lost by rewriting it whole.
        ws.clear()
        ws.update([list(new_df.columns)] + [list(row) for _, row in new_df.iterrows()], "A1")
        print("  updated the planar Sheet")
        _finish_renumbering(lang_id)
    return True


def sync_planars(lang_ids: list[str] | None = None, apply: bool = False) -> list[str]:
    """Bring every (or each named) language's planar Sheet up to date with its
    planar file. Returns the languages whose Sheet changed (or would)."""
    from .drive import _load_drive_config

    cfg = _load_drive_config()
    all_changes: dict[str, dict] = {}
    failed: list[str] = []
    for lang_id, lang_cfg in cfg.items():
        if lang_id.startswith("_") or (lang_ids and lang_id not in lang_ids):
            continue
        print(f"\n{lang_id}", flush=True)
        sheet_id = lang_cfg.get("planar_spreadsheet_id")
        if not sheet_id:
            # Said out loud: a language that has dropped out of
            # drive_config.json otherwise looks like one never in it.
            print("  no planar_spreadsheet_id in drive_config.json — skipping")
            continue
        if not _sync_one(lang_id, sheet_id, apply, all_changes):
            failed.append(lang_id)

    if apply and all_changes:
        PLANAR_CHANGES_PATH.write_text(json.dumps(all_changes, indent=2))
    elif not apply and all_changes:
        print("\nDry run — rerun with --apply to update the Sheets.")
    if failed:
        raise SystemExit(f"sync-planar: could not renumber the class sheets of "
                         f"{', '.join(failed)}; see ERROR above")
    return list(all_changes)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding sync-planar`."""
    ap = argparse.ArgumentParser(
        description="Bring each planar Sheet up to date with its planar file "
                    "(renumbering position answers in the class sheets first)."
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", action="append", dest="langs",
        help="restrict to this language (repeatable)",
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    sync_planars(lang_ids=args.langs, apply=args.apply)
    sys.exit(0)
