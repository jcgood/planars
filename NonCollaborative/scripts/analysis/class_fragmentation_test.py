"""Is a domain class's (or bundle's) family count more fragmented than its
own test count would predict by chance alone?

nyan1308_tree_count_by_class.pdf shows very different family counts per
domain type (morphosyntactic 3, phonological 6, tonosegmental 9,
intonational 1, length 3), and nyan1308_tree_count_bundles.pdf the same for
the three pooled bundles (phonologylike, syntaxlike, syntaxlike_notono --
see BUNDLES in planars_groupings.py, reused here rather than redefined).
But every one of these groups also has a different number of underlying
tests, and a group with more tests has more chances to produce conflicting
spans -- so a bigger family count could just be a test-count artifact
rather than telling you anything about that group's own internal structure.
A "group" below is either a single domain type or a bundle (a union of
several); the test itself doesn't care which, since both are just "some
subset of Domain_Type values."

The null model here: "this group's tests are an arbitrary, unremarkable
sample of the same size from the full pool of 95 tests -- nothing about
being e.g. tonosegmental, or syntaxlike, specifically drives its
fragmentation." Simulated by randomly reassigning Domain_Type labels across
the 95 tests (row-level permutation, preserving each of the 5 underlying
domain types' own test COUNT exactly -- e.g. every permutation still has
exactly 44 tests labeled "tonosegmental", just not the same 44 tests), then
recomputing the resulting family count for each group (single type or
bundle) from the shuffled assignment. Because a bundle is just a fixed
union of domain types, permuting the 5 underlying type labels automatically
gives a valid permutation for every bundle too -- a bundle's in-group test
count is unchanged by the shuffle (it's a sum of type counts that are each
individually unchanged), so classes and bundles can share the exact same
permutation draws in one pass rather than needing separate runs. Test
identity (Left_Edge/Right_Edge/Size/Test_Labels) is held fixed throughout
-- only which label attaches to which row is randomized.

One-sided p-value per group (p_value_le_observed): the fraction of
permutations whose family count is <= the observed one -- same convention
as span_placement_test.py's p_value_le_observed, so "small p = unusually
laminar" reads the same way in both tables. A small p-value means that
group's tests produce fewer mutually-conflicting spans (i.e. are more
laminar) than a same-sized random sample from the whole dataset typically
would. A large p-value means the reverse: that group is more fragmented
than its test count alone would predict -- its fragmentation is not just
an artifact of how many tests it happens to have.

n_positions is taken from the FULL (unfiltered) dataset for every
permutation, matching the convention already used elsewhere in this
project (the overlay charts, collect_counts() in laminar_tree_counts.py)
-- the root span's own right edge doesn't affect which OTHER spans
conflict with each other, so this choice doesn't bias the null distribution,
it just keeps every replicate's synthetic root consistent.

Outputs (under results/nyan1308/counts-and-chance/ by default):
  nyan1308_class_fragmentation_test.tsv    -- the 5 singleton domain types
  nyan1308_bundle_fragmentation_test.tsv   -- the 3 pooled bundles
  nyan1308_fragmentation_null_draws.tsv    -- every individual permutation's
                                               family count, long format
                                               (group, kind, family_count) --
                                               the full null distributions
                                               the two summary TSVs above
                                               only report percentiles of.
                                               Feeds the density/observed-tick
                                               chart in
                                               fragmentation_test_plot.r
                                               rather than needing R to
                                               re-run the permutation itself.

Usage:
  python scripts/analysis/class_fragmentation_test.py
  python scripts/analysis/class_fragmentation_test.py --n-permutations 2000

The plain command reproduces the committed results/nyan1308/counts-and-chance/
files exactly (5000 draws, seed 0). Both summary TSVs record the draw count and
seed that made them, so a file can always say where its p-values came from.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    load_domain_dataframe,
    load_spans,
    aggregate_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)
from planars_groupings import BUNDLES  # noqa: E402  (single source of truth for bundle definitions)
from laminar_tree_counts import CLASS_COLORS  # noqa: E402  (single source of truth for class colors)

CLASS_ORDER = ["morphosyntactic", "phonological", "tonosegmental", "intonational", "length"]

# (group_name, domain_types) -- singleton classes as one-element lists, plus
# every bundle from planars_groupings.py's BUNDLES (name, subset, color,
# display label -- only name and subset are needed here).
CLASS_GROUPS: list[tuple[str, list[str]]] = [(cls, [cls]) for cls in CLASS_ORDER]
BUNDLE_GROUPS: list[tuple[str, list[str]]] = [(name, subset) for name, subset, _color, _display in BUNDLES]

# group name -> house-style color, so the R plot doesn't need its own copy
# of either palette.
GROUP_COLORS: dict[str, str] = {
    **CLASS_COLORS,
    **{name: color for name, _subset, color, _display in BUNDLES},
}


def family_count_for_group(df, n_positions: int, domain_types: list[str]) -> int:
    group_df = df[df["Domain_Type"].isin(domain_types)]
    spans = aggregate_spans(group_df)
    if not spans:
        return 0
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    if truncated:
        raise RuntimeError(f"Family enumeration reached MAX_FAMILIES for {domain_types}; "
                            "permutation counts would be incomplete.")
    return len(families)


def run_test(
        domain_file: str,
        domains_dir: Path,
        groups: list[tuple[str, list[str]]],
        n_permutations: int = 2000,
        seed: int = 0,
        n_positions: int | None = None,
) -> tuple[list[dict], dict[str, list[int]]]:
    """Returns (summary_rows, null_counts) -- null_counts maps each group
    name to its full list of per-permutation family counts (length
    n_permutations), not just the percentiles baked into summary_rows. Kept
    separate rather than embedded in summary_rows so a caller that only
    wants the summary (e.g. a quick console check) isn't forced to also
    build/return the much larger raw arrays.

    n_positions: the planar structure's position count, when known; None
    uses the largest right edge in the data, as before.
    """
    df = load_domain_dataframe(domain_file, str(domains_dir))
    _, n_positions = load_spans(domain_file, str(domains_dir), n_positions=n_positions)  # full-dataset n_positions

    observed = {
        name: family_count_for_group(df, n_positions, types)
        for name, types in groups
    }
    n_tests = {
        name: int(df["Domain_Type"].isin(types).sum())
        for name, types in groups
    }

    rng = np.random.default_rng(seed)
    labels = df["Domain_Type"].to_numpy().copy()
    null_counts: dict[str, list[int]] = {name: [] for name, _ in groups}

    permuted_df = df.copy()
    for _ in range(n_permutations):
        shuffled = rng.permutation(labels)
        permuted_df["Domain_Type"] = shuffled
        for name, types in groups:
            null_counts[name].append(family_count_for_group(permuted_df, n_positions, types))

    rows = []
    for name, _types in groups:
        null = np.array(null_counts[name])
        p_value = float(np.mean(null <= observed[name]))
        rows.append({
            "group": name,
            # .get(): a dataset whose domain types aren't this project's five
            # (the shifted test data renames one) still gets a colour rather
            # than a KeyError. The exporter overrides this with the bundle's
            # own palette anyway; it is here for the standalone R chart.
            "color": GROUP_COLORS.get(name, "#7F7F7F"),
            "n_tests": n_tests[name],
            "observed_families": observed[name],
            "null_mean": round(float(null.mean()), 3),
            "null_p05": int(np.percentile(null, 5)),
            "null_p95": int(np.percentile(null, 95)),
            "p_value_le_observed": round(p_value, 4),
        })
    return rows, null_counts


def write_tsv(rows: list[dict], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_null_draws(
        null_counts: dict[str, list[int]],
        bundle_names: set[str],
        path: Path,
) -> None:
    """Long format: one row per (group, permutation draw). `kind` is "class"
    or "bundle" so the R side can facet/color the two panels without needing
    to know the group-name lists itself.
    """
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["group", "kind", "family_count"])
        for name, counts in null_counts.items():
            kind = "bundle" if name in bundle_names else "class"
            for count in counts:
                writer.writerow([name, kind, count])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "nyan1308" / "counts-and-chance")
    # 5000 is what produced the committed results/nyan1308/counts-and-chance/
    # files, so the plain command reproduces them.
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    # One shared pass over both singleton classes and bundles -- see module
    # docstring for why they can safely share the same permutation draws.
    all_rows, null_counts = run_test(
        args.domain_file, args.domains_dir,
        groups=CLASS_GROUPS + BUNDLE_GROUPS,
        n_permutations=args.n_permutations, seed=args.seed,
    )
    # Carry what produced these numbers in the files themselves. A p-value from
    # 2000 draws and one from 5000 look identical in a TSV, and the run's own
    # report of the count goes to the terminal, where nobody reading the file
    # later will see it.
    for row in all_rows:
        row["n_permutations"] = args.n_permutations
        row["seed"] = args.seed

    bundle_names = {name for name, _types in BUNDLE_GROUPS}
    class_rows = [r for r in all_rows if r["group"] not in bundle_names]
    bundle_rows = [r for r in all_rows if r["group"] in bundle_names]

    write_tsv(class_rows, args.output_dir / "nyan1308_class_fragmentation_test.tsv")
    write_tsv(bundle_rows, args.output_dir / "nyan1308_bundle_fragmentation_test.tsv")
    write_null_draws(null_counts, bundle_names, args.output_dir / "nyan1308_fragmentation_null_draws.tsv")

    def show(title, rows):
        print(f"\n{title}")
        print(f"{'group':20} {'n_tests':>7} {'observed':>8} {'null_mean':>9} {'null_p05-p95':>13} {'p(<=obs)':>9}")
        for r in rows:
            print(
                f"{r['group']:20} {r['n_tests']:7d} {r['observed_families']:8d} "
                f"{r['null_mean']:9.2f} {r['null_p05']:5d}-{r['null_p95']:<6d} {r['p_value_le_observed']:9.4f}"
            )

    print(f"{args.n_permutations} permutations, seed={args.seed}")
    show("Singleton domain types:", class_rows)
    show("Bundles:", bundle_rows)


if __name__ == "__main__":
    main()
