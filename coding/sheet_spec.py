"""What each Drive file the tooling writes should look like, built from the schemas.

Phase 10 unit 5 (issue #271); design: docs/drive-door-design.md § 2.1. The
Drive door checks every write against these specs. Nothing here is stored:
each call reads the schemas and the language's own sources (planar TSV,
diagnostics YAML) afresh, so a spec cannot drift from them. A wrong spec shows
up as a wrong check, not as a quietly stale table.

So far: class sheets (`class_sheet_spec`), and sharing for every kind of
Drive file (`sharing_spec`: who gets which role, and whether a link share is
allowed). The other kinds' contents get their sections as unit 5 reaches them
(design § 5).

A class sheet is its locked tabs, one tab per construction in the language's
diagnostics file, and Status, in the order `locked_tabs.reorder_tabs` puts
them. Each column has an owner:

  tooling    the columns that identify a row (`planars.schema_values.row_columns`)
             and the Status tab's columns `planar.yaml` gives to the tooling
             (Construction, and the problems column validate-coding rewrites).
  annotator  criterion columns, the trailing columns (Source, Comments) and
             Status. The tooling may fill an empty one (a new row, a pre-fill)
             but never changes one an annotator has filled, unless the command
             says so through the door (design § 2.4 rule 1).

Which rows an element-row tab has is computed here from the planar. The rows
of a pair-row or keyed-row tab are generated from the tab before it, from what
annotators entered there, so their spec gives only the row key;
``expected_row_keys`` gets the keys from the generators' own builders, for
the Drive door's end-of-command check (rule 6).
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

from planars.schema_values import (
    ELEMENT_ROWS,
    KEYED_ROWS,
    PAIR_ROWS,
    STATUS_COLUMNS,
    STATUS_CONSTRUCTION_COLUMN,
    STATUS_STATUS_COLUMN,
    STATUS_TAB,
    STATUS_TOOLING_COLUMNS,
    STATUS_VALUES,
    TRAILING_COLUMNS,
    row_columns,
    row_key,
    row_type,
)

from .biuniqueness_rows import CLASS_NAME as BIUNIQUENESS_CLASS
# A tab's kind is also its identity label on Drive, so the door owns the names.
from .drive_door import CONSTRUCTION_TAB as CONSTRUCTION
from .drive_door import LOCKED_TAB as LOCKED
from .drive_door import STATUS_TAB_KIND as STATUS
from .biuniqueness_rows import ELEMENTS as BIUNIQUENESS_ELEMENTS_TAB
from .biuniqueness_rows import element_rows as biuniqueness_element_rows
from .locked_tabs import locked_tab_contents, locked_tab_specs
from .make_forms import _read_diagnostics_for_language, build_element_index, element_rows
from .schemas import apply_schema_criteria, is_free_entry

TOOLING = "tooling"
ANNOTATOR = "annotator"

# Columns `sync-params --split/--merge` parks an old criterion in, renamed
# with one of these prefixes, so annotators can move its answers into the new
# columns before the coordinator deletes it by hand (`--remove` leaves it). A
# declared holding state, not drift: the spec allows them, and
# integrity-check --sheets reminds the coordinator they are there.
# Prefix -> the operation that made it.
SPLIT_PREFIX, MERGED_PREFIX = "_split_", "_merged_"
PARKED_COLUMN_PREFIXES = {SPLIT_PREFIX: "split", MERGED_PREFIX: "merge"}


def parked_operation(column: str) -> Optional[str]:
    """``split`` or ``merge`` if ``column`` is a parked old criterion, else None."""
    for prefix, operation in PARKED_COLUMN_PREFIXES.items():
        if column.startswith(prefix):
            return operation
    return None


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    owner: str                            # TOOLING or ANNOTATOR
    allowed: Optional[Tuple[str, ...]]    # dropdown values; None = no dropdown


@dataclass(frozen=True)
class TabSpec:
    title: str
    kind: str                                   # LOCKED, CONSTRUCTION or STATUS
    columns: Tuple[ColumnSpec, ...] = ()        # empty for a locked tab
    row_columns: Tuple[str, ...] = ()           # the tooling's columns, before the criteria
    row_key: Tuple[str, ...] = ()               # those of them that identify a row
    rows: Optional[Tuple[Tuple[str, ...], ...]] = None
    # rows: a locked tab's whole content; an element-row tab's row_columns
    # values, in sheet order; a Status tab's Construction cells.
    # None where the rows come from another tab (pair and keyed rows).
    protected: bool = False

    @property
    def header(self) -> List[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> ColumnSpec:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.title} has no column {name!r}")


@dataclass(frozen=True)
class ClassSheetSpec:
    lang_id: str
    class_name: str
    tabs: Tuple[TabSpec, ...]

    @property
    def tab_titles(self) -> List[str]:
        return [t.title for t in self.tabs]

    def tab(self, title: str) -> TabSpec:
        for t in self.tabs:
            if t.title == title:
                return t
        raise KeyError(f"{self.class_name}_{self.lang_id} has no tab {title!r}")


def _class_constructions(lang_id: str, class_name: str, data_dir: Path) -> list:
    """[(construction, criterion_names, {name: values})] for one class, in the
    diagnostics file's order, each through coding.schemas.criteria_for."""
    specs = _read_diagnostics_for_language(lang_id, data_dir / lang_id / "lang_setup")
    rows = [(con, names, values) for cls, con, names, values in specs if cls == class_name]
    if not rows:
        raise KeyError(f"diagnostics_{lang_id}.yaml has no class {class_name!r}")
    return apply_schema_criteria(class_name, rows, lang_id)


def _element_rows(lang_id: str, class_name: str, construction: str,
                  planar_path: Path) -> Tuple[Tuple[str, ...], ...]:
    """(Element, Position_Name, Position_Number) for every row an element-row
    tab has, in sheet order, from the generators' own row builders."""
    if class_name == BIUNIQUENESS_CLASS and construction == BIUNIQUENESS_ELEMENTS_TAB:
        import pandas as pd
        planar_df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
        rows = biuniqueness_element_rows(planar_df, lang_id, [])
    else:
        rows = element_rows(build_element_index(planar_path.name, planar_path.parent), lang_id)
    return tuple((str(el), str(name), str(pos)) for el, name, pos, *_ in rows)


def _construction_tab(lang_id: str, class_name: str, construction: str,
                      names: List[str], values: Dict[str, List[str]],
                      planar_path: Path) -> TabSpec:
    key_cols = row_columns(class_name, construction)
    columns = [ColumnSpec(c, TOOLING, None) for c in key_cols]
    columns += [ColumnSpec(n, ANNOTATOR, None if is_free_entry(values[n]) else tuple(values[n]))
                for n in names]
    columns += [ColumnSpec(c, ANNOTATOR, None) for c in TRAILING_COLUMNS]
    rows = None
    if row_type(class_name, construction) == ELEMENT_ROWS:
        rows = _element_rows(lang_id, class_name, construction, planar_path)
    return TabSpec(construction, CONSTRUCTION, tuple(columns), tuple(key_cols),
                   tuple(row_key(class_name, construction)), rows)


def expected_row_keys(lang_id: str, class_name: str, tab: TabSpec,
                      data_dir: Path) -> Optional[FrozenSet[Tuple[str, ...]]]:
    """The row keys a construction or Status tab should hold, or None when
    they can't be worked out (a source tab not imported yet, a prescreening
    question the builder refuses to guess at).

    Element-row and Status tabs: from the spec's own rows. Pair tabs:
    ``generate_sheets.pair_rows``, which reads the prescreening TSV under the
    module's ``CODED_DATA`` (the same folder as ``data_dir`` wherever the door
    runs: live, or a test's redirected copy). Keyed tabs: ``keyed_rows`` from
    the source tabs' TSVs under ``data_dir``; rows added by hand are not
    generated, so ``counts_as_generated`` leaves them out of the comparison."""
    if tab.kind == STATUS or (tab.kind == CONSTRUCTION
                              and row_type(class_name, tab.title) == ELEMENT_ROWS):
        index = [tab.row_columns.index(k) for k in tab.row_key]
        return frozenset(tuple(r[i] for i in index) for r in tab.rows or ())
    if tab.kind != CONSTRUCTION:
        return None
    kind = row_type(class_name, tab.title)
    # The builders print progress notes for a command's own output; quiet here.
    with contextlib.redirect_stdout(io.StringIO()):
        if kind == PAIR_ROWS:
            from .generate_sheets import pair_rows
            try:
                pairs = pair_rows(lang_id, class_name, tab.title, file_issue=False)
            except SystemExit:
                return None
            index = [tab.row_columns.index(k) for k in tab.row_key]
            return frozenset(tuple(str(p[i]) for i in index) for p in pairs)
        if kind == KEYED_ROWS:
            import pandas as pd
            from .biuniqueness_rows import keyed_rows, sources_of
            cls_dir = data_dir / lang_id / class_name
            if not all((cls_dir / f"{s}.tsv").exists() for s in sources_of(tab.title)):
                return None
            read = lambda n: pd.read_csv(cls_dir / f"{n}.tsv", sep="\t", dtype=str,
                                         keep_default_na=False)
            planar_path = data_dir / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
            planar_df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
            rows = keyed_rows(tab.title, read, planar_df, lang_id)
            return frozenset(tuple(str(r.get(k, "")).strip() for k in tab.row_key) for r in rows)
    raise ValueError(f"{class_name}/{tab.title}: unknown row type {kind!r}")


def counts_as_generated(class_name: str, construction: str, record: Dict[str, str]) -> bool:
    """Whether a sheet row is one the generators make (and so is compared
    with ``expected_row_keys``). Only a keyed tab's hand-added rows are not."""
    if row_type(class_name, construction) != KEYED_ROWS:
        return True
    from .biuniqueness_rows import is_generated
    return is_generated(record)


def class_sheet_spec(lang_id: str, class_name: str, data_dir: Path) -> ClassSheetSpec:
    """The spec for one language's sheet for one class.

    ``data_dir`` is the folder holding the language folders (``CODED_DATA``,
    or the frozen copy tests use)."""
    planar_path = data_dir / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    constructions = _class_constructions(lang_id, class_name, data_dir)

    locked = {spec["title"]: (spec, rows)
              for spec, rows in locked_tab_contents(class_name, lang_id, planar_path)}
    first, last = [], []
    for spec in locked_tab_specs():
        if spec["title"] not in locked:
            continue
        rows = locked[spec["title"]][1]
        tab = TabSpec(spec["title"], LOCKED, rows=tuple(tuple(r) for r in rows), protected=True)
        (first if spec["place"] == "first" else last).append(tab)

    middle = [_construction_tab(lang_id, class_name, con, names, values, planar_path)
              for con, names, values in constructions]

    key_col = STATUS_CONSTRUCTION_COLUMN
    status = TabSpec(
        STATUS_TAB, STATUS,
        tuple(ColumnSpec(c, TOOLING if c in STATUS_TOOLING_COLUMNS else ANNOTATOR,
                         tuple(STATUS_VALUES) if c == STATUS_STATUS_COLUMN else None)
              for c in STATUS_COLUMNS),
        (key_col,), (key_col,),
        tuple((con,) for con, _, _ in constructions),
    )
    return ClassSheetSpec(lang_id, class_name, tuple(first + middle + last + [status]))


# ---------------------------------------------------------------------------
# Sharing: who may have access to each kind of Drive file
# ---------------------------------------------------------------------------

READER, WRITER = "reader", "writer"
# Who a kind of file is shared with, besides its owner (the tooling's account):
#   annotator      the language's annotator, by name
#   all_annotators every annotator languages.yaml names, by name
#   nobody         no one; anything inside it is shared on its own
# and the role they get. ``link`` is the role "anyone with the link" gets, or
# None (named people only: Phase 10 unit 14). Every kind in the door's KINDS
# has an entry; a kind missing here is an error, not a default.
_ANNOTATOR, _ALL_ANNOTATORS, _NOBODY = "annotator", "all_annotators", "nobody"
_SHARING: Dict[str, Dict[str, Optional[str]]] = {
    "class_sheet":       {"who": _ANNOTATOR, "role": WRITER, "link": None},
    "planar_sheet":      {"who": _ANNOTATOR, "role": WRITER, "link": None},
    "diagnostics_sheet": {"who": _ANNOTATOR, "role": WRITER, "link": None},
    # Built by the tooling, read by the annotator (generate-status-sheet).
    "status_sheet":      {"who": _ANNOTATOR, "role": READER, "link": None},
    # Where the annotator writes notes to the coordinator.
    "notes_doc":         {"who": _ANNOTATOR, "role": WRITER, "link": None},
    # Notebooks and PDF reports keep link sharing until a notebook shared by
    # name is shown to open in Colab for a signed-in annotator (design § 7,
    # Q4). Then they become {"who": _ANNOTATOR, "role": READER, "link": None}.
    "report":            {"who": _NOBODY, "role": None, "link": READER},
    "notebook":          {"who": _NOBODY, "role": None, "link": READER},
    "manifest":          {"who": _NOBODY, "role": None, "link": None},
}
# Folders differ by which folder: a language folder lets its annotator see
# their files; the Annotation Status folder holds every language's status
# sheet; the root and archive folders grant nothing of their own.
_FOLDER_SHARING: Dict[str, Dict[str, Optional[str]]] = {
    "language": {"who": _ANNOTATOR, "role": READER, "link": None},
    "status":   {"who": _ALL_ANNOTATORS, "role": READER, "link": None},
    "root":     {"who": _NOBODY, "role": None, "link": None},
    "archive":  {"who": _NOBODY, "role": None, "link": None},
}


@dataclass(frozen=True)
class SharingSpec:
    """The grants a file should carry: each named person's role (addresses
    in lower case), and the role of a link share, or None for none."""
    people: Tuple[Tuple[str, str], ...]
    link: Optional[str]

    def role_for(self, email: Optional[str]) -> Optional[str]:
        """The role the spec gives this address, or None if it gives none."""
        return dict(self.people).get((email or "").lower())


def sharing_spec(identity, archived: bool = False) -> SharingSpec:
    """Who may have access to the file ``identity`` (a ``drive_door.Identity``)
    names, and how. An archived file is read-only: everyone listed is a reader,
    and nobody gets a link share."""
    from .people import annotator_email, every_annotator_email

    table = _FOLDER_SHARING if identity.kind == "folder" else _SHARING
    key = identity.name if identity.kind == "folder" else identity.kind
    if key not in table:
        raise ValueError(f"no sharing rule for a {identity.kind} {key!r} "
                         "(coding/sheet_spec.py, _SHARING)")
    rule = table[key]
    if rule["who"] == _ANNOTATOR:
        email = annotator_email(identity.lang_id)
        emails = [email] if email else []
    elif rule["who"] == _ALL_ANNOTATORS:
        emails = every_annotator_email()
    elif rule["who"] == _NOBODY:
        emails = []
    else:
        raise ValueError(f"unknown sharing rule {rule['who']!r}")
    role = READER if archived else rule["role"]
    link = None if archived else rule["link"]
    return SharingSpec(tuple(sorted((e.lower(), role) for e in emails)), link)
