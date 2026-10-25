"""Unit tests for planars/spans.py — core span math.

All tests use synthetic position sets so no file I/O is required.
Keystone is at position 5 throughout unless otherwise noted.
"""
from __future__ import annotations

import pandas as pd

from planars.spans import (
    blocked_span,
    fmt_span,
    gained_position_counts,
    loose_span,
    position_sets_from_element_mask,
    strict_span,
)

K = 5  # default keystone position


# ---------------------------------------------------------------------------
# strict_span
# ---------------------------------------------------------------------------

class TestStrictSpan:
    def test_keystone_only_none_in_span(self):
        assert strict_span(set(), K) == (K, K)

    def test_keystone_only_non_adjacent_in_span(self):
        # In-span positions exist but have a gap next to the keystone
        assert strict_span({3, 8}, K) == (K, K)

    def test_expand_left_only(self):
        assert strict_span({3, 4}, K) == (3, K)

    def test_expand_right_only(self):
        assert strict_span({6, 7}, K) == (K, 7)

    def test_expand_both_sides(self):
        assert strict_span({3, 4, 6, 7}, K) == (3, 7)

    def test_gap_stops_expansion(self):
        # 4 is in the span but 3 isn't → left stops at 4; 6 is in but 7 isn't → right stops at 6
        assert strict_span({4, 6}, K) == (4, 6)

    def test_gap_mid_left(self):
        # 4 is in, 3 is not, 2 is in — stops at 4
        assert strict_span({2, 4}, K) == (4, K)

    def test_gap_mid_right(self):
        # 6 is in, 7 is not, 8 is in — stops at 6
        assert strict_span({6, 8}, K) == (K, 6)

    def test_full_contiguous_range(self):
        assert strict_span({1, 2, 3, 4, 6, 7, 8, 9}, K) == (1, 9)

    def test_single_left_neighbor(self):
        assert strict_span({4}, K) == (4, K)

    def test_single_right_neighbor(self):
        assert strict_span({6}, K) == (K, 6)

    def test_keystone_at_left_edge(self):
        k = 1
        assert strict_span({2, 3}, k) == (k, 3)

    def test_keystone_at_right_edge(self):
        k = 9
        assert strict_span({7, 8}, k) == (7, k)


# ---------------------------------------------------------------------------
# loose_span
# ---------------------------------------------------------------------------

class TestLooseSpan:
    def test_keystone_only_none_in_span(self):
        assert loose_span(set(), K) == (K, K)

    def test_expand_right_only(self):
        assert loose_span({6, 8}, K) == (K, 8)

    def test_expand_both_sides(self):
        assert loose_span({2, 4, 6, 8}, K) == (2, 8)

    def test_gap_does_not_stop_expansion(self):
        # Unlike strict_span, a gap should not halt loose_span.
        # Position 3 is absent (gap), but 2 is in the span → left edge is 2.
        assert loose_span({2, 4}, K) == (2, K)

    def test_gap_both_sides(self):
        assert loose_span({1, 4, 6, 9}, K) == (1, 9)

    def test_single_in_span_far_left(self):
        assert loose_span({1}, K) == (1, K)

    def test_single_in_span_far_right(self):
        assert loose_span({9}, K) == (K, 9)

    def test_loose_ge_strict_left(self):
        # Loose span left edge ≤ strict span left edge (loose goes at least as far)
        qual = {2, 4, 6}
        ls = loose_span(qual, K)
        ss = strict_span(qual, K)
        assert ls[0] <= ss[0]

    def test_loose_ge_strict_right(self):
        qual = {2, 4, 6}
        ls = loose_span(qual, K)
        ss = strict_span(qual, K)
        assert ls[1] >= ss[1]

    def test_keystone_at_left_edge(self):
        k = 1
        assert loose_span({3, 5, 7}, k) == (k, 7)

    def test_keystone_at_right_edge(self):
        k = 9
        assert loose_span({1, 3, 5}, k) == (1, k)


# ---------------------------------------------------------------------------
# blocked_span
# ---------------------------------------------------------------------------

class TestBlockedSpan:
    # all_positions excludes keystone (mirrors how callers build it from data_df)
    _ALL = {1, 2, 3, 4, 6, 7, 8, 9}

    def test_no_blocked_positions_spans_all(self):
        assert blocked_span(self._ALL, set(), K) == (1, 9)

    def test_keystone_only_when_all_blocked(self):
        assert blocked_span(self._ALL, self._ALL, K) == (K, K)

    def test_blocked_immediately_left(self):
        # Position 4 is blocked → left edge stays at keystone
        assert blocked_span(self._ALL, {4}, K) == (K, 9)

    def test_blocked_immediately_right(self):
        # Position 6 is blocked → right edge stays at keystone
        assert blocked_span(self._ALL, {6}, K) == (1, K)

    def test_blocked_further_left(self):
        # Position 2 is blocked → span extends left only to 3
        assert blocked_span(self._ALL, {2}, K) == (3, 9)

    def test_blocked_further_right(self):
        # Position 8 is blocked → span extends right only to 7
        assert blocked_span(self._ALL, {8}, K) == (1, 7)

    def test_blocked_both_sides(self):
        assert blocked_span(self._ALL, {3, 7}, K) == (4, 6)

    def test_keystone_in_blocked_still_included(self):
        # The keystone must always be in the span, even if it is in blocked_positions.
        result = blocked_span(self._ALL, {K}, K)
        assert result[0] <= K <= result[1]

    def test_empty_all_positions(self):
        # No non-keystone positions → span is just the keystone
        assert blocked_span(set(), set(), K) == (K, K)

    def test_single_position_left_unblocked(self):
        assert blocked_span({4}, set(), K) == (4, K)

    def test_single_position_left_blocked(self):
        assert blocked_span({4}, {4}, K) == (K, K)

    def test_single_position_right_unblocked(self):
        assert blocked_span({6}, set(), K) == (K, 6)

    def test_single_position_right_blocked(self):
        assert blocked_span({6}, {6}, K) == (K, K)

    def test_blocked_does_not_stop_other_side(self):
        # Blocking on the right should not affect the left expansion.
        result = blocked_span(self._ALL, {6}, K)
        assert result[0] == 1  # left fully expanded
        assert result[1] == K  # right stopped at keystone


# ---------------------------------------------------------------------------
# position_sets_from_element_mask
# ---------------------------------------------------------------------------

def _make_df(pos_elements: dict[int, list[str]]) -> pd.DataFrame:
    """Build a synthetic data_df from {position_number: [elem1, elem2, ...]}."""
    rows = [
        {"Position_Number": pos, "Element": elem}
        for pos, elems in pos_elements.items()
        for elem in elems
    ]
    return pd.DataFrame(rows)


class TestPositionSetsFromElementMask:
    def test_all_in_span(self):
        df = _make_df({3: ["a", "b"], 4: ["c"], 6: ["d", "e"]})
        mask = pd.Series([True] * len(df), index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert partial == {3, 4, 6}
        assert complete == {3, 4, 6}

    def test_none_in_span(self):
        df = _make_df({3: ["a", "b"], 4: ["c"]})
        mask = pd.Series([False] * len(df), index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert partial == set()
        assert complete == set()

    def test_partial_but_not_complete(self):
        # Position 3 has elements a (counts toward the span) and b (does not)
        df = _make_df({3: ["a", "b"]})
        mask = pd.Series([True, False], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert 3 in partial
        assert 3 not in complete

    def test_single_element_position_in_span_both(self):
        df = _make_df({6: ["a"]})
        mask = pd.Series([True], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert 6 in partial
        assert 6 in complete

    def test_single_element_position_not_in_span(self):
        df = _make_df({6: ["a"]})
        mask = pd.Series([False], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert 6 not in partial
        assert 6 not in complete

    def test_complete_subset_of_partial(self):
        # complete positions must always be a subset of partial positions
        df = _make_df({3: ["a", "b"], 4: ["c", "d"], 6: ["e"]})
        # Position 3: a counts, b doesn't → partial only
        # Position 4: both count → complete
        # Position 6: counts → complete
        mask = pd.Series([True, False, True, True, True], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert complete.issubset(partial)

    def test_mixed_multi_element_positions(self):
        df = _make_df({3: ["a", "b", "c"], 4: ["d", "e"]})
        # Position 3: only a counts → partial
        # Position 4: both count → complete
        mask = pd.Series([True, False, False, True, True], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert partial == {3, 4}
        assert complete == {4}

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["Position_Number", "Element"])
        mask = pd.Series([], dtype=bool)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        assert partial == set()
        assert complete == set()

    def test_returns_integer_position_numbers(self):
        df = _make_df({3: ["a"], 6: ["b"]})
        mask = pd.Series([True, True], index=df.index)
        partial, complete, _counts = position_sets_from_element_mask(df, mask)
        for pos in partial | complete:
            assert isinstance(pos, int)

    def test_counts_are_k_of_n_per_position(self):
        df = _make_df({3: ["a", "b", "c"], 4: ["d", "e"], 6: ["f"]})
        mask = pd.Series([True, False, False, True, True, False], index=df.index)
        _partial, _complete, counts = position_sets_from_element_mask(df, mask)
        assert counts == {3: (1, 3), 4: (2, 2), 6: (0, 1)}
        assert all(isinstance(p, int) for p in counts)


# ---------------------------------------------------------------------------
# gained_position_counts
# ---------------------------------------------------------------------------

class TestGainedPositionCounts:
    COUNTS = {2: (0, 2), 3: (1, 4), 4: (2, 2), 6: (3, 3), 7: (1, 2)}

    def test_positions_outside_counterpart_in_order(self):
        assert gained_position_counts((2, 7), (4, 6), self.COUNTS) == [
            (2, 0, 2), (3, 1, 4), (7, 1, 2)]

    def test_same_span_gains_nothing(self):
        assert gained_position_counts((4, 6), (4, 6), self.COUNTS) == []

    def test_position_without_elements_left_out(self):
        # Position 5 (the keystone here) has no count and is inside both anyway;
        # position 1 has no elements in the data.
        assert gained_position_counts((1, 5), (4, 5), self.COUNTS) == [
            (2, 0, 2), (3, 1, 4)]


# ---------------------------------------------------------------------------
# fmt_span
# ---------------------------------------------------------------------------

class TestFmtSpan:
    _POS_TO_NAME = {1: "v:leftedge", 5: "v:verbstem", 9: "v:rightedge"}

    def test_basic_format(self):
        result = fmt_span((1, 9), self._POS_TO_NAME)
        assert "1" in result
        assert "9" in result
        assert "v:leftedge" in result
        assert "v:rightedge" in result

    def test_keystone_only(self):
        result = fmt_span((5, 5), self._POS_TO_NAME)
        assert "5" in result
        assert "v:verbstem" in result

    def test_unknown_position_uses_question_mark(self):
        result = fmt_span((2, 7), self._POS_TO_NAME)
        assert "?" in result

    def test_returns_string(self):
        assert isinstance(fmt_span((1, 9), self._POS_TO_NAME), str)
