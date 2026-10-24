"""Per-position boundary ("juncture") strength for one dataset (the figures
below are nyan1308's).

This is a deliberate shift in unit of analysis: everywhere else in this
project's laminar-family work, the object being measured is a DOMAIN (a
span, with its own family-count/convergence). Here the object is a
JUNCTURE -- the cut between position p and p+1 -- and the question is how
strongly that specific cut is treated as a real constituent edge, on
either side, across the 69 maximal laminar families ("trees"). This is a
structural-robustness weighting of the boundary-frequency idea already in
this project (scripts/nyan_boundary_skyline.r, which weights by raw TEST
count instead of family count).

Primary measure -- "summed": for each position p, sum over every span S
with S.left == p (or S.right == p) of how many of the 69 trees contain S.
Multiple constituents reconfirming the same juncture -- even nested ones,
even within the same tree -- makes that juncture stronger; this is exactly
the intended behavior for a boundary-strength measure, not an artifact to
correct for.

Secondary measure, kept only as a reference point -- "capped": the number
of the 69 trees that have AT LEAST ONE span with left == p (or right ==
p), counted once per tree no matter how many of that tree's own nested
spans share the edge. Bounded by 69. Useful as a "how many of the 69
analyses agree this is a boundary AT ALL, independent of how many times
over" comparison line on the chart, but it is not the analytical target --
see the 2026-09-14 discussion in this project's session notes
(docs/CHART_MECHANICS_AND_UNCERTAINTY.md) for why summed vs. capped
diverge and which question each one answers. Checked directly, not
assumed: e.g. position 5 in the pooled (all domain types) nyan1308 data
gets summed=260 but capped=69, because several nested spans that all
start at position 5 happen to co-occur in the same trees.

All domain types are pooled by default (matching how the rest of this
project's "all tests" analyses work), but compute_boundary_strength()
takes an optional `subset` of Domain_Type values -- see load_spans() in
laminar_analysis.py for the exact values -- so a future per-domain-type or
per-bundle breakdown is a one-argument change, not a rewrite.

strength_from_families() is the pure per-position core -- spans and an
already-enumerated family list in, summed/capped left/right dicts out --
factored out so boundary_strength_test.py (the permutation test asking
whether these numbers are higher than chance) can call the exact same
counting logic on a randomly-repositioned replicate's spans/families
without re-deriving it. compute_boundary_strength() is a thin wrapper
that adds the load-from-disk step and the position range.

Output (under results/<dataset>/boundaries/ by default; the dataset is named
after --domain-file):
  <dataset>_boundary_strength.tsv (with --subset, <dataset>_boundary_strength_<types>.tsv)

The charts these numbers feed -- the per-side boundary chart and the density
overlay -- are drawn by the planarsviz package from the bundle
export_planarsviz_data.py writes, which calls compute_boundary_strength()
here.

Usage:
  python scripts/analysis/boundary_strength.py
  python scripts/analysis/boundary_strength.py --subset morphosyntactic,length
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)
from datasets import add_dataset_arguments, resolve_dataset_arguments  # noqa: E402


def strength_from_families(
        spans: list,
        families: list[frozenset],
) -> tuple[dict[int, int], dict[int, int], dict[int, int], dict[int, int]]:
    """Per-position left/right summed and capped strength from spans and
    their already-enumerated maximal laminar families.

    summed: for each position p, sum over every span S with S.left == p (or
    S.right == p) of how many of the families contain S. Multiple
    constituents reconfirming the same juncture -- even nested ones, even
    within the same tree -- makes that juncture stronger; see the module
    docstring for why this is the intended behavior, not an artifact.

    capped: the number of families that have AT LEAST ONE span with
    left == p (or right == p), counted once per family no matter how many
    of that family's own nested spans share the edge. Bounded by
    len(families). Kept only as a reference point -- see module docstring.

    Both count only the spans in ``spans``. A family can also hold the
    placeholder root [1..n] that enumerate_maximal_laminar_families() adds
    when no test covers the whole structure; no test puts an edge there, so
    it counts toward neither measure. (Until 2026-09-23 it counted toward
    capped, which drew a "capped" mark with no evidence behind it at
    positions 1 and n; Jeff's call to leave it out, as summed always has.)

    Returns dicts keyed by position; a position with no span is
    simply absent (callers fill in 0 for the positions they report over).
    """
    span_family_count: dict = defaultdict(int)
    for fam in families:
        for s in fam:
            span_family_count[s] += 1

    left_summed: dict[int, int] = defaultdict(int)
    right_summed: dict[int, int] = defaultdict(int)
    for s in spans:
        n = span_family_count[s]
        left_summed[s.left] += n
        right_summed[s.right] += n

    left_capped: dict[int, int] = defaultdict(int)
    right_capped: dict[int, int] = defaultdict(int)
    observed = set(spans)
    for fam in families:
        members = [s for s in fam if s in observed]
        for p in {s.left for s in members}:
            left_capped[p] += 1
        for p in {s.right for s in members}:
            right_capped[p] += 1

    return left_summed, right_summed, left_capped, right_capped


def compute_boundary_strength(
        domain_file: str,
        domains_dir: Path,
        subset: list[str] | None = None,
        n_positions: int | None = None,
) -> tuple[list[dict], int]:
    """subset: Domain_Type values to include (e.g. ["morphosyntactic"]).
    None (the default) pools every domain type, matching the rest of this
    project's "all tests" analyses.

    n_positions: the planar structure's position count, when known; passed to
    load_spans(). None means one row per position up to the largest right
    edge, as before.
    """
    spans, n_positions = load_spans(domain_file, str(domains_dir), subset=subset,
                                    n_positions=n_positions)
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    if truncated:
        raise RuntimeError("Family enumeration reached MAX_FAMILIES; counts would be incomplete.")

    left_summed, right_summed, left_capped, right_capped = strength_from_families(spans, families)

    rows = [
        {
            "position": p,
            "left_summed": left_summed[p],
            "left_capped": left_capped[p],
            "right_summed": right_summed[p],
            "right_capped": right_capped[p],
        }
        for p in range(1, n_positions + 1)
    ]
    return rows, len(families)


def write_tsv(rows: list[dict], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_dataset_arguments(parser, "boundaries", groupings=False)
    parser.add_argument(
        "--subset", default=None,
        help="Comma-separated Domain_Type values (e.g. morphosyntactic,length) "
             "to restrict to. Default: pool every domain type. Output filenames "
             "get a _<subset> tag so a subset run never overwrites the pooled one.",
    )
    args = parser.parse_args()
    run = resolve_dataset_arguments(args, "boundaries")
    subset = args.subset.split(",") if args.subset else None
    tag = f"_{'_'.join(subset)}" if subset else ""

    # As the exporter does: the pooled analysis runs over the planar
    # structure's positions, a subset analysis up to its own last one.
    rows, n_families = compute_boundary_strength(
        args.domain_file, args.domains_dir, subset=subset,
        n_positions=None if subset else run.n_positions,
    )
    write_tsv(rows, run.output_dir / f"{run.dataset}_boundary_strength{tag}.tsv")

    print(f"{n_families} maximal laminar families" + (f" ({args.subset})" if args.subset else " (all domain types pooled)"))
    print(f"{'pos':>3} {'left_summed':>11} {'left_capped':>11} {'right_summed':>12} {'right_capped':>12}")
    for r in rows:
        print(f"{r['position']:3d} {r['left_summed']:11d} {r['left_capped']:11d} "
              f"{r['right_summed']:12d} {r['right_capped']:12d}")


if __name__ == "__main__":
    main()
