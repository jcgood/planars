"""Tests for coding/update_sheets.py — the "add missing rows/columns" logic.

Covers the pure/testable functions this module's `--apply` path relies on to
decide what to write to a live annotation sheet. This is exactly the code
path behind the 2026-07-29 stray-row incident (#248): _compute_missing_rows,
given a stale planar element_index, is what actually decided a retired
element was "missing" and needed adding back. There was no direct test
coverage for this logic before now.

Live-Sheet-touching orchestration in main() (opening spreadsheets, iterating
the manifest) is covered by tests/test_update_sheets_snapshot.py, which runs
the whole command against a stand-in Drive. These tests operate on plain Python
data structures and a minimal fake Worksheet, matching the existing pattern in
test_restructure.py for restructure_sheets.py's own helper functions.

`_compute_missing_rows` takes the criterion block's start column and width
because the tab's own header is what says where it is; the `3, 1` in these
calls is "criteria begin at column 3, there is one of them", matching each
fake header below.
"""
from __future__ import annotations

from coding.update_sheets import (
    _add_trailing_columns,
    _build_planar_pos_map,
    _check_structural_drift,
    _compute_missing_rows,
    _planar_rows_for_lang,
    _sheet_element_keys,
    _TRAILING_COLS,
)


class _FakeWorksheet:
    """Minimal stand-in for a gspread.Worksheet -- no network calls."""

    def __init__(self, rows):
        self._rows = rows
        self.insert_cols_calls = []

    def get_all_values(self):
        return self._rows

    def insert_cols(self, data, col):
        self.insert_cols_calls.append((data, col))


# ---------------------------------------------------------------------------
# _sheet_element_keys
# ---------------------------------------------------------------------------

class TestSheetElementKeys:
    def test_empty_rows(self):
        assert _sheet_element_keys([], []) == set()

    def test_missing_element_column(self):
        rows = [["Position_Name", "Position_Number"], ["v:npsubj1", "5"]]
        assert _sheet_element_keys(rows, rows[0]) == set()

    def test_missing_position_number_column(self):
        rows = [["Element", "Position_Name"], ["he", "v:npsubj1"]]
        assert _sheet_element_keys(rows, rows[0]) == set()

    def test_extracts_keys(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he", "v:npsubj1", "5"],
            ["NP{S,A}", "v:npsubj1", "5"],
        ]
        assert _sheet_element_keys(rows, rows[0]) == {("he", "5"), ("NP{S,A}", "5")}

    def test_strips_whitespace(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            [" he ", "v:npsubj1", " 5 "],
        ]
        assert _sheet_element_keys(rows, rows[0]) == {("he", "5")}

    def test_skips_short_rows(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he"],  # missing columns
        ]
        assert _sheet_element_keys(rows, rows[0]) == set()


# ---------------------------------------------------------------------------
# _planar_rows_for_lang
# ---------------------------------------------------------------------------

class TestPlanarRowsForLang:
    def test_filters_by_language(self):
        element_index = {
            "he@5": (5, "v:npsubj1", "stan1293", "he"),
            "foo@3": (3, "v:foo", "arao1248", "foo"),
        }
        result = _planar_rows_for_lang(element_index, "stan1293")
        assert result == [(5, "he", "v:npsubj1")]

    def test_sorts_by_position_then_element(self):
        element_index = {
            "they@5": (5, "v:npsubj1", "stan1293", "they"),
            "he@5": (5, "v:npsubj1", "stan1293", "he"),
            "not@1": (1, "v:neg1", "stan1293", "not"),
        }
        result = _planar_rows_for_lang(element_index, "stan1293")
        assert result == [
            (1, "not", "v:neg1"),
            (5, "he", "v:npsubj1"),
            (5, "they", "v:npsubj1"),
        ]

    def test_empty_index(self):
        assert _planar_rows_for_lang({}, "stan1293") == []


# ---------------------------------------------------------------------------
# _build_planar_pos_map
# ---------------------------------------------------------------------------

class TestBuildPlanarPosMap:
    def test_builds_position_name_to_number_map(self):
        element_index = {
            "he@5": (5, "v:npsubj1", "stan1293", "he"),
            "NP{S,A}@5": (5, "v:npsubj1", "stan1293", "NP{S,A}"),
            "not@1": (1, "v:neg1", "stan1293", "not"),
        }
        result = _build_planar_pos_map(element_index, "stan1293")
        assert result == {"v:npsubj1": 5, "v:neg1": 1}

    def test_filters_by_language(self):
        element_index = {"foo@3": (3, "v:foo", "arao1248", "foo")}
        assert _build_planar_pos_map(element_index, "stan1293") == {}


# ---------------------------------------------------------------------------
# _check_structural_drift
# ---------------------------------------------------------------------------

class TestCheckStructuralDrift:
    def test_no_rows_no_drift(self):
        assert _check_structural_drift([], {"v:npsubj1": 5}) == []

    def test_header_only_no_drift(self):
        rows = [["Element", "Position_Name", "Position_Number"]]
        assert _check_structural_drift(rows, {"v:npsubj1": 5}) == []

    def test_missing_required_columns_returns_empty(self):
        rows = [["Element", "Foo"], ["he", "bar"]]
        assert _check_structural_drift(rows, {}) == []

    def test_no_drift_when_positions_match(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he", "v:npsubj1", "5"],
        ]
        assert _check_structural_drift(rows, {"v:npsubj1": 5}) == []

    def test_warns_on_removed_position(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he", "v:npsubj1", "5"],
        ]
        warnings = _check_structural_drift(rows, {})  # v:npsubj1 no longer in planar
        assert len(warnings) == 1
        assert "no longer exists in planar structure" in warnings[0]

    def test_warns_on_renumbered_position(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he", "v:npsubj1", "5"],
        ]
        warnings = _check_structural_drift(rows, {"v:npsubj1": 6})
        assert len(warnings) == 1
        assert "sheet has pos 5" in warnings[0]
        assert "planar has pos 6" in warnings[0]

    def test_skips_keystone_position(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["KEYSTONE", "v:verbstem", "30"],
        ]
        # v:verbstem absent from planar_pos_map -- would normally warn, but is
        # explicitly exempted since it's a reserved special position.
        assert _check_structural_drift(rows, {}) == []

    def test_ignores_rows_with_blank_position_number(self):
        rows = [
            ["Element", "Position_Name", "Position_Number"],
            ["he", "v:npsubj1", ""],
        ]
        assert _check_structural_drift(rows, {}) == []


# ---------------------------------------------------------------------------
# _compute_missing_rows
# ---------------------------------------------------------------------------

class TestComputeMissingRows:
    def test_no_missing_rows_when_sheet_already_current(self):
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
            ["he", "v:npsubj1", "5", "y", "", ""],
        ])
        element_index = {"he@5": (5, "v:npsubj1", "stan1293", "he")}
        missing = _compute_missing_rows(ws, element_index, "stan1293", 3, 1)
        assert missing == []

    def test_adds_row_for_planar_element_absent_from_sheet(self):
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
        ])
        element_index = {"he@5": (5, "v:npsubj1", "stan1293", "he")}
        missing = _compute_missing_rows(ws, element_index, "stan1293", 3, 1)
        assert missing == [["he", "v:npsubj1", "5", "", "", ""]]

    def test_keystone_row_gets_na_param_values(self):
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
        ])
        element_index = {"KEYSTONE@30": (30, "v:verbstem", "stan1293", "KEYSTONE")}
        missing = _compute_missing_rows(ws, element_index, "stan1293", 3, 1)
        assert missing == [["KEYSTONE", "v:verbstem", "30", "NA", "", ""]]

    def test_hyphen_wrapped_elements_get_bracketed(self):
        # planar.yaml convention: elements with leading/trailing hyphens are
        # wrapped in [brackets] to avoid Excel parsing issues.
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
        ])
        element_index = {"-s@13": (13, "v:perfectinflection", "stan1293", "-s")}
        missing = _compute_missing_rows(ws, element_index, "stan1293", 3, 1)
        assert missing[0][0] == "[-s]"

    def test_ignores_elements_from_other_languages(self):
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
        ])
        element_index = {"foo@3": (3, "v:foo", "arao1248", "foo")}
        missing = _compute_missing_rows(ws, element_index, "stan1293", 3, 1)
        assert missing == []

    def test_this_is_the_exact_248_failure_shape(self):
        # The stray-row incident: a retired element (PRON{P,T}) still present
        # in a STALE element_index (because the planar file on disk had been
        # silently reverted) gets treated as "missing" from an already-correct
        # sheet and re-added. This test documents that _compute_missing_rows
        # itself has no way to know the index is stale -- it trusts its input
        # completely, which is exactly why the fix landed as a precondition
        # check (coded_data_clean_tree) upstream of this function, not inside
        # it. See data_dependency_schema/preconditions.yaml.
        ws = _FakeWorksheet([
            ["Element", "Position_Name", "Position_Number", "free", "Source", "Comments"],
            ["me", "v:obj-part", "34", "y", "", ""],
        ])
        stale_element_index = {
            "me@34": (34, "v:obj-part", "stan1293", "me"),
            "PRON{P,T}@34": (34, "v:obj-part", "stan1293", "PRON{P,T}"),  # retired, but present in the stale index
        }
        missing = _compute_missing_rows(ws, stale_element_index, "stan1293", 3, 1)
        assert missing == [["PRON{P,T}", "v:obj-part", "34", "", "", ""]]


# ---------------------------------------------------------------------------
# _add_trailing_columns
# ---------------------------------------------------------------------------

class TestAddTrailingColumns:
    def test_noop_when_nothing_missing(self):
        header = ["Element", "Position_Name", "Position_Number"] + list(_TRAILING_COLS)
        ws = _FakeWorksheet([header])
        result = _add_trailing_columns(ws, header, [header])
        assert result == header
        assert ws.insert_cols_calls == []

    def test_appends_single_missing_column_at_end(self):
        header = ["Element", "Position_Name", "Position_Number"]
        rows = [header, ["he", "v:npsubj1", "5"]]
        ws = _FakeWorksheet(rows)
        result = _add_trailing_columns(ws, header, rows)
        assert result == header + list(_TRAILING_COLS)
        assert len(ws.insert_cols_calls) == len(_TRAILING_COLS)

    def test_inserted_column_data_has_blank_cells_for_existing_rows(self):
        header = ["Element", "Position_Name", "Position_Number"]
        rows = [header, ["he", "v:npsubj1", "5"], ["she", "v:npsubj1", "5"]]
        ws = _FakeWorksheet(rows)
        _add_trailing_columns(ws, header, rows)
        first_col_data, _ = ws.insert_cols_calls[0]
        # header + one blank per data row (2 data rows here)
        assert first_col_data == [[_TRAILING_COLS[0]] + [""] * 2]

    def test_only_missing_trailing_columns_are_added(self):
        # First trailing column already present -- only later ones get added.
        header = ["Element", "Position_Name", "Position_Number", _TRAILING_COLS[0]]
        rows = [header]
        ws = _FakeWorksheet(rows)
        result = _add_trailing_columns(ws, header, rows)
        assert result == header + list(_TRAILING_COLS[1:])
        assert len(ws.insert_cols_calls) == len(_TRAILING_COLS) - 1
