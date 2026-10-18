"""Tests for coding/sync_params.py — criterion column sync logic.

Covers the pure/testable functions: criterion edits in the diagnostics YAML
(rename/split/merge), CLI flag parsing, and sheet header introspection
against a minimal fake Worksheet. main() as a whole is run against the
offline Drive in test_sync_params_snapshot.py.
"""
from __future__ import annotations

import textwrap

import pytest

from coding.make_forms import _dump_diagnostics_yaml, _load_diagnostics_yaml_for_edit
from coding.sync_params import (
    _build_dropdown_refresh_requests,
    _get_current_params,
    _merge_in_yaml,
    _parse_merges,
    _parse_rename_pair,
    _parse_renames,
    _parse_splits,
    _rename_in_yaml,
    _split_in_yaml,
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
# Criterion edits in diagnostics_{lang_id}.yaml (rename/split/merge, #315)
# ---------------------------------------------------------------------------

# Criteria a split or merge creates must be defined in the schema with values
# (no [y, n] default since 2026-10-12). These tests invent names, so they
# declare those names' values here instead of in diagnostic_criteria.yaml.
_TEST_CRITERIA = {"free_left": ["y", "n"], "free_right": ["y", "n", "both"],
                  "x": ["y", "n"], "y": ["a", "b"], "combined": ["y", "n"]}


@pytest.fixture(autouse=True)
def _test_criteria(monkeypatch):
    import coding.sync_params as sp
    real = sp.criterion_values
    monkeypatch.setattr(sp, "criterion_values", lambda n: _TEST_CRITERIA.get(n) or real(n))


YAML_TEXT = textwrap.dedent("""\
    language: lang0001
    classes:
      noninterruption:
        constructions: [general]
        criteria:
          a: [y, n]
          # why free is here
          free: [y, n, both]
          b: [y, n]
        notes: "kept as written"
      metrical:
        constructions: [stress_domain, other]
        construction_criteria:
          stress_domain:
            left: [y, n]
            mid: [y, n]
            # why right is here
            right: [y, n]
          other:
            free: [y, n]
        obligatory_positions: [v:npsubj1]
""")


@pytest.fixture()
def yaml_data(tmp_path):
    path = tmp_path / "diagnostics_lang0001.yaml"
    path.write_text(YAML_TEXT, encoding="utf-8")
    return _load_diagnostics_yaml_for_edit(path)


def _crit(data, cls, construction=None):
    c = data["classes"][cls]
    return c["construction_criteria"][construction] if construction else c["criteria"]


class TestYamlRoundTrip:
    def test_an_unedited_yaml_is_written_back_byte_for_byte(self, yaml_data):
        assert _dump_diagnostics_yaml(yaml_data) == YAML_TEXT


class TestRenameInYaml:
    def test_renames_in_place_keeping_values(self, yaml_data):
        changes = _rename_in_yaml(yaml_data, "free", "shareable", None)
        assert list(_crit(yaml_data, "noninterruption")) == ["a", "shareable", "b"]
        assert list(_crit(yaml_data, "noninterruption")["shareable"]) == ["y", "n", "both"]
        assert list(_crit(yaml_data, "metrical", "other")) == ["shareable"]
        assert len(changes) == 2

    def test_only_the_renamed_line_changes(self, yaml_data):
        _rename_in_yaml(yaml_data, "free", "shareable", "noninterruption")
        assert _dump_diagnostics_yaml(yaml_data) == YAML_TEXT.replace(
            "      free: [y, n, both]", "      shareable: [y, n, both]")

    def test_class_filter_restricts_the_rename(self, yaml_data):
        changes = _rename_in_yaml(yaml_data, "free", "shareable", "metrical")
        assert "free" in _crit(yaml_data, "noninterruption")
        assert changes and all("[metrical/other]" in c for c in changes)

    def test_absent_criterion_changes_nothing(self, yaml_data):
        assert _rename_in_yaml(yaml_data, "missing", "new", None) == []
        assert _dump_diagnostics_yaml(yaml_data) == YAML_TEXT

    def test_renaming_onto_an_existing_criterion_stops_the_command(self, yaml_data):
        with pytest.raises(SystemExit, match="already listed"):
            _rename_in_yaml(yaml_data, "free", "b", "noninterruption")


class TestSplitInYaml:
    def test_splits_in_place_with_schema_values(self, yaml_data):
        _split_in_yaml(yaml_data, "free", "free_left", "free_right")
        crit = _crit(yaml_data, "noninterruption")
        assert list(crit) == ["a", "free_left", "free_right", "b"]
        assert list(crit["free_right"]) == ["y", "n", "both"]
        out = _dump_diagnostics_yaml(yaml_data)
        assert "      # why free is here\n      free_left: [y, n]\n      free_right: [y, n, both]\n" in out

    def test_a_new_criterion_with_no_schema_values_stops_the_command(self, yaml_data):
        with pytest.raises(SystemExit, match="not defined"):
            _split_in_yaml(yaml_data, "free", "undefined_one", "undefined_two")


class TestMergeInYaml:
    def test_merges_at_the_first_ones_place(self, yaml_data):
        _merge_in_yaml(yaml_data, "left", "right", "combined")
        assert list(_crit(yaml_data, "metrical", "stress_domain")) == ["combined", "mid"]

    def test_a_merged_away_criterions_comment_is_kept(self, yaml_data):
        _merge_in_yaml(yaml_data, "left", "right", "combined")
        out = _dump_diagnostics_yaml(yaml_data)
        assert "# why right is here\n        combined: [y, n]\n        mid: [y, n]\n" in out

    def test_merges_when_only_one_is_present(self, yaml_data):
        _merge_in_yaml(yaml_data, "free", "nothere", "combined")
        assert list(_crit(yaml_data, "noninterruption")) == ["a", "combined", "b"]

    def test_neither_present_changes_nothing(self, yaml_data):
        assert _merge_in_yaml(yaml_data, "p", "q", "combined") == []


def test_other_fields_survive_an_edit(yaml_data):
    """The old TSV round trip kept only notes; obligatory_positions was lost."""
    _rename_in_yaml(yaml_data, "free", "shareable", None)
    out = _dump_diagnostics_yaml(yaml_data)
    assert "obligatory_positions: [v:npsubj1]" in out
    assert 'notes: "kept as written"' in out


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

    def test_no_y_n_default_when_values_are_missing(self):
        """A column with no values is an error, not a [y, n] dropdown (the
        default was removed 2026-10-12; criteria_for always supplies values)."""
        ws = _FakeWorksheet(["Element", "free"], row_count=5)
        with pytest.raises(KeyError):
            _build_dropdown_refresh_requests(ws, ["free"], {})

    def test_skips_param_not_in_header(self):
        ws = _FakeWorksheet(["Element", "free"], row_count=5)
        requests = _build_dropdown_refresh_requests(ws, ["nonexistent"], {})
        assert requests == []
