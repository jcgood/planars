"""Smoke tests for analysis modules with no coded data (#93).

Covers the modules that have no annotation TSVs in coded_data/:
  nonpermutability, free_occurrence, biuniqueness, repair, segmental,
  tonal, tonosegmental, pausing, proform, play_language, idiom

Each test passes a minimal synthetic _data tuple (no file I/O) and verifies:
  1. The derive function does not raise.
  2. It returns a dict with the expected standard keys.
  3. format_result() returns a non-empty string.
  4. Span tuples have left_edge <= right_edge.

The 5 modules that already have coded data (ciscategorial, subspanrepetition,
noninterruption, stress, aspiration) are covered by the snapshot tests.
"""
from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Synthetic data factory
# ---------------------------------------------------------------------------

_K = 5  # keystone position
_POS_TO_NAME = {3: "v:left2", 4: "v:left1", 5: "v:verbstem", 6: "v:right1", 7: "v:right2"}


def _make_data(criteria: list[str], all_y: bool = True) -> tuple:
    """Build a minimal synthetic _data 5-tuple for the given criterion columns.

    Two non-keystone positions (4 and 6) with one element each.  All criteria
    are set to "y" (or "n" depending on all_y) so qualification logic runs
    through at least one qualifying path.  strict=False is always used so blank
    values don't trigger validation errors.
    """
    value = "y" if all_y else "n"
    rows = [
        {"Position_Number": 4, "Element": "elem-L", **{c: value for c in criteria}},
        {"Position_Number": 6, "Element": "elem-R", **{c: value for c in criteria}},
    ]
    data_df = pd.DataFrame(rows)

    # keystone_df: one row representing the keystone (not used by these modules)
    ks_rows = [{"Position_Number": _K, "Element": "v:verbstem", **{c: "NA" for c in criteria}}]
    keystone_df = pd.DataFrame(ks_rows)

    return (data_df, _K, _POS_TO_NAME, criteria, keystone_df)


# ---------------------------------------------------------------------------
# Module registry: (module_name, derive_fn_name, criteria, extra_checks)
# ---------------------------------------------------------------------------
# extra_checks: list of result-dict keys that must be present beyond the standard set

# Keys that every module's result dict must contain.
# complete_positions / partial_positions are intentionally excluded: some modules
# (nonpermutability, biuniqueness) use domain-specific names for their position sets.
_STANDARD_KEYS = {
    "keystone_position",
    "position_number_to_name",
    "element_table",
    "missing_data",
}

_MODULES = [
    ("planars.nonpermutability", "derive_nonpermutability_domains",
     ["permutable", "scopal"],
     {"strict_complete_span", "strict_partial_span",
      "flexible_complete_span", "flexible_partial_span"}),

    ("planars.free_occurrence",  "derive_free_occurrence_spans",
     ["free"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.biuniqueness",     "derive_biuniqueness_domains",
     ["biunique"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.repair",           "derive_repair_domains",
     ["restart"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.segmental",        "derive_segmental_domains",
     ["applies"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.tonal",            "derive_tonal_domains",
     ["applies"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.tonosegmental",    "derive_tonosegmental_domains",
     ["applies"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.pausing",          "derive_pausing_domains",
     ["pause_domain"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.proform",          "derive_proform_domains",
     ["substitutable"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.play_language",    "derive_play_language_domains",
     ["applies"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),

    ("planars.idiom",            "derive_idiom_domains",
     ["idiomatic"],
     {"strict_complete_span", "loose_complete_span",
      "strict_partial_span",  "loose_partial_span"}),
]

_IDS = [m[0].split(".")[-1] for m in _MODULES]


def _span_keys(spec: tuple) -> set[str]:
    return spec[3]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_spans_valid(result: dict, span_keys: set[str]) -> list[str]:
    """Return list of span keys where left > right (invariant violation)."""
    bad = []
    for key in span_keys:
        val = result.get(key)
        if isinstance(val, tuple) and len(val) == 2:
            l, r = val
            if l > r:
                bad.append(f"{key}: ({l}, {r})")
    return bad


# ---------------------------------------------------------------------------
# Parametrized smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mod_name,fn_name,criteria,span_keys", _MODULES, ids=_IDS)
class TestSmokeModule:
    def _derive(self, mod_name, fn_name, criteria, all_y=True):
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
        data = _make_data(criteria, all_y=all_y)
        return fn(_data=data, strict=False), mod

    def test_does_not_raise(self, mod_name, fn_name, criteria, span_keys):
        self._derive(mod_name, fn_name, criteria)

    def test_returns_dict(self, mod_name, fn_name, criteria, span_keys):
        result, _ = self._derive(mod_name, fn_name, criteria)
        assert isinstance(result, dict)

    def test_standard_keys_present(self, mod_name, fn_name, criteria, span_keys):
        result, _ = self._derive(mod_name, fn_name, criteria)
        missing = _STANDARD_KEYS - set(result.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_span_keys_present(self, mod_name, fn_name, criteria, span_keys):
        result, _ = self._derive(mod_name, fn_name, criteria)
        missing = span_keys - set(result.keys())
        assert not missing, f"Missing span keys: {missing}"

    def test_span_left_le_right(self, mod_name, fn_name, criteria, span_keys):
        result, _ = self._derive(mod_name, fn_name, criteria)
        bad = _all_spans_valid(result, span_keys)
        assert not bad, f"Span invariant violated: {bad}"

    def test_format_result_returns_string(self, mod_name, fn_name, criteria, span_keys):
        result, mod = self._derive(mod_name, fn_name, criteria)
        out = mod.format_result(result)
        assert isinstance(out, str)
        assert out.strip()

    def test_all_n_does_not_raise(self, mod_name, fn_name, criteria, span_keys):
        # All criteria set to "n" → qualification logic runs the zero-qualifying path.
        result, _ = self._derive(mod_name, fn_name, criteria, all_y=False)
        assert isinstance(result, dict)

    def test_derive_alias_exists(self, mod_name, fn_name, criteria, span_keys):
        # Each module must expose a `derive` alias for generate_notebooks.py.
        mod = importlib.import_module(mod_name)
        assert callable(getattr(mod, "derive", None)), \
            f"{mod_name} is missing a `derive` alias"
