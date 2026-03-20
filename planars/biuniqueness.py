from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"biunique"}


def derive_biuniqueness_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive biuniqueness (extended exponence) domains from a filled biuniqueness TSV.

    The biuniqueness domain identifies the span covered by a discontinuous
    morpheme — a circumfix or extended exponent where a single meaning is
    expressed by two or more pieces in different positions. The domain is
    the span from the leftmost piece to the rightmost piece.

    A position is complete if ALL its elements are pieces (biunique=n).
    A position is partial  if AT LEAST ONE element is a piece (biunique=n).

    Four span variants (strict/loose × complete/partial) = 4 spans total.
    The loose partial span is most semantically meaningful: it extends from
    the position of the prefixal piece to the position of the suffixal piece,
    directly identifying the extended exponent domain.

    Each circumfix/extended-exponent group should be annotated in its own TSV
    (one construction per file), analogous to subspanrepetition.

    Parameter
    ---------
    biunique : y/n — whether the element participates in a biunique
               (one-form / one-meaning) relationship. n = the element is one
               of the pieces of a circumfix or extended exponent set, and
               therefore deviates from strict biuniqueness.

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, piece_complete_positions, piece_partial_positions, and four span keys.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_PARAMS, strict=strict)

    missing_data = {}
    if not strict:
        blank_els = data_df.loc[data_df["biunique"] == "", "Element"].tolist()
        if blank_els:
            missing_data["biunique"] = blank_els

    # Qualifying condition: biunique=n means the element IS a piece of the
    # extended exponent (it deviates from biuniqueness).
    data_df["is_piece"] = data_df["biunique"] == "n"

    partial_positions, complete_positions = position_sets_from_element_mask(
        data_df, data_df["is_piece"]
    )

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "piece_complete_positions": sorted(complete_positions),
        "piece_partial_positions":  sorted(partial_positions),
        "strict_complete_span": strict_span(complete_positions, keystone_pos),
        "loose_complete_span":  loose_span(complete_positions,  keystone_pos),
        "strict_partial_span":  strict_span(partial_positions,  keystone_pos),
        "loose_partial_span":   loose_span(partial_positions,   keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_biuniqueness_domains result dict as a human-readable string."""
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
        f"Extended exponent piece complete positions: {result['piece_complete_positions']}",
        f"Extended exponent piece partial positions:  {result['piece_partial_positions']}",
        "",
        f"Strict complete biuniqueness span: {fmt(result['strict_complete_span'])}",
        f"Loose complete biuniqueness span:  {fmt(result['loose_complete_span'])}",
        f"Strict partial biuniqueness span:  {fmt(result['strict_partial_span'])}",
        f"Loose partial biuniqueness span:   {fmt(result['loose_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_biuniqueness_domains
