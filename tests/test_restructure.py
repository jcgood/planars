#!/usr/bin/env python3
"""Tests for rename-map logic in restructure_sheets.py.

Run from the repo root:
    python tests/test_restructure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from restructure_sheets import _compute_stats, _lookup_existing, _parse_rename_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing(*tuples):
    """Build an existing-annotations dict from (element, pos_name, {values}) tuples."""
    return {(el, pn): vals for el, pn, vals in tuples}


def _rows(*tuples):
    """Build a rows list from (element, pos_name, pos_num) tuples."""
    return [[el, pn, num] for el, pn, num in tuples]


def check(label, got, expected):
    assert got == expected, f"FAIL {label}: expected {expected!r}, got {got!r}"
    print(f"PASS  {label}")


# ---------------------------------------------------------------------------
# _parse_rename_map
# ---------------------------------------------------------------------------

check(
    "_parse_rename_map: empty",
    _parse_rename_map([]),
    {},
)

check(
    "_parse_rename_map: single pair",
    _parse_rename_map(["--rename-map", "old:new"]),
    {"old": "new"},
)

check(
    "_parse_rename_map: multiple pairs",
    _parse_rename_map(["--rename-map", "a:b", "--rename-map", "c:d"]),
    {"a": "b", "c": "d"},
)

check(
    "_parse_rename_map: colon in new name",
    _parse_rename_map(["--rename-map", "old:new:extra"]),
    {"old": "new:extra"},
)

check(
    "_parse_rename_map: ignores other flags",
    _parse_rename_map(["--apply", "--rename-map", "x:y"]),
    {"x": "y"},
)

try:
    _parse_rename_map(["--rename-map", "nocolon"])
    print("FAIL  _parse_rename_map: missing colon should raise SystemExit")
except SystemExit:
    print("PASS  _parse_rename_map: missing colon raises SystemExit")


# ---------------------------------------------------------------------------
# _lookup_existing
# ---------------------------------------------------------------------------

existing = _existing(
    ("NP", "subj", {"V-combines": "y"}),
    ("VP", "old-name", {"V-combines": "n"}),
)

check(
    "_lookup_existing: direct match",
    _lookup_existing("NP", "subj", existing, {}),
    {"V-combines": "y"},
)

check(
    "_lookup_existing: no match, no rename",
    _lookup_existing("VP", "new-name", existing, {}),
    None,
)

check(
    "_lookup_existing: rename match",
    _lookup_existing("VP", "new-name", existing, {"new-name": "old-name"}),
    {"V-combines": "n"},
)

check(
    "_lookup_existing: rename present but element differs",
    _lookup_existing("NP", "new-name", existing, {"new-name": "old-name"}),
    None,
)

check(
    "_lookup_existing: direct takes priority over rename",
    _lookup_existing("NP", "subj", existing, {"subj": "old-name"}),
    {"V-combines": "y"},
)


# ---------------------------------------------------------------------------
# _compute_stats — no rename
# ---------------------------------------------------------------------------

existing2 = _existing(
    ("NP", "subj", {"p": "y"}),
    ("VP", "obj", {"p": "n"}),
    ("ADV", "gone", {"p": "y"}),   # will be dropped
)

# New planar: subj stays, obj renamed to obj2, gone removed, new-pos added
rows2 = _rows(
    ("NP", "subj", "1"),
    ("VP", "obj2", "2"),    # renamed from obj — without rename-map, treated as new
    ("PP", "new-pos", "3"),  # brand new
)

carried, new, dropped = _compute_stats(rows2, existing2, {})
check("_compute_stats no rename: carried", carried, 1)   # only subj
check("_compute_stats no rename: new", new, 2)           # obj2 and new-pos
check("_compute_stats no rename: dropped", len(dropped), 2)  # obj and gone
assert ("VP", "obj") in dropped
assert ("ADV", "gone") in dropped
print("PASS  _compute_stats no rename: dropped contents")


# ---------------------------------------------------------------------------
# _compute_stats — with rename map
# ---------------------------------------------------------------------------

carried, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2"})
check("_compute_stats with rename: carried", carried, 2)   # subj + obj→obj2
check("_compute_stats with rename: new", new, 1)           # only new-pos
check("_compute_stats with rename: dropped", len(dropped), 1)  # only gone
assert ("ADV", "gone") in dropped
assert ("VP", "obj") not in dropped
print("PASS  _compute_stats with rename: dropped contents")


# ---------------------------------------------------------------------------
# _compute_stats — rename that doesn't match any element
# ---------------------------------------------------------------------------

carried, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2", "ghost": "other"})
check("_compute_stats unmatched rename: carried", carried, 2)
check("_compute_stats unmatched rename: new", new, 1)


print("\nAll tests passed.")
