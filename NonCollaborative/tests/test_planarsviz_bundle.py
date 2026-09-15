"""Regression checks for the committed Nyan planarsviz export contract."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
BUNDLE = ROOT / "results" / "planarsviz" / "nyan1308" / "data"
RESULTS = ROOT / "results" / "planarsviz" / "nyan1308"
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
    selections = {row["selection"]: row["family_id"] for row in rows if row["selection"] != "exemplary"}
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


def test_conflict_pairs_are_symmetric_as_an_undirected_relation():
    pairs = read_tsv("conflict_pairs.tsv")
    normalized = {(row["span_id_a"], row["span_id_b"]) for row in pairs}
    assert len(normalized) == 65
    assert all(a != b for a, b in normalized)
    assert all(a < b for a, b in normalized)
