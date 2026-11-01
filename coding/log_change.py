"""`python -m coding log-change` — log a source edited by hand: what kind of
change it was, what it did to answers and spans, and the file's fingerprint.

Phase 10 unit 17 (issue #271); design: docs/change-log-design.md § 4.1. A
source (``coding/source_log.py``: the schema files, and each language's
planar and diagnostics file) may be edited by hand, but every change to one
gets a line in its stream's change log, and nothing can be committed until
it has (``integrity-check --check-changes``, before a commit, in CI and in
the daily refresh).

    python -m coding log-change --change CLASS --layer LAYER --why "#N: …" [--answers TEXT] [--apply]
    python -m coding log-change --lang LANG_ID --change CLASS --layer LAYER --why "#N: …" [--apply]

Without ``--lang`` it logs the schema files (``schemas/changes.tsv``); with
it, that language's sources (its ``changes.tsv`` in planars-data). It finds
every source whose fingerprint differs from its last line, puts back the
version that line was written for (``source_log.previous_text``), measures
the effects (``change_effects.measure``: answered cells broken, spans moved)
and prints the lines. ``--change`` and ``--layer`` repeat, pairwise, for
several changes in one edit: one line each, the fingerprint on the last.
Claude drafts them from the diff and the person confirms: a rename and a
remove-plus-add look alike in a diff.

For a schema edit the *before* side runs the analysis code as last
committed, so a span rule is logged together with its module change, after
both are written and before they are committed: the line then records the
spans they move (Updating a span rule, coordinator guide).

A *breaking* change (answers broken, or spans moved: § 6.1) must name an
issue in ``--why`` (``#N``) and say in ``--answers`` what happens to the
existing answers (the command that carries them over, or the issue telling
the annotator which cells to redo); it is refused without both.

With ``--apply``: for a language, the previous version goes into its
archive and the source, archive copy and log are committed and pushed in
planars-data (the local-file door). For the schemas, the previous version
goes into ``schemas/archive/`` (``source_log.archive_schema``, unit 18), the
lines are added to ``schemas/changes.tsv`` and the edited files, their
archive copies and the log are staged, to be
committed together with whatever else goes with them (the pre-commit hook
checks that they match). When spans moved, the snapshots are regenerated
and staged in planars too (``tests/snapshots/``: the record of how).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import List, Optional, Tuple

from . import change_effects, file_door, source_log

BY = "log-change"
ISSUE = re.compile(r"#\d+")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding log-change",
        description="Log a source edited by hand (the schemas, or with --lang a language's "
                    "planar and diagnostics file): change class, layer, effects on answers "
                    "and spans, fingerprint. Without --apply, show the lines.")
    p.add_argument("--lang", metavar="LANG_ID",
                   help="log this language's sources (default: the schema files)")
    p.add_argument("--change", action="append", default=[], metavar="CLASS",
                   choices=[c for c in file_door.CHANGE_CLASSES if c != file_door.BASELINE],
                   help="what kind of change (repeat, paired with --layer, for several)")
    p.add_argument("--layer", action="append", default=[], metavar="LAYER",
                   choices=list(file_door.LAYERS),
                   help="what it touches: shape (columns and values), taxonomy (the theory's "
                        "categories), convention (how coders write things)")
    p.add_argument("--why", default="", metavar="TEXT",
                   help="why it was made; a breaking change names its issue (#N)")
    p.add_argument("--answers", default="", metavar="TEXT",
                   help="for a breaking change: what happens to the existing answers (the "
                        "command that carries them over, or the issue for the annotator)")
    p.add_argument("--apply", action="store_true", help="write the lines")
    return p


def _pairs(args: argparse.Namespace) -> List[Tuple[str, str]]:
    if not args.change or len(args.change) != len(args.layer):
        sys.exit("ERROR: give --change and --layer the same number of times, one pair per "
                 f"change (classes: {', '.join(file_door.CHANGE_CLASSES[:-1])}; layers: "
                 f"{', '.join(file_door.LAYERS)}).")
    return list(zip(args.change, args.layer))


def main(args: Optional[argparse.Namespace] = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    stream = args.lang or source_log.SCHEMAS
    if args.lang and not (file_door.CODED_DATA / args.lang).is_dir():
        sys.exit(f"ERROR: no language folder coded_data/{args.lang}.")
    if stream == source_log.SCHEMAS and source_log.unplaced():
        sys.exit("ERROR: schemas/ has files that are neither logged nor exempt: "
                 f"{', '.join(source_log.unplaced())}. Add each to SCHEMA_SOURCES or "
                 "NOT_LOGGED in coding/source_log.py, with its reason.")
    pending = source_log.unlogged([stream])
    if not pending:
        print(f"Every source in {stream} matches its last logged line; nothing to log.")
        return
    pairs = _pairs(args)
    if not args.why.strip():
        sys.exit("ERROR: --why is required: why the change was made.")

    before = {}
    for u in pending:
        found, text = source_log.previous_text(u.source)
        if not found:
            sys.exit(f"ERROR: {u.source.shown}: the version its last line was written for "
                     f"(fingerprint {u.logged}) is in neither the archive nor git history, so "
                     f"what the edit did cannot be measured. Restore it from a backup or ask "
                     f"the coordinator; nothing was logged.")
        before[u.source.path] = text
    print(f"Measuring the effects of {len(pending)} edited file(s) on every language's "
          f"answers and spans…")
    # A schema edit is measured with the code as last committed on the
    # before side, so a span rule and its module change count as one.
    code_from = "HEAD" if stream == source_log.SCHEMAS and (source_log.ROOT / ".git").exists() \
        else None
    effects = change_effects.measure(before, code_from=code_from)

    problems = []
    if effects.breaking:
        if not ISSUE.search(args.why):
            problems.append("--why must name an issue (#N): this change is breaking")
        if not args.answers.strip():
            problems.append("--answers must say what happens to the existing answers: this "
                            "change is breaking")
    lines = []
    for u in pending:
        new = source_log.read_text(u.source.path)
        what = source_log.describe(u.source, before[u.source.path], new)
        if args.answers.strip():
            what += f"; answers: {args.answers.strip()}"
        lines.append((u, what))
        print(f"\n{u.source.shown}: {what}")
        for change, layer in pairs:
            print(f"  {change} / {layer}")
    print(f"\nAnswers broken: {effects.answers_cell()}")
    print(f"Spans moved: {effects.spans_cell() or 'none'}")
    print(f"Level: {'breaking' if effects.breaking else 'not breaking'} "
          f"(versions are read from these lines: coding/versions.py)")
    if problems:
        sys.exit("ERROR: nothing was logged:\n  " + "\n  ".join(problems))
    if not args.apply:
        print("\nRun again with --apply to write the lines.")
        return

    if stream == source_log.SCHEMAS:
        rows, archived = [], []
        for u, what in lines:
            mark = file_door.fingerprint(u.source.path.read_bytes())
            old = before[u.source.path]
            previous = source_log.archive_schema(u.source, old) if old is not None else ""
            if previous:
                archived.append(source_log.previous_copy(source_log.SCHEMAS, previous))
            for i, (change, layer) in enumerate(pairs):
                rows.append(source_log.line(
                    u.source, what=what, by=BY, why=args.why.strip(), change=change, layer=layer,
                    answers=effects.answers_cell(), spans=effects.spans_cell(),
                    mark=mark if i == len(pairs) - 1 else "", previous=previous))
        source_log.append_project_lines(rows)
        source_log.stage([source_log.PROJECT_LOG] + [u.source.path for u, _ in lines] + archived)
        print(f"\nLogged {len(rows)} line(s) in schemas/changes.tsv and staged it with the "
              f"edited file(s). Commit them together and push.")
    else:
        for u, what in lines:
            file_door.log_hand_edit(u.source.target, before[u.source.path], why=args.why.strip(),
                                    what=what, changes=pairs, effects=effects)
        print(f"\nLogged in {stream}/changes.tsv; planars-data is committed and pushed when the "
              f"command ends.")
    if effects.spans_cell():
        _regenerate_snapshots()


def _regenerate_snapshots() -> None:
    """Spans moved: rewrite tests/snapshots/ and stage it, so the commit
    carries how they moved (and the pre-push check passes)."""
    root = source_log.ROOT
    done = subprocess.run([sys.executable, str(root / "generate_snapshots.py")], cwd=root,
                          capture_output=True, text=True)
    if done.returncode != 0:
        print(f"WARNING: the snapshots could not be regenerated: {done.stderr.strip()[-500:]}. "
              f"Run `python generate_snapshots.py` and commit tests/snapshots/.")
        return
    source_log.stage([root / "tests" / "snapshots"])
    print("Spans moved: the snapshots are regenerated and staged in planars "
          "(review with `git diff --cached tests/snapshots/`); commit them.")


if __name__ == "__main__":
    main()
