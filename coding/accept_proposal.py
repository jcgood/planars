"""`python -m coding accept-proposal --lang LANG_ID` — review a language's
proposal sheet and apply what is accepted to the sources.

Phase 10 unit 11a (issue #271); design: docs/ownership-design.md § 3.3. Run
by the coordinator's Claude, from the language's ``proposal`` issue. Without
``--apply`` it lists the proposal (each change, each conflict) and stops.
With ``--apply`` it asks about each one:

1. a change: accept, or reject with a reason; a conflict (a row the
   annotator and the coordinator both changed): take the annotator's
   version, or keep the source's with a reason;
2. applies what is accepted to the sources through the local-file door
   (previous version archived, a change-log line naming the issue and the
   annotator's reasons): the planar file, and the diagnostics YAML
   (``make_forms._diff_diagnostics_tsv_yaml``/``_apply_yaml_diff`` on the
   round-trip YAML, so comments survive; the diagnostics TSV is then
   rebuilt from it). Each is validated first, and nothing is written if
   either fails. A diagnostics change those functions call ambiguous (an
   unknown class or criterion, a class removed) or one in a class with
   per-construction criteria is not applied: it is listed for the
   coordinator to make by hand;
3. names what carries the change into the class sheets: for the planar,
   what ``sync-planar`` recommends (a restructure is given as a dry run,
   to be checked before its live run, Q4); additions the daily refresh
   carries in (update-sheets, sync-params); a new class needs
   ``generate-sheets``;
4. refills the proposal sheet from the new sources (rejected rows go back
   to the source's value; the Drive door saves each tab first) and saves
   the new base;
5. writes Last review on the sheet: the date, what was accepted, what was
   not and why — where the annotator sees the outcome;
6. comments the same, with the next steps, on the issue and closes it.

Nothing is written until every change has been decided.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from . import drive_door, file_door
from .drive import _load_drive_config
from .drive_doorway import get_doorway
from .proposal_diff import Row, apply, compare, describe, without
from .proposal_sheets import (FIRST_REVIEW_TEXT, ID_KEY, LABEL, _read_base, _write_base,
                              issue_title, sheet_name)
from .sheet_spec import (PROPOSAL_DIAGNOSTICS_TAB, PROPOSAL_PLANAR_TAB, PROPOSAL_TABS,
                         REVIEW_TAB_TITLE, WHAT_CHANGED_COLUMN, proposal_sheet_spec)

CODED_DATA = drive_door.CODED_DATA
NOTE = WHAT_CHANGED_COLUMN


class Decision:
    """One change or conflict, and what the coordinator decided."""

    def __init__(self, tab: str, words: List[str], accept_edit: Tuple[int, int, Sequence[Row]],
                 reject_edit: Optional[Tuple[int, int, Sequence[Row]]], conflict: bool):
        self.tab, self.words, self.conflict = tab, words, conflict
        self.accept_edit, self.reject_edit = accept_edit, reject_edit
        self.accepted: Optional[bool] = None
        self.reason = ""

    def summary(self) -> str:
        return "; ".join(self.words)


def _decisions(comparisons: Dict[str, object]) -> List[Decision]:
    out = []
    for title, comp in comparisons.items():
        header = list(comp.base[0]) if comp.base else []

        def bare(rows):
            return [without(r, header, NOTE) for r in rows]

        for h in comp.changes:
            out.append(Decision(title, describe(header, comp.base, h, NOTE),
                                (h.lo, h.hi, bare(h.rows)), None, conflict=False))
        for c in comp.conflicts:
            start, end = c.span
            ours = describe(header, comp.old_base, c.ours, NOTE)
            theirs = describe(header, comp.old_base, c.theirs, NOTE)
            out.append(Decision(title, ["the proposal: " + "; ".join(ours),
                                        "the source now: " + "; ".join(theirs)],
                                (start, end, bare(c.ours.rows)),
                                (start, end, bare(c.theirs.rows)), conflict=True))
    return out


def _ask(decision: Decision) -> None:
    print(f"\n[{decision.tab}] " + ("CONFLICT — changed by both" if decision.conflict
                                    else "Change"))
    for line in decision.words:
        print(f"  {line}")
    question = ("  Take the annotator's version? [y/n] " if decision.conflict
                else "  Accept? [y/n] ")
    while True:
        answer = input(question).strip().lower()
        if answer in ("y", "n"):
            break
    decision.accepted = answer == "y"
    if not decision.accepted:
        while not decision.reason:
            decision.reason = input("  Why not? (the annotator reads this) ").strip()


def _target(comp, decisions: List[Decision]) -> List[Row]:
    """The tab as the source should now render, reasons dropped: the new
    base with each accepted change applied, and each conflict resolved."""
    header = list(comp.base[0])
    edits = []
    for d in decisions:
        if d.accepted:
            edits.append(d.accept_edit)
        elif d.conflict:
            edits.append(d.reject_edit)
    rows = apply(comp.base, edits)
    return [without(r, header, NOTE) for r in rows]


def _grid_frame(rows: List[Row], header: List[str]) -> pd.DataFrame:
    columns = [c for c in header if c != NOTE]
    records = [{c: (r[i] if i < len(r) else "") for i, c in enumerate(header) if c != NOTE}
               for r in rows[1:]]
    return pd.DataFrame(records, columns=columns, dtype=str)


def _new_planar(lang_id: str, rows: List[Row], header: List[str],
                problems: List[str]) -> Optional[pd.DataFrame]:
    from .validate_planar import validate_planar_df
    df = _grid_frame(rows, header)
    errors = [i for i in validate_planar_df(df) if i.level == "error"]
    for e in errors:
        problems.append(f"the planar as accepted would not pass validation: {e.location}: "
                        f"{e.message}")
    return None if errors else df


def _new_diagnostics(lang_id: str, rows: List[Row], header: List[str],
                     problems: List[str], by_hand: List[str]):
    """The edited round-trip YAML, or None if nothing changes or it fails."""
    import yaml
    from .make_forms import _apply_yaml_diff, _diff_diagnostics_tsv_yaml, \
        _load_diagnostics_yaml_for_edit
    from .validate_diagnostics import validate_diagnostics_yaml

    path = file_door.diagnostics_yaml(lang_id).path
    plain = yaml.safe_load(path.read_text(encoding="utf-8"))
    deterministic, ambiguous = _diff_diagnostics_tsv_yaml(_grid_frame(rows, header), plain,
                                                          lang_id)
    per_construction = {name for name, data in (plain.get("classes") or {}).items()
                        if (data or {}).get("construction_criteria")}
    for change in ambiguous:
        by_hand.append(f"diagnostics: {change['kind'].replace('_', ' ')} "
                       f"`{change.get('criterion') or change['class_name']}`")
    keep = []
    for change in deterministic:
        if change["class_name"] in per_construction and change["kind"].startswith("criterion"):
            by_hand.append(f"diagnostics: {change['kind'].replace('_', ' ')} "
                           f"`{change['criterion']}` in `{change['class_name']}`, whose "
                           "criteria are set per construction")
        else:
            keep.append(change)
    if not keep:
        return None, []
    data = _apply_yaml_diff(_load_diagnostics_yaml_for_edit(path), keep)
    blocking = [i for i in validate_diagnostics_yaml(data, lang_id)
                if i.level == "error" and i.blocking]
    for e in blocking:
        problems.append(f"the diagnostics file as accepted would not pass validation: "
                        f"{e.location}: {e.message}")
    return (None if blocking else data), keep


def _next_steps(lang_id: str, old_planar: Optional[pd.DataFrame],
                new_planar: Optional[pd.DataFrame], diag_changes: List[Dict]) -> List[str]:
    from .sync_planar import _diff_positions, _recommend
    steps = []
    if new_planar is not None and old_planar is not None:
        rec = _recommend(_diff_positions(old_planar, new_planar), lang_id)
        if rec.startswith("python -m coding restructure-sheets"):
            dry = rec.split("  #")[0].replace(" --apply", "")
            steps.append(f"The planar's positions changed. Check the dry run, then run it "
                         f"with --apply: `{dry}`")
        elif rec.startswith("python -m coding"):
            steps.append(f"New positions reach the class sheets with the daily refresh, or "
                         f"now: `{rec}`")
    if any(c["kind"] == "class_added" for c in diag_changes):
        steps.append(f"A class was added. Make its sheet: "
                     f"`python -m coding generate-sheets --lang {lang_id} --apply`")
    if any(c["kind"] != "class_added" for c in diag_changes):
        steps.append("Criterion and construction changes reach the class sheets with the "
                     "daily refresh (sync-params and update-sheets), or now: "
                     "`python -m coding sync-params --apply` then "
                     "`python -m coding update-sheets --apply`")
    return steps


def _review_rows(decisions: List[Decision], issue: Optional[int], by_hand: List[str]) -> List[List[str]]:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = [[REVIEW_TAB_TITLE], [f"Reviewed {day}" + (f" (issue #{issue})" if issue else "")], [""]]
    accepted = [d for d in decisions if d.accepted]
    rejected = [d for d in decisions if not d.accepted]
    if accepted:
        rows.append(["Accepted:"])
        rows += [[f"  {d.tab}: {d.summary()}"] for d in accepted]
        rows.append([""])
    if rejected:
        rows.append(["Not accepted:"])
        rows += [[f"  {d.tab}: {d.summary()} — {d.reason}"] for d in rejected]
        rows.append([""])
    if by_hand:
        rows.append(["Accepted, to be made by the coordinator by hand:"])
        rows += [[f"  {line}"] for line in by_hand]
        rows.append([""])
    rows += [[line] for line in FIRST_REVIEW_TEXT[2:]]
    return rows


def _issue_comment(decisions: List[Decision], by_hand: List[str], steps: List[str]) -> List[str]:
    lines = ["Reviewed with `accept-proposal`; the outcome is on the sheet's Last review tab.", ""]
    for label_, chosen in (("Accepted", [d for d in decisions if d.accepted]),
                           ("Not accepted", [d for d in decisions if not d.accepted])):
        if chosen:
            lines.append(f"**{label_}:**")
            lines += [f"- {d.tab}: {d.summary()}" + (f" — {d.reason}" if d.reason else "")
                      for d in chosen]
            lines.append("")
    if by_hand:
        lines.append("**Accepted, but to be made in the source by hand** (the tooling "
                     "cannot apply these safely):")
        lines += [f"- {line}" for line in by_hand]
        lines.append("")
    if steps:
        lines.append("**Next:**")
        lines += [f"- {s}" for s in steps]
    return lines


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding accept-proposal",
        description="Review a language's proposal sheet: list its changes (dry run), or "
                    "decide each one and apply the accepted ones to the sources (--apply).")
    p.add_argument("--lang", metavar="LANG_ID", required=True)
    p.add_argument("--apply", action="store_true",
                   help="Ask about each change, then write (default: list them).")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    lang_id = args.lang
    from . import issues

    sheet_id = _load_drive_config().get(lang_id, {}).get(ID_KEY)
    base = _read_base(lang_id)
    if not sheet_id or base is None:
        sys.exit(f"ERROR: {lang_id} has no proposal sheet with a saved base; make it with "
                 f"`python -m coding proposal-sheets --lang {lang_id} --apply`.")
    ss = get_doorway().open_spreadsheet(sheet_id)
    spec = proposal_sheet_spec(lang_id, CODED_DATA)
    fills = {t: [list(spec.tab(t).header)] + [list(r) for r in spec.tab(t).rows or ()]
             for t, _ in PROPOSAL_TABS}
    comparisons = {t: compare(base.get(t, []), ss.worksheet(t).get_all_values(), fills[t], NOTE)
                   for t, _ in PROPOSAL_TABS}
    decisions = _decisions(comparisons)
    if not decisions:
        print(f"{sheet_name(lang_id)} holds no proposal.")
        return
    issue = issues.find_open(LABEL, title=issue_title(lang_id))
    print(f"{sheet_name(lang_id)}: {len(decisions)} change(s) to decide "
          f"({sum(d.conflict for d in decisions)} conflict(s)).")
    if not args.apply:
        for d in decisions:
            print(f"\n[{d.tab}] {'CONFLICT' if d.conflict else 'Change'}")
            for line in d.words:
                print(f"  {line}")
        print(f"\nRun with --apply to decide each one: "
              f"`python -m coding accept-proposal --lang {lang_id} --apply`")
        return
    for d in decisions:
        _ask(d)

    # Work out both new sources before writing either.
    problems: List[str] = []
    by_hand: List[str] = []
    planar_rows = _target(comparisons[PROPOSAL_PLANAR_TAB],
                          [d for d in decisions if d.tab == PROPOSAL_PLANAR_TAB])
    diag_rows = _target(comparisons[PROPOSAL_DIAGNOSTICS_TAB],
                        [d for d in decisions if d.tab == PROPOSAL_DIAGNOSTICS_TAB])
    planar_header = fills[PROPOSAL_PLANAR_TAB][0]
    old_planar = pd.read_csv(file_door.planar(lang_id).path, sep="\t", dtype=str,
                             keep_default_na=False)
    new_planar = _new_planar(lang_id, planar_rows, planar_header, problems)
    new_yaml, diag_changes = _new_diagnostics(lang_id, diag_rows,
                                              fills[PROPOSAL_DIAGNOSTICS_TAB][0],
                                              problems, by_hand)
    if problems:
        print("\nERROR: nothing was written:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)

    accepted = [d for d in decisions if d.accepted]
    ref = f"#{issue}" if issue else "the proposal sheet"
    why = f"accepted from {ref}: " + "; ".join(
        d.summary() for d in accepted) if accepted else ""
    from .make_forms import _dump_diagnostics_yaml
    if accepted and new_planar is not None and not new_planar.equals(old_planar):
        file_door.write(file_door.planar(lang_id), file_door.frame_text(new_planar), why=why)
        print(f"  planar_{lang_id}.tsv updated")
    else:
        new_planar = None
    if accepted and new_yaml is not None:
        from .sync_diagnostics_yaml import _sync_to_tsv
        file_door.write(file_door.diagnostics_yaml(lang_id), _dump_diagnostics_yaml(new_yaml),
                        why=why)
        _sync_to_tsv(lang_id, apply=True, error_langs=[])
        print(f"  diagnostics_{lang_id}.yaml updated")

    # Refill the sheet from the new sources and record the review on it.
    spec = proposal_sheet_spec(lang_id, CODED_DATA)
    new_fills = {t: [list(spec.tab(t).header)] + [list(r) for r in spec.tab(t).rows or ()]
                 for t, _ in PROPOSAL_TABS}
    for title, _ in PROPOSAL_TABS:
        ws = ss.worksheet(title)
        with drive_door.replacing(ws, f"{sheet_name(lang_id)} reviewed ({ref}); refilled "
                                      "from the sources"):
            ws.clear()
            ws.update(new_fills[title], "A1")
    _write_base(lang_id, new_fills, f"proposal sheet refilled after review ({ref})")
    review = ss.worksheet(REVIEW_TAB_TITLE)
    review_rows = _review_rows(decisions, issue, by_hand)
    review.clear()
    review.update(review_rows, "A1")

    steps = _next_steps(lang_id, old_planar, new_planar, diag_changes)
    body = "\n".join(_issue_comment(decisions, by_hand, steps))
    if issue:
        issues.close(issue, body)
        print(f"  closed #{issue}")
    print("\n" + body)


if __name__ == "__main__":
    main()
