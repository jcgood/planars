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
    assert {row["domain_type"] for row in subsets} == {
        "intonational", "length", "morphosyntactic", "phonological", "tonosegmental"
    }
    for row in subsets:
        subset_dir = BUNDLE / row["path"]
        subset_metadata = json.loads((subset_dir / "metadata.json").read_text())
        assert subset_metadata["contract_version"] == "0.2.0"
        assert subset_metadata["source_domain_sha256"] == digest
        assert subset_metadata["enumeration_truncated"] is False
        assert len(list(csv.DictReader((subset_dir / "families.tsv").open(), delimiter="\t"))) == row["n_maximal_families"]


def test_conflict_pairs_are_symmetric_as_an_undirected_relation():
    pairs = read_tsv("conflict_pairs.tsv")
    normalized = {(row["span_id_a"], row["span_id_b"]) for row in pairs}
    assert len(normalized) == 65
    assert all(a != b for a, b in normalized)
    assert all(a < b for a, b in normalized)
