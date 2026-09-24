"""Checks on the committed cross-language planarsviz bundle.

The bundle is built only by reading the per-language bundles
(scripts/analysis/export_cross_language.py; contract in
planarsviz/inst/data-contract.md, "Cross-language bundle"). These tests check
that it still matches them -- every structure present once, no input bundle
changed since -- and recompute a few of its numbers straight from two source
bundles, without going through the exporter's own functions.
"""

import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CHART_DATA = ROOT / "results" / "chart_data"
BUNDLE = CHART_DATA / "cross_language" / "data"
NOT_STRUCTURES = {"illustrations", "shifted_nyan", "cross_language"}


def read_tsv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def structure_names():
    return sorted(d.name for d in CHART_DATA.iterdir()
                  if d.is_dir() and d.name not in NOT_STRUCTURES and (d / "data" / "metadata.json").exists())


def test_every_structure_present_once_and_no_input_changed():
    metadata = json.loads((BUNDLE / "metadata.json").read_text())
    assert metadata["dataset"] == "cross_language"
    names = structure_names()
    assert len(names) == 22
    assert [i["dataset"] for i in metadata["inputs"]] == names
    for entry in metadata["inputs"]:
        path = CHART_DATA / entry["dataset"] / "data" / "metadata.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["metadata_sha256"], (
            f"{entry['dataset']}'s bundle changed after the cross-language bundle was written. Re-run:\n"
            "    python scripts/analysis/export_cross_language.py --apply\n"
            "from NonCollaborative/, then redraw its charts."
        )
    for table in ("structures.tsv", "conflict_divide.tsv", "summary.tsv"):
        assert sorted(r["dataset"] for r in read_tsv(BUNDLE / table)) == names, table
    assert len(read_tsv(BUNDLE / "family_count_tests.tsv")) == len(names) * 6


@pytest.mark.parametrize("dataset, syntax_group, phonology_group", [
    ("chac1251_verbal", "morsyn_indet", "phonological"),
    ("nyan1308", "syntaxlike", "phonologylike"),
])
def test_family_count_ratios_match_source(dataset, syntax_group, phonology_group):
    rows = {(r["null"], r["role"]): r for r in read_tsv(BUNDLE / "family_count_tests.tsv") if r["dataset"] == dataset}
    for null in ("span_placement", "arbitrary_layers"):
        source = {r["group"]: r for r in read_tsv(CHART_DATA / dataset / "data" / f"{null}_test.tsv")}
        for role, group in (("all", "all"), ("syntax_side", syntax_group), ("phonology_side", phonology_group)):
            src, out = source[group], rows[(null, role)]
            assert out["observed_families"] == src["observed_families"]
            assert out["p_value_le_observed"] == src["p_value_le_observed"]
            ratio = int(src["observed_families"]) / int(src["null_p50"])
            assert float(out["observed_ratio"]) == pytest.approx(ratio, abs=1e-4)


# Which side each domain type is on, written out again here rather than
# imported, so a change to the exporter's rule has to be made twice on purpose.
SIDE = {
    "chac1251_verbal": {"morphosyntactic": "s", "indeterminate": "s", "phonological": "p"},
    "nyan1308": {"morphosyntactic": "s", "tonosegmental": "s", "length": "s",
                 "phonological": "p", "intonational": "p"},
}


@pytest.mark.parametrize("dataset", sorted(SIDE))
def test_conflict_divide_counts_match_source(dataset):
    spans = {s["span_id"]: {SIDE[dataset][t] for t in s["domain_types"].split("|")}
             for s in read_tsv(CHART_DATA / dataset / "data" / "spans.tsv") if s["synthetic"] != "True"}
    conflicts = read_tsv(CHART_DATA / dataset / "data" / "conflict_pairs.tsv")
    between = sum(not (spans[c["span_id_a"]] & spans[c["span_id_b"]]) for c in conflicts)
    pairs = list(combinations(spans, 2))
    expected = sum(not (spans[a] & spans[b]) for a, b in pairs) / len(pairs)
    row = next(r for r in read_tsv(BUNDLE / "conflict_divide.tsv") if r["dataset"] == dataset)
    assert int(row["n_conflict_pairs"]) == len(conflicts)
    assert int(row["n_between"]) == between
    assert (int(row["n_between"]) + int(row["n_within_syntax"]) + int(row["n_within_phonology"])
            + int(row["n_within_both"])) == len(conflicts)
    assert float(row["expected_share_between"]) == pytest.approx(expected, abs=1e-4)


def test_boundary_profile_is_root_relative_and_scaled():
    for dataset in ("chac1251_verbal", "nyan1308"):
        meta = json.loads((CHART_DATA / dataset / "data" / "metadata.json").read_text())
        rows = [r for r in read_tsv(BUNDLE / "boundary_profile.tsv") if r["dataset"] == dataset]
        assert len(rows) == 2 * meta["n_positions"]
        assert all(int(r["relative_position"]) == int(r["position"]) - meta["root_position"] for r in rows)
        assert max(float(r["scaled"]) for r in rows) == 1.0
