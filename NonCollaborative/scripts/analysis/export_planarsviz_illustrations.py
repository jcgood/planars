"""Export the `illustrations` data bundle for the `planarsviz` R package.

Unlike every other bundle this project exports, `illustrations` has no
language behind it -- it is pure tree-shape combinatorics, kept in its own
bundle for exactly that reason (question 1,
docs/PLANARSVIZ_LIBRARY_PROGRESS.md): the library's rule is "Python computes,
R draws from a data folder," and these have data, just no language.

Three tables, reusing the already-verified counting/enumeration code in
scripts/exploratory/catalan.py rather than re-deriving any of it:

- `tree_shapes.tsv`: every distinct rooted ordered n-ary tree shape (each
  internal node >=2 children) for n=2..4 leaves (exhaustive: 1, 3, 11 shapes),
  plus the first 15 (of 45) for n=5, in `enumerate_trees()`'s own order.
  Replaces the JSON file scripts/exploratory/generate_supercatalan_rows.py
  used to hand to its R side.
- `tree_count_growth.tsv`: Catalan numbers (binary trees) and little Schröder
  numbers / OEIS A001003 (n-ary trees), both reindexed by leaf count so they
  share one x axis, for n=1..--tree-counts-max-n. Both formulas verified
  against results/nyan1308/counts-and-chance/tree_counting_equations.tex
  before catalan.py's catalan_number() existed to compute them. Named
  differently from the per-language bundle's own tree_counts.tsv (laminar
  family counts by class) on purpose -- same word, unrelated schema, and this
  project's bundles never reuse a filename for two different contracts.
- `random_trees.tsv`: --n-random-trees uniformly-random n-ary tree shapes
  over --n-leaves leaves, via catalan.py's exactly-uniform sampler (a
  counting recurrence turned into weighted choices, not rejection sampling
  or anything approximate; moved there from the now-archived
  scripts/analysis/random_tree_overlay.py, whose own job -- writing a
  generated .r file -- this bundle replaces). --seed makes the sample
  reproducible -- the one thing that script never had: it wrote 200
  already-sampled trees straight into a generated .r file with no seed
  recorded anywhere, so the sample it drew could never be reproduced or
  checked. Recorded in metadata.json's `random_trees.seed`.

Usage:
    python scripts/analysis/export_planarsviz_illustrations.py
    python scripts/analysis/export_planarsviz_illustrations.py --seed 7 --n-random-trees 300
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(REPO_DIR / "scripts" / "exploratory"))

from catalan import (  # noqa: E402
    all_trees_new,
    catalan_number,
    enumerate_trees,
    sample_labeled_tree,
    to_newick as random_to_newick,
)

# (row name, n leaves, sample size or None for exhaustive) -- matches
# generate_supercatalan_rows.py's ROWS exactly, since this replaces it.
TREE_SHAPE_ROWS = [(2, None), (3, None), (4, None), (5, 15)]

CONTRACT_VERSION = 1


def _shape_to_newick(tree):
    """Newick for a bare tree_shapes.tsv tree: no branch lengths, leaves are
    just their 1-based position among that tree's own leaves (not real
    positions -- these trees illustrate shape, not any language)."""
    if isinstance(tree, int):
        return str(tree)
    return "(" + ",".join(_shape_to_newick(c) for c in tree) + ")"


def _tree_height(tree):
    if isinstance(tree, int):
        return 0
    return 1 + max(_tree_height(c) for c in tree)


def build_tree_shapes():
    rows = []
    for n, sample in TREE_SHAPE_ROWS:
        trees = enumerate_trees(n)
        total = len(trees)
        if sample is not None:
            trees = trees[:sample]
        for shape_number, tree in enumerate(trees, 1):
            rows.append({
                "n": n,
                "shape_number": shape_number,
                "n_shapes_total": total,
                "newick": _shape_to_newick(tree) + ";",
                "height": _tree_height(tree),
            })
    return rows


def build_tree_counts(max_n):
    return [
        {"n": n, "catalan": catalan_number(n), "little_schroder": all_trees_new(n)}
        for n in range(1, max_n + 1)
    ]


def build_random_trees(n_trees, n_leaves, seed):
    rng = random.Random(seed)
    rows = []
    for i in range(1, n_trees + 1):
        tree = sample_labeled_tree(n_leaves, rng)
        rows.append({"tree_number": i, "newick": random_to_newick(tree) + ";"})
    return rows


def write_tsv(rows, path):
    import csv
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "chart_data")
    parser.add_argument(
        "--tree-counts-max-n", type=int, default=15,
        help="Largest leaf count in tree_count_growth.tsv (default: 15 -- both sequences "
             "have long passed 69, nyan1308's family count, well before this).",
    )
    parser.add_argument("--n-random-trees", type=int, default=200)
    parser.add_argument(
        "--n-leaves", type=int, default=22,
        help="Leaf count for the random sample (default: 22, matching nyan1308's "
             "position count -- the overlay chart draws these against nyan1308's "
             "real position labels).",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Random seed for random_trees.tsv (default: 0, so a plain run is "
             "always reproducible; the script this replaces had no seed at all).",
    )
    args = parser.parse_args()

    data_dir = args.output_dir / "illustrations" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    tree_shapes = build_tree_shapes()
    write_tsv(tree_shapes, data_dir / "tree_shapes.tsv")
    print(f"wrote {data_dir / 'tree_shapes.tsv'} ({len(tree_shapes)} shapes)")

    tree_counts = build_tree_counts(args.tree_counts_max_n)
    write_tsv(tree_counts, data_dir / "tree_count_growth.tsv")
    print(f"wrote {data_dir / 'tree_count_growth.tsv'} (n=1..{args.tree_counts_max_n})")

    random_trees = build_random_trees(args.n_random_trees, args.n_leaves, args.seed)
    write_tsv(random_trees, data_dir / "random_trees.tsv")
    print(f"wrote {data_dir / 'random_trees.tsv'} ({len(random_trees)} trees, seed={args.seed})")

    metadata = {
        "contract_version": CONTRACT_VERSION,
        "dataset": "illustrations",
        "tree_shapes": {
            "rows": [
                {"n": n, "exhaustive": sample is None, "sample_size": sample}
                for n, sample in TREE_SHAPE_ROWS
            ],
        },
        "tree_count_growth": {"n_min": 1, "n_max": args.tree_counts_max_n},
        "random_trees": {
            "n_trees": args.n_random_trees,
            "n_leaves": args.n_leaves,
            "seed": args.seed,
        },
    }
    metadata_path = data_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"wrote {metadata_path}")


if __name__ == "__main__":
    main()
