"""Per-position boundary ("juncture") strength for nyan1308.

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

Outputs (under results/ by default):
  nyan1308_boundary_strength.tsv
  nyan1308_boundary_strength.pdf

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

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)


def compute_boundary_strength(
        domain_file: str,
        domains_dir: Path,
        subset: list[str] | None = None,
) -> tuple[list[dict], int]:
    """subset: Domain_Type values to include (e.g. ["morphosyntactic"]).
    None (the default) pools every domain type, matching the rest of this
    project's "all tests" analyses.
    """
    spans, n_positions = load_spans(domain_file, str(domains_dir), subset=subset)
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    if truncated:
        raise RuntimeError("Family enumeration reached MAX_FAMILIES; counts would be incomplete.")

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
    for fam in families:
        for p in {s.left for s in fam}:
            left_capped[p] += 1
        for p in {s.right for s in fam}:
            right_capped[p] += 1

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


def write_tsv(rows: list[dict], output_dir: Path, tag: str = ""):
    path = output_dir / f"nyan1308_boundary_strength{tag}.tsv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def save_figure(rows: list[dict], n_families: int, output_dir: Path, tag: str = ""):
    """Summed is the analytical target, drawn as a full-width bar. Capped is
    only a reference point -- drawn as a short white tick mark on each bar,
    not a second bar of equal visual weight -- plus the dotted line at
    n_families marking capped's theoretical ceiling.
    """
    positions = [r["position"] for r in rows]

    fig, (ax_left, ax_right) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for ax, side, title in [
        (ax_left, "left", "Left edge"),
        (ax_right, "right", "Right edge"),
    ]:
        summed = [r[f"{side}_summed"] for r in rows]
        capped = [r[f"{side}_capped"] for r in rows]
        width = 0.7
        ax.bar(positions, summed, width=width, color="#7876B1", label="strength (summed)")
        ax.scatter(positions, capped, marker="_", s=260, linewidths=2,
                   color="black", label="capped (reference only, max 69)", zorder=3)
        ax.set_ylabel(title, fontsize=13)
        ax.tick_params(axis="both", labelsize=11)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.axhline(n_families, color="black", linewidth=0.7, linestyle=":", alpha=0.5)

    ax_left.legend(loc="upper left", fontsize=10)
    ax_right.set_xlabel("Position on the planar structure", fontsize=13)
    ax_right.set_xticks(positions)
    fig.tight_layout()
    fig.savefig(output_dir / f"nyan1308_boundary_strength{tag}.pdf")
    plt.close(fig)


def save_distribution_figure(rows: list[dict], output_dir: Path, tag: str = ""):
    """Model left-edge and right-edge juncture strength (the summed measure
    only -- capped is not used here) as two overlapping inferred
    distributions over position, via a weighted Gaussian KDE: each
    position's summed strength is that position's weight, not a repeated
    observation, so the two distributions are directly comparable in shape
    regardless of their different total weights (gaussian_kde normalizes to
    integrate to 1 either way).
    """
    from scipy.stats import gaussian_kde

    positions = np.array([r["position"] for r in rows], dtype=float)
    left_w = np.array([r["left_summed"] for r in rows], dtype=float)
    right_w = np.array([r["right_summed"] for r in rows], dtype=float)

    grid = np.linspace(positions.min() - 1, positions.max() + 1, 400)
    left_kde = gaussian_kde(positions, weights=left_w, bw_method=0.15)(grid)
    right_kde = gaussian_kde(positions, weights=right_w, bw_method=0.15)(grid)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.fill_between(grid, left_kde, color="#7876B1", alpha=0.5, label="left-edge strength")
    ax.plot(grid, left_kde, color="#7876B1", linewidth=1.5)
    ax.fill_between(grid, right_kde, color="#BC3C29", alpha=0.5, label="right-edge strength")
    ax.plot(grid, right_kde, color="#BC3C29", linewidth=1.5)

    # Rug of the raw weighted positions, so the smoothing doesn't hide where
    # the actual discrete data points are.
    ax.scatter(positions, [-0.005] * len(positions), s=left_w / 2, color="#7876B1",
               alpha=0.6, clip_on=False)
    ax.scatter(positions, [-0.012] * len(positions), s=right_w / 2, color="#BC3C29",
               alpha=0.6, clip_on=False)

    ax.set_xlim(positions.min() - 1, positions.max() + 1)
    ax.set_xticks(positions)
    ax.set_xlabel("Position on the planar structure", fontsize=13)
    ax.set_ylabel("Inferred density (juncture strength)", fontsize=13)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    fig.savefig(output_dir / f"nyan1308_boundary_strength_distributions{tag}.pdf")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results")
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
    rows, n_families = compute_boundary_strength(args.domain_file, args.domains_dir, subset=subset)
    write_tsv(rows, args.output_dir, tag=tag)
    save_figure(rows, n_families, args.output_dir, tag=tag)
    save_distribution_figure(rows, args.output_dir, tag=tag)

    print(f"{n_families} maximal laminar families" + (f" ({args.subset})" if args.subset else " (all domain types pooled)"))
    print(f"{'pos':>3} {'left_summed':>11} {'left_capped':>11} {'right_summed':>12} {'right_capped':>12}")
    for r in rows:
        print(f"{r['position']:3d} {r['left_summed']:11d} {r['left_capped']:11d} "
              f"{r['right_summed']:12d} {r['right_capped']:12d}")


if __name__ == "__main__":
    main()
