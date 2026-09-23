"""Check the illustrations bundle's tree shapes and counts against catalan.py.

For the illustrations bundle (docs/PLANARSVIZ_LIBRARY_PROGRESS.md, phase E):
data/tree_shapes.tsv should have exactly the shapes
scripts/exploratory/catalan.py's enumerate_trees() produces, in the same
order, for n=2..4 (exhaustive) and the first 15 of n=5's 45. And
data/tree_count_growth.tsv's two count columns should equal catalan_number()
and all_trees_new() computed directly, for every n in the bundle.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_tree_shapes_export.py
"""

import csv
import sys
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(NC / "scripts" / "exploratory"))

from catalan import all_trees_new, catalan_number, enumerate_trees  # noqa: E402

DATA = NC / "results" / "planarsviz" / "illustrations" / "data"
ok = True


def fail(msg):
    global ok
    ok = False
    print("  MISMATCH:", msg)


def to_newick(tree):
    if isinstance(tree, int):
        return str(tree)
    return "(" + ",".join(to_newick(c) for c in tree) + ")"


rows = list(csv.DictReader((DATA / "tree_shapes.tsv").open(), delimiter="\t"))
by_n = {}
for r in rows:
    by_n.setdefault(int(r["n"]), []).append(r)

for n, sample in [(2, None), (3, None), (4, None), (5, 15)]:
    trees = enumerate_trees(n)
    total = len(trees)
    if sample is not None:
        trees = trees[:sample]
    bundle_rows = sorted(by_n.get(n, []), key=lambda r: int(r["shape_number"]))
    if len(bundle_rows) != len(trees):
        fail(f"n={n}: {len(bundle_rows)} rows in bundle vs {len(trees)} expected")
        continue
    for i, (tree, row) in enumerate(zip(trees, bundle_rows), 1):
        expected = to_newick(tree) + ";"
        if row["newick"] != expected:
            fail(f"n={n} shape {i}: newick {row['newick']} vs {expected}")
        if int(row["n_shapes_total"]) != total:
            fail(f"n={n} shape {i}: n_shapes_total {row['n_shapes_total']} vs {total}")
    print(f"n={n}: {len(bundle_rows)} shapes checked ({total} total, "
          f"{'exhaustive' if sample is None else f'sampled {sample}'})")

counts = list(csv.DictReader((DATA / "tree_count_growth.tsv").open(), delimiter="\t"))
for row in counts:
    n = int(row["n"])
    expected_catalan = catalan_number(n)
    expected_schroder = all_trees_new(n)
    if int(row["catalan"]) != expected_catalan:
        fail(f"n={n}: catalan {row['catalan']} vs {expected_catalan}")
    if int(row["little_schroder"]) != expected_schroder:
        fail(f"n={n}: little_schroder {row['little_schroder']} vs {expected_schroder}")
print(f"tree_count_growth: {len(counts)} rows (n=1..{counts[-1]['n']}) checked")

print("ALL TREE SHAPE/COUNT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
if not ok:
    sys.exit(1)
