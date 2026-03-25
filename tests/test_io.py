"""Tests for planars/io.py.

Part 1 — Happy-path parity: load_filled_sheet produces identical results to
load_filled_tsv using a mock gspread Worksheet backed by a local TSV.

Part 2 — Error paths: _parse_filled_df (via load_filled_tsv with a temp file)
raises ValueError for every documented error condition.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from planars.io import load_filled_tsv, load_filled_sheet

ROOT = Path(__file__).resolve().parent.parent


class _MockWorksheet:
    """Minimal gspread.Worksheet mock backed by a local TSV file.

    Returns the exact string values from the file, matching what gspread's
    get_all_values() returns (all cells as strings, empty cells as "").
    """

    def __init__(self, path: Path):
        with open(path, encoding="utf-8", newline="") as f:
            self._rows = list(csv.reader(f, delimiter="\t"))

    def get_all_values(self):
        return [list(row) for row in self._rows]


CASES = [
    (
        "stan1293", "ciscategorial", "general",
        {"V-combines", "N-combines", "A-combines"},
    ),
    (
        "stan1293", "stress", "general",
        {"stressed", "obligatory", "independence", "left-interaction", "right-interaction"},
    ),
]


@pytest.mark.parametrize("lang_id,class_name,construction,params", CASES,
                         ids=[f"{c[0]}/{c[1]}/{c[2]}" for c in CASES])
def test_tsv_and_sheet_agree(lang_id, class_name, construction, params):
    tsv_path = ROOT / "coded_data" / lang_id / class_name / f"{construction}.tsv"
    if not tsv_path.exists():
        pytest.skip(f"file not found: {tsv_path.relative_to(ROOT)}")

    tsv_out   = load_filled_tsv(tsv_path, params, strict=False)
    sheet_out = load_filled_sheet(_MockWorksheet(tsv_path), params, strict=False)

    data_df_t, ks_pos_t, p2n_t, pcols_t, ks_df_t = tsv_out
    data_df_s, ks_pos_s, p2n_s, pcols_s, ks_df_s = sheet_out

    assert ks_pos_s  == ks_pos_t,  "keystone_pos mismatch"
    assert p2n_s     == p2n_t,     "pos_to_name mismatch"
    assert pcols_s   == pcols_t,   "criterion_cols mismatch"
    assert data_df_s.reset_index(drop=True).equals(data_df_t.reset_index(drop=True)), \
        "data_df mismatch"
    assert ks_df_s.reset_index(drop=True).equals(ks_df_t.reset_index(drop=True)), \
        "keystone_df mismatch"


# ---------------------------------------------------------------------------
# Part 2 — Error paths
# ---------------------------------------------------------------------------

def _write_tsv(df: pd.DataFrame, tmp_path: Path, name: str = "t.tsv") -> Path:
    """Write a DataFrame as a TSV to tmp_path and return the path."""
    p = tmp_path / name
    df.to_csv(p, sep="\t", index=False)
    return p


def _valid_df() -> pd.DataFrame:
    """Minimal valid 3-row DataFrame (left, keystone, right)."""
    return pd.DataFrame([
        {"Element": "elem-L", "Position_Name": "v:left",     "Position_Number": "3", "crit": "y"},
        {"Element": "ks",     "Position_Name": "v:verbstem", "Position_Number": "5", "crit": "na"},
        {"Element": "elem-R", "Position_Name": "v:right",    "Position_Number": "7", "crit": "n"},
    ])


class TestLoadFilledTsvErrorPaths:
    def test_missing_required_criterion_column(self, tmp_path):
        df = _valid_df().drop(columns=["crit"])
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Missing required column"):
            load_filled_tsv(p, required_criteria={"crit"}, strict=False)

    def test_missing_structural_column(self, tmp_path):
        df = _valid_df().drop(columns=["Element"])
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Missing required column"):
            load_filled_tsv(p, required_criteria={"crit"}, strict=False)

    def test_blank_position_number(self, tmp_path):
        df = _valid_df()
        df.loc[0, "Position_Number"] = ""
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="blank Position_Number"):
            load_filled_tsv(p, required_criteria=set(), strict=False)

    def test_no_keystone_row(self, tmp_path):
        df = _valid_df()
        df["Position_Name"] = df["Position_Name"].replace("v:verbstem", "v:notakey")
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="No keystone row"):
            load_filled_tsv(p, required_criteria=set(), strict=False)

    def test_multiple_keystone_positions(self, tmp_path):
        # Two rows with v:verbstem at different position numbers triggers the
        # name-to-number consistency check (v:verbstem → {5, 9} is inconsistent).
        df = _valid_df()
        extra = pd.DataFrame([{
            "Element": "ks2", "Position_Name": "v:verbstem",
            "Position_Number": "9", "crit": "na",
        }])
        df = pd.concat([df, extra], ignore_index=True)
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Inconsistent"):
            load_filled_tsv(p, required_criteria=set(), strict=False)

    def test_inconsistent_name_to_number(self, tmp_path):
        # Same Position_Name maps to two different Position_Numbers
        df = pd.DataFrame([
            {"Element": "a", "Position_Name": "v:left",     "Position_Number": "3", "crit": "y"},
            {"Element": "b", "Position_Name": "v:left",     "Position_Number": "4", "crit": "y"},
            {"Element": "k", "Position_Name": "v:verbstem", "Position_Number": "5", "crit": "na"},
        ])
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Inconsistent"):
            load_filled_tsv(p, required_criteria=set(), strict=False)

    def test_inconsistent_number_to_name(self, tmp_path):
        # Same Position_Number maps to two different Position_Names
        df = pd.DataFrame([
            {"Element": "a", "Position_Name": "v:left",  "Position_Number": "3", "crit": "y"},
            {"Element": "b", "Position_Name": "v:other", "Position_Number": "3", "crit": "y"},
            {"Element": "k", "Position_Name": "v:verbstem", "Position_Number": "5", "crit": "na"},
        ])
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Inconsistent"):
            load_filled_tsv(p, required_criteria=set(), strict=False)

    def test_blank_required_criterion_strict_true(self, tmp_path):
        df = _valid_df()
        df.loc[0, "crit"] = ""   # blank in a non-keystone row
        p = _write_tsv(df, tmp_path)
        with pytest.raises(ValueError, match="Blank value"):
            load_filled_tsv(p, required_criteria={"crit"}, strict=True)

    def test_blank_required_criterion_strict_false_ok(self, tmp_path):
        df = _valid_df()
        df.loc[0, "crit"] = ""
        p = _write_tsv(df, tmp_path)
        # Should not raise when strict=False
        data_df, _, _, _, _ = load_filled_tsv(p, required_criteria={"crit"}, strict=False)
        assert (data_df["crit"] == "").any()

    def test_valid_file_loads_correctly(self, tmp_path):
        p = _write_tsv(_valid_df(), tmp_path)
        data_df, ks_pos, pos_to_name, crit_cols, ks_df = load_filled_tsv(
            p, required_criteria={"crit"}, strict=False
        )
        assert ks_pos == 5
        assert pos_to_name[5] == "v:verbstem"
        assert len(data_df) == 2  # non-keystone rows
        assert len(ks_df) == 1
        assert "crit" in crit_cols


class TestLoadFilledSheetErrorPaths:
    def test_empty_sheet_raises(self):
        class _EmptyWS:
            title = "empty"
            def get_all_values(self): return []

        with pytest.raises(ValueError, match="empty"):
            load_filled_sheet(_EmptyWS(), required_criteria=set(), strict=False)

    def test_sheet_with_header_only(self):
        class _HeaderOnlyWS:
            title = "headeronly"
            def get_all_values(self):
                return [["Element", "Position_Name", "Position_Number", "crit"]]

        # Header-only: no keystone row → should raise
        with pytest.raises(ValueError, match="No keystone row"):
            load_filled_sheet(_HeaderOnlyWS(), required_criteria=set(), strict=False)
