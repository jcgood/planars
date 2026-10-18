"""Cached loaders for the planars YAML schema files.

Provides module-level cached access to diagnostic_classes.yaml (merged with
diagnostic_classes_status.yaml), diagnostic_criteria.yaml and planar.yaml so
multiple callers in the same process share a single file read rather than each
opening the file independently. Also holds the readers built on them
(``criterion_values``, ``reads_from``, the value-placeholder helpers,
``criteria_for``).

languages.yaml is intentionally excluded: it is written to by ``lookup-lang``
mid-session and read at specific workflow points where freshness matters.
A shared cache would return stale data after a write. Each caller that needs
languages.yaml loads it directly at the point of use.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent

_diagnostic_classes_cache: Dict | None = None
_diagnostic_criteria_cache: Dict | None = None
_planar_schema_cache: Dict | None = None


def load_diagnostic_classes() -> Dict:
    """Return diagnostic_classes.yaml merged with diagnostic_classes_status.yaml
    (cached per process), keyed by class ``name``.

    The two files split the linguistic content of an analysis class from its
    process/tracking state (Phase 3, issue #271); every existing reader wants
    both together, so this loader merges them transparently and returns the
    same shape callers relied on before the split: ``{"classes": [{name, ...}, ...]}``.
    Returns an empty dict if diagnostic_classes.yaml is missing.
    """
    global _diagnostic_classes_cache
    if _diagnostic_classes_cache is None:
        path = ROOT / "schemas" / "diagnostic_classes.yaml"
        status_path = ROOT / "schemas" / "diagnostic_classes_status.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            status_by_name: Dict[str, Dict] = {}
            if status_path.exists():
                with open(status_path, encoding="utf-8") as f:
                    status_data = yaml.safe_load(f) or {}
                for entry in status_data.get("classes", []) or []:
                    if isinstance(entry, dict) and entry.get("name"):
                        status_by_name[entry["name"]] = entry
            merged_classes = []
            for cls in data.get("classes", []) or []:
                merged = dict(cls)
                merged.update(status_by_name.get(cls.get("name"), {}))
                merged_classes.append(merged)
            data["classes"] = merged_classes
            _diagnostic_classes_cache = data
        else:
            _diagnostic_classes_cache = {}
    return _diagnostic_classes_cache


def load_planar_schema() -> Dict:
    """Return the parsed planar.yaml dict (cached per process).

    Returns the raw YAML structure including ``keystone_position_name`` and
    ``structural_columns``. Returns an empty dict if the file is missing.
    """
    global _planar_schema_cache
    if _planar_schema_cache is None:
        path = ROOT / "schemas" / "planar.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _planar_schema_cache = yaml.safe_load(f) or {}
        else:
            _planar_schema_cache = {}
    return _planar_schema_cache


def load_diagnostic_criteria() -> Dict:
    """Return the parsed diagnostic_criteria.yaml dict (cached per process).

    Returns the raw YAML structure: ``{"analyses": [{name, diagnostic_criteria: [...]}]}``.
    Returns an empty dict if the file is missing.
    """
    global _diagnostic_criteria_cache
    if _diagnostic_criteria_cache is None:
        path = ROOT / "schemas" / "diagnostic_criteria.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _diagnostic_criteria_cache = yaml.safe_load(f) or {}
        else:
            _diagnostic_criteria_cache = {}
    return _diagnostic_criteria_cache


def criterion_values(criterion_name: str) -> List[str] | None:
    """Return a criterion's declared ``values`` list from diagnostic_criteria.yaml.

    Returns None if the criterion is not found or declares no values, so callers
    can distinguish "not in the schema" from "declared as an empty list".

    Exists so that a criterion's allowed values are read from the schema rather
    than restated in code. Restating them is not hypothetical: validate_coding.py
    hardcoded ``["y", "n"]`` for the coreference pair criteria while
    diagnostic_criteria.yaml declared them ``[y, n, untestable]``, so the sheets
    offered ``untestable`` in their dropdowns and validation then flagged it as
    an invalid value. See docs/data-layer-design.md for why this class of
    duplication is the project's dominant failure mode.
    """
    for analysis in load_diagnostic_criteria().get("analyses", []) or []:
        for crit in analysis.get("diagnostic_criteria", []) or []:
            if isinstance(crit, dict) and crit.get("name") == criterion_name:
                vals = crit.get("values")
                return list(vals) if vals else None
    return None


def reads_from(class_name: str, use: str) -> Dict:
    """The other class's tab ``class_name``'s ``reads_from.<use>`` names in
    diagnostic_classes.yaml: {"class", "construction", "criteria"}. Raises if
    it is not declared (hidden-facts R2: these reads were typed paths with
    nothing recording the dependency). The TSV is
    ``coded_data/{lang}/{class}/{construction}.tsv``."""
    for cls in load_diagnostic_classes().get("classes", []):
        if cls.get("name") == class_name:
            entry = (cls.get("reads_from") or {}).get(use)
            if not entry:
                raise KeyError(f"diagnostic_classes.yaml class {class_name!r} has no reads_from.{use}")
            return entry
    raise KeyError(f"diagnostic_classes.yaml has no class {class_name!r}")


def _value_placeholders() -> Dict[str, Dict]:
    """diagnostic_criteria.yaml's value_placeholders: {kind: {value, free_entry, meaning}}."""
    declared = load_diagnostic_criteria().get("value_placeholders")
    if not declared:
        raise KeyError("schemas/diagnostic_criteria.yaml is missing value_placeholders")
    return declared


def placeholder(kind: str) -> str:
    """The spelling of a declared placeholder value, e.g. placeholder("position_number")
    is "<position_number>" (hidden-facts D6: code used to type it)."""
    declared = _value_placeholders()
    if kind not in declared:
        raise KeyError(f"diagnostic_criteria.yaml value_placeholders has no {kind!r}")
    return declared[kind]["value"]


def placeholder_kind(value) -> "str | None":
    """The declared kind of a placeholder value, None for an ordinary value.
    A value written <like_this> that is not declared raises."""
    text = str(value)
    if not (text.startswith("<") and text.endswith(">")):
        return None
    for kind, entry in _value_placeholders().items():
        if entry["value"] == text:
            return kind
    raise ValueError(f"{text} is not declared in diagnostic_criteria.yaml value_placeholders")


def free_entry_kind(values) -> "str | None":
    """The free-entry kind (e.g. "free_text", "position_names") if a
    criterion's declared values are only free-entry placeholders, else None
    (an ordinary fixed value set, possibly with a placeholder such as
    <position_number> among its choices)."""
    if not values:
        return None
    kinds = {placeholder_kind(v) for v in values}
    if len(kinds) != 1 or None in kinds:
        return None
    (kind,) = kinds
    return kind if _value_placeholders()[kind].get("free_entry") else None


def is_free_entry(values) -> bool:
    """True if a criterion's declared values are only free-entry placeholders
    (free_entry_kind): it takes free entry, so it gets no dropdown -- a
    dropdown would just offer the placeholder itself as a choice. Every
    writer of dropdown validation, the sheet spec, and validate-coding ask this."""
    return free_entry_kind(values) is not None


def criteria_for(class_name: str, construction: str, names: List[str],
                 values: Dict[str, List[str]], lang_id: str = "") -> tuple:
    """The criterion columns, and each one's allowed values, for one tab.

    `names`/`values` are what the language's diagnostics file lists for the
    class (or, with construction_criteria, for this construction). If the
    schema gives this construction a single `criterion:` in
    diagnostic_classes.yaml, that is the tab's one column; otherwise the
    language's list is. Each column's values come from the language's file
    if it lists the criterion, else from diagnostic_criteria.yaml. There is
    no `[y, n]` default (removed 2026-10-12, Phase 10): a criterion with no
    values anywhere raises, naming what to fix, instead of being given values
    nobody chose.

    The one place this rule lives. Until 2026-10-12 it was typed into five
    places (generate_sheets twice, restructure_sheets, refresh_dropdowns,
    sync_params), each a per-class block (hidden-facts entries D1, D2, R1).

    Returns (criterion_names, {name: allowed_values}).
    """
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    con = next((c for c in (classes.get(class_name, {}).get("constructions") or [])
                if isinstance(c, dict) and c.get("name") == construction), {})
    out_names = [con["criterion"]] if con.get("criterion") else list(names)
    out_values: Dict[str, List[str]] = {}
    for name in out_names:
        vals = values.get(name) or criterion_values(name)
        if not vals:
            where = f"diagnostics_{lang_id}.yaml" if lang_id else "the language's diagnostics YAML"
            raise ValueError(
                f"Criterion '{name}' ({class_name}/{construction}) has no allowed values: "
                f"list them in {where} or in schemas/diagnostic_criteria.yaml.")
        out_values[name] = list(vals)
    return out_names, out_values


def apply_schema_criteria(class_name: str, constructions: list, lang_id: str = "") -> list:
    """criteria_for() over a list of (construction, names, values) tuples."""
    return [(c, *criteria_for(class_name, c, pn, pv, lang_id)) for c, pn, pv in constructions]
