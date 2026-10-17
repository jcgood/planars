"""Values owned by schemas/planar.yaml (and a few from diagnostic_classes.yaml),
read in one place.

Every module in planars/ and coding/ that needs the keystone's name, the
Status tab's title and values, the columns that identify a row on each
kind of annotation tab (and the trailing columns after the criteria), or a
class's required criteria imports them from here instead of typing them
(Phase 10, issue #271; hidden-facts entries D0, R3, D3, D4, D5, D-1).
tests/test_no_hidden_facts.py fails if one of these values is typed anywhere
else in the code.

No fallback defaults: a fallback would be a second copy of the value. If
planar.yaml lacks one of these keys, importing this module fails, naming it.
"""
from __future__ import annotations

from importlib.resources import files as _res_files

import yaml

_planar = yaml.safe_load(
    _res_files("schemas").joinpath("planar.yaml").read_text(encoding="utf-8")) or {}


def _require(*keys: str):
    value = _planar
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(f"schemas/planar.yaml is missing {'.'.join(keys)}")
        value = value[key]
    return value


KEYSTONE_NAME: str = _require("keystone_position_name")

STATUS_TAB: str = _require("status_tab", "title")
STATUS_COLUMNS: list = list(_require("status_tab", "columns"))
STATUS_IN_PROGRESS: str = _require("status_tab", "values", "in_progress")
STATUS_READY: str = _require("status_tab", "values", "ready")
STATUS_VALUES = [STATUS_IN_PROGRESS, STATUS_READY]


def is_keystone(position_name) -> bool:
    """True if a Position_Name cell names the keystone (case and spaces ignored)."""
    return str(position_name).strip().lower() == KEYSTONE_NAME.lower()


# ---------------------------------------------------------------------------
# Row shapes: the columns before the criteria on each kind of annotation tab
# (hidden-facts entries D3, D4, D5's trailing-column fallbacks; Phase 10).
# ---------------------------------------------------------------------------

TRAILING_COLUMNS: list = list(_require("trailing_columns"))
def _key_within(where: str, key, columns: list) -> list:
    if not key or not set(key) <= set(columns):
        raise KeyError(f"schemas/planar.yaml {where} must be a non-empty subset of {columns}")
    return list(key)


# The planar file's own columns (planar_{lang_id}.tsv) and the fixed values
# of Position_Type and Class_Type (hidden-facts M0).
PLANAR_COLUMNS: list = [c["name"] for c in _require("planar_columns")]
PLANAR_REQUIRED_COLUMNS: list = [c["name"] for c in _require("planar_columns") if c.get("required")]


def _planar_column_values(name: str) -> dict:
    for col in _require("planar_columns"):
        if col["name"] == name:
            if not col.get("values"):
                raise KeyError(f"schemas/planar.yaml planar_columns.{name} has no values")
            return dict(col["values"])
    raise KeyError(f"schemas/planar.yaml planar_columns has no {name}")


_POSITION_TYPES = _planar_column_values("Position_Type")
ZONE: str = _POSITION_TYPES["zone"]
SLOT: str = _POSITION_TYPES["slot"]
POSITION_TYPES: list = list(_POSITION_TYPES.values())
CLASS_TYPES: list = list(_planar_column_values("Class_Type").values())

ELEMENT_ROW_COLUMNS: list = [c["name"] for c in _require("structural_columns")]
ELEMENT_ROW_KEY: list = _key_within("element_row_key", _require("element_row_key"),
                                    ELEMENT_ROW_COLUMNS)
PAIR_ROW_SHAPES: dict = {name: list(_require("pair_row_shapes", name, "columns"))
                         for name in _require("pair_row_shapes")}
PAIR_ROW_KEYS: dict = {name: _key_within(f"pair_row_shapes.{name}.key",
                                         _require("pair_row_shapes", name, "key"), cols)
                       for name, cols in PAIR_ROW_SHAPES.items()}

# Every column that identifies a row on an element-row or pair-row tab. For
# code that has a header but not its construction; anything that knows the
# construction should ask row_columns() instead.
ROW_IDENTITY_COLUMNS = frozenset(ELEMENT_ROW_COLUMNS).union(*PAIR_ROW_SHAPES.values())

ELEMENT_ROWS = "element"


def _class_entry(class_name: str) -> dict:
    classes = yaml.safe_load(
        _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")) or {}
    for cls in classes.get("classes", []):
        if cls.get("name") == class_name:
            return cls
    raise KeyError(f"diagnostic_classes.yaml has no class {class_name!r}")


def _construction_entry(class_name: str, construction: str) -> dict:
    for con in _class_entry(class_name).get("constructions") or []:
        if isinstance(con, dict) and con.get("name") == construction:
            return con
    return {}


def source_construction(class_name: str) -> str:
    """The one tab a class's other tabs are generated from: the target of its
    constructions' ``depends_on`` (e.g. nonpermutability's
    element_prescreening). Raises unless exactly one tab is depended on —
    biuniqueness_deviations' chain has two, and its code reads its own chain
    (planars.biuniqueness_deviations._tab_chain). Hidden-facts R4: the
    prescreening TSV's name was typed into each pair builder."""
    targets = {c["depends_on"] for c in _class_entry(class_name).get("constructions") or []
               if isinstance(c, dict) and c.get("depends_on")}
    if len(targets) != 1:
        raise ValueError(f"diagnostic_classes.yaml class {class_name!r}: expected one tab that "
                         f"others depend_on, found {sorted(targets)}")
    return targets.pop()


def required_criteria(class_name: str) -> frozenset:
    """The class's ``required_criteria`` in diagnostic_classes.yaml: the
    criterion columns an analysis module's loader insists on (hidden-facts
    D-1; each module used to type its own copy). Raises if the class has no
    ``required_criteria`` field (an empty list is a real answer)."""
    cls = _class_entry(class_name)
    if "required_criteria" not in cls:
        raise KeyError(f"diagnostic_classes.yaml class {class_name!r} has no required_criteria")
    return frozenset(cls["required_criteria"] or [])


PAIR_ROWS = "pair_rows"
KEYED_ROWS = "keyed_rows"
ROW_TYPES = (ELEMENT_ROWS, PAIR_ROWS, KEYED_ROWS)


# The rules, applied to one construction's entry in diagnostic_classes.yaml
# (``{}`` for a construction the class does not list). ``where`` names it in
# errors. Callers that already hold the entry (coding.restructure_sheets'
# _get_keyed_row_constructions) use these; everyone else uses the
# (class_name, construction) forms below. Anything the schema does not
# declare fully is an error, never a guess.

def row_type_of(con: dict, where: str) -> str:
    value = con.get("row_type", ELEMENT_ROWS)
    if value not in ROW_TYPES:
        raise ValueError(f"diagnostic_classes.yaml {where}: unknown row_type "
                         f"{value!r}; expected one of {list(ROW_TYPES)}")
    return value


def row_columns_of(con: dict, where: str) -> list:
    kind = row_type_of(con, where)
    if kind == ELEMENT_ROWS:
        return list(ELEMENT_ROW_COLUMNS)
    if kind == "pair_rows":
        shape = con.get("pair_shape")
        if shape not in PAIR_ROW_SHAPES:
            raise ValueError(f"diagnostic_classes.yaml {where}: pair_shape {shape!r} is not "
                             f"one of planar.yaml's pair_row_shapes {sorted(PAIR_ROW_SHAPES)}")
        return list(PAIR_ROW_SHAPES[shape])
    columns, key = con.get("keyed_columns"), con.get("key")
    if not columns or not key or not set(key) <= set(columns):
        raise ValueError(f"diagnostic_classes.yaml {where}: a keyed_rows construction must "
                         f"declare keyed_columns and a key drawn from them "
                         f"(got keyed_columns={columns}, key={key})")
    return list(columns)


def row_key_of(con: dict, where: str) -> list:
    row_columns_of(con, where)  # validates everything below
    kind = row_type_of(con, where)
    if kind == ELEMENT_ROWS:
        return list(ELEMENT_ROW_KEY)
    if kind == "pair_rows":
        return list(PAIR_ROW_KEYS[con["pair_shape"]])
    return list(con["key"])


def row_type(class_name: str, construction: str) -> str:
    """``element``, ``pair_rows`` or ``keyed_rows``. A construction the class
    does not list under ``constructions``, or lists without ``row_type``, has
    element rows (the schema's documented convention)."""
    return row_type_of(_construction_entry(class_name, construction),
                       f"{class_name}/{construction}")


def row_columns(class_name: str, construction: str) -> list:
    """The columns that identify a row on this construction's tab, in order."""
    return row_columns_of(_construction_entry(class_name, construction),
                          f"{class_name}/{construction}")


def row_key(class_name: str, construction: str) -> list:
    """The columns that identify one row on this construction's tab (answers
    are carried over by them when a tab is rebuilt): a subset of
    row_columns(), in the schema's order."""
    return row_key_of(_construction_entry(class_name, construction),
                      f"{class_name}/{construction}")


def header_shape(header) -> "str | None":
    """Which element- or pair-row shape a tab's header starts with: ``"element"``,
    a ``pair_row_shapes`` name, or None if it starts with none of them. For code
    that holds a header but not its construction."""
    header = list(header)
    shapes = {ELEMENT_ROWS: ELEMENT_ROW_COLUMNS, **PAIR_ROW_SHAPES}
    for name, cols in shapes.items():
        if header[:len(cols)] == cols:
            return name
    return None
