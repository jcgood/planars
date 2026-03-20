from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"applies"}


def derive_segmental_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive segmental phonological domains from a filled segmental TSV.

    A segmental domain identifies the span of positions within which a
    segmental (non-prosodic) phonological process applies. Examples include:
    vowel deletion/coalescence at position junctures (e.g., Araona vowel
    syncope domain), consonant coalescence (e.g., Cup'ik uvular-velar
    coalescence domain), nasality spreading, palatalization, and similar
    context-triggered alternations.

    Each phonological process is annotated in its own TSV (one process per
    construction). Multiple segmental processes may identify different spans.

    A position is complete if ALL its elements are within the domain
    (applies=y). A position is partial if AT LEAST ONE element is (applies=y).

    Four span variants (strict/loose × complete/partial) = 4 spans total.

    Parameter
    ---------
    applies : y/n — whether the segmental phonological process applies to
              or at this element's position. y = this position is within
              the domain of the process.

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, complete_positions, partial_positions, and four span keys.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_PARAMS, strict=strict)

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["applies"] == "", "Element"].tolist()
        if blank_els:
            missing_data["applies"] = blank_els

    data_df["is_in_domain"] = data_df["applies"] == "y"

    partial_positions, complete_positions = position_sets_from_element_mask(
        data_df, data_df["is_in_domain"]
    )

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "complete_positions": sorted(complete_positions),
        "partial_positions":  sorted(partial_positions),
        "strict_complete_span": strict_span(complete_positions, keystone_pos),
        "loose_complete_span":  loose_span(complete_positions,  keystone_pos),
        "strict_partial_span":  strict_span(partial_positions,  keystone_pos),
        "loose_partial_span":   loose_span(partial_positions,   keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_segmental_domains result dict as a human-readable string."""
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
        f"Segmental domain complete positions: {result['complete_positions']}",
        f"Segmental domain partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete segmental span: {fmt(result['strict_complete_span'])}",
        f"Loose complete segmental span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial segmental span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial segmental span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_segmental_domains
