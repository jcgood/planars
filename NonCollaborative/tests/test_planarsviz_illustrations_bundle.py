"""Regression checks for the committed illustrations planarsviz export.

Unlike test_planarsviz_bundle.py's nyan1308 bundle, this one has no language
behind it (phase E, docs/PLANARSVIZ_LIBRARY_PROGRESS.md, 2026-09-22) -- see
planarsviz/inst/data-contract.md's "Illustrations bundle" section for the
contract these assertions are checking.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
BUNDLE = ROOT / "results" / "chart_data" / "illustrations" / "data"


def read_tsv(name):
    with (BUNDLE / name).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_metadata_matches_dataset_name_and_row_counts():
    metadata = json.loads((BUNDLE / "metadata.json").read_text())
    assert metadata["dataset"] == "illustrations"

    shapes = read_tsv("tree_shapes.tsv")
    expected_rows = {row["n"]: (row["exhaustive"], row["sample_size"]) for row in metadata["tree_shapes"]["rows"]}
    assert set(int(n) for n in expected_rows) == {2, 3, 4, 5}
    for n, (exhaustive, sample_size) in expected_rows.items():
        rows_for_n = [r for r in shapes if r["n"] == str(n)]
        expected_count = int(rows_for_n[0]["n_shapes_total"]) if exhaustive else sample_size
        assert len(rows_for_n) == expected_count, f"n={n}"
    # Exhaustive counts are the little Schröder numbers themselves.
    total_by_n = {int(r["n"]): int(r["n_shapes_total"]) for r in shapes}
    assert total_by_n == {2: 1, 3: 3, 4: 11, 5: 45}

    counts = read_tsv("tree_count_growth.tsv")
    assert len(counts) == metadata["tree_count_growth"]["n_max"]
    assert {int(r["n"]) for r in counts} == set(range(1, metadata["tree_count_growth"]["n_max"] + 1))
    # A few known values (also typeset in tree_counting_equations.tex).
    by_n = {int(r["n"]): r for r in counts}
    assert (by_n[1]["catalan"], by_n[1]["little_schroder"]) == ("1", "1")
    assert (by_n[4]["catalan"], by_n[4]["little_schroder"]) == ("5", "11")
    assert (by_n[7]["catalan"], by_n[7]["little_schroder"]) == ("132", "903")

    trees = read_tsv("random_trees.tsv")
    assert len(trees) == metadata["random_trees"]["n_trees"]
    assert {int(r["tree_number"]) for r in trees} == set(range(1, metadata["random_trees"]["n_trees"] + 1))
    # The recorded seed is what makes this bundle reproducible -- the property
    # its generated-R-script predecessor never had. Not re-deriving the sample
    # here (verify_random_trees_export.py does, against catalan.py directly);
    # this just pins the seed and leaf count so a change to either is visible
    # as a diff on this test rather than a silent default drift.
    assert metadata["random_trees"]["seed"] == 0
    assert metadata["random_trees"]["n_leaves"] == 22
