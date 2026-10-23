from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from planars.io import load_filled_tsv
from planars.position_cells import position_numbers
from planars.spans import fmt_span

from planars.schema_values import required_criteria

_REQUIRED_CRITERIA = required_criteria("free_occurrence")


def dependency_positions(cell, where: str = "") -> List[int]:
    """The positions a dependent-on-left/right cell lists (``8|12|30``: any
    one is enough); none for na, ``?`` or blank. Raises on a cell that is
    not positions, naming ``where`` -- validate-coding reports such cells to
    the annotator, so one reaching here is never read as "no dependency"."""
    numbers, problems = position_numbers(cell)
    if problems:
        raise ValueError(f"{where or 'dependent-on cell'} {str(cell)!r}: {problems[0]}")
    return numbers


def bound_keystone_span(dep_left_cell, dep_right_cell, keystone_pos: int) -> Tuple[int, int]:
    """Minimal span of a bound keystone (free=n): from the nearest position
    it depends on to its left to the nearest one to its right (the smallest
    frame in which it can surface, #318), or the keystone itself on a side
    with none. Also tier 1 of phrasal_accent's obligatory core
    (coding/generate_sheets.py)."""
    left = dependency_positions(dep_left_cell, "keystone dependent-on-left")
    right = dependency_positions(dep_right_cell, "keystone dependent-on-right")
    left_edge = max(left) if left else keystone_pos
    right_edge = min(right) if right else keystone_pos
    return (min(left_edge, keystone_pos), max(right_edge, keystone_pos))


def derive_free_occurrence_spans(
    tsv_path: Optional[Path] = None,
    strict: bool = True,
    *,
    _data: Optional[Tuple] = None,
) -> Dict[str, object]:
    """Derive free occurrence spans from a filled free_occurrence TSV.

    Span rules designed in issue #99 (Apr 2026).

    Data model: element rows with five criterion columns.
    free: pre-filled from noninterruption/general.tsv at sheet generation time.
    All annotation columns (left-edge-of-free-form, right-edge-of-free-form,
    dependent-on-left, dependent-on-right) apply to bound elements (free=n) only;
    free elements (free=y) receive na in all annotation columns. The keystone
    always has na in all annotation columns (it is the anchor, not a dependent).

    Span rule (mirrors diagnostic_classes.yaml)
    -------------------------------------------
    A position is free-occurrence-internal if ANY of the following hold:
      1. It is to the left of the anchor (keystone) and left-edge-of-free-form=y for
         at least one element.
      2. It is to the right of the anchor and right-edge-of-free-form=y for at least
         one element.
      3. At least one of its elements lists the anchor's position number among
         its dependent-on-left or dependent-on-right positions.

    dependent-on-left/right list one or more position numbers separated by |
    (e.g. 8|12|30), meaning any one of them is enough for the element to
    surface (#318).

    Maximal free occurrence span = leftmost to rightmost free-occurrence-internal
    position.

    Minimal free occurrence span:
      - If the keystone element is free (free=y): the span is the keystone position
        alone (the single-free-form utterance is just the anchor).
      - If the keystone is bound (free=n): the span runs from the nearest position
        listed in its dependent-on-left to the nearest listed in its
        dependent-on-right (the smallest frame in which it can surface), or from
        the keystone itself on a side with none listed.

    Note: Adam Tallman (2026-04-24, issue #99) confirmed that all annotation columns
    (left-edge-of-free-form, right-edge-of-free-form, dependent-on-left,
    dependent-on-right) apply only to bound elements (free=n); free elements (free=y)
    receive na in all annotation columns.

    A dependent-on cell that is not positions (e.g. 3,4) raises with strict;
    otherwise it is treated as unannotated and listed in missing_data.

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
        listed: List[int] = []
        for col in ("dependent-on-left", "dependent-on-right"):
            try:
                listed += dependency_positions(row.get(col, ""),
                                               f"{row.get('Element', '?')} {col}")
            except ValueError:
                if strict:
                    raise
                # Unreadable (validate-coding reports it): treated as unannotated.
                missing_data.setdefault(col, []).append(row.get("Element", "?"))
        if keystone_pos in listed:
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
        ks = keystone_df.iloc[0]
        try:
            minimal_span_result = bound_keystone_span(
                ks.get("dependent-on-left", ""), ks.get("dependent-on-right", ""), keystone_pos)
        except ValueError:
            if strict:
                raise
            missing_data.setdefault("keystone dependent-on", []).append(ks.get("Element", "?"))
            minimal_span_result = (keystone_pos, keystone_pos)
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
        lines.append("NOTE: Some cells are unannotated — spans computed treating blanks as outside the span.")
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
