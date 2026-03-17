from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span

_TRAILING_COLS = {"Comments"}


def derive_v_ciscategorial_fractures(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive v-ciscategorial fracture spans from a filled ciscategorial TSV.

    A position qualifies if elements have V-combines=y and all other params=n.

    Returns a dict with:
      - keystone_position
      - complete_positions: positions where ALL elements are v-ciscategorial
      - partial_positions:  positions where >=1 element is v-ciscategorial
      - strict_complete_span, loose_complete_span
      - strict_partial_span, loose_partial_span
      - position_number_to_name
      - element_table: DataFrame with is_v_ciscategorial flag
      - missing_data: {col: [elements]} for blank annotation cells (empty if none)
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, param_cols, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, param_cols, _ = load_filled_tsv(
            tsv_path, required_params={"V-combines"}, strict=strict
        )

    if "V-combines" not in param_cols:
        raise ValueError(f"Expected a parameter column named 'V-combines'. Found: {param_cols}")

    other_params = [c for c in param_cols if c != "V-combines" and c not in _TRAILING_COLS]

    if strict:
        for c in other_params:
            if (data_df[c] == "").any():
                bad = data_df.index[data_df[c] == ""].tolist()[:10]
                raise ValueError(f"Blank value(s) in column '{c}' (example row indices: {bad}).")

    missing_data = {}
    if not strict:
        for c in ["V-combines"] + other_params:
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    is_v = data_df["V-combines"] == "y"
    for c in other_params:
        is_v = is_v & (data_df[c] == "n")
    data_df["is_v_ciscategorial"] = is_v

    complete_positions = set(
        int(pos) for pos, grp in data_df.groupby("Position_Number")
        if len(grp) > 0 and grp["is_v_ciscategorial"].all()
    )
    partial_positions = set(
        data_df.loc[data_df["is_v_ciscategorial"], "Position_Number"].unique().tolist()
    )

    return {
        "keystone_position": keystone_pos,
        "complete_positions": sorted(complete_positions),
        "partial_positions": sorted(partial_positions),
        "strict_complete_span": strict_span(complete_positions, keystone_pos),
        "loose_complete_span": loose_span(complete_positions, keystone_pos),
        "strict_partial_span": strict_span(partial_positions, keystone_pos),
        "loose_partial_span": loose_span(partial_positions, keystone_pos),
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
    }


def format_result(result: Dict[str, object]) -> str:
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)
    lines = []
    missing = result.get("missing_data", {})
    if missing:
        lines.append("NOTE: Some cells are unannotated — spans computed treating blanks as non-qualifying.")
        for col, elements in missing.items():
            preview = elements[:5]
            suffix = f" … ({len(elements)} total)" if len(elements) > 5 else ""
            lines.append(f"  {col}: {preview}{suffix}")
        lines.append("")
    lines += [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"V-ciscategorial complete positions: {result['complete_positions']}",
        f"V-ciscategorial partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete v-ciscategorial span: {fmt(result['strict_complete_span'])}",
        f"Loose complete v-ciscategorial span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial v-ciscategorial span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial v-ciscategorial span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)
