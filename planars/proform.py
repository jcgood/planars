from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_CRITERIA = {"shareable_proform_replace"}


def derive_proform_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive proform substitution domains from a filled proform TSV.

    [NEEDS REVIEW] Criterion design confirmed by Adam Tallman (May 2026);
    not yet validated against annotation data.

    The proform domain identifies the span of positions that can be replaced
    by a proform (pro-verb, pro-VP, e.g. "do so"). Classified as a
    morphosyntactic domain type (Tallman et al. 2024).

    Two-tier qualification rule
    ---------------------------
    shareable_proform_replace=y    → element strictly qualifies
    shareable_proform_replace=both → element loosely qualifies (adjunct-style:
                                     optionally inside or outside the "do so" span)
    shareable_proform_replace=n    → element does not qualify

    A position strictly qualifies (complete) when ALL elements = y.
    A position loosely qualifies (partial) when ANY element = y or both.

    Strict span uses complete positions; loose span uses partial positions
    (which subsumes complete).

    Four span variants (strict/loose × complete/partial) = 4 spans total.

    Qualification rule (mirrors diagnostic_classes.yaml)
    ----------------------------------------------------
    Two-tier qualification. Strict (complete) qualification: ALL elements in the
    position have shareable_proform_replace=y. Loose (partial) qualification: at
    least one element has shareable_proform_replace=y or shareable_proform_replace=both.
    Positions where all elements are n do not qualify. Strict span uses complete
    positions; loose span uses partial positions (which subsumes complete).

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, complete_positions, partial_positions, and four span keys.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["shareable_proform_replace"] == "", "Element"].tolist()
        if blank_els:
            missing_data["shareable_proform_replace"] = blank_els

    # Strict (complete) qualification: element always replaceable
    is_strong = data_df["shareable_proform_replace"] == "y"

    # Loose (partial) qualification: element always or optionally replaceable
    is_weak = data_df["shareable_proform_replace"].isin(["y", "both"])

    _, complete_positions = position_sets_from_element_mask(data_df, is_strong)
    partial_positions, _ = position_sets_from_element_mask(data_df, is_weak)

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
    """Format a derive_proform_domains result dict as a human-readable string."""
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
        f"Proform substitution complete positions (all elements y):   {result['complete_positions']}",
        f"Proform substitution partial positions  (any element y/both): {result['partial_positions']}",
        "",
        f"Strict complete proform span: {fmt(result['strict_complete_span'])}",
        f"Loose complete proform span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial proform span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial proform span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_proform_domains
