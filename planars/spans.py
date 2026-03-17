from __future__ import annotations

from typing import Dict, Set, Tuple

import pandas as pd


def blocked_span(
    all_positions: Set[int],
    blocked_positions: Set[int],
    keystone_pos: int,
) -> Tuple[int, int]:
    """Expand from keystone through all positions, stopping just before any blocked position.

    The blocked position is excluded from the span. Used for stress domains where
    the edge is defined by the first position containing a boundary-triggering element,
    rather than by positions that qualify.
    """
    left = right = keystone_pos

    for pos in sorted([p for p in all_positions if p < keystone_pos], reverse=True):
        if pos in blocked_positions:
            break
        left = pos

    for pos in sorted([p for p in all_positions if p > keystone_pos]):
        if pos in blocked_positions:
            break
        right = pos

    return left, right


def fmt_span(span: Tuple[int, int], pos_to_name: Dict[int, str]) -> str:
    l, r = span
    return f"positions {l}\u2013{r}  ({pos_to_name.get(l, '?')} \u2192 {pos_to_name.get(r, '?')})"


def strict_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Contiguous (no gaps) expansion from keystone."""
    left = right = keystone_pos
    while (left - 1) in qual_positions:
        left -= 1
    while (right + 1) in qual_positions:
        right += 1
    return left, right


def loose_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Non-contiguous (gaps allowed) expansion from keystone."""
    left_candidates = [p for p in qual_positions if p < keystone_pos]
    right_candidates = [p for p in qual_positions if p > keystone_pos]
    left = min(left_candidates) if left_candidates else keystone_pos
    right = max(right_candidates) if right_candidates else keystone_pos
    return left, right


def position_sets_from_element_mask(
    data_df: pd.DataFrame, element_mask: pd.Series
) -> Tuple[Set[int], Set[int]]:
    """Compute partial and complete qualifying position sets from an element-level mask."""
    partial_positions: Set[int] = set(
        data_df.loc[element_mask, "Position_Number"].unique().tolist()
    )

    complete_positions: Set[int] = set()
    for pos, grp in data_df.groupby("Position_Number"):
        if len(grp) > 0 and element_mask.loc[grp.index].all():
            complete_positions.add(int(pos))

    return partial_positions, complete_positions
