from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, loose_span, strict_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"stressable"}

# NOTE: The qualification rule below is provisional.
# A position qualifies for the stressable domain if its elements can carry stress
# (stressable=y or stressable=both). stressable=n elements do not qualify.
# Refine this rule and update codebook.yaml once the analysis design is confirmed.


def derive_stress_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive stress domain spans from a filled stress TSV.

    Stressable domain — positions where elements can carry stress:
      complete: ALL elements have stressable=y or stressable=both
      partial:  >=1 element has stressable=y or stressable=both

    Returns strict and loose spans for each of the four combinations
    (strict/loose × complete/partial).

    PROVISIONAL: qualification rule needs confirmation against codebook.yaml.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _ = load_filled_tsv(
            tsv_path, _REQUIRED_PARAMS, strict=strict
        )

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["stressable"] == "", "Element"].tolist()
        if blank_els:
            missing_data["stressable"] = blank_els

    data_df["qualifies"] = data_df["stressable"].isin({"y", "both"})

    partial_positions, complete_positions = position_sets_from_element_mask(
        data_df, data_df["qualifies"]
    )

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "complete_positions": sorted(complete_positions),
        "partial_positions":  sorted(partial_positions),
        "strict_complete_span": strict_span(complete_positions, keystone_pos),
        "loose_complete_span":  loose_span(complete_positions, keystone_pos),
        "strict_partial_span":  strict_span(partial_positions, keystone_pos),
        "loose_partial_span":   loose_span(partial_positions, keystone_pos),
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
        f"Stressable complete positions: {result['complete_positions']}",
        f"Stressable partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete span: {fmt(result['strict_complete_span'])}",
        f"Loose complete span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)
