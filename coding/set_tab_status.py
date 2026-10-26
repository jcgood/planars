#!/usr/bin/env python3
"""Set a tab's status in a class sheet's Status tab, for an annotator.

An annotator marks a tab ready-for-review in the Status tab of a class sheet
when it is finished; a tab that depends on it (e.g. phrasal_accent's general
pairs, built from prescreening) is only filled after that. When an annotator
says a tab is done but forgot to mark it, the coordinator marks it with this
command rather than by hand in the sheet.

    python -m coding set-tab-status --lang stan1293 --class phrasal_accent \\
        --construction prescreening                       # dry run
    python -m coding set-tab-status --lang stan1293 --class phrasal_accent \\
        --construction prescreening --apply               # write it

--status defaults to ready-for-review; --status in-progress sets it back.
The cell is written through the Drive door, declared as replacing the
annotator's value (drive_door.replacing). When the tab now ready has a tab
built from it, the command prints the generate-sheets command that builds
that tab now (the daily refresh also does, at its next run, if it is empty).
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from planars.schema_values import (
    STATUS_CONSTRUCTION_COLUMN, STATUS_READY, STATUS_STATUS_COLUMN, STATUS_TAB,
    STATUS_VALUES,
)

from . import drive_door
from .drive import load_manifest
from .drive_doorway import get_doorway
from .schemas import load_diagnostic_classes
from .validate_coding import read_status_tab


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding set-tab-status",
        description="Set a tab's status in a class sheet's Status tab.")
    p.add_argument("--lang", required=True, help="language ID (Glottocode)")
    p.add_argument("--class", dest="class_name", required=True, help="class, e.g. phrasal_accent")
    p.add_argument("--construction", required=True, help="the tab, e.g. prescreening")
    p.add_argument("--status", default=STATUS_READY, choices=STATUS_VALUES,
                   help=f"default {STATUS_READY}")
    p.add_argument("--apply", action="store_true", help="write it (default: dry run)")
    return p


def _waiting_dependents(class_name: str, construction: str) -> List[str]:
    """The constructions of ``class_name`` built from ``construction``."""
    for c in load_diagnostic_classes().get("classes", []):
        if c["name"] == class_name:
            return [k["name"] for k in c.get("constructions", [])
                    if k.get("depends_on") == construction]
    return []


def main(args: Optional[argparse.Namespace] = None) -> None:
    args = args or build_parser().parse_args()
    doorway = get_doorway()
    sheets = load_manifest(doorway).get(args.lang, {}).get("sheets", {})
    info = sheets.get(args.class_name)
    if not info:
        sys.exit(f"{args.lang} has no {args.class_name} sheet in the manifest "
                 f"(its classes: {', '.join(sorted(sheets)) or 'none'}).")
    ss = doorway.open_spreadsheet(info["spreadsheet_id"])
    ws, rows = read_status_tab(ss)
    if ws is None or not rows:
        sys.exit(f"The {args.class_name} sheet for {args.lang} has no {STATUS_TAB} tab; "
                 f"python -m coding update-sheets --apply adds it.")
    header = [h.strip() for h in rows[0]]
    ci, si = header.index(STATUS_CONSTRUCTION_COLUMN), header.index(STATUS_STATUS_COLUMN)
    found = [(r, row) for r, row in enumerate(rows[1:], start=2)
             if ci < len(row) and row[ci].strip() == args.construction]
    if not found:
        names = [row[ci].strip() for row in rows[1:] if ci < len(row) and row[ci].strip()]
        sys.exit(f"The {STATUS_TAB} tab has no '{args.construction}' row "
                 f"(its tabs: {', '.join(names)}).")
    r, row = found[0]
    current = row[si].strip() if si < len(row) else ""
    where = f"{args.lang} {args.class_name}/{args.construction}"
    if current == args.status:
        print(f"{where} is already {args.status}; nothing to do.")
        return
    if not args.apply:
        print(f"Would set {where}: {current or '(blank)'} -> {args.status}. "
              f"Add --apply to write it.")
        return
    with drive_door.replacing(ws, f"coordinator set {args.construction} to {args.status}"):
        ws.update_cell(r, si + 1, args.status)
    print(f"Set {where}: {current or '(blank)'} -> {args.status}.")
    if args.status == STATUS_READY:
        for dep in _waiting_dependents(args.class_name, args.construction):
            print(f"  {dep} is built from it at the next daily refresh; to build it now:\n"
                  f"    python -m coding generate-sheets --lang {args.lang} "
                  f"--regen-construction {args.class_name}:{dep}")


if __name__ == "__main__":
    main()
