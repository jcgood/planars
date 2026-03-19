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

    Walking outward from the keystone in each direction, we include each successive
    position until we reach one in blocked_positions — at which point we stop and
    exclude that position (and everything beyond it). The keystone itself is always
    included regardless of whether it is in blocked_positions.

    Args:
        all_positions: all position numbers in the data (excluding keystone).
        blocked_positions: positions that trigger a domain boundary.
        keystone_pos: position number of the keystone (v:verbstem).

    Returns:
        (left_edge, right_edge) position numbers of the span.
    """
    left = right = keystone_pos

    # Walk leftward from keystone; stop before the first blocked position.
    for pos in sorted([p for p in all_positions if p < keystone_pos], reverse=True):
        if pos in blocked_positions:
            break
        left = pos

    # Walk rightward from keystone; stop before the first blocked position.
    for pos in sorted([p for p in all_positions if p > keystone_pos]):
        if pos in blocked_positions:
            break
        right = pos

    return left, right


def fmt_span(span: Tuple[int, int], pos_to_name: Dict[int, str]) -> str:
    """Format a (left, right) span as a human-readable string with position names.

    Args:
        span: (left_edge, right_edge) position number pair.
        pos_to_name: mapping from position number to position name.

    Returns:
        A string like "positions 3–7  (det:article → v:verbstem)".
    """
    l, r = span
    return f"positions {l}\u2013{r}  ({pos_to_name.get(l, '?')} \u2192 {pos_to_name.get(r, '?')})"


def strict_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Contiguous (no gaps) expansion from keystone.

    Extends left and right from the keystone only while adjacent positions qualify.
    The first gap on either side halts expansion in that direction. The keystone
    itself is always included even if it is not in qual_positions.

    Args:
        qual_positions: position numbers that qualify for inclusion.
        keystone_pos: position number of the keystone (v:verbstem).

    Returns:
        (left_edge, right_edge) position numbers of the span.
    """
    left = right = keystone_pos
    while (left - 1) in qual_positions:
        left -= 1
    while (right + 1) in qual_positions:
        right += 1
    return left, right


def loose_span(qual_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Non-contiguous (gaps allowed) expansion from keystone.

    Extends to the farthest qualifying position on each side, regardless of
    whether intermediate positions qualify. The keystone is always included.

    Args:
        qual_positions: position numbers that qualify for inclusion.
        keystone_pos: position number of the keystone (v:verbstem).

    Returns:
        (left_edge, right_edge) position numbers of the span.
    """
    left_candidates = [p for p in qual_positions if p < keystone_pos]
    right_candidates = [p for p in qual_positions if p > keystone_pos]
    left = min(left_candidates) if left_candidates else keystone_pos
    right = max(right_candidates) if right_candidates else keystone_pos
    return left, right


def position_sets_from_element_mask(
    data_df: pd.DataFrame, element_mask: pd.Series
) -> Tuple[Set[int], Set[int]]:
    """Compute partial and complete qualifying position sets from an element-level mask.

    A position is partial if at least one of its elements satisfies the mask.
    A position is complete if all of its elements satisfy the mask.

    Args:
        data_df: DataFrame of non-keystone rows, must have a "Position_Number" column.
        element_mask: boolean Series aligned to data_df's index indicating which
            elements satisfy the qualification condition.

    Returns:
        (partial_positions, complete_positions) as sets of integer position numbers.
    """
    partial_positions: Set[int] = set(
        data_df.loc[element_mask, "Position_Number"].unique().tolist()
    )

    complete_positions: Set[int] = set()
    for pos, grp in data_df.groupby("Position_Number"):
        # A position qualifies completely only when every element in it passes the mask.
        if len(grp) > 0 and element_mask.loc[grp.index].all():
            complete_positions.add(int(pos))

    return partial_positions, complete_positions
