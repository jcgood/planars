"""Tests for coding/sync_params.py — criterion column sync logic.

Covers the pure/testable functions: Criteria-cell token manipulation
(rename/split/merge), diagnostics TSV updates, CLI flag parsing, and sheet
header introspection against a minimal fake Worksheet. Live-Sheet-mutating
orchestration in main() (batch_update calls, column insertion/deletion) is
not covered here, matching the existing pattern for restructure_sheets.py
and update_sheets.py's own helper-function tests.
"""
from __future__ import annotations

import pandas as pd
import pytest

from coding.sync_params import (
    _build_dropdown_refresh_requests,
    _criterion_name_from_spec,
    _get_current_params,
    _merge_criteria_in_cell,
    _parse_merges,
    _parse_rename_pair,
    _parse_renames,
    _parse_splits,
    _rename_criterion_in_cell,
    _split_criterion_in_cell,
    _update_diagnostics_tsv,
)


class _FakeWorksheet:
    """Minimal stand-in for a gspread.Worksheet -- no network calls."""

    def __init__(self, header, row_count=None, sheet_id=1):
        self._header = header
        self.row_count = row_count if row_count is not None else len(header) + 1
        self.id = sheet_id

    def row_values(self, row):
        assert row == 1
        return self._header


# ---------------------------------------------------------------------------
# _criterion_name_from_spec
# ---------------------------------------------------------------------------

class TestCriterionNameFromSpec:
    def test_plain_name(self):
        assert _criterion_name_from_spec("free") == "free"

    def test_strips_brace_values(self):
        assert _criterion_name_from_spec("stressed{y/n/both}") == "stressed"

    def test_strips_whitespace(self):
        assert _criterion_name_from_spec("  free  ") == "free"


# ---------------------------------------------------------------------------
# _rename_criterion_in_cell
# ---------------------------------------------------------------------------

class TestRenameCriterionInCell:
    def test_renames_matching_token(self):
        assert _rename_criterion_in_cell("free, obligatory", "free", "shareable") == "shareable, obligatory"

    def test_preserves_brace_values(self):
        result = _rename_criterion_in_cell("stressed{y/n/both}, free", "stressed", "accented")
        assert result == "accented{y/n/both}, free"

    def test_no_match_leaves_cell_unchanged(self):
        assert _rename_criterion_in_cell("free, obligatory", "missing", "new") == "free, obligatory"

    def test_empty_cell(self):
        assert _rename_criterion_in_cell("", "free", "new") == ""


# ---------------------------------------------------------------------------
# _split_criterion_in_cell
# ---------------------------------------------------------------------------

class TestSplitCriterionInCell:
    def test_splits_matching_token_into_two(self):
        result = _split_criterion_in_cell("free, obligatory", "free", "free_left", "free_right")
        assert result == "free_left, free_right, obligatory"

    def test_no_match_leaves_cell_unchanged(self):
        assert _split_criterion_in_cell("free, obligatory", "missing", "a", "b") == "free, obligatory"

    def test_preserves_position_of_split(self):
        result = _split_criterion_in_cell("a, free, b", "free", "x", "y")
        assert result == "a, x, y, b"


# ---------------------------------------------------------------------------
# _merge_criteria_in_cell
# ---------------------------------------------------------------------------

class TestMergeCriteriaInCell:
    def test_merges_both_present(self):
        result = _merge_criteria_in_cell("left, right, other", "left", "right", "combined")
        assert result == "combined, other"

    def test_merges_only_one_present(self):
        result = _merge_criteria_in_cell("left, other", "left", "right", "combined")
        assert result == "combined, other"

    def test_new_token_inserted_at_first_match_position(self):
        result = _merge_criteria_in_cell("a, left, b, right, c", "left", "right", "combined")
        assert result == "a, combined, b, c"

    def test_neither_present_leaves_cell_unchanged(self):
        assert _merge_criteria_in_cell("free, obligatory", "left", "right", "combined") == "free, obligatory"


# ---------------------------------------------------------------------------
# _update_diagnostics_tsv
# ---------------------------------------------------------------------------

class TestUpdateDiagnosticsTsv:
    def _write_tsv(self, path, rows):
        pd.DataFrame(rows).to_csv(path, sep="\t", index=False)

    def test_dry_run_reports_changes_without_writing(self, tmp_path):
        diag = tmp_path / "diagnostics_stan1293.tsv"
        self._write_tsv(diag, [{"Class": "metrical", "Criteria": "free, obligatory"}])
        changes = _update_diagnostics_tsv(
            diag, lambda c: _rename_criterion_in_cell(c, "free", "shareable"),
            class_filter=None, dry_run=True,
        )
        assert len(changes) == 1
        assert "free" in changes[0] and "shareable" in changes[0]
        df = pd.read_csv(diag, sep="\t", dtype=str)
        assert df.at[0, "Criteria"] == "free, obligatory"  # unchanged on disk

    def test_apply_writes_changes(self, tmp_path):
        diag = tmp_path / "diagnostics_stan1293.tsv"
        self._write_tsv(diag, [{"Class": "metrical", "Criteria": "free, obligatory"}])
        _update_diagnostics_tsv(
            diag, lambda c: _rename_criterion_in_cell(c, "free", "shareable"),
            class_filter=None, dry_run=False,
        )
        df = pd.read_csv(diag, sep="\t", dtype=str)
        assert df.at[0, "Criteria"] == "shareable, obligatory"

    def test_class_filter_restricts_rows(self, tmp_path):
        diag = tmp_path / "diagnostics_stan1293.tsv"
        self._write_tsv(diag, [
            {"Class": "metrical", "Criteria": "free"},
            {"Class": "segmental", "Criteria": "free"},
        ])
        changes = _update_diagnostics_tsv(
            diag, lambda c: _rename_criterion_in_cell(c, "free", "shareable"),
            class_filter="metrical", dry_run=True,
        )
        assert len(changes) == 1
        assert "[metrical]" in changes[0]

    def test_no_changes_when_criterion_absent(self, tmp_path):
        diag = tmp_path / "diagnostics_stan1293.tsv"
        self._write_tsv(diag, [{"Class": "metrical", "Criteria": "obligatory"}])
        changes = _update_diagnostics_tsv(
            diag, lambda c: _rename_criterion_in_cell(c, "free", "shareable"),
            class_filter=None, dry_run=True,
        )
        assert changes == []


# ---------------------------------------------------------------------------
# CLI flag parsing (--rename / --split / --merge)
# ---------------------------------------------------------------------------

class TestParseRenamePair:
    def test_two_parts_no_class_filter(self):
        assert _parse_rename_pair("old:new") == (None, "old", "new")

    def test_three_parts_has_class_filter(self):
        assert _parse_rename_pair("stress:stressable:stressed") == ("stress", "stressable", "stressed")

    def test_strips_whitespace(self):
        assert _parse_rename_pair(" old : new ") == (None, "old", "new")

    def test_new_name_can_contain_colon(self):
        # 3+ colon-separated parts beyond the class -> new name rejoins with ':'
        assert _parse_rename_pair("cls:old:a:b") == ("cls", "old", "a:b")


class TestParseRenames:
    def test_no_rename_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog"])
        assert _parse_renames() == []

    def test_single_rename_flag(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--rename", "old:new"])
        assert _parse_renames() == [(None, "old", "new")]

    def test_equals_syntax(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--rename=old:new"])
        assert _parse_renames() == [(None, "old", "new")]

    def test_multiple_rename_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--rename", "a:b", "--rename", "c:d"])
        assert _parse_renames() == [(None, "a", "b"), (None, "c", "d")]

    def test_ignores_other_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--apply", "--rename", "old:new", "--remove"])
        assert _parse_renames() == [(None, "old", "new")]


class TestParseSplits:
    def test_no_split_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog"])
        assert _parse_splits() == []

    def test_single_split(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--split", "old:new1:new2"])
        assert _parse_splits() == [("old", "new1", "new2")]

    def test_equals_syntax(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--split=old:new1:new2"])
        assert _parse_splits() == [("old", "new1", "new2")]

    def test_malformed_split_is_skipped_with_warning(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "--split", "old:new1"])
        result = _parse_splits()
        assert result == []
        assert "WARNING" in capsys.readouterr().out


class TestParseMerges:
    def test_no_merge_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog"])
        assert _parse_merges() == []

    def test_single_merge(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--merge", "old1:old2:new"])
        assert _parse_merges() == [("old1", "old2", "new")]

    def test_equals_syntax(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--merge=old1:old2:new"])
        assert _parse_merges() == [("old1", "old2", "new")]

    def test_malformed_merge_is_skipped_with_warning(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "--merge", "old1:old2"])
        result = _parse_merges()
        assert result == []
        assert "WARNING" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _get_current_params
# ---------------------------------------------------------------------------

class TestGetCurrentParams:
    def test_excludes_structural_and_trailing_columns(self):
        ws = _FakeWorksheet(["Element", "Position_Name", "Position_Number", "free", "obligatory", "Source", "Comments"])
        params, comments_col = _get_current_params(ws)
        assert params == ["free", "obligatory"]
        assert comments_col == 5  # index of "Source", the first trailing col

    def test_pair_row_structural_columns_excluded(self):
        ws = _FakeWorksheet(["Element_A", "Element_B", "scopal", "Source", "Comments"])
        params, comments_col = _get_current_params(ws)
        assert params == ["scopal"]

    def test_coreference_pair_structural_columns_excluded(self):
        ws = _FakeWorksheet(["Element_A", "Position_A", "Position_B", "Direction", "forward", "Source", "Comments"])
        params, _ = _get_current_params(ws)
        assert params == ["forward"]

    def test_no_trailing_columns_present(self):
        ws = _FakeWorksheet(["Element", "Position_Name", "Position_Number", "free"])
        params, comments_col = _get_current_params(ws)
        assert params == ["free"]
        assert comments_col == 4  # default: end of header


# ---------------------------------------------------------------------------
# _build_dropdown_refresh_requests
# ---------------------------------------------------------------------------

class TestBuildDropdownRefreshRequests:
    def test_empty_stale_params_returns_no_requests(self):
        ws = _FakeWorksheet(["Element", "free"])
        assert _build_dropdown_refresh_requests(ws, [], {}) == []

    def test_builds_one_request_per_stale_param(self):
        ws = _FakeWorksheet(["Element", "free", "obligatory"], row_count=10, sheet_id=42)
        requests = _build_dropdown_refresh_requests(
            ws, ["free"], {"free": ["y", "n", "both"]},
        )
        assert len(requests) == 1
        rule = requests[0]["setDataValidation"]
        assert rule["range"]["sheetId"] == 42
        assert rule["range"]["startColumnIndex"] == 1  # "free" is at index 1
        assert rule["range"]["endRowIndex"] == 10
        values = [v["userEnteredValue"] for v in rule["rule"]["condition"]["values"]]
        assert values == ["y", "n", "both"]

    def test_defaults_to_y_n_when_no_explicit_values(self):
        ws = _FakeWorksheet(["Element", "free"], row_count=5)
        requests = _build_dropdown_refresh_requests(ws, ["free"], {})
        values = [v["userEnteredValue"] for v in requests[0]["setDataValidation"]["rule"]["condition"]["values"]]
        assert values == ["y", "n"]

    def test_skips_param_not_in_header(self):
        ws = _FakeWorksheet(["Element", "free"], row_count=5)
        requests = _build_dropdown_refresh_requests(ws, ["nonexistent"], {})
        assert requests == []
