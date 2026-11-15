"""laminar.domain_support, laminar.resolution_test and
laminar.resolution_profile on small made-up
structures whose answers can be worked out by hand."""
from __future__ import annotations

import itertools

import numpy as np

from laminar import domain_support as ds
from laminar import resolution_profile as rp
from laminar import resolution_test as rt
from laminar.laminar_analysis import Span, classify_pair

HEADER = "Test_Labels\tDomain_Type\tLeft_Edge\tRight_Edge\tSize\n"


def write_domains(tmp_path, rows):
    """rows: (label, left, right); every test morphosyntactic."""
    lines = [f"{label}\tmorphosyntactic\t{left}\t{right}\t{right - left + 1}\n" for label, left, right in rows]
    (tmp_path / "domains_synth.tsv").write_text(HEADER + "".join(lines), encoding="utf-8")
    return "domains_synth.tsv"


def test_crossing_matches_classify_pair():
    """The vectorised crossing test agrees with classify_pair on every pair
    of spans over six positions."""
    spans = [Span(a, b) for a, b in itertools.combinations_with_replacement(range(1, 7), 2) if a < b]
    left = np.array([s.left for s in spans])
    right = np.array([s.right for s in spans])
    for span in spans:
        expected = [classify_pair(s, span) == "conflict" for s in spans]
        assert list(ds.crosses(left, right, span)) == expected


def test_holm():
    assert ds.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def test_domain_support_by_hand(tmp_path):
    """Six positions: the whole structure, 2-4 twice, 3-5 once. 2-4 and 3-5
    cross, so there are two trees, each holding one of them."""
    name = write_domains(tmp_path, [("root", 1, 6), ("a1", 2, 4), ("a2", 2, 4), ("b", 3, 5)])
    rows = {r["span_id"]: r for r in ds.run_support(name, tmp_path, n_permutations=200,
                                                       n_bootstrap=50, seed=1, n_positions=6)}
    assert (rows["2-4"]["tests_for"], rows["2-4"]["tests_against"]) == (2, 1)
    assert (rows["3-5"]["tests_for"], rows["3-5"]["tests_against"]) == (1, 2)
    assert rows["2-4"]["concordance"] == round(2 / 3, 4)
    assert rows["2-4"]["crossing_spans"] == "3-5"
    assert rows["2-4"]["family_share"] == rows["3-5"]["family_share"] == 0.5
    # Nothing can cross the whole structure: untestable, not evidence.
    assert rows["1-6"]["null_max_against"] == 0 and rows["1-6"]["p_le_observed"] == 1.0
    for row in rows.values():
        for key in ("boot_present", "boot_majority", "boot_share_mean", "boot_share_lo", "boot_share_hi"):
            assert 0.0 <= row[key] <= 1.0
        assert row["boot_share_lo"] <= row["boot_share_mean"] <= row["boot_share_hi"]
    again = {r["span_id"]: r for r in ds.run_support(name, tmp_path, n_permutations=200,
                                                        n_bootstrap=50, seed=1, n_positions=6)}
    assert again == rows


def test_tree_resolution_by_hand():
    """Six positions, region 2-5 (4 positions, at most 3 domains inside;
    outside, 3 units, at most 2 domains)."""
    family = [Span(1, 6), Span(2, 5), Span(3, 4)]
    tree = rt.tree_resolution(family, (2, 5), 6)
    assert (tree["inside"], tree["outside"], tree["crossing"]) == (2, 1, 0)
    assert tree["resolution_in"] == 2 / 3 and tree["resolution_out"] == 1 / 2
    assert tree["resolution_tree"] == 3 / 5
    crossed = rt.tree_resolution([Span(1, 6), Span(1, 3)], (2, 5), 6)
    assert (crossed["inside"], crossed["outside"], crossed["crossing"]) == (0, 1, 1)


def test_resolution_test_runs(tmp_path):
    name = write_domains(tmp_path, [("root", 1, 6), ("w", 2, 5), ("x", 2, 3), ("y", 4, 5)])
    summary, trees, tally = rt.run_test(name, tmp_path, (2, 5), n_permutations=100, seed=1, n_positions=6)
    assert summary["n_trees"] == len(trees) == 1
    assert summary["resolution_in"] == 1.0          # 2-5, 2-3, 4-5: 3 of 3
    assert summary["resolution_out"] == 0.5         # 1-6: 1 of 2
    assert sum(tally.values()) == 100
    assert 0.0 <= summary["p_le_observed"] <= 1.0


def test_resolution_profile_grids_by_hand():
    """Two trees over six positions; every stretch's inside count, crossing
    count and presence, averaged over the trees."""
    trees = [[Span(1, 6), Span(2, 5), Span(2, 3)], [Span(1, 6), Span(3, 5)]]
    inside, crossing, present = rp.family_grids(trees, 6)
    assert inside[0, 5] == 1.5          # 1-6 holds 2-5 and 2-3 / 3-5
    assert inside[1, 4] == 1.0          # 2-5 holds 2-3 in tree 1 and 3-5 in tree 2
    assert crossing[0, 2] == 1.0        # 1-3 is crossed by 2-5 in tree 1 (2-3 nests), by 3-5 in tree 2
    assert present[1, 4] == 0.5 and present[0, 5] == 1.0
    res = rp.resolution_grid(inside, 6)
    assert res[0, 5] == 1.5 / 4 and np.isnan(res[1, 2])
