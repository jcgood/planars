"""Regression checks for the committed Nyan planarsviz export contract."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
BUNDLE = ROOT / "results" / "chart_data" / "nyan1308" / "data"
RESULTS = ROOT / "results" / "chart_data" / "nyan1308"
SOURCE = ROOT / "domains" / "domains_nyan1308.tsv"


def read_tsv(name):
    with (BUNDLE / name).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_bundle_counts_and_contract():
    metadata = json.loads((BUNDLE / "metadata.json").read_text())
    assert metadata["contract_version"] == "0.2.0"
    assert metadata["enumeration_truncated"] is False
    assert len(read_tsv("tests.tsv")) == metadata["n_active_tests"] == 95
    assert len(read_tsv("spans.tsv")) == metadata["n_unique_spans"] == 26
    assert len(read_tsv("families.tsv")) == metadata["n_maximal_families"] == 69
    assert len(read_tsv("conflict_pairs.tsv")) == metadata["n_conflict_pairs"] == 65
    labels = {row["position"]: row["label"] for row in read_tsv("position_labels.tsv")}
    assert labels["10"] == "Root"
    assert labels["11"] == "Ext"


def test_bundle_records_current_source_hash_and_domain_subsets():
    metadata = json.loads((BUNDLE / "metadata.json").read_text())
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert metadata["source_domain_sha256"] == digest
    subsets = json.loads((BUNDLE / "subsets.json").read_text())
    assert {row["domain_type"] for row in subsets if row["kind"] == "domain_type"} == {
        "intonational", "length", "morphosyntactic", "phonological", "tonosegmental"
    }
    filters = {row["subset_id"]: row["domain_types"] for row in subsets if row["kind"] == "filter"}
    assert filters == {"no_tono": ["intonational", "length", "morphosyntactic", "phonological"]}
    for row in subsets:
        subset_dir = BUNDLE / row["path"]
        subset_metadata = json.loads((subset_dir / "metadata.json").read_text())
        assert subset_metadata["contract_version"] == "0.2.0"
        assert subset_metadata["source_domain_sha256"] == digest
        assert subset_metadata["enumeration_truncated"] is False
        assert len(list(csv.DictReader((subset_dir / "families.tsv").open(), delimiter="\t"))) == row["n_maximal_families"]


def test_recovered_selections():
    # docs/PLAN_planarsviz_library.md section 4.1 (0-based family numbers
    # there; family_NNN ids here are 1-based).
    def fid(number):
        return f"family_{number + 1:03d}"
    rows = read_tsv("selections.tsv")
    selections = {row["selection"]: row["family_id"] for row in rows
                  if row["selection"] not in ("exemplary", "most_binary")}
    assert selections == {"consensus_all": fid(15), "consensus_A": fid(46),
                          "consensus_B": fid(15), "consensus_C": fid(6)}
    # generate_exemplary_trees(include_sparsest=True): six by coverage, then
    # the sparsest family (67).
    exemplary = [row["family_id"] for row in sorted(
        (row for row in rows if row["selection"] == "exemplary"), key=lambda row: int(row["rank"]))]
    assert exemplary == [fid(i) for i in [15, 0, 37, 53, 46, 6, 67]]
    groups = read_tsv("conflict_groups.tsv")
    assert [sum(r["group_id"] == g for r in groups) for g in "ABC"] == [10, 23, 36]
    assert sorted(r["family_id"] for r in groups) == [fid(i) for i in range(69)]

    def drawn(group):
        ranked = [r for r in groups if r["group_id"] == group and r["draw_rank"]]
        return [r["family_id"] for r in sorted(ranked, key=lambda r: int(r["draw_rank"]))]
    assert drawn("B") == [fid(i) for i in [9, 25, 16, 18, 10, 11, 12, 13, 14, 15, 17, 19]]
    assert drawn("C") == [fid(i) for i in [0, 40, 53, 37, 1, 2, 3, 4, 5, 6, 7, 8]]
    assert len(drawn("A")) == 10


def test_most_binary_selection_is_a_maximally_resolved_family():
    # The illustration tree: the family that branches most binarily. It can
    # never have fewer spans than the most resolved family, since every extra
    # compatible span is another branching point.
    families = {row["family_id"]: int(row["n_spans"]) for row in read_tsv("families.tsv")}
    chosen = [row["family_id"] for row in read_tsv("selections.tsv")
              if row["selection"] == "most_binary"]
    assert len(chosen) == 1
    assert families[chosen[0]] == max(families.values())


def test_conflict_pairs_are_symmetric_as_an_undirected_relation():
    pairs = read_tsv("conflict_pairs.tsv")
    normalized = {(row["span_id_a"], row["span_id_b"]) for row in pairs}
    assert len(normalized) == 65
    assert all(a != b for a, b in normalized)
    assert all(a < b for a, b in normalized)


def test_fragmentation_tables_agree():
    """The null tally must account for every draw, and the two fragmentation
    tables must describe the same groups.

    Written as a test rather than left to check_fragmentation.R because this
    is the invariant that makes the tally safe to store instead of the raw
    draws: if a group's counts stop summing to its own n_permutations, the
    stored distribution is no longer the one the p-value came from, and the
    violin would be drawn from an incomplete null without anything looking
    wrong. The porting check covers the rest (numbers against the committed
    TSVs, pixels against the reference); this is the piece worth having run
    automatically.
    """
    summary = read_tsv("fragmentation_test.tsv")
    tally = read_tsv("fragmentation_null.tsv")
    assert summary and tally

    kinds = {row["group"]: row["kind"] for row in summary}
    draws = {row["group"]: int(row["n_permutations"]) for row in summary}
    assert set(kinds) == {row["group"] for row in tally}

    totals = {}
    for row in tally:
        assert row["kind"] == kinds[row["group"]]
        totals[row["group"]] = totals.get(row["group"], 0) + int(row["n"])
    assert totals == draws

    # A tally that had silently collapsed distinct counts together would still
    # sum correctly, so also check each group's rows are one per value.
    seen = set()
    for row in tally:
        key = (row["group"], row["family_count"])
        assert key not in seen, f"duplicate tally row for {key}"
        seen.add(key)


def test_span_placement_tables_agree():
    """The span-placement null tally must account for every draw, describe the
    same groups as the summary, and keep the group order the numbers depend on.

    The first two are test_fragmentation_tables_agree()'s reasoning exactly:
    a tally that stops summing to its own n_permutations is no longer the
    distribution the p-value came from, and nothing would look wrong.

    The third is particular to this test. `span_placement_test.run_test()`
    advances one shared random stream across the groups in the order it is
    given them, so the order in the table is what says which draws each group
    got. If an export ever reordered them the numbers would still be
    internally consistent and still wrong against the committed TSVs, which
    is the kind of drift a pixel check would only catch by accident.
    """
    summary = read_tsv("span_placement_test.tsv")
    tally = read_tsv("span_placement_null.tsv")
    assert summary and tally

    kinds = {row["group"]: row["kind"] for row in summary}
    draws = {row["group"]: int(row["n_permutations"]) for row in summary}
    assert set(kinds) == {row["group"] for row in tally}

    totals = {}
    for row in tally:
        assert row["kind"] == kinds[row["group"]]
        totals[row["group"]] = totals.get(row["group"], 0) + int(row["n"])
    assert totals == draws

    seen = set()
    for row in tally:
        key = (row["group"], row["family_count"])
        assert key not in seen, f"duplicate tally row for {key}"
        seen.add(key)

    # Pooled first, then classes, then bundles -- the order run_test() was
    # given, and so the order its shared random stream assumed.
    order = [row["kind"] for row in summary]
    assert order[0] == "all", f"first row is {order[0]}, not the pooled group"
    assert order == sorted(order, key=["all", "class", "bundle"].index), (
        f"groups are out of order: {order}"
    )

    # Every group re-places its spans over the FULL structure, not its own
    # observed range, so one n_positions serves them all.
    assert len({row["n_positions"] for row in summary}) == 1


def test_arbitrary_layers_tables_agree():
    """The arbitrary-layers tables must hold together the way the
    span-placement ones do, plus the two things particular to this test.

    The shared part is test_span_placement_tables_agree()'s: the tally
    accounts for every draw, the two tables describe the same groups, and the
    group order the shared random stream depends on is preserved.

    The first particular one is `includes_root`. It records whether a group's
    real spans contain the full-structure span, and the null mirrors that. If
    it ever disagreed with the data, the null would be drawing a differently
    shaped set than the observed one it is compared against, and every p-value
    would be quietly wrong rather than visibly broken.

    The second is truncation. This null crosses far more chaotically than the
    other two, so the enumeration cap is raised for it; a draw that hit even
    the raised cap is counted as the cap instead of its real value, which
    biases the whole summary downward. n_truncated must be zero.
    """
    summary = read_tsv("arbitrary_layers_test.tsv")
    tally = read_tsv("arbitrary_layers_null.tsv")
    assert summary and tally

    kinds = {row["group"]: row["kind"] for row in summary}
    draws = {row["group"]: int(row["n_permutations"]) for row in summary}
    assert set(kinds) == {row["group"] for row in tally}

    totals = {}
    for row in tally:
        assert row["kind"] == kinds[row["group"]]
        totals[row["group"]] = totals.get(row["group"], 0) + int(row["n"])
    assert totals == draws

    seen = set()
    for row in tally:
        key = (row["group"], row["family_count"])
        assert key not in seen, f"duplicate tally row for {key}"
        seen.add(key)

    order = [row["kind"] for row in summary]
    assert order[0] == "all", f"first row is {order[0]}, not the pooled group"
    assert order == sorted(order, key=["all", "class", "bundle"].index), (
        f"groups are out of order: {order}"
    )

    for row in summary:
        assert row["includes_root"] in {"y", "n"}, row
        assert int(row["n_truncated"]) == 0, (
            f"{row['group']} had {row['n_truncated']} draws hit the family cap; "
            f"its null summary is biased downward"
        )

    # The pooled group is the whole dataset, so if any group contains the
    # full-structure span it does. nyan1308's does (synthetic_root is false).
    pooled = next(row for row in summary if row["group"] == "all")
    assert pooled["includes_root"] == "y"


def test_boundary_strength_test_covers_every_position():
    """Every group must have exactly one row per (side, statistic, position),
    and the jump statistic's position-1 row (no position 0 to jump from) must
    always read 0.

    Written as a test for the same reason test_fragmentation_tables_agree()
    is: a group silently missing a position, or a jump row silently carrying
    a stale non-zero value at position 1, would make the ribbon chart draw a
    gap or a spurious point without anything else catching it.
    """
    rows = read_tsv("boundary_strength_test.tsv")
    assert rows
    n_positions = json.loads((BUNDLE / "metadata.json").read_text())["n_positions"]

    by_group_side_statistic = {}
    for row in rows:
        key = (row["group"], row["side"], row["statistic"])
        by_group_side_statistic.setdefault(key, set()).add(int(row["position"]))
    for key, positions in by_group_side_statistic.items():
        assert positions == set(range(1, n_positions + 1)), f"{key} does not cover every position"

    for row in rows:
        if row["statistic"] == "jump" and int(row["position"]) == 1:
            assert float(row["observed"]) == 0.0
