from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from planars.io import load_filled_tsv
from planars.spans import fmt_span

_REQUIRED_CRITERIA = {
    "free",
    "left-edge-of-free-form",
    "right-edge-of-free-form",
    "dependent-on-left",
    "dependent-on-right",
}


def _parse_pos_ref(val: str) -> Optional[int]:
    """Return integer position number from a dependent-on-* cell, or None if na/blank."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def derive_free_occurrence_spans(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive free occurrence spans from a filled free_occurrence TSV.

    Qualification rules designed in issue #99 (Apr 2026).

    Data model: element rows with five criterion columns.
    free: pre-filled from noninterruption/general.tsv at sheet generation time.
    All annotation columns (left-edge-of-free-form, right-edge-of-free-form,
    dependent-on-left, dependent-on-right) apply to bound elements (free=n) only;
    free elements (free=y) receive na in all annotation columns. The keystone
    always has na in all annotation columns (it is the anchor, not a dependent).

    Qualification rule (mirrors diagnostic_classes.yaml)
    -----------------------------------------------------
    A position is free-occurrence-internal if ANY of the following hold:
      1. It is to the left of the anchor (keystone) and left-edge-of-free-form=y for
         at least one element.
      2. It is to the right of the anchor and right-edge-of-free-form=y for at least
         one element.
      3. At least one of its elements has dependent-on-left or dependent-on-right
         referencing the anchor's position number.

    Maximal free occurrence span = leftmost to rightmost free-occurrence-internal
    position.

    Minimal free occurrence span:
      - If the keystone element is free (free=y): the span is the keystone position
        alone (the single-free-form utterance is just the anchor).
      - If the keystone is bound (free=n): the span is determined by the positions the
        keystone depends on (dependent-on-left, dependent-on-right), since the keystone
        requires those positions in order to be realized.

    Note: Adam Tallman (2026-04-24, issue #99) confirmed that all annotation columns
    (left-edge-of-free-form, right-edge-of-free-form, dependent-on-left,
    dependent-on-right) apply only to bound elements (free=n); free elements (free=y)
    receive na in all annotation columns.

    Args:
        tsv_path: Path to the filled free_occurrence TSV.
        strict:   If True, raise on missing free values; otherwise record in missing_data.
        _data:    Synthetic 5-tuple (data_df, keystone_pos, pos_to_name, criterion_cols,
                  keystone_df) for testing without file I/O.

    Returns dict with:
        keystone_position, position_number_to_name, element_table, missing_data,
        free_occurrence_internal_positions, minimal_span, maximal_span.
    """
    if _data is not None:
        data_df, keystone_pos, pos_to_name, _, keystone_df = _data
    else:
        data_df, keystone_pos, pos_to_name, _, keystone_df = load_filled_tsv(
            tsv_path, _REQUIRED_CRITERIA, strict=strict
        )

    # Missing data tracking.
    missing_data: Dict[str, list] = {}
    if not strict:
        for col in ["free"]:
            if col in data_df.columns:
                blanks = data_df.loc[data_df[col] == "", "Element"].tolist()
                if blanks:
                    missing_data[col] = blanks

    # ---------------------------------------------------------------------------
    # Maximal span: free-occurrence-internal positions.
    # ---------------------------------------------------------------------------
    internal_positions: Set[int] = {keystone_pos}

    for _, row in data_df.iterrows():
        pos = int(row["Position_Number"])
        if pos < keystone_pos and row.get("left-edge-of-free-form", "") == "y":
            internal_positions.add(pos)
        if pos > keystone_pos and row.get("right-edge-of-free-form", "") == "y":
            internal_positions.add(pos)
        dep_l = _parse_pos_ref(row.get("dependent-on-left", ""))
        dep_r = _parse_pos_ref(row.get("dependent-on-right", ""))
        if dep_l == keystone_pos or dep_r == keystone_pos:
            internal_positions.add(pos)

    maximal_span_result: Tuple[int, int] = (min(internal_positions), max(internal_positions))

    # ---------------------------------------------------------------------------
    # Minimal span: determined by keystone's free status and its dependencies.
    # ---------------------------------------------------------------------------
    ks_free = ""
    if keystone_df is not None and not keystone_df.empty and "free" in keystone_df.columns:
        ks_free = keystone_df["free"].iloc[0]

    if ks_free == "y":
        minimal_span_result: Tuple[int, int] = (keystone_pos, keystone_pos)
    elif ks_free == "n":
        dep_l_pos: Optional[int] = None
        dep_r_pos: Optional[int] = None
        if keystone_df is not None and not keystone_df.empty:
            if "dependent-on-left" in keystone_df.columns:
                dep_l_pos = _parse_pos_ref(keystone_df["dependent-on-left"].iloc[0])
            if "dependent-on-right" in keystone_df.columns:
                dep_r_pos = _parse_pos_ref(keystone_df["dependent-on-right"].iloc[0])
        left_edge = dep_l_pos if dep_l_pos is not None else keystone_pos
        right_edge = dep_r_pos if dep_r_pos is not None else keystone_pos
        minimal_span_result = (min(left_edge, keystone_pos), max(right_edge, keystone_pos))
    else:
        if strict:
            raise ValueError(
                f"Keystone 'free' value is blank or na; cannot compute minimal span. "
                f"Set strict=False to skip."
            )
        minimal_span_result = (keystone_pos, keystone_pos)

    return {
        "keystone_position":                keystone_pos,
        "position_number_to_name":          pos_to_name,
        "element_table":                    data_df,
        "missing_data":                     missing_data,
        "free_occurrence_internal_positions": sorted(internal_positions),
        "minimal_span":                     minimal_span_result,
        "maximal_span":                     maximal_span_result,
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
        f"Free-occurrence-internal positions: {result['free_occurrence_internal_positions']}",
        "",
        f"Minimal free occurrence span: {fmt(result['minimal_span'])}",
        f"Maximal free occurrence span: {fmt(result['maximal_span'])}",
    ]
    return "\n".join(lines)


# Standard entry point used by generate_notebooks.py.
derive = derive_free_occurrence_spans
