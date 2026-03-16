from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from planars.spans import strict_span

DATA_DIR = ""


def _resolve_path(filename: str) -> Path:
    base = Path(DATA_DIR) if DATA_DIR else Path(__file__).resolve().parent
    return base / filename


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

    df["Position_Number"] = df["Position_Number"].astype(str).str.strip()
    if (df["Position_Number"] == "").any():
        raise ValueError("Some rows have blank Position_Number.")
    df["Position_Number"] = df["Position_Number"].astype(int)

    df["Position_Name"] = df["Position_Name"].astype(str).str.strip()
    df["Element"] = df["Element"].astype(str).str.strip()

    for c in ("free", "multiple"):
        df[c] = df[c].astype(str).str.strip().str.lower()

    keystone_mask = df["Position_Name"].str.lower() == "v:verbroot"
    if not keystone_mask.any():
        raise ValueError("No Keystone row found (Position_Name == 'v:verbroot').")

    keystone_positions = sorted(df.loc[keystone_mask, "Position_Number"].unique().tolist())
    if len(keystone_positions) != 1:
        raise ValueError(f"Expected exactly 1 Keystone position, found: {keystone_positions}")
    keystone_pos = keystone_positions[0]

    data_df = df.loc[~keystone_mask].copy()

    for c in ("free", "multiple"):
        if (data_df[c] == "").any():
            bad = data_df.index[data_df[c] == ""].tolist()[:10]
            raise ValueError(f"Blank value(s) in column '{c}' (example row indices: {bad}).")

    data_df["is_free"] = data_df["free"] == "y"
    data_df["is_bound"] = data_df["free"] == "n"
    data_df["is_multiple_free"] = (data_df["free"] == "y") & (data_df["multiple"] == "y")
    data_df["is_single_free_ok"] = data_df["is_bound"] | (
        (data_df["free"] == "y") & (data_df["multiple"] == "n")
    )

    no_free_complete_positions: Set[int] = set()
    no_free_partial_positions: Set[int] = set()
    single_free_complete_positions: Set[int] = set()
    single_free_partial_positions: Set[int] = set()

    for pos, grp in data_df.groupby("Position_Number"):
        p = int(pos)

        if grp["is_bound"].all():
            no_free_complete_positions.add(p)
        if grp["is_bound"].any():
            no_free_partial_positions.add(p)

        if grp["is_single_free_ok"].all():
            single_free_complete_positions.add(p)
        if grp["is_single_free_ok"].any():
            single_free_partial_positions.add(p)

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
        "no_free_complete_domain": strict_span(no_free_complete_positions, keystone_pos),
        "no_free_partial_domain": strict_span(no_free_partial_positions, keystone_pos),
        "single_free_complete_domain": strict_span(single_free_complete_positions, keystone_pos),
        "single_free_partial_domain": strict_span(single_free_partial_positions, keystone_pos),
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
    }


def format_result(result: Dict[str, object]) -> str:
    p = result["position_number_to_name"]

    def fmt(span):
        l, r = span
        return f"positions {l}\u2013{r}  ({p.get(l, '?')} \u2192 {p.get(r, '?')})"

    lines = [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"No-free complete positions:      {result['no_free_complete_positions']}",
        f"No-free partial positions:       {result['no_free_partial_positions']}",
        f"Single-free complete positions:  {result['single_free_complete_positions']}",
        f"Single-free partial positions:   {result['single_free_partial_positions']}",
        "",
        f"No-free complete span:      {fmt(result['no_free_complete_domain'])}",
        f"No-free partial span:       {fmt(result['no_free_partial_domain'])}",
        f"Single-free complete span:  {fmt(result['single_free_complete_domain'])}",
        f"Single-free partial span:   {fmt(result['single_free_partial_domain'])}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result = derive_noninterruption_domains("noninterruption_stan1293_general_fill.tsv")
    print(format_result(result))
