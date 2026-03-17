from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"free", "multiple"}


def derive_noninterruption_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive non-interruption spans from a filled noninterruption TSV.

    Two domain types, each with complete/partial qualification = 4 strict spans:

    No-free domain — positions where elements are bound (free=n):
      complete: ALL elements have free=n
      partial:  >=1 element has free=n

    Single-free domain — positions with no multiply-occurring free elements:
      complete: ALL elements have free=n OR (free=y, multiple=n)
      partial:  >=1 element has free=n OR (free=y, multiple=n)

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, and positions and spans for each of the four combinations.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _ = _data
    else:
        data_df, keystone_pos, pos_to_name, _ = load_filled_tsv(tsv_path, _REQUIRED_PARAMS, strict=strict)

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_PARAMS):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    data_df["is_bound"] = data_df["free"] == "n"
    data_df["is_single_free_ok"] = (
        (data_df["free"] == "n") |
        ((data_df["free"] == "y") & (data_df["multiple"] == "n"))
    )

    no_free_partial,    no_free_complete    = position_sets_from_element_mask(data_df, data_df["is_bound"])
    single_free_partial, single_free_complete = position_sets_from_element_mask(data_df, data_df["is_single_free_ok"])

    return {
        "keystone_position": keystone_pos,
        "missing_data": missing_data,
        "no_free_complete_positions":     sorted(no_free_complete),
        "no_free_partial_positions":      sorted(no_free_partial),
        "single_free_complete_positions": sorted(single_free_complete),
        "single_free_partial_positions":  sorted(single_free_partial),
        "no_free_complete_span":          strict_span(no_free_complete, keystone_pos),
        "no_free_partial_span":           strict_span(no_free_partial, keystone_pos),
        "single_free_complete_span":      strict_span(single_free_complete, keystone_pos),
        "single_free_partial_span":       strict_span(single_free_partial, keystone_pos),
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
    }


def format_result(result: Dict[str, object]) -> str:
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
        f"No-free complete positions:      {result['no_free_complete_positions']}",
        f"No-free partial positions:       {result['no_free_partial_positions']}",
        f"Single-free complete positions:  {result['single_free_complete_positions']}",
        f"Single-free partial positions:   {result['single_free_partial_positions']}",
        "",
        f"No-free complete span:      {fmt(result['no_free_complete_span'])}",
        f"No-free partial span:       {fmt(result['no_free_partial_span'])}",
        f"Single-free complete span:  {fmt(result['single_free_complete_span'])}",
        f"Single-free partial span:   {fmt(result['single_free_partial_span'])}",
    ]
    return "\n".join(lines)
