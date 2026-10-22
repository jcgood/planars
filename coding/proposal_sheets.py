"""`python -m coding proposal-sheets` — each language's proposal sheet, made
and kept filled from the sources.

Phase 10 unit 11a (issue #271); design: docs/ownership-design.md § 3.2–3.4.
A proposal sheet is where a language's annotator proposes changes to the
planar and the diagnostics file, the two sources only the coordinator edits.
Its tabs (``sheet_spec.proposal_sheet_spec``): **Last review** (the
tooling's; what the last review accepted and rejected, and how to propose a
change), then **Planar** and **Diagnostics**, each a copy of its source plus
a **What changed?** column, every cell the annotator's. It sits in the
language's folder; the annotator is a writer by name, and the coordinators
are writers through the root folder (Q2).

What it was last filled with is saved in planars-data as the language's
**base** (``file_door.proposal_base``, archived and logged like any data
file). The annotator's proposal is the sheet's difference from the base, not
from today's source, so a coordinator's own edit to a source meanwhile is not
read as the annotator proposing to undo it (§ 3.4).

For each language with a folder in the ID file:

- no proposal sheet yet: make it, fill it from the sources, save the base,
  record its ID in the ID file (``proposal_spreadsheet_id``);
- a tab still holding exactly the base: refilled from the sources when they
  have changed (inside the Drive door's ``replacing()``, which saves the tab
  first), and the base updated;
- a tab that differs from the base holds a proposal and is left as it is.

Dry run by default; ``--apply`` writes. A sheet with no base, or a language
whose sources can't be read, is reported and the run exits non-zero after
the other languages.

Not here yet (the rest of 11a): the daily comparison that turns a proposal
into a ``proposal`` issue, refreshing the untouched rows of a tab that holds
one, and ``accept-proposal``.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Optional

from . import drive_door, file_door
from .drive import _load_drive_config, _save_drive_config, ensure_user_permission
from .drive_doorway import get_doorway
from .sheet_spec import PROPOSAL_TABS, REVIEW_TAB_TITLE, proposal_sheet_spec

CODED_DATA = drive_door.CODED_DATA
ID_KEY = "proposal_spreadsheet_id"

# What Last review says before any proposal has been reviewed. Moves into
# the schema with the other sentences annotators read (unit 11d).
FIRST_REVIEW_TEXT = (
    "No proposal has been reviewed yet.",
    "",
    "To propose a change to this language's planar structure or diagnostics, "
    "edit the Planar or Diagnostics tab: change a cell, add a row or delete one, "
    "and say why in that row's What changed? column.",
    "Nothing else changes until the coordinator has reviewed your proposal. "
    "What was accepted, and why anything was not, is written here.",
)


def sheet_name(lang_id: str) -> str:
    return f"proposal_{lang_id}"


def _grid_of(tab) -> List[List[str]]:
    """A proposal tab's spec as the grid written to the sheet."""
    return [list(tab.header)] + [list(r) for r in tab.rows or ()]


def _normal(grid: List[List[str]]) -> List[List[str]]:
    """``grid`` as compared: cells stripped, trailing blanks and blank rows
    dropped, as Sheets returns a grid."""
    rows = [[str(v).strip() for v in r] for r in grid]
    rows = [r[:max((i + 1 for i, v in enumerate(r) if v), default=0)] for r in rows]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def _read_base(lang_id: str) -> Optional[Dict[str, List[List[str]]]]:
    text = file_door.read(file_door.proposal_base(lang_id))
    return None if text is None else json.loads(text)


def _write_base(lang_id: str, base: Dict[str, List[List[str]]], why: str) -> None:
    file_door.write(file_door.proposal_base(lang_id),
                    json.dumps(base, indent=2, ensure_ascii=False) + "\n", why=why)


def _review_rows() -> List[List[str]]:
    return [[REVIEW_TAB_TITLE]] + [[line] for line in FIRST_REVIEW_TEXT]


def _create(doorway, lang_id: str, folder_id: str, fills: Dict[str, List[List[str]]]):
    """Make the sheet in the language's folder and fill it."""
    ss = doorway.create_spreadsheet(sheet_name(lang_id),
                                    identity=drive_door.lang_file(drive_door.PROPOSAL_SHEET,
                                                                  lang_id))
    doorway.move_file(ss.id, folder_id)
    review = ss.sheet1
    review.update_title(REVIEW_TAB_TITLE)
    review.update(_review_rows(), "A1")
    for title, _ in PROPOSAL_TABS:
        grid = fills[title]
        ws = ss.add_worksheet(title=title, rows=len(grid) + 100, cols=len(grid[0]))
        ws.update(grid, "A1")
    return ss


def _refill(ss, title: str, grid: List[List[str]], lang_id: str) -> None:
    ws = ss.worksheet(title)
    with drive_door.replacing(ws, f"{sheet_name(lang_id)}'s {title} tab held no proposal; "
                                  "refilled from the changed source"):
        ws.clear()
        ws.update(grid, "A1")


def _share(doorway, lang_id: str, file_id: str) -> None:
    from .people import annotator_email
    email = annotator_email(lang_id)
    if email:
        ensure_user_permission(doorway, file_id, email, "writer")
    else:
        print(f"  [{lang_id}] no annotator in people.yaml: shared with the coordinators only")


def _one_language(doorway, lang_id: str, config: Dict, apply: bool,
                  problems: List[str]) -> None:
    """Make or refill one language's sheet."""
    try:
        spec = proposal_sheet_spec(lang_id, CODED_DATA)
    except Exception as exc:  # noqa: BLE001 - reported, the run goes on
        problems.append(f"[{lang_id}] its sources could not be read, so its proposal "
                        f"sheet was not made or refilled: {exc}")
        return
    fills = {title: _grid_of(spec.tab(title)) for title, _ in PROPOSAL_TABS}
    sheet_id = config.get(lang_id, {}).get(ID_KEY)

    if not sheet_id:
        folder_id = config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            problems.append(f"[{lang_id}] no language folder in drive_config.json, so no "
                            "proposal sheet could be made (run generate-sheets for it first)")
            return
        if not apply:
            print(f"  [{lang_id}] would make {sheet_name(lang_id)} in its folder")
            return
        found = doorway.list_files(
            q=(f"name='{sheet_name(lang_id)}' and '{folder_id}' in parents"
               " and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"),
            fields="files(id)")
        if found:
            # Made by a run that stopped before recording it: its content
            # can't be trusted, and a second sheet would split proposals.
            problems.append(f"[{lang_id}] its folder already holds a {sheet_name(lang_id)} "
                            f"(id {found[0]['id']}) that drive_config.json doesn't record; "
                            "nothing was made. Check it and delete it on Drive, then re-run")
            return
        ss = _create(doorway, lang_id, folder_id, fills)
        _share(doorway, lang_id, ss.id)
        _write_base(lang_id, fills, "proposal sheet made and filled from the sources")
        # Saved at once, not after the loop: a crash on a later language
        # would otherwise lose this ID and the next run make a second sheet.
        config.setdefault(lang_id, {})[ID_KEY] = ss.id
        _save_drive_config(config)
        print(f"  [{lang_id}] made {sheet_name(lang_id)}: {ss.url}")
        return

    base = _read_base(lang_id)
    if base is None:
        problems.append(f"[{lang_id}] {sheet_name(lang_id)} exists but planars-data has no "
                        f"{file_door.proposal_base(lang_id).relpath}, so what the annotator "
                        "changed can't be told; nothing was written to it")
        return
    ss = doorway.open_spreadsheet(sheet_id)
    new_base = dict(base)
    for title, _ in PROPOSAL_TABS:
        now = ss.worksheet(title).get_all_values()
        if _normal(now) != _normal(base.get(title, [])):
            print(f"  [{lang_id}] {title}: holds a proposal; left as it is")
            continue
        if _normal(fills[title]) == _normal(base.get(title, [])):
            print(f"  [{lang_id}] {title}: up to date")
            continue
        if not apply:
            print(f"  [{lang_id}] {title}: would refill from the changed source")
            continue
        _refill(ss, title, fills[title], lang_id)
        new_base[title] = fills[title]
        print(f"  [{lang_id}] {title}: refilled from the changed source")
    if apply and new_base != base:
        _write_base(lang_id, new_base, "proposal sheet refilled from the changed sources")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding proposal-sheets",
        description="Make each language's proposal sheet, and refill the tabs that "
                    "hold no proposal when a source has changed.")
    p.add_argument("--lang", metavar="LANG_ID", help="Only this language.")
    p.add_argument("--apply", action="store_true",
                   help="Write to Drive and planars-data (default: dry run).")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    config = _load_drive_config()
    langs = [args.lang] if args.lang else sorted(k for k in config if not k.startswith("_"))
    print(f"{'' if args.apply else 'DRY RUN — '}Proposal sheets")
    doorway = get_doorway()
    problems: List[str] = []
    for lang_id in langs:
        _one_language(doorway, lang_id, config, args.apply, problems)
    if not args.apply:
        print("\nRun with --apply to write.")
    if problems:
        print("\nERROR: some proposal sheets were not made or refilled:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)


if __name__ == "__main__":
    main()
