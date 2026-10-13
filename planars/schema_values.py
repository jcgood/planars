"""Values owned by schemas/planar.yaml, read in one place.

Every module in planars/ and coding/ that needs the keystone's name or the
Status tab's title and values imports them from here instead of typing them
(Phase 10, issue #271; hidden-facts entries D0 and R3).
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
STATUS_IN_PROGRESS: str = _require("status_tab", "values", "in_progress")
STATUS_READY: str = _require("status_tab", "values", "ready")
STATUS_VALUES = [STATUS_IN_PROGRESS, STATUS_READY]


def is_keystone(position_name) -> bool:
    """True if a Position_Name cell names the keystone (case and spaces ignored)."""
    return str(position_name).strip().lower() == KEYSTONE_NAME.lower()
