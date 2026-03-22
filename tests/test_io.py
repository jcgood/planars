"""Test that load_filled_sheet produces identical results to load_filled_tsv.

Uses a mock gspread Worksheet backed by a local filled TSV so no network
connection is required.
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
    tsv_path = ROOT / "coded_data" / lang_id / class_name / f"{construction}_filled.tsv"
    if not tsv_path.exists():
        pytest.skip(f"file not found: {tsv_path.relative_to(ROOT)}")

    tsv_out   = load_filled_tsv(tsv_path, params, strict=False)
    sheet_out = load_filled_sheet(_MockWorksheet(tsv_path), params, strict=False)

    data_df_t, ks_pos_t, p2n_t, pcols_t, ks_df_t = tsv_out
    data_df_s, ks_pos_s, p2n_s, pcols_s, ks_df_s = sheet_out

    assert ks_pos_s  == ks_pos_t,  "keystone_pos mismatch"
    assert p2n_s     == p2n_t,     "pos_to_name mismatch"
    assert pcols_s   == pcols_t,   "param_cols mismatch"
    assert data_df_s.reset_index(drop=True).equals(data_df_t.reset_index(drop=True)), \
        "data_df mismatch"
    assert ks_df_s.reset_index(drop=True).equals(ks_df_t.reset_index(drop=True)), \
        "keystone_df mismatch"
