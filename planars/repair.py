from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_CRITERIA = {"restart"}
_QUALIFICATION_RULE_HASH = "29dbc84b"


def derive_repair_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive repair domains from a filled repair TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Diagnostic criterion design and qualification rules were
    automatically derived from reading Tallman et al. 2024 (langsci/291), ch. 2
    (Cup'ik) §Repair domain. Verify before use for annotation or analysis.

    The repair domain identifies the minimal span that speakers restart from
    when they make an error during production: if an error occurs at any
    position within the domain, the speaker returns to the left edge of the
    domain and starts again. This is a production-based constituency test.

    A position is complete if ALL its elements belong to the restart domain
    (restart=y). A position is partial if AT LEAST ONE element does (restart=y).

    Four span variants (strict/loose × complete/partial) = 4 spans total.

    Diagnostic criterion
    --------------------
    restart : y/n — whether this element's position is within the repair
              domain. y = an error at this position triggers restart from
              the left edge of the domain.

    Qualification rule (mirrors diagnostic_classes.yaml)
    ----------------------------------------------------
    A position qualifies if it contains an element where restart=y. Complete
    qualification: ALL elements in the position have restart=y. Partial
    qualification: at least one element has restart=y.

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, complete_positions, partial_positions, and four span keys.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["restart"] == "", "Element"].tolist()
        if blank_els:
            missing_data["restart"] = blank_els

    data_df["is_restart"] = data_df["restart"] == "y"

    partial_positions, complete_positions = position_sets_from_element_mask(
        data_df, data_df["is_restart"]
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
    """Format a derive_repair_domains result dict as a human-readable string."""
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
        f"Repair domain complete positions: {result['complete_positions']}",
        f"Repair domain partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete repair span: {fmt(result['strict_complete_span'])}",
        f"Loose complete repair span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial repair span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial repair span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_repair_domains
