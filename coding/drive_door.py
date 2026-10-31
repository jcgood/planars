"""The Drive door: every write to Drive is checked before it is made.

Phase 10 unit 5 (issue #271); design: docs/drive-door-design.md. Commands
reach Drive through ``drive_doorway.get_doorway()``, which hands them a
``CheckedDoorway`` wrapped around the live doorway (or around the fake, in
tests). Reads pass straight through. Every write is checked first:

- **The command may write at all.** The dispatcher (``coding/__main__.py``)
  tells the door which command is running (``running``). If
  ``operations.yaml`` says this invocation doesn't write to Drive (a dry run),
  every write is refused. A write the record declares as always made, even on
  a dry run (``always_on_writes``: import-sheets' pink highlighting), is
  allowed inside ``with always_on(name)``. A door with no command running
  refuses writes rather than guessing. ``running`` tells the local-file door
  (``coding/file_door.py``) too, so one call covers both.
- **Only writes the door understands.** The handles have only the protocol's
  methods (no passing unknown names through to gspread), and a
  ``batch_update`` request type not in ``REQUEST_TYPES`` is refused.
- **The rules for class sheets** (design § 2.4), from ``sheet_spec``:
  1. an annotator's filled cell is never blanked or changed, and a tab holding
     annotations is never cleared, deleted or shrunk, except inside
     ``with replacing(tab, reason)``. That block first re-reads the tab: if it
     differs from what the command read earlier in the run, an annotator
     edited it mid-run. It then saves the tab to ``state_files.SNAPSHOT_DIR``
     (in planars-data), and, given
     the row keys the rebuilt tab keeps (``kept``), refuses to drop any
     answered row unless told the drop is meant (``allow_drop``);
  2. a locked tab only ever receives its builder's content;
  3. dropdowns only on criterion columns (and Status), with exactly the
     spec's values;
  4. protection only on locked tabs (and the one tab of a planar or
     diagnostics Sheet);
  5. (every kind of file, not only class sheets) a grant is made, changed or
     removed only as the file's sharing spec says (``sheet_spec.sharing_spec``):
     named people at their role (a class sheet's annotator is a writer while
     the sheet is live, a reader once it is labelled archived), a link share
     only where the spec allows one (notebooks and reports, until design § 7
     Q4's test), and a grant the spec calls for is never removed;
  6. at the end of a command that succeeded and was allowed to write, each
     class sheet whose shape it changed is re-read and compared with its spec:
     tab names, order and protection, and for each tab it wrote, the columns
     and the row keys (pair and keyed rows from the generators' own builders,
     ``sheet_spec.expected_row_keys``). Only mismatches the sheet did not have
     before the command first wrote to it are reported: older drift has its
     own issues (``sheet-drift``, ``planar-changed``, ``dependent-stale``). A
     sheet made to replace another (``create_spreadsheet(..., replaces=old_id)``,
     restructure-sheets) takes the old sheet's tab list as its "before", and
     its carried-over pair and keyed rows are left to the ``dependent-stale``
     check. Formatting, dropdowns and highlights change no shape and cost no
     extra read.
  7. a comment goes only on a class sheet, and may mention (``+address``,
     which makes Google email that person) only the sheet's annotator
     (issue #309: how an annotator without GitHub hears about problems).
- **The rules for the planar and diagnostics Sheets** (design § 8, "5f"),
  each a one-tab copy of one file (``COPY_SHEETS``; ``sheet_spec.copy_sheet_spec``):
  every cell is the tooling's, since unit 11b made them read-only copies, so
  rule 1 has nothing to look after; no dropdowns; the tab is protected
  (annotators are readers by sharing, but coordinators are writers on the
  root folder, which every file inherits); and rule 6 checks that the Sheet
  has one protected tab holding exactly the file.
- **The rules for a status sheet** (design § 8, "5f"; ``sheet_spec.status_sheet_spec``):
  every cell is the tooling's, so rule 1 has nothing to look after; no
  dropdowns; no protection (annotators are readers by sharing); and rule 6
  checks it has one tab, ``Status``, whose rows under the header name every
  construction of the diagnostics file, in order, each with a status.
- **The rules for a proposal sheet** (unit 11a; ``sheet_spec.proposal_sheet_spec``):
  its Planar and Diagnostics tabs are the annotator's proposal, every cell
  theirs, so rule 1 holds for all of them (a refill goes through
  ``replacing()``); Instructions is a locked tab (rule 2, protected); Last
  review is the tooling's; no dropdowns; and rule 6 checks its four tabs,
  their order and protection, and that each proposal tab written has its
  source's columns and What changed?.
- **Rule 8, the files that are not spreadsheets** (``FILE_KINDS``: notes
  Docs, reports, contributor charts, notebooks, folders; design § 8, "5f";
  ``sheet_spec.file_spec``): a create, rename, move or upload sends only the
  spec's name, folder, type and kind of content (a notebook's and a PDF's
  checked by their form; the manifest, checked against its contract, was
  deleted in unit 11c-5); a
  notes Doc's text is never replaced, and only an acknowledgment line is
  appended to it; a file only one of which may exist (all but archive
  folders) is not made a second time; and only a notebook
  (``TRASHABLE_KINDS``) is put in the trash, never deleted outright.

Every call is retried on Google's "try again" answers and on a dropped
connection (the rule is ``planars/google_retry.py``, which the Colab
notebooks' reader shares), here and nowhere else in the commands. A call that creates something is retried only after
checking the first attempt didn't land, so a retry never makes a duplicate.

**Provenance.** At the end of the command the door appends one line per tab
or Drive file it wrote to ``state_files.PROVENANCE_LOG``: the command and its
arguments, what was written, which sheet it is, how many calls and cells,
and the ``replacing`` reason if there was one. A command that wrote nothing
leaves no line.

**Which file is which (identity labels).** Every Drive file the tooling makes
carries its identity as Drive properties (``planars_kind``, ``planars_lang``,
``planars_class``, ``planars_name``; ``planars_state=archived`` once
archived): public properties, which any coordinator's client can read. The
kinds are ``KINDS``, and an ``Identity`` that doesn't fit one can't be made.
Every create on the door takes ``identity=`` and writes the label;
``mark_archived`` is called where a class sheet is archived
(``restructure_sheets._lock_archived_sheet``, ``retire_classes._archive_drive_sheet``)
and undone on rollback (``restructure_sheets._rollback_unit``). The door places a file from what this command made, else its
label (read once per command); the files made before labels existed were
labelled by ``migrations/label_drive_files.py``. Every kind has a spec
(``SHEET_KINDS``, ``FILE_KINDS``). A write to a file the door cannot place
passes unchecked by rules 1-4, 6 and 8 for now; before the last kind is
enforced, such a write is refused (design § 5).

Each tab of a class sheet is labelled too, with Sheets developer metadata:
its kind (locked, construction, status) and its name. When a command that
was allowed to write succeeds, the door labels every unlabelled tab of each
class sheet it wrote, from the spec, in one ``batch_update`` per sheet. A
tab's label is what the door goes by, so a tab renamed by hand keeps its
identity; renaming a tab through the door drops its labels.

**Watch and enforce.** Enforce: a broken rule raises ``DoorViolation`` and
nothing is written. Watch: the write goes ahead, and at the end of the
command the door files or updates one ``door-violation`` GitHub issue (the
terminal reaches no one). Tests use enforce for everything. Live runs use
``LIVE_MODE`` (watch), except that a broken rule on a file whose kind is in
``LIVE_ENFORCED_KINDS`` (class sheets since 2026-10-19; status sheets and
the diagnostics Sheet since 2026-10-21; contributor charts since 2026-10-27)
raises: each check
is told which file it is for, and its kind decides.

**Tests.** A test's provenance log and snapshots go to its own temporary
folder (``tests/conftest.py``). Tests run a command through
``tests/command_runner.run_command``, which says which command is running;
``tests/test_drive_door.py`` tests each rule.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import (Any, Callable, Dict, FrozenSet, Iterable, Iterator, List, Mapping,
                    Optional, Sequence, Tuple)

import gspread

from planars import drive_labels, google_retry

ROOT =Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

ENFORCE = "enforce"
WATCH = "watch"

# The one place the live mode is set (design § 4). A kind of file moves to
# enforce once the door has seen real writes to it go through cleanly and
# every reported violation is resolved (Q7): it is then listed in
# LIVE_ENFORCED_KINDS, and a broken rule on a file of that kind raises live
# too. Class sheets since 2026-10-19 (Jeff dropped the one-week minimum);
# status sheets and the diagnostics Sheet since 2026-10-21 (clean real writes:
# every status sheet rebuilt 2026-10-20 and -21, the diagnostics push of
# 2026-10-19); contributor charts since 2026-10-27 (six uploads by
# laminar-charts on 2026-10-26). Everything else stays in LIVE_MODE, watch.
LIVE_MODE = WATCH
CLASS_SHEET = drive_labels.CLASS_SHEET
PLANAR_SHEET = drive_labels.PLANAR_SHEET
DIAGNOSTICS_SHEET = "diagnostics_sheet"
STATUS_SHEET = "status_sheet"
# A language's proposal sheet (unit 11a; ownership-design § 3.2): where its
# annotator proposes changes to the planar and the diagnostics file.
PROPOSAL_SHEET = "proposal_sheet"
LIVE_ENFORCED_KINDS: FrozenSet[str] = frozenset({CLASS_SHEET, STATUS_SHEET, DIAGNOSTICS_SHEET,
                                                 "charts"})
# The Sheets that are a one-tab copy of one file, and what the door calls
# that file and the Sheet in what it reports (sheet_spec.copy_sheet_spec).
COPY_SHEETS: Dict[str, Tuple[str, str]] = {
    PLANAR_SHEET: ("the planar file", "the planar Sheet"),
    DIAGNOSTICS_SHEET: ("the diagnostics file", "the diagnostics Sheet"),
}
# The spreadsheets, whose tabs and cells the door checks against a spec
# (rules 1-4 and 6), and the files that are not spreadsheets, whose name,
# folder, type and content it checks (rule 8, sheet_spec.file_spec). Every
# kind in KINDS is one or the other (tests/test_drive_door.py checks), and
# every kind's sharing is checked (rule 5).
NOTES_DOC = "notes_doc"
SHEET_KINDS: FrozenSet[str] = frozenset({CLASS_SHEET, *COPY_SHEETS, STATUS_SHEET,
                                         PROPOSAL_SHEET})
FILE_KINDS: FrozenSet[str] = frozenset({NOTES_DOC, "report", "charts", "notebook", "folder"})
# The kinds of file that may be put in Drive's trash (rule 8): the tooling
# writes every cell of them, so nobody's work is in one. (The manifest was
# one too, for one run of migrations/trash_manifest.py, 2026-10-29.)
TRASHABLE_KINDS: FrozenSet[str] = frozenset({"notebook"})

# Every batch_update request type the tooling sends, each checked below.
# A new one is added here, with its check, before any command can use it.
REQUEST_TYPES = frozenset({
    "updateSheetProperties", "repeatCell", "setDataValidation", "insertDimension",
    "deleteDimension", "updateDimensionProperties", "updateCells", "mergeCells",
    "unmergeCells", "addProtectedRange",
})

VIOLATION_LABEL = "door-violation"
_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_FOLDER_MIME = "application/vnd.google-apps.folder"
_DOC_MIME = "application/vnd.google-apps.document"
# A mention in a Drive comment: "+" and an email address (rule 7).
_MENTION = re.compile(r"\+([\w.+-]+@[\w-]+(?:\.[\w-]+)+)")


class DoorViolation(RuntimeError):
    """A write broke one of the door's rules (enforce mode)."""


class AnswersWouldBeDropped(DoorViolation):
    """``replacing(kept=...)`` found answered rows the rebuilt tab would not
    keep. Raised in every mode: nothing has been written. ``lines`` names each
    row and its answers, for the command's own message."""

    def __init__(self, tab: str, lines: List[str]) -> None:
        super().__init__(f"rebuilding {tab!r} would drop {len(lines)} answered row(s):\n"
                         + "\n".join(lines))
        self.lines = lines


# ---------------------------------------------------------------------------
# Identity: what a Drive file is
# ---------------------------------------------------------------------------

# Every kind of Drive file the tooling makes, and which parts of its identity
# it carries: _LANG means required, None means absent, and a set of names
# means one of them is required. Anything else cannot be placed.
_LANG, _BY_NAME = "required", "by name"
KINDS: Dict[str, Dict[str, Any]] = {
    CLASS_SHEET:         {"lang": _LANG, "class": _LANG, "name": None},
    PLANAR_SHEET:        {"lang": _LANG, "class": None, "name": None},
    DIAGNOSTICS_SHEET:   {"lang": _LANG, "class": None, "name": None},
    STATUS_SHEET:        {"lang": _LANG, "class": None, "name": None},
    PROPOSAL_SHEET:      {"lang": _LANG, "class": None, "name": None},
    NOTES_DOC:          {"lang": _LANG, "class": None, "name": None},
    "report":            {"lang": _LANG, "class": None, "name": None},
    # A language's contributor charts, one PDF per grouping
    # (laminar/contributor_charts.py; coding/laminar_charts.py).
    "charts":            {"lang": _LANG, "class": None, "name": {"classes", "types"}},
    # These two depend on the name: see Identity.__post_init__. (A
    # "validation" notebook was retired 2026-10-23,
    # migrations/retire_validation_notebooks.py; the ones made are in the trash.)
    "notebook":          {"lang": _BY_NAME, "class": None,
                          "name": {"domains", "report", "all_languages"}},
    "folder":            {"lang": _BY_NAME, "class": None,
                          "name": {"root", "language", "archive", "status"}},
}
# Folders that belong to one language; the others belong to none. Every
# notebook belongs to one language except all_languages.
_LANGUAGE_FOLDERS = {"language", "archive"}

# The Drive properties a file's identity is written to, and a tab's labels
# (its kind, one of the three below, which sheet_spec uses too, and its
# name — the locked tab's title, the construction, or Status): the names are
# planars/drive_labels.py's, which Colab reads too.
_LABEL = {"kind": drive_labels.KIND, "lang_id": drive_labels.LANG,
          "class_name": drive_labels.CLASS, "name": drive_labels.NAME}
STATE_LABEL = drive_labels.STATE
ARCHIVED = drive_labels.ARCHIVED
TAB_KIND_LABEL = drive_labels.TAB_KIND
TAB_NAME_LABEL = drive_labels.TAB_NAME
LOCKED_TAB = "locked"
STATUS_TAB_KIND = "status"
CONSTRUCTION_TAB = drive_labels.CONSTRUCTION_TAB
TAB_KINDS = (LOCKED_TAB, CONSTRUCTION_TAB, STATUS_TAB_KIND)
# The one tab of a planar or diagnostics Sheet: every cell the tooling's, a
# copy of its source that annotators read (sheet_spec.copy_sheet_spec; Phase
# 10 unit 11b). Not a label: the Sheet has only one tab.
COPY_TAB = "copy"
# The one tab of a language's status sheet: every cell the tooling's, rebuilt
# on every run (sheet_spec.status_sheet_spec). Not a label either.
STATUS_PAGE_TAB = "status page"
# A proposal sheet's tabs (sheet_spec.proposal_sheet_spec), told apart by
# title: Instructions is a locked tab (LOCKED_TAB); Last review is the
# tooling's, rewritten after each review; the Planar and Diagnostics tabs are
# the annotator's proposal, every cell theirs.
REVIEW_TAB = "review"
PROPOSAL_TAB = "proposal"
# The tabs whose filled cells are annotators' answers (rule 1).
_ANSWER_TABS = (CONSTRUCTION_TAB, STATUS_TAB_KIND, PROPOSAL_TAB)


@dataclass(frozen=True)
class Identity:
    """What a Drive file is: its kind, and the language, class or name that
    say which one. Checked against ``KINDS`` when made."""
    kind: str
    lang_id: Optional[str] = None
    class_name: Optional[str] = None
    name: Optional[str] = None

    def __post_init__(self) -> None:
        rule = KINDS.get(self.kind)
        if rule is None:
            raise ValueError(f"unknown kind of Drive file {self.kind!r}; "
                             f"known: {sorted(KINDS)}")
        lang_rule = rule["lang"]
        if self.kind == "folder":
            lang_rule = _LANG if self.name in _LANGUAGE_FOLDERS else None
        elif self.kind == "notebook":
            lang_rule = None if self.name == "all_languages" else _LANG
        for part, value, needed in (("language", self.lang_id, lang_rule),
                                    ("class", self.class_name, rule["class"])):
            if needed == _LANG and not value:
                raise ValueError(f"a {self.kind} needs its {part}")
            if needed is None and value:
                raise ValueError(f"a {self.kind} has no {part} (given {value!r})")
        names = rule["name"]
        if names is None and self.name:
            raise ValueError(f"a {self.kind} has no name (given {self.name!r})")
        if names is not None and self.name not in names:
            raise ValueError(f"a {self.kind}'s name is one of {sorted(names)}, "
                             f"not {self.name!r}")

    def describe(self) -> str:
        if self.kind == CLASS_SHEET:
            return f"{self.class_name}_{self.lang_id}"
        parts = [self.kind] + [p for p in (self.name, self.lang_id) if p]
        return " ".join(parts)

    def labels(self) -> Dict[str, str]:
        """The Drive properties that record this identity."""
        return {label: getattr(self, field) for field, label in _LABEL.items()
                if getattr(self, field)}

    @classmethod
    def from_labels(cls, properties: Mapping[str, str]) -> Optional["Identity"]:
        """The identity a file's properties record; None if they record none
        or one that cannot be placed."""
        if _LABEL["kind"] not in properties:
            return None
        try:
            return cls(**{field: properties.get(label) or None
                          for field, label in _LABEL.items()})
        except ValueError:
            return None


def class_sheet(lang_id: str, class_name: str) -> Identity:
    return Identity(CLASS_SHEET, lang_id, class_name)


def lang_file(kind: str, lang_id: str) -> Identity:
    """A planar, diagnostics or status sheet, notes Doc or report."""
    return Identity(kind, lang_id)


def charts(grouping: str, lang_id: str) -> Identity:
    """A language's contributor charts PDF, by ``classes`` or ``types``."""
    return Identity("charts", lang_id, name=grouping)


def notebook(name: str, lang_id: Optional[str] = None) -> Identity:
    return Identity("notebook", lang_id, name=name)


def folder(name: str, lang_id: Optional[str] = None) -> Identity:
    return Identity("folder", lang_id, name=name)


# ---------------------------------------------------------------------------
# Which command is running
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Context:
    command: str
    may_write: bool
    always_on: FrozenSet[str]


_context: Optional[_Context] = None
_always_on_active: List[str] = []


def _record_for(op_id: str) -> Optional[dict]:
    from .registry import _load_operations
    return _load_operations().get(op_id)


@contextlib.contextmanager
def running(command: str, args: Optional[argparse.Namespace] = None, *,
            may_write: Optional[bool] = None) -> Iterator[None]:
    """Tell both doors which command is running, for the length of the block:
    this one and the local-file door (``file_door.begin``/``finish``).

    ``command`` is the hyphenated command (``update-sheets``). Whether it may
    write comes from its ``operations.yaml`` record and ``args``, the same
    match provenance uses; pass ``may_write`` instead for code that runs
    outside the dispatcher and has no record (a migration). At the end, if
    the command succeeded, the door labels the tabs it wrote; then, however
    it ended, it logs what it wrote and, in watch mode, reports any
    violations in one GitHub issue. The local-file door then commits the
    files the command wrote.
    """
    from . import file_door
    file_door.begin(command, args, may_write=may_write)
    succeeded = False
    try:
        with _drive_running(command, args, may_write=may_write):
            yield
        succeeded = True
    except SystemExit as exc:
        succeeded = exc.code in (0, None)
        raise
    finally:
        file_door.finish(succeeded)


@contextlib.contextmanager
def _drive_running(command: str, args: Optional[argparse.Namespace], *,
                   may_write: Optional[bool]) -> Iterator[None]:
    """This door's part of ``running``."""
    global _context
    from .provenance import writes_to_drive
    op_id = command.replace("-", "_")
    record = _record_for(op_id)
    if may_write is None:
        if record is None:
            raise ValueError(f"{command!r} has no operations.yaml record; "
                             "pass may_write to say whether it writes to Drive")
        may_write = writes_to_drive(op_id, args if args is not None else argparse.Namespace())
    always = frozenset((record or {}).get("always_on_writes", []))
    # get_doorway, not "the door if one exists": live, the command makes its
    # door only at its first Drive call, after this point, so until 2026-10-17
    # no live command was logged, shape-checked or reported. Making the door
    # costs nothing; it signs in to Google only when first used. Made before
    # _context is set, so a failure here leaves no command marked running.
    from .drive_doorway import get_doorway
    door = get_doorway()
    previous, _context = _context, _Context(command, may_write, always)
    if isinstance(door, CheckedDoorway):
        door.begin_command()
    succeeded = False
    try:
        yield
        succeeded = True
    except SystemExit as exc:
        succeeded = exc.code in (0, None)
        raise
    finally:
        try:
            if isinstance(door, CheckedDoorway):
                door.finish_command(command, args, succeeded=succeeded)
        finally:
            _context = previous


@contextlib.contextmanager
def always_on(name: str) -> Iterator[None]:
    """Mark writes that the running command makes even on a dry run. Allowed
    only if its operations.yaml record lists ``name`` under ``always_on_writes``."""
    _always_on_active.append(name)
    try:
        yield
    finally:
        _always_on_active.pop()


@contextlib.contextmanager
def replacing(tab: "CheckedWorksheet", reason: str, *,
              kept: Optional[Iterable[Sequence[str]]] = None,
              allow_drop: bool = False) -> Iterator[None]:
    """Declare that the writes in this block replace annotations on ``tab``
    on purpose (rule 1). ``reason`` says why, in words a coordinator can read.

    Before the block runs, the door re-reads the tab. If it differs from what
    the command read earlier in this run, an annotator edited it mid-run, and
    the door says so (by mode). It saves what it read to
    ``state_files.SNAPSHOT_DIR``.

    ``kept``: for a tab being rebuilt row by row, the row keys (the schema's
    ``row_key`` columns, as the tab holds them now) whose answers the rebuilt
    tab carries over. Any other row holding an answer would be lost, so the
    door raises ``AnswersWouldBeDropped`` before anything is written, in
    every mode, unless ``allow_drop`` says the coordinator confirmed it.
    """
    if not isinstance(tab, CheckedWorksheet):
        raise TypeError("replacing() takes a tab handle from the Drive door")
    if not reason.strip():
        raise ValueError("replacing() needs a reason")
    door, key = tab._door, tab._key
    door._before_replacing(tab, reason, kept, allow_drop)
    door._replacing[key] = reason
    try:
        yield
    finally:
        door._replacing.pop(key, None)


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

# Which answers are retried, and how, is planars.google_retry's (the Colab
# notebooks use the same rule). The door passes its own waits and sleep, so
# a test can make them instant (monkeypatch _WAITS or time.sleep here).
_status_of = google_retry.status_of
_WAITS = google_retry.WAITS


def _retry(fn: Callable[[], Any], landed: Optional[Callable[[], Any]] = None) -> Any:
    """``planars.google_retry.retry`` with the door's waits."""
    return google_retry.retry(fn, landed, waits=_WAITS, sleep=lambda s: time.sleep(s))


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------

def _anchor(range_name: str) -> Tuple[int, int]:
    """0-based (row, col) of an A1 range's top-left cell."""
    first = range_name.split("!")[-1].split(":")[0]
    row, col = gspread.utils.a1_to_rowcol(first)
    return row - 1, col - 1


def _cell(grid: List[List[str]], r: int, c: int) -> str:
    if r < len(grid) and c < len(grid[r]):
        return grid[r][c]
    return ""


def _put(grid: List[List[str]], r: int, c: int, value: str) -> None:
    while len(grid) <= r:
        grid.append([])
    row = grid[r]
    while len(row) <= c:
        row.append("")
    row[c] = value


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _row(grid: List[List[str]], r: int) -> List[str]:
    return grid[r] if r < len(grid) else []


def _trimmed(grid: List[List[str]]) -> List[List[str]]:
    """The grid without trailing empty cells and rows, as Sheets returns it."""
    rows = [list(r) for r in grid]
    for r in rows:
        while r and r[-1] == "":
            r.pop()
    while rows and not rows[-1]:
        rows.pop()
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save_snapshot(tab: "CheckedWorksheet", rows: List[List[str]], reason: str) -> Path:
    """Save a tab's content before replacing() lets its answers be replaced,
    so whatever is lost can be checked and put back by hand. One file per
    tab, overwritten each time: once a rebuild has succeeded, the sheet holds
    what is worth having."""
    identity = tab._ss.identity
    if identity is not None and identity.class_name:
        stem = f"{identity.lang_id}_{identity.class_name}_{tab.title}"
    elif identity is not None and identity.lang_id:
        stem = f"{identity.lang_id}_{identity.kind}_{tab.title}"
    else:
        stem = f"{tab._ss.id}_{tab.title}"
    from . import file_door
    target = file_door.regen_snapshot(re.sub(r"[^\w.-]", "_", stem))
    file_door.write_state(target, json.dumps({
        "spreadsheet_id": tab._ss.id,
        "spreadsheet": tab._ss.title,
        "lang_id": identity.lang_id if identity else None,
        "class_name": identity.class_name if identity else None,
        "tab": tab.title,
        "command": _context.command if _context else None,
        "reason": reason,
        "saved_at": _now(),
        "rows": rows,
    }, indent=2, ensure_ascii=False))
    return target.path


# ---------------------------------------------------------------------------
# The door
# ---------------------------------------------------------------------------

class CheckedDoorway:
    """Wraps a doorway (live or fake) and checks every write it is asked for."""

    def __init__(self, inner, mode: str = LIVE_MODE) -> None:
        if mode not in (ENFORCE, WATCH):
            raise ValueError(f"unknown door mode {mode!r}")
        self._inner = inner
        self.mode = mode
        self.violations: List[str] = []
        self._created: Dict[str, Identity] = {}      # made by this command
        # Each file's Drive properties, read once per command.
        self._labels: Dict[str, Dict[str, str]] = {}
        # Each spreadsheet's tab labels: {sheet id: {key: value}}.
        self._tab_labels: Dict[str, Dict[int, Dict[str, str]]] = {}
        # Spreadsheets this command wrote to, for the end-of-command labels.
        self._sheets_written: Dict[str, "CheckedSpreadsheet"] = {}
        self._specs: Dict[Tuple[str, str], Any] = {}
        self._grids: Dict[Tuple[str, int], List[List[str]]] = {}
        self._replacing: Dict[Tuple[str, int], str] = {}
        self._written: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
        # Rule 6: each class sheet's tabs (order, names, protection) and each
        # tab's content as they were before this command first changed them.
        # None: the command made it.
        self._before_sheets: Dict[str, Optional[List[Dict[str, Any]]]] = {}
        self._before_tabs: Dict[Tuple[str, int], Optional[List[List[str]]]] = {}
        self._replacements: Dict[str, str] = {}   # new sheet id -> the sheet it replaces
        # Each spreadsheet's tabs by sheet id, for finding the tab a request
        # names (CheckedSpreadsheet._tab_by_sheet_id).
        self._tabs: Dict[str, Dict[int, Any]] = {}
        self._started = ""

    @property
    def inner(self):
        """The wrapped doorway. For tests' assertions only; commands never
        reach past the door (tests/test_doorway_coverage.py)."""
        return self._inner

    # -- command lifetime ---------------------------------------------------
    def begin_command(self) -> None:
        """Start a command with nothing remembered from the last one: its
        language files, the sheets and their labels may all have changed."""
        self.violations = []
        self._specs.clear()
        self._grids.clear()
        self._created = {}
        self._labels = {}
        self._tab_labels = {}
        self._sheets_written = {}
        self._written = {}
        self._before_sheets = {}
        self._before_tabs = {}
        self._replacements = {}
        self._tabs = {}
        self._started = _now()

    def finish_command(self, command: str, args: Optional[argparse.Namespace] = None,
                       succeeded: bool = True) -> None:
        """After a command that succeeded, and was allowed to write (not a dry
        run that only painted highlights), label the tabs of every class
        sheet it wrote and check each one's shape (rule 6). Then, however it
        ended, log what it wrote, and act on what broke a rule: raise
        (enforce) or report it in one issue (watch)."""
        shape_problems: List[Tuple[List[str], str]] = []    # (problems, sheet id)
        if succeeded and _context is not None and _context.may_write:
            for ss in list(self._sheets_written.values()):
                self._label_tabs(ss)
            for ss in list(self._sheets_written.values()):
                found = self._shape_problems(ss)
                if found:
                    shape_problems.append((found, ss.id))
            self._before_sheets, self._before_tabs, self._replacements = {}, {}, {}
        if self._written:
            # One line in the command's output, so a run log shows the door
            # was at work: a silent door looks the same as a broken one, which
            # is how unit 20's bug (no live command checked) hid for four days.
            calls = sum(e["writes"] for e in self._written.values())
            broken = len(self.violations) + sum(len(p) for p, _ in shape_problems)
            print(f"Drive door ({self._mode_label()}): checked {calls} write(s) to "
                  f"{len(self._written)} tab(s) or file(s); {broken} broke a rule.")
            from . import provenance
            arguments = vars(args) if args is not None else {}
            provenance.append_writes([
                {"timestamp": self._started, "command": command, "args": arguments, **entry}
                for entry in self._written.values()])
            self._written = {}
        try:
            # Each sheet's kind decides its mode. The watched ones first, so
            # an enforced sheet's refusal doesn't keep them out of the issue.
            shape_problems.sort(key=lambda found: self._enforces(found[1]))
            for found, target in shape_problems:
                self._act("shape at the end of the command", found, target)
        finally:
            # Reported once, under the command that made them: daily-refresh
            # runs commands inside its own, and must not report them again.
            violations, self.violations = self.violations, []
            if self.mode == WATCH and violations:
                _report_violations(command, violations)

    # -- provenance ---------------------------------------------------------
    def _wrote(self, file_id: str, title: str, tab: Optional[str], action: str,
               cells: int = 0, identity: Optional[Identity] = None,
               reason: Optional[str] = None) -> None:
        """Count one write toward its tab's (or file's) provenance line."""
        entry = self._written.setdefault((file_id, tab), {
            "file_id": file_id, "title": title, "tab": tab,
            "identity": identity.describe() if identity else None,
            "actions": [], "writes": 0, "cells": 0, "replacing": []})
        entry["writes"] += 1
        entry["cells"] += cells
        if title and not entry["title"]:
            entry["title"] = title
        if identity and not entry["identity"]:
            entry["identity"] = identity.describe()
        if action not in entry["actions"]:
            entry["actions"].append(action)
        if reason and reason not in entry["replacing"]:
            entry["replacing"].append(reason)

    def _wrote_file(self, file_id: str, title: str, action: str) -> None:
        self._wrote(file_id, title, None, action, identity=self._known_identity(file_id))

    def _wrote_sheet(self, ss: "CheckedSpreadsheet") -> None:
        """Remember a spreadsheet this command wrote, to label its tabs at the end."""
        self._sheets_written.setdefault(ss.id, ss)

    # -- identity -------------------------------------------------------------
    def _known_identity(self, file_id: str) -> Optional[Identity]:
        """What the door already knows a file to be, without reading Drive."""
        if file_id in self._created:
            return self._created[file_id]
        return Identity.from_labels(self._labels.get(file_id, {}))

    def _read_labels(self, file_id: str) -> Dict[str, str]:
        """A file's Drive properties, read once per command. No such file
        (404) or not ours to read (403) means no labels; any other failure,
        after get_file's retries, is raised, never taken (and kept for the
        rest of the command) as "no label" (2026-10-25: a labelled language
        folder was reported unlabelled that way)."""
        if file_id not in self._labels:
            try:
                meta = self.get_file(file_id, fields="properties")
            except Exception as exc:  # noqa: BLE001 - re-raised unless 403/404
                if _status_of(exc) not in (403, 404):
                    raise
                meta = {}
            self._labels[file_id] = dict(meta.get("properties") or {})
        return self._labels[file_id]

    def _identify(self, file_id: str) -> Optional[Identity]:
        """What a file is: made by this command, else its label."""
        if file_id in self._created:
            return self._created[file_id]
        return Identity.from_labels(self._read_labels(file_id))

    def is_archived(self, file_id: str) -> bool:
        return self._read_labels(file_id).get(STATE_LABEL) == ARCHIVED

    def _write_labels(self, file_id: str, properties: Mapping[str, Optional[str]],
                      what: str) -> None:
        """Set a file's labels (a None value removes one). A write like any
        other: the command must be allowed to write."""
        self._check(what, target=file_id)
        _retry(lambda: self._inner.update_file(file_id, properties=dict(properties)))
        labels = self._labels.setdefault(file_id, {})
        for key, value in properties.items():
            if value is None:
                labels.pop(key, None)
            else:
                labels[key] = value
        self._wrote_file(file_id, "", "label")

    def mark_archived(self, file_id: str, archived: bool = True) -> None:
        """Label a file archived (or, undoing that, live). Called where a
        class sheet is archived, before its annotator's grant is lowered, so
        the sharing rule expects reader; and the reverse when undone."""
        identity = self._identify(file_id)
        if identity is None:
            self._check(f"mark {file_id} {'archived' if archived else 'live'}",
                        [f"{file_id} has no label, so the door cannot say what it is"])
            return
        labels: Dict[str, Optional[str]] = {STATE_LABEL: ARCHIVED if archived else None}
        self._write_labels(file_id, labels,
                           f"mark {identity.describe()} {'archived' if archived else 'live'}")

    def _check_found(self, file_id: str, identity: Identity, what: str) -> None:
        """A file found rather than made must not be labelled as something else."""
        existing = Identity.from_labels(self._read_labels(file_id))
        if existing is not None and existing != identity:
            self._act(what, [f"found {existing.describe()} where {identity.describe()} "
                             "was expected"], file_id)

    # -- tab labels -----------------------------------------------------------
    def _tab_labels_of(self, ss: "CheckedSpreadsheet") -> Dict[int, Dict[str, str]]:
        """Each tab's labels, by sheet id; read once per spreadsheet per command."""
        if ss.id not in self._tab_labels:
            meta = _retry(lambda: ss._inner.fetch_sheet_metadata(params={
                "fields": "sheets(properties(sheetId,title),developerMetadata)"}))
            self._tab_labels[ss.id] = {
                sheet["properties"]["sheetId"]: {
                    m["metadataKey"]: m.get("metadataValue", "")
                    for m in sheet.get("developerMetadata", [])
                    if m.get("metadataKey") in (TAB_KIND_LABEL, TAB_NAME_LABEL)}
                for sheet in meta.get("sheets", [])}
        return self._tab_labels[ss.id]

    def unlabelled_tabs(self, ss: "CheckedSpreadsheet") -> List[Tuple[Any, str]]:
        """Each tab of a class sheet that has no label yet and that its spec
        lists, with the kind the spec gives it. A tab the spec doesn't list is
        left out (rule 6 reports it); so is every tab of a sheet that isn't a
        live-placeable class sheet or whose spec can't be built."""
        identity = ss.identity
        if identity is None or identity.kind != CLASS_SHEET:
            return []
        spec = self._spec(identity)
        if isinstance(spec, Exception):
            return []
        self._tab_labels.pop(ss.id, None)
        labels = self._tab_labels_of(ss)
        kinds = {t.title: t.kind for t in spec.tabs}
        return [(ws, kinds[ws.title]) for ws in _retry(ss._inner.worksheets)
                if not labels.get(ws.id) and ws.title in kinds]

    def _label_tabs(self, ss: "CheckedSpreadsheet") -> int:
        """Label each tab of a class sheet that has no label yet with what its
        spec says it is (``unlabelled_tabs``), in one batch_update. Labels
        already there are kept: they are what lets a tab renamed by hand still
        be recognised. How many tabs it labelled."""
        tabs = self.unlabelled_tabs(ss)
        requests = []
        for ws, kind in tabs:
            for key, value in ((TAB_KIND_LABEL, kind), (TAB_NAME_LABEL, ws.title)):
                requests.append({"createDeveloperMetadata": {"developerMetadata": {
                    "metadataKey": key, "metadataValue": value,
                    "location": {"sheetId": ws.id}, "visibility": "DOCUMENT"}}})
        if not requests:
            return 0
        self._check(f"label the tabs of {ss.title!r}", target=ss.id)
        _retry(lambda: ss._inner.batch_update({"requests": requests}))
        self._tab_labels.pop(ss.id, None)
        self._wrote(ss.id, ss.title, None, "label_tabs", identity=ss.identity)
        return len(tabs)

    def _drop_tab_labels(self, ws: "CheckedWorksheet") -> None:
        """Remove a tab's labels (it is being renamed by the tooling, so its
        name label would be wrong; the end of the command labels it afresh)."""
        if not self._tab_labels_of(ws._ss).get(ws.id):
            return
        _retry(lambda: ws._ss._inner.batch_update({"requests": [
            {"deleteDeveloperMetadata": {"dataFilter": {"developerMetadataLookup": {
                "metadataKey": key, "metadataLocation": {"sheetId": ws.id}}}}}
            for key in (TAB_KIND_LABEL, TAB_NAME_LABEL)]}))
        self._tab_labels[ws._ss.id].pop(ws.id, None)

    # -- rule 6: shape at the end of the command -------------------------------
    def _checks_shape(self, ss: "CheckedSpreadsheet") -> bool:
        """Whether rule 6 looks after this spreadsheet in this command: a class
        sheet, a planar or diagnostics Sheet, or a status sheet, written by a command allowed to write (a dry
        run's highlights change no shape)."""
        return self._checks_shape_of(ss.identity)

    @staticmethod
    def _checks_shape_of(identity: Optional[Identity]) -> bool:
        if _context is None or not _context.may_write:
            return False
        return identity is not None and identity.kind in SHEET_KINDS

    def _before_shape_write(self, ss: "CheckedSpreadsheet",
                            ws: Optional["CheckedWorksheet"] = None) -> None:
        """Before a write that can change a class sheet's shape, remember the
        sheet's tabs (and this tab's content) as they are, the first time
        only, so rule 6 blames the command only for what it changed. The tab
        read reuses the command's own where there is one (Q6)."""
        if not self._checks_shape(ss):
            return
        made = ss.id in self._created
        if ss.id not in self._before_sheets:
            self._before_sheets[ss.id] = None if made else self._sheet_layout(ss)
        if ws is not None and ws._key not in self._before_tabs:
            self._before_tabs[ws._key] = None if made else [list(r) for r in self._grid(ws)]

    def _sheet_layout(self, ss: "CheckedSpreadsheet") -> List[Dict[str, Any]]:
        """The spreadsheet's tabs in order: id, title, name (its label, which
        survives a rename by hand, else its title) and whether it is protected."""
        meta = _retry(lambda: ss._inner.fetch_sheet_metadata(params={
            "fields": "sheets(properties(sheetId,title,index),developerMetadata,"
                      "protectedRanges(range))"}))
        sheets = sorted(meta.get("sheets", []), key=lambda s: s["properties"].get("index", 0))
        layout = []
        for sheet in sheets:
            props = sheet["properties"]
            name = next((m.get("metadataValue") for m in sheet.get("developerMetadata", [])
                         if m.get("metadataKey") == TAB_NAME_LABEL), None)
            layout.append({"id": props["sheetId"], "title": props["title"],
                           "name": name or props["title"],
                           "protected": bool(sheet.get("protectedRanges"))})
        return layout

    def _shape_problems(self, ss: "CheckedSpreadsheet") -> List[str]:
        """Rule 6: re-read a class sheet the command changed the shape of and
        compare it with its spec — tab names, order and protection, and for
        each tab it wrote, the header and row keys. Only what does not match
        now and did match before the command first wrote is reported: drift
        that was already there has its own issues (sheet-drift,
        planar-changed, dependent-stale), and a rebuild that fixes some of it
        is not blamed for the rest."""
        if ss.id not in self._before_sheets or self.is_archived(ss.id):
            return []
        identity = ss.identity
        where = identity.describe()
        spec = self._spec(identity)
        if isinstance(spec, Exception):
            return [f"cannot check the shape of {where}: its spec could not be built ({spec})"]
        if identity.kind in COPY_SHEETS:
            return self._copy_shape_problems(ss, spec, where)
        if identity.kind == STATUS_SHEET:
            return self._status_page_shape_problems(ss, spec, where)
        if identity.kind == PROPOSAL_SHEET:
            return self._proposal_shape_problems(ss, spec, where)
        after = self._sheet_layout(ss)
        before = self._before_sheets[ss.id]
        new = _layout_mismatches(spec, after) - (
            _layout_mismatches(spec, before) if before is not None else set())
        by_id = {t["id"]: t for t in after}
        for (sheet_id, tab_id), earlier in self._before_tabs.items():
            if sheet_id != ss.id or tab_id not in by_id:
                continue
            entry = by_id[tab_id]
            try:
                tab = spec.tab(entry["name"])
            except KeyError:
                continue  # not a tab the class has: the layout reports it
            if ss.id in self._replacements and tab.rows is None:
                # A replacement sheet carries a pair or keyed tab's rows over
                # from the sheet it replaces (renames applied); they are not
                # generated, so their staleness against the generator is the
                # dependent-stale check's, as it was before.
                expected = None
            else:
                expected = self._expected_row_keys(identity, tab)
            now =_retry(lambda: ss._inner.worksheet(entry["title"]).get_all_values())
            new |= _tab_mismatches(identity.class_name, tab, now, expected) - (
                _tab_mismatches(identity.class_name, tab, earlier, expected)
                if earlier is not None else set())
        return _describe_mismatches(where, new)

    def _copy_shape_problems(self, ss: "CheckedSpreadsheet", spec, where: str) -> List[str]:
        """Rule 6 for a planar or diagnostics Sheet: one unprotected tab,
        holding exactly its file. As for class sheets, only what is new is
        reported."""
        source, sheet = COPY_SHEETS[spec.kind]
        after = self._sheet_layout(ss)
        before = self._before_sheets[ss.id]
        new = _copy_layout_mismatches(sheet, after) - (
            _copy_layout_mismatches(sheet, before) if before is not None else set())
        first = after[0]["id"] if after else None
        for (sheet_id, tab_id), earlier in self._before_tabs.items():
            if sheet_id != ss.id or tab_id != first:
                continue
            now = _retry(lambda: ss._inner.worksheet(after[0]["title"]).get_all_values())
            new |= _copy_tab_mismatches(source, spec.tab, now) - (
                _copy_tab_mismatches(source, spec.tab, earlier) if earlier is not None else set())
        return _describe_mismatches(where, new)

    def _status_page_shape_problems(self, ss: "CheckedSpreadsheet", spec,
                                    where: str) -> List[str]:
        """Rule 6 for a status sheet: one unprotected tab, ``Status``, whose
        rows under the header name every construction of the diagnostics
        file, in order. The sheet is rebuilt whole each run, so everything
        wrong after the run is reported, not only what is new."""
        after = self._sheet_layout(ss)
        new = _status_page_layout_mismatches(spec.tab.title, after)
        if after and ss.id in {sheet_id for sheet_id, _ in self._before_tabs}:
            now = _retry(lambda: ss._inner.worksheet(after[0]["title"]).get_all_values())
            new |= _status_page_tab_mismatches(spec.tab, now)
        return _describe_mismatches(where, new)

    def _proposal_shape_problems(self, ss: "CheckedSpreadsheet", spec,
                                 where: str) -> List[str]:
        """Rule 6 for a proposal sheet: its four tabs in order, only
        Instructions protected, and each proposal tab the command wrote has its source's
        columns and What changed?. Its rows are the annotator's proposal, so
        they are not compared. Only what is new is reported."""
        after = self._sheet_layout(ss)
        before = self._before_sheets[ss.id]
        new = _layout_mismatches(spec, after) - (
            _layout_mismatches(spec, before) if before is not None else set())
        by_id = {t["id"]: t for t in after}
        for (sheet_id, tab_id), earlier in self._before_tabs.items():
            if sheet_id != ss.id or tab_id not in by_id:
                continue
            try:
                tab = spec.tab(by_id[tab_id]["name"])
            except KeyError:
                continue  # not one of its tabs: the layout reports it
            if tab.kind != PROPOSAL_TAB:
                continue
            title = by_id[tab_id]["title"]
            now = _retry(lambda: ss._inner.worksheet(title).get_all_values())
            new |= _column_mismatches(tab, _header_of(now))
            if earlier is not None:
                new -= _column_mismatches(tab, _header_of(earlier))
        return _describe_mismatches(where, new)

    def _expected_row_keys(self, identity: Identity, tab) -> Optional[frozenset]:
        """The tab's row keys from the generators; None if they can't be
        worked out, in which case rows are not compared (the header still is)."""
        if tab.kind == LOCKED_TAB:
            return None
        from .sheet_spec import expected_row_keys
        try:
            return expected_row_keys(identity.lang_id, identity.class_name, tab, CODED_DATA)
        except Exception:  # noqa: BLE001 - the command's own build of these rows would fail too
            return None

    # -- replacing (rule 1) -------------------------------------------------
    def _before_replacing(self, tab: "CheckedWorksheet", reason: str,
                          kept: Optional[Iterable[Sequence[str]]], allow_drop: bool) -> None:
        """What ``replacing()`` does before its block runs: look for an
        annotator's mid-run edit, save the tab, refuse to drop answered rows."""
        key = tab._key
        fresh = [list(r) for r in _retry(tab._inner.get_all_values)]
        earlier = self._grids.get(key)
        if earlier is not None:
            edited = tab._edits_since(earlier, fresh)
            if edited:
                self._check(f"replace {tab.title!r} of {tab._ss.title!r}", [edited],
                            target=tab._ss.id)
        self._grids[key] = fresh
        _save_snapshot(tab, fresh, reason)
        if kept is None:
            return
        lines = tab._answered_rows_not_kept(fresh, kept)
        if lines and not allow_drop:
            raise AnswersWouldBeDropped(tab.title, lines)

    # -- checking -----------------------------------------------------------
    def _check(self, what: str, problems: Sequence[str] = (),
               target: "Optional[str | Identity]" = None) -> None:
        """Run the always-true checks, plus ``problems`` from the rules, and
        act on them by mode. ``what`` names the write for the message;
        ``target`` is the file written (its id, or the identity of one being
        made), which decides the mode (``_enforces``)."""
        found = list(problems)
        ctx = _context
        if ctx is None:
            found.insert(0, "no command is running, so the door cannot tell whether "
                            "it may write (run it through `python -m coding`)")
        elif not ctx.may_write:
            allowed = [n for n in _always_on_active if n in ctx.always_on]
            if not allowed:
                found.insert(0, f"`{ctx.command}` was run without the flag that lets "
                                "it write to Drive (a dry run), but tried to write")
        self._act(what, found, target)

    def _mode_label(self) -> str:
        """The mode, for the one line a command prints about the door."""
        if self.mode == ENFORCE or not LIVE_ENFORCED_KINDS:
            return self.mode
        return f"{self.mode}; enforce for {', '.join(sorted(LIVE_ENFORCED_KINDS))}"

    def _enforces(self, target: "Optional[str | Identity]") -> bool:
        """Whether a broken rule on ``target`` raises: always in enforce mode
        (tests), and live for a kind in LIVE_ENFORCED_KINDS."""
        if self.mode == ENFORCE:
            return True
        identity = target if isinstance(target, Identity) else (
            self._identify(target) if target else None)
        return identity is not None and identity.kind in LIVE_ENFORCED_KINDS

    def _act(self, what: str, problems: Sequence[str],
             target: "Optional[str | Identity]" = None) -> None:
        """Act on broken rules by mode: raise (enforce) or remember (watch)."""
        if not problems:
            return
        command = _context.command if _context else "(no command)"
        messages = [f"{command}: {what}: {p}" for p in problems]
        if self._enforces(target):
            raise DoorViolation("The Drive door refused a write.\n  " + "\n  ".join(messages))
        self.violations.extend(messages)

    def _spec(self, identity: Identity):
        """The spec of a class sheet, a planar or diagnostics Sheet, a status
        sheet or a proposal sheet, or the error that stopped it being built."""
        key = (identity.kind, identity.lang_id, identity.class_name)
        if key not in self._specs:
            from .sheet_spec import (class_sheet_spec, copy_sheet_spec, proposal_sheet_spec,
                                     status_sheet_spec)
            try:
                if identity.kind == CLASS_SHEET:
                    spec = class_sheet_spec(identity.lang_id, identity.class_name, CODED_DATA)
                elif identity.kind in COPY_SHEETS:
                    spec = copy_sheet_spec(identity.kind, identity.lang_id, CODED_DATA)
                elif identity.kind == STATUS_SHEET:
                    spec = status_sheet_spec(identity.lang_id, CODED_DATA)
                elif identity.kind == PROPOSAL_SHEET:
                    spec = proposal_sheet_spec(identity.lang_id, CODED_DATA)
                else:
                    raise ValueError(f"no spec for a {identity.kind} yet")
                self._specs[key] = spec
            except Exception as exc:  # noqa: BLE001 - reported as a violation
                self._specs[key] = exc
        return self._specs[key]

    # -- the cached view of a tab --------------------------------------------
    def _grid(self, ws: "CheckedWorksheet") -> List[List[str]]:
        key = ws._key
        if key not in self._grids:
            values = _retry(ws._inner.get_all_values)
            self._grids[key] = [list(r) for r in values]
        return self._grids[key]

    def _forget(self, key: Tuple[str, int]) -> None:
        self._grids.pop(key, None)

    # -- reads --------------------------------------------------------------
    def open_spreadsheet(self, spreadsheet_id: str) -> "CheckedSpreadsheet":
        inner = _retry(lambda: self._inner.open_spreadsheet(spreadsheet_id))
        return CheckedSpreadsheet(self, inner)

    def list_files(self, q: str, fields: str = "files(id, name)",
                   page_size: Optional[int] = None) -> List[Dict]:
        return _retry(lambda: self._inner.list_files(q, fields=fields, page_size=page_size))

    def get_file(self, file_id: str, fields: str = "id",
                 supports_all_drives: bool = False) -> Dict:
        return _retry(lambda: self._inner.get_file(
            file_id, fields=fields, supports_all_drives=supports_all_drives))

    def list_permissions(self, file_id: str,
                         fields: str = "permissions(id,type)") -> List[Dict]:
        return _retry(lambda: self._inner.list_permissions(file_id, fields=fields))

    def get_doc_text(self, doc_id: str) -> str:
        return _retry(lambda: self._inner.get_doc_text(doc_id))

    def list_comments(self, file_id: str) -> List[Dict]:
        return _retry(lambda: self._inner.list_comments(file_id))

    # -- creating -----------------------------------------------------------
    def _same_named(self, name: str, mimetype: Optional[str],
                    parents: Optional[Sequence[str]]) -> set:
        clauses = [f"name='{_quote(name)}'", "trashed=false"]
        if mimetype:
            clauses.append(f"mimeType='{mimetype}'")
        if parents:
            clauses.append(f"'{parents[0]}' in parents")
        return {f["id"] for f in self.list_files(" and ".join(clauses))}

    def _create(self, make: Callable[[], Any], name: str, mimetype: Optional[str],
                parents: Optional[Sequence[str]], from_id: Callable[[str], Any]) -> Any:
        """Create once: before a retry, look for a same-named file that wasn't
        there before the first attempt."""
        before = self._same_named(name, mimetype, parents)

        def landed():
            new = self._same_named(name, mimetype, parents) - before
            return from_id(sorted(new)[0]) if new else None

        return _retry(make, landed=landed)

    # Every create says what it is making (``identity``), and the door writes
    # that as the new file's label: a file the tooling made is never unplaced.
    def _made(self, file_id: str, identity: Identity) -> None:
        self._created[file_id] = identity
        self._labels[file_id] = dict(identity.labels())

    def create_spreadsheet(self, title: str, *, identity: Identity,
                           replaces: Optional[str] = None):
        """Make a spreadsheet labelled ``identity``. ``replaces``: the id of
        the sheet this one takes over from (restructure-sheets), whose tab
        list rule 6 takes as the "before", and whose pair and keyed rows the
        new sheet carries over rather than generates (see _shape_problems)."""
        self._check(f"create spreadsheet {title!r}", target=identity)
        old_layout = None
        if replaces is not None and self._checks_shape_of(identity):
            old_layout = self._sheet_layout(self.open_spreadsheet(replaces))
        inner = self._create(lambda: self._inner.create_spreadsheet(title), title,
                             _SPREADSHEET_MIME, None, self._inner.open_spreadsheet)
        # Sheets can't be given Drive properties when made; label straight after.
        _retry(lambda: self._inner.update_file(inner.id, properties=identity.labels()))
        self._made(inner.id, identity)
        self._wrote_file(inner.id, title, "create_spreadsheet")
        ss = CheckedSpreadsheet(self, inner)
        self._wrote_sheet(ss)
        self._before_shape_write(ss)   # a new sheet: all of its shape is this command's
        if replaces is not None and self._checks_shape(ss):
            self._before_sheets[ss.id] = old_layout
            self._replacements[ss.id] = replaces
        return ss

    def create_file(self, name: str, parents: Optional[Sequence[str]] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None, *, identity: Identity) -> str:
        self._check(f"create file {name!r}",
                    self._file_problems(identity, name=name, parents=parents or [],
                                        mimetype=mimetype, content=content, creating=True),
                    target=identity)
        file_id = self._create(
            lambda: self._inner.create_file(name, parents=parents, content=content,
                                            mimetype=mimetype, properties=identity.labels()),
            name, mimetype if content is None else None, parents, lambda fid: fid)
        self._made(file_id, identity)
        self._wrote_file(file_id, name, "create_file")
        return file_id

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None, *,
                             identity: Identity) -> str:
        if identity.kind != "folder":
            raise ValueError(f"get_or_create_folder makes folders, not a {identity.kind}")
        parent_clause = f" and '{parent_id}' in parents" if parent_id else ""
        found = self.list_files(f"name='{_quote(name)}' and mimeType='{_FOLDER_MIME}' "
                                f"and trashed=false{parent_clause}")
        if found:
            self._check_found(found[0]["id"], identity, f"find folder {name!r}")
            return found[0]["id"]
        return self.create_file(name, [parent_id] if parent_id else [], mimetype=_FOLDER_MIME,
                                identity=identity)

    def create_doc(self, name: str, parent_id: str, *, identity: Identity) -> str:
        self._check(f"create doc {name!r}",
                    self._file_problems(identity, name=name, parents=[parent_id],
                                        mimetype=_DOC_MIME, creating=True),
                    target=identity)
        doc_id = self._create(
            lambda: self._inner.create_doc(name, parent_id, properties=identity.labels()),
            name, _DOC_MIME, [parent_id], lambda fid: fid)
        self._made(doc_id, identity)
        self._wrote_file(doc_id, name, "create_doc")
        return doc_id

    # -- other file writes --------------------------------------------------
    def update_file(self, file_id: str, name: Optional[str] = None,
                    content: Optional[bytes] = None,
                    mimetype: Optional[str] = None) -> None:
        self._check(f"update file {file_id}",
                    self._file_problems(self._identify(file_id), name=name,
                                        mimetype=mimetype, content=content),
                    target=file_id)
        _retry(lambda: self._inner.update_file(file_id, name=name, content=content,
                                               mimetype=mimetype))
        self._wrote_file(file_id, name or "", "update_file")

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        self._check(f"move file {file_id}",
                    self._file_problems(self._identify(file_id), parents=[new_parent_id]),
                    target=file_id)
        _retry(lambda: self._inner.move_file(file_id, new_parent_id))
        self._wrote_file(file_id, "", "move_file")

    def trash_file(self, file_id: str) -> None:
        identity = self._identify(file_id)
        problems = [] if identity is not None and identity.kind in TRASHABLE_KINDS else [
            f"only a {' or '.join(sorted(TRASHABLE_KINDS))} goes to the trash, not "
            f"{identity.describe() if identity else 'a file with no label'}"]
        self._check(f"trash file {file_id}", problems, target=file_id)
        _retry(lambda: self._inner.trash_file(file_id))
        self._wrote_file(file_id, "", "trash_file")

    def append_doc_text(self, doc_id: str, text: str) -> None:
        self._check(f"append to doc {doc_id}", self._appended_text_problems(doc_id, text),
                    target=doc_id)
        _retry(lambda: self._inner.append_doc_text(doc_id, text))
        self._wrote_file(doc_id, "", "append_doc_text")

    # -- files that are not spreadsheets (rule 8) -----------------------------
    def _file_problems(self, identity: Optional[Identity], *, name: Optional[str] = None,
                       parents: Optional[Sequence[str]] = None,
                       mimetype: Optional[str] = None, content: Optional[bytes] = None,
                       creating: bool = False) -> List[str]:
        """What is wrong with a write to a notes Doc, report, charts PDF,
        notebook or folder, from its spec (``sheet_spec.file_spec``): each
        part the write sends (name, folder, type, content) must be the
        spec's, and a file only one of which may exist is not made twice.
        Nothing for a spreadsheet, or a file the door can't place."""
        if identity is None or identity.kind not in FILE_KINDS:
            return []
        from .sheet_spec import content_problems, file_spec
        spec = file_spec(identity)
        what = identity.describe()
        out = []
        if name is not None and name != spec.name:
            out.append(f"{what} is called {spec.name!r}, not {name!r}")
        if mimetype is not None and mimetype != spec.mimetype:
            out.append(f"{what} is a {spec.mimetype} file, not {mimetype}")
        if content is not None:
            out += [f"{what}: {p}" for p in content_problems(spec, content)]
        if parents is not None:
            out += self._folder_problems(what, spec.folder, parents)
        if creating and spec.one_only:
            out += self._duplicate_problems(identity)
        return out

    def _folder_problems(self, what: str, wanted: Optional[Identity],
                         parents: Sequence[str]) -> List[str]:
        """A file sits in the folder its spec names (``wanted``), or, for
        None, in none of the project's folders."""
        found = [self._identify(p) for p in parents]
        if wanted is None:
            inside = [f for f in found if f is not None]
            return [f"{what} sits outside the project's folders, not in "
                    f"{inside[0].describe()}"] if inside else []
        if found != [wanted]:
            shown = ", ".join(f.describe() if f else "a folder with no label"
                              for f in found) or "no folder"
            return [f"{what} sits in {wanted.describe()}, not {shown}"]
        return []

    def _duplicate_problems(self, identity: Identity) -> List[str]:
        """A second live file with this identity: the commands keep the first
        one's id (drive_config.json), so a second would be found by
        no one, and a notes Doc's notes would be split between the two."""
        clauses = [f"properties has {{ key='{k}' and value='{_quote(v)}' }}"
                   for k, v in identity.labels().items()] + ["trashed=false"]
        for f in self.list_files(" and ".join(clauses), fields="files(id, name, properties)"):
            labels = f.get("properties") or {}
            if labels.get(STATE_LABEL) != ARCHIVED and Identity.from_labels(labels) == identity:
                return [f"{identity.describe()} already exists ({f['id']}); "
                        "making a second one would leave one of them unused"]
        return []

    def _appended_text_problems(self, doc_id: str, text: str) -> List[str]:
        """Only a notes Doc takes appended text, and only an acknowledgment
        line (``sheet_spec.appended_text_problems``)."""
        identity = self._identify(doc_id)
        if identity is None:
            return []
        if identity.kind not in FILE_KINDS:
            return [f"text is appended only to notes Docs, not to {identity.describe()}"]
        from .sheet_spec import appended_text_problems, file_spec
        return [f"{identity.describe()}: {p}"
                for p in appended_text_problems(file_spec(identity), text)]

    # -- sharing (rule 5) ----------------------------------------------------
    def _sharing(self, file_id: str):
        """The file's identity and sharing spec, or (None, None) if the door
        can't place it."""
        identity = self._identify(file_id)
        if identity is None:
            return None, None
        from .sheet_spec import sharing_spec
        return identity, sharing_spec(identity, archived=self.is_archived(file_id))

    def _sharing_problems(self, file_id: str, type: str, email: Optional[str],
                          role: str) -> List[str]:
        """What is wrong with ``file_id`` holding this grant (rule 5)."""
        identity, spec = self._sharing(file_id)
        if spec is None:
            return []
        state = "archived" if self.is_archived(file_id) else "live"
        what = f"{identity.describe()} ({state})"
        if type == "anyone":
            if spec.link is None:
                return [f"{what} is shared with named people only, not by link"]
            if role != spec.link:
                return [f"a link to {what} gives {spec.link}, not {role}"]
            return []
        if type != "user":
            return [f"{what} is shared with named people only, not {type!r}"]
        wanted = spec.role_for(email)
        if wanted is None:
            return [f"{what} is not shared with this address: the sharing spec "
                    "(coding/sheet_spec.py) names "
                    + (f"{len(spec.people)} person(s), from people.yaml" if spec.people
                       else "nobody")]
        if role != wanted:
            return [f"{what}: this person is a {wanted}, not a {role}"]
        return []

    def _removal_problems(self, file_id: str, permission_id: str) -> List[str]:
        """What is wrong with removing this grant: the spec calls for it."""
        identity, spec = self._sharing(file_id)
        if spec is None:
            return []
        grant = next((p for p in self.list_permissions(
            file_id, fields="permissions(id,type,emailAddress)")
            if p.get("id") == permission_id), None)
        if grant is None:
            return []
        if grant.get("type") == "anyone" and spec.link is not None:
            return [f"{identity.describe()}'s link share is in its sharing spec; "
                    "removing it is not"]
        if grant.get("type") == "user" and spec.role_for(grant.get("emailAddress")):
            return [f"{identity.describe()} is shared with this person by its sharing "
                    "spec; removing the grant is not"]
        return []

    def create_permission(self, file_id: str, type: str, role: str,
                          email: Optional[str] = None, notify: bool = False) -> str:
        self._check(f"share {file_id} ({type}, {role})",
                    self._sharing_problems(file_id, type, email, role), target=file_id)

        def landed():
            for p in self.list_permissions(file_id, fields="permissions(id,type,emailAddress)"):
                if p.get("type") == type and (type != "user" or p.get("emailAddress") == email):
                    return p["id"]
            return None

        permission_id = _retry(lambda: self._inner.create_permission(
            file_id, type=type, role=role, email=email, notify=notify), landed=landed)
        self._wrote_file(file_id, "", "create_permission")
        return permission_id

    def delete_permission(self, file_id: str, permission_id: str) -> None:
        self._check(f"remove a grant on {file_id}",
                    self._removal_problems(file_id, permission_id), target=file_id)
        _retry(lambda: self._inner.delete_permission(file_id, permission_id))
        self._wrote_file(file_id, "", "delete_permission")

    def update_permission(self, file_id: str, permission_id: str, role: str) -> None:
        problems: List[str] = []
        if self._identify(file_id) is not None:
            grant = next((p for p in self.list_permissions(
                file_id, fields="permissions(id,type,emailAddress)")
                if p.get("id") == permission_id), None)
            if grant is not None:
                problems = self._sharing_problems(file_id, grant.get("type", ""),
                                                  grant.get("emailAddress"), role)
        self._check(f"change a grant on {file_id} to {role}", problems, target=file_id)
        _retry(lambda: self._inner.update_permission(file_id, permission_id, role))
        self._wrote_file(file_id, "", "update_permission")

    # -- comments (rule 7) ---------------------------------------------------
    def _comment_problems(self, file_id: str, content: str) -> List[str]:
        """A comment goes only on a class sheet, and may mention (``+address``,
        which makes Google email that person) only the sheet's own annotator."""
        identity = self._identify(file_id)
        if identity is None or identity.kind != CLASS_SHEET:
            return [f"comments go only on class sheets; {file_id} is not one the door "
                    "can place"]
        from .people import annotator_email
        expected = annotator_email(identity.lang_id)
        others = sorted({m for m in _MENTION.findall(content) if m != expected})
        if others:
            return [f"a comment on {identity.describe()} may mention only "
                    f"{identity.lang_id}'s annotator (languages.yaml, people.yaml), not "
                    f"{len(others)} other address(es)"]
        return []

    def create_comment(self, file_id: str, content: str) -> str:
        self._check(f"comment on {file_id}", self._comment_problems(file_id, content),
                    target=file_id)

        def landed():
            for c in self.list_comments(file_id):
                if c.get("content") == content:
                    return c["id"]
            return None

        comment_id = _retry(lambda: self._inner.create_comment(file_id, content), landed=landed)
        self._wrote_file(file_id, "", "create_comment")
        return comment_id


def _quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


# ---------------------------------------------------------------------------
# Rule 6: how a class sheet differs from its spec, as a set of mismatches
# ---------------------------------------------------------------------------
# Each mismatch is (what, tab, detail). Sets, so that a command is blamed
# only for mismatches that were not there before it wrote.

def _layout_mismatches(spec, layout: List[Dict[str, Any]]) -> set:
    """Tabs missing, extra, out of order, or protected when they shouldn't be
    (or not when they should)."""
    titles = spec.tab_titles
    names = [t["name"] for t in layout]
    out = {("tab missing", t, "") for t in titles if t not in names}
    out |= {("tab the class does not have", t["title"], "") for t in layout
            if t["name"] not in titles}
    present = tuple(n for n in names if n in titles)
    if present != tuple(t for t in titles if t in names):
        out.add(("tabs out of order", "", " | ".join(present)))
    for t in layout:
        if t["name"] in titles:
            wanted = spec.tab(t["name"]).protected
            if t["protected"] != wanted:
                out.add(("not protected" if wanted else "protected, but only locked tabs are",
                         t["name"], ""))
    return out


def _tab_mismatches(class_name: str, tab, grid: List[List[Any]],
                    expected: Optional[frozenset]) -> set:
    """A locked tab's content, or a construction or Status tab's columns and
    row keys (when ``expected`` is known), against the spec."""
    rows = _trimmed([[_text(v) for v in r] for r in grid])
    if tab.kind == LOCKED_TAB:
        want = _trimmed([[_text(v) for v in r] for r in tab.rows or ()])
        return set() if rows == want else {("content differs from what its builder makes",
                                            tab.title, "")}
    from .sheet_spec import counts_as_generated, parked_operation
    header = rows[0] if rows else []
    out = _column_mismatches(tab, header, allowed_extra=parked_operation)
    if expected is None or any(k not in header for k in tab.row_key):
        return out
    want = {tuple(v.strip() for v in key) for key in expected}
    seen: set = set()
    for raw in rows[1:]:
        if not any(v.strip() for v in raw):
            continue
        record = dict(zip(header, raw))
        if not counts_as_generated(class_name, tab.title, record):
            continue
        key = tuple(record.get(k, "").strip() for k in tab.row_key)
        if key in seen:
            out.add(("row twice", tab.title, _key_text(tab.row_key, key)))
        seen.add(key)
    out |= {("row missing", tab.title, _key_text(tab.row_key, k)) for k in want - seen}
    out |= {("row the spec does not have", tab.title, _key_text(tab.row_key, k))
            for k in seen - want}
    return out


def _column_mismatches(tab, header: Sequence[str],
                       allowed_extra: Callable[[str], Any] = lambda c: False) -> set:
    """Columns missing, extra (unless ``allowed_extra`` says the column may
    be there) or out of order, against the tab's spec."""
    out = {("column missing", tab.title, c) for c in tab.header if c not in header}
    out |= {("column the spec does not have", tab.title, c) for c in header
            if c and c not in tab.header and not allowed_extra(c)}
    common = tuple(c for c in header if c in tab.header)
    if common != tuple(c for c in tab.header if c in header):
        out.add(("columns out of order", tab.title, " | ".join(common)))
    return out


def _header_of(grid: List[List[Any]]) -> List[str]:
    rows = _trimmed([[_text(v) for v in r] for r in grid])
    return rows[0] if rows else []


def _copy_layout_mismatches(sheet: str, layout: List[Dict[str, Any]]) -> set:
    """A planar or diagnostics Sheet (``sheet`` names it) has one tab, and it
    is protected (a read-only copy: coordinators, writers on the root folder,
    would otherwise be able to edit it)."""
    out = {(f"tab {sheet} does not have", t["title"], "") for t in layout[1:]}
    out |= {(f"not protected, but {sheet} is a read-only copy", t["title"], "")
            for t in layout[:1] if not t["protected"]}
    return out


def _copy_tab_mismatches(source: str, tab, grid: List[List[Any]]) -> set:
    """A planar or diagnostics Sheet's tab against its file (``source`` names
    it): its columns, then its rows, read by column name (a column moved in
    the Sheet moves its values with it), compared stripped and in order, as
    the imports compare them."""
    rows = _trimmed([[_text(v) for v in r] for r in grid])
    header = rows[0] if rows else []
    out = {(what, "", detail) for what, _, detail in _column_mismatches(tab, header)}
    have = [tuple(dict(zip(header, r)).get(c, "").strip() for c in tab.header)
            for r in rows[1:] if any(v.strip() for v in r)]
    want = list(tab.rows or ())

    def describe(row):
        rec = dict(zip(tab.header, row))
        if "Position" in rec:
            return f"position {rec['Position']} ({rec.get('Position_Name', '')})"
        if "Class" in rec:
            return f"class {rec['Class']} ({rec.get('Constructions', '')})"
        return " | ".join(row)

    missing = [r for r in want if r not in have]
    extra = [r for r in have if r not in want]
    out |= {(f"row of {source} missing", "", describe(r)) for r in missing}
    out |= {(f"row {source} does not have", "", describe(r)) for r in extra}
    if not missing and not extra and have != want:
        out.add(("rows out of order or repeated", "", ""))
    return out


def _status_page_layout_mismatches(title: str, layout: List[Dict[str, Any]]) -> set:
    """A status sheet has one tab, called ``title``, and nothing protected:
    annotators can only read it because they are shared as readers."""
    out = {("tab a status sheet does not have", t["title"], "") for t in layout[1:]}
    if layout and layout[0]["title"] != title:
        out.add(("tab not named " + repr(title), layout[0]["title"], ""))
    out |= {("protected, but a status sheet is read-only by sharing", t["title"], "")
            for t in layout if t["protected"]}
    return out


# A cell holding =HYPERLINK("url", "label"): what Sheets shows is the label.
# A live read returns the label; the offline Drive returns the formula.
_HYPERLINK = re.compile(r'^=HYPERLINK\("[^"]*",\s*"([^"]*)"\)$')


def _shown(value: str) -> str:
    m = _HYPERLINK.match(value)
    return m.group(1) if m else value


def _status_page_tab_mismatches(tab, grid: List[List[Any]]) -> set:
    """The status sheet's tab against its spec: a header row equal to the
    spec's columns (after the banner), then one row per (class, construction)
    in the spec's order, each with a status filled in."""
    rows = _trimmed([[_text(v) for v in r] for r in grid])
    header = list(tab.header)
    at = next((i for i, r in enumerate(rows) if r == header), None)
    if at is None:
        return {("no header row", "", " | ".join(header))}
    have = [tuple(_shown(v).strip() for v in (r + [""] * len(header))[:2])
            for r in rows[at + 1:]]
    want = list(tab.rows or ())
    out = {("construction missing", "", f"{c} / {k}") for c, k in want if (c, k) not in have}
    out |= {("row the diagnostics file does not have", "", " / ".join(r))
            for r in have if r not in want}
    if not out and have != want:
        out.add(("rows out of order or repeated", "", ""))
    out |= {("no status shown", "", " / ".join(_shown(v) for v in r[:2]))
            for r in rows[at + 1:] if len(r) < 3 or not r[2].strip()}
    return out


def _key_text(columns: Sequence[str], key: Sequence[str]) -> str:
    return ", ".join(f"{c} {v!r}" for c, v in zip(columns, key))


def _describe_mismatches(where: str, mismatches: set, shown: int = 3) -> List[str]:
    """One line per kind of mismatch per tab, with a count and the first few."""
    groups: Dict[Tuple[str, str], List[str]] = {}
    for what, tab, detail in sorted(mismatches):
        groups.setdefault((what, tab), []).append(detail)
    lines = []
    for (what, tab), details in groups.items():
        place = f"{where}/{tab}" if tab else where
        count = f" ({len(details)})" if len(details) > 1 else ""
        named = [d for d in details if d]
        listed = ("; ".join(named[:shown])
                  + (f"; and {len(named) - shown} more" if len(named) > shown else ""))
        lines.append(f"{place}: {what}{count}" + (f": {listed}" if listed else "")
                     + " (new with this command)")
    return lines


# ---------------------------------------------------------------------------
# Spreadsheet and tab handles
# ---------------------------------------------------------------------------

class CheckedSpreadsheet:
    """One spreadsheet, as a command holds it."""

    def __init__(self, door: CheckedDoorway, inner) -> None:
        self._door = door
        self._inner = inner

    @property
    def id(self) -> str:
        return self._inner.id

    @property
    def title(self) -> str:
        return self._inner.title

    @property
    def url(self) -> str:
        return self._inner.url

    @property
    def identity(self) -> Optional[Identity]:
        return self._door._identify(self._inner.id)

    def _wrap(self, ws) -> "CheckedWorksheet":
        return CheckedWorksheet(self, ws)

    # -- reads --------------------------------------------------------------
    @property
    def sheet1(self) -> "CheckedWorksheet":
        return self._wrap(_retry(lambda: self._inner.sheet1))

    def worksheets(self) -> List["CheckedWorksheet"]:
        return [self._wrap(ws) for ws in _retry(self._inner.worksheets)]

    def worksheet(self, title: str) -> "CheckedWorksheet":
        return self._wrap(_retry(lambda: self._inner.worksheet(title)))

    def list_protected_ranges(self, sheetid: int) -> List[Dict[str, Any]]:
        return _retry(lambda: self._inner.list_protected_ranges(sheetid))

    def values_batch_get(self, ranges: List[str],
                         params: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return _retry(lambda: self._inner.values_batch_get(ranges, params=params))

    def fetch_sheet_metadata(self, params: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return _retry(lambda: self._inner.fetch_sheet_metadata(params=params))

    def construction_tabs(self) -> List[str]:
        """The constructions this class sheet has a tab for, in tab order:
        each tab labelled as a construction, by its name label (the
        construction, which stays put if someone renames the tab by hand).
        What the sheet holds, as opposed to what the diagnostics YAML says it
        should (unit 11c: this replaced the manifest's ``constructions``).

        The door labels the tabs a command makes or renames only when the
        command ends, so mid-command a tab with no label yet counts, by its
        title, when the sheet's spec lists it as a construction
        (``unlabelled_tabs``). Any other unlabelled tab is not the tooling's."""
        new = {ws.id: ws.title for ws, kind in self._door.unlabelled_tabs(self)
               if kind == CONSTRUCTION_TAB}
        labels = self._door._tab_labels_of(self)
        names = []
        for ws in _retry(self._inner.worksheets):
            label = labels.get(ws.id, {})
            if label.get(TAB_KIND_LABEL) == CONSTRUCTION_TAB and label.get(TAB_NAME_LABEL):
                names.append(label[TAB_NAME_LABEL])
            elif ws.id in new:
                names.append(new[ws.id])
        return names

    def _tab_by_sheet_id(self, sheet_id: int) -> Optional["CheckedWorksheet"]:
        """The tab a request names. The door keeps each spreadsheet's tabs for
        the command and re-reads them only for an id it hasn't seen: one read
        per request would exhaust Google's per-minute read quota when a
        command sends one request per highlighted cell (#306)."""
        tabs = self._door._tabs.get(self.id)
        if tabs is None or sheet_id not in tabs:
            tabs = {ws.id: ws for ws in _retry(self._inner.worksheets)}
            self._door._tabs[self.id] = tabs
        inner = tabs.get(sheet_id)
        return self._wrap(inner) if inner is not None else None

    # -- tab writes ----------------------------------------------------------
    def add_worksheet(self, title: str, rows: int, cols: int,
                      index: Optional[int] = None) -> "CheckedWorksheet":
        self._door._check(f"add tab {title!r} to {self.title!r}", target=self.id)
        self._door._before_shape_write(self)
        ws = self._wrap(_create_tab(self, title, rows, cols, index))
        if self._door._checks_shape(self):
            self._door._before_tabs.setdefault(ws._key, None)
        self._door._forget(ws._key)
        ws._note("add_worksheet")
        return ws

    def del_worksheet(self, worksheet: "CheckedWorksheet") -> Any:
        tab = _unwrap_tab(worksheet)
        self._door._before_shape_write(self, worksheet)
        problems = worksheet._annotation_loss_problems("delete the tab", all_cells=True)
        self._door._check(f"delete tab {worksheet.title!r} of {self.title!r}", problems,
                          target=self.id)
        result = _retry(lambda: self._inner.del_worksheet(tab))
        self._door._forget(worksheet._key)
        self._door._tab_labels.get(self.id, {}).pop(worksheet.id, None)
        self._door._tabs.get(self.id, {}).pop(worksheet.id, None)
        worksheet._note("del_worksheet")
        return result

    def reorder_worksheets(self, worksheets_in_desired_order: Sequence["CheckedWorksheet"]) -> Any:
        self._door._check(f"reorder the tabs of {self.title!r}", target=self.id)
        self._door._before_shape_write(self)
        tabs = [_unwrap_tab(w) for w in worksheets_in_desired_order]
        result = _retry(lambda: self._inner.reorder_worksheets(tabs))
        self._door._wrote(self.id, self.title, None, "reorder_worksheets",
                          identity=self.identity)
        self._door._wrote_sheet(self)
        return result

    # -- batch endpoints ----------------------------------------------------
    def batch_update(self, body: Mapping[str, Any]) -> Any:
        problems: List[str] = []
        touched: List[Tuple[str, int]] = []
        hit: Dict[Optional[int], Tuple[Optional["CheckedWorksheet"], int]] = {}
        for request in body.get("requests", []):
            problems.extend(self._request_problems(request, touched, hit))
        self._door._check(f"batch update of {self.title!r}", problems, target=self.id)
        result = _retry(lambda: self._inner.batch_update(body))
        for key in touched:
            self._door._forget(key)
        for ws, cells in hit.values():
            if ws is None:
                self._door._wrote(self.id, self.title, None, "batch_update",
                                  identity=self.identity)
                self._door._wrote_sheet(self)
            else:
                ws._note("batch_update", cells)
        return result

    def values_batch_update(self, body: Mapping[str, Any]) -> Any:
        problems: List[str] = []
        writes: List[Tuple["CheckedWorksheet", Dict[Tuple[int, int], str]]] = []
        tabs: Dict[Optional[str], CheckedWorksheet] = {}   # one lookup per tab, not per cell
        for entry in body.get("data", []):
            rng = entry["range"]
            prefix = (rng.rsplit("!", 1)[0].strip("'").replace("''", "'")
                      if "!" in rng else None)
            if prefix not in tabs:
                # A bare range goes to the first tab, as the values API sends it.
                tabs[prefix] = self.worksheet(prefix) if prefix else self.sheet1
            ws = tabs[prefix]
            r0, c0 = _anchor(rng)
            changes = {(r0 + i, c0 + j): _text(v)
                       for i, row in enumerate(entry["values"]) for j, v in enumerate(row)}
            self._door._before_shape_write(self, ws)
            problems.extend(ws._value_problems(changes))
            writes.append((ws, changes))
        self._door._check(f"write values in {self.title!r}", problems, target=self.id)
        result = _retry(lambda: self._inner.values_batch_update(body))
        for ws, changes in writes:
            ws._apply(changes)
            ws._note("values_batch_update", len(changes))
        return result

    def _request_problems(self, request: Mapping[str, Any], touched: List[Tuple[str, int]],
                          hit: Dict[Optional[int], Tuple[Optional["CheckedWorksheet"], int]],
                          ) -> List[str]:
        if len(request) != 1:
            return [f"a request must name exactly one operation: {sorted(request)}"]
        (kind, payload), = request.items()
        if kind not in REQUEST_TYPES:
            return [f"the door does not know the {kind!r} request; add it, with its "
                    "check, to drive_door.REQUEST_TYPES"]
        sheet_id = _request_sheet_id(kind, payload)
        ws = self._tab_by_sheet_id(sheet_id) if sheet_id is not None else None
        cells = 0
        if kind == "updateCells":
            cells = sum(len(row.get("values", [])) for row in payload.get("rows", []))
        prior_ws, prior_cells = hit.get(sheet_id if ws is not None else None, (ws, 0))
        hit[sheet_id if ws is not None else None] = (prior_ws, prior_cells + cells)
        if ws is None:
            return []
        if kind == "setDataValidation":
            return ws._dropdown_problems(payload)
        if kind == "addProtectedRange":
            self._door._before_shape_write(self)
            return ws._protection_problems()
        if kind == "deleteDimension":
            self._door._before_shape_write(self, ws)
            touched.append(ws._key)
            rng = payload["range"]
            return ws._dimension_loss_problems(rng["dimension"], rng["startIndex"], rng["endIndex"])
        if kind == "insertDimension":
            self._door._before_shape_write(self, ws)
            touched.append(ws._key)
            return []
        if kind == "updateSheetProperties":
            if any(f in payload.get("fields", "*") for f in ("*", "title", "index")):
                self._door._before_shape_write(self)  # a rename or a move, not freezing rows
            touched.append(ws._key)
            return []
        if kind == "updateCells":
            fields = payload.get("fields", "*")
            if "*" not in fields and "userEnteredValue" not in fields:
                return []
            self._door._before_shape_write(self, ws)
            touched.append(ws._key)
            rng = payload["range"]
            r0, c0 = rng.get("startRowIndex", 0), rng.get("startColumnIndex", 0)
            changes = {}
            for i, row in enumerate(payload.get("rows", [])):
                for j, cell in enumerate(row.get("values", [])):
                    if "userEnteredValue" in cell:
                        entered = cell["userEnteredValue"]
                        changes[(r0 + i, c0 + j)] = _text(
                            entered.get("stringValue", entered.get("formulaValue", "")))
            return ws._value_problems(changes)
        return []  # formatting: repeatCell, mergeCells, unmergeCells, updateDimensionProperties


def _request_sheet_id(kind: str, payload: Mapping[str, Any]) -> Optional[int]:
    if kind == "updateSheetProperties":
        return payload.get("properties", {}).get("sheetId")
    if kind == "addProtectedRange":
        return payload.get("protectedRange", {}).get("range", {}).get("sheetId")
    return payload.get("range", {}).get("sheetId")


def _unwrap_tab(worksheet):
    if not isinstance(worksheet, CheckedWorksheet):
        raise TypeError("pass the tab handle the Drive door gave you")
    return worksheet._inner


class CheckedWorksheet:
    """One tab, as a command holds it."""

    def __init__(self, spreadsheet: CheckedSpreadsheet, inner) -> None:
        self._ss = spreadsheet
        self._door = spreadsheet._door
        self._inner = inner

    # -- plain properties ---------------------------------------------------
    @property
    def id(self) -> int:
        return self._inner.id

    @property
    def title(self) -> str:
        return self._inner.title

    @property
    def row_count(self) -> int:
        return self._inner.row_count

    @property
    def col_count(self) -> int:
        return self._inner.col_count

    @property
    def spreadsheet(self) -> CheckedSpreadsheet:
        return self._ss

    @property
    def _key(self) -> Tuple[str, int]:
        return (self._ss.id, self._inner.id)

    # -- reads --------------------------------------------------------------
    def get_all_values(self) -> List[List[str]]:
        values = _retry(self._inner.get_all_values)
        self._door._grids[self._key] = [list(r) for r in values]
        return values

    def row_values(self, row: int) -> List[str]:
        return _retry(lambda: self._inner.row_values(row))

    # -- what this tab is -----------------------------------------------------
    def _label(self) -> Dict[str, str]:
        """This tab's labels ({} if it has none, or its sheet isn't a class sheet)."""
        identity = self._ss.identity
        if identity is None or identity.kind != CLASS_SHEET:
            return {}
        return self._door._tab_labels_of(self._ss).get(self.id, {})

    def _name(self) -> str:
        """What the tab is called in the spec: its name label, which survives
        a rename by hand, or else its title."""
        return self._label().get(TAB_NAME_LABEL) or self.title

    def _kind(self) -> Tuple[Optional[str], Any]:
        """(tab kind, spec-or-error) for a tab of a class sheet (from the
        tab's label, else its title), of a planar or diagnostics Sheet, of a
        status sheet, or of a proposal sheet (by title); (None, None) for a
        tab of a spreadsheet whose contents have no spec yet."""
        identity = self._ss.identity
        if identity is not None and identity.kind in COPY_SHEETS:
            return COPY_TAB, None
        if identity is not None and identity.kind == STATUS_SHEET:
            return STATUS_PAGE_TAB, None
        if identity is not None and identity.kind == PROPOSAL_SHEET:
            from .sheet_spec import PROPOSAL_INSTRUCTIONS_TAB, REVIEW_TAB_TITLE
            if self.title == PROPOSAL_INSTRUCTIONS_TAB:
                return LOCKED_TAB, self._door._spec(identity)
            return (REVIEW_TAB if self.title == REVIEW_TAB_TITLE else PROPOSAL_TAB), None
        if identity is None or identity.kind != CLASS_SHEET:
            return None, None
        kind = self._label().get(TAB_KIND_LABEL)
        if kind not in TAB_KINDS:
            from planars.schema_values import STATUS_TAB
            from .locked_tabs import system_tab_titles
            title = self.title
            if title == STATUS_TAB:
                kind = STATUS_TAB_KIND
            elif title in system_tab_titles():
                kind = LOCKED_TAB
            else:
                kind = CONSTRUCTION_TAB
        return kind, (self._door._spec(identity) if kind == LOCKED_TAB else None)

    def _tooling_columns(self) -> set:
        """Columns of this tab that the tooling owns (by header name)."""
        identity = self._ss.identity
        kind, _ = self._kind()
        if kind == PROPOSAL_TAB:
            return set()     # every column the annotator's
        if kind == STATUS_TAB_KIND:
            from planars.schema_values import STATUS_TOOLING_COLUMNS
            return set(STATUS_TOOLING_COLUMNS)
        from planars.schema_values import row_columns
        try:
            return set(row_columns(identity.class_name, self._name()))
        except Exception:  # noqa: BLE001 - unknown shape: protect every column
            return set()

    def _annotator_cell(self, grid: List[List[str]], tooling: set, r: int, c: int) -> bool:
        header = grid[0] if grid else []
        name = header[c] if c < len(header) else ""
        return r >= 1 and name not in tooling

    # -- rule 1: annotations are never lost silently ---------------------------
    def _replacing_reason(self) -> Optional[str]:
        return self._door._replacing.get(self._key)

    def _note(self, action: str, cells: int = 0) -> None:
        """Count a write to this tab toward its provenance line."""
        self._door._wrote(self._ss.id, self._ss.title, self.title, action, cells,
                          self._ss.identity, self._replacing_reason())
        self._door._wrote_sheet(self._ss)

    # -- rule 1 inside replacing(): mid-run edits, answered rows dropped ------
    def _protected_cells(self, grid: List[List[str]]) -> Optional[set]:
        """Header names of this tab's tooling columns, or None if the tab is
        not one whose annotations the door looks after."""
        kind, _ = self._kind()
        if kind not in _ANSWER_TABS:
            return None
        return self._tooling_columns()

    def _edits_since(self, earlier: List[List[str]], now: List[List[str]]) -> Optional[str]:
        """A message if an annotator changed this tab between the command's
        earlier read (``earlier``) and ``now``; None if not."""
        tooling = self._protected_cells(now)
        if tooling is None:
            return None
        if _trimmed(earlier[:1]) != _trimmed(now[:1]):
            return (f"the columns of {self.title!r} changed while the command ran "
                    "(someone edited the sheet mid-run); its answers may be read wrong")
        changed = [(r, c) for r in range(1, max(len(earlier), len(now)))
                   for c in range(max(len(_row(earlier, r)), len(_row(now, r))))
                   if self._annotator_cell(now, tooling, r, c)
                   and _cell(earlier, r, c) != _cell(now, r, c)]
        if not changed:
            return None
        r, c = changed[0]
        return (f"an annotator changed {len(changed)} answer cell(s) in {self.title!r} while "
                f"the command ran (first: row {r + 1}, {_cell(earlier, r, c)!r} -> "
                f"{_cell(now, r, c)!r}); the command worked from what it read before")

    def _answered_rows_not_kept(self, grid: List[List[str]],
                                kept: Iterable[Sequence[str]]) -> List[str]:
        """One line for each row holding an answer whose key is not in ``kept``."""
        identity = self._ss.identity
        kind, _ = self._kind()
        if kind != CONSTRUCTION_TAB:
            raise ValueError(f"replacing(kept=...) needs a construction tab of a sheet the "
                             f"door can place; {self.title!r} is not one")
        from planars.schema_values import row_key
        key_cols = row_key(identity.class_name, self._name())
        tooling = self._tooling_columns()
        keep = {tuple(str(v).strip() for v in k) for k in kept}
        header = grid[0] if grid else []
        lines = []
        for r in range(1, len(grid)):
            rec = dict(zip(header, grid[r]))
            answers = [(name, value) for name, value in rec.items()
                       if name not in tooling and str(value).strip()]
            key = tuple(str(rec.get(k, "")).strip() for k in key_cols)
            if not answers or key in keep:
                continue
            who = ", ".join(f"{k} {v!r}" for k, v in zip(key_cols, key))
            lines.append(f"  {who}: " + "; ".join(f"{n}: {v!r}" for n, v in answers))
        return lines

    def _annotation_loss_problems(self, action: str, *, all_cells: bool = False,
                                  rows_from: Optional[int] = None,
                                  cols_from: Optional[int] = None) -> List[str]:
        kind, _ = self._kind()
        if kind not in _ANSWER_TABS or self._replacing_reason():
            return []
        grid = self._door._grid(self)
        tooling = self._tooling_columns()
        lost = 0
        for r, row in enumerate(grid):
            for c, value in enumerate(row):
                if value == "" or not self._annotator_cell(grid, tooling, r, c):
                    continue
                if all_cells or (rows_from is not None and r >= rows_from) \
                        or (cols_from is not None and c >= cols_from):
                    lost += 1
        if not lost:
            return []
        return [f"would {action} {self.title!r}, losing {lost} filled annotation cell(s); "
                "a command that means to do this says so with drive_door.replacing()"]

    def _dimension_loss_problems(self, dimension: str, start: int, end: int) -> List[str]:
        kind, _ = self._kind()
        if kind not in _ANSWER_TABS or self._replacing_reason():
            return []
        grid = self._door._grid(self)
        tooling = self._tooling_columns()
        lost = sum(1 for r, row in enumerate(grid) for c, v in enumerate(row)
                   if v != "" and self._annotator_cell(grid, tooling, r, c)
                   and start <= (r if dimension == "ROWS" else c) < end)
        if not lost:
            return []
        what = "rows" if dimension == "ROWS" else "columns"
        return [f"would delete {what} {start + 1}-{end} of {self.title!r}, losing {lost} "
                "filled annotation cell(s); a command that means to do this says so "
                "with drive_door.replacing()"]

    def _value_problems(self, changes: Dict[Tuple[int, int], str]) -> List[str]:
        kind, spec = self._kind()
        if kind is None:
            return []
        if kind == LOCKED_TAB:
            return self._locked_problems(spec, changes)
        if kind not in _ANSWER_TABS or self._replacing_reason():
            return []
        grid = self._door._grid(self)
        tooling = self._tooling_columns()
        changed = [(r, c) for (r, c), new in changes.items()
                   if _cell(grid, r, c) != "" and new != _cell(grid, r, c)
                   and self._annotator_cell(grid, tooling, r, c)]
        if not changed:
            return []
        r, c = changed[0]
        where = f"row {r + 1}, column {grid[0][c] if c < len(grid[0]) else c + 1!r}"
        return [f"would change {len(changed)} filled annotation cell(s) in {self.title!r} "
                f"(first: {where}, {_cell(grid, r, c)!r} -> {changes[(r, c)]!r}); a command "
                "that means to do this says so with drive_door.replacing()"]

    # -- rule 2: locked tabs hold their builder's content ---------------------
    def _locked_problems(self, spec, changes: Dict[Tuple[int, int], str]) -> List[str]:
        if isinstance(spec, Exception):
            return [f"cannot check locked tab {self.title!r}: the sheet's spec could "
                    f"not be built ({spec})"]
        try:
            rows = spec.tab(self._name()).rows or ()
        except KeyError:
            return [f"{self.title!r} is not a locked tab this class carries"]
        wrong = [(r, c) for (r, c), new in changes.items()
                 if new != (rows[r][c] if r < len(rows) and c < len(rows[r]) else "")]
        if not wrong:
            return []
        return [f"would write {len(wrong)} cell(s) of locked tab {self.title!r} that "
                "differ from what its builder makes"]

    # -- rule 3: dropdowns match the spec --------------------------------------
    def _dropdown_problems(self, payload: Mapping[str, Any]) -> List[str]:
        kind, _ = self._kind()
        if kind is None:
            return []
        rule = payload.get("rule")
        if rule is None:
            return []  # clearing a dropdown is always allowed
        if kind == LOCKED_TAB:
            return [f"no dropdowns on locked tab {self.title!r}"]
        if kind == COPY_TAB:
            return [f"no dropdowns on {COPY_SHEETS[self._ss.identity.kind][1]} "
                    f"{self._ss.title!r}"]
        if kind == STATUS_PAGE_TAB:
            return [f"no dropdowns on status sheet {self._ss.title!r}"]
        if kind in (REVIEW_TAB, PROPOSAL_TAB):
            return [f"no dropdowns on proposal sheet {self._ss.title!r}"]
        grid = self._door._grid(self)
        header = grid[0] if grid else []
        rng = payload["range"]
        start = rng.get("startColumnIndex", 0)
        end = rng.get("endColumnIndex", max(len(header), start + 1))
        values = tuple(v.get("userEnteredValue", "")
                       for v in rule.get("condition", {}).get("values", []))
        problems = []
        for c in range(start, end):
            name = header[c] if c < len(header) else None
            allowed = self._allowed(kind, name)
            if isinstance(allowed, str):
                problems.append(allowed)
            elif allowed is None:
                problems.append(f"no dropdown belongs on column {name or c + 1!r} of "
                                f"{self.title!r}: it is not a criterion column")
            elif tuple(values) != tuple(allowed):
                problems.append(f"dropdown on {name!r} in {self.title!r} offers "
                                f"{list(values)}, but the language's diagnostics file "
                                f"allows {list(allowed)}")
        return problems

    def _allowed(self, kind: str, name: Optional[str]):
        """The column's allowed values, None for a column that has no dropdown,
        or a message saying why it cannot be checked."""
        if kind == STATUS_TAB_KIND:
            from planars.schema_values import STATUS_STATUS_COLUMN, STATUS_VALUES
            return tuple(STATUS_VALUES) if name == STATUS_STATUS_COLUMN else None
        identity = self._ss.identity
        spec = self._door._spec(identity)
        if isinstance(spec, Exception):
            return (f"cannot check the dropdown on {name!r} in {self.title!r}: the "
                    f"sheet's spec could not be built ({spec})")
        try:
            tab = spec.tab(self._name())
        except KeyError:
            return (f"cannot check the dropdown on {name!r}: {self.title!r} is not a "
                    f"construction of {identity.describe()} in the diagnostics file")
        try:
            column = tab.column(name) if name else None
        except KeyError:
            return (f"cannot check the dropdown on {name!r} in {self.title!r}: the "
                    "diagnostics file has no such criterion for this tab")
        if column is None or column.owner != "annotator":
            return None
        return column.allowed

    # -- rule 4: protection only on locked tabs --------------------------------
    def _protection_problems(self) -> List[str]:
        kind, _ = self._kind()
        if kind is None or kind in (LOCKED_TAB, COPY_TAB):
            return []
        return [f"only locked tabs and copies are protected; {self.title!r} is neither"]

    # -- applying a write to the door's view -----------------------------------
    def _apply(self, changes: Dict[Tuple[int, int], str]) -> None:
        grid = self._door._grids.get(self._key)
        if grid is None:
            return
        for (r, c), value in changes.items():
            _put(grid, r, c, value)

    # -- writes -------------------------------------------------------------
    def update(self, values: Sequence[Sequence[Any]], range_name: str = "A1",
               raw: bool = True) -> Any:
        r0, c0 = _anchor(range_name)
        changes = {(r0 + i, c0 + j): _text(v)
                   for i, row in enumerate(values) for j, v in enumerate(row)}
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"write {self.title!r} of {self._ss.title!r}",
                          self._value_problems(changes), target=self._ss.id)
        result = _retry(lambda: self._inner.update(values, range_name, raw=raw))
        self._apply(changes)
        self._note("update", len(changes))
        return result

    def update_cell(self, row: int, col: int, value: Any) -> Any:
        changes = {(row - 1, col - 1): _text(value)}
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"write a cell of {self.title!r} in {self._ss.title!r}",
                          self._value_problems(changes), target=self._ss.id)
        result = _retry(lambda: self._inner.update_cell(row, col, value))
        self._apply(changes)
        self._note("update_cell", 1)
        return result

    def insert_cols(self, values: Sequence[Sequence[Any]], col: int = 1) -> Any:
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"insert columns into {self.title!r} of {self._ss.title!r}",
                          target=self._ss.id)
        result = _retry(lambda: self._inner.insert_cols(values, col))
        self._door._forget(self._key)
        self._note("insert_cols", sum(len(c) for c in values))
        return result

    def append_rows(self, values: Sequence[Sequence[Any]],
                    value_input_option: str = "RAW") -> Any:
        problems: List[str] = []
        self._door._before_shape_write(self._ss, self)
        kind, spec = self._kind()
        if kind == LOCKED_TAB:
            start = len(self._door._grid(self))
            changes = {(start + i, j): _text(v)
                       for i, row in enumerate(values) for j, v in enumerate(row)}
            problems = self._locked_problems(spec, changes)
        self._door._check(f"add rows to {self.title!r} of {self._ss.title!r}", problems,
                          target=self._ss.id)
        result = _retry(lambda: self._inner.append_rows(values, value_input_option=value_input_option))
        self._door._forget(self._key)
        self._note("append_rows", sum(len(r) for r in values))
        return result

    def clear(self) -> Any:
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"clear {self.title!r} of {self._ss.title!r}",
                          self._annotation_loss_problems("clear", all_cells=True),
                          target=self._ss.id)
        result = _retry(self._inner.clear)
        self._door._grids[self._key] = []
        self._note("clear")
        return result

    def resize(self, rows: Optional[int] = None, cols: Optional[int] = None) -> Any:
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"resize {self.title!r} of {self._ss.title!r}",
                          self._annotation_loss_problems("shrink", rows_from=rows,
                                                         cols_from=cols),
                          target=self._ss.id)
        result = _retry(lambda: self._inner.resize(rows=rows, cols=cols))
        self._door._forget(self._key)
        self._note("resize")
        return result

    def update_title(self, title: str) -> Any:
        self._door._before_shape_write(self._ss, self)
        self._door._check(f"rename tab {self.title!r} of {self._ss.title!r} to {title!r}",
                          target=self._ss.id)
        self._door._drop_tab_labels(self)
        result = _retry(lambda: self._inner.update_title(title))
        self._note("update_title")
        return result


def _create_tab(ss: CheckedSpreadsheet, title: str, rows: int, cols: int,
                index: Optional[int]):
    """Add a tab once: before a retry, see whether the first attempt made it."""
    def landed():
        try:
            return ss._inner.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            return None

    return _retry(lambda: ss._inner.add_worksheet(title=title, rows=rows, cols=cols,
                                                  index=index), landed=landed)


# ---------------------------------------------------------------------------
# Watch-mode report
# ---------------------------------------------------------------------------

def _report_violations(command: str, violations: List[str]) -> None:
    """One GitHub issue for every door violation a watched run let through."""
    from . import issues
    counts: Dict[str, int] = {}
    for v in violations:
        counts[v] = counts.get(v, 0) + 1
    lines = [f"- {v}" + (f" (×{n})" if n > 1 else "") for v, n in counts.items()]
    body = (
        f"The Drive door is watching writes before it starts refusing them "
        f"(docs/drive-door-design.md § 4). `{command}` made writes that break its rules; "
        "they went ahead.\n\n" + "\n".join(lines) + "\n\n"
        "Each one is either a real bug in the command (fix the command) or a gap in the "
        "sheet spec (fix `coding/sheet_spec.py` or `coding/drive_door.py`). Close this "
        "issue when every line is resolved.\n"
    )
    title = "Drive door: writes that broke a rule"
    try:
        # By title: the local-file door files under the same label, as its own issue.
        issues.file_issue(VIOLATION_LABEL, title, body, match_title=True)
    except Exception as exc:  # noqa: BLE001 - never fail a finished run over the report
        print(f"WARNING: could not file the {VIOLATION_LABEL} issue: {exc}")
        print(body)
