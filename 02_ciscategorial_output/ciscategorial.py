from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


def _strict_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """
    Contiguous (no gaps) expansion from keystone:
      extend left while (pos-1) is qualifying
      extend right while (pos+1) is qualifying
    """
    left = right = keystone_pos
    while (left - 1) in qual_positions:
        left -= 1
    while (right + 1) in qual_positions:
        right += 1
    return left, right


def _loose_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """
    Non-contiguous (gaps allowed) expansion from keystone:
      extend to the farthest qualifying position on each side (if any),
      regardless of intervening non-qualifying positions.
    """
    left_candidates = [p for p in qual_positions if p < keystone_pos]
    right_candidates = [p for p in qual_positions if p > keystone_pos]
    left = min(left_candidates) if left_candidates else keystone_pos
    right = max(right_candidates) if right_candidates else keystone_pos
    return left, right


def derive_v_ciscategorial_fractures(filled_tsv: str) -> Dict[str, object]:
    """
    Implements your v-ciscategorial domain derivation using a filled ciscategorial TSV.

    Assumptions about the filled TSV structure:
      - Has columns: Element, Position_Name, Position_Number
      - All remaining columns are parameters, including one named exactly 'V-combines'
      - Cell values are 'y', 'n', or 'NA' (case-insensitive); 'NA' only appears on Keystone row(s)
      - Keystone row(s) have Position_Name == 'Keystone' (case-insensitive) and are not treated as data

    Returns a dict with:
      - element_table: per-row computed flags
      - partial_positions: positions with >=1 v-ciscategorial element
      - full_positions: positions where ALL (non-keystone) elements are v-ciscategorial
      - four spans (left,right) for the four fractures
    """
    path = _resolve_path(filled_tsv)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)

    required = {"Element", "Position_Name", "Position_Number"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    # Identify parameter columns
    param_cols = [c for c in df.columns if c not in ["Element", "Position_Name", "Position_Number"]]
    if "V-combines" not in param_cols:
        raise ValueError(
            f"Expected a parameter column named 'V-combines'. Found: {param_cols}"
        )
    other_params = [c for c in param_cols if c != "V-combines"]

    # Normalize
    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    for c in param_cols:
        df[c] = df[c].astype(str).str.strip().str.lower()

    # Keystone handling (not data, but needed for locating the keystone position)
    keystone_mask = df["Position_Name"].str.lower() == "v:verbroot"
    if not keystone_mask.any():
        raise ValueError("No Keystone row found (Position_Name == 'Keystone').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 Keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    # Work on non-keystone rows for evidence
    data_df = df.loc[~keystone_mask].copy()

    # Basic “prototype” validation: no blanks in parameter cells (data rows)
    for c in param_cols:
        if (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) found in column '{c}' (example row indices: {bad}).")

    # v-ciscategorial row = y for V-combines AND n for every other param
    is_v = data_df["V-combines"] == "y"
    for c in other_params:
        is_v = is_v & (data_df[c] == "n")
    data_df["is_v_ciscategorial"] = is_v

    # Step 2: positions where at least one element is v-ciscategorial
    partial_positions: Set[int] = set(
        data_df.loc[data_df["is_v_ciscategorial"], "Position_Number"].unique().tolist()
    )

    # Step 3: fully v-ciscategorial positions = all elements in that position are v-ciscategorial
    full_positions: Set[int] = set()
    for pos, grp in data_df.groupby("Position_Number"):
        # if a position has no rows here, it won't appear; keystone row is excluded by design
        if len(grp) > 0 and grp["is_v_ciscategorial"].all():
            full_positions.add(int(pos))

    # Step 4: compute four fractures as spans relative to the keystone position
    strict_complete = _strict_span(full_positions, keystone_pos)
    loose_complete = _loose_span(full_positions, keystone_pos)
    strict_partial = _strict_span(partial_positions, keystone_pos)
    loose_partial = _loose_span(partial_positions, keystone_pos)

    # Optional: position-name lookup for convenient display later
    pos_to_name = (
        df.sort_values(["Position_Number"])
          .groupby("Position_Number")["Position_Name"]
          .first()
          .to_dict()
    )

    return {
        "keystone_position": keystone_pos,
        "partial_positions": sorted(partial_positions),
        "full_positions": sorted(full_positions),
        "strict_complete_v_fracture": strict_complete,
        "loose_complete_v_fracture": loose_complete,
        "strict_partial_v_fracture": strict_partial,
        "loose_partial_v_fracture": loose_partial,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,  # includes is_v_ciscategorial flag
    }


if __name__ == "__main__":
    result = derive_v_ciscategorial_fractures("ciscategorial_stan1293_general_filled.tsv")

    pos_to_name = result["position_number_to_name"]

    def fmt(span):
        l, r = span
        return f"positions {l}–{r}  ({pos_to_name.get(l, '?')} → {pos_to_name.get(r, '?')})"

    print("Keystone position:", result["keystone_position"],
          f"({pos_to_name.get(result['keystone_position'], '?')})")
    print()
    print("V-ciscategorial complete positions:", result["full_positions"])
    print("V-ciscategorial partial positions: ", result["partial_positions"])
    print()
    print("Strict complete v-ciscategorial span:", fmt(result["strict_complete_v_fracture"]))
    print("Loose complete v-ciscategorial span: ", fmt(result["loose_complete_v_fracture"]))
    print("Strict partial v-ciscategorial span: ", fmt(result["strict_partial_v_fracture"]))
    print("Loose partial v-ciscategorial span:  ", fmt(result["loose_partial_v_fracture"]))
