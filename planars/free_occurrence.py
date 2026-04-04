from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_CRITERIA = {"free"}
_QUALIFICATION_RULE_HASH = "101625a7"


def derive_free_occurrence_spans(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive free occurrence spans from a filled free_occurrence TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Diagnostic criterion design and qualification rules were
    automatically derived from reading Tallman et al. 2024 (langsci/291), ch. 13
    (Araona) §Free occurrence. Verify before use for annotation or analysis.

    The free occurrence domain identifies the span of positions where elements
    are free forms (free=y) — elements that can constitute a standalone utterance
    independently of the verbal head.

    A position is complete if ALL its elements are free forms (free=y).
    A position is partial  if AT LEAST ONE element is a free form (free=y).

    Four span variants (strict/loose × complete/partial) = 4 spans total.

    Diagnostic criterion
    --------------------
    free : y/n — whether the element can occur as a standalone utterance
           independent of the verbal head. Reuses the same criterion as
           noninterruption.py; if both analyses are run, a single annotation
           sheet with both `free` and `multiple` columns covers both.

    Qualification rule (mirrors diagnostic_classes.yaml)
    ----------------------------------------------------
    The free occurrence domain = positions where free=y. Four span variants
    (strict/loose × complete/partial) = 4 spans total.
      complete: ALL elements in the position have free=y.
      partial:  AT LEAST ONE element in the position has free=y.
    Both strict and loose spans are computed (unlike noninterruption, which uses
    strict-only, free occurrence domains need not be contiguous).
    Note on minimal vs. maximal free occurrence (Tallman et al. 2024, ch. 1): The
    Introduction distinguishes the minimal free occurrence domain (the smallest span
    that can stand as an independent utterance) from the maximal free occurrence domain
    (the largest such span). In the planar framework these correspond to the strict
    complete span (conservative/minimal) and the loose partial span
    (liberal/maximal) respectively. No additional criterion is needed.

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, complete_positions, partial_positions, and four span keys.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["free"] == "", "Element"].tolist()
        if blank_els:
            missing_data["free"] = blank_els

    data_df["is_free"] = data_df["free"] == "y"

    partial_positions, complete_positions = position_sets_from_element_mask(
        data_df, data_df["is_free"]
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
    """Format a derive_free_occurrence_spans result dict as a human-readable string."""
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
        f"Free occurrence complete positions: {result['complete_positions']}",
        f"Free occurrence partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete free occurrence span: {fmt(result['strict_complete_span'])}",
        f"Loose complete free occurrence span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial free occurrence span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial free occurrence span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_free_occurrence_spans
