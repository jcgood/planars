"""Tests for coding/generate_sheets.py — data-protection helpers.

Covers:
  - _check_force_against_existing_sheets: blocks --force when sheets exist
  - _build_nonperm_pairs: pair generation algorithm (exclusion rules, bracket-wrapping)
  - _filter_nonperm_pairs_by_prescreening: scopal=n excluded; na/blank kept
  - _prefill_free_occurrence_rows: keystone and non-keystone pre-fill logic
  - _regen_dependents_simple: skips when dep TSV exists; regenerates when absent
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import coding.generate_sheets as _gs
from coding.generate_sheets import (
    _build_nonperm_pairs,
    _check_force_against_existing_sheets,
    _filter_nonperm_pairs_by_prescreening,
    _prefill_free_occurrence_rows,
    _regen_dependents_simple,
)


class TestCheckForceAgainstExistingSheets:
    def test_raises_when_force_and_sheets_exist(self):
        existing = {"sheets": {"ciscategorial": {"spreadsheet_id": "abc"}}}
        with pytest.raises(SystemExit):
            _check_force_against_existing_sheets("arao1248", force=True, existing_lang_data=existing)

    def test_passes_when_force_but_no_sheets(self):
        # --force on a brand-new language with no sheets yet is fine.
        _check_force_against_existing_sheets("newlang", force=True, existing_lang_data={})

    def test_passes_when_force_and_sheets_key_empty(self):
        # sheets dict exists but is empty — no sheets to protect.
        _check_force_against_existing_sheets("arao1248", force=True, existing_lang_data={"sheets": {}})

    def test_passes_when_no_force_and_sheets_exist(self):
        # Normal (non-force) run with existing sheets — should not raise.
        existing = {"sheets": {"ciscategorial": {"spreadsheet_id": "abc"}}}
        _check_force_against_existing_sheets("arao1248", force=False, existing_lang_data=existing)

    def test_passes_when_no_force_and_no_sheets(self):
        _check_force_against_existing_sheets("newlang", force=False, existing_lang_data={})

    def test_error_message_names_lang_id(self, capsys):
        existing = {"sheets": {"ciscategorial": {"spreadsheet_id": "abc"}}}
        with pytest.raises(SystemExit):
            _check_force_against_existing_sheets("arao1248", force=True, existing_lang_data=existing)
        out = capsys.readouterr().out
        assert "arao1248" in out

    def test_error_message_names_existing_classes(self, capsys):
        existing = {"sheets": {
            "ciscategorial": {"spreadsheet_id": "abc"},
            "stress": {"spreadsheet_id": "def"},
        }}
        with pytest.raises(SystemExit):
            _check_force_against_existing_sheets("stan1293", force=True, existing_lang_data=existing)
        out = capsys.readouterr().out
        assert "ciscategorial" in out
        assert "stress" in out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ei(lang_id: str, entries: list) -> dict:
    """Build a minimal element_index from [(pos, pos_name, element), ...] tuples."""
    return {f"{e}@{p}": (p, n, lang_id, e) for p, n, e in entries}


# ---------------------------------------------------------------------------
# _build_nonperm_pairs
# ---------------------------------------------------------------------------

class TestBuildNonpermPairs:
    def test_fixed_structural_order_excluded(self):
        # a at pos 1, b at pos 2 — a always before b, no permutation possible.
        ei = _ei("lang0001", [(1, "p1", "a"), (2, "p2", "b")])
        pos_type = {1: "Slot", 2: "Slot"}
        assert _build_nonperm_pairs(ei, "lang0001", pos_type) == []

    def test_same_slot_pair_excluded(self):
        # a and b share the same Slot position — fixed co-occurrence order by convention.
        ei = _ei("lang0001", [(1, "p1", "a"), (1, "p1", "b")])
        pos_type = {1: "Slot"}
        assert _build_nonperm_pairs(ei, "lang0001", pos_type) == []

    def test_zone_pair_included(self):
        # a and b share a Zone position — within-zone permutation is possible.
        ei = _ei("lang0001", [(1, "p1", "a"), (1, "p1", "b")])
        pos_type = {1: "Zone"}
        pairs = _build_nonperm_pairs(ei, "lang0001", pos_type)
        assert pairs == [["a", "b"]]

    def test_straddling_pair_included(self):
        # a spans positions 1 and 3; b is at position 2.
        # max(a)=3 > min(b)=2 and max(b)=2 > min(a)=1 — structurally ambiguous order.
        ei = {
            "a@1": (1, "p1", "lang0001", "a"),
            "a@3": (3, "p3", "lang0001", "a"),
            "b@2": (2, "p2", "lang0001", "b"),
        }
        pos_type = {1: "Slot", 2: "Slot", 3: "Slot"}
        pairs = _build_nonperm_pairs(ei, "lang0001", pos_type)
        assert ["a", "b"] in pairs

    def test_hyphenated_elements_bracket_wrapped(self):
        # Elements with leading/trailing hyphens must match the bracket-wrapped
        # form used in element_prescreening.tsv (e.g. -ed → [-ed]).
        ei = _ei("lang0001", [(1, "p1", "-ed"), (1, "p1", "-ing")])
        pos_type = {1: "Zone"}
        pairs = _build_nonperm_pairs(ei, "lang0001", pos_type)
        assert pairs == [["[-ed]", "[-ing]"]]

    def test_keystone_excluded_from_all_pairs(self):
        # v:verbstem position must never appear in any pair.
        ei = _ei("lang0001", [(1, "v:verbstem", "vs"), (2, "p2", "a"), (2, "p2", "b")])
        pos_type = {1: "Slot", 2: "Zone"}
        pairs = _build_nonperm_pairs(ei, "lang0001", pos_type)
        flat = [e for pair in pairs for e in pair]
        assert "vs" not in flat

    def test_other_lang_elements_excluded(self):
        # Elements from a different language must not appear in the pair list.
        ei = {
            "a@1": (1, "p1", "lang0001", "a"),
            "b@1": (1, "p1", "other9999", "b"),
        }
        pos_type = {1: "Zone"}
        pairs = _build_nonperm_pairs(ei, "lang0001", pos_type)
        assert pairs == []


# ---------------------------------------------------------------------------
# _filter_nonperm_pairs_by_prescreening
# ---------------------------------------------------------------------------

class TestFilterNonpermPairsByPrescreening:
    def _write_prescreening(self, tmp_path: Path, lang_id: str, rows: list[dict]) -> None:
        d = tmp_path / lang_id / "nonpermutability"
        d.mkdir(parents=True)
        path = d / "element_prescreening.tsv"
        header = "\t".join(rows[0].keys())
        lines = [header] + ["\t".join(r.values()) for r in rows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_scopal_n_excludes_element(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        self._write_prescreening(tmp_path, "lang0001", [
            {"Element": "a", "scopal": "n"},
            {"Element": "b", "scopal": "y"},
            {"Element": "c", "scopal": "y"},
        ])
        pairs = [["a", "b"], ["b", "c"], ["a", "c"]]
        result = _filter_nonperm_pairs_by_prescreening(pairs, "lang0001")
        assert result == [["b", "c"]]

    def test_scopal_na_not_excluded(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        self._write_prescreening(tmp_path, "lang0001", [
            {"Element": "a", "scopal": "na"},
            {"Element": "b", "scopal": "y"},
        ])
        pairs = [["a", "b"]]
        result = _filter_nonperm_pairs_by_prescreening(pairs, "lang0001")
        assert result == [["a", "b"]]

    def test_blank_scopal_not_excluded(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        self._write_prescreening(tmp_path, "lang0001", [
            {"Element": "a", "scopal": ""},
            {"Element": "b", "scopal": "y"},
        ])
        pairs = [["a", "b"]]
        result = _filter_nonperm_pairs_by_prescreening(pairs, "lang0001")
        assert result == [["a", "b"]]

    def test_missing_prescreening_file_returns_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        pairs = [["a", "b"], ["b", "c"]]
        result = _filter_nonperm_pairs_by_prescreening(pairs, "lang0001")
        assert result == pairs


# ---------------------------------------------------------------------------
# _prefill_free_occurrence_rows
# ---------------------------------------------------------------------------

_FREE_PARAMS = ["free", "left-edge-of-free-form", "right-edge-of-free-form",
                "dependent-on-left", "dependent-on-right"]
_BASE = 3  # Element, Position_Name, Position_Number


def _row(element: str, pos_name: str, pos_num: str = "1") -> list:
    return [element, pos_name, pos_num] + [""] * len(_FREE_PARAMS)


def _free_val(row: list) -> str:
    return row[_BASE + _FREE_PARAMS.index("free")]


def _annot_vals(row: list) -> list:
    return [row[_BASE + i] for i in range(1, len(_FREE_PARAMS))]


def _write_noninterruption(tmp_path: Path, lang_id: str, rows: list[dict]) -> None:
    d = tmp_path / lang_id / "noninterruption"
    d.mkdir(parents=True)
    path = d / "general.tsv"
    header = "\t".join(rows[0].keys())
    lines = [header] + ["\t".join(r.values()) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestPrefillFreeOccurrenceRows:
    def test_keystone_does_not_get_na_from_noninterruption(self, tmp_path, monkeypatch):
        # noninterruption marks keystone free=na; free_occurrence should leave it blank.
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        _write_noninterruption(tmp_path, "lang0001", [
            {"Element": "vs", "free": "na"},
        ])
        rows = [_row("vs", "v:verbstem")]
        result = _prefill_free_occurrence_rows(rows, _FREE_PARAMS, "lang0001")
        assert _free_val(result[0]) == ""

    def test_keystone_gets_real_value_from_noninterruption(self, tmp_path, monkeypatch):
        # If noninterruption carries a real y/n for the keystone, use it.
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        _write_noninterruption(tmp_path, "lang0001", [
            {"Element": "vs", "free": "y"},
        ])
        rows = [_row("vs", "v:verbstem")]
        result = _prefill_free_occurrence_rows(rows, _FREE_PARAMS, "lang0001")
        assert _free_val(result[0]) == "y"

    def test_keystone_annotation_cols_set_to_na(self, tmp_path, monkeypatch):
        # Keystone annotation columns (left-edge, right-edge, etc.) are always na.
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        _write_noninterruption(tmp_path, "lang0001", [{"Element": "vs", "free": "y"}])
        rows = [_row("vs", "v:verbstem")]
        result = _prefill_free_occurrence_rows(rows, _FREE_PARAMS, "lang0001")
        assert all(v == "na" for v in _annot_vals(result[0]))

    def test_free_n_row_annotation_cols_left_blank(self, tmp_path, monkeypatch):
        # free=n: annotators fill in the annotation columns; leave them blank here.
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        _write_noninterruption(tmp_path, "lang0001", [{"Element": "a", "free": "n"}])
        rows = [_row("a", "p1")]
        result = _prefill_free_occurrence_rows(rows, _FREE_PARAMS, "lang0001")
        assert _free_val(result[0]) == "n"
        assert all(v == "" for v in _annot_vals(result[0]))

    def test_free_y_row_annotation_cols_set_to_na(self, tmp_path, monkeypatch):
        # free=y: element is free, so annotation columns are not applicable.
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        _write_noninterruption(tmp_path, "lang0001", [{"Element": "a", "free": "y"}])
        rows = [_row("a", "p1")]
        result = _prefill_free_occurrence_rows(rows, _FREE_PARAMS, "lang0001")
        assert _free_val(result[0]) == "y"
        assert all(v == "na" for v in _annot_vals(result[0]))


# ---------------------------------------------------------------------------
# _regen_dependents_simple
# ---------------------------------------------------------------------------

_NONPERM_SCHEMA = {
    "classes": [
        {
            "name": "nonpermutability",
            "constructions": [
                {"name": "element_prescreening"},
                {"name": "general", "depends_on": "element_prescreening",
                 "staleness_check": "element_set"},
            ],
        }
    ]
}


class TestRegenDependentsSimple:
    def _setup_lang(self, tmp_path: Path, lang_id: str) -> tuple[Path, Path]:
        d = tmp_path / lang_id / "nonpermutability"
        d.mkdir(parents=True)
        source = d / "element_prescreening.tsv"
        dep = d / "general.tsv"
        return source, dep

    def _manifest(self, lang_id: str) -> dict:
        return {lang_id: {"sheets": {"nonpermutability": {"spreadsheet_id": "fake_id"}}}}

    def test_skips_when_dep_tsv_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        monkeypatch.setattr(_gs, "load_diagnostic_classes", lambda: _NONPERM_SCHEMA)
        source, dep = self._setup_lang(tmp_path, "lang0001")
        source.write_text("Element\tscopal\na\ty\n", encoding="utf-8")
        dep.write_text("Element_A\tElement_B\tscopal\n", encoding="utf-8")

        with patch.object(_gs, "_regen_construction") as mock_regen:
            _regen_dependents_simple(MagicMock(), self._manifest("lang0001"))
        mock_regen.assert_not_called()

    def test_skips_when_source_tsv_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        monkeypatch.setattr(_gs, "load_diagnostic_classes", lambda: _NONPERM_SCHEMA)
        (tmp_path / "lang0001" / "nonpermutability").mkdir(parents=True)

        with patch.object(_gs, "_regen_construction") as mock_regen:
            _regen_dependents_simple(MagicMock(), self._manifest("lang0001"))
        mock_regen.assert_not_called()

    def test_regenerates_when_dep_tsv_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        monkeypatch.setattr(_gs, "load_diagnostic_classes", lambda: _NONPERM_SCHEMA)
        source, _ = self._setup_lang(tmp_path, "lang0001")
        source.write_text("Element\tscopal\na\ty\n", encoding="utf-8")

        with patch.object(_gs, "_regen_construction") as mock_regen:
            _regen_dependents_simple(MagicMock(), self._manifest("lang0001"))
        mock_regen.assert_called_once()
        _, call_args, _ = mock_regen.mock_calls[0]
        assert call_args[1] == "lang0001"
        assert call_args[2] == "nonpermutability"
        assert call_args[3] == "general"

    def test_skips_lang_not_in_manifest(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gs, "CODED_DATA", tmp_path)
        monkeypatch.setattr(_gs, "load_diagnostic_classes", lambda: _NONPERM_SCHEMA)
        source, _ = self._setup_lang(tmp_path, "lang0001")
        source.write_text("Element\tscopal\na\ty\n", encoding="utf-8")

        with patch.object(_gs, "_regen_construction") as mock_regen:
            _regen_dependents_simple(MagicMock(), {})  # empty manifest
        mock_regen.assert_not_called()
