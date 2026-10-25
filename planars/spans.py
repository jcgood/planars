"""Span arithmetic shared by every analysis module.

``strict_span`` (contiguous from the keystone, no gaps), ``loose_span`` (to
the farthest in-span position on each side), ``blocked_span`` (up to the
first blocking position), ``position_sets_from_element_mask`` (partial and
complete positions from a per-element yes/no, with each position's *k of n*),
``gained_position_counts`` (the positions a partial span gains over its
complete counterpart, with their k of n) and ``fmt_span`` (a span as text).
The terms themselves are defined in ``schemas/terms.yaml``.
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple

import pandas as pd


def blocked_span(
    all_positions: Set[int],
    blocked_positions: Set[int],
    keystone_pos: int,
) -> Tuple[int, int]:
    """Expand from keystone through all positions, stopping just before any blocked position.

    The blocked position is excluded from the span. Used for stress domains where
    the edge is defined by the first position containing a boundary-triggering element,
    rather than by positions that count toward the span.

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


def strict_span(span_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Contiguous (no gaps) expansion from keystone.

    Extends left and right from the keystone only while adjacent positions are in
    span_positions. The first gap on either side halts expansion in that direction.
    The keystone itself is always included even if it is not in span_positions.

    Args:
        span_positions: position numbers that count toward the span.
        keystone_pos: position number of the keystone (v:verbstem).

    Returns:
        (left_edge, right_edge) position numbers of the span.
    """
    left = right = keystone_pos
    while (left - 1) in span_positions:
        left -= 1
    while (right + 1) in span_positions:
        right += 1
    return left, right


def loose_span(span_positions: Set[int], keystone_pos: int) -> Tuple[int, int]:
    """Non-contiguous (gaps allowed) expansion from keystone.

    Extends to the farthest in-span position on each side, regardless of
    whether intermediate positions are in span_positions. The keystone is always
    included.

    Args:
        span_positions: position numbers that count toward the span.
        keystone_pos: position number of the keystone (v:verbstem).

    Returns:
        (left_edge, right_edge) position numbers of the span.
    """
    left_candidates = [p for p in span_positions if p < keystone_pos]
    right_candidates = [p for p in span_positions if p > keystone_pos]
    left = min(left_candidates) if left_candidates else keystone_pos
    right = max(right_candidates) if right_candidates else keystone_pos
    return left, right


def position_sets_from_element_mask(
    data_df: pd.DataFrame, element_mask: pd.Series
) -> Tuple[Set[int], Set[int], Dict[int, Tuple[int, int]]]:
    """Compute the partial and complete position sets from an element-level mask.

    A position is partial if at least one of its elements satisfies the mask.
    A position is complete if all of its elements satisfy the mask.

    Args:
        data_df: DataFrame of non-keystone rows, must have a "Position_Number" column.
        element_mask: boolean Series aligned to data_df's index indicating which
            elements satisfy the span condition.

    Returns:
        (partial_positions, complete_positions, counts): the two sets of
        integer position numbers, and for every position with elements its
        *k of n* as ``{position: (k, n)}`` -- how many of its n elements
        satisfy the mask. A partial span's weight is read from these counts
        (``gained_position_counts``).
    """
    counts: Dict[int, Tuple[int, int]] = {
        int(pos): (int(element_mask.loc[grp.index].sum()), len(grp))
        for pos, grp in data_df.groupby("Position_Number")
    }
    partial_positions: Set[int] = {pos for pos, (k, _n) in counts.items() if k > 0}
    # A position is complete only when every element in it passes the mask.
    complete_positions: Set[int] = {pos for pos, (k, n) in counts.items() if n > 0 and k == n}
    return partial_positions, complete_positions, counts


def gained_position_counts(
    span: Tuple[int, int],
    counterpart: Tuple[int, int],
    counts: Dict[int, Tuple[int, int]],
) -> List[Tuple[int, int, int]]:
    """The positions `span` covers beyond `counterpart`, each with its k of n.

    `span` is a span that lets in positions where only some elements satisfy
    the span rule (a partial span); `counterpart` is the same span built from
    positions where every element does (its complete span). Each position
    inside `span` but outside `counterpart` is returned as
    ``(position, k, n)`` from `counts` (``position_sets_from_element_mask``'s
    third value), in position order; a loose span's gap is gained with k = 0.
    A position with no elements in the data has no count and is left out.
    The keystone is never gained: both spans always contain it.
    """
    left, right = span
    c_left, c_right = counterpart
    gained = [p for p in range(left, right + 1) if not c_left <= p <= c_right]
    return [(p, *counts[p]) for p in gained if p in counts]
