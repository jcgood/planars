#!/usr/bin/env python3
"""`python -m coding rename-construction` — rename a construction (a tab of a
class sheet) in every language that has it, keeping its answers and its link.

    python -m coding rename-construction coreference:np_reference:np_coreference
    python -m coding rename-construction CLASS:OLD:NEW [CLASS:OLD:NEW ...] --apply
    python -m coding rename-construction CLASS:OLD:NEW --lang stan1293 --apply

First rename the construction in ``schemas/diagnostic_classes.yaml`` (the
schema is the code's; the command refuses until it lists NEW and not OLD).
Then, for each language whose diagnostics file has CLASS with OLD, ``--apply``:

  1. renames it in ``diagnostics_{lang_id}.yaml`` (its ``constructions``, and
     the ``construction_criteria`` / ``keystone_active`` keys; comments and
     layout kept), then pushes the file to the language's diagnostics Sheet,
     as ``sync-diagnostics-yaml`` does;
  2. renames the tab on the class sheet in place, and its row on the Status
     tab — the sheet and its link stay the same, and so do the answers (the
     ID file is not touched: it holds sheet IDs, not tab names);
  3. moves ``coded_data/{lang_id}/{class}/OLD.tsv`` to ``NEW.tsv`` (the
     local-file door keeps the old one in the archive and logs both);
  4. carries check-comments' record of what it has seen on the tab over to
     the new name, so those comments are not reported again.

The Colab notebooks take a tab's construction from its label, which the
Drive door rewrites under the new name when the command ends, so they need
no telling.

Archived TSVs, change logs, provenance lines and saved copies keep the old
name: they are history.

The diagnostics file is written before anything on Drive, because the Drive
door checks each class sheet against it when the command ends. Every step
looks first at what is there and skips what is already done, so a run that
stopped partway is finished by running it again. Run it all in one sitting
and push: the daily refresh adds a tab for a construction the diagnostics
file has and the sheet lacks, so a renamed file with an unrenamed tab would
gain an empty tab beside the answered one.

Dry run by default: prints what each language would change.
"""
from __future__ import annotations

import argparse
from typing import List, Optional, Tuple

from gspread.utils import rowcol_to_a1

from planars.schema_values import STATUS_CONSTRUCTION_COLUMN, STATUS_TAB, _class_entry

from . import check_comments, file_door
from . import drive_ids
from .drive import _load_drive_config
from .drive_doorway import WorksheetNotFound, get_doorway
from .make_forms import _dump_diagnostics_yaml, _load_diagnostics_yaml_for_edit
from .sync_diagnostics_yaml import _sync_to_sheet
from .validate_diagnostics import validate_diagnostics_yaml

Rename = Tuple[str, str, str]  # (class, old, new)


def _parse(spec: str) -> Rename:
    parts = spec.split(":")
    if len(parts) != 3 or not all(p.strip() for p in parts):
        raise SystemExit(f"rename-construction: {spec!r} should be CLASS:OLD:NEW")
    cls, old, new = (p.strip() for p in parts)
    if old == new:
        raise SystemExit(f"rename-construction: {spec!r} renames a construction to itself")
    return cls, old, new


def _schema_problems(renames: List[Rename]) -> List[str]:
    """What stops a rename at the schema: it must list NEW, and not OLD."""
    problems = []
    for cls, old, new in renames:
        try:
            entry = _class_entry(cls)
        except KeyError:
            problems.append(f"{cls}: no such class in schemas/diagnostic_classes.yaml")
            continue
        names = ({c["name"] for c in entry.get("constructions") or [] if isinstance(c, dict)}
                 | set(entry.get("known_constructions") or []))
        if new not in names:
            problems.append(f"{cls}: schemas/diagnostic_classes.yaml has no construction "
                            f"{new!r} — rename it there first")
        if old in names:
            problems.append(f"{cls}: schemas/diagnostic_classes.yaml still lists {old!r} — "
                            f"rename it there first")
    return problems


def _rename_key(mapping, old: str, new: str) -> bool:
    """Rename a key in place, keeping its position (and, for ruamel, its comments)."""
    if not hasattr(mapping, "keys") or old not in mapping:
        return False
    if new in mapping:
        raise SystemExit(f"rename-construction: both {old!r} and {new!r} are keys here")
    keys = list(mapping.keys())
    value = mapping.pop(old)
    if hasattr(mapping, "insert"):
        mapping.insert(keys.index(old), new, value)
    else:
        mapping[new] = value
    return True


def _rename_in_yaml(data, cls: str, old: str, new: str) -> List[str]:
    """Rename OLD to NEW in one class of a loaded diagnostics file. What changed."""
    class_data = (data.get("classes") or {}).get(cls)
    if not class_data:
        return []
    changes = []
    constructions = class_data.get("constructions") or []
    if old in constructions:
        if new in constructions:
            raise SystemExit(f"rename-construction: {cls} lists both {old!r} and {new!r}")
        constructions[constructions.index(old)] = new
        changes.append(f"constructions: {old} → {new}")
    for key in ("construction_criteria", "keystone_active"):
        if _rename_key(class_data.get(key), old, new):
            changes.append(f"{key}: {old} → {new}")
    return changes


def _rename_yaml(lang_id: str, renames: List[Rename],
                 apply: bool) -> Tuple[List[Rename], bool]:
    """Step 1 for one language: (the renames that apply to it — its file has
    the class with OLD, or with NEW already, from a run that stopped partway —
    and whether the file changes)."""
    path = file_door.diagnostics_yaml(lang_id).path
    if not path.exists():
        return [], False
    data = _load_diagnostics_yaml_for_edit(path)
    mine: List[Rename] = []
    changes: List[str] = []
    for cls, old, new in renames:
        constructions = ((data.get("classes") or {}).get(cls) or {}).get("constructions") or []
        if old in constructions or new in constructions:
            mine.append((cls, old, new))
            changes += [f"{cls} {c}" for c in _rename_in_yaml(data, cls, old, new)]
    for c in changes:
        print(f"  diagnostics file: {c}")
    if not (apply and changes):
        return mine, bool(changes)
    blocking = [i for i in validate_diagnostics_yaml(data, lang_id)
                if i.level == "error" and i.blocking]
    if blocking:
        for e in blocking:
            print(f"  ERROR {e.location}: {e.message}")
        raise SystemExit(f"rename-construction: the renamed diagnostics_{lang_id}.yaml would "
                         f"not pass validation (above); nothing was written for {lang_id}")
    file_door.write(file_door.diagnostics_yaml(lang_id), _dump_diagnostics_yaml(data),
                    why="rename-construction: " + "; ".join(changes))
    return mine, True


def _rename_on_sheet(doorway, sheet_id: str, cls: str, old: str, new: str,
                     apply: bool) -> bool:
    """Step 2: the tab and its Status row, in place. True if anything changes."""
    ss = doorway.open_spreadsheet(sheet_id)
    titles = [ws.title for ws in ss.worksheets()]
    if old in titles and new in titles:
        raise SystemExit(f"rename-construction: {cls}'s sheet has both tabs {old!r} and "
                         f"{new!r}; settle which holds the answers by hand first")
    changed = False
    if old in titles:
        print(f"  {cls} sheet: rename tab {old} → {new}")
        changed = True
        if apply:
            ss.worksheet(old).update_title(new)
    elif new not in titles:
        print(f"  {cls} sheet: has no tab {old!r} or {new!r} (nothing to rename)")
    try:
        status = ss.worksheet(STATUS_TAB)
    except WorksheetNotFound:
        return changed
    rows = status.get_all_values()
    header = [h.strip() for h in rows[0]] if rows else []
    if STATUS_CONSTRUCTION_COLUMN not in header:
        return changed
    col = header.index(STATUS_CONSTRUCTION_COLUMN)
    for r, row in enumerate(rows[1:], start=2):
        if col < len(row) and row[col].strip() == old:
            print(f"  {cls} sheet: Status row {old} → {new}")
            changed = True
            if apply:
                status.update([[new]], rowcol_to_a1(r, col + 1))
    return changed


def _rename_local(lang_id: str, cls: str, old: str, new: str, apply: bool) -> bool:
    """Steps 3 and 4. True if the TSV moves."""
    source = file_door.annotation(lang_id, cls, old)
    moves = source.path.exists()
    if moves:
        print(f"  local: {source.relpath} → {new}.tsv")
        if apply:
            target = file_door.annotation(lang_id, cls, new)
            if target.path.exists():
                raise SystemExit(f"rename-construction: both {source.relpath} and "
                                 f"{target.relpath} exist; settle which is current by hand")
            why = f"construction renamed {old} → {new} (rename-construction)"
            file_door.write(target, file_door.read(source), why=why,
                            what=f"moved from {source.relpath}")
            file_door.remove(source, why=f"moved to {cls}/{new}.tsv: {why}")
    if apply:
        moved = check_comments.rename_tab_in_state(lang_id, cls, old, new)
        if moved:
            print(f"  comments seen on {cls}/{old}: {moved} carried over")
    return moves


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m coding rename-construction",
        description="Rename a construction in every language that has it, keeping its "
                    "answers and its sheet's link.")
    ap.add_argument("renames", nargs="+", metavar="CLASS:OLD:NEW",
                    help="the construction to rename (repeatable)")
    ap.add_argument("--lang", metavar="LANG_ID", help="only this language")
    ap.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    return ap


def main(args: Optional[argparse.Namespace] = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    renames = [_parse(s) for s in args.renames]
    problems = _schema_problems(renames)
    if problems:
        raise SystemExit("rename-construction:\n  " + "\n  ".join(problems))
    apply = args.apply
    doorway = get_doorway()
    config = _load_drive_config()
    langs = [args.lang] if args.lang else drive_ids.languages(config)
    print(("" if apply else "DRY RUN — ") + "renaming: "
          + ", ".join(f"{c}/{o} → {n}" for c, o, n in renames))
    touched = 0
    for lang_id in langs:
        print(f"\n{lang_id}:")
        mine, changed = _rename_yaml(lang_id, renames, apply)
        if not mine:
            print("  nothing to rename")
            continue
        if apply:
            _sync_to_sheet(lang_id, config, apply=True, error_langs=[])
        sheets = drive_ids.class_sheets(config, lang_id)
        for cls, old, new in mine:
            if cls in sheets:
                changed |= _rename_on_sheet(doorway, sheets[cls], cls, old, new, apply)
            changed |= _rename_local(lang_id, cls, old, new, apply)
        if changed:
            touched += 1
        else:
            print("  already renamed")
    if not apply:
        print(f"\nDry run: {touched} language(s) would change. Run with --apply to make "
              f"the changes.")
    else:
        print(f"\nDone: {touched} language(s).")
