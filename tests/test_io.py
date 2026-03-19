#!/usr/bin/env python3
"""Test that load_filled_sheet produces identical results to load_filled_tsv.

Uses a mock gspread Worksheet backed by a local filled TSV so no network
connection is required.

Run from the repo root:
    python tests/test_io.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from planars.io import load_filled_tsv, load_filled_sheet


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


def _check(label, got, expected):
    if isinstance(got, pd.DataFrame):
        g = got.reset_index(drop=True)
        e = expected.reset_index(drop=True)
        if not g.equals(e):
            raise AssertionError(
                f"FAIL {label}: DataFrames differ\n"
                f"  got columns:      {list(g.columns)}\n"
                f"  expected columns: {list(e.columns)}\n"
                f"  got shape: {g.shape}, expected shape: {e.shape}"
            )
    elif got != expected:
        raise AssertionError(f"FAIL {label}: got {got!r}, expected {expected!r}")
    print(f"  ok  {label}")


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


def main():
    errors = 0
    for lang_id, class_name, construction, params in CASES:
        tsv_path = ROOT / "coded_data" / lang_id / class_name / f"{construction}_filled.tsv"
        if not tsv_path.exists():
            print(f"  SKIP {lang_id}/{class_name}/{construction}: file not found")
            continue

        print(f"\n{lang_id}/{class_name}/{construction}")
        try:
            tsv_out = load_filled_tsv(tsv_path, params, strict=False)
            sheet_out = load_filled_sheet(_MockWorksheet(tsv_path), params, strict=False)

            data_df_t, ks_pos_t, p2n_t, pcols_t, ks_df_t = tsv_out
            data_df_s, ks_pos_s, p2n_s, pcols_s, ks_df_s = sheet_out

            _check("keystone_pos", ks_pos_s, ks_pos_t)
            _check("pos_to_name",  p2n_s,    p2n_t)
            _check("param_cols",   pcols_s,  pcols_t)
            _check("data_df",      data_df_s, data_df_t)
            _check("keystone_df",  ks_df_s,  ks_df_t)
        except AssertionError as e:
            print(f"  {e}")
            errors += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print()
    if errors:
        print(f"{errors} test(s) failed.")
        sys.exit(1)
    else:
        print("All tests passed.")


if __name__ == "__main__":
    main()
