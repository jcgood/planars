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

**The stamp** (``stamp``; unit 18, docs/result-stamp-design.md): what every
result records about what it was drawn from, the one place one is built.
The code's version (``code_version``: ``pyproject.toml``'s, raised by the
pre-commit hook for any commit that changes ``RESULT_CODE``), and for the
schemas and each language its version and its log *position*
(``source_log.position``), from which ``rebuild`` writes those files as
they stood (``source_log.files_at``), without git. ``stamp_problems`` says,
in plain words, what would stop a stamped result being rebuilt (code
changed since its version was set, a file edited outside the tooling);
``stamp_text`` is the one line a page prints.

**Releases** (``release_problems``, run by ``integrity-check
--check-release``, the first step of the release procedure in the
coordinator guide): a release is refused while a breaking edit still has
annotation waiting on it, i.e. an issue its ``why`` names is open and
carries a label marked ``for_annotator`` in schemas/issue_labels.yaml.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from . import file_door, source_log
from .change_effects import UNKNOWN, answers_broken

BREAKING, ADDITION, REVISION = "breaking", "addition", "revision"
ISSUE = re.compile(r"#(\d+)")

# The code that produces results: a commit changing any of it raises the
# code version (bump_version_hook.py and check_snapshots.py read this;
# design § 5, Q3), and the contributor charts are redrawn when the chart code
# in it changes (laminar/contributor_charts.py). The documentation kept
# beside that code is not part of it: editing a README or the planarsviz
# guide changes no result, so it raises no version and redraws no chart.
# Every reader asks is_result_code() or result_code_pathspecs(), never the
# folders alone.
RESULT_CODE = ("planars", "laminar", "chapters", "planarsviz")
DOC_SUFFIXES = (".md",)
DOC_FOLDERS = ("planarsviz/docs",)


def is_result_code(path: str) -> bool:
    """Whether this repository path (relative, with ``/``) is code that
    produces results: under a RESULT_CODE folder and not documentation."""
    parts = path.split("/")
    if parts[0] not in RESULT_CODE or len(parts) < 2:
        return False
    if any(path == f or path.startswith(f + "/") for f in DOC_FOLDERS):
        return False
    return not path.endswith(DOC_SUFFIXES)


def result_code_pathspecs() -> List[str]:
    """is_result_code() as git pathspecs, for ``git status``/``git diff``."""
    return [*RESULT_CODE,
            *(f":(exclude,glob)**/*{s}" for s in DOC_SUFFIXES),
            *(f":(exclude){f}" for f in DOC_FOLDERS)]
PYPROJECT = source_log.ROOT / "pyproject.toml"
_VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


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


def edits(stream: str, at: Optional[int] = None) -> Iterator[Edit]:
    """The stream's edits since its last baseline, oldest first; with
    ``at``, as the log stood at that position. Lines with no change class
    (an annotation file's) are not edits to a source."""
    lines = source_log.read_lines(stream)[:at]
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


def counts(stream: str, at: Optional[int] = None) -> Tuple[int, int, int]:
    """(breaking, addition, revision) edits since the baseline (at a position)."""
    found = {BREAKING: 0, ADDITION: 0, REVISION: 0}
    for edit in edits(stream, at):
        found[edit.level] += 1
    return found[BREAKING], found[ADDITION], found[REVISION]


def version(stream: str, at: Optional[int] = None) -> str:
    """``3.12.40``: the stream's version (``schemas`` or a language ID), now
    or when its log had ``at`` lines."""
    return ".".join(str(n) for n in counts(stream, at))


def versions() -> Dict[str, str]:
    """Every stream's version: the schemas, then each language."""
    return {s: version(s) for s in [source_log.SCHEMAS, *file_door.language_ids()]}


# ---------------------------------------------------------------------------
# The stamp (unit 18)
# ---------------------------------------------------------------------------

def code_version() -> str:
    """The code's version, as ``pyproject.toml`` has it now (not the
    installed copy's metadata, which an editable install leaves stale)."""
    m = _VERSION_LINE.search(PYPROJECT.read_text(encoding="utf-8"))
    if m is None:
        raise RuntimeError("pyproject.toml has no 'version = \"…\"' line.")
    return m.group(1)


def code_changed() -> Optional[bool]:
    """Whether the result code has changes not yet committed (so its version
    doesn't name it). None when there's no git checkout to ask (e.g. an
    installed copy, which is its version)."""
    if not (source_log.ROOT / ".git").exists():
        return None
    done = subprocess.run(["git", "-C", str(source_log.ROOT), "status", "--porcelain", "--",
                           *result_code_pathspecs()], capture_output=True, text=True)
    if done.returncode != 0:
        return None
    return any(l.strip() for l in done.stdout.splitlines())


def _stream(stream: str) -> dict:
    return {"version": version(stream), "position": source_log.position(stream),
            "drifted": source_log.drifted(stream)}


def stamp(lang_ids: Iterable[str], *, drawn: bool = True) -> dict:
    """What a result drawn now from these languages records (module
    docstring). Plain JSON, so any result can carry it as it is.
    ``drawn=False`` leaves out the time, for a file rewritten only when what
    it was drawn from changes (a bundle's source record)."""
    out = {
        "code": {"version": code_version(), "uncommitted_changes": code_changed()},
        "schemas": _stream(source_log.SCHEMAS),
        "languages": {lang: _stream(lang) for lang in lang_ids},
    }
    return {"drawn": source_log.now(), **out} if drawn else out


def stamp_problems(s: dict) -> List[str]:
    """Why a result with this stamp could not be rebuilt from it, in plain
    words ([] if it can)."""
    out = []
    if s["code"]["uncommitted_changes"]:
        out.append(f"drawn with code changed since version {s['code']['version']} "
                   f"(uncommitted changes in {', '.join(RESULT_CODE)})")
    for name, stream in [("schemas", s["schemas"]), *s["languages"].items()]:
        if stream["drifted"]:
            out.append(f"{name}: {', '.join(stream['drifted'])} changed outside the tooling "
                       f"(not in its change log)")
    return out


def stamp_text(s: dict) -> str:
    """The stamp in one line, for the foot of a page."""
    from planars.languages import get_display_name
    parts = [f"Drawn {s['drawn'][:10]}"] if "drawn" in s else []
    parts += [f"code {s['code']['version']}",
              f"schemas {s['schemas']['version']} (line {s['schemas']['position']})"]
    parts += [f"{get_display_name(lang)} {st['version']} (line {st['position']})"
              for lang, st in s["languages"].items()]
    text = " · ".join(parts)
    problems = stamp_problems(s)
    return text + (f" — not reproducible: {'; '.join(problems)}" if problems else "")


def rebuild(s: dict, dest: Path) -> None:
    """Write the schemas and languages a stamp names, as they stood, into
    ``dest/schemas/`` and ``dest/coded_data/{lang}/``. The code is the
    stamp's version (from a release or the package index, not from here).
    Raises ``source_log.RebuildError`` if they can't be rebuilt."""
    source_log.files_at(source_log.SCHEMAS, s["schemas"]["position"], dest / "schemas")
    for lang, st in s["languages"].items():
        source_log.files_at(lang, st["position"], dest / "coded_data" / lang)


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
