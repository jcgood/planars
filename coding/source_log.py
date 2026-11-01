"""Which files are sources, their change logs, and the check that every
change to one is logged (Phase 10 unit 17; docs/change-log-design.md).

A *source* is a file a person edits that defines the framework or a
language: the schemas (``SCHEMA_SOURCES``, here) and each language's planar
and diagnostics file (``file_door.SOURCES``). Every other file in
``schemas/`` is listed in ``NOT_LOGGED`` with the reason; a file in neither
is ``unplaced`` and fails the check until it is put in one.

**The logs.** A *stream* is one log: ``schemas`` (``PROJECT_LOG``,
``schemas/changes.tsv``, in this repository) or a language
(``coded_data/{lang}/changes.tsv``, which also logs its annotation files).
Both have ``file_door.CHANGE_LOG_COLUMNS``. A line about a source names its
change class and layer, its effects (``coding/change_effects.py``) and, on
the last line of an edit, the file's *fingerprint* (``file_door.fingerprint``).

**The rule** (``unlogged``): each source's fingerprint equals the one on its
last logged line. It reads the files and the logs, never git history
(versioning must not depend on git). Run by ``integrity-check
--check-changes``: before a commit (``--staged``, with the staged content),
in CI (``--schemas``) and in the daily refresh (its ``changes`` step, which
files a ``source-unlogged`` issue). Lines are written by ``log-change`` (a
hand edit) and by the local-file door (a command's edit).

``previous_text`` finds the version a source's last line was written for (in
the language's archive, then in git history: a convenience for measuring a
hand edit, not part of the rule).
"""
from __future__ import annotations

import csv
import io
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import file_door

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "schemas"
PROJECT_LOG = SCHEMAS_DIR / "changes.tsv"
SCHEMAS = "schemas"   # the project's stream

# The schema files that are sources, and why (docs/change-log-design.md § 3.1).
SCHEMA_SOURCES: Dict[str, str] = {
    "diagnostic_classes.yaml": "classes, constructions, row shapes, span rules",
    "diagnostic_criteria.yaml": "criteria and their values",
    "planar.yaml": "the planar's columns and conventions, sheet columns",
    "terms.yaml": "the analytical terms",
    "languages.yaml": "language metadata, e.g. examples, which changes the sheets and chapters",
}
# Every other file in schemas/, and why it is not logged.
NOT_LOGGED: Dict[str, str] = {
    "diagnostic_classes_status.yaml": "process state: a promotion is a decision "
                                      "(record-decision), the hash a review stamp",
    "issue_labels.yaml": "tooling, not the framework",
    "decisions.tsv": "its own log",
    "changes.tsv": "this log",
    "__init__.py": "code: says what each schema file owns",
}
# How many commits back previous_text looks in git history.
HISTORY_DEPTH = 300


@dataclass(frozen=True)
class Source:
    """One source: its stream, its name in that stream's log, and its path."""
    stream: str
    name: str
    path: Path

    @property
    def target(self) -> Optional[file_door.LocalFile]:
        """The language file, for the local-file door (None for a schema)."""
        if self.stream == SCHEMAS:
            return None
        for kind in sorted(file_door.SOURCES):
            f = file_door.LocalFile(kind, self.stream)
            if f.relpath == self.name:
                return f
        raise ValueError(f"{self.stream}/{self.name} is not a language source")

    @property
    def shown(self) -> str:
        """How a person reads its name: ``schemas/terms.yaml``,
        ``planars-data stan1293/lang_setup/planar_stan1293.tsv``."""
        return f"schemas/{self.name}" if self.stream == SCHEMAS else \
            f"planars-data {self.stream}/{self.name}"


def schema_source(name: str) -> Source:
    if name not in SCHEMA_SOURCES:
        raise ValueError(f"{name} is not a logged schema file (source_log.SCHEMA_SOURCES)")
    return Source(SCHEMAS, name, SCHEMAS_DIR / name)


def language_sources(lang_id: str) -> List[Source]:
    """The language's sources (those that exist)."""
    out = []
    for kind in sorted(file_door.SOURCES):
        f = file_door.LocalFile(kind, lang_id)
        if f.path.exists():
            out.append(Source(lang_id, f.relpath, f.path))
    return out


def sources(streams: Optional[Iterable[str]] = None) -> List[Source]:
    """Every source in ``streams`` (default: schemas and every language)."""
    wanted = list(streams) if streams is not None else [SCHEMAS, *file_door.language_ids()]
    out: List[Source] = []
    for stream in wanted:
        if stream == SCHEMAS:
            out += [schema_source(n) for n in SCHEMA_SOURCES if (SCHEMAS_DIR / n).exists()]
        else:
            out += language_sources(stream)
    return out


def unplaced() -> List[str]:
    """Files in schemas/ that are in neither SCHEMA_SOURCES nor NOT_LOGGED."""
    if not SCHEMAS_DIR.is_dir():
        return []
    return sorted(p.name for p in SCHEMAS_DIR.iterdir()
                  if p.is_file() and not p.name.startswith(".")
                  and p.name not in SCHEMA_SOURCES and p.name not in NOT_LOGGED)


# ---------------------------------------------------------------------------
# Reading and writing the logs
# ---------------------------------------------------------------------------

def log_path(stream: str) -> Path:
    return PROJECT_LOG if stream == SCHEMAS else file_door.change_log(stream)


def read_rows(text: Optional[str]) -> List[Dict[str, str]]:
    """A log's lines from its text, oldest first."""
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter="\t"))


def read_lines(stream: str) -> List[Dict[str, str]]:
    """The stream's log, oldest first ([] if it has none)."""
    return read_rows(read_text(log_path(stream)))


def _fingerprints(lines: List[Dict[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in lines:
        if line.get("fingerprint"):
            out[line["file"]] = line["fingerprint"]
    return out


def last_fingerprints(stream: str) -> Dict[str, str]:
    """Each file's fingerprint on its last line that has one."""
    return _fingerprints(read_lines(stream))


def append_project_lines(rows: Sequence[Sequence[str]]) -> None:
    """Add lines to ``schemas/changes.tsv`` (made with its header if new).
    Refuses a log whose header is not ``CHANGE_LOG_COLUMNS``."""
    new = not PROJECT_LOG.exists()
    if not new:
        with open(PROJECT_LOG, encoding="utf-8", newline="") as f:
            header = tuple(next(csv.reader(f, delimiter="\t"), []))
        if header != file_door.CHANGE_LOG_COLUMNS:
            raise RuntimeError(f"schemas/changes.tsv has the columns {list(header)}, not "
                               f"{list(file_door.CHANGE_LOG_COLUMNS)}; nothing was logged.")
    with open(PROJECT_LOG, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        if new:
            writer.writerow(file_door.CHANGE_LOG_COLUMNS)
        writer.writerows(rows)


def now() -> str:
    return datetime.now(timezone.utc).strftime(file_door.CHANGE_LOG_TIME_FORMAT)


def line(source: Source, *, what: str, by: str, why: str, change: str, layer: str,
         answers: str = "", spans: str = "", mark: str = "", previous: str = "",
         when: Optional[str] = None) -> List[str]:
    """One log line, in ``CHANGE_LOG_COLUMNS`` order."""
    return [when or now(), source.name, what, by, why, previous, "",
            change, layer, answers, spans, mark]


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Unlogged:
    source: Source
    current: str   # the file's fingerprint now ("" if it is gone)
    logged: str    # on its last line ("" if it has none)


def unlogged(streams: Optional[Iterable[str]] = None, *,
             staged_in: Optional[Path] = None) -> List[Unlogged]:
    """Sources whose fingerprint differs from their last line's. With
    ``staged_in`` (a repository), only the sources staged for its next
    commit are checked, and both they and their logs are read as staged:
    what the commit would hold."""
    staged = staged_paths(staged_in) if staged_in is not None else None
    out: List[Unlogged] = []
    for source in sources(streams):
        if staged is not None:
            if source.path.resolve() not in staged:
                continue
            data = _staged(staged_in, source.path)
            log = _staged(staged_in, log_path(source.stream))
            marks = _fingerprints(read_rows(log.decode("utf-8") if log else None))
        else:
            data, marks = source.path.read_bytes(), last_fingerprints(source.stream)
        current = file_door.fingerprint(data)
        logged = marks.get(source.name, "")
        if current != logged:
            out.append(Unlogged(source, current, logged))
    return out


def staged_paths(repo: Path) -> set:
    """The files staged for ``repo``'s next commit (resolved paths)."""
    names = _git(repo, "diff", "--cached", "--name-only", "--no-renames", "-z").stdout
    return {(repo / n).resolve() for n in names.split("\0") if n}


def _staged(repo: Path, path: Path) -> Optional[bytes]:
    """``path`` as staged in ``repo`` (None if the commit has no such file)."""
    try:
        rel = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return None
    shown = subprocess.run(["git", "-C", str(repo), "show", f":{rel}"], capture_output=True)
    return shown.stdout if shown.returncode == 0 else None


def stage(paths: Sequence[Path]) -> None:
    """``git add`` files in this repository (the schemas and their log),
    so they go into the next commit together. Skipped outside a git
    checkout (tests)."""
    if not (ROOT / ".git").exists():
        return
    rel = [str(Path(p).resolve().relative_to(ROOT)) for p in paths
           if Path(p).resolve().is_relative_to(ROOT)]
    done = _git(ROOT, "add", "--", *rel) if rel else None
    if done is not None and done.returncode != 0:
        print(f"WARNING: could not stage {', '.join(rel)}: {done.stderr.strip()}. "
              f"Stage them by hand: they are committed together.")


def log_tool_edit(source: Source, old: Optional[str], *, by: str, why: str,
                  changes: Sequence[Tuple[str, str]]) -> None:
    """Log a schema file a command just rewrote (lookup-lang's
    languages.yaml): its effects measured, one line per change, the
    fingerprint on the last, the file and log staged together."""
    from .change_effects import measure
    problems = file_door.check_changes(changes)
    if problems:
        raise ValueError("; ".join(problems))
    new = read_text(source.path)
    effects = measure({source.path: old})
    rows = [line(source, what=describe(source, old, new), by=by, why=why, change=c, layer=l,
                 answers=effects.answers_cell(), spans=effects.spans_cell(),
                 mark=file_door.fingerprint(new) if i == len(changes) - 1 else "")
            for i, (c, l) in enumerate(changes)]
    append_project_lines(rows)
    stage([source.path, PROJECT_LOG])


def command_for(stream: str) -> str:
    """The log-change command that logs a stream's edits (a dry run)."""
    lang = "" if stream == SCHEMAS else f" --lang {stream}"
    return (f'python -m coding log-change{lang} --change CLASS --layer LAYER '
            f'--why "#N: what and why"')


# ---------------------------------------------------------------------------
# The version a line was written for
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _repo_of(path: Path) -> Optional[Path]:
    done = _git(path.parent, "rev-parse", "--show-toplevel") if path.parent.exists() else None
    return Path(done.stdout.strip()) if done is not None and done.returncode == 0 else None


def previous_text(source: Source) -> Tuple[bool, Optional[str]]:
    """``(found, text)``: the content whose fingerprint is on the source's
    last line (``(True, None)`` when it has no line: the file is new).
    Looked for in the language's archive, then in git history."""
    mark = last_fingerprints(source.stream).get(source.name, "")
    if not mark:
        return True, None
    if source.stream != SCHEMAS:
        target = source.target
        folder = file_door.CODED_DATA / source.stream / file_door.ARCHIVE_FOLDER / target.folder
        for copy in sorted(folder.glob(f"{source.path.stem}_*{source.path.suffix}"), reverse=True):
            data = copy.read_bytes()
            if file_door.fingerprint(data) == mark:
                return True, data.decode("utf-8")
    repo = _repo_of(source.path)
    if repo is None:
        return False, None
    rel = str(source.path.resolve().relative_to(repo.resolve()))
    candidates = [f":{rel}"]
    commits = _git(repo, "log", f"-{HISTORY_DEPTH}", "--format=%H", "--", rel).stdout.split()
    candidates += [f"{c}:{rel}" for c in commits]
    for spec in candidates:
        shown = subprocess.run(["git", "-C", str(repo), "show", spec], capture_output=True)
        if shown.returncode == 0 and file_door.fingerprint(shown.stdout) == mark:
            return True, shown.stdout.decode("utf-8")
    return False, None


def describe(source: Source, old: Optional[str], new: Optional[str]) -> str:
    """The change in a few words: the door's description for a language
    source, lines changed for a schema."""
    if new is None:
        return "removed"
    if source.stream != SCHEMAS:
        return file_door._describe(source.target, old, new)
    if old is None:
        return "created"
    import difflib
    diff = [l for l in difflib.ndiff(old.splitlines(), new.splitlines()) if l.startswith(("+ ", "- "))]
    return f"{len(diff)} line(s) changed"


def read_text(path: Path) -> Optional[str]:
    """The file's text exactly as stored, or None."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()
