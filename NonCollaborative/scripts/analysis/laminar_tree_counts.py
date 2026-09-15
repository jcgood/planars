"""Plot counts of maximal laminar families for nyan1308.

The project calls a maximal laminar family a tree: it is a maximal set of
observed spans that are mutually nested or disjoint.  Counts here therefore
refer to maximal laminar families, not to the number of raw diagnostic rows.

The existing laminar_analysis.load_spans() function deduplicates diagnostics
with the same positional span and excludes size-1 spans.  This script uses
that same convention.  "Adjacent" means a span of size 2, i.e. [i, i+1].

Outputs (under results/ by default):
  nyan1308_tree_count_all.pdf
  nyan1308_tree_count_by_class.pdf
  nyan1308_tree_count_without_adjacent.pdf
  nyan1308_tree_count_bundles.pdf   -- BUNDLES: phonologylike, syntaxlike,
                                        syntaxlike_notono (see laminar_analysis.py's
                                        __main__ for the matching forest charts)
  nyan1308_tree_counts.tsv          -- includes both per-class and bundle rows

Usage:
  python scripts/analysis/laminar_tree_counts.py
  python scripts/analysis/laminar_tree_counts.py --domain-file domains_other.tsv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    find_conflicts,
    enumerate_maximal_laminar_families,
    load_spans,
)
from planars_groupings import BUNDLES  # noqa: E402


CLASS_ORDER = [
    "morphosyntactic",
    "phonological",
    "tonosegmental",
    "intonational",
    "length",
]

# Exact pooled-plot colors.
CLASS_COLORS = {
    "morphosyntactic": "#BC3C29",
    "tonosegmental": "#0072B5",
    "length": "#E18727",
    "phonological": "#20845E",
    "intonational": "#7876B1",
}

# Pooled multi-class bundles (BUNDLES) are imported from planars_groupings.py,
# the one place they are defined; their colours match each bundle's own forest
# chart (nyan1308_{name}_laminar_forest.pdf, from laminar_analysis.main()).


def count_families(spans, n_positions: int) -> tuple[int, int]:
    """Return (number of maximal families, number of compatible spans)."""
    families, truncated = enumerate_maximal_laminar_families(
        spans, find_conflicts(spans), n_positions
    )
    if truncated:
        raise RuntimeError(
            "Family enumeration reached MAX_FAMILIES; count is incomplete."
        )
    return len(families), len(spans)


def collect_counts(domain_file: str, domains_dir: Path) -> list[dict]:
    all_spans, n_positions = load_spans(domain_file, str(domains_dir))
    rows: list[dict] = []

    all_count, all_n_spans = count_families(all_spans, n_positions)
    rows.append({
        "condition": "all_tests",
        "class": "all",
        "n_unique_spans": all_n_spans,
        "n_maximal_laminar_families": all_count,
    })

    without_adjacent = [span for span in all_spans if span.size != 2]
    no_adj_count, no_adj_n_spans = count_families(without_adjacent, n_positions)
    rows.append({
        "condition": "without_adjacent_spans",
        "class": "all",
        "n_unique_spans": no_adj_n_spans,
        "n_maximal_laminar_families": no_adj_count,
    })

    for domain_class in CLASS_ORDER:
        class_spans, _ = load_spans(
            domain_file, str(domains_dir), subset=[domain_class]
        )
        class_count, class_n_spans = count_families(class_spans, n_positions)
        rows.append({
            "condition": "all_tests",
            "class": domain_class,
            "n_unique_spans": class_n_spans,
            "n_maximal_laminar_families": class_count,
        })

        class_without_adjacent = [span for span in class_spans if span.size != 2]
        no_adj_class_count, no_adj_class_n_spans = count_families(
            class_without_adjacent, n_positions
        )
        rows.append({
            "condition": "without_adjacent_spans",
            "class": domain_class,
            "n_unique_spans": no_adj_class_n_spans,
            "n_maximal_laminar_families": no_adj_class_count,
        })

    return rows


def collect_bundle_counts(domain_file: str, domains_dir: Path) -> list[dict]:
    """Same schema as collect_counts()'s rows, one per entry in BUNDLES."""
    rows: list[dict] = []
    for name, subset, _color, _display in BUNDLES:
        bundle_spans, n_positions = load_spans(domain_file, str(domains_dir), subset=subset)
        count, n_spans = count_families(bundle_spans, n_positions)
        rows.append({
            "condition": "all_tests",
            "class": name,
            "n_unique_spans": n_spans,
            "n_maximal_laminar_families": count,
        })
    return rows


def add_value_labels(ax, bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            str(int(height)),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=12,
        )


def save_all_figure(rows: list[dict], output_dir: Path):
    row = next(r for r in rows if r["condition"] == "all_tests" and r["class"] == "all")
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["All tests"], [row["n_maximal_laminar_families"]], color="#444444", width=0.55)
    add_value_labels(ax, bars)
    ax.set_ylabel("Number of maximal laminar families")
    ax.set_title("Chichewa (nyan1308): all tests")
    ax.set_ylim(0, row["n_maximal_laminar_families"] * 1.18)
    fig.tight_layout()
    fig.savefig(output_dir / "nyan1308_tree_count_all.pdf")
    plt.close(fig)


def save_horizontal_bar_chart(
        items: list[tuple[str, int, str]],
        xlabel: str,
        output_path: Path,
        figsize: tuple[float, float] = (8, 3.8),
) -> None:
    """Shared "house style" horizontal bar chart: least-to-most (bottom to
    top), no title, no bounding box, narrow bars, transparent background with
    black text (reads correctly on a white/light background, which is the
    common case; will be invisible on a dark slide -- flip to white if that's
    ever the target instead), value labels to the right of each bar. `items`
    is a list of (label, value, color); sorted here, callers don't need to
    pre-sort.
    """
    items = sorted(items, key=lambda item: item[1])
    labels = [label for label, _, _ in items]
    values = [value for _, value, _ in items]
    colors = [color for _, _, color in items]

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("none")
    ax.set_facecolor("none")
    bars = ax.barh(labels, values, color=colors, height=0.45)
    for bar in bars:
        width = bar.get_width()
        ax.annotate(
            str(int(width)),
            xy=(width, bar.get_y() + bar.get_height() / 2),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=15,
            color="black",
        )
    ax.set_xlabel(xlabel, fontsize=14, color="black")
    ax.set_xlim(0, max(values) * 1.2)
    ax.tick_params(axis="y", labelsize=14, colors="black")
    ax.tick_params(axis="x", labelsize=13, colors="black")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)
    fig.tight_layout()
    fig.savefig(output_path, transparent=True)
    plt.close(fig)


def save_class_figure(rows: list[dict], output_dir: Path):
    items = [
        (c.title(),
         next(r for r in rows if r["condition"] == "all_tests" and r["class"] == c)[
             "n_maximal_laminar_families"
         ],
         CLASS_COLORS[c])
        for c in CLASS_ORDER
    ]
    save_horizontal_bar_chart(
        items, "Number of trees", output_dir / "nyan1308_tree_count_by_class.pdf"
    )


def save_bundle_figure(bundle_rows: list[dict], output_dir: Path):
    items = [
        (display,
         next(r for r in bundle_rows if r["class"] == name)["n_maximal_laminar_families"],
         color)
        for name, _subset, color, display in BUNDLES
    ]
    save_horizontal_bar_chart(
        items, "Number of trees", output_dir / "nyan1308_tree_count_bundles.pdf"
    )


def save_without_adjacent_figure(rows: list[dict], output_dir: Path):
    conditions = [("all_tests", "All tests"), ("without_adjacent_spans", "Without size-2 spans")]
    values = [
        next(r for r in rows if r["condition"] == condition and r["class"] == "all")[
            "n_maximal_laminar_families"
        ]
        for condition, _ in conditions
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([label for _, label in conditions], values, color=["#777777", "#222222"], width=0.6)
    add_value_labels(ax, bars)
    ax.set_ylabel("Number of maximal laminar families")
    ax.set_title("Chichewa (nyan1308): effect of removing adjacent spans")
    ax.set_ylim(0, max(values) * 1.25)
    fig.tight_layout()
    fig.savefig(output_dir / "nyan1308_tree_count_without_adjacent.pdf")
    plt.close(fig)


def write_tsv(rows: list[dict], output_dir: Path):
    path = output_dir / "nyan1308_tree_counts.tsv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_counts(args.domain_file, args.domains_dir)
    bundle_rows = collect_bundle_counts(args.domain_file, args.domains_dir)
    write_tsv(rows + bundle_rows, args.output_dir)
    save_all_figure(rows, args.output_dir)
    save_class_figure(rows, args.output_dir)
    save_without_adjacent_figure(rows, args.output_dir)
    save_bundle_figure(bundle_rows, args.output_dir)

    for row in rows + bundle_rows:
        print(
            f"{row['condition']:24} {row['class']:18} "
            f"spans={row['n_unique_spans']:2} "
            f"families={row['n_maximal_laminar_families']:2}"
        )


if __name__ == "__main__":
    main()
