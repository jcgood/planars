"""What each Drive file the tooling writes should look like, built from the schemas.

Phase 10 unit 5 (issue #271); design: docs/drive-door-design.md § 2.1. The
Drive door checks every write against these specs. Nothing here is stored:
each call reads the schemas and the language's own sources (planar TSV,
diagnostics YAML) afresh, so a spec cannot drift from them. A wrong spec shows
up as a wrong check, not as a quietly stale table.

Every kind of Drive file has a spec: class sheets (`class_sheet_spec`),
the planar and diagnostics Sheets (`copy_sheet_spec`), the status sheets
(`status_sheet_spec`: one `Status` tab listing every construction, all the
tooling's), the proposal sheets (`proposal_sheet_spec`, titled
`proposal_sheet_title`: a locked Instructions tab, Last review, the
tooling's, then Planar and Diagnostics, copies of the two sources plus a
What changed? column, every cell the annotator's), and the files that are not spreadsheets — notes Docs, the
manifest, notebooks, PDF reports, contributor chart PDFs and folders (`file_spec`: name, folder,
type, what may be written into it, `content_problems`,
`appended_text_problems`). Sharing is specified for every kind
(`sharing_spec`: who gets which role, and whether a link share is allowed; one
table per kind, and a kind with no entry raises; the coordinators in
people.yaml are writers on the root folder, which everything under it
inherits). `sharing_differences(spec, grants)` compares a file's own grants
with its spec (integrity-check's SHARING section).

`file_spec` is the one place each non-spreadsheet file is named, together with
`ROOT_FOLDER_NAME`, `ARCHIVE_FOLDER_NAME` and `STATUS_FOLDER_NAME`; commands
read the names from here. `STATUS_SHEET_COLUMNS` is the status sheet's header,
which generate-status-sheet reads. Row shapes come from `planars.schema_values`
(`row_columns`, `row_key`) and the rows of an element-row tab from the
generators' own builders (`make_forms.element_rows`,
`biuniqueness_rows.element_rows`); locked-tab content from
`locked_tabs.locked_tab_contents`. `tests/test_sheet_spec.py` holds every
recorded class sheet to its spec.

`expected_row_keys` gives the row keys any construction or Status tab should
hold: pair tabs from `generate_sheets.pair_rows` (the one pair builder that
creating, extending and regenerating a sheet all call), keyed tabs from
`biuniqueness_rows.keyed_rows`, None when a source isn't imported yet;
`counts_as_generated` leaves a keyed tab's hand-added rows out. The door's
rule 6 uses both. `PARKED_COLUMN_PREFIXES`/`parked_operation` are the one
statement of the `_split_`/`_merged_` holding columns `sync-params` leaves
for the coordinator to delete by hand (read by sync-params, integrity-check
and the door).

A notes Doc is the annotator's: its text is never replaced, and the only
thing the tooling adds is one acknowledgment line at a time (check-notes),
in the form check-notes strips before looking for new notes.

The planar Sheet is one tab holding exactly ``planar_{lang_id}.tsv``, the
source: its header, then its rows. The diagnostics Sheet is one tab holding
exactly what ``diagnostics_{lang_id}.yaml``, its source, renders to
(``make_forms._yaml_to_tsv_df``, which also writes the TSV copy and is what
``sync-diagnostics-yaml --to-sheet`` pushes). Both are read-only copies
(Phase 10 unit 11b, docs/ownership-design.md § 3.1): every cell is the
tooling's, the annotator is a reader by sharing, the tab is protected (the
coordinators are writers on the root folder, which every file inherits), no
cell has a dropdown, and nothing is read back from them (sync-planar and
sync-diagnostics-yaml rebuild them daily).

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
    trailing_columns_for,
    row_columns,
    row_key,
    row_type,
)

from .biuniqueness_rows import CLASS_NAME as BIUNIQUENESS_CLASS
# A tab's kind is also its identity label on Drive, so the door owns the names.
from .drive_door import CONSTRUCTION_TAB as CONSTRUCTION
from .drive_door import LOCKED_TAB as LOCKED
from .drive_door import COPY_TAB as COPY
from .drive_door import DIAGNOSTICS_SHEET, PLANAR_SHEET
from .drive_door import PROPOSAL_TAB as PROPOSAL
from .drive_door import REVIEW_TAB as REVIEW
from .drive_door import STATUS_PAGE_TAB as STATUS_PAGE
from .drive_door import STATUS_TAB_KIND as STATUS
from .biuniqueness_rows import ELEMENTS as BIUNIQUENESS_ELEMENTS_TAB
from .biuniqueness_rows import element_rows as biuniqueness_element_rows
from .locked_tabs import locked_tab_contents, locked_tab_specs
from .make_forms import _read_diagnostics_for_language, build_element_index, element_rows
from .schemas import apply_schema_criteria, dropdown_values

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
    kind: str                                   # LOCKED, CONSTRUCTION, STATUS or COPY
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
                      planar_path: Optional[Path]) -> TabSpec:
    """A construction tab's spec; with no ``planar_path``, its columns only
    (``rows`` None)."""
    key_cols = row_columns(class_name, construction)
    columns = [ColumnSpec(c, TOOLING, None) for c in key_cols]
    columns += [ColumnSpec(n, ANNOTATOR, dropdown_values(values[n])) for n in names]
    columns += [ColumnSpec(c, ANNOTATOR, None) for c in trailing_columns_for(lang_id)]
    rows = None
    if planar_path is not None and row_type(class_name, construction) == ELEMENT_ROWS:
        rows = _element_rows(lang_id, class_name, construction, planar_path)
    return TabSpec(construction, CONSTRUCTION, tuple(columns), tuple(key_cols),
                   tuple(row_key(class_name, construction)), rows)


def construction_columns(lang_id: str, class_name: str, construction: str,
                         data_dir: Path) -> TabSpec:
    """One construction tab's columns and row key, without its rows: what an
    imported annotation TSV holds (the local-file door's check). Raises
    KeyError if the diagnostics file has no such class or construction."""
    for con, names, values in _class_constructions(lang_id, class_name, data_dir):
        if con == construction:
            return _construction_tab(lang_id, class_name, con, names, values, None)
    raise KeyError(f"diagnostics_{lang_id}.yaml has no construction {construction!r} "
                   f"in class {class_name!r}")


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
# The planar and diagnostics Sheets: copies of one file each
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CopySheetSpec:
    """One tab, ``tab``: the file's header as its columns (every one the
    tooling's, none with a dropdown) and its rows, stripped, in order.
    ``kind`` is the Sheet's (planar_sheet or diagnostics_sheet)."""
    kind: str
    lang_id: str
    tab: TabSpec


def copy_sheet_spec(kind: str, lang_id: str, data_dir: Path) -> CopySheetSpec:
    """The spec for one language's planar or diagnostics Sheet, from its
    source: the planar file, or the diagnostics YAML as it renders to rows."""
    import pandas as pd
    lang_setup = data_dir / lang_id / "lang_setup"
    if kind == PLANAR_SHEET:
        df = pd.read_csv(lang_setup / f"planar_{lang_id}.tsv", sep="\t", dtype=str,
                         keep_default_na=False)
    elif kind == DIAGNOSTICS_SHEET:
        import yaml
        from .make_forms import _yaml_to_tsv_df
        with open(lang_setup / f"diagnostics_{lang_id}.yaml", encoding="utf-8") as f:
            df = _yaml_to_tsv_df(yaml.safe_load(f), lang_id)
    else:
        raise ValueError(f"a {kind} is not a copy of one file")
    columns = tuple(ColumnSpec(str(c), TOOLING, None) for c in df.columns)
    rows = tuple(tuple(str(v).strip() for v in row) for row in df.itertuples(index=False))
    title = f"{kind.removesuffix('_sheet')}_{lang_id}"
    return CopySheetSpec(kind, lang_id, TabSpec(title, COPY, columns, rows=rows, protected=True))


# ---------------------------------------------------------------------------
# The proposal sheet: where an annotator proposes changes to the sources
# ---------------------------------------------------------------------------

# Its tabs, in order (ownership-design § 3.2). Instructions is locked: it
# says the sheet is for editing, unlike the read-only planar and diagnostics
# Sheets, and how (Jeff, 2026-10-24). Last review is the tooling's: what the
# last review accepted and rejected (accept-proposal writes it). The other
# two are copies of the planar and of the diagnostics file as the
# diagnostics Sheet shows it, plus a column for the annotator's reason.
# Named as the class sheets' instructions tab is (schemas/planar.yaml
# locked_tabs), so annotators find the same tab under the same name.
PROPOSAL_INSTRUCTIONS_TAB = next(s["title"] for s in locked_tab_specs()
                                 if s["builder"] == "instructions")
REVIEW_TAB_TITLE = "Last review"
PROPOSAL_PLANAR_TAB = "Planar"
PROPOSAL_DIAGNOSTICS_TAB = "Diagnostics"
WHAT_CHANGED_COLUMN = "What changed?"
# Each proposal tab and the source it copies (copy_sheet_spec's kind).
PROPOSAL_TABS: Tuple[Tuple[str, str], ...] = (
    (PROPOSAL_PLANAR_TAB, PLANAR_SHEET),
    (PROPOSAL_DIAGNOSTICS_TAB, DIAGNOSTICS_SHEET),
)


def proposal_sheet_title(lang_id: str) -> str:
    """What the sheet is called on Drive: "English [stan1293] planars and
    diagnostics" (Jeff, 2026-10-24; it was proposal_{lang_id})."""
    from planars.languages import get_display_name
    return f"{get_display_name(lang_id)} planars and diagnostics"


def proposal_instructions_rows(lang_id: str) -> Tuple[Tuple[str, ...], ...]:
    """The Instructions tab. Short: an annotator reads it (Adam, #318). Moves
    into the schema with the other sentences annotators read (unit 11d)."""
    lines = (
        proposal_sheet_title(lang_id),
        "",
        f"This sheet is for editing. The planar_{lang_id} and diagnostics_{lang_id} "
        "sheets in this folder are read-only: they show the current versions.",
        "",
        "To suggest a change:",
        "1. Edit the Planar or Diagnostics tab as you would like it to be: change a "
        "cell, add a row, or delete one.",
        "2. Say why in that row's What changed? cell. For a deleted row, give the "
        "reason on the row just above it.",
        "3. For a new position, add its row where it belongs and renumber the "
        "positions after it.",
        "",
        "Within a day a GitHub issue lists your changes. The coordinator accepts or "
        "declines each one. The outcome goes on the Last review tab, and the Planar "
        "and Diagnostics tabs are refilled from the new versions.",
    )
    return tuple((line,) for line in lines)


@dataclass(frozen=True)
class ProposalSheetSpec:
    """Instructions (locked, protected), Last review, then the Planar and
    Diagnostics tabs: each the source's columns and rows
    (``copy_sheet_spec``) plus WHAT_CHANGED_COLUMN, every cell the
    annotator's. Last review is not protected: it is rewritten after each
    review, so an edit to it is simply replaced."""
    lang_id: str
    tabs: Tuple[TabSpec, ...]

    @property
    def tab_titles(self) -> List[str]:
        return [t.title for t in self.tabs]

    def tab(self, title: str) -> TabSpec:
        for t in self.tabs:
            if t.title == title:
                return t
        raise KeyError(f"{proposal_sheet_title(self.lang_id)} has no tab {title!r}")


def proposal_sheet_spec(lang_id: str, data_dir: Path) -> ProposalSheetSpec:
    """The spec for one language's proposal sheet, from its two sources."""
    tabs = [TabSpec(PROPOSAL_INSTRUCTIONS_TAB, LOCKED,
                    rows=proposal_instructions_rows(lang_id), protected=True),
            TabSpec(REVIEW_TAB_TITLE, REVIEW, (ColumnSpec(REVIEW_TAB_TITLE, TOOLING, None),))]
    for title, kind in PROPOSAL_TABS:
        copy = copy_sheet_spec(kind, lang_id, data_dir).tab
        columns = tuple(ColumnSpec(c.name, ANNOTATOR, None) for c in copy.columns) \
            + (ColumnSpec(WHAT_CHANGED_COLUMN, ANNOTATOR, None),)
        rows = tuple(row + ("",) for row in copy.rows or ())
        tabs.append(TabSpec(title, PROPOSAL, columns, rows=rows))
    return ProposalSheetSpec(lang_id, tuple(tabs))


# ---------------------------------------------------------------------------
# The status sheet: a read-only page per language, rebuilt each run
# ---------------------------------------------------------------------------

# Its columns: each row restates one Status-tab row (planar.yaml
# status_tab.columns) with its class; the Status column holds the
# completeness percentage. generate-status-sheet writes these.
STATUS_SHEET_COLUMNS = ("Class", STATUS_CONSTRUCTION_COLUMN, STATUS_STATUS_COLUMN)


@dataclass(frozen=True)
class StatusSheetSpec:
    """One tab, ``tab`` (``Status``): a banner, then a header of
    STATUS_SHEET_COLUMNS, then one row per (class, construction) of the
    diagnostics file, in its order. Every cell is the tooling's; the status
    text comes from the live class sheets, so only its presence is specified."""
    lang_id: str
    tab: TabSpec


def status_sheet_spec(lang_id: str, data_dir: Path) -> StatusSheetSpec:
    """The spec for one language's status sheet, from its diagnostics file."""
    specs = _read_diagnostics_for_language(lang_id, data_dir / lang_id / "lang_setup")
    columns = tuple(ColumnSpec(c, TOOLING, None) for c in STATUS_SHEET_COLUMNS)
    rows = tuple((class_name, construction) for class_name, construction, _, _ in specs)
    return StatusSheetSpec(lang_id, TabSpec(STATUS_TAB, STATUS_PAGE, columns, rows=rows))


# ---------------------------------------------------------------------------
# Files that are not spreadsheets: notes Docs, the manifest, notebooks,
# PDF reports, contributor chart PDFs and folders
# ---------------------------------------------------------------------------

# What may be written into a file of each kind (``content_problems``).
NO_CONTENT = "nothing"                    # a folder
ACKNOWLEDGMENTS = "acknowledgment lines"  # the notes Doc: the annotator's text
MANIFEST_JSON = "the manifest"            # JSON the manifest contract accepts
NOTEBOOK_JSON = "a notebook"              # a Jupyter notebook's JSON
PDF = "a PDF"

_DOC_MIME = "application/vnd.google-apps.document"
_FOLDER_MIME = "application/vnd.google-apps.folder"
_JSON_MIME = "application/json"
_PDF_MIME = "application/pdf"

# The folders the project's top-level folders are called (the language
# folder is called by its Glottocode). Only names given here are made.
ROOT_FOLDER_NAME = "ConstituencyTypology"
ARCHIVE_FOLDER_NAME = "_archived"
STATUS_FOLDER_NAME = "Annotation Status"


@dataclass(frozen=True)
class FileSpec:
    """A Drive file that is not a spreadsheet: what it is called, the folder
    it sits in (None: outside every project folder, at the top of the owner's
    Drive), its type, what may be written into it, and whether only one live
    file may carry its identity."""
    name: str
    folder: Optional[object]     # a drive_door.Identity, or None
    mimetype: str
    content: str
    one_only: bool


def file_spec(identity) -> FileSpec:
    """The spec for a notes Doc, report, charts PDF, notebook, the manifest or a folder
    (``identity`` is a ``drive_door.Identity``). The one place each is named:
    the commands that make these files call this for the name."""
    from planars.languages import get_display_name
    from .drive_door import folder

    kind, lang = identity.kind, identity.lang_id
    if kind == "notes_doc":
        # The annotator writes here, so it sits beside their sheets.
        return FileSpec(f"{get_display_name(lang)} — Annotation Notes",
                        folder("language", lang), _DOC_MIME, ACKNOWLEDGMENTS, True)
    if kind == "report":
        return FileSpec(f"report_{lang}.pdf", folder("language", lang), _PDF_MIME, PDF, True)
    if kind == "charts":
        by = {"classes": "class", "types": "type"}[identity.name]
        return FileSpec(f"charts_by_{by}_{lang}.pdf", folder("language", lang), _PDF_MIME,
                        PDF, True)
    if kind == "notebook":
        if identity.name == "all_languages":
            return FileSpec("all_languages.ipynb", folder("root"), _JSON_MIME,
                            NOTEBOOK_JSON, True)
        return FileSpec(f"{identity.name}_{lang}.ipynb", folder("language", lang),
                        _JSON_MIME, NOTEBOOK_JSON, True)
    if kind == "manifest":
        return FileSpec("manifest.json", folder("root"), _JSON_MIME, MANIFEST_JSON, True)
    if kind == "folder" and identity.name == "root":
        return FileSpec(ROOT_FOLDER_NAME, None, _FOLDER_MIME, NO_CONTENT, True)
    if kind == "folder" and identity.name == "status":
        return FileSpec(STATUS_FOLDER_NAME, None, _FOLDER_MIME, NO_CONTENT, True)
    if kind == "folder" and identity.name == "language":
        return FileSpec(lang, folder("root"), _FOLDER_MIME, NO_CONTENT, True)
    if kind == "folder" and identity.name == "archive":
        # Not the only one of its language: before restructure-sheets put
        # _v{N} on an archived sheet's name, it made _archived/v{N}/ folders,
        # which are labelled archive folders too.
        return FileSpec(ARCHIVE_FOLDER_NAME, folder("language", lang), _FOLDER_MIME,
                        NO_CONTENT, False)
    raise ValueError(f"a {kind} is a spreadsheet, not a file with a file spec")


def content_problems(spec: FileSpec, content: bytes) -> List[str]:
    """What is wrong with writing ``content`` as the whole of a file of this
    spec."""
    if spec.content == NO_CONTENT:
        return ["a folder holds no content"]
    if spec.content == ACKNOWLEDGMENTS:
        return ["the notes Doc's text is the annotator's: the tooling only appends "
                "acknowledgment lines to it (check-notes), never replaces it"]
    if spec.content == PDF:
        return [] if content.startswith(b"%PDF-") else ["what is sent is not a PDF"]
    import json
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return [f"what is sent is not JSON ({exc})"]
    if spec.content == MANIFEST_JSON:
        from . import manifest_contract
        return [f"the manifest does not match its contract: {p}"
                for p in manifest_contract.check(data)]
    if spec.content == NOTEBOOK_JSON:
        if not (isinstance(data, dict) and isinstance(data.get("cells"), list)
                and isinstance(data.get("nbformat"), int)):
            return ["what is sent is not a notebook (no cells list or nbformat number)"]
        return []
    raise ValueError(f"unknown kind of content {spec.content!r}")


def appended_text_problems(spec: FileSpec, text: str) -> List[str]:
    """What is wrong with appending ``text`` to a file of this spec: only a
    notes Doc takes appended text, and only one acknowledgment line, in the
    form check-notes strips before it looks for new notes (or the next run
    would read the tooling's own line as the annotator's)."""
    from .drive import is_acknowledgment_line
    if spec.content != ACKNOWLEDGMENTS:
        return [f"text is appended only to notes Docs, not to {spec.content}"]
    if "\n" in text or not is_acknowledgment_line(text):
        return ["only an acknowledgment line is appended to a notes Doc "
                "(drive.acknowledgment_line), not other text"]
    return []


# ---------------------------------------------------------------------------
# Sharing: who may have access to each kind of Drive file
# ---------------------------------------------------------------------------

READER, WRITER = "reader", "writer"
# Who a kind of file is shared with, besides its owner (the tooling's account):
#   annotator      the language's annotator, by name
#   all_annotators every annotator languages.yaml names, by name
#   coordinators   every coordinator besides the owner (people.yaml), so their
#                  own account can run the tooling (Jeff, 2026-10-18)
#   nobody         no one; anything inside it is shared on its own
# and the role they get. ``link`` is the role "anyone with the link" gets, or
# None (named people only: Phase 10 unit 14). Every kind in the door's KINDS
# has an entry; a kind missing here is an error, not a default.
_ANNOTATOR, _ALL_ANNOTATORS, _COORDINATORS, _NOBODY = (
    "annotator", "all_annotators", "coordinators", "nobody")
_SHARING: Dict[str, Dict[str, Optional[str]]] = {
    "class_sheet":       {"who": _ANNOTATOR, "role": WRITER, "link": None},
    # Read-only copies of the planar and the diagnostics file (unit 11b);
    # changes to either are proposed on the proposal sheet.
    "planar_sheet":      {"who": _ANNOTATOR, "role": READER, "link": None},
    "diagnostics_sheet": {"who": _ANNOTATOR, "role": READER, "link": None},
    # Built by the tooling, read by the annotator (generate-status-sheet).
    "status_sheet":      {"who": _ANNOTATOR, "role": READER, "link": None},
    # Where the annotator proposes changes to the sources (unit 11a). The
    # coordinators edit it too (ownership-design Q2), as writers inherited
    # from the root folder.
    "proposal_sheet":    {"who": _ANNOTATOR, "role": WRITER, "link": None},
    # Where the annotator writes notes to the coordinator.
    "notes_doc":         {"who": _ANNOTATOR, "role": WRITER, "link": None},
    # Notebooks and PDF reports keep link sharing until a notebook shared by
    # name is shown to open in Colab for a signed-in annotator (design § 7,
    # Q4). Then they become {"who": _ANNOTATOR, "role": READER, "link": None}.
    "report":            {"who": _NOBODY, "role": None, "link": READER},
    "notebook":          {"who": _NOBODY, "role": None, "link": READER},
    # Contributor charts (laminar-charts): no grants of their own. The
    # language folder they sit in already lets its annotator read them, and
    # coordinators have the root's writer; no link share, since they come
    # from unpublished annotation.
    "charts":            {"who": _NOBODY, "role": None, "link": None},
    "manifest":          {"who": _NOBODY, "role": None, "link": None},
}
# Folders differ by which folder: a language folder lets its annotator see
# their files; the Annotation Status folder holds every language's status
# sheet; the root gives coordinators writer, which everything under it
# inherits; archive folders grant nothing of their own.
_FOLDER_SHARING: Dict[str, Dict[str, Optional[str]]] = {
    "language": {"who": _ANNOTATOR, "role": READER, "link": None},
    "status":   {"who": _ALL_ANNOTATORS, "role": READER, "link": None},
    "root":     {"who": _COORDINATORS, "role": WRITER, "link": None},
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
    from .people import annotator_email, coordinator_emails, every_annotator_email

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
    elif rule["who"] == _COORDINATORS:
        emails = coordinator_emails()
    elif rule["who"] == _NOBODY:
        emails = []
    else:
        raise ValueError(f"unknown sharing rule {rule['who']!r}")
    role = READER if archived else rule["role"]
    link = None if archived else rule["link"]
    return SharingSpec(tuple(sorted((e.lower(), role) for e in emails)), link)


def is_own_grant(grant: Dict) -> bool:
    """A grant made on the file itself, not inherited from its folder (Drive
    marks those in ``permissionDetails``) and not its owner's."""
    if grant.get("role") == "owner":
        return False
    details = grant.get("permissionDetails") or []
    return not (details and all(d.get("inherited") for d in details))


def sharing_differences(spec: SharingSpec, grants: List[Dict]) -> List[str]:
    """How a file's grants (as Drive lists them: type, role, emailAddress,
    permissionDetails) differ from ``spec``. Only the file's own grants count:
    an inherited one is its folder's, checked on the folder. People are named
    as people.yaml names them, never by address, since this goes into GitHub
    issues and planars is public."""
    from .people import name_for_email

    def who(email):
        return name_for_email(email) or "someone not in people.yaml"

    out = []
    own = [g for g in grants if is_own_grant(g)]
    for g in own:
        if g.get("type") == "anyone":
            if spec.link is None:
                out.append(f"shared by link ({g.get('role')}); it should be named people only")
            elif g.get("role") != spec.link:
                out.append(f"its link share gives {g.get('role')}, not {spec.link}")
        elif g.get("type") == "user":
            wanted = spec.role_for(g.get("emailAddress"))
            if wanted is None:
                out.append(f"{who(g.get('emailAddress'))} has {g.get('role')} access "
                           "the sharing rule doesn't give them")
            elif g.get("role") != wanted:
                out.append(f"{who(g.get('emailAddress'))} is a {g.get('role')}, not a {wanted}")
        else:
            out.append(f"shared with a {g.get('type')} ({g.get('role')}); it should be "
                       "named people only")
    held = {(g.get("emailAddress") or "").lower() for g in grants if g.get("type") == "user"}
    for email, role in spec.people:
        if email not in held:
            out.append(f"{who(email)} should be a {role} and has no access")
    if spec.link and not any(g.get("type") == "anyone" for g in grants):
        out.append(f"its {spec.link} link share is missing")
    return out
