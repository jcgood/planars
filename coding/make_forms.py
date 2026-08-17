from __future__ import annotations

import copy
import re
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml
from pandera.errors import SchemaError

from .contracts import VALID_CLASS_TYPES, class_type_schema, position_integer_schema, position_is_integer
from .schemas import load_planar_schema

_BRACE_SUFFIX_RE = re.compile(r'\{[^}]*\}$')


def _registry_element_types(planar_schema: Dict) -> Dict[str, str]:
    """Flatten element_conventions.standard_labels.* into {label: element_type}."""
    standard_labels = (planar_schema.get("element_conventions") or {}).get("standard_labels") or {}
    out: Dict[str, str] = {}
    for group_name in ("phrase_types", "adverb_scope_labels", "other_labels"):
        group = standard_labels.get(group_name)
        items = group.get("items") if isinstance(group, dict) else group
        for item in items or []:
            label = item.get("label")
            element_type = item.get("element_type")
            if label and element_type:
                out[label] = element_type
    return out


def _formative_exceptions(planar_schema: Dict) -> set:
    """Literal forms exempted from the ALL CAPS -> category-label rule (e.g. 'I')."""
    conventions = planar_schema.get("element_type_conventions") or {}
    exceptions = conventions.get("formative_capitalization_exceptions") or {}
    return {item["form"] for item in (exceptions.get("items") or []) if item.get("form")}


def classify_element(token: str, planar_schema: Dict | None = None) -> str:
    """Classify a single Elements-cell token per schemas/planar.yaml's element_type rules.

    Returns one of:
        "formative"           — a bottom-level unit (concrete form, in any script,
                                 or a non-phrasal category placeholder like PRON).
        "embedded_structure"  — stands for an entire embedded planar structure
                                 (e.g. NP{S,A}), with its own internal positions.
        "reserved"             — the special KEYSTONE marker.
        "unknown"              — looks like an ALL CAPS category label by typography
                                 but has no matching entry in planar.yaml's
                                 standard_labels. Never silently defaulted to
                                 "formative" — callers should treat this as an
                                 error requiring the label to be registered.

    Typography check is Unicode-aware (str.isupper(), not an ASCII [A-Z] test):
    a brace-suffix-stripped token counts as an ALL CAPS category-label candidate
    if every cased character in it is uppercase, regardless of script. This
    matters because formatives (returned as "formative") may be non-ASCII in
    future languages and must not be misclassified by an ASCII-only check.
    formative_capitalization_exceptions in planar.yaml carves out ordinary
    lexical items conventionally capitalized in their own orthography (e.g.
    English "I") so they aren't mistaken for category-label candidates.
    """
    if planar_schema is None:
        planar_schema = load_planar_schema()

    stripped = _BRACE_SUFFIX_RE.sub("", token.strip())

    if stripped in _formative_exceptions(planar_schema):
        return "formative"

    if stripped == "KEYSTONE":
        return "reserved"

    if not stripped.isupper():
        return "formative"

    return _registry_element_types(planar_schema).get(stripped, "unknown")


def classify_biuniqueness_scope(token: str, planar_schema: Dict | None = None) -> str:
    """Classify a single Elements-cell token for the Biuniqueness_Scope column
    (issue #254 Part 2a — Stage 0 of the biuniqueness/allomorphy Sheet pipeline).

    Returns one of:
        "filled"          — a concrete listed form (formative, not an ALL CAPS
                             category placeholder) — a direct candidate for Stage 1's
                             has_allomorphs annotation.
        "open_category"   — a formative ALL CAPS category placeholder (e.g. PRON,
                             VERBPART) standing for an open/closed class of forms —
                             not itself annotable; needs Stage 2 to expand it into
                             specific member forms first.
        "excluded"         — embedded_structure (stands for a whole embedded planar
                             structure, not a morph) or reserved (KEYSTONE) — biuniqueness/
                             allomorphy is a morph-level phenomenon and applies to neither.
        "unknown"          — the token's Element_Types classification is itself
                             "unknown" (unregistered ALL CAPS label) — never silently
                             defaulted; register the label in planar.yaml first.

    Built entirely on top of classify_element() and the same typography rule it uses —
    no independent registry data (see planar.yaml's Biuniqueness_Scope description).
    """
    if planar_schema is None:
        planar_schema = load_planar_schema()

    element_type = classify_element(token, planar_schema)
    if element_type in ("embedded_structure", "reserved"):
        return "excluded"
    if element_type == "unknown":
        return "unknown"

    stripped = _BRACE_SUFFIX_RE.sub("", token.strip())
    if stripped in _formative_exceptions(planar_schema):
        return "filled"
    return "open_category" if stripped.isupper() else "filled"


def _resolve_path(filename: str, data_dir: Path | str) -> Path:
    """Resolve a filename against data_dir."""
    return Path(data_dir) / filename


def _infer_language_id_from_planar_filename(planar_filename: str) -> str:
    """Extract the language ID from a planar filename.

    Accepts both bare (planar_<lang>.tsv) and dated (planar_<lang>-<date>.tsv)
    filenames. Only the portion before the first hyphen after the 'planar_' prefix
    is treated as the language ID.

    Args:
        planar_filename: basename or path of the planar TSV file.

    Returns:
        The language ID string (e.g. 'stan1293').

    Raises:
        ValueError: if the filename doesn't start with 'planar_' or the ID is empty.
    """
    # Accept: planar_<lang>.tsv OR planar_<lang>-<date>.tsv
    stem = Path(planar_filename).stem
    if not stem.startswith("planar_"):
        raise ValueError(
            f"Expected planar filename to start with 'planar_', got '{planar_filename}'"
        )

    remainder = stem[len("planar_") :]
    # If a date/version suffix exists, drop it (e.g., stan1293-20260209 -> stan1293)
    lang_id = remainder.split("-", 1)[0].strip()
    if not lang_id:
        raise ValueError(f"Could not infer language id from '{planar_filename}'")
    return lang_id


# value tuple: (Position_Number, Position_Name, Language_ID, Element_Plain)
ElementIndex = Dict[str, Tuple[int, str, str, str]]


def _split_elements(elements_raw: str) -> List[str]:
    """Split a comma-separated elements string, ignoring commas inside braces.

    E.g. 'QWORDS, NP{S,A,P}' -> ['QWORDS', 'NP{S,A,P}']
    """
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in elements_raw:
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def build_element_index(planar_filename: str, data_dir: Path | str) -> ElementIndex:
    """Build a mapping with unique keys per element occurrence in a planar TSV.

    Each element that appears in the planar structure gets a key of the form
    ``f"{element_plain}@{position_number}"`` so the same element name can appear
    in multiple positions without collision.

    Args:
        planar_filename: basename of the planar TSV file. Must have columns:
            Class_Type, Elements, Position_Name, Position.
        data_dir: directory containing the planar TSV file.

    Returns:
        Dict mapping ``"element@pos"`` keys to
        ``(position_number, position_name, language_id, element_plain)`` tuples.

    Raises:
        ValueError: if required columns are missing, Position is non-integer,
            a duplicate key is found, or Class_Type is unexpected.
    """
    lang_id = _infer_language_id_from_planar_filename(planar_filename)
    path = _resolve_path(planar_filename, data_dir)

    df = pd.read_csv(path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required_cols = {"Class_Type", "Elements", "Position_Name", "Position"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    # Normalize once (strip everything, lowercase Class_Type) and filter to
    # this language's rows, so the pandera checks below and the row-by-row
    # indexing loop that follows both work off the same values instead of
    # each re-deriving them and risking drift. A row with blank Position or
    # blank Elements is a placeholder, not a contract violation, so it's
    # filtered out here rather than checked — mirrors the original
    # hand-written loop's own skip order (see contracts.py's module
    # docstring for the two-stage narrowing this reproduces).
    work = df.copy()
    for col in ("Language_ID", "Class_Type", "Elements", "Position_Name", "Position"):
        work[col] = work[col].astype(str).str.strip() if col in work.columns else ""
    work["Class_Type"] = work["Class_Type"].str.lower()
    work = work[work["Language_ID"] == lang_id]

    has_position = work[work["Position"] != ""]
    try:
        position_integer_schema().validate(has_position)
    except SchemaError as e:
        bad = has_position.loc[~position_is_integer(has_position["Position"]), "Position"].iloc[0]
        raise ValueError(f"{e.check.error} Found: '{bad}'.") from e

    has_elements = has_position[has_position["Elements"] != ""]
    try:
        class_type_schema().validate(has_elements)
    except SchemaError as e:
        bad_row = has_elements.loc[~has_elements["Class_Type"].isin(VALID_CLASS_TYPES)].iloc[0]
        raise ValueError(
            f"Unexpected Class_Type '{bad_row['Class_Type']}' at position {bad_row['Position']}."
        ) from e

    element_to_info: ElementIndex = {}

    def add_element(element_plain: str, pos: int, position_name: str) -> None:
        """Register one element occurrence; raise if the (element, pos) key is duplicate."""
        element_plain = (element_plain or "").strip()
        if not element_plain:
            return

        key = f"{element_plain}@{pos}"
        if key in element_to_info:
            raise ValueError(
                f"Duplicate unique key '{key}' (element repeated within same position?)"
            )

        element_to_info[key] = (pos, position_name, lang_id, element_plain)

    # "open", "list", and "mixed" class types all enumerate individual
    # elements the same way for indexing purposes -- the distinction between
    # them matters for form generation and ALL-CAPS convention checking
    # (validate_planar.py), not here.
    for _, row in has_elements.iterrows():
        for element_plain in _split_elements(row["Elements"]):
            add_element(element_plain, int(row["Position"]), row["Position_Name"])

    return element_to_info


def planar_to_manifest_dict(planar_path: Path, lang_id: str) -> dict:
    """Read a planar TSV and return a compact JSON-serializable structure.

    Stored in the Drive manifest so Colab notebooks can derive nonpermutability
    spans without needing local TSV access. Mirrors the data structures built by
    planars.nonpermutability._load_planar, using bracket-wrapping for hyphenated
    element names.

    Returns:
        {
          "keystone_pos": int,
          "positions": [{"pos": int, "name": str, "type": str, "elements": [str]}, ...]
        }
    The keystone position itself is not included in "positions" (it is excluded
    from pair generation), matching _load_planar(keystone_active=False) behaviour.
    """
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id]
    keystone_name = "v:verbstem"
    keystone_pos: int | None = None
    positions = []
    for _, row in df.iterrows():
        pos = int(row["Position"])
        pname = row["Position_Name"].strip()
        ptype = row["Position_Type"].strip()
        raw_elems = _split_elements(row.get("Elements", "") or "")
        elements = [
            f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e
            for e in raw_elems
        ]
        if pname.lower() == keystone_name:
            keystone_pos = pos
            continue
        positions.append({"pos": pos, "name": pname, "type": ptype, "elements": elements})
    return {"keystone_pos": keystone_pos, "positions": positions}


def _resolve_diagnostics_path(lang_id: str, data_dir: Path | str) -> Path:
    """Find the language-specific diagnostics file in the lang_setup folder.

    Expected name: diagnostics_{lang_id}.tsv
    """
    p = Path(data_dir) / f"diagnostics_{lang_id}.tsv"
    if p.exists():
        return p
    raise FileNotFoundError(f"Could not find diagnostics_{lang_id}.tsv in {data_dir}")


def _resolve_diagnostics_yaml_path(lang_id: str, data_dir: Path | str) -> Path:
    """Return the path for diagnostics_{lang_id}.yaml (may not exist yet)."""
    return Path(data_dir) / f"diagnostics_{lang_id}.yaml"


# ---------------------------------------------------------------------------
# Compact YAML dumper — writes lists as inline [y, n] style
# ---------------------------------------------------------------------------

class _CompactDumper(yaml.Dumper):
    pass


def _inline_list_representer(dumper: yaml.Dumper, data: list) -> Any:
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


_CompactDumper.add_representer(list, _inline_list_representer)


def _dump_diagnostics_yaml(data: dict) -> str:
    """Serialize a diagnostics YAML dict to a string with inline value lists."""
    return yaml.dump(
        data,
        Dumper=_CompactDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


# ---------------------------------------------------------------------------
# keystone_active resolution
# ---------------------------------------------------------------------------

def resolve_keystone_active(
    lang_id: str,
    class_name: str,
    construction: Optional[str] = None,
    data_dir: Path | str = "",
) -> Optional[bool]:
    """Resolve keystone_active for a (lang, class, construction) triple.

    Two-level lookup:
    1. diagnostics_{lang}.yaml → classes → {class} → keystone_active
       - bool: applies to all constructions in the class
       - dict: look up by construction name specifically
    2. diagnostic_classes.yaml → class → keystone_active_default

    Returns:
        True  — keystone participates; require real criterion values on keystone row.
        False — keystone is inactive; require 'na' on keystone row.
        None  — unspecified at both levels (treat as False; warn via check-codebook).
    """
    # Level 1: language YAML
    yaml_path = _resolve_diagnostics_yaml_path(lang_id, data_dir)
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as _f:
            _yaml_data = yaml.safe_load(_f) or {}
        _class_data = (_yaml_data.get("classes") or {}).get(class_name, {})
        _ka = _class_data.get("keystone_active")
        if _ka is not None:
            if isinstance(_ka, bool):
                return _ka
            if isinstance(_ka, dict) and construction is not None:
                _val = _ka.get(construction)
                if isinstance(_val, bool):
                    return _val
                # construction not in dict → fall through to class default

    # Level 2: diagnostic_classes.yaml default
    try:
        from .schemas import load_diagnostic_classes
        _schema = load_diagnostic_classes()
    except Exception:
        return None
    for _cls in _schema.get("classes", []):
        if _cls.get("name") == class_name:
            _default = _cls.get("keystone_active_default")
            if isinstance(_default, bool):
                return _default
            return None  # "[NEEDS REVIEW]" or absent
    return None


def resolve_keystone_na_criteria(
    class_name: str,
) -> List[str]:
    """Return criteria that must always be 'na' on the keystone row for this class.

    These are criteria that are self-referential on the keystone (e.g., 'independence'
    asks whether an element's stress is independent *of* the keystone — a circular
    question for the keystone itself).

    Reads keystone_na_criteria from diagnostic_classes.yaml. Returns an empty list
    if the field is absent or the class is not found.
    """
    try:
        from .schemas import load_diagnostic_classes
        _schema = load_diagnostic_classes()
    except Exception:
        return []
    for _cls in _schema.get("classes", []):
        if _cls.get("name") == class_name:
            val = _cls.get("keystone_na_criteria")
            if isinstance(val, list):
                return [str(c) for c in val]
            return []
    return []


# ---------------------------------------------------------------------------
# TSV ↔ YAML serializers
# ---------------------------------------------------------------------------

def _encode_criteria_dict(criteria_dict: Dict[str, List[str]]) -> List[str]:
    """Encode a {name: values} criteria dict to brace-syntax strings.

    Criteria with the default [y, n] values are emitted as plain names;
    all others use the ``name{v1/v2/...}`` brace syntax.
    """
    parts = []
    for crit_name, crit_values in criteria_dict.items():
        if list(crit_values) == ["y", "n"]:
            parts.append(crit_name)
        else:
            parts.append(f"{crit_name}{{{'/'.join(crit_values)}}}")
    return parts


def _yaml_to_tsv_df(yaml_data: dict, lang_id: str) -> pd.DataFrame:
    """Convert a diagnostics YAML dict to a TSV-format DataFrame.

    The returned DataFrame has columns: Class, Language, Constructions, Criteria.
    Criteria with non-default values are encoded with brace syntax (e.g.
    ``accented{y/n/both}``); default [y, n] criteria use plain names.

    For classes that use ``construction_criteria`` (per-construction criteria),
    one row is emitted per construction so that each row's Criteria column
    carries only the criteria relevant to that construction.  Classes that use
    the shared ``criteria`` key (the common case) emit a single row with all
    constructions comma-separated, preserving backward compatibility.
    """
    rows = []
    for class_name, class_data in yaml_data.get("classes", {}).items():
        constructions = class_data.get("constructions", [])
        criteria_dict: Dict[str, List[str]] = class_data.get("criteria", {})
        construction_criteria: Dict[str, Dict[str, List[str]]] = class_data.get("construction_criteria", {})

        if construction_criteria:
            # Per-construction criteria: one row per construction with its own criteria.
            # Constructions not listed in construction_criteria fall back to the class-level
            # criteria dict (which may be empty if all constructions have their own entries).
            for construction in constructions:
                cc = construction_criteria.get(construction, criteria_dict)
                rows.append({
                    "Class": class_name,
                    "Language": lang_id,
                    "Constructions": construction,
                    "Criteria": ", ".join(_encode_criteria_dict(cc)),
                })
        else:
            # Shared criteria: one row per class with all constructions (existing behavior).
            rows.append({
                "Class": class_name,
                "Language": lang_id,
                "Constructions": ", ".join(constructions),
                "Criteria": ", ".join(_encode_criteria_dict(criteria_dict)),
            })
    return pd.DataFrame(rows, columns=["Class", "Language", "Constructions", "Criteria"])


def _tsv_df_to_yaml(df: pd.DataFrame, lang_id: str) -> dict:
    """Convert a diagnostics TSV DataFrame to a YAML-format dict.

    Used for migrating existing TSVs to YAML and for round-tripping TSV
    changes back into YAML.  Each TSV row (one per class) becomes a class
    entry; constructions are expanded into a list; criteria brace syntax is
    decoded into explicit value lists.

    When multiple rows share the same Class (produced by ``_yaml_to_tsv_df``
    for classes with ``construction_criteria``), the rows are merged back into
    a ``construction_criteria`` dict so the round-trip is lossless.
    """
    classes: Dict[str, Any] = {}
    for _, row in df.iterrows():
        lang = str(row.get("Language", "")).strip()
        if lang != lang_id:
            continue

        class_name = str(row.get("Class", "")).strip()
        constructions = _parse_csv_list(str(row.get("Constructions", "")))
        criterion_names, criterion_values = _parse_criterion_specs(str(row.get("Criteria", "")))
        crit_dict = {name: criterion_values[name] for name in criterion_names}

        if class_name not in classes:
            classes[class_name] = {
                "constructions": list(constructions),
                "criteria": crit_dict,
            }
        else:
            # Second (or later) row for the same class: convert to construction_criteria.
            existing = classes[class_name]
            if "construction_criteria" not in existing:
                # Promote the first row's entry to construction_criteria format.
                prev_constructions = existing.get("constructions", [])
                prev_criteria = existing.get("criteria", {})
                existing["construction_criteria"] = {
                    c: dict(prev_criteria) for c in prev_constructions
                }
                existing.pop("criteria", None)
            # Append this row's construction(s) with their per-construction criteria.
            for c in constructions:
                existing["construction_criteria"][c] = crit_dict
                if c not in existing["constructions"]:
                    existing["constructions"].append(c)

    return {"language": lang_id, "classes": classes}


def _parse_csv_list(value: str) -> List[str]:
    """Split a comma-separated string into a list of non-empty stripped tokens."""
    return [v.strip() for v in (value or "").split(",") if v.strip()]


_DEFAULT_CRITERION_VALUES = ["y", "n"]


def _parse_criterion_spec(spec: str) -> Tuple[str, List[str]]:
    """Parse a diagnostic criterion specification into (name, allowed_values).

    Examples:
        'free'              -> ('free', ['y', 'n'])
        'stressable{y/n/both}' -> ('stressable', ['y', 'n', 'both'])
    """
    spec = spec.strip()
    if "{" in spec:
        if not spec.endswith("}"):
            raise ValueError(f"Malformed criterion spec (missing closing brace): '{spec}'")
        name, _, values_str = spec[:-1].partition("{")
        values = [v.strip() for v in values_str.split("/") if v.strip()]
        if not values:
            raise ValueError(f"Criterion spec has empty value list: '{spec}'")
        return name.strip(), values
    return spec, list(_DEFAULT_CRITERION_VALUES)


def _parse_criterion_specs(value: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Parse a comma-separated criterion specs string.

    Returns (criterion_names, criterion_values) where criterion_values maps each name
    to its allowed values list.
    """
    criterion_names: List[str] = []
    criterion_values: Dict[str, List[str]] = {}
    for spec in _parse_csv_list(value):
        name, values = _parse_criterion_spec(spec)
        criterion_names.append(name)
        criterion_values[name] = values
    return criterion_names, criterion_values


def _read_diagnostics_for_language(
    language_id: str,
    data_dir: Path | str,
) -> List[Tuple[str, str, List[str], Dict[str, List[str]]]]:
    """Read diagnostics for a language, preferring YAML over TSV.

    Checks for diagnostics_{lang_id}.yaml first; falls back to
    diagnostics_{lang_id}.tsv if the YAML is absent.

    Each row is (class_name, construction, criterion_names, criterion_values) where
    criterion_values maps each criterion name to its list of allowed values.
    """
    yaml_path = _resolve_diagnostics_yaml_path(language_id, data_dir)
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        df = _yaml_to_tsv_df(yaml_data, language_id)
    else:
        diag_path = _resolve_diagnostics_path(language_id, data_dir)
        df = pd.read_csv(diag_path, sep="\t", header=0, dtype=str, keep_default_na=False)

    required = {"Class", "Language", "Constructions", "Criteria"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Diagnostics file missing required columns: {sorted(missing)}")

    out: List[Tuple[str, str, List[str], Dict[str, List[str]]]] = []

    for _, row in df.iterrows():
        lang = (row.get("Language", "") or "").strip()
        if lang != language_id:
            continue

        class_name = (row.get("Class", "") or "").strip()
        constructions = _parse_csv_list(row.get("Constructions", ""))
        criterion_names, criterion_values = _parse_criterion_specs(row.get("Criteria", ""))

        if not class_name:
            raise ValueError("Diagnostics file has a row with empty Class.")
        if not constructions:
            continue

        for construction in constructions:
            out.append((class_name, construction, criterion_names, criterion_values))

    return out


# ---------------------------------------------------------------------------
# TSV → YAML diff and apply
# ---------------------------------------------------------------------------

def _diff_diagnostics_tsv_yaml(
    tsv_df: pd.DataFrame,
    yaml_data: dict,
    lang_id: str,
) -> "Tuple[List[Dict], List[Dict]]":
    """Diff a diagnostics TSV DataFrame against a YAML dict.

    Parses both into a normalized structure and categorises each difference
    as deterministic (safe to auto-apply) or ambiguous (requires coordinator
    review with string-distance suggestions).

    Deterministic changes:
        class_added, construction_added, construction_removed,
        criterion_added, criterion_removed, criterion_values_changed

    Ambiguous changes:
        unknown_class   — class in TSV not in YAML and no close match in schema
        class_removed   — class in YAML absent from TSV (may be intentional)
        unknown_criterion — criterion not in diagnostic_criteria.yaml

    Args:
        tsv_df: DataFrame with columns Class, Language, Constructions, Criteria.
        yaml_data: dict loaded from diagnostics_{lang_id}.yaml.
        lang_id: language ID string.

    Returns:
        (deterministic, ambiguous) — two lists of change dicts. Each dict has
        at least 'kind' and 'class_name' keys; additional keys depend on kind.
    """
    from coding.schemas import load_diagnostic_classes, load_diagnostic_criteria

    diag_classes = load_diagnostic_classes()
    diag_criteria = load_diagnostic_criteria()
    # diagnostic_classes.yaml: {"classes": [{"name": "ciscategorial", ...}, ...]}
    known_classes = {entry["name"] for entry in diag_classes.get("classes", []) if "name" in entry}
    # diagnostic_criteria.yaml: {"analyses": [{"name": ..., "diagnostic_criteria": [...]}, ...]}
    known_criteria: set = set()
    for analysis in diag_criteria.get("analyses", []):
        for crit in analysis.get("diagnostic_criteria", []):
            if isinstance(crit, str):
                known_criteria.add(crit)
            elif isinstance(crit, dict) and "name" in crit:
                known_criteria.add(crit["name"])

    # --- parse TSV into normalised structure ---
    # Multiple rows for the same class (produced by construction_criteria classes) are
    # merged: constructions are unioned and criteria are aggregated into a flat dict.
    tsv_classes: Dict[str, Dict] = {}
    for _, row in tsv_df.iterrows():
        lang = str(row.get("Language", "")).strip()
        if lang != lang_id:
            continue
        class_name = str(row.get("Class", "")).strip()
        constructions = set(_parse_csv_list(str(row.get("Constructions", ""))))
        crit_names, crit_values = _parse_criterion_specs(str(row.get("Criteria", "")))
        row_criteria = {n: crit_values[n] for n in crit_names}
        if class_name not in tsv_classes:
            tsv_classes[class_name] = {
                "constructions": constructions,
                "criteria": row_criteria,
            }
        else:
            tsv_classes[class_name]["constructions"].update(constructions)
            tsv_classes[class_name]["criteria"].update(row_criteria)

    # --- parse YAML into normalised structure ---
    # For classes with construction_criteria, flatten all per-construction criteria
    # into a single aggregate dict for diff purposes (construction-level attribution
    # is preserved in the YAML itself; the diff only tracks presence/absence/values).
    yaml_classes: Dict[str, Dict] = {}
    for class_name, class_data in (yaml_data.get("classes") or {}).items():
        constructions = set(class_data.get("constructions") or [])
        criteria = dict(class_data.get("criteria") or {})
        for cc in (class_data.get("construction_criteria") or {}).values():
            criteria.update(cc)
        yaml_classes[class_name] = {
            "constructions": constructions,
            "criteria": criteria,
        }

    deterministic: List[Dict] = []
    ambiguous: List[Dict] = []

    # --- classes in TSV but not in YAML ---
    for class_name in tsv_classes:
        if class_name not in yaml_classes:
            # Serialize constructions as a sorted list — sets are not JSON-serializable.
            serializable_data = {**tsv_classes[class_name],
                                 "constructions": sorted(tsv_classes[class_name]["constructions"])}
            if class_name in known_classes:
                deterministic.append({"kind": "class_added", "class_name": class_name,
                                      "data": serializable_data})
            else:
                suggestions = get_close_matches(class_name, known_classes, n=3, cutoff=0.6)
                ambiguous.append({"kind": "unknown_class", "class_name": class_name,
                                  "suggestions": suggestions, "data": serializable_data})

    # --- classes in YAML but not in TSV ---
    for class_name in yaml_classes:
        if class_name not in tsv_classes:
            ambiguous.append({"kind": "class_removed", "class_name": class_name})

    # --- classes present in both: diff constructions and criteria ---
    for class_name in tsv_classes:
        if class_name not in yaml_classes:
            continue
        tsv = tsv_classes[class_name]
        yml = yaml_classes[class_name]

        for c in tsv["constructions"] - yml["constructions"]:
            deterministic.append({"kind": "construction_added", "class_name": class_name,
                                   "construction": c})
        for c in yml["constructions"] - tsv["constructions"]:
            deterministic.append({"kind": "construction_removed", "class_name": class_name,
                                   "construction": c})

        for crit in tsv["criteria"]:
            if crit not in yml["criteria"]:
                if crit in known_criteria:
                    deterministic.append({"kind": "criterion_added", "class_name": class_name,
                                          "criterion": crit, "values": tsv["criteria"][crit]})
                else:
                    suggestions = get_close_matches(crit, known_criteria, n=3, cutoff=0.6)
                    ambiguous.append({"kind": "unknown_criterion", "class_name": class_name,
                                      "criterion": crit, "suggestions": suggestions,
                                      "values": tsv["criteria"][crit]})
            elif tsv["criteria"][crit] != yml["criteria"][crit]:
                deterministic.append({"kind": "criterion_values_changed",
                                      "class_name": class_name, "criterion": crit,
                                      "old_values": yml["criteria"][crit],
                                      "new_values": tsv["criteria"][crit]})

        for crit in yml["criteria"]:
            if crit not in tsv["criteria"]:
                deterministic.append({"kind": "criterion_removed", "class_name": class_name,
                                      "criterion": crit})

    return deterministic, ambiguous


def _apply_yaml_diff(yaml_data: dict, deterministic_changes: "List[Dict]") -> dict:
    """Apply deterministic diff changes to a YAML dict, returning a new dict.

    Preserves notes and any other YAML-only fields. Does not touch ambiguous
    changes — those are left for coordinator review.

    Args:
        yaml_data: original YAML dict (not mutated).
        deterministic_changes: list of change dicts from _diff_diagnostics_tsv_yaml.

    Returns:
        New YAML dict with changes applied.
    """
    data = copy.deepcopy(yaml_data)
    classes = data.setdefault("classes", {})

    for change in deterministic_changes:
        kind = change["kind"]
        class_name = change["class_name"]

        if kind == "class_added":
            entry = change["data"]
            classes[class_name] = {
                "constructions": sorted(entry["constructions"]),
                "criteria": entry["criteria"],
            }

        elif kind == "construction_added":
            cons = classes[class_name].setdefault("constructions", [])
            if change["construction"] not in cons:
                cons.append(change["construction"])

        elif kind == "construction_removed":
            cons = classes[class_name].get("constructions", [])
            if change["construction"] in cons:
                cons.remove(change["construction"])

        elif kind == "criterion_added":
            classes[class_name].setdefault("criteria", {})[change["criterion"]] = change["values"]

        elif kind == "criterion_removed":
            classes[class_name].get("criteria", {}).pop(change["criterion"], None)

        elif kind == "criterion_values_changed":
            classes[class_name].setdefault("criteria", {})[change["criterion"]] = change["new_values"]

    return data
