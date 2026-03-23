from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, position_sets_from_element_mask

_REQUIRED_CRITERIA = {"permutable", "scopal"}


def derive_nonpermutability_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive non-permutability spans from a filled nonpermutability TSV.

    [AUTO-DERIVED: NEEDS REVIEW] Diagnostic criterion design and qualification rules were
    automatically derived from reading Tallman et al. 2024 (langsci/291), ch. 13
    (Araona) and the intro §Fracturing. Verify before use for annotation or analysis.

    Two domain types, each with complete/partial qualification = 4 strict spans:

    Strict non-permutability — positions where elements have absolutely fixed order:
      complete: ALL elements have permutable=n
      partial:  >=1 element has permutable=n

    Flexible non-permutability — positions where order is fixed OR variable only
    with an obligatory scope difference (scopal permutation):
      complete: ALL elements have permutable=n OR (permutable=y AND scopal=y)
      partial:  >=1 element has permutable=n OR (permutable=y AND scopal=y)

    Diagnostic criteria
    -------------------
    permutable : y/n — whether the element's position can vary relative to adjacent
                 positions. n = fixed order (qualifies for both domains).
    scopal     : y/n — if permutable=y, whether variable ordering is associated with
                 a difference in semantic scope. y = scopal (qualifies for flexible
                 domain only); n = free permutation (does not qualify for either domain).

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, and positions and spans for each of the four combinations.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _, _ = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA, strict=strict)

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_CRITERIA):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    # Strict domain: element must have absolutely fixed order (permutable=n).
    data_df["is_strict_nonpermutable"] = data_df["permutable"] == "n"

    # Flexible domain: element has fixed order OR variable order with obligatory
    # scope difference (scopal permutation is still considered "non-permutable"
    # under the flexible interpretation).
    data_df["is_flexible_nonpermutable"] = (
        (data_df["permutable"] == "n") |
        ((data_df["permutable"] == "y") & (data_df["scopal"] == "y"))
    )

    strict_partial,   strict_complete   = position_sets_from_element_mask(data_df, data_df["is_strict_nonpermutable"])
    flexible_partial, flexible_complete = position_sets_from_element_mask(data_df, data_df["is_flexible_nonpermutable"])

    return {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
        "strict_complete_positions":   sorted(strict_complete),
        "strict_partial_positions":    sorted(strict_partial),
        "flexible_complete_positions": sorted(flexible_complete),
        "flexible_partial_positions":  sorted(flexible_partial),
        "strict_complete_span":        strict_span(strict_complete,   keystone_pos),
        "strict_partial_span":         strict_span(strict_partial,    keystone_pos),
        "flexible_complete_span":      strict_span(flexible_complete, keystone_pos),
        "flexible_partial_span":       strict_span(flexible_partial,  keystone_pos),
    }


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_nonpermutability_domains result dict as a human-readable string."""
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
        f"Strict non-permutability complete positions:   {result['strict_complete_positions']}",
        f"Strict non-permutability partial positions:    {result['strict_partial_positions']}",
        f"Flexible non-permutability complete positions: {result['flexible_complete_positions']}",
        f"Flexible non-permutability partial positions:  {result['flexible_partial_positions']}",
        "",
        f"Strict non-permutability complete span:   {fmt(result['strict_complete_span'])}",
        f"Strict non-permutability partial span:    {fmt(result['strict_partial_span'])}",
        f"Flexible non-permutability complete span: {fmt(result['flexible_complete_span'])}",
        f"Flexible non-permutability partial span:  {fmt(result['flexible_partial_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_nonpermutability_domains
