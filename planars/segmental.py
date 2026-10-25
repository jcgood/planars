from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

# Criteria are construction-specific (declared via construction_criteria in
# diagnostics_{lang_id}.yaml) so no single set of required criteria applies to
# all segmental constructions.  The set of criteria used is detected dynamically
# from criterion_cols in the loaded TSV.
#
# Known construction → criteria mappings:
#   aspiration_prominence : aspirated
#   flapping              : flapping_left, flapping_internal, flapping_right
# (diagnostic_classes.yaml's required_criteria for the class is empty.)
from planars.schema_values import required_criteria

_REQUIRED_CRITERIA = required_criteria("segmental")

# Values that count toward the span (element is within the segmental domain).
# 'both' indicates variable application and is treated as in the span; the
# strong (y-only) vs. weak (y/both) distinction is latent in the data.
_IN_SPAN_VALUES = frozenset({"y", "both"})


def derive_segmental_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive segmental phonological domains from a filled segmental TSV.

    Each segmental process is annotated in its own TSV (one construction per
    TSV). Multiple segmental processes in one language may identify different
    spans. Criteria are construction-specific — declared via construction_criteria
    in diagnostics_{lang_id}.yaml — and detected dynamically from the TSV.

    Span rule (mirrors diagnostic_classes.yaml)
    -------------------------------------------
    Construction-specific positive-evidence path:

    Each construction declares its own criteria via construction_criteria in
    diagnostics_{lang_id}.yaml. An element counts toward the span when ALL of its
    construction's criteria are in {y, both}:

    Single-criterion constructions (e.g. aspiration_prominence):
      aspirated ∈ {y, both} → element counts toward the span.

    Multi-criterion chain constructions (e.g. flapping):
      ALL of flapping_left, flapping_internal, flapping_right ∈ {y, both}
      → element counts toward the span (the flapping chain is unbroken at this
      element). n or na at any criterion breaks the chain.

    both counts toward the span in all cases: it indicates variable application
    of the process. The strong/weak distinction (y-only vs y/both) is latent
    in the annotation data and can be derived analytically.

    Complete: ALL elements in the position count toward the span.
    Partial: at least one element counts toward the span.
    Returns four spans (strict/loose × complete/partial).

    The keystone row is included when deciding which elements count toward the
    span, so the verbstem's criterion values participate (mirrors metrical.py
    blocking-check pattern).
    """
    if _data is None:
        _data = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)
    data_df, keystone_pos, pos_to_name, criterion_cols, keystone_df = _data

    if not criterion_cols:
        if strict:
            raise ValueError(
                "Segmental TSV has no criterion columns. "
                "Ensure construction_criteria is set in diagnostics_{lang_id}.yaml."
            )
        # strict=False (e.g. check-codebook schema validation): return empty result.
        empty: set = set()
        return {
            "keystone_position":       keystone_pos,
            "position_number_to_name": pos_to_name,
            "element_table":           data_df,
            "missing_data":            {},
            "criterion_cols":          [],
            "complete_positions":      [],
            "partial_positions":       [],
            "position_counts":         {},
            "strict_complete_span":    strict_span(empty, keystone_pos),
            "loose_complete_span":     loose_span(empty, keystone_pos),
            "strict_partial_span":     strict_span(empty, keystone_pos),
            "loose_partial_span":      loose_span(empty, keystone_pos),
        }

    # Include keystone rows so verbstem criterion values participate in the span rule.
    domain_df = pd.concat([data_df, keystone_df], ignore_index=True)

    missing_data: Dict[str, List[str]] = {}
    if not strict:
        for col in criterion_cols:
            blank_els = domain_df.loc[domain_df[col] == "", "Element"].tolist()
            if blank_els:
                missing_data[col] = blank_els

    # An element is in the span when ALL criteria are in {y, both}.
    in_span = pd.Series(True, index=domain_df.index)
    for col in criterion_cols:
        in_span &= domain_df[col].isin(_IN_SPAN_VALUES)

    partial_positions, complete_positions, position_counts = position_sets_from_element_mask(
        domain_df, in_span
    )

    return {
        "keystone_position":       keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table":           data_df,
        "missing_data":            missing_data,
        "criterion_cols":          list(criterion_cols),
        "complete_positions":      sorted(complete_positions),
        "partial_positions":       sorted(partial_positions),
        "position_counts":         position_counts,
        "strict_complete_span":    strict_span(complete_positions, keystone_pos),
        "loose_complete_span":     loose_span(complete_positions,  keystone_pos),
        "strict_partial_span":     strict_span(partial_positions,  keystone_pos),
        "loose_partial_span":      loose_span(partial_positions,   keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_segmental_domains result dict as a human-readable string."""
    p = result["position_number_to_name"]
    fmt = lambda span: fmt_span(span, p)
    criteria = result.get("criterion_cols", [])
    lines = []
    missing = result.get("missing_data", {})
    if missing:
        lines.append(
            "NOTE: Some cells are unannotated — spans computed treating blanks as outside the span."
        )
        for col, elements in missing.items():
            preview = elements[:5]
            suffix = f" … ({len(elements)} total)" if len(elements) > 5 else ""
            lines.append(f"  {col}: {preview}{suffix}")
        lines.append("")
    lines += [
        f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})",
        f"Criteria: {', '.join(criteria) if criteria else '(none)'}",
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
