from __future__ import annotations

from pathlib import Path
from typing import Dict

from planars.io import load_filled_tsv
from planars.spans import fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_PARAMS = {"widescope_left", "widescope_right", "fillable_botheither_conjunct"}

_CATEGORIES = {
    "maximum_fillable":        "is_fillable",
    "maximum_widescope_left":  "is_widescope_left",
    "maximum_widescope_right": "is_widescope_right",
    "maximum_narrowscope_left":  "is_narrowscope_left",
    "maximum_narrowscope_right": "is_narrowscope_right",
}


def derive_subspanrepetition_spans(tsv_path: Path, strict: bool = True) -> Dict[str, object]:
    """Derive subspan repetition spans from a filled subspanrepetition TSV.

    Span categories (each with strict/loose x complete/partial = 20 spans total):
      maximum_fillable        — fillable_botheither_conjunct == 'y'
      maximum_widescope_left  — widescope_left == 'y'
      maximum_widescope_right — widescope_right == 'y'
      maximum_narrowscope_left  — widescope_left == 'n'
      maximum_narrowscope_right — widescope_right == 'n'

    Returns a dict with keystone_position, position_number_to_name, element_table,
    missing_data, and for each category: complete_positions, partial_positions,
    strict/loose x complete/partial spans.
    """
    data_df, keystone_pos, pos_to_name, _ = load_filled_tsv(tsv_path, _REQUIRED_PARAMS, strict=strict)

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_PARAMS):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    data_df["is_fillable"]         = data_df["fillable_botheither_conjunct"] == "y"
    data_df["is_widescope_left"]   = data_df["widescope_left"] == "y"
    data_df["is_widescope_right"]  = data_df["widescope_right"] == "y"
    data_df["is_narrowscope_left"] = data_df["widescope_left"] == "n"
    data_df["is_narrowscope_right"] = data_df["widescope_right"] == "n"

    results: Dict[str, object] = {
        "keystone_position": keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table": data_df,
        "missing_data": missing_data,
    }

    for cat_name, flag_col in _CATEGORIES.items():
        partial_positions, complete_positions = position_sets_from_element_mask(
            data_df, data_df[flag_col]
        )
        results[f"{cat_name}_complete_positions"] = sorted(complete_positions)
        results[f"{cat_name}_partial_positions"]  = sorted(partial_positions)
        results[f"strict_complete_{cat_name}_span"] = strict_span(complete_positions, keystone_pos)
        results[f"loose_complete_{cat_name}_span"]  = loose_span(complete_positions, keystone_pos)
        results[f"strict_partial_{cat_name}_span"]  = strict_span(partial_positions, keystone_pos)
        results[f"loose_partial_{cat_name}_span"]   = loose_span(partial_positions, keystone_pos)

    return results


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
    ]
    for k in _CATEGORIES:
        lines += [
            "",
            f"== {k} ==",
            f"{k} complete positions: {result[f'{k}_complete_positions']}",
            f"{k} partial positions:  {result[f'{k}_partial_positions']}",
            "",
            f"Strict complete {k} span: {fmt(result[f'strict_complete_{k}_span'])}",
            f"Loose complete {k} span:  {fmt(result[f'loose_complete_{k}_span'])}",
            f"Strict partial {k} span:  {fmt(result[f'strict_partial_{k}_span'])}",
            f"Loose partial {k} span:   {fmt(result[f'loose_partial_{k}_span'])}",
        ]
    return "\n".join(lines)
