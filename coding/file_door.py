"""The local-file door: every write to a language's files is checked, the
previous version kept, and the change logged.

Phase 10 unit 6a (issue #271); design: docs/ownership-design.md § 4-5. The
twin of the Drive door (coding/drive_door.py), for the files in planars-data
(``coded_data/``). Commands name a file by what it is, never by its path:
``write(annotation(lang, class, construction), text, why=...)``. The door
builds the path, from one function per kind (``KINDS``); a kind not in the
table can't be named.

**What it does for every write, so no command has to remember:**

- writes only if the content differs (``write`` returns False otherwise);
- copies the previous version first to
  ``{lang}/archive/{folder}/{name}_{stamp}{ext}`` (``folder`` is the class,
  or ``lang_setup``; ``stamp`` is UTC, ``ARCHIVE_STAMP_FORMAT``, the one
  archive date format), never over an earlier copy;
- appends one line to the language's change log, ``{lang}/changes.tsv``
  (``CHANGE_LOG_COLUMNS``): when, which file, what changed (worked out by the
  door), which command, why (the caller's reason) and where the previous
  version went;
- when the command ends, however it ends, commits and pushes exactly the
  files it wrote (with their archive copies and change-log lines), with a
  message made from the change-log lines. Nothing else in planars-data is
  staged. Skipped when ``coded_data/`` is not a git repository (tests). This
  is the only place the tooling commits to planars-data (the daily
  refresh's own commit steps went in unit 6b).

**Checks, before anything is written** (a write that breaks one is refused:
``DoorViolation``, and nothing is written):

1. a command is running (``drive_door.running`` tells both doors), and its
   ``operations.yaml`` record says this invocation writes local files
   (``writes_locally``, gated like ``writes_to_drive``): a dry run writes
   nothing;
2. a source (``SOURCES``: the planar, the diagnostics YAML) is written only
   by a command whose record lists it under ``edits_sources``, or by code
   with no record (a migration, which passes ``may_write`` to ``running``);
3. an annotation TSV has the columns its tab should have
   (``sheet_spec.construction_columns``; parked ``_split_``/``_merged_``
   columns allowed). Only mismatches the previous version did not already
   have are reported: older drift has its own issues (the Drive door's
   rule 6 works the same way). A class or construction the diagnostics file
   doesn't list is not checked here (that is the ``stale-manifest`` issue);
4. an annotation TSV loses no answered row (a row with any criterion,
   Source or Comments cell filled, matched by the schema's row key) unless
   the caller says why with ``drops=`` (the Drive door's ``replacing``).
   ``remove`` drops a whole file on purpose: it needs only its reason.

**The tooling's own files** (unit 6b; ``STATE_KINDS``): the state files in
``.state/`` (pending changes, the provenance log, regen snapshots, the
restructure journal, check-notes' notes state) and the ID file,
``drive_config.json``. Where each lives is ``coding/state_files.py``'s. They
are written with ``write_state``, ``append_state`` (the provenance log) and
``remove_state``, which check rule 1 (a dry run writes none, except the
Drive door's own records, ``DRIVE_RECORDS``, which log the Drive writes it
let through), write only what differs and commit with the rest. They are
not research data, so they get no archive copy or change-log line: git
keeps their history.

**Enforced** (unit 6c, 2026-10-22): the door watched live writes first
(design § 4.1, the Drive door's § 4 rule), letting a broken rule through and
filing a ``door-violation`` issue, until its first real data-file write went
through cleanly (the 2026-10-22 refresh); every kind is now refused in live
runs as in tests. ``tests/test_file_door_coverage.py`` fails if code under
``coding/`` writes a file any other way, apart from the listed writes outside
planars-data.

**Overwrites** (design § 5.3): a change-log line written inside the daily
refresh says so in its ``by`` column (``import-sheets (daily refresh)``), so
``overwrites(since)`` can answer from the log alone whether the refresh
replaced a file whose last change was made by someone running a different
command (a migration, restructure-sheets): the daily refresh's
``data-overwrite`` issue. A hand edit leaves no line, so it is not seen
until unit 17 requires one.

Not here: test data under ``.test_fixtures/`` (``capture-drive-state`` is
its one writer) and hand edits (unit 17).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import io
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple, Union

from . import state_files

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

# The command whose runs hold the others in the daily refresh, and how a
# change-log line written inside one says so.
REFRESH_COMMAND = "daily-refresh"
IN_REFRESH = " (daily refresh)"

# The datestamp in an archived file's name (planar_stan1293_20260209_101500.tsv),
# always UTC. One statement for every archive (hidden-facts M-misc).
ARCHIVE_STAMP_FORMAT = "%Y%m%d_%H%M%S"

# ---------------------------------------------------------------------------
# Kinds: what a file is, and where it lives
# ---------------------------------------------------------------------------

ANNOTATION = "annotation"
PLANAR = "planar"
DIAGNOSTICS_YAML = "diagnostics_yaml"
DIAGNOSTICS_TSV = "diagnostics_tsv"
PROPOSAL_BASE = "proposal_base"

# Every kind a command can write, the parts that name one, and its file name
# within its folder. The folder is the class for an annotation TSV and
# ``lang_setup`` for the rest. Archive copies and the change log are written
# by the door itself and are not kinds a command names.
KINDS: Dict[str, Dict[str, object]] = {
    ANNOTATION:       {"parts": ("class_name", "construction"),
                       "name": lambda f: f"{f.construction}.tsv",
                       "what": "a construction's annotations, imported from its sheet"},
    PLANAR:           {"parts": (), "name": lambda f: f"planar_{f.lang_id}.tsv",
                       "what": "the planar file"},
    DIAGNOSTICS_YAML: {"parts": (), "name": lambda f: f"diagnostics_{f.lang_id}.yaml",
                       "what": "the diagnostics file"},
    # Built from the YAML; deleted in unit 11b (ownership-design Q5).
    DIAGNOSTICS_TSV:  {"parts": (), "name": lambda f: f"diagnostics_{f.lang_id}.tsv",
                       "what": "the diagnostics TSV (a copy of the diagnostics file)"},
    # What the proposal sheet was last filled with (unit 11a; ownership-design
    # § 3.4): an annotator's proposal is the sheet's difference from it.
    PROPOSAL_BASE:    {"parts": (), "name": lambda f: f"proposal_base_{f.lang_id}.json",
                       "what": "what the proposal sheet was last filled with"},
}
# The files a person edits; every other kind is built from something else.
SOURCES: FrozenSet[str] = frozenset({PLANAR, DIAGNOSTICS_YAML})
# Built from another file in planars-data, so rebuilding one loses nothing:
# not an overwrite (``overwrites``).
BUILT: FrozenSet[str] = frozenset({DIAGNOSTICS_TSV, PROPOSAL_BASE})
SETUP_FOLDER = "lang_setup"
ARCHIVE_FOLDER = "archive"
CHANGE_LOG_NAME = "changes.tsv"
CHANGE_LOG_COLUMNS = ("when (UTC)", "file", "what changed", "by", "why", "previous version")
# Sorts as text in time order, which overwrites() relies on.
CHANGE_LOG_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class LocalFile:
    """One file in a language's folder, named by what it is."""
    kind: str
    lang_id: str
    class_name: Optional[str] = None
    construction: Optional[str] = None

    def __post_init__(self) -> None:
        rule = KINDS.get(self.kind)
        if rule is None:
            raise ValueError(f"unknown kind of local file {self.kind!r}; known: {sorted(KINDS)}")
        if not self.lang_id:
            raise ValueError(f"a {self.kind} file needs a language")
        for part in ("class_name", "construction"):
            needed = part in rule["parts"]
            if bool(getattr(self, part)) != needed:
                raise ValueError(f"a {self.kind} file {'needs' if needed else 'has no'} {part}")

    @property
    def folder(self) -> str:
        return self.class_name if self.kind == ANNOTATION else SETUP_FOLDER

    @property
    def name(self) -> str:
        return KINDS[self.kind]["name"](self)

    @property
    def relpath(self) -> str:
        """Within the language's folder: ``metrical/stress_domain.tsv``."""
        return f"{self.folder}/{self.name}"

    @property
    def path(self) -> Path:
        return CODED_DATA / self.lang_id / self.folder / self.name


def annotation(lang_id: str, class_name: str, construction: str) -> LocalFile:
    return LocalFile(ANNOTATION, lang_id, class_name, construction)


def planar(lang_id: str) -> LocalFile:
    return LocalFile(PLANAR, lang_id)


def diagnostics_yaml(lang_id: str) -> LocalFile:
    return LocalFile(DIAGNOSTICS_YAML, lang_id)


def diagnostics_tsv(lang_id: str) -> LocalFile:
    return LocalFile(DIAGNOSTICS_TSV, lang_id)


def proposal_base(lang_id: str) -> LocalFile:
    return LocalFile(PROPOSAL_BASE, lang_id)


def class_folder(lang_id: str, class_name: str) -> Path:
    return CODED_DATA / lang_id / class_name


def annotation_files(lang_id: str, class_name: str) -> List[LocalFile]:
    """The class's annotation TSVs on disk, in name order."""
    folder = class_folder(lang_id, class_name)
    if not folder.is_dir():
        return []
    return [annotation(lang_id, class_name, p.stem) for p in sorted(folder.glob("*.tsv"))]


def change_log(lang_id: str) -> Path:
    return CODED_DATA / lang_id / CHANGE_LOG_NAME


# ---------------------------------------------------------------------------
# The tooling's own files (unit 6b): state files and the ID file
# ---------------------------------------------------------------------------

PENDING_CHANGES = "pending_changes"
PROVENANCE_LOG = "provenance_log"
REGEN_SNAPSHOT = "regen_snapshot"
RESTRUCTURE_JOURNAL = "restructure_journal"
NOTES_STATE = "notes_state"
COMMENTS_STATE = "comments_state"
RENUMBERING = "renumbering"
ID_FILE = "id_file"

# Where each lives is coding/state_files.py's (read at call time: tests move
# them). A regen snapshot is one file per tab, named by ``name``.
STATE_KINDS: Dict[str, Dict[str, object]] = {
    PENDING_CHANGES:     {"path": lambda f: state_files.PENDING_PATH,
                          "what": "destructive changes waiting for apply-pending"},
    PROVENANCE_LOG:      {"path": lambda f: state_files.PROVENANCE_LOG,
                          "what": "the log of what each command wrote to Drive"},
    REGEN_SNAPSHOT:      {"path": lambda f: state_files.SNAPSHOT_DIR / f"{f.name}.json",
                          "what": "a tab as it was before its answers were replaced"},
    RESTRUCTURE_JOURNAL: {"path": lambda f: state_files.JOURNAL_PATH,
                          "what": "restructure-sheets' record of an interrupted run"},
    NOTES_STATE:         {"path": lambda f: state_files.NOTES_STATE_PATH,
                          "what": "what check-notes last saw in each notes Doc"},
    COMMENTS_STATE:      {"path": lambda f: state_files.COMMENTS_STATE_PATH,
                          "what": "what check-comments last saw in each Comments cell"},
    RENUMBERING:         {"path": lambda f: state_files.RENUMBERING_PATH,
                          "what": "import-planar's record of class sheets renumbered "
                                  "ahead of a new planar"},
    ID_FILE:            {"path": lambda f: state_files.ID_FILE,
                          "what": "the Drive IDs of the files the tooling made"},
}
# The Drive door's records of writes it let through. They are written
# whenever a command is running, a dry run included: a dry run's one Drive
# write (import-sheets' highlighting, ``always_on_writes``) is still logged.
DRIVE_RECORDS: FrozenSet[str] = frozenset({PROVENANCE_LOG, REGEN_SNAPSHOT})


@dataclass(frozen=True)
class StateFile:
    """One of the tooling's own files, named by what it is. Not a language's
    research data, so the door keeps no archive copy or change-log line for
    it (git keeps its history); it checks, writes only what differs, and
    commits."""
    kind: str
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in STATE_KINDS:
            raise ValueError(f"unknown kind of state file {self.kind!r}; "
                             f"known: {sorted(STATE_KINDS)}")
        needed = self.kind == REGEN_SNAPSHOT
        if bool(self.name) != needed:
            raise ValueError(f"a {self.kind} file {'needs' if needed else 'has no'} name")

    @property
    def path(self) -> Path:
        return STATE_KINDS[self.kind]["path"](self)

    @property
    def relpath(self) -> str:
        """Within planars-data: ``.state/pending_changes.json``."""
        try:
            return str(self.path.relative_to(state_files.CODED_DATA))
        except ValueError:
            return self.path.name


def pending_changes() -> StateFile:
    return StateFile(PENDING_CHANGES)


def provenance_log() -> StateFile:
    return StateFile(PROVENANCE_LOG)


def regen_snapshot(name: str) -> StateFile:
    return StateFile(REGEN_SNAPSHOT, name)


def restructure_journal() -> StateFile:
    return StateFile(RESTRUCTURE_JOURNAL)


def notes_state() -> StateFile:
    return StateFile(NOTES_STATE)


def comments_state() -> StateFile:
    return StateFile(COMMENTS_STATE)


def renumbering() -> StateFile:
    return StateFile(RENUMBERING)


def id_file() -> StateFile:
    return StateFile(ID_FILE)


def stamp() -> str:
    """Now, in the archive date format (UTC)."""
    return datetime.now(timezone.utc).strftime(ARCHIVE_STAMP_FORMAT)


# ---------------------------------------------------------------------------
# Text: the door writes exactly what it is given
# ---------------------------------------------------------------------------

def tsv_text(header: Sequence[str], records: Sequence[Dict]) -> str:
    """An annotation TSV as import-sheets writes it (csv module, minimal
    quoting); keys not in ``header`` are ignored. LF line ends, as every
    other writer of these files uses (``frame_text``): until 2026-10-22 this
    wrote CRLF, so a file alternated between the two with whichever command
    wrote it last and its history showed every line changed. A file still
    in CRLF takes LF at its next change of content."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(header), delimiter="\t",
                            extrasaction="ignore", quoting=csv.QUOTE_MINIMAL,
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue()


def frame_text(df) -> str:
    """A table as pandas writes it (``to_csv``, tab-separated, LF line ends)."""
    return df.to_csv(sep="\t", index=False)


def read(target: LocalFile) -> Optional[str]:
    """The file's text exactly as stored (line ends kept), or None."""
    return _read(target.path)


def _read(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _rows(text: Optional[str]) -> List[List[str]]:
    if not text:
        return []
    return [r for r in csv.reader(io.StringIO(text, newline=""), delimiter="\t")]


# ---------------------------------------------------------------------------
# The running command
# ---------------------------------------------------------------------------

class DoorViolation(RuntimeError):
    """A local write broke one of the door's rules (enforce mode)."""


@dataclass
class _Run:
    command: str
    may_write: bool
    sources: FrozenSet[str]
    may_write_drive: bool = False
    written: List[Path] = field(default_factory=list)   # to commit, in order
    lines: List[str] = field(default_factory=list)      # for the commit message
    state: Dict[str, str] = field(default_factory=dict)  # state file -> what was done
    specs: Dict[Tuple[str, str, str], object] = field(default_factory=dict)


# A stack: daily-refresh runs commands inside its own run.
_runs: List[_Run] = []


def _declared(op_id: str, args: argparse.Namespace) -> Tuple[Optional[dict], bool, FrozenSet[str]]:
    """The command's record, whether this invocation writes local files, and
    which sources it may edit (union over the active parts of its record)."""
    from .gating import active_parts
    from .registry import _load_operations
    record = _load_operations().get(op_id)
    if record is None:
        return None, False, frozenset()
    named = {s for part in [record, *record.get("modes", [])]
             for s in part.get("edits_sources", [])}
    if named - SOURCES:
        raise ValueError(f"operations.yaml record {op_id!r}: edits_sources names "
                         f"{sorted(named - SOURCES)}, which are not sources "
                         f"(file_door.SOURCES: {sorted(SOURCES)})")
    parts = active_parts(record, args)
    return (record, any(p["writes_locally"] for p in parts),
            frozenset(s for p in parts for s in p.get("edits_sources", [])))


def begin(command: str, args: Optional[argparse.Namespace] = None, *,
          may_write: Optional[bool] = None) -> None:
    """Start a command's run (called by ``drive_door.running``). With
    ``may_write`` (code with no operations.yaml record: a migration) the
    answer is given, and every source may be written."""
    args = args if args is not None else argparse.Namespace()
    op_id = command.replace("-", "_")
    record, writes, sources = _declared(op_id, args)
    if may_write is not None:
        writes, sources = may_write, (sources if record is not None else SOURCES)
        drive = may_write
    elif record is None:
        raise ValueError(f"{command!r} has no operations.yaml record; "
                         "pass may_write to say whether it writes")
    else:
        from .provenance import writes_to_drive
        drive = writes_to_drive(op_id, args)
    _runs.append(_Run(command, writes, sources, may_write_drive=drive))


def finish(succeeded: bool) -> None:
    """End the current run: commit and push what it wrote. After a failed
    command a commit failure is printed rather than raised, so it can't hide
    the command's own error."""
    run = _runs.pop()
    if run.lines:
        print(f"Local-file door: changed {len(run.lines)} file(s), previous versions "
              f"archived and logged.")
    if run.written:
        try:
            _commit(run)
        except RuntimeError as exc:
            if succeeded:
                raise
            print(f"ERROR: {exc}")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write(target: LocalFile, text: str, *, why: str, drops: Optional[str] = None,
          what: Optional[str] = None) -> bool:
    """Write ``text`` to ``target`` if it differs from what is there. True if
    written. ``why`` goes in the change log; ``what`` replaces the door's own
    description of the change.

    ``drops`` says why answered rows may go (rule 4): for a command that
    matches rows its own way and accounts for them itself (restructure-sheets
    carries answers over by element and position name, so after a
    renumbering no row keeps its old key). The change log then notes that
    answered rows were not matched, and why."""
    if not why.strip():
        raise ValueError("write() needs a reason (why=)")
    path = target.path
    old = _read(path)
    if old == text:
        return False
    run = _runs[-1] if _runs else None
    problems = _permission_problems(run, target, "write")
    lost: List[str] = []
    if target.kind == ANNOTATION:
        problems += _column_problems(run, target, old, text)
        lost = _loss_problems(target, old, text)
        if drops is None:
            problems += lost
    _act(run, target, problems)
    previous = _archive(path, target) if old is not None else None
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    description = what or _describe(target, old, text)
    if lost and drops:
        description += f"; answered rows not matched in the new version ({drops})"
    _log(run, target, description, why, previous, path)
    return True


def remove(target: LocalFile, *, why: str) -> bool:
    """Delete ``target``, keeping its last version in the archive. Its folder
    goes too once empty. True if there was a file to remove."""
    if not why.strip():
        raise ValueError("remove() needs a reason (why=)")
    path = target.path
    old = _read(path)
    if old is None:
        return False
    run = _runs[-1] if _runs else None
    _act(run, target, _permission_problems(run, target, "remove"))
    previous = _archive(path, target)
    path.unlink()
    if path.parent.is_dir() and not any(path.parent.iterdir()):
        path.parent.rmdir()
    rows = max(len(_rows(old)) - 1, 0)
    _log(run, target, f"removed ({rows} row{'s' if rows != 1 else ''})", why, previous, path)
    return True


def move_class(lang_id: str, old_class: str, new_class: str, *, why: str) -> int:
    """Move a class's annotation TSVs to the folder of its new name (a class
    rename). Each file is written under the new name and removed from the
    old, so the change log records both and the old folder's last versions
    stay in the archive. Returns how many files moved."""
    moved = 0
    for f in annotation_files(lang_id, old_class):
        write(annotation(lang_id, new_class, f.construction), read(f), why=why,
              what=f"moved from {f.relpath}")
        remove(f, why=f"moved to {new_class}/{f.name}: {why}")
        moved += 1
    return moved


def write_state(target: StateFile, text: str) -> bool:
    """Write one of the tooling's own files if ``text`` differs from what is
    there. True if written."""
    path = target.path
    if _read(path) == text:
        return False
    run = _runs[-1] if _runs else None
    _act(run, target, _state_problems(run, target, "write"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    _note_state(run, target, path, "written")
    return True


def append_state(target: StateFile, text: str) -> None:
    """Add ``text`` to the end of one of the tooling's own files (the
    provenance log, which only grows)."""
    if not text:
        return
    run = _runs[-1] if _runs else None
    _act(run, target, _state_problems(run, target, "append to"))
    path = target.path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(text)
    _note_state(run, target, path, "appended to")


def remove_state(target: StateFile) -> bool:
    """Delete one of the tooling's own files (a restructure journal with
    nothing left in it). True if there was one."""
    path = target.path
    if not path.exists():
        return False
    run = _runs[-1] if _runs else None
    _act(run, target, _state_problems(run, target, "remove"))
    path.unlink()
    _note_state(run, target, path, "removed")
    return True


def _note_state(run: Optional[_Run], target: StateFile, path: Path, action: str) -> None:
    if run is not None:
        run.written.append(path)
        run.state[target.relpath] = action


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _act(run: Optional[_Run], target: Union[LocalFile, StateFile], problems: List[str]) -> None:
    """Refuse the write if anything is wrong with it."""
    if not problems:
        return
    command = run.command if run else "(no command)"
    where = target.relpath if isinstance(target, StateFile) else f"{target.lang_id}/{target.relpath}"
    messages = [f"{command}: {where}: {p}" for p in problems]
    raise DoorViolation("The local-file door refused a write.\n  " + "\n  ".join(messages))


def _permission_problems(run: Optional[_Run], target: LocalFile, action: str) -> List[str]:
    if run is None:
        return ["no command is running, so the door cannot tell whether it may write "
                "(run it through `python -m coding`)"]
    out = []
    if not run.may_write:
        out.append(f"`{run.command}` was run without the flag that lets it write files "
                   f"(a dry run), but tried to {action} one")
    if target.kind in SOURCES and target.kind not in run.sources:
        out.append(f"this is {KINDS[target.kind]['what']}, a source a person edits; "
                   f"`{run.command}`'s operations.yaml record does not list it under "
                   f"edits_sources")
    return out


def _state_problems(run: Optional[_Run], target: StateFile, action: str) -> List[str]:
    """Rule 1 for the tooling's own files: a command is running, and this
    invocation writes somewhere (they record its Drive or local work), unless
    the file is one of the Drive door's records (``DRIVE_RECORDS``)."""
    if run is None:
        return ["no command is running, so the door cannot tell whether it may write "
                "(run it through `python -m coding`)"]
    if target.kind in DRIVE_RECORDS or run.may_write or run.may_write_drive:
        return []
    return [f"`{run.command}` was run without the flag that lets it write (a dry run), "
            f"but tried to {action} {STATE_KINDS[target.kind]['what']}"]


def _tab_spec(run: Optional[_Run], target: LocalFile):
    """The tab's columns from the spec, or None when the language has no
    diagnostics file or it doesn't list the class or construction."""
    key = (target.lang_id, target.class_name, target.construction)
    cache = run.specs if run else {}
    if key not in cache:
        from .sheet_spec import construction_columns
        try:
            cache[key] = construction_columns(*key, CODED_DATA)
        except (KeyError, FileNotFoundError):
            cache[key] = None
    return cache[key]


def _column_problems(run: Optional[_Run], target: LocalFile, old: Optional[str],
                     new: str) -> List[str]:
    """Rule 3: columns the spec doesn't expect, missing or out of order,
    that the previous version did not already have."""
    tab = _tab_spec(run, target)
    if tab is None:
        return []
    from .drive_door import _column_mismatches, _describe_mismatches
    from .sheet_spec import parked_operation

    def mismatches(text: Optional[str]) -> set:
        rows = _rows(text)
        return _column_mismatches(tab, rows[0] if rows else [], allowed_extra=parked_operation)

    found = mismatches(new) - (mismatches(old) if old is not None else set())
    # _describe_mismatches names the place as where/tab; the message already
    # starts with the file, so only the mismatch is kept.
    return [line.split(": ", 1)[1] for line in _describe_mismatches("", found)]


def _answers(target: LocalFile, text: Optional[str]) -> Optional[Dict[Tuple[str, ...], List[Tuple[str, str]]]]:
    """Each row's key and its filled annotator cells; None if the rows can't
    be matched (the key columns are missing)."""
    from planars.schema_values import row_columns, row_key
    rows = _rows(text)
    if not rows:
        return {}
    header = rows[0]
    keys = row_key(target.class_name, target.construction)
    tooling = set(row_columns(target.class_name, target.construction))
    if any(k not in header for k in keys):
        return None
    out: Dict[Tuple[str, ...], List[Tuple[str, str]]] = {}
    for raw in rows[1:]:
        rec = dict(zip(header, raw))
        key = tuple(rec.get(k, "").strip() for k in keys)
        filled = [(n, v) for n, v in rec.items() if n not in tooling and str(v).strip()]
        out.setdefault(key, []).extend(filled)
    return out


def _loss_problems(target: LocalFile, old: Optional[str], new: str) -> List[str]:
    """Rule 4: an answered row in the previous version is missing from the new."""
    if old is None:
        return []
    before, after = _answers(target, old), _answers(target, new)
    if before is None or after is None:
        return []
    from planars.schema_values import row_key
    keys = row_key(target.class_name, target.construction)
    lost = [(k, a) for k, a in before.items() if a and k not in after]
    if not lost:
        return []
    shown = "; ".join(", ".join(f"{c} {v!r}" for c, v in zip(keys, k)) for k, _ in lost[:3])
    more = f"; and {len(lost) - 3} more" if len(lost) > 3 else ""
    return [f"{len(lost)} answered row(s) would be lost, with no reason given: {shown}{more}"]


# ---------------------------------------------------------------------------
# What changed
# ---------------------------------------------------------------------------

def _describe(target: LocalFile, old: Optional[str], new: str) -> str:
    """The change in a few words, for the change log."""
    if target.kind in (DIAGNOSTICS_YAML, PROPOSAL_BASE):
        if old is None:
            return "created"
        diff = [l for l in difflib.ndiff(old.splitlines(), new.splitlines())
                if l.startswith(("+ ", "- "))]
        return f"{len(diff)} line(s) changed"
    new_rows = _rows(new)
    if old is None:
        n = max(len(new_rows) - 1, 0)
        return f"created ({n} row{'s' if n != 1 else ''})"
    old_rows = _rows(old)
    old_header = old_rows[0] if old_rows else []
    new_header = new_rows[0] if new_rows else []
    parts = []
    added = [c for c in new_header if c not in old_header]
    gone = [c for c in old_header if c not in new_header]
    if added:
        parts.append(f"column(s) added: {', '.join(added)}")
    if gone:
        parts.append(f"column(s) removed: {', '.join(gone)}")
    common = [c for c in new_header if c in old_header]
    olds = [dict(zip(old_header, r)) for r in old_rows[1:]]
    news = [dict(zip(new_header, r)) for r in new_rows[1:]]
    key = _row_key_columns(target, old_header, new_header)
    if key:
        by_old = {tuple(r.get(k, "") for k in key): r for r in olds}
        by_new = {tuple(r.get(k, "") for k in key): r for r in news}
        pairs = [(by_old[k], by_new[k]) for k in by_new if k in by_old]
        rows_added = sum(1 for k in by_new if k not in by_old)
        rows_gone = sum(1 for k in by_old if k not in by_new)
    else:
        pairs = list(zip(olds, news))
        rows_added = max(len(news) - len(olds), 0)
        rows_gone = max(len(olds) - len(news), 0)
    cells = sum(1 for a, b in pairs for c in common if a.get(c, "") != b.get(c, ""))
    if cells:
        parts.append(f"{cells} cell(s) changed")
    if rows_added:
        parts.append(f"{rows_added} row(s) added")
    if rows_gone:
        parts.append(f"{rows_gone} row(s) removed")
    return "; ".join(parts) or "rewritten, same cells"


def _row_key_columns(target: LocalFile, *headers: Sequence[str]) -> List[str]:
    """The columns rows are matched by, when every header has them: the
    schema's row key for an annotation TSV, Position for the planar."""
    if target.kind == ANNOTATION:
        from planars.schema_values import row_key
        keys = row_key(target.class_name, target.construction)
    elif target.kind == PLANAR:
        keys = ["Position"]
    else:
        return []
    return keys if all(all(k in h for k in keys) for h in headers) else []


# ---------------------------------------------------------------------------
# Archive, change log, commit
# ---------------------------------------------------------------------------

def _archive(path: Path, target: LocalFile) -> Path:
    """Copy the current file into the language's archive; never over an
    earlier copy. Returns the copy's path."""
    folder = CODED_DATA / target.lang_id / ARCHIVE_FOLDER / target.folder
    folder.mkdir(parents=True, exist_ok=True)
    base = f"{path.stem}_{stamp()}"
    dest, n = folder / f"{base}{path.suffix}", 2
    while dest.exists():
        dest, n = folder / f"{base}_{n}{path.suffix}", n + 1
    shutil.copy2(path, dest)
    return dest


def _log(run: Optional[_Run], target: LocalFile, what: str, why: str,
         previous: Optional[Path], path: Path) -> None:
    lang_dir = CODED_DATA / target.lang_id
    log = change_log(target.lang_id)
    by = run.command if run else "(no command)"
    if run is not None and _runs and _runs[0] is not run and _runs[0].command == REFRESH_COMMAND:
        by += IN_REFRESH
    when = datetime.now(timezone.utc).strftime(CHANGE_LOG_TIME_FORMAT)
    prev = str(previous.relative_to(lang_dir)) if previous else ""
    new_log = not log.exists()
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        if new_log:
            writer.writerow(CHANGE_LOG_COLUMNS)
        writer.writerow([when, target.relpath, what, by, why, prev])
    if run is not None:
        run.written += [path, log] + ([previous] if previous else [])
        run.lines.append(f"{target.lang_id}/{target.relpath}: {what} ({why})")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def push(repo: Path) -> subprocess.CompletedProcess:
    """Push; if GitHub refuses because someone else pushed meanwhile (a
    person during a daily refresh, 2026-10-22), replay this repository's
    commits on top of theirs and push again. A replay that conflicts is
    undone, and the refused push's result returned, so the local commit
    stays as it was."""
    first = _git(repo, "push")
    if first.returncode == 0:
        return first
    if _git(repo, "pull", "--rebase").returncode != 0:
        _git(repo, "rebase", "--abort")
        return first
    return _git(repo, "push")


def _commit(run: _Run) -> None:
    """Commit and push the run's files. Raises if ``git add`` or ``git
    commit`` fails (a write that reached disk but not git leaves planars-data
    dirty, #248); a failed push is printed: the commit is safe locally."""
    repo = CODED_DATA
    if not (repo / ".git").exists():
        return
    rel = []
    for p in dict.fromkeys(run.written):
        try:
            r = str(p.resolve().relative_to(repo.resolve()))
        except ValueError:
            continue
        # A file made and removed in the same run (a restructure journal
        # cleared once the run finished) is nothing to git.
        if p.exists() or _git(repo, "ls-files", "--", r).stdout.strip():
            rel.append(r)
    if not rel:
        return
    lines = run.lines + [f"{path}: {action}" for path, action in run.state.items()]
    message = f"data: {run.command} changed {len(lines)} file(s)\n\n" + "\n".join(lines)
    for step in (["add", "-A", "--", *rel], ["commit", "-m", message, "--", *rel]):
        done = _git(repo, *step)
        if done.returncode != 0:
            if step[0] == "commit" and "nothing to commit" in done.stdout:
                return
            raise RuntimeError(
                f"Could not commit what {run.command} wrote in planars-data "
                f"(git {step[0]}): {done.stderr.strip() or done.stdout.strip()}. "
                f"The files are written but not committed; commit them in coded_data/ "
                f"by hand and push.")
    pushed = push(repo)
    if pushed.returncode != 0:
        print(f"WARNING: committed {run.command}'s files in planars-data but could not "
              f"push: {pushed.stderr.strip()}. Run: git -C coded_data push")


# ---------------------------------------------------------------------------
# Reading the log: overwrites
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Overwrite:
    """A daily-refresh write that replaced someone's change to a file."""
    lang_id: str
    file: str            # within the language's folder
    when: str            # the refresh's write
    by: str
    replaced_when: str   # the change it replaced
    replaced_by: str
    replaced_why: str
    replaced_version: str  # the archive copy holding it, within the language's folder


def _command_of(by: str) -> str:
    return by[:-len(IN_REFRESH)] if by.endswith(IN_REFRESH) else by


def overwrites(since: str) -> List[Overwrite]:
    """Every write made inside a daily refresh at or after ``since`` (the
    log's UTC format) that replaced a file whose previous change-log line was
    written outside a refresh by a different command. The same command (an
    import someone ran by hand, then the refresh's) is the same source, not
    an overwrite; nor is rebuilding a file built from another (``BUILT``)."""
    found: List[Overwrite] = []
    for log in sorted(CODED_DATA.glob(f"*/{CHANGE_LOG_NAME}")):
        lang_id = log.parent.name
        if lang_id.startswith("."):
            continue
        built = {LocalFile(kind, lang_id).relpath for kind in BUILT}
        with open(log, encoding="utf-8", newline="") as f:
            lines = list(csv.DictReader(f, delimiter="\t"))
        last: Dict[str, Dict[str, str]] = {}
        for line in lines:
            before = last.get(line["file"])
            last[line["file"]] = line
            if (before is None or line["when (UTC)"] < since or line["file"] in built
                    or not line["by"].endswith(IN_REFRESH)
                    or before["by"].endswith(IN_REFRESH)
                    or _command_of(before["by"]) == _command_of(line["by"])):
                continue
            found.append(Overwrite(lang_id, line["file"], line["when (UTC)"],
                                   line["by"], before["when (UTC)"], before["by"],
                                   before["why"], line["previous version"]))
    return found
