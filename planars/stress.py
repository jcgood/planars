from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import blocked_span, fmt_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"stressed", "obligatory", "independence"}


def derive_stress_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive stress domain spans from a filled stress TSV.

    Two domain types, each with complete/partial qualification = 4 spans:

    Minimal stress domain — expand from ROOT; stop just before the first position
    (going outward in each direction) where the blocking condition holds.
    Blocking condition: stressed ∈ {y, both} AND independence = y.
      partial:  any element in the position satisfies the condition (smaller domain)
      complete: all elements in the position satisfy the condition (larger domain)

    Maximal stress domain — expand from ROOT; stop just before the first position
    where any/all elements have obligatory = y AND independence = y.
      partial:  any element in the position satisfies the condition (smaller domain)
      complete: all elements in the position satisfy the condition (larger domain)

    The keystone (v:verbstem) is always part of the domain. Its parameter values
    participate in blocking checks but it is never excluded from the span.
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
    # trigger a domain boundary, while always remaining part of the span.
    # (keystone_df is kept separate from data_df by the loader so it is not
    # double-counted in span expansion — it is only used for blocking here.)
    blocking_df = pd.concat([data_df, keystone_df], ignore_index=True)

    # Minimal domain: blocked by a position where any/all elements are independently
    # stressed (stressed ∈ {y, both}) AND prosodically independent (independence=y).
    # Partial blocking: ANY element satisfies the condition → smaller minimal domain.
    # Complete blocking: ALL elements satisfy the condition → larger minimal domain.
    minimal_block_mask = (
        blocking_df["stressed"].isin({"y", "both"}) &
        (blocking_df["independence"] == "y")
    )
    minimal_partial_blocked, minimal_complete_blocked = position_sets_from_element_mask(
        blocking_df, minimal_block_mask
    )

    # Maximal domain: blocked by obligatory stress AND independence.
    # Same partial/complete distinction as the minimal domain.
    maximal_block_mask = (
        (blocking_df["obligatory"] == "y") &
        (blocking_df["independence"] == "y")
    )
    maximal_partial_blocked, maximal_complete_blocked = position_sets_from_element_mask(
        blocking_df, maximal_block_mask
    )

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "minimal_partial_blocked_positions": sorted(minimal_partial_blocked),
        "minimal_complete_blocked_positions": sorted(minimal_complete_blocked),
        "maximal_partial_blocked_positions": sorted(maximal_partial_blocked),
        "maximal_complete_blocked_positions": sorted(maximal_complete_blocked),
        "minimal_partial_span": blocked_span(all_positions, minimal_partial_blocked, keystone_pos),
        "minimal_complete_span": blocked_span(all_positions, minimal_complete_blocked, keystone_pos),
        "maximal_partial_span": blocked_span(all_positions, maximal_partial_blocked, keystone_pos),
        "maximal_complete_span": blocked_span(all_positions, maximal_complete_blocked, keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_stress_domains result dict as a human-readable string.

    Args:
        result: dict returned by derive_stress_domains.

    Returns:
        Multi-line string reporting blocked positions, domain spans, and any
        missing-data warnings.
    """
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
        f"Minimal partial blocked positions: {result['minimal_partial_blocked_positions']}",
        f"Minimal complete blocked positions: {result['minimal_complete_blocked_positions']}",
        f"Maximal partial blocked positions:  {result['maximal_partial_blocked_positions']}",
        f"Maximal complete blocked positions: {result['maximal_complete_blocked_positions']}",
        "",
        f"Minimal stress span (partial):  {fmt(result['minimal_partial_span'])}",
        f"Minimal stress span (complete): {fmt(result['minimal_complete_span'])}",
        f"Maximal stress span (partial):  {fmt(result['maximal_partial_span'])}",
        f"Maximal stress span (complete): {fmt(result['maximal_complete_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_stress_domains
