"""What each Drive file the tooling writes should look like, built from the schemas.

Phase 10 unit 5 (issue #271); design: docs/drive-door-design.md § 2.1. The
Drive door checks every write against these specs. Nothing here is stored:
each call reads the schemas and the language's own sources (planar TSV,
diagnostics YAML) afresh, so a spec cannot drift from them. A wrong spec shows
up as a wrong check, not as a quietly stale table.

So far: class sheets (`class_sheet_spec`). The other kinds of Drive file get
their sections as unit 5 reaches them (design § 5).

A class sheet is its locked tabs, one tab per construction in the language's
diagnostics file, and Status, in the order `locked_tabs.reorder_tabs` puts
them. Each column has an owner:

  tooling    the columns that identify a row (`planars.schema_values.row_columns`)
             and the Status tab's Construction column. Written by the tooling.
  annotator  criterion columns, the trailing columns (Source, Comments) and
             Status. The tooling may fill an empty one (a new row, a pre-fill)
             but never changes one an annotator has filled, unless the command
             says so through the door (design § 2.4 rule 1).

Which rows an element-row tab has is computed here from the planar. The rows
of a pair-row or keyed-row tab are generated from the tab before it, from what
annotators entered there, so their spec gives only the row key; the rows
themselves are compared by integrity-check's dependent-staleness section.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from planars.schema_values import (
    ELEMENT_ROWS,
    STATUS_COLUMNS,
    STATUS_TAB,
    STATUS_VALUES,
    TRAILING_COLUMNS,
    row_columns,
    row_key,
    row_type,
)

from .biuniqueness_rows import CLASS_NAME as BIUNIQUENESS_CLASS
from .biuniqueness_rows import ELEMENTS as BIUNIQUENESS_ELEMENTS_TAB
from .biuniqueness_rows import element_rows as biuniqueness_element_rows
from .locked_tabs import locked_tab_contents, locked_tab_specs
from .make_forms import _read_diagnostics_for_language, build_element_index, element_rows
from .schemas import apply_schema_criteria, is_free_entry

TOOLING = "tooling"
ANNOTATOR = "annotator"

LOCKED = "locked"
CONSTRUCTION = "construction"
STATUS = "status"


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

    key_col, status_col = STATUS_COLUMNS
    status = TabSpec(
        STATUS_TAB, STATUS,
        (ColumnSpec(key_col, TOOLING, None), ColumnSpec(status_col, ANNOTATOR, tuple(STATUS_VALUES))),
        (key_col,), (key_col,),
        tuple((con,) for con, _, _ in constructions),
    )
    return ClassSheetSpec(lang_id, class_name, tuple(first + middle + last + [status]))
