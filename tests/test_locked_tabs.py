"""Tests for coding/locked_tabs.py — the tabs the tooling writes and protects.

Run against the in-memory fake, so what is checked is what a sheet ends up
holding: which tabs exist, their content, their order and their protection.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coding import locked_tabs as lt
from fake_drive import FakeDriveDoorway
from planars.schema_values import STATUS_TAB

LANG = "lang0001"


def _planar(tmp_path: Path, extra: str = "") -> Path:
    p = tmp_path / f"planar_{LANG}.tsv"
    p.write_text(
        "Language_ID\tPosition\tPosition_Name\tPosition_Type\tElements\n"
        f"{LANG}\t2\tv:subj\tslot\tm2, m3\n"
        f"{LANG}\t1\tv:verbstem\tslot\tKEYSTONE\n" + extra,
        encoding="utf-8",
    )
    return p


@pytest.fixture
def classes(monkeypatch):
    table = {"classes": [
        {"name": "withref", "display_name": "With ref", "include_planar_reference_tab": True,
         "applicability_conditions": "Always."},
        {"name": "noref", "display_name": "No ref", "applicability_conditions": "Always."},
    ]}
    monkeypatch.setattr(lt, "load_diagnostic_classes", lambda: table)
    return table


@pytest.fixture
def sheet():
    doorway = FakeDriveDoorway()
    ss = doorway.create_spreadsheet("test sheet")
    ss.sheet1.update_title("general")
    ss.add_worksheet(STATUS_TAB, rows=5, cols=2)
    return doorway, ss


def _titles(ss):
    return [ws.title for ws in ss.worksheets()]


def test_registry_is_what_the_code_runs_from():
    assert lt.locked_tab_titles() == ["Instructions", "Planar Structure"]
    assert lt.system_tab_titles()[-1] == STATUS_TAB


def test_unknown_builder_hard_fails(monkeypatch):
    monkeypatch.setattr(lt, "load_planar_schema", lambda: {"locked_tabs": [
        {"title": "X", "builder": "nope", "place": "first", "include": "always"}]})
    with pytest.raises(ValueError, match="unknown builder"):
        lt.locked_tab_specs()


def test_unknown_include_hard_fails(monkeypatch):
    monkeypatch.setattr(lt, "load_planar_schema", lambda: {"locked_tabs": [
        {"title": "X", "builder": "instructions", "place": "first", "include": "sometimes"}]})
    with pytest.raises(ValueError, match="include"):
        lt.locked_tab_specs()


def test_creates_protects_and_orders(classes, sheet, tmp_path):
    doorway, ss = sheet
    changes = lt.rebuild_locked_tabs(ss, "withref", LANG, _planar(tmp_path))
    lt.reorder_tabs(ss)
    assert _titles(ss) == ["Instructions", "general", "Planar Structure", STATUS_TAB]
    ref = ss.worksheet("Planar Structure").get_all_values()
    assert ref[0] == ["Position", "Position_Name", "Position_Type", "Elements"]
    assert [r[0] for r in ref[1:]] == ["1", "2"]  # sorted by position
    for title in ("Instructions", "Planar Structure"):
        ws = ss.worksheet(title)
        [p] = ss.list_protected_ranges(ws.id)
        assert p["range"] == {"sheetId": ws.id} and p["warningOnly"] is False
        assert f"{title}: create" in changes and f"{title}: protect" in changes
    # Status is the annotators' to edit and is never protected.
    assert ss.list_protected_ranges(ss.worksheet(STATUS_TAB).id) == []


def test_second_run_writes_nothing(classes, sheet, tmp_path):
    doorway, ss = sheet
    planar = _planar(tmp_path)
    lt.rebuild_locked_tabs(ss, "withref", LANG, planar)
    doorway.clear_mutations()
    assert lt.rebuild_locked_tabs(ss, "withref", LANG, planar) == []
    assert doorway.mutations == []


def test_changed_source_is_rewritten_once(classes, sheet, tmp_path):
    doorway, ss = sheet
    lt.rebuild_locked_tabs(ss, "withref", LANG, _planar(tmp_path))
    planar = _planar(tmp_path, f"{LANG}\t3\tv:obj\tslot\tm4\n")
    changes = lt.rebuild_locked_tabs(ss, "withref", LANG, planar)
    assert changes == ["Planar Structure: refresh (its source has changed)"]
    assert ss.worksheet("Planar Structure").get_all_values()[-1][1] == "v:obj"
    # Still protected exactly once.
    assert len(ss.list_protected_ranges(ss.worksheet("Planar Structure").id)) == 1


def test_hand_edit_is_undone(classes, sheet, tmp_path):
    """Only the owner can edit a locked tab, but the owner can — and the next
    rebuild puts the generated content back."""
    _, ss = sheet
    planar = _planar(tmp_path)
    lt.rebuild_locked_tabs(ss, "withref", LANG, planar)
    ss.worksheet("Instructions").update_cell(1, 1, "edited by hand")
    assert lt.rebuild_locked_tabs(ss, "withref", LANG, planar) == [
        "Instructions: refresh (its source has changed)"]
    assert ss.worksheet("Instructions").get_all_values()[0][0].endswith("ANNOTATION INSTRUCTIONS")


def test_existing_unprotected_tab_gets_protected(classes, sheet, tmp_path):
    """Sheets made before 2026-10-13 have current tabs that were never locked."""
    _, ss = sheet
    planar = _planar(tmp_path)
    lt.rebuild_locked_tabs(ss, "withref", LANG, planar)
    ss._protected_ranges = []
    assert lt.rebuild_locked_tabs(ss, "withref", LANG, planar) == [
        "Instructions: protect", "Planar Structure: protect"]


def test_opted_out_class_loses_the_tab(classes, sheet, tmp_path):
    _, ss = sheet
    planar = _planar(tmp_path)
    lt.rebuild_locked_tabs(ss, "withref", LANG, planar)
    changes = lt.rebuild_locked_tabs(ss, "noref", LANG, planar)
    assert "Planar Structure: remove (this class no longer carries it)" in changes
    assert "Planar Structure" not in _titles(ss)


def test_dry_run_writes_nothing(classes, sheet, tmp_path):
    doorway, ss = sheet
    doorway.clear_mutations()
    changes = lt.rebuild_locked_tabs(ss, "withref", LANG, _planar(tmp_path), apply=False)
    assert "Instructions: create" in changes
    assert doorway.mutations == []
    assert _titles(ss) == ["general", STATUS_TAB]
