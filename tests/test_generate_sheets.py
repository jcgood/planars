"""Tests for coding/generate_sheets.py — data-protection helpers.

Covers _check_force_against_existing_sheets, which blocks --force when a
language already has annotation sheet IDs in the manifest.
"""
from __future__ import annotations

import pytest

from coding.generate_sheets import _check_force_against_existing_sheets


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
