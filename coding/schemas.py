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
from typing import Dict

import yaml

ROOT = Path(__file__).resolve().parent.parent

_diagnostic_classes_cache: Dict | None = None
_diagnostic_criteria_cache: Dict | None = None
_planar_schema_cache: Dict | None = None


def load_diagnostic_classes() -> Dict:
    """Return the parsed diagnostic_classes.yaml dict (cached per process).

    Returns the raw YAML structure: ``{"classes": [{name, ...}, ...]}``.
    Returns an empty dict if the file is missing.
    """
    global _diagnostic_classes_cache
    if _diagnostic_classes_cache is None:
        path = ROOT / "schemas" / "diagnostic_classes.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _diagnostic_classes_cache = yaml.safe_load(f) or {}
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
