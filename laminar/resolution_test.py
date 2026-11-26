"""Is a region of the planar structure (a word) flatter -- less resolved --
than the structure around it (the phrase)? Tests the idea that words have
less internal structure than phrases.

Resolution (the project's measure of internal structure; Jeff, 2026-11-14):
the share of the domains a stretch could hold that it actually holds. A
stretch of k units can hold at most k - 1 domains (counting the stretch
itself), reached only when every domain splits in two; a flat stretch holds
one. Phylogenetics measures a tree the same way: Colless's (1980) consensus
index counts a tree's clades against the most a fully resolved tree has.
Binarity (domains that split in exactly two, as in the "most binary"
selection) is kept but is not the measure of flatness: a stretch can add
domains that split three ways and become more resolved while its binary
share falls.

For a region [a, b] (k = b - a + 1 positions) and one tree (maximal laminar
family) of an N-position structure:
  - inside: the tree's domains lying within [a, b], the region itself
    included when it is a domain; resolution_in = inside / (k - 1);
  - outside: with the region counted as one unit there are N - k + 1 units,
    so at most N - k domains; the tree's domains that contain the region or
    are disjoint from it (the root included) count, resolution_out =
    outside / (N - k);
  - a domain that crosses the region belongs to neither and is counted
    separately (crossing): in the observed nyan1308 trees there are none
    with the orthographic word, but randomly placed spans often cross it.
The statistic is difference = resolution_in - resolution_out, averaged over
the trees; negative means the word is flatter than the phrase.

Null model: span_placement_test.py's. The dataset's distinct spans keep
their lengths and get uniformly random positions; the maximal families are
rebuilt and the same averages taken. p_le_observed is the share of
replicates with a difference as low as observed or lower (word as flat or
flatter by chance); p_ge_observed the reverse. The region stays where it is:
it is a fixed hypothesis about where the word is, not something estimated
from the spans. It comes from the dataset's highlights file
(planar_tables/highlights_<dataset>.tsv, the first row of --region-id) or
from --region L-R.

Reading the null: randomly placed spans often cross the region, and a
crossing domain counts for neither side, so the null's trees lose domains
inside the region that the real trees keep (null_crossing_mean against the
observed crossing_mean). A real word that no domain crosses can therefore
look more resolved than the null even when its tests are no denser. Read
the difference together with the crossing counts.

Caution, not fixable by any shuffle: if the tests were chosen to probe one
region (Chichewa's are mostly verb-internal, wordhood diagnostics), that
region gets more domains because more tests looked there. The shuffle
spreads the same spans evenly, so it removes exactly this imbalance.

Outputs (under results/<dataset>/counts-and-chance/ by default), named by
the region's positions so that runs on different regions sit side by side
(e.g. nyan1308_resolution_5-19_test.tsv):
  <dataset>_resolution_<L>-<R>_test.tsv        -- one row: the region,
                                                  observed means (resolution
                                                  in and out, difference,
                                                  whole-tree resolution,
                                                  crossing), the null's
                                                  summary, p-values,
                                                  n_permutations, seed
  <dataset>_resolution_<L>-<R>_trees.tsv       -- the observed trees, one
                                                  row each
  <dataset>_resolution_<L>-<R>_null_tally.tsv  -- (difference, n) tally of
                                                  the null (rounded to 4
                                                  places)

Usage (from anywhere):
  python -m laminar.resolution_test
  python -m laminar.resolution_test --region 5-17
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np

from laminar.datasets import NC, add_dataset_arguments, resolve_dataset_arguments
from laminar.laminar_analysis import Span, enumerate_maximal_laminar_families, find_conflicts, load_spans
from laminar.span_placement_test import random_replicate


DEFAULT_REGION_ID = "orthographic_word"   # the highlight the region is read from


def region_in_highlights(path: Path, region_id: str = DEFAULT_REGION_ID) -> tuple[int, int] | None:
    """The first row of `region_id` in a highlights file (its first row is
    the outermost layer), or None when the file has no such highlight."""
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["highlight_id"] == region_id:
                return int(row["left"]), int(row["right"])
    return None


def region_from_highlights(dataset: str, region_id: str) -> tuple[int, int]:
    """The region from planar_tables/highlights_<dataset>.tsv (the
    exporter's highlights file); stops with what to do when there is none."""
    path = NC / "planar_tables" / f"highlights_{dataset}.tsv"
    if not path.exists():
        raise SystemExit(f"No highlights file for {dataset} ({path}); give the region with --region L-R.")
    region = region_in_highlights(path, region_id)
    if region is None:
        raise SystemExit(f"{path} has no highlight {region_id!r}; give the region with --region L-R.")
    return region


def tree_resolution(family, region: tuple[int, int], n_positions: int) -> dict:
    """Resolution inside and outside `region` for one tree (see docstring)."""
    a, b = region
    k = b - a + 1
    inside = outside = crossing = 0
    for span in family:
        if a <= span.left and span.right <= b:
            inside += 1
        elif (span.left <= a and span.right >= b) or span.right < a or span.left > b:
            outside += 1
        else:
            crossing += 1
    res_in = inside / (k - 1)
    res_out = outside / (n_positions - k)
    return {"inside": inside, "outside": outside, "crossing": crossing,
            "resolution_in": res_in, "resolution_out": res_out,
            "difference": res_in - res_out,
            "resolution_tree": len(family) / (n_positions - 1)}


def mean_resolution(spans: list[Span], region: tuple[int, int], n_positions: int) -> tuple[dict, list[dict], bool]:
    families, truncated = enumerate_maximal_laminar_families(spans, find_conflicts(spans), n_positions)
    trees = [tree_resolution(f, region, n_positions) for f in families]
    means = {key: float(np.mean([t[key] for t in trees])) for key in trees[0]}
    return means, trees, truncated


def run_test(domain_file: str, domains_dir: Path, region: tuple[int, int],
             n_permutations: int = 5000, seed: int = 0,
             n_positions: int | None = None) -> tuple[dict, list[dict], dict[float, int]]:
    spans, n_positions = load_spans(domain_file, str(domains_dir), n_positions=n_positions)
    a, b = region
    if not (1 <= a < b <= n_positions) or (a, b) == (1, n_positions):
        raise SystemExit(f"Region {a}-{b} must lie inside 1-{n_positions}, span at least two "
                         "positions and not be the whole structure.")
    observed, trees, truncated = mean_resolution(spans, region, n_positions)
    if truncated:
        raise RuntimeError("The observed family enumeration reached MAX_FAMILIES.")

    rng = np.random.default_rng(seed)
    sizes = [s.size for s in spans]
    null = []
    null_crossing = []
    n_truncated = 0
    for _ in range(n_permutations):
        means, _, truncated = mean_resolution(random_replicate(sizes, n_positions, rng), region, n_positions)
        n_truncated += truncated
        null.append(means["difference"])
        null_crossing.append(means["crossing"])
    null = np.array(null)
    summary = {
        "region": f"{a}-{b}", "n_spans": len(spans), "n_positions": n_positions, "n_trees": len(trees),
        "resolution_in": round(observed["resolution_in"], 4),
        "resolution_out": round(observed["resolution_out"], 4),
        "difference": round(observed["difference"], 4),
        "resolution_tree": round(observed["resolution_tree"], 4),
        "crossing_mean": round(observed["crossing"], 3),
        "trees_flatter_inside": sum(t["difference"] < 0 for t in trees),
        "trees_equal": sum(t["difference"] == 0 for t in trees),
        "trees_flatter_outside": sum(t["difference"] > 0 for t in trees),
        "null_mean": round(float(null.mean()), 4),
        "null_p05": round(float(np.percentile(null, 5)), 4),
        "null_p95": round(float(np.percentile(null, 95)), 4),
        "null_crossing_mean": round(float(np.mean(null_crossing)), 3),
        "p_le_observed": round(float(np.mean(null <= observed["difference"] + 1e-12)), 4),
        "p_ge_observed": round(float(np.mean(null >= observed["difference"] - 1e-12)), 4),
        "n_truncated": n_truncated, "n_permutations": n_permutations, "seed": seed,
    }
    return summary, trees, dict(Counter(round(float(x), 4) for x in null))


def tree_rows(trees: list[dict]) -> list[dict]:
    """The observed trees as the _trees table writes them, one row each."""
    return [{"tree": i + 1, **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items()}}
            for i, t in enumerate(trees)]


def tally_rows(tally: dict[float, int]) -> list[dict]:
    """The null as the _null_tally table writes it: (difference, n)."""
    return [{"difference": d, "n": n} for d, n in sorted(tally.items())]


def write_tsv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_dataset_arguments(parser, "counts-and-chance", groupings=False)
    parser.add_argument("--region-id", default=DEFAULT_REGION_ID,
                        help="Highlight whose first row is the region (default orthographic_word).")
    parser.add_argument("--region", default=None, metavar="L-R",
                        help="The region as positions, instead of a highlight.")
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run = resolve_dataset_arguments(args, "counts-and-chance")
    if args.region:
        left, right = (int(x) for x in args.region.split("-"))
        region = (left, right)
    else:
        region = region_from_highlights(run.dataset, args.region_id)

    summary, trees, tally = run_test(args.domain_file, args.domains_dir, region,
                                     n_permutations=args.n_permutations, seed=args.seed,
                                     n_positions=run.n_positions)
    stem = run.output_dir / f"{run.dataset}_resolution_{region[0]}-{region[1]}"
    write_tsv(Path(f"{stem}_test.tsv"), [summary])
    write_tsv(Path(f"{stem}_trees.tsv"), tree_rows(trees))
    write_tsv(Path(f"{stem}_null_tally.tsv"), tally_rows(tally))
    for key, value in summary.items():
        print(f"{key:24} {value}")


if __name__ == "__main__":
    main()
