"""Telling an annotator that values on their ready-for-review tabs need
fixing, or that a finished tab was marked ready-for-review for them.

Issue #309, step 3. ``validate-coding --notify`` (daily, in
sheet-validation.yml) calls ``notify`` once for each language it checked
completely. The details live in one place, each sheet's Status tab
(``validate_coding.write_problems``); a notice says only how many cells need
fixing in which sheet, and which tabs the check marked ready-for-review
because every cell was answered with no errors
(``validate_coding.looks_finished``), with a link. A marked tab is reported
once, on the day it is marked.

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

When the check marks a tab, the coordinators are told too, by a comment on
the issue mentioning each one with a GitHub username in people.yaml
(``coordinator: true`` or ``owner: true``) other than the annotator.

When nothing needs fixing, the issue is closed. A language with no
annotator named in languages.yaml gets the issue, and the issue says nobody
was told.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

from planars.languages import get_display_name
from planars.schema_values import (
    STATUS_MARKED_BY_COLUMN, STATUS_PROBLEMS_COLUMN, STATUS_READY, STATUS_TAB,
)

from . import issues
from .people import annotator_name, coordinator_githubs, email_for, github_for

LABEL = "needs-fixing"
_MARKER = re.compile(r"<!-- needs-fixing: ([0-9a-f,]*) -->")


@dataclass(frozen=True)
class SheetProblems:
    """One class sheet's cells that need fixing on its ready-for-review tabs,
    and its tabs marked ready-for-review today because they were finished."""
    class_name: str
    spreadsheet_id: str
    url: str
    lines: Tuple[str, ...]      # "construction: row N (element), column: 'v' — should be …"
    finished: Tuple[str, ...] = ()   # construction names


def title_for(lang_id: str) -> str:
    return f"To do in the {get_display_name(lang_id)} sheets"


def _old_title_for(lang_id: str) -> str:
    """The title before finished tabs were reported (2026-10-26), so an issue
    filed under it is found and retitled rather than duplicated."""
    return f"Values to fix in the {get_display_name(lang_id)} sheets"


def _code(sheet: SheetProblems, line: str) -> str:
    return hashlib.sha256(f"{sheet.class_name}\t{line}".encode("utf-8")).hexdigest()[:10]


def _items(sheet: SheetProblems) -> List[str]:
    return list(sheet.lines) + [f"finished: {c}" for c in sheet.finished]


def codes(sheets: Sequence[SheetProblems]) -> Set[str]:
    return {_code(s, item) for s in sheets for item in _items(s)}


def read_codes(body: str) -> Set[str]:
    m = _MARKER.search(body or "")
    return set(filter(None, m.group(1).split(","))) if m else set()


def _count(n: int) -> str:
    return f"{n} cell{'s' if n != 1 else ''}"


def _finished_text(sheet: SheetProblems) -> str:
    tabs = ", ".join(sheet.finished)
    return f"{tabs} finished, so marked {STATUS_READY}"


def summary(sheets: Sequence[SheetProblems]) -> str:
    """One line per sheet: how many cells to fix, which tabs were marked,
    and where to look."""
    out = []
    for s in sheets:
        bits = []
        if s.lines:
            bits.append(f"{_count(len(s.lines))} to fix")
        if s.finished:
            bits.append(_finished_text(s))
        out.append(f"- **{s.class_name}**: {'; '.join(bits)} — [open the sheet]({s.url}); "
                   f"see its {STATUS_TAB} tab")
    return "\n".join(out)


def body_for(lang_id: str, sheets: Sequence[SheetProblems], told: str) -> str:
    # Short: an annotator reads it, and reading comes out of annotation time
    # (Adam, #318).
    return (
        f"{summary(sheets)}\n\n"
        f"Fix the pink cells. A tab with every cell answered and nothing to fix is "
        f"marked {STATUS_READY} for you, and a tab built from it is filled. This issue "
        f"closes by itself when nothing is left. {told}\n\n"
        f"<!-- needs-fixing: {','.join(sorted(codes(sheets)))} -->\n")


def drive_comment(email: str, sheet: SheetProblems) -> str:
    bits = []
    if sheet.lines:
        bits.append(f"{_count(len(sheet.lines))} "
                    f"{'needs' if len(sheet.lines) == 1 else 'need'} fixing")
    if sheet.finished:
        bits.append(_finished_text(sheet))
    return (f"+{email} {'; '.join(bits)}: see the {STATUS_TAB} "
            f"tab, column '{STATUS_PROBLEMS_COLUMN}'.")


def _marked_comment(lang_id: str, sheets: Sequence[SheetProblems], told_before: Set[str],
                    annotator_github: Optional[str]) -> Optional[str]:
    """The comment that tells the coordinators which tabs the check marked
    ready-for-review today, mentioning each (people.coordinator_githubs) but
    the annotator, who is told by the notice itself; None when no tab was
    newly marked or there is nobody to mention. Posted whichever way the
    annotator is told, since an edited issue body notifies nobody."""
    coordinators = [g for g in coordinator_githubs() if g != annotator_github]
    lines = []
    for s in sheets:
        tabs = [c for c in s.finished if _code(s, f"finished: {c}") not in told_before]
        if tabs:
            lines.append(f"- **{s.class_name}**: {', '.join(tabs)} — [open the sheet]({s.url})")
    if not coordinators or not lines:
        return None
    mentions = " ".join(f"@{g}" for g in coordinators)
    return (f"{mentions} the daily check marked these {get_display_name(lang_id)} tabs "
            f"{STATUS_READY} (every cell answered, no errors); the Status tab's "
            f"'{STATUS_MARKED_BY_COLUMN}' column records it:\n\n" + "\n".join(lines))


def notify(lang_id: str, sheets: Sequence[SheetProblems], doorway=None) -> str:
    """File, update or close the language's needs-fixing issue, and tell the
    annotator about anything new. ``sheets``: every class sheet with at least
    one cell to fix or one tab marked today; empty means nothing. Returns what it did."""
    sheets = [s for s in sheets if s.lines or s.finished]
    title = title_for(lang_id)
    number = issues.find_open(LABEL, title=title)
    if number is None:
        number = issues.find_open(LABEL, title=_old_title_for(lang_id))
    if not sheets:
        if number is None:
            return "nothing to fix"
        issues.close(number, "Nothing left to fix or mark — closing.")
        return f"closed #{number}"

    # The body records the codes of today's problems only, so one fixed and
    # later broken again counts as new.
    told_before = read_codes(issues.body_of(number)) if number is not None else set()
    new = [s for s in sheets if {_code(s, i) for i in _items(s)} - told_before]
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
        issues.edit(number, title, body)
        action = f"updated #{number}"
    marked = _marked_comment(lang_id, sheets, told_before, github)
    if marked:
        issues.comment(number, marked)
        action += "; told the coordinators what was marked"
    if not new:
        return f"{action} (nothing new to tell the annotator)"
    if github and action.startswith("updated"):
        issues.comment(number, f"@{github} something new on your sheets:\n\n{summary(new)}")
    elif not github and name:
        email = email_for(name)
        if doorway is None:
            from .drive_doorway import get_doorway
            doorway = get_doorway()
        for s in new:
            doorway.create_comment(s.spreadsheet_id, drive_comment(email, s))
    return f"{action}; told the annotator about {len(new)} sheet(s)"
