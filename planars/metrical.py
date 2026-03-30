from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import blocked_span, fmt_span, position_sets_from_element_mask

_REQUIRED_CRITERIA = {"accented", "obligatory", "independence"}


def derive_metrical_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive metrical phonological domains from a filled metrical TSV.

    Uses blocked-span logic: the domain expands from the keystone until an
    independently or obligatorily accented position creates a boundary.

    Known construction types:
      stress_domain    — boundary-defined stress domain; e.g., English, stan1293

    Diagnostic criteria
    -------------------
    accented    : y/n/both — whether this element bears accent (stress or pitch-accent).
    obligatory  : y/n      — whether accent on this element is obligatory.
    independence: y/n      — whether this element's accent is metrically independent
                             (i.e. it does not cliticize to a neighbouring domain).

    Domain logic
    ------------
    Expand from keystone in each direction, stopping just before the first
    position where the blocking condition holds.

    Minimal metrical domain — blocked by: accented ∈ {y, both} AND independence = y.
      An independently-accented element begins a new metrical domain; the minimal
      domain ends just before it.

    Maximal metrical domain — blocked by: obligatory = y AND independence = y.
      An obligatorily-independent element creates a hard boundary.

    The keystone always remains part of the domain. Its criterion values
    participate in blocking checks so the ROOT position can itself trigger a
    boundary, while always being included in the span.

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, and four span keys (minimal/maximal × partial/complete).
    """
    if _data is None:
        _data = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)
    data_df, keystone_pos, pos_to_name, _, keystone_df = _data

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_CRITERIA):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    all_positions = set(data_df["Position_Number"].unique().tolist())

    # Include keystone rows in blocking checks so the ROOT position can itself
    # trigger a domain boundary, while always remaining part of the span.
    blocking_df = pd.concat([data_df, keystone_df], ignore_index=True)

    # Minimal domain: blocked by independently accented position.
    minimal_block_mask = (
        blocking_df["accented"].isin({"y", "both"}) &
        (blocking_df["independence"] == "y")
    )
    minimal_partial_blocked, minimal_complete_blocked = position_sets_from_element_mask(
        blocking_df, minimal_block_mask
    )

    # Maximal domain: blocked by obligatory + independent accent.
    maximal_block_mask = (
        (blocking_df["obligatory"] == "y") &
        (blocking_df["independence"] == "y")
    )
    maximal_partial_blocked, maximal_complete_blocked = position_sets_from_element_mask(
        blocking_df, maximal_block_mask
    )

    return {
        "keystone_position":                  keystone_pos,
        "position_number_to_name":            pos_to_name,
        "element_table":                      data_df,
        "missing_data":                       missing_data,
        "minimal_partial_blocked_positions":  sorted(minimal_partial_blocked),
        "minimal_complete_blocked_positions": sorted(minimal_complete_blocked),
        "maximal_partial_blocked_positions":  sorted(maximal_partial_blocked),
        "maximal_complete_blocked_positions": sorted(maximal_complete_blocked),
        "minimal_partial_span":               blocked_span(all_positions, minimal_partial_blocked,  keystone_pos),
        "minimal_complete_span":              blocked_span(all_positions, minimal_complete_blocked, keystone_pos),
        "maximal_partial_span":               blocked_span(all_positions, maximal_partial_blocked,  keystone_pos),
        "maximal_complete_span":              blocked_span(all_positions, maximal_complete_blocked, keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_metrical_domains result dict as a human-readable string."""
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
        f"Minimal partial blocked positions:  {result['minimal_partial_blocked_positions']}",
        f"Minimal complete blocked positions: {result['minimal_complete_blocked_positions']}",
        f"Maximal partial blocked positions:  {result['maximal_partial_blocked_positions']}",
        f"Maximal complete blocked positions: {result['maximal_complete_blocked_positions']}",
        "",
        f"Minimal metrical span (partial):   {fmt(result['minimal_partial_span'])}",
        f"Minimal metrical span (complete):  {fmt(result['minimal_complete_span'])}",
        f"Maximal metrical span (partial):   {fmt(result['maximal_partial_span'])}",
        f"Maximal metrical span (complete):  {fmt(result['maximal_complete_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_metrical_domains
