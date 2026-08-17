#!/usr/bin/env python3
"""Turn `validate-coding` output into a GitHub issue a person can act on.

    python -m coding validation-report /tmp/report.txt --out /tmp/issue_body.md

Used by `.github/workflows/sheet-validation.yml`. Pure parsing and formatting;
the `gh` calls stay in the workflow, mirroring `notify.py`'s split so the
judgment-carrying part is testable.

Why this exists
---------------
The workflow used to build the issue body with an inline shell heredoc, and
filed *one issue per label*: if an open `sheet-validation` issue existed, every
later failure was appended to it as a comment. Issue #260 accumulated three
unrelated problems that way over three days — a crash, a set of naming
warnings, and a missing analysis module — under a title naming only the first,
which had been fixed two days earlier. The current problem was buried in the
newest comment of an issue about something else. Three changes follow from
that, and this module implements the parts that are not shell:

1. **Advisory warnings do not open or hold open an issue.** A warning that
   duplicates a known, tracked gap (`phrasal_accent` has no analysis module —
   that is issue #237, deliberate and planned) would otherwise keep the issue
   open forever, since it recurs every single day. Warnings still appear, in
   the job summary and in the body of an issue filed for other reasons; they
   just do not by themselves constitute a failure to report. Errors and
   crashes do.

2. **A changed problem gets a new issue, not a comment on the old one.** Each
   report carries a fingerprint of *what is wrong*, ignoring counts, row
   numbers, and quoted values. Same fingerprint means the same problem
   recurring, and a comment is right. A different fingerprint means the old
   issue is about something else, and the workflow closes it as superseded and
   opens a new one.

3. **The exception line is actually the exception.** The old extractor walked
   backwards from the end of the log for the first line that was not
   "Connecting"/"Warning", but the traceback lands at the *top* of the captured
   output while normal stdout continues below it. So it reported the last line
   of ordinary output as the crash — which is why #260's body says "crashed
   with an unhandled exception" and then shows a routine blank-cell count.

One more thing this fixes in passing: 429 near-identical warning lines is not a
report anyone reads. Repeated messages are collapsed with a count.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_LANG_RE = re.compile(r"^[a-z]+\d{4}$")
_PLANAR_RE = re.compile(r"^\s{2}Planar validation \(\d+ issue")
_DIAGNOSTICS_RE = re.compile(r"^\s{2}Diagnostics validation \(\d+ issue")
_SECTION_RE = re.compile(r"^\s{2}\[(\S+/\S+)\] \d+ issue")
_DETAIL_RE = re.compile(r"^\s{4}\[(ERROR|WARNING)\] (.+)$")
_TRACEBACK_MARKER = "Traceback (most recent call last):"

# Anything that varies run to run without changing what is wrong: row numbers,
# counts, and the specific value or column being complained about.
_DIGITS_RE = re.compile(r"\d+")
_QUOTED_RE = re.compile(r"'[^']*'")
_BRACKETED_RE = re.compile(r"\[[^\]]*\]")


@dataclass
class ReportIssue:
    severity: str          # "error" | "warning"
    lang: str
    section: str           # "planar", "diagnostics", or "class/construction"
    message: str

    def normalised(self) -> str:
        """The issue's shape, with run-to-run detail removed, for fingerprinting."""
        text = _QUOTED_RE.sub("'*'", self.message)
        text = _BRACKETED_RE.sub("[*]", text)
        return _DIGITS_RE.sub("N", text)


@dataclass
class ValidationReport:
    issues: List[ReportIssue] = field(default_factory=list)
    crash: Optional[str] = None
    raw: str = ""

    @property
    def errors(self) -> List[ReportIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ReportIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def should_file(self) -> bool:
        """Whether this report warrants an open issue.

        Errors and crashes do. Warnings alone do not — see this module's
        docstring; a recurring advisory warning is what kept #260 open for
        three days after the problem it was named for had been fixed.
        """
        return bool(self.crash) or bool(self.errors)

    def fingerprint(self) -> str:
        """Stable hash of *what is wrong*, ignoring how many times and where.

        Two runs reporting the same kinds of problem in the same places share a
        fingerprint even if the counts and row numbers differ. A run reporting
        something else does not.
        """
        if self.crash:
            # A crash is identified by its exception type and message shape,
            # not by the file and line, which move with any edit.
            parts = ["crash:" + _DIGITS_RE.sub("N", _QUOTED_RE.sub("'*'", self.crash))]
        else:
            parts = sorted({
                f"{i.severity}:{i.lang}:{i.section}:{i.normalised()}"
                for i in self.issues
                if i.severity == "error"
            })
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def parse_report(text: str) -> ValidationReport:
    """Parse `validate-coding` stdout+stderr into structured issues."""
    lines = text.splitlines()
    report = ValidationReport(raw=text)

    if _TRACEBACK_MARKER in text:
        report.crash = _extract_exception(lines)

    lang: Optional[str] = None
    section: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if _LANG_RE.match(stripped) and line == stripped:
            lang, section = stripped, None
        elif _PLANAR_RE.match(line):
            section = "planar"
        elif _DIAGNOSTICS_RE.match(line):
            section = "diagnostics"
        elif m := _SECTION_RE.match(line):
            section = m.group(1)
        elif m := _DETAIL_RE.match(line):
            if lang and section:
                report.issues.append(ReportIssue(
                    severity=m.group(1).lower(), lang=lang,
                    section=section, message=m.group(2).strip()))
    return report


def _extract_exception(lines: List[str]) -> str:
    """Return the exception line of the last traceback in the log.

    A traceback's frames are indented; the exception line that terminates it is
    not. Scanning forward from the last traceback marker for the first
    unindented, non-empty line finds it, and does not confuse it with ordinary
    stdout printed afterwards — which is precisely what the previous
    "walk backwards from the end" approach got wrong.
    """
    last = max(i for i, l in enumerate(lines) if _TRACEBACK_MARKER in l)
    for line in lines[last + 1:]:
        if line and not line[0].isspace():
            return line.strip()
    return "(exception line not found in traceback)"


def _collapse(issues: List[ReportIssue]) -> List[Tuple[int, ReportIssue]]:
    """Group identical-shaped issues, most frequent first, keeping one example.

    429 near-identical lines is not a report anyone reads.
    """
    groups: Dict[Tuple[str, str, str], List[ReportIssue]] = {}
    for issue in issues:
        groups.setdefault((issue.lang, issue.section, issue.normalised()),
                          []).append(issue)
    return sorted(((len(v), v[0]) for v in groups.values()),
                  key=lambda pair: (-pair[0], pair[1].lang, pair[1].section))


def _format_group(count: int, issue: ReportIssue) -> str:
    prefix = f"**{issue.lang}** / `{issue.section}`"
    message = issue.message
    # validate-coding prefixes many messages with the construction name, which
    # the section already gives — "phrasal_accent/general: general: ..." reads
    # as a typo rather than as structure.
    construction = issue.section.split("/")[-1]
    for redundant in (f"{construction}: ", f"{construction} "):
        if message.startswith(redundant):
            message = message[len(redundant):]
            break
    if count == 1:
        return f"- {prefix}: {message}"
    return f"- {prefix}: {message}\n  _(and {count - 1} more like it)_"


def issue_title(report: ValidationReport, date: str) -> str:
    """A title naming the problem, so a stale issue is obvious at a glance."""
    if report.crash:
        return f"Sheet validation crashed — {date}"
    n = len(report.errors)
    where = sorted({f"{i.lang} {i.section}" for i in report.errors})
    scope = where[0] if len(where) == 1 else f"{len(where)} sheets"
    return f"Sheet validation: {n} error{'s' if n != 1 else ''} in {scope} — {date}"


def build_issue_body(report: ValidationReport, date: str) -> str:
    """Render the issue body, fingerprint marker included."""
    out: List[str] = []

    if report.crash:
        out.append("## What's wrong\n")
        out.append("The validation script crashed with an unhandled exception — "
                   "this is an infrastructure error, not a data coding problem.\n")
        out.append(f"```\n{report.crash}\n```\n")
        out.append("_No annotation data needs to be corrected._\n")
        out.append("\n## What to do\n")
        out.append("If this is a transient API error it will clear on the next "
                   "scheduled run, and the issue closes automatically. If it "
                   "repeats, the traceback below is the place to start.\n")
    else:
        out.append("## What's wrong\n")
        for count, issue in _collapse(report.errors):
            out.append(_format_group(count, issue))
        out.append("\n## What to do\n")
        out.extend(_what_to_do(report))

    warnings = report.warnings
    if warnings:
        out.append(f"\n## Advisory warnings ({len(warnings)}) — not blocking\n")
        out.append("These do not open or hold open this issue. Several are "
                   "expected and tracked elsewhere.\n")
        for count, issue in _collapse(warnings)[:15]:
            out.append(_format_group(count, issue))
        distinct = len(_collapse(warnings))
        if distinct > 15:
            out.append(f"\n_({distinct - 15} more distinct warning kinds — see the full log.)_")

    out.append("\n## Full log\n")
    out.append("<details><summary>Show full validation output</summary>\n")
    out.append(f"```\n{report.raw}\n```\n")
    out.append("</details>\n")
    out.append(f"\n<!-- validation-fingerprint: {report.fingerprint()} -->")
    return "\n".join(out) + "\n"


def _what_to_do(report: ValidationReport) -> List[str]:
    messages = [i.message for i in report.errors]
    steps: List[str] = []
    if any("header differs" in m for m in messages):
        steps.append(
            "**Column structure mismatch:** a sheet has columns that differ from "
            "the local TSV. Open it, compare its header row to the TSV header "
            "above, and fix the column structure in the Sheet.\n")
    if any("missing structural column" in m for m in messages):
        steps.append(
            "**Wrong row structure:** the sheet's rows do not match the shape "
            "`diagnostic_classes.yaml` declares for that construction (`row_type`). "
            "Either the sheet needs regenerating for that construction, or the "
            "schema's `row_type` is wrong. Do not fix this by editing cells.\n")
    if any("unexpected value" in m for m in messages):
        steps.append(
            "**Invalid cell values:** open the affected sheet, find the pink "
            "cells, and correct them to one of the allowed options listed above.\n")
    if not steps:
        steps.append("Review the errors above against the full log.\n")
    steps.append("This issue closes automatically when the next validation run "
                 "reports no errors.")
    return steps


def read_fingerprint(body: str) -> Optional[str]:
    """Recover the fingerprint from an existing issue body, if it has one."""
    m = re.search(r"<!-- validation-fingerprint: ([0-9a-f]+) -->", body or "")
    return m.group(1) if m else None


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding validation-report`."""
    ap = argparse.ArgumentParser(
        description="Turn validate-coding output into a GitHub issue body."
    )
    ap.add_argument("report", metavar="REPORT.txt", type=Path,
                     help="path to the raw validate-coding output")
    ap.add_argument("--out", metavar="BODY.md", type=Path,
                     help="write the generated issue body here")
    ap.add_argument("--previous-body", metavar="PREV.md", type=Path,
                     help="path to the previous issue body, to compare fingerprints")
    ap.add_argument("--date", default="",
                     help="date to stamp into the issue title/body (YYYY-MM-DD)")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()

    report_path = args.report
    out_path = args.out
    prev_path = args.previous_body
    date = args.date

    report = parse_report(report_path.read_text(encoding="utf-8"))
    body = build_issue_body(report, date)
    if out_path:
        out_path.write_text(body, encoding="utf-8")

    previous = read_fingerprint(prev_path.read_text(encoding="utf-8")) if (
        prev_path and prev_path.exists()) else None

    # Machine-readable, for the workflow to branch on. Printed as key=value so
    # it can be appended straight to $GITHUB_OUTPUT.
    print(f"should_file={'true' if report.should_file() else 'false'}")
    print(f"fingerprint={report.fingerprint()}")
    print(f"same_problem={'true' if previous == report.fingerprint() else 'false'}")
    print(f"errors={len(report.errors)}")
    print(f"warnings={len(report.warnings)}")
    print(f"crashed={'true' if report.crash else 'false'}")
    print(f"title={issue_title(report, date)}")


if __name__ == "__main__":
    main()
