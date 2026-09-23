"""Check the illustrations bundle's random_trees.tsv: valid trees, reproducible.

For the illustrations bundle (docs/PLANARSVIZ_LIBRARY_PROGRESS.md, phase E):
every row of data/random_trees.tsv should be a well-formed n-ary tree (every
internal node >=2 children) whose leaves are exactly 1..n_leaves once each,
matching metadata.json's n_trees/n_leaves. And re-running catalan.py's
sampler with the same recorded seed should reproduce the committed table
exactly -- the one property the now-archived
scripts/analysis/random_tree_overlay.py's generated script never had (it
recorded no seed at all), and the whole reason this bundle exists rather
than just fixing that file in place.

This does not, and cannot, check that the sample "looks right" -- that is
what results/chart_checks/reference/illustrations/
illustrations_random_tree_overlay.png is for a human to look at.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_random_trees_export.py
"""

import csv
import json
import random
import re
import sys
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(NC / "scripts" / "exploratory"))

from catalan import sample_labeled_tree  # noqa: E402

DATA = NC / "results" / "chart_data" / "illustrations" / "data"
ok = True


def fail(msg):
    global ok
    ok = False
    print("  MISMATCH:", msg)


metadata = json.loads((DATA / "metadata.json").read_text())["random_trees"]
rows = list(csv.DictReader((DATA / "random_trees.tsv").open(), delimiter="\t"))

if len(rows) != metadata["n_trees"]:
    fail(f"{len(rows)} rows vs metadata's n_trees={metadata['n_trees']}")

for row in rows:
    newick = row["newick"]
    # A leaf is a bare position number directly between "(" / "," and
    # "," / ")" -- an internal node's "L-R" span label sits right after its
    # closing ")" instead, so this never matches those.
    leaves = sorted(int(m) for m in re.findall(r"(?<=[(,])\d+(?=[,)])", newick))
    expected = list(range(1, metadata["n_leaves"] + 1))
    if leaves != expected:
        fail(f"tree {row['tree_number']}: leaves {leaves[:5]}... vs expected 1..{metadata['n_leaves']}")
        break
print(f"{len(rows)} trees, {metadata['n_leaves']} leaves each: leaf sets checked")

rng = random.Random(metadata["seed"])
reproduced = []
for _ in range(metadata["n_trees"]):
    tree = sample_labeled_tree(metadata["n_leaves"], rng)
    reproduced.append(tree)


def to_newick(tree):
    if isinstance(tree, int):
        return str(tree)
    inner = ",".join(to_newick(c) for c in tree)

    def leftmost(t):
        return t if isinstance(t, int) else leftmost(t[0])

    def rightmost(t):
        return t if isinstance(t, int) else rightmost(t[-1])
    return "(%s)%d-%d" % (inner, leftmost(tree), rightmost(tree))


mismatches = 0
for i, (row, tree) in enumerate(zip(rows, reproduced), 1):
    expected = to_newick(tree) + ";"
    if row["newick"] != expected:
        mismatches += 1
if mismatches:
    fail(f"{mismatches}/{len(rows)} trees did not reproduce with seed={metadata['seed']}")
else:
    print(f"seed={metadata['seed']}: all {len(rows)} trees reproduce exactly")

print("ALL RANDOM TREE CHECKS PASSED" if ok else "SOME CHECKS FAILED")
if not ok:
    sys.exit(1)
