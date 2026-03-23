from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


def _parse_filled_df(
    df: pd.DataFrame,
    required_criteria: Set[str],
    strict: bool,
) -> Tuple[pd.DataFrame, int, Dict[int, str], List[str]]:
    """Core parsing logic shared by load_filled_tsv and load_filled_sheet.

    Normalizes column types, validates structural integrity, locates the keystone
    row (Position_Name == 'v:verbstem'), and splits keystone rows from the rest.

    Args:
        df: raw DataFrame with at least the structural columns and required_criteria.
        required_criteria: parameter column names that must be present and (when
            strict=True) non-blank in all non-keystone rows.
        strict: if True, raise ValueError on any blank required_param cell in
            non-keystone rows; if False, leave blanks as empty strings.

    Returns:
        data_df:      DataFrame of non-keystone rows, all param cells normalized.
        keystone_pos: integer Position_Number of the keystone row.
        pos_to_name:  dict mapping Position_Number -> Position_Name.
        criterion_cols:   list of all non-structural column names (criteria + trailing).
        keystone_df:  DataFrame of keystone rows (for blocking checks in stress/aspiration).
    """
    missing = (required_criteria | _STRUCTURAL_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    criterion_cols = [c for c in df.columns if c not in _STRUCTURAL_COLS]
    for c in criterion_cols:
        df[c] = df[c].astype(str).str.strip().str.lower()

    # Validate Position_Name ↔ Position_Number is a consistent 1-to-1 mapping.
    # A mismatch means the sheet was generated from a different version of the
    # planar structure (e.g. a position was inserted or renumbered).
    name_to_num_count = df.groupby("Position_Name")["Position_Number"].nunique()
    num_to_name_count = df.groupby("Position_Number")["Position_Name"].nunique()
    bad_names = name_to_num_count[name_to_num_count > 1].index.tolist()
    bad_nums  = num_to_name_count[num_to_name_count > 1].index.tolist()
    if bad_names or bad_nums:
        msgs = []
        if bad_names:
            msgs.append(f"Position_Name(s) with multiple Position_Numbers: {bad_names}")
        if bad_nums:
            msgs.append(f"Position_Number(s) with multiple Position_Names: {bad_nums}")
        raise ValueError(
            "Inconsistent Position_Name ↔ Position_Number mapping "
            "(sheet may be out of sync with the planar structure — "
            "run restructure_sheets.py):\n  " + "\n  ".join(msgs)
        )

    keystone_mask = df["Position_Name"].str.lower() == "v:verbstem"
    if not keystone_mask.any():
        raise ValueError("No keystone row found (Position_Name == 'v:verbstem').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    keystone_df = df.loc[keystone_mask].copy()
    data_df = df.loc[~keystone_mask].copy()

    for c in required_criteria:
        if strict and (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) in column '{c}' (example row indices: {bad}).")

    pos_to_name = (
        df.sort_values("Position_Number")
          .groupby("Position_Number")["Position_Name"]
          .first()
          .to_dict()
    )

    return data_df, keystone_pos, pos_to_name, criterion_cols, keystone_df


def load_filled_tsv(
    path: Path,
    required_criteria: Set[str],
    strict: bool = True,
) -> Tuple[pd.DataFrame, int, Dict[int, str], List[str], pd.DataFrame]:
    """Load and validate a filled analysis TSV.

    Reads the file, normalizes column types, locates the keystone row
    (Position_Name == 'v:verbstem'), and optionally validates that no
    parameter cells are blank in non-keystone rows.

    All non-structural columns are normalized (stripped, lowercased).
    required_criteria are checked for existence. When strict=True (default),
    blank values in required_criteria raise ValueError. When strict=False,
    blanks are left as empty strings for the caller to handle.

    Returns:
        data_df:      DataFrame of non-keystone rows
        keystone_pos: integer Position_Number of the keystone
        pos_to_name:  dict mapping Position_Number -> Position_Name
        criterion_cols:   list of all non-structural column names
        keystone_df:  DataFrame of keystone rows (for blocking checks)
    """
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    return _parse_filled_df(df, required_criteria, strict)


def load_filled_sheet(
    ws,
    required_criteria: Set[str],
    strict: bool = True,
) -> Tuple[pd.DataFrame, int, Dict[int, str], List[str], pd.DataFrame]:
    """Load and validate a filled annotation from a gspread Worksheet.

    Reads all values from the worksheet and applies the same normalization
    and validation as load_filled_tsv. Intended for Colab workflows where
    data is read directly from Google Sheets without a local TSV intermediary.

    Returns the same 5-tuple as load_filled_tsv:
    (data_df, keystone_pos, pos_to_name, criterion_cols, keystone_df).
    """
    rows = ws.get_all_values()
    if not rows:
        raise ValueError(f"Sheet '{ws.title}' is empty.")
    header, data_rows = rows[0], rows[1:]
    df = pd.DataFrame(data_rows, columns=header)
    return _parse_filled_df(df, required_criteria, strict)
