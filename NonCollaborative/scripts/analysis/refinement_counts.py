"""How many trees are hiding behind each of the 69 maximal laminar families.

"69 maximal laminar families" quietly treats every polytomy (a node with >=3
direct children) as a single settled answer. It isn't one -- a polytomy in
this project's trees is always SOFT: the data is simply silent about how to
further divide that stretch, not a claim that the true structure really does
branch 3+ ways at once (see REFERENCES.md's "partially resolved tree"
discussion). Each polytomy stands in for every way that region could still be
sub-divided. This script counts that hidden multiplicity, per family and in
total.

The count, for one family, is a PRODUCT over every node in its tree of a
local "how many ways can this node's own direct children be arranged"
factor. A binary node (2 direct items) has exactly one arrangement, so it
contributes a factor of 1 regardless of convention -- only genuine
polytomies (arity >= 3) change the product. This is recursive-friendly
because a laminar family's tree is already exactly this: each node's own
children (leaves and/or further spans, doesn't matter which) partition a
disjoint region of positions, so what happens inside one child is completely
independent of what happens inside another, and of the parent's own
resolution choice. See the "silent 2-block" example in REFERENCES.md
(two 3-leaf polytomies, 3x3=9 hidden completions) -- this module generalizes
that to whole trees, all 69 (or fewer, under --subset) families, and every
node instead of just hand-picked ones.

Two conventions for the per-node local factor -- genuinely different
questions, both computed here because it is an open empirical question
whether every constituent must ultimately be binary:

  little Schroder number for the node's arity (A001003, "super-Catalan" in
  this project's own usage, see scripts/exploratory/catalan.py) -- counts
  every way of resolving that node at ANY remaining level of vagueness,
  including refinements that still leave part of it flatter than fully
  binary. This is what "refinements"/"hidden completions" meant everywhere
  else this was computed this session.

  Catalan number for the node's arity -- counts only the FULLY BINARY
  resolutions, i.e. "how many maximally specific candidate structures
  remain on the table," treating a polytomy as pure ignorance about which
  binary split is correct.

Neither is more "correct" in general: some observed constructions really
can be argued to be genuinely ternary (or worse) even where that's not
theoretically fashionable, so the Catalan convention's assumption that the
truth is always binary is itself a substantive (if common) claim, not a
neutral default. Both are computed side by side rather than picking one.

Summing a family's total across all families (rather than needing to
deduplicate) is safe under EITHER convention: the same injective-completion
argument that proved distinct maximal families can't share a fully-binary
completion (see REFERENCES.md's Catalan-ceiling proof) works unchanged for
ANY shared refinement, binary or not -- if two different maximal families
both refined into some common tree T (fully resolved or not), all of their
spans together would have to be pairwise compatible, contradicting
maximality unless the two families were the same to begin with.

Outputs (under results/nyan1308/laminar-families/ by default):
  nyan1308_refinement_counts.tsv       -- one row per family: n_spans,
                                           n_polytomies, max_arity,
                                           schroder_total, catalan_total
  nyan1308_refinement_polytomies.tsv   -- one row per DISTINCT (span, arity)
                                           polytomy seen anywhere across the
                                           families, with how many families
                                           it appears in -- the list to
                                           actually look at a high-arity
                                           node directly, rather than just
                                           trusting the aggregate product.

Usage:
  python scripts/analysis/refinement_counts.py
  python scripts/analysis/refinement_counts.py --subset morphosyntactic,length
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
EXPLORATORY_DIR = SCRIPT_DIR.parent / "exploratory"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(EXPLORATORY_DIR))

from laminar_analysis import (  # noqa: E402
    Span,
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
    build_parent_map,
    get_children,
)
from catalan import all_trees_new  # noqa: E402  (little Schroder numbers, A001003)


def catalan_number(n_leaves: int) -> int:
    """Number of strictly-binary ordered trees with n_leaves leaves.

    Standard formula: Catalan(n_leaves - 1) = C(2n-2, n-1) / n for n leaves
    (n=1 -> 1, n=2 -> 1, n=3 -> 2, n=4 -> 5, ...). Matches all_trees_new()
    at n=1,2 (both conventions agree there's exactly one way to arrange 0 or
    1 internal split) and diverges from n=3 onward, since all_trees_new()
    also counts the 3-leaf flat (non-binary) shape that this excludes.
    """
    if n_leaves < 1:
        raise ValueError(f"n_leaves must be >= 1, got {n_leaves}")
    if n_leaves == 1:
        return 1
    return math.comb(2 * n_leaves - 2, n_leaves - 1) // n_leaves


def node_arity(span: Span, children: dict[Span, list[Span]]) -> int:
    """Number of direct items (exposed leaves + direct child spans) at span.

    Mirrors span_to_newick()'s own gap-filling logic exactly, so "arity" here
    means the same thing as "how many direct children this node gets in the
    rendered tree" -- not the number of raw positions span covers. A span
    with no recorded child spans at all (fully silent about its own
    internals) is itself one polytomy of arity == span.size, matching the
    "silent block" example in REFERENCES.md (a 3-position span with no
    further splits recorded is a 3-way polytomy, not three separate nodes).
    """
    direct_children = children.get(span, [])
    if not direct_children:
        return span.size

    child_covered: set[int] = set()
    for child in direct_children:
        child_covered.update(range(child.left, child.right + 1))

    n_items = 0
    prev_boundary = span.left
    for child in sorted(direct_children, key=lambda s: s.left):
        for pos in range(prev_boundary, child.left):
            if pos not in child_covered:
                n_items += 1  # exposed leaf, itself a direct item
        n_items += 1  # the child span itself is one direct item
        prev_boundary = child.right + 1
    for pos in range(prev_boundary, span.right + 1):
        if pos not in child_covered:
            n_items += 1
    return n_items


def collect_polytomies(
        span: Span, children: dict[Span, list[Span]],
) -> list[tuple[Span, int]]:
    """Every node in span's subtree with arity >= 3, as (node_span, arity).

    Binary/leaf nodes (arity <= 2) are omitted -- they contribute a factor
    of 1 under both conventions below, so leaving them out changes nothing
    about the product, only makes the polytomy listing itself readable
    (see the module docstring: only genuine polytomies matter here).
    A leaf-only span (no direct child spans) is still one node in this
    walk -- its own arity is checked, but there is nothing further to
    recurse into.
    """
    results: list[tuple[Span, int]] = []
    arity = node_arity(span, children)
    if arity >= 3:
        results.append((span, arity))
    for child in children.get(span, []):
        results.extend(collect_polytomies(child, children))
    return results


def family_refinement_counts(family_spans: list[Span]) -> dict:
    """Per-family totals under both conventions, plus the raw polytomy list.

    schroder_total / catalan_total are products over every polytomy node's
    local factor -- see the module docstring for why this product is
    structurally justified (each polytomy's children partition disjoint,
    independently-resolved regions).
    """
    parent_map = build_parent_map(family_spans)
    children = get_children(parent_map)
    root = max(family_spans, key=lambda s: s.size)

    polytomies = collect_polytomies(root, children)

    schroder_total = 1
    catalan_total = 1
    for _span, arity in polytomies:
        schroder_total *= all_trees_new(arity)
        catalan_total *= catalan_number(arity)

    return {
        "n_spans": len(family_spans),
        "polytomies": polytomies,
        "n_polytomies": len(polytomies),
        "max_arity": max((a for _s, a in polytomies), default=2),
        "schroder_total": schroder_total,
        "catalan_total": catalan_total,
    }


def compute_all(
        domain_file: str,
        domains_dir: Path,
        subset: list[str] | None = None,
) -> tuple[list[dict], list[dict], int]:
    """Returns (family_rows, polytomy_rows, n_families).

    family_rows: one row per maximal laminar family.
    polytomy_rows: one row per DISTINCT (left, right, arity) polytomy seen
    anywhere, with how many of the families it occurs in -- the same span
    can have different arity in different families (its neighbouring spans
    differ), so (span, arity) rather than span alone is the dedup key.
    """
    spans, n_positions = load_spans(domain_file, str(domains_dir), subset=subset)
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    if truncated:
        raise RuntimeError("Family enumeration reached MAX_FAMILIES; counts would be incomplete.")

    family_rows: list[dict] = []
    polytomy_counter: dict[tuple[int, int, int], dict] = {}

    for idx, family_set in enumerate(families):
        family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
        result = family_refinement_counts(family_list)
        family_rows.append({
            "family": idx + 1,
            "n_spans": result["n_spans"],
            "n_polytomies": result["n_polytomies"],
            "max_arity": result["max_arity"],
            "schroder_total": result["schroder_total"],
            "catalan_total": result["catalan_total"],
        })
        for span, arity in result["polytomies"]:
            key = (span.left, span.right, arity)
            if key not in polytomy_counter:
                polytomy_counter[key] = {
                    "left": span.left,
                    "right": span.right,
                    "arity": arity,
                    "n_families": 0,
                    "little_schroder": all_trees_new(arity),
                    "catalan": catalan_number(arity),
                }
            polytomy_counter[key]["n_families"] += 1

    polytomy_rows = sorted(
        polytomy_counter.values(),
        key=lambda r: (-r["arity"], -r["n_families"], r["left"]),
    )
    return family_rows, polytomy_rows, len(families)


def write_tsv(rows: list[dict], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "nyan1308" / "laminar-families")
    parser.add_argument(
        "--subset", default=None,
        help="Comma-separated Domain_Type values (e.g. morphosyntactic,length) "
             "to restrict to. Default: pool every domain type. Output filenames "
             "get a _<subset> tag so a subset run never overwrites the pooled one.",
    )
    args = parser.parse_args()
    subset = args.subset.split(",") if args.subset else None
    tag = f"_{'_'.join(subset)}" if subset else ""

    args.output_dir.mkdir(parents=True, exist_ok=True)
    family_rows, polytomy_rows, n_families = compute_all(args.domain_file, args.domains_dir, subset=subset)

    write_tsv(family_rows, args.output_dir / f"nyan1308_refinement_counts{tag}.tsv")
    if polytomy_rows:
        write_tsv(polytomy_rows, args.output_dir / f"nyan1308_refinement_polytomies{tag}.tsv")

    schroder_grand_total = sum(r["schroder_total"] for r in family_rows)
    catalan_grand_total = sum(r["catalan_total"] for r in family_rows)

    label = f" ({args.subset})" if args.subset else " (all domain types pooled)"
    print(f"{n_families} maximal laminar families{label}")
    print(f"{len(polytomy_rows)} distinct (span, arity) polytomies observed across those families")
    print()
    print("Grand totals (sum across all families -- no double-counting, see module docstring):")
    print(f"  little Schroder (n-ary resolutions allowed): {schroder_grand_total:,}")
    print(f"  Catalan (binary resolutions only):           {catalan_grand_total:,}")
    print()
    print("Highest-arity polytomies observed (inspect these directly, don't just trust the product):")
    print(f"{'left':>5} {'right':>5} {'arity':>5} {'n_families':>10} {'little_schroder':>15} {'catalan':>8}")
    for row in polytomy_rows[:15]:
        print(
            f"{row['left']:5d} {row['right']:5d} {row['arity']:5d} "
            f"{row['n_families']:10d} {row['little_schroder']:15d} {row['catalan']:8d}"
        )


if __name__ == "__main__":
    main()
