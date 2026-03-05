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


def derive_noninterruption_domains(filled_tsv: str) -> Dict[str, object]:
    """
    Derives four non-interruption spans from a filled noninterruption TSV.

    Assumptions about the filled TSV structure:
      - Has columns: Element, Position_Name, Position_Number, free, multiple
      - Cell values are 'y' or 'n' (case-insensitive)
      - Keystone row(s) have Position_Name == 'v:verbroot' and are excluded from
        domain logic beyond anchoring the span

    Four strict (contiguous) spans are derived by combining two domain tests
    with complete/partial position qualification:

    No-free domain — positions where elements are bound (free=n):
      complete: ALL elements in the position have free=n
      partial:  AT LEAST ONE element has free=n

    Single-free domain — positions with no multiply-occurring free elements:
      complete: ALL elements have free=n OR (free=y, multiple=n)
      partial:  AT LEAST ONE element has free=n OR (free=y, multiple=n)

    Returns a dict with:
      - keystone_position: int
      - no_free_complete_positions: sorted list
      - no_free_partial_positions: sorted list
      - single_free_complete_positions: sorted list
      - single_free_partial_positions: sorted list
      - no_free_complete_domain: (left, right) strict span
      - no_free_partial_domain: (left, right) strict span
      - single_free_complete_domain: (left, right) strict span
      - single_free_partial_domain: (left, right) strict span
      - position_number_to_name: dict for display
      - element_table: DataFrame with per-row flags added
    """
    path = _resolve_path(filled_tsv)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)

    required = {"Element", "Position_Name", "Position_Number", "free", "multiple"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {sorted(missing)}")

    # Normalize
    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    for c in ("free", "multiple"):
        df[c] = df[c].astype(str).str.strip().str.lower()

    # Keystone: excluded from domain logic, used only as span anchor
    keystone_mask = df["Position_Name"].str.lower() == "v:verbroot"
    if not keystone_mask.any():
        raise ValueError("No Keystone row found (Position_Name == 'v:verbroot').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 Keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    data_df = df.loc[~keystone_mask].copy()

    # Validate: no blank values in free or multiple for data rows
    for c in ("free", "multiple"):
        if (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) in column '{c}' (example row indices: {bad}).")

    # Per-row flags
    data_df["is_free"] = data_df["free"] == "y"
    data_df["is_bound"] = data_df["free"] == "n"
    data_df["is_multiple_free"] = (data_df["free"] == "y") & (data_df["multiple"] == "y")
    # qualifies for single-free if bound OR (free but not multiple)
    data_df["is_single_free_ok"] = data_df["is_bound"] | (
        (data_df["free"] == "y") & (data_df["multiple"] == "n")
    )

    no_free_complete_positions: Set[int] = set()
    no_free_partial_positions: Set[int] = set()
    single_free_complete_positions: Set[int] = set()
    single_free_partial_positions: Set[int] = set()

    for pos, grp in data_df.groupby("Position_Number"):
        p = int(pos)

        # No-free: complete = all bound; partial = at least one bound
        if grp["is_bound"].all():
            no_free_complete_positions.add(p)
        if grp["is_bound"].any():
            no_free_partial_positions.add(p)

        # Single-free: complete = all ok; partial = at least one ok
        if grp["is_single_free_ok"].all():
            single_free_complete_positions.add(p)
        if grp["is_single_free_ok"].any():
            single_free_partial_positions.add(p)

    # Strict spans from keystone
    no_free_complete_domain    = _strict_span(no_free_complete_positions, keystone_pos)
    no_free_partial_domain     = _strict_span(no_free_partial_positions, keystone_pos)
    single_free_complete_domain = _strict_span(single_free_complete_positions, keystone_pos)
    single_free_partial_domain  = _strict_span(single_free_partial_positions, keystone_pos)

    # Position-name lookup for display
    pos_to_name = (
        df.sort_values("Position_Number")
          .groupby("Position_Number")["Position_Name"]
          .first()
          .to_dict()
    )

    return {
        "keystone_position": keystone_pos,
        "no_free_complete_positions": sorted(no_free_complete_positions),
        "no_free_partial_positions": sorted(no_free_partial_positions),
        "single_free_complete_positions": sorted(single_free_complete_positions),
        "single_free_partial_positions": sorted(single_free_partial_positions),
        "no_free_complete_domain": no_free_complete_domain,
        "no_free_partial_domain": no_free_partial_domain,
        "single_free_complete_domain": single_free_complete_domain,
        "single_free_partial_domain": single_free_partial_domain,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
    }


if __name__ == "__main__":
    result = derive_noninterruption_domains("noninterruption_stan1293_general_fill.tsv")

    pos_to_name = result["position_number_to_name"]

    def fmt(span):
        l, r = span
        return f"positions {l}–{r}  ({pos_to_name.get(l, '?')} → {pos_to_name.get(r, '?')})"

    print("Keystone position:", result["keystone_position"],
          f"({pos_to_name.get(result['keystone_position'], '?')})")
    print()
    print("No-free complete positions:      ", result["no_free_complete_positions"])
    print("No-free partial positions:       ", result["no_free_partial_positions"])
    print("Single-free complete positions:  ", result["single_free_complete_positions"])
    print("Single-free partial positions:   ", result["single_free_partial_positions"])
    print()
    print("No-free complete domain:      ", fmt(result["no_free_complete_domain"]))
    print("No-free partial domain:       ", fmt(result["no_free_partial_domain"]))
    print("Single-free complete domain:  ", fmt(result["single_free_complete_domain"]))
    print("Single-free partial domain:   ", fmt(result["single_free_partial_domain"]))
