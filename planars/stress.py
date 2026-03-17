from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import blocked_span, fmt_span

_REQUIRED_PARAMS = {"stressable", "obligatory", "independence"}


def derive_stress_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive stress domain spans from a filled stress TSV.

    Two domain types, each producing a single span:

    Minimal stress domain — expand from ROOT; stop just before the first position
    (going outward in each direction) where any element has stressable ∈ {y, both}
    AND independence = y. That position is excluded (it begins a new stress domain).

    Maximal stress domain — expand from ROOT; stop just before the first position
    where any element has obligatory = y AND independence = y. Everything before
    that blocking position is included.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, keystone_df = _data
    else:
        data_df, keystone_pos, pos_to_name, _, keystone_df = load_filled_tsv(
            tsv_path, _REQUIRED_PARAMS, strict=strict
        )

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_PARAMS):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    all_positions = set(data_df["Position_Number"].unique().tolist())

    # Include keystone rows in blocking checks so the ROOT position can itself
    # trigger a domain boundary (e.g. obligatory=y AND independence=y on the ROOT).
    blocking_df = pd.concat([data_df, keystone_df], ignore_index=True)

    # Minimal: blocked by (stressable ∈ {y, both}) AND (independence = y)
    minimal_block_mask = (
        blocking_df["stressable"].isin({"y", "both"}) &
        (blocking_df["independence"] == "y")
    )
    minimal_blocked = set(
        blocking_df.loc[minimal_block_mask, "Position_Number"].unique().tolist()
    )

    # Maximal: blocked by (obligatory = y) AND (independence = y)
    maximal_block_mask = (
        (blocking_df["obligatory"] == "y") &
        (blocking_df["independence"] == "y")
    )
    maximal_blocked = set(
        blocking_df.loc[maximal_block_mask, "Position_Number"].unique().tolist()
    )

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "minimal_blocked_positions": sorted(minimal_blocked),
        "maximal_blocked_positions": sorted(maximal_blocked),
        "minimal_span": blocked_span(all_positions, minimal_blocked, keystone_pos),
        "maximal_span": blocked_span(all_positions, maximal_blocked, keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)
    lines = []
    missing = result.get("missing_data", {})
    if missing:
        lines.append(
            "NOTE: Some cells are unannotated — spans computed treating blanks as non-qualifying."
        )
        for col, elements in missing.items():
            preview = elements[:5]
            suffix = f" … ({len(elements)} total)" if len(elements) > 5 else ""
            lines.append(f"  {col}: {preview}{suffix}")
        lines.append("")
    lines += [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        "",
        f"Minimal blocked positions: {result['minimal_blocked_positions']}",
        f"Maximal blocked positions: {result['maximal_blocked_positions']}",
        "",
        f"Minimal stress span: {fmt(result['minimal_span'])}",
        f"Maximal stress span: {fmt(result['maximal_span'])}",
    ]
    return "\n".join(lines)
