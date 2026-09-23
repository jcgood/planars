"""Count maximal laminar families for nyan1308, pooled, per class and per bundle.

The project calls a maximal laminar family a tree: it is a maximal set of
observed spans that are mutually nested or disjoint.  Counts here therefore
refer to maximal laminar families, not to the number of raw diagnostic rows.

The existing laminar_analysis.load_spans() function deduplicates diagnostics
with the same positional span and excludes size-1 spans.  This script uses
that same convention.  "Adjacent" means a span of size 2, i.e. [i, i+1].

Output (under results/nyan1308/counts-and-chance/ by default):
  nyan1308_tree_counts.tsv  -- includes both per-class and bundle rows

The bar charts these counts feed are drawn by the planarsviz package
(plot_tree_counts()) from the bundle export_planarsviz_data.py writes, which
reads collect_counts()/collect_bundle_counts() here.

Usage:
  python scripts/analysis/laminar_tree_counts.py
  python scripts/analysis/laminar_tree_counts.py --domain-file domains_other.tsv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    find_conflicts,
    enumerate_maximal_laminar_families,
    load_spans,
)
# Pooled multi-class bundles come from planars_groupings.py, the one place
# they are defined; their colours match each bundle's own forest chart.
from planars_groupings import BUNDLES  # noqa: E402


CLASS_ORDER = [
    "morphosyntactic",
    "phonological",
    "tonosegmental",
    "intonational",
    "length",
]

# Exact pooled-plot colors. Read by class_fragmentation_test.py and by
# export_planarsviz_data.py's DOMAIN_TYPE_STYLE, which is where R gets them.
# `indeterminate` is CCDB's third domain type (absent from nyan1308); it is
# not in CLASS_ORDER above, so it never displaces the five nyan1308 classes --
# it only supplies a colour for datasets (CCDB's) that observe it.
CLASS_COLORS = {
    "morphosyntactic": "#BC3C29",
    "tonosegmental": "#0072B5",
    "length": "#E18727",
    "phonological": "#20845E",
    "intonational": "#7876B1",
    "indeterminate": "#6F99AD",
}

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


def collect_counts(domain_file: str, domains_dir: Path,
                   classes: list[str] | None = None) -> list[dict]:
    """Family counts for all tests and per domain type, with and without
    size-2 spans.

    classes: the domain types to count, in order (default CLASS_ORDER). A
    type with no tests in the data can't be counted -- load_spans() fails on
    an empty subset -- so a caller handling other datasets passes only the
    types that occur (export_planarsviz_data.py does).
    """
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

    for domain_class in (CLASS_ORDER if classes is None else classes):
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


def collect_bundle_counts(domain_file: str, domains_dir: Path,
                          bundles: list | None = None) -> list[dict]:
    """Same schema as collect_counts()'s rows, one per entry in BUNDLES (or
    in `bundles`, same shape; pass only bundles with a type that occurs, for
    the reason given in collect_counts())."""
    rows: list[dict] = []
    for name, subset, _color, _display in (BUNDLES if bundles is None else bundles):
        bundle_spans, n_positions = load_spans(domain_file, str(domains_dir), subset=subset)
        count, n_spans = count_families(bundle_spans, n_positions)
        rows.append({
            "condition": "all_tests",
            "class": name,
            "n_unique_spans": n_spans,
            "n_maximal_laminar_families": count,
        })
    return rows


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
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "nyan1308" / "counts-and-chance")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_counts(args.domain_file, args.domains_dir)
    bundle_rows = collect_bundle_counts(args.domain_file, args.domains_dir)
    write_tsv(rows + bundle_rows, args.output_dir)

    for row in rows + bundle_rows:
        print(
            f"{row['condition']:24} {row['class']:18} "
            f"spans={row['n_unique_spans']:2} "
            f"families={row['n_maximal_laminar_families']:2}"
        )


if __name__ == "__main__":
    main()
