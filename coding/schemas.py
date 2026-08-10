"""Cached loaders for the planars YAML schema files.

Provides module-level cached access to diagnostic_classes.yaml and
diagnostic_criteria.yaml so multiple callers in the same process share a
single file read rather than each opening the file independently.

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
