from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"applies"}


def derive_play_language_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive play language domains from a filled play_language TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Parameter design was automatically derived from
    reading Tallman et al. 2024 (langsci/291), Discussion ch. 17 and a brief mention
    in ch. 8 (Chatino) — no complete language data section was reviewed. Parameter
    design is speculative. Verify thoroughly before use.

    The play language domain identifies the span of positions targeted by
    play language (ludling) operations — e.g., infixation in pig-Latin-like
    games, reversal or permutation of elements within a span. The domain is
    the span within which the ludling operation applies. Currently attested
    in Zenzontepec Chatino (Tallman et al. 2024, ch. 8). Classified as a
    phonological domain type.

    A position is complete if ALL its elements are within the play language
    domain (applies=y). A position is partial if AT LEAST ONE element is
    (applies=y).

    Four span variants (strict/loose × complete/partial) = 4 spans total.

    Parameter
    ---------
    applies : y/n — whether the play language operation targets this element's
              position. y = this position is within the domain of the operation.

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
    """Format a derive_play_language_domains result dict as a human-readable string."""
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
        f"Play language domain complete positions: {result['complete_positions']}",
        f"Play language domain partial positions:  {result['partial_positions']}",
        "",
        f"Strict complete play language span: {fmt(result['strict_complete_span'])}",
        f"Loose complete play language span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial play language span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial play language span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_play_language_domains
