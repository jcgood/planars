"""
Generate a series of PDFs, one per row, showing all (or a sample of) the
super-Catalan (little Schroder, OEIS A001003) tree shapes for n = 2..5
leaves. See catalan.py for the counting/enumeration code this builds on.

Each PDF holds one row of tree shapes, meant to be placed as stacked rows
on a slide:
    n=2 -> 1 tree
    n=3 -> 3 trees
    n=4 -> 11 trees
    n=5 -> the first 15 (of 45) trees in enumeration order

Rendering is done in R (render_supercatalan_rows.r), via ggtree's
`layout_dendrogram()` -- the same approach already proven in
the archived laminar_freqtree.r. An earlier version of this script drew the
trees directly in LaTeX/TikZ; that turned out to be the wrong tool for
this, and an earlier version of the R rendering gave each tree a height
proportional to its own number of levels -- so a height-1 tree came out
short and a height-3 tree came out three times as tall. That's wrong here:
every one of these trees stands for the same thing (one full span over n
leaves), so every root belongs at the same height regardless of how few
levels it took to get there, exactly as every root does in
the archived laminar_freqtree.r. render_supercatalan_rows.r now fixes each
tree's drawing box to one shared total height and lets ggtree's own
auto-fit stretch that tree's natural levels to reach it -- a shallow tree
ends up a wide, sparse triangle, not a short one.

ggtree's cladogram layout still gets each tree's own internal shape right
for free (a node's height is 1 + its tallest child's height, counted up
from the leaves -- never influenced by how deep the node sits in the whole
tree), which is what keeps a small subtree looking clean rather than
disjointed regardless of how deep it's buried; fixing every root to the
same height is a uniform rescale on top of that and doesn't disturb it.

Trees are unlabeled -- nodes are just where lines meet, no dot or box
marking them. All leaves sit on one shared height-0 line and all roots on
one shared top line, the way a sentence diagram lines up words along the
bottom.

This script only computes each tree's Newick string and leaf count, and
writes them to an intermediate JSON file for the R side to render -- see
render_supercatalan_rows.r for the actual layout and drawing.

Each row's PDF is cropped to its own content, so the four output pages end
up with four different physical sizes (n=2's is tiny; n=5's is wide) --
but the underlying horizontal scale (the marginal width per added leaf --
see WIDTH_PAD_IN in render_supercatalan_rows.r for why it's not simply
points per leaf) and the fixed root-to-leaf height are identical across
all of them. If you view them
independently -- separate PDF-viewer windows, or pasted into a slide and
each individually "fit to frame" -- every page fills its window regardless
of physical size, so a tree in the tiny n=2 row can *look* a different
size than one in the wide n=5 row even though the underlying scale is the
same. Scale all four rows by the same factor (not fit-to-width per row) to
see the true, consistent proportions.

Usage:
    python generate_supercatalan_rows.py         # write the JSON only
    python generate_supercatalan_rows.py --pdf    # also render to PDF
                                                   # (needs Rscript and
                                                   # pdfcrop on PATH)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from catalan import enumerate_trees

SCRIPT_DIR = Path(__file__).parent
OUT_DIR = SCRIPT_DIR.parent.parent / "results"
DATA_PATH = SCRIPT_DIR / "supercatalan_trees.json"
R_SCRIPT = SCRIPT_DIR / "render_supercatalan_rows.r"
CROP_MARGIN_BP = 5  # whitespace border pdfcrop leaves around each row's content

ROWS = [
    ("supercatalan_trees_n2", 2, None),
    ("supercatalan_trees_n3", 3, None),
    ("supercatalan_trees_n4", 4, None),
    ("supercatalan_trees_n5_sample15", 5, 15),
]


def to_newick(tree):
    """Newick string for `tree` (no branch lengths -- a pure cladogram)."""
    if isinstance(tree, int):
        return str(tree)
    return "(" + ",".join(to_newick(c) for c in tree) + ")"


def tree_height(tree):
    """1 + tallest child's height; a leaf's height is 0.

    Kept as metadata in the output JSON (e.g. for inspecting the sample)
    even though render_supercatalan_rows.r no longer sizes anything by
    it -- every tree's drawing box is now a fixed height regardless of
    this value; see that script for why.
    """
    if isinstance(tree, int):
        return 0
    return 1 + max(tree_height(c) for c in tree)


def leaf_count(tree):
    if isinstance(tree, int):
        return 1
    return sum(leaf_count(c) for c in tree)


def build_data():
    rows = []
    for name, n, sample in ROWS:
        trees = enumerate_trees(n)
        if sample is not None:
            trees = trees[:sample]
        rows.append(
            {
                "name": name,
                "trees": [
                    {
                        "newick": to_newick(t) + ";",
                        "n_leaves": leaf_count(t),
                        "height": tree_height(t),
                    }
                    for t in trees
                ],
            }
        )
    return {"rows": rows}


def build_rows(render_pdf):
    OUT_DIR.mkdir(exist_ok=True)
    data = build_data()
    DATA_PATH.write_text(json.dumps(data, indent=2))
    print(f"wrote {DATA_PATH} ({len(data['rows'])} rows)")
    for row in data["rows"]:
        print(f"  {row['name']}: {len(row['trees'])} trees")

    if not render_pdf:
        return

    subprocess.run(["Rscript", str(R_SCRIPT)], check=True, cwd=SCRIPT_DIR)

    for row in data["rows"]:
        raw_pdf = OUT_DIR / f"{row['name']}_raw.pdf"
        final_pdf = OUT_DIR / f"{row['name']}.pdf"
        subprocess.run(
            ["pdfcrop", "--margins", str(CROP_MARGIN_BP), str(raw_pdf), str(final_pdf)],
            check=True,
            capture_output=True,
        )
        raw_pdf.unlink()
        print(f"cropped {final_pdf}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="also render each row to PDF via Rscript + pdfcrop",
    )
    args = parser.parse_args()
    build_rows(args.pdf)
