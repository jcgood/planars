from __future__ import annotations

from typing import Set, Tuple

import pandas as pd


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
