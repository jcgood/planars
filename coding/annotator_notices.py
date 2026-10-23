"""Telling an annotator that values on their ready-for-review tabs need fixing.

Issue #309, step 3. ``validate-coding --notify`` (daily, in
sheet-validation.yml) calls ``notify`` once for each language it checked
completely. The details live in one place, each sheet's Status tab
(``validate_coding.write_problems``); a notice says only how many cells need
fixing in which sheet, with a link.

One ``needs-fixing`` issue per language, titled with the language's name. It
is the coordinator's record and holds, in a hidden marker, a short code for
each problem it has told the annotator about. The annotator is told when a
problem appears that they have not been told about — not every day, and not
when the list only shrinks:

- with a GitHub username in people.yaml (``github:``): the issue mentions
  them (in its first body, or in a comment once it exists), and GitHub
  emails them;
- without one: a comment on each spreadsheet with something new, mentioning
  their email address, and Google emails them. The Drive door lets such a
  comment mention only that sheet's annotator (rule 7).

When nothing needs fixing, the issue is closed. A language with no
annotator named in languages.yaml gets the issue, and the issue says nobody
was told.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence, Set, Tuple

from planars.languages import get_display_name
from planars.schema_values import STATUS_PROBLEMS_COLUMN, STATUS_TAB

from . import issues
from .people import annotator_name, email_for, github_for

LABEL = "needs-fixing"
_MARKER = re.compile(r"<!-- needs-fixing: ([0-9a-f,]*) -->")


@dataclass(frozen=True)
class SheetProblems:
    """The cells that need fixing on one class sheet's ready-for-review tabs."""
    class_name: str
    spreadsheet_id: str
    url: str
    lines: Tuple[str, ...]      # "construction: row N (element), column: 'v' — should be …"


def title_for(lang_id: str) -> str:
    return f"Values to fix in the {get_display_name(lang_id)} sheets"


def _code(sheet: SheetProblems, line: str) -> str:
    return hashlib.sha256(f"{sheet.class_name}\t{line}".encode("utf-8")).hexdigest()[:10]


def codes(sheets: Sequence[SheetProblems]) -> Set[str]:
    return {_code(s, line) for s in sheets for line in s.lines}


def read_codes(body: str) -> Set[str]:
    m = _MARKER.search(body or "")
    return set(filter(None, m.group(1).split(","))) if m else set()


def _count(n: int) -> str:
    return f"{n} cell{'s' if n != 1 else ''}"


def summary(sheets: Sequence[SheetProblems]) -> str:
    """One line per sheet: how many cells, and where to look."""
    return "\n".join(
        f"- **{s.class_name}**: {_count(len(s.lines))} — [open the sheet]({s.url}); "
        f"listed on its {STATUS_TAB} tab"
        for s in sheets)


def body_for(lang_id: str, sheets: Sequence[SheetProblems], told: str) -> str:
    # Short: an annotator reads it, and reading comes out of annotation time
    # (Adam, #318).
    return (
        f"Some values on your ready-for-review tabs aren't allowed:\n\n"
        f"{summary(sheets)}\n\n"
        f"Fix the pink cells. This issue closes by itself when none are left. {told}\n\n"
        f"<!-- needs-fixing: {','.join(sorted(codes(sheets)))} -->\n")


def drive_comment(email: str, sheet: SheetProblems) -> str:
    return (f"+{email} {_count(len(sheet.lines))} "
            f"{'needs' if len(sheet.lines) == 1 else 'need'} fixing: see the {STATUS_TAB} "
            f"tab, column '{STATUS_PROBLEMS_COLUMN}'.")


def notify(lang_id: str, sheets: Sequence[SheetProblems], doorway=None) -> str:
    """File, update or close the language's needs-fixing issue, and tell the
    annotator about anything new. ``sheets``: every class sheet with at least
    one cell to fix; empty means nothing does. Returns what it did."""
    sheets = [s for s in sheets if s.lines]
    title = title_for(lang_id)
    number = issues.find_open(LABEL, title=title)
    if not sheets:
        if number is None:
            return "nothing to fix"
        issues.close(number, "Nothing needs fixing any more — closing.")
        return f"closed #{number}"

    # The body records the codes of today's problems only, so one fixed and
    # later broken again counts as new.
    told_before = read_codes(issues.body_of(number)) if number is not None else set()
    new = [s for s in sheets if {_code(s, l) for l in s.lines} - told_before]
    name = annotator_name(lang_id)
    github = github_for(name) if name else None

    if github:
        told = f"@{github}"
    elif name:
        told = f"({name} is told by a comment on each sheet: no GitHub username in people.yaml.)"
    else:
        told = (f"(Nobody was told: languages.yaml names no annotator for "
                f"{get_display_name(lang_id)}.)")
    body = body_for(lang_id, sheets, told)

    if number is None:
        number = issues.create(LABEL, title, body)
        action = f"filed #{number}"
    else:
        issues.get_github().edit_issue(number, title, body)
        action = f"updated #{number}"
    if not new:
        return f"{action} (nothing new to tell the annotator)"
    if github and action.startswith("updated"):
        issues.comment(number, f"@{github} something new needs fixing:\n\n{summary(new)}")
    elif not github and name:
        email = email_for(name)
        if doorway is None:
            from .drive_doorway import get_doorway
            doorway = get_doorway()
        for s in new:
            doorway.create_comment(s.spreadsheet_id, drive_comment(email, s))
    return f"{action}; told the annotator about {len(new)} sheet(s)"
