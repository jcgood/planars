"""Tests for planars/coreference.py — the pair-row loading error paths (no
dedicated test file existed before Phase 6's boundary 3, issue #271; the
happy path is already covered by tests/snapshots/*_coreference_*.txt via
tests/test_snapshots.py, which stays green throughout this file's additions).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from planars.coreference import _load_planar_for_coreference, derive_coreference_domains

_PLANAR_HEADER = "Language_ID\tPlanar_Type\tPosition\tPosition_Type\tPosition_Name\tElements\tClass_Type\n"


def _write_planar(tmp_path: Path, rows: str) -> Path:
    p = tmp_path / "planar_lang0001.tsv"
    p.write_text(_PLANAR_HEADER + rows, encoding="utf-8")
    return p


def _valid_planar_rows() -> str:
    return (
        "lang0001\tverbal\t1\tSlot\tv:left\tFOO\topen\n"
        "lang0001\tverbal\t5\tSlot\tv:verbstem\tKS\topen\n"
        "lang0001\tverbal\t9\tSlot\tv:right\tBAR\topen\n"
    )


class TestLoadPlanarForCoreference:
    def test_valid_planar_loads(self, tmp_path):
        p = _write_planar(tmp_path, _valid_planar_rows())
        keystone_pos, pos_to_name, elem_to_positions = _load_planar_for_coreference(p, "lang0001")
        assert keystone_pos == 5
        assert pos_to_name[5] == "v:verbstem"
        assert "FOO" in elem_to_positions

    def test_missing_required_column_raises(self, tmp_path):
        p = tmp_path / "planar_lang0001.tsv"
        # No Elements column.
        p.write_text(
            "Language_ID\tPlanar_Type\tPosition\tPosition_Type\tPosition_Name\tClass_Type\n"
            "lang0001\tverbal\t1\tSlot\tv:left\topen\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Missing required column"):
            _load_planar_for_coreference(p, "lang0001")

    def test_non_integer_position_raises(self, tmp_path):
        rows = "lang0001\tverbal\tabc\tSlot\tv:verbstem\tKS\topen\n"
        p = _write_planar(tmp_path, rows)
        with pytest.raises(ValueError, match="Non-integer Position"):
            _load_planar_for_coreference(p, "lang0001")

    def test_no_keystone_raises(self, tmp_path):
        rows = "lang0001\tverbal\t1\tSlot\tv:left\tFOO\topen\n"
        p = _write_planar(tmp_path, rows)
        with pytest.raises(ValueError, match="No keystone row"):
            _load_planar_for_coreference(p, "lang0001")

    def test_other_language_rows_ignored(self, tmp_path):
        rows = (
            "otherlang\tverbal\tabc\tSlot\tv:left\tBAD\tbogus\n"
            + _valid_planar_rows()
        )
        p = _write_planar(tmp_path, rows)
        # The other-language row's garbage Position must not raise.
        keystone_pos, _, _ = _load_planar_for_coreference(p, "lang0001")
        assert keystone_pos == 5


class TestDeriveCoreferenceDomainsMissingColumns:
    def test_missing_element_a_column_raises(self):
        # _data bypasses the planar/pair-TSV file reads entirely, isolating
        # this test to the pair_df column-presence check.
        pair_df = pd.DataFrame({"Position_B": ["1"], "reflexive_allowed": ["y"]})
        with pytest.raises(ValueError, match="Missing required column"):
            derive_coreference_domains(
                tsv_path=Path("reflexivization.tsv"),
                _data=(pair_df, 5, {5: "v:verbstem"}, {"FOO": {1}}),
            )
