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


def test_conflict_matrix_matches_classify_pair():
    spans = [Span(a, b) for a, b in itertools.combinations(range(1, 7), 2)]
    matrix = rp.conflict_matrix(spans)
    for (i, s), (j, t) in itertools.product(enumerate(spans), repeat=2):
        assert matrix[i, j] == (classify_pair(s, t) == "conflict")


def test_conflict_density_by_hand():
    """1-6, 2-3, 2-4, 3-5: 3-5 crosses both 2-3 and 2-4; nothing else
    crosses."""
    spans = [Span(1, 6), Span(2, 3), Span(2, 4), Span(3, 5)]
    n_dom, n_conf = rp.conflict_grids(spans, 6)
    dens = rp.density_grid(n_dom, n_conf)
    assert (n_dom[1, 4], n_conf[1, 4]) == (3, 2) and dens[1, 4] == 2 / 3   # 2-5
    assert dens[1, 3] == 0.0                                              # 2-4: 2-3 in 2-4
    assert np.isnan(dens[1, 2])                                           # 2-3: one domain
    assert dens[0, 5] == 2 / 6                                            # whole structure
    # 2-4 -> 2-5 brings in 3-5: two new pairs, both conflicts.
    assert rp.marginal_conflict(n_dom, n_conf, (1, 3), (1, 4)) == 1.0
    # 1-5 -> 1-6 brings in 1-6, which encloses all three: three pairs, none conflict.
    assert rp.marginal_conflict(n_dom, n_conf, (0, 4), (0, 5)) == 0.0
    # 2-3 -> 2-4 brings in 2-4 beside 2-3: one pair, nested.
    assert rp.marginal_conflict(n_dom, n_conf, (1, 2), (1, 3)) == 0.0
    # A stack of grids (the null's replicates) gives one value per replicate.
    stacked = rp.marginal_conflict(np.stack([n_dom, n_dom]), np.stack([n_conf, n_conf]), (1, 3), (1, 4))
    assert list(stacked) == [1.0, 1.0]


def test_juncture_counts_by_hand():
    """1-6, 2-3, 2-4, 3-5: the conflicts are 2-3 x 3-5 and 2-4 x 3-5, both
    lying over 2-5, so each spans junctures 2|3, 3|4 and 4|5 once."""
    spans = [Span(1, 6), Span(2, 3), Span(2, 4), Span(3, 5)]
    counts, n_pairs = rp.juncture_counts(spans, 6)
    assert list(counts) == [0, 2, 2, 2, 0] and n_pairs == 2
    assert list(rp.juncture_shares(counts, n_pairs)) == [0.0, 1.0, 1.0, 1.0, 0.0]
    # A stack of replicates, one with no conflict.
    stacked = rp.juncture_shares(np.stack([counts, np.zeros(5)]), np.array([2, 0]))
    assert list(stacked[0]) == [0.0, 1.0, 1.0, 1.0, 0.0] and np.isnan(stacked[1]).all()
    # 1-4 x 3-6 lies over the whole structure.
    assert list(rp.juncture_counts([Span(1, 4), Span(3, 6)], 6)[0]) == [1, 1, 1, 1, 1]


def test_resolution_profile_runs(tmp_path):
    name = write_domains(tmp_path, [("root", 1, 6), ("x", 2, 3), ("y", 2, 4), ("z", 3, 5)])
    profile, jumps, positions, junctures, quantal = rp.run_profile(name, tmp_path, n_permutations=50,
                                                                   seed=1, n_positions=6)
    row = next(r for r in profile if (r["left"], r["right"]) == (2, 5))
    assert row["n_domains"] == 3 and row["conflict_density"] == round(2 / 3, 4)
    step = next(r for r in jumps if (r["from"], r["to"]) == ("2-4", "2-5"))
    assert step["marginal_conflict"] == 1.0 and step["added_pairs"] == 2
    assert [r["share"] for r in junctures] == [0.0, 1.0, 1.0, 1.0, 0.0]
    assert junctures[1]["position_passed"] == 2 and junctures[1]["change"] == 1.0
    assert junctures[4]["change"] == -1.0 and junctures[0]["change"] == ""
    assert quantal["n_conflicting_pairs"] == 2 and 0.0 <= quantal["p_largest_ge"] <= 1.0
    again = rp.run_profile(name, tmp_path, n_permutations=50, seed=1, n_positions=6)
    assert again == (profile, jumps, positions, junctures, quantal)
