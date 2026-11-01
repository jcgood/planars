"""Versions, read from the change logs, and the rule they enforce for a
release (Phase 10 unit 17; docs/change-log-design.md § 6-7).

Nothing stores a version: it is counted from the log every time it is asked
for, so it can't be forgotten or bumped wrongly.

**The level of an edit** (``level``), read from its lines, never chosen. An
*edit* is the lines a stream's log got at one moment from one command (the
same ``when`` and ``by``): one hand edit logged by ``log-change``, or one
command's change to a source. It is

- **breaking** if it broke answers or moved spans, or its effects could not
  be measured (``unknown``). A change that moves results without touching
  any answer counts (Jeff, 2026-10-31): a chart or chapter drawn before it
  no longer matches;
- otherwise an **addition** if one of its lines is an ``add``;
- otherwise a **revision** (rename, change, reword, and a remove, split or
  merge that broke nothing).

Counted per edit, not per line, so one edit described as a rename and an
added value moves the version once.

**The version** (``version``): one stream for ``schemas/``, one per
language, written breaking.addition.revision, e.g. ``schemas 3.12.40``: the
count of edits at each level since the stream's last ``baseline`` line
(``migrations/start_source_logs.py``, 2026-10-31). Unit 18 stamps both on
every result.

**Releases** (``release_problems``, run by ``integrity-check
--check-release``, the first step of the release procedure in the
coordinator guide): a release is refused while a breaking edit still has
annotation waiting on it, i.e. an issue its ``why`` names is open and
carries a label marked ``for_annotator`` in schemas/issue_labels.yaml.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from . import file_door, source_log
from .change_effects import UNKNOWN, answers_broken

BREAKING, ADDITION, REVISION = "breaking", "addition", "revision"
ISSUE = re.compile(r"#(\d+)")


@dataclass(frozen=True)
class Edit:
    """One edit's lines in a stream."""
    stream: str
    lines: Tuple[Dict[str, str], ...]

    @property
    def when(self) -> str:
        return self.lines[0]["when (UTC)"]

    @property
    def level(self) -> str:
        return level(self.lines)

    @property
    def issues(self) -> List[int]:
        return sorted({int(n) for line in self.lines for n in ISSUE.findall(line.get("why", ""))})


def _broke(line: Dict[str, str]) -> bool:
    answers = (line.get("answers broken") or "").strip()
    spans = (line.get("spans moved") or "").strip()
    if answers.startswith(UNKNOWN) or spans.startswith(UNKNOWN):
        return True
    n = answers_broken(answers)
    if n is None:
        # Effects are written on every source line; an empty cell is a line
        # whose command stopped before measuring: not known, so breaking.
        return True
    return n > 0 or bool(spans)


def level(lines) -> str:
    """An edit's level, from its lines (see the module docstring)."""
    if any(_broke(l) for l in lines):
        return BREAKING
    if any(l.get("change") == "add" for l in lines):
        return ADDITION
    return REVISION


def edits(stream: str) -> Iterator[Edit]:
    """The stream's edits since its last baseline, oldest first. Lines with
    no change class (an annotation file's) are not edits to a source."""
    lines = source_log.read_lines(stream)
    start = max((i for i, l in enumerate(lines) if l.get("change") == file_door.BASELINE),
                default=-1)
    group: List[Dict[str, str]] = []
    for line in lines[start + 1:]:
        if not line.get("change") or line["change"] == file_door.BASELINE:
            continue
        if group and (line["when (UTC)"], line["by"]) != (group[0]["when (UTC)"], group[0]["by"]):
            yield Edit(stream, tuple(group))
            group = []
        group.append(line)
    if group:
        yield Edit(stream, tuple(group))


def counts(stream: str) -> Tuple[int, int, int]:
    """(breaking, addition, revision) edits since the baseline."""
    found = {BREAKING: 0, ADDITION: 0, REVISION: 0}
    for edit in edits(stream):
        found[edit.level] += 1
    return found[BREAKING], found[ADDITION], found[REVISION]


def version(stream: str) -> str:
    """``3.12.40``: the stream's version (``schemas`` or a language ID)."""
    return ".".join(str(n) for n in counts(stream))


def versions() -> Dict[str, str]:
    """Every stream's version: the schemas, then each language."""
    return {s: version(s) for s in [source_log.SCHEMAS, *file_door.language_ids()]}


def release_problems() -> List[str]:
    """Why a release can't be made now: each breaking edit whose issue is
    open and waiting on an annotator. GitHub must be reachable: an
    unanswered question is not a yes."""
    from . import issues
    if not issues.available():
        raise RuntimeError("GitHub can't be reached, so whether annotation still waits on a "
                           "breaking change can't be checked. Sign in with `gh auth login`.")
    waiting = set(issues.annotator_labels())
    out = []
    for stream in [source_log.SCHEMAS, *file_door.language_ids()]:
        for edit in edits(stream):
            if edit.level != BREAKING:
                continue
            for n in edit.issues:
                issue = issues.get_github().get_issue(n)
                if issue is None:
                    out.append(f"{stream}, {edit.when}: issue #{n} could not be read")
                    continue
                labels = set(issue.get("labels") or []) & waiting
                if issue.get("state") == "OPEN" and labels:
                    out.append(f"{stream}, {edit.when}: a breaking change whose issue #{n} "
                               f"({issue.get('title', '')}) is open under "
                               f"{', '.join(sorted(labels))}")
    return out
