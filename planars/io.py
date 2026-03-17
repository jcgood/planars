from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


def load_filled_tsv(
    path: Path,
    required_params: Set[str],
    strict: bool = True,
) -> Tuple[pd.DataFrame, int, Dict[int, str], List[str]]:
    """Load and validate a filled analysis TSV.

    Reads the file, normalizes column types, locates the keystone row
    (Position_Name == 'v:verbroot'), and optionally validates that no
    parameter cells are blank in non-keystone rows.

    All non-structural columns are normalized (stripped, lowercased).
    required_params are checked for existence. When strict=True (default),
    blank values in required_params raise ValueError. When strict=False,
    blanks are left as empty strings for the caller to handle.

    Returns:
        data_df:      DataFrame of non-keystone rows
        keystone_pos: integer Position_Number of the keystone
        pos_to_name:  dict mapping Position_Number -> Position_Name
        param_cols:   list of all non-structural column names
    """
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)

    missing = (required_params | _STRUCTURAL_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    param_cols = [c for c in df.columns if c not in _STRUCTURAL_COLS]
    for c in param_cols:
        df[c] = df[c].astype(str).str.strip().str.lower()

    keystone_mask = df["Position_Name"].str.lower() == "v:verbroot"
    if not keystone_mask.any():
        raise ValueError("No keystone row found (Position_Name == 'v:verbroot').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    data_df = df.loc[~keystone_mask].copy()

    for c in required_params:
        if strict and (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) in column '{c}' (example row indices: {bad}).")

    pos_to_name = (
        df.sort_values("Position_Number")
          .groupby("Position_Number")["Position_Name"]
          .first()
          .to_dict()
    )

    return data_df, keystone_pos, pos_to_name, param_cols
