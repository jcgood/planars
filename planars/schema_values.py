"""Values owned by schemas/planar.yaml (and a few from diagnostic_classes.yaml),
read in one place.

Every module in planars/ and coding/ that needs the keystone's name, the
Status tab's title and values, the columns that identify a row on each
kind of annotation tab (and the trailing columns after the criteria), a
class's required criteria, or the classes' domain types imports them from
here instead of typing them
(Phase 10, issue #271; hidden-facts entries D0, R3, D3, D4, D5, D-1).
tests/test_no_hidden_facts.py fails if one of these values is typed anywhere
else in the code.

No fallback defaults: a fallback would be a second copy of the value. If
planar.yaml lacks one of these keys, importing this module fails, naming it.
"""
from __future__ import annotations

import copy
import functools
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
STATUS_IN_PROGRESS: str = _require("status_tab", "values", "in_progress")
STATUS_READY: str = _require("status_tab", "values", "ready")
STATUS_VALUES = [STATUS_IN_PROGRESS, STATUS_READY]

_STATUS_ROLES = ("construction", "status", "problems")
_STATUS_OWNERS = ("tooling", "annotator")


def _status_columns() -> list:
    cols = _require("status_tab", "columns")
    roles = [c.get("role") for c in cols]
    if sorted(roles) != sorted(_STATUS_ROLES):
        raise KeyError(f"schemas/planar.yaml status_tab.columns must have each role in "
                       f"{list(_STATUS_ROLES)} exactly once; found {roles}")
    for c in cols:
        if not c.get("name") or c.get("owner") not in _STATUS_OWNERS:
            raise KeyError(f"schemas/planar.yaml status_tab.columns entry {c} needs a name "
                           f"and an owner in {list(_STATUS_OWNERS)}")
    return [dict(c) for c in cols]


_STATUS_COLUMN_SPECS = _status_columns()
STATUS_COLUMNS: list = [c["name"] for c in _STATUS_COLUMN_SPECS]   # in sheet order
_status_by_role = {c["role"]: c["name"] for c in _STATUS_COLUMN_SPECS}
STATUS_CONSTRUCTION_COLUMN: str = _status_by_role["construction"]
STATUS_STATUS_COLUMN: str = _status_by_role["status"]
STATUS_PROBLEMS_COLUMN: str = _status_by_role["problems"]
STATUS_TOOLING_COLUMNS = frozenset(c["name"] for c in _STATUS_COLUMN_SPECS
                                   if c["owner"] == "tooling")


def status_map(rows) -> dict:
    """{construction: status} from a Status tab's cells (header row first),
    found by header name, so a column added or moved doesn't misread it. {}
    for a tab with no rows or without both columns. The one reader of the
    tab's contents: coding/ and planars/reports.py both call it."""
    rows = [list(r) for r in rows or []]
    if len(rows) < 2:
        return {}
    header = [h.strip() for h in rows[0]]
    if STATUS_CONSTRUCTION_COLUMN not in header or STATUS_STATUS_COLUMN not in header:
        return {}
    ci, si = header.index(STATUS_CONSTRUCTION_COLUMN), header.index(STATUS_STATUS_COLUMN)
    out = {}
    for row in rows[1:]:
        name = row[ci].strip() if ci < len(row) else ""
        if name:
            out[name] = row[si].strip() if si < len(row) else ""
    return out


def is_keystone(position_name) -> bool:
    """True if a Position_Name cell names the keystone (case and spaces ignored)."""
    return str(position_name).strip().lower() == KEYSTONE_NAME.lower()


# ---------------------------------------------------------------------------
# Row shapes: the columns before the criteria on each kind of annotation tab
# (hidden-facts entries D3, D4, D5's trailing-column fallbacks; Phase 10).
# ---------------------------------------------------------------------------

TRAILING_COLUMNS: list = list(_require("trailing_columns"))

# Example styles: which trailing columns each leaves out (planar.yaml).
EXAMPLE_STYLES: dict = {name: list((spec or {}).get("omits") or [])
                        for name, spec in _require("example_styles").items()}
for _style, _omits in EXAMPLE_STYLES.items():
    if not set(_omits) <= set(TRAILING_COLUMNS):
        raise KeyError(f"schemas/planar.yaml example_styles.{_style}.omits must be "
                       f"trailing columns ({TRAILING_COLUMNS})")
SYNTHETIC_EXAMPLE_STYLE: str = _require("synthetic_example_style")
EXAMPLE_SEPARATOR: str = _require("example_separator")
if SYNTHETIC_EXAMPLE_STYLE not in EXAMPLE_STYLES:
    raise KeyError(f"schemas/planar.yaml synthetic_example_style must be one of {list(EXAMPLE_STYLES)}")


def example_style(lang_id: str) -> str:
    """How `lang_id`'s examples are written: its languages.yaml meta
    `examples`, or SYNTHETIC_EXAMPLE_STYLE for a synthetic test language.
    Fails on a language with none or an unknown one."""
    from planars.languages import get_entry, is_synthetic
    entry = get_entry(lang_id)
    if entry is None and is_synthetic(lang_id):
        return SYNTHETIC_EXAMPLE_STYLE
    style = ((entry or {}).get("meta") or {}).get("examples")
    if style not in EXAMPLE_STYLES:
        raise ValueError(
            f"{lang_id}: schemas/languages.yaml meta `examples` is {style!r}; it must be one of "
            f"{list(EXAMPLE_STYLES)} (schemas/planar.yaml example_styles).")
    return style


def trailing_columns_for(lang_id: str) -> list:
    """The trailing columns `lang_id`'s annotation tabs carry, in order."""
    omits = EXAMPLE_STYLES[example_style(lang_id)]
    return [c for c in TRAILING_COLUMNS if c not in omits]
def _key_within(where: str, key, columns: list) -> list:
    if not key or not set(key) <= set(columns):
        raise KeyError(f"schemas/planar.yaml {where} must be a non-empty subset of {columns}")
    return list(key)


# The planar file's own columns (planar_{lang_id}.tsv) and the fixed values
# of Position_Type and Class_Type (hidden-facts M0).
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


@functools.lru_cache(maxsize=4)
def _parse_classes(text: str) -> dict:
    return yaml.safe_load(text) or {}


def _class_entry(class_name: str) -> dict:
    # The file is read every call, so an edit is always seen, but parsed only
    # when its text changes: parsing it on every lookup made one command test
    # take 70 seconds (2026-10-17, Phase 10 unit 20). A copy, so a caller
    # changing what it gets back can't change the next caller's answer.
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    for cls in _parse_classes(text).get("classes", []):
        if cls.get("name") == class_name:
            return copy.deepcopy(cls)
    raise KeyError(f"diagnostic_classes.yaml has no class {class_name!r}")


def class_domain_types() -> dict:
    """``{class_name: (domain_type, domain_subtype or None)}`` for every class
    in diagnostic_classes.yaml, in the file's order. A class without a
    domain_type fails here, naming it, rather than falling into a default."""
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    out = {}
    for cls in _parse_classes(text).get("classes", []):
        if not cls.get("domain_type"):
            raise KeyError(f"diagnostic_classes.yaml class {cls.get('name')!r} has no domain_type")
        out[cls["name"]] = (cls["domain_type"], cls.get("domain_subtype"))
    return out


def _construction_entry(class_name: str, construction: str) -> dict:
    for con in _class_entry(class_name).get("constructions") or []:
        if isinstance(con, dict) and con.get("name") == construction:
            return con
    return {}


def prefill_by_label(class_name: str, construction: str) -> dict:
    """A construction's ``prefill_by_label`` in diagnostic_classes.yaml:
    ``{criterion: (value, frozenset of planar labels)}``, the value a new row
    starts with when its element is one of those labels (#318 c). Empty when
    the construction declares none; raises on a malformed entry."""
    return prefill_by_label_of(_construction_entry(class_name, construction),
                               f"{class_name}/{construction}")


def prefill_by_label_of(con: dict, where: str) -> dict:
    """prefill_by_label, applied to one construction's entry (``where`` names it)."""
    where = f"{where} prefill_by_label"
    out = {}
    for crit, spec in (con.get("prefill_by_label") or {}).items():
        if (not isinstance(spec, dict) or set(spec) != {"value", "labels"}
                or not isinstance(spec["labels"], list) or not spec["labels"]):
            raise ValueError(f"diagnostic_classes.yaml {where}: {crit!r} needs exactly "
                             f"'value' and a non-empty 'labels' list, got {spec!r}")
        out[crit] = (str(spec["value"]), frozenset(spec["labels"]))
    return out


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
