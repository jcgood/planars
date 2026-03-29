from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import blocked_span, fmt_span, strict_span, loose_span, position_sets_from_element_mask

_REQUIRED_CRITERIA_BLOCKED  = {"accented", "obligatory", "independence"}
_REQUIRED_CRITERIA_POSITIVE = {"applies"}


# ---------------------------------------------------------------------------
# Blocked-span path (stress_domain: accented/obligatory/independence criteria)
# ---------------------------------------------------------------------------

def _derive_blocked_domain(data: Tuple, strict: bool) -> Dict[str, object]:
    data_df, keystone_pos, pos_to_name, _, keystone_df = data

    missing_data = {}
    if not strict:
        for c in sorted(_REQUIRED_CRITERIA_BLOCKED):
            blank_els = data_df.loc[data_df[c] == "", "Element"].tolist()
            if blank_els:
                missing_data[c] = blank_els

    all_positions = set(data_df["Position_Number"].unique().tolist())

    # Include keystone rows in blocking checks so the ROOT position can itself
    # trigger a domain boundary, while always remaining part of the span.
    blocking_df = pd.concat([data_df, keystone_df], ignore_index=True)

    # Minimal domain: blocked by independently accented position.
    minimal_block_mask = (
        blocking_df["accented"].isin({"y", "both"}) &
        (blocking_df["independence"] == "y")
    )
    minimal_partial_blocked, minimal_complete_blocked = position_sets_from_element_mask(
        blocking_df, minimal_block_mask
    )

    # Maximal domain: blocked by obligatory + independent stress.
    maximal_block_mask = (
        (blocking_df["obligatory"] == "y") &
        (blocking_df["independence"] == "y")
    )
    maximal_partial_blocked, maximal_complete_blocked = position_sets_from_element_mask(
        blocking_df, maximal_block_mask
    )

    return {
        "domain_logic":                       "blocked",
        "keystone_position":                  keystone_pos,
        "position_number_to_name":            pos_to_name,
        "element_table":                      data_df,
        "missing_data":                       missing_data,
        "minimal_partial_blocked_positions":  sorted(minimal_partial_blocked),
        "minimal_complete_blocked_positions": sorted(minimal_complete_blocked),
        "maximal_partial_blocked_positions":  sorted(maximal_partial_blocked),
        "maximal_complete_blocked_positions": sorted(maximal_complete_blocked),
        "minimal_partial_span":               blocked_span(all_positions, minimal_partial_blocked,  keystone_pos),
        "minimal_complete_span":              blocked_span(all_positions, minimal_complete_blocked, keystone_pos),
        "maximal_partial_span":               blocked_span(all_positions, maximal_partial_blocked,  keystone_pos),
        "maximal_complete_span":              blocked_span(all_positions, maximal_complete_blocked, keystone_pos),
    }


# ---------------------------------------------------------------------------
# Positive-qualification path (applies criterion: pitch-accent, iambic foot, etc.)
# ---------------------------------------------------------------------------

def _derive_positive_domain(data: Tuple, strict: bool) -> Dict[str, object]:
    data_df, keystone_pos, pos_to_name, _, _ = data

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
        "domain_logic":            "positive",
        "keystone_position":       keystone_pos,
        "position_number_to_name": pos_to_name,
        "element_table":           data_df,
        "missing_data":            missing_data,
        "complete_positions":      sorted(complete_positions),
        "partial_positions":       sorted(partial_positions),
        "strict_complete_span":    strict_span(complete_positions, keystone_pos),
        "loose_complete_span":     loose_span(complete_positions,  keystone_pos),
        "strict_partial_span":     strict_span(partial_positions,  keystone_pos),
        "loose_partial_span":      loose_span(partial_positions,   keystone_pos),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def derive_metrical_domains(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive metrical phonological domains from a filled metrical TSV.

    Dispatches on the criterion columns present in the data:

    - ``accented`` / ``obligatory`` / ``independence`` columns → blocked-span
      path for stress_domain constructions. The domain expands from the
      keystone until an independently or obligatorily accented position
      creates a boundary. Returns minimal/maximal × partial/complete spans.

    - ``applies`` column → positive-qualification path for pitch-accent,
      iambic foot, word-stress, and similar positively-delimited metrical
      domains. Returns four standard spans (strict/loose × complete/partial).

    Known construction types:
      stress_domain         — blocked-span (accented/obligatory/independence)
      pitch-accent domain   — positive-qual (applies); e.g., Araona, Quechua
      iambic foot domain    — positive-qual (applies); e.g., Cup'ik
      word-stress domain    — positive-qual (applies); e.g., Mebengokre
      right-edge stress domain — positive-qual (applies); e.g., Mocoví
      tone-stress locus domain — positive-qual (applies); e.g., Hup
      auxiliary construction domain — positive-qual (applies); e.g., Quechua

    Returns a dict with ``domain_logic`` ("blocked" or "positive") plus
    result keys appropriate to that logic type.
    """
    if _data is not None:
        _, _, _, criterion_cols, _ = _data
        col_set = set(criterion_cols)
    else:
        _header = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False, nrows=0)
        col_set = set(_header.columns)

    if "accented" in col_set:
        if _data is None:
            _data = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA_BLOCKED, strict=strict)
        return _derive_blocked_domain(_data, strict)
    elif "applies" in col_set:
        if _data is None:
            _data = load_filled_tsv(tsv_path, _REQUIRED_CRITERIA_POSITIVE, strict=strict)
        return _derive_positive_domain(_data, strict)
    else:
        raise ValueError(
            f"Cannot determine metrical domain type from columns {sorted(col_set)}. "
            "Expected 'accented' (blocked-span) or 'applies' (positive qualification)."
        )


def format_result(result: Dict[str, object]) -> str:
    """Format a derive_metrical_domains result dict as a human-readable string."""
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
    lines.append(f"Keystone position: {result['keystone_position']} ({p.get(result['keystone_position'], '?')})")
    lines.append("")

    if result.get("domain_logic") == "blocked":
        lines += [
            f"Minimal partial blocked positions:  {result['minimal_partial_blocked_positions']}",
            f"Minimal complete blocked positions: {result['minimal_complete_blocked_positions']}",
            f"Maximal partial blocked positions:  {result['maximal_partial_blocked_positions']}",
            f"Maximal complete blocked positions: {result['maximal_complete_blocked_positions']}",
            "",
            f"Minimal metrical span (partial):   {fmt(result['minimal_partial_span'])}",
            f"Minimal metrical span (complete):  {fmt(result['minimal_complete_span'])}",
            f"Maximal metrical span (partial):   {fmt(result['maximal_partial_span'])}",
            f"Maximal metrical span (complete):  {fmt(result['maximal_complete_span'])}",
        ]
    else:
        lines += [
            f"Metrical domain complete positions: {result['complete_positions']}",
            f"Metrical domain partial positions:  {result['partial_positions']}",
            "",
            f"Strict complete metrical span: {fmt(result['strict_complete_span'])}",
            f"Loose complete metrical span:  {fmt(result['loose_complete_span'])}",
            f"Strict partial metrical span:  {fmt(result['strict_partial_span'])}",
            f"Loose partial metrical span:   {fmt(result['loose_partial_span'])}",
        ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py to call each module's main
# derive function without a per-module name mapping. New analysis modules must
# define this alias pointing to their primary derive function.
derive = derive_metrical_domains
