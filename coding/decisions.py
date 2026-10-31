"""`python -m coding record-decision` — write a decision into its log and
close the issue it settles. Also the rule that every closed `diagnostics` or
`linguistics` issue has one (the daily refresh's `decisions` step, and
integrity-check's DECISIONS section).

Phase 10 unit 16e (issue #271); design: docs/plain-record-design.md § 4.
A decision about the framework or about one language used to live only in a
GitHub thread, unless it happened to change a file. The record is now one
line in a plain TSV, and the issue holds only the discussion that led to it.

**The two logs** (``COLUMNS``: date, issue, decided by, decision, scope):

- ``schemas/decisions.tsv`` (``FRAMEWORK_LOG``): decisions about the
  framework (a class, a criterion, a term, a span rule, a convention). In
  this public repository, so git keeps its history: ``record`` commits that
  one file and pushes it at once, since the daily refresh reads it from
  GitHub;
- ``coded_data/{lang}/decisions.tsv`` (``file_door.decisions``): decisions
  about one language (its planar, how a construction is coded, a proposal
  change not accepted). Private planars-data; written through the local-file
  door, which archives the previous version and logs the change.

A line does not list the files a decision changed: each of those changes
names the issue in its own change-log line. ``decided by`` holds names from
people.yaml, ``NAME_SEPARATOR`` between several; a name not there is
refused, so the column can be trusted. The same line is never written twice
(a re-run after GitHub failed writes nothing new and finishes the issue).

    python -m coding record-decision --issue N --by NAME --decision TEXT \\
        [--lang LANG_ID] [--scope WHAT] [--keep-open] [--apply]
    python -m coding record-decision --batch FILE.tsv [--apply]

Without ``--apply`` it prints the line and where it would go. With it, it
writes the line, comments the decision on the issue (the repository is
public: the decision's words are posted there) and closes it, unless
``--keep-open`` (an issue that settles several things, such as #318, closes
with its last one). ``accept-proposal`` writes each change it does not
accept through ``record`` too. ``--batch`` records many lines from a TSV
(``BATCH_COLUMNS``, each with its own date) with no comments and no issue
closed, all or none: the one-time backfill of issues already closed.

**The rule** (``needs_decision: true`` in schemas/issue_labels.yaml, read by
``issues.decision_labels``): an issue closed under such a label on or after
``CHECK_FROM`` whose number is in neither log is ``unrecorded``; the daily
refresh reopens it (``reopen_unrecorded``) with a comment giving the command
to record its decision, or to correct its label if it needed none.
``CHECK_FROM`` is the day the rule began (2026-11-01): issues closed before
it are the backfill's (plain-record-design § 7 Q4), and the date moves back
once that batch is recorded.
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from . import file_door, issues

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK_LOG = ROOT / "schemas" / "decisions.tsv"
COLUMNS = ("date", "issue", "decided by", "decision", "scope")
NAME_SEPARATOR = "; "
# Issues closed before this day need no line yet: see the module docstring.
CHECK_FROM = "2026-11-01"


@dataclass(frozen=True)
class Decision:
    """One line of a decision log."""
    issue: Optional[int]     # None only for accept-proposal with no open issue
    decided_by: str
    decision: str
    scope: str = ""
    date: str = ""           # filled with today's date (UTC) when empty

    def row(self) -> List[str]:
        day = self.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return [day, f"#{self.issue}" if self.issue else "", self.decided_by,
                " ".join(self.decision.split()), self.scope]


# ---------------------------------------------------------------------------
# The logs
# ---------------------------------------------------------------------------

def checked_names(by: str) -> str:
    """``by`` with each name confirmed in people.yaml; raises ValueError."""
    from .people import known_names
    names = [n.strip() for n in by.split(NAME_SEPARATOR.strip()) if n.strip()]
    known = known_names()
    unknown = [n for n in names if n not in known]
    if not names or unknown:
        raise ValueError(
            f"decided by {by!r}: {', '.join(repr(n) for n in unknown) or 'no name'} "
            f"is not a name in planars-data's people.yaml (known: {', '.join(known)}). "
            f"Give each person by that name, several separated by '{NAME_SEPARATOR}'.")
    return NAME_SEPARATOR.join(names)


def _rows(text: Optional[str]) -> List[Dict[str, str]]:
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter="\t"))


def _with(text: Optional[str], decision: Decision) -> str:
    """The log's text with ``decision`` added at the end."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
    if not text:
        writer.writerow(COLUMNS)
    else:
        header = tuple(next(csv.reader(io.StringIO(text), delimiter="\t"), []))
        if header != COLUMNS:
            raise RuntimeError(f"a decision log has the columns {list(header)}, not "
                               f"{list(COLUMNS)}; nothing was written.")
        if not text.endswith("\n"):
            buf.write("\n")
    writer.writerow(decision.row())
    return (text or "") + buf.getvalue()


def _already(text: Optional[str], decision: Decision) -> bool:
    row = dict(zip(COLUMNS, decision.row()))
    return any(r.get("issue") == row["issue"] and r.get("decision") == row["decision"]
               for r in _rows(text))


def where(lang_id: Optional[str]) -> str:
    """The log's name, as a person reads it."""
    if lang_id:
        return f"planars-data's `{lang_id}/{file_door.decisions(lang_id).relpath}`"
    shown = (FRAMEWORK_LOG.relative_to(ROOT) if FRAMEWORK_LOG.is_relative_to(ROOT)
             else FRAMEWORK_LOG)
    return f"`{shown}`"


def record(decision: Decision, lang_id: Optional[str] = None, *, commit: bool = True) -> bool:
    """Add ``decision`` to the language's log, or to the framework's
    without ``lang_id``. False if the same line is already there. With
    ``commit=False`` the framework log is left for the caller to commit
    (``commit_framework_log``), as a batch does once at the end."""
    why = (f"decision for #{decision.issue}" if decision.issue
           else "decision with no issue")
    if lang_id:
        target = file_door.decisions(lang_id)
        old = file_door.read(target)
        if _already(old, decision):
            return False
        file_door.write(target, _with(old, decision), why=why,
                        what=f"decision added: {decision.row()[3][:80]}")
        return True
    old = FRAMEWORK_LOG.read_text(encoding="utf-8") if FRAMEWORK_LOG.exists() else None
    if _already(old, decision):
        return False
    with open(FRAMEWORK_LOG, "w", encoding="utf-8", newline="") as f:
        f.write(_with(old, decision))
    if commit:
        commit_framework_log(why)
    return True


def commit_framework_log(why: str) -> None:
    """Commit only the framework log and push it, so the daily refresh, which
    reads it from GitHub, sees the line. Nothing else staged goes with it.
    Skipped when the log is not in this repository (tests)."""
    if not FRAMEWORK_LOG.resolve().is_relative_to(ROOT) or not (ROOT / ".git").exists():
        return
    rel = str(FRAMEWORK_LOG.relative_to(ROOT))

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)

    for step in (["add", "--", rel],
                 ["commit", "-m", f"decisions: {why}", "--only", "--", rel]):
        done = git(*step)
        if done.returncode != 0:
            raise RuntimeError(f"{rel} is written but could not be committed (git {step[0]}): "
                               f"{(done.stderr or done.stdout).strip()}. Commit and push it "
                               f"by hand, or the daily refresh will reopen the issue.")
    pushed = file_door.push(ROOT)
    if pushed.returncode != 0:
        print(f"WARNING: {rel} is committed but not pushed ({pushed.stderr.strip()}). "
              f"Run `git push`: until GitHub has it, the daily refresh reopens the issue.")


def _framework_text() -> Optional[str]:
    return FRAMEWORK_LOG.read_text(encoding="utf-8") if FRAMEWORK_LOG.exists() else None


def recorded_issues() -> Set[int]:
    """Every issue number in either log, all languages included."""
    texts = [_framework_text()]
    texts += [file_door.read(file_door.decisions(lang_id)) for lang_id in file_door.language_ids()]
    out: Set[int] = set()
    for text in texts:
        for row in _rows(text):
            number = (row.get("issue") or "").lstrip("#")
            if number.isdigit():
                out.add(int(number))
    return out


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------

def unrecorded(since: str = CHECK_FROM) -> List[Dict]:
    """Issues closed under a ``needs_decision`` label on or after ``since``
    whose number is in neither log, lowest number first."""
    done = recorded_issues()
    found: Dict[int, Dict] = {}
    for label in issues.decision_labels():
        for issue in issues.list_closed(label):
            if (issue.get("closedAt") or "")[:10] >= since and issue["number"] not in done:
                found[issue["number"]] = issue
    return [found[n] for n in sorted(found)]


def reopen_message(number: int) -> str:
    labels = " or ".join(f"`{l}`" for l in issues.decision_labels())
    return (
        f"Reopened: this issue was closed without its decision in a decision log. An issue "
        f"labelled {labels} ends in a decision, and the record of it is a line in a file, "
        f"not this thread (docs/plain-record-design.md § 4).\n\n"
        f"To record it, draft the decision from this thread and run (it closes the issue "
        f"again):\n\n"
        f"```bash\npython -m coding record-decision --issue {number} --by \"NAME\" "
        f"--decision \"…\" --apply\n```\n\n"
        f"Add `--lang LANG_ID` for a decision about one language. A decision to change "
        f"nothing is still a line.\n\n"
        f"If the issue needed no linguistic decision (a tooling bug), correct its label "
        f"instead, then close it:\n\n"
        f"```bash\npython -m coding issue --relabel {number} --remove LABEL --add bug\n```\n")


def reopen_unrecorded() -> List[int]:
    """Reopen every ``unrecorded`` issue with the command that records it."""
    reopened = []
    for issue in unrecorded():
        issues.reopen(issue["number"], reopen_message(issue["number"]))
        reopened.append(issue["number"])
    return reopened


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding record-decision",
        description="Write a decision into its log (the framework's, or one language's "
                    "with --lang), comment it on its issue and close the issue. Without "
                    "--apply, show the line and write nothing.")
    p.add_argument("--issue", type=int, metavar="N",
                   help="the issue the decision settles")
    p.add_argument("--by", metavar="NAME",
                   help=f"who decided, as named in people.yaml; several separated by "
                        f"'{NAME_SEPARATOR}'")
    p.add_argument("--batch", type=Path, metavar="FILE.tsv",
                   help=f"instead of one decision: a TSV with the columns {', '.join(BATCH_COLUMNS)} "
                        "(lang blank for the framework; date blank for today), each line "
                        "recorded with no comment on its issue and no issue closed (the "
                        "one-time backfill of issues already closed)")
    p.add_argument("--decision", metavar="TEXT",
                   help="the decision in a sentence or two, plainly worded (posted on the "
                        "public issue)")
    p.add_argument("--lang", metavar="LANG_ID",
                   help="a decision about one language: its log in planars-data")
    p.add_argument("--scope", default="", metavar="WHAT",
                   help="optional: the class, criterion or position it concerns")
    p.add_argument("--keep-open", action="store_true",
                   help="comment but leave the issue open (it settles more than this)")
    p.add_argument("--apply", action="store_true", help="write, comment and close")
    return p


BATCH_COLUMNS = ("issue", "lang", "date", "decided by", "decision", "scope")


def _batch(path: Path, apply: bool) -> None:
    """Record every line of a batch file; nothing is written unless every
    line is valid. No comments, no closing: the issues are already closed,
    and a comment on each would notify everyone watching them."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
    if tuple(reader.fieldnames or ()) != BATCH_COLUMNS:
        sys.exit(f"ERROR: {path} has the columns {list(reader.fieldnames or [])}, not "
                 f"{list(BATCH_COLUMNS)}.")
    problems, todo = [], []
    for n, row in enumerate(rows, 2):
        issue, lang = (row["issue"] or "").lstrip("#").strip(), (row["lang"] or "").strip()
        date = (row["date"] or "").strip()
        if not issue.isdigit():
            problems.append(f"line {n}: issue {row['issue']!r} is not a number")
        if lang and not (file_door.CODED_DATA / lang).is_dir():
            problems.append(f"line {n}: no language folder coded_data/{lang}")
        if date and not (len(date) == 10 and date[4] == date[7] == "-"):
            problems.append(f"line {n}: date {date!r} is not YYYY-MM-DD")
        if not (row["decision"] or "").strip():
            problems.append(f"line {n}: no decision")
        try:
            by = checked_names(row["decided by"] or "")
        except ValueError as exc:
            problems.append(f"line {n}: {exc}")
            continue
        if issue.isdigit():
            todo.append((Decision(int(issue), by, row["decision"], (row["scope"] or "").strip(),
                                  date), lang or None))
    if problems:
        sys.exit("ERROR: nothing was recorded:\n  " + "\n  ".join(problems))
    if not apply:
        for decision, lang in todo:
            print(f"Would add to {where(lang)}: {chr(9).join(decision.row())}")
        print(f"{len(todo)} line(s). Run again with --apply to record them.")
        return
    added = [(d, lang) for d, lang in todo if record(d, lang, commit=False)]
    if any(lang is None for _, lang in added):
        commit_framework_log(f"{sum(lang is None for _, lang in added)} decision(s) from "
                             f"{path.name}")
    print(f"Recorded {len(added)} line(s); {len(todo) - len(added)} were already there.")


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    if args.batch:
        if args.issue or args.by or args.decision or args.lang or args.keep_open:
            sys.exit("ERROR: --batch takes no other flags but --apply: each line says the rest.")
        _batch(args.batch, args.apply)
        return
    if not (args.issue and args.by and args.decision):
        sys.exit("ERROR: give --issue, --by and --decision (or --batch FILE.tsv).")
    if args.lang and not (file_door.CODED_DATA / args.lang).is_dir():
        sys.exit(f"ERROR: no language folder coded_data/{args.lang}.")
    try:
        by = checked_names(args.by)
    except ValueError as exc:
        sys.exit(f"ERROR: {exc}")
    if not args.decision.strip():
        sys.exit("ERROR: --decision is empty.")
    issue = issues.get_github().get_issue(args.issue)
    if issue is None:
        sys.exit(f"ERROR: issue #{args.issue} could not be read on GitHub.")
    decision = Decision(args.issue, by, args.decision, args.scope.strip())
    line = "\t".join(decision.row())
    if not args.apply:
        print(f"Would add to {where(args.lang)}:\n  {line}")
        print(f"and comment it on #{args.issue}"
              + ("" if args.keep_open else ", then close it") + ".")
        print("Run again with --apply to do it.")
        return
    added = record(decision, args.lang)
    print(f"{'Added to' if added else 'Already in'} {where(args.lang)}:\n  {line}")
    scope = f" Scope: {decision.scope}." if decision.scope else ""
    body = (f"Decision recorded in {where(args.lang)} with `record-decision`:\n\n"
            f"> {decision.row()[3]}\n\nDecided by {by}.{scope}")
    if args.keep_open or issue.get("state") != "OPEN":
        issues.comment(args.issue, body)
        print(f"Commented on #{args.issue}.")
    else:
        issues.close(args.issue, body)
        print(f"Commented on and closed #{args.issue}.")


if __name__ == "__main__":
    main()
