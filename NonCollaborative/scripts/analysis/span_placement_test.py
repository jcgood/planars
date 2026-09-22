"""Does the real span arrangement produce fewer laminar-family "trees" than
an arbitrary arrangement of same-sized spans would -- a direct test of the
Tree hypothesis, broken down by domain class and bundle the same way
class_fragmentation_test.py is?

class_fragmentation_test.py asked "is this GROUP's family count surprising
given how many TESTS it has" by permuting which label attaches to which
test, holding every span's own position fixed. This asks a different
question: holding a group's own span LENGTHS fixed (ignore domain type and
test count entirely once the group's own spans are picked out), how
conflicted would spans of those same lengths be if their positions on the
planar structure were arbitrary rather than the real, linguistically-
motivated ones? A span's length only constrains where it CAN sit (a
length-22 span has exactly one legal position on a 22-position structure; a
length-2 span has 21) -- nothing about the null model favors nesting or
disjointness over crossing, so any tendency toward nesting in the real data
has to come from the real positions themselves, not from anything already
built into the null.

A "group" is the pooled dataset ("all", every domain type), one of the 5
single domain types, or one of the 3 bundles from planars_groupings.py's
BUNDLES -- same GROUPS list shape as class_fragmentation_test.py's
CLASS_GROUPS + BUNDLE_GROUPS, with "all" (subset=None) added as its own
group here (that script didn't need an "all" row; this one does, since the
single-group version of this test WAS the "all" analysis).

Every group's random re-placement draws over the FULL dataset's
n_positions (22 for nyan1308), not that group's own observed range -- e.g.
tonosegmental's real spans happen to stay within [5-17], but its null
placements can land anywhere on the full structure. This matches the
project-wide convention (run_domain_overlay(), compute_boundary_strength())
that a subset analysis still spans the complete planar structure; it also
keeps every group's null directly comparable on one shared axis.

Null model, per group: for each of the group's own observed spans' lengths,
draw a uniformly random legal left edge (1..n_positions-length+1, so the
span never runs off the end of the structure -- this is exactly why a
longer span has fewer legal positions than a shorter one, matching the
intuition that motivated this test). Two spans of DIFFERENT lengths can
never collide (their (left,right) pairs differ because their sizes differ),
so collisions are only possible within one length's own group of spans;
grouping the draw by length and sampling distinct positions without
replacement within each length group rules those out directly rather than
by retrying draws, and keeps a replicate's span count exactly equal to that
group's own observed span count. This means the observed data and every
null replicate are directly comparable: same n_spans, same length
multiset, same n_positions -- position is the only thing that varies.

One-sided p-value (p_le_observed): the fraction of null replicates whose
family count is <= the observed one. Small means the real arrangement is
unusually laminar (tree-like) for its length profile alone -- direct
support for the Tree hypothesis beyond what the lengths alone would
predict. Large would mean the reverse: the real data is unusually
CONFLICTED relative to same-length random placements. A group with very few
spans (e.g. intonational, 3) has little room to conflict either way even
under the null, so a p-value near the middle there is not itself surprising
-- read the null's own spread (null_p05/p95), not just the p-value, before
concluding a group's placement is unremarkable.

Family counts are stored as a (group, family_count, n) tally, not one row
per replicate -- family_count is a small-range integer, so this loses
nothing a downstream chart needs (order of the draws, which nothing uses)
while being far smaller. This follows the design Jeff settled for the
fragmentation test's own null-draws table (see
docs/PLANARSVIZ_LIBRARY_PROGRESS.md's "Chart 19" section): 5000 raw draws
collapsed to at most a few hundred distinct integers, per group.

Outputs (under results/nyan1308/counts-and-chance/ by default):
  nyan1308_span_placement_test.tsv        -- one row per group: n_spans,
                                              observed count, null summary
                                              stats, p-value, plus
                                              n_permutations/seed
  nyan1308_span_placement_null_tally.tsv  -- (group, family_count, n) tally
                                              of every group's null
                                              distribution

Usage:
  python scripts/analysis/span_placement_test.py
  python scripts/analysis/span_placement_test.py --n-permutations 5000
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    Span,
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)
from planars_groupings import BUNDLES  # noqa: E402  (single source of truth for bundle definitions)

CLASS_ORDER = ["morphosyntactic", "phonological", "tonosegmental", "intonational", "length"]

# (group_name, domain_types) -- "all" (subset=None) first, then the 5 single
# domain types, then the 3 bundles. Same shape as class_fragmentation_test.py's
# CLASS_GROUPS + BUNDLE_GROUPS, plus the "all" row this test also needs.
GROUPS: list[tuple[str, list[str] | None]] = (
    [("all", None)]
    + [(cls, [cls]) for cls in CLASS_ORDER]
    + [(name, subset) for name, subset, _color, _display in BUNDLES]
)


def random_replicate(sizes: list[int], n_positions: int, rng: np.random.Generator) -> list[Span]:
    """One null draw: every span in `sizes` gets a uniformly random legal
    left edge, grouped by size so same-size spans can never collide (see
    module docstring). Returns len(sizes) distinct Span objects.
    """
    by_size: dict[int, int] = Counter(sizes)
    spans: list[Span] = []
    for size, count in by_size.items():
        max_left = n_positions - size + 1
        # random.sample-equivalent via numpy: distinct positions, no replacement.
        lefts = rng.choice(max_left, size=count, replace=False) + 1
        spans.extend(Span(int(left), int(left) + size - 1) for left in lefts)
    return spans


def family_count(spans: list[Span], n_positions: int) -> tuple[int, bool]:
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    return len(families), truncated


def run_group(
        name: str,
        spans: list[Span],
        n_positions: int,
        n_permutations: int,
        rng: np.random.Generator,
) -> tuple[dict, dict[int, int]]:
    """One group's full test: returns (summary_dict, null_tally). `spans`
    must already be filtered to this group (e.g. via load_spans(subset=...))
    but n_positions is always the FULL dataset's, per the module docstring.
    """
    observed, observed_truncated = family_count(spans, n_positions)
    if observed_truncated:
        raise RuntimeError(f"Observed family enumeration reached MAX_FAMILIES for group "
                            f"'{name}'; the real result itself would be incomplete.")

    sizes = [s.size for s in spans]

    null_tally: dict[int, int] = Counter()
    n_truncated = 0
    for _ in range(n_permutations):
        replicate = random_replicate(sizes, n_positions, rng)
        count, truncated = family_count(replicate, n_positions)
        if truncated:
            n_truncated += 1
        null_tally[count] += 1

    counts_expanded = np.array(
        [count for count, n in null_tally.items() for _ in range(n)]
    )
    p_le = float(np.mean(counts_expanded <= observed))

    summary = {
        "group": name,
        "n_spans": len(spans),
        "n_positions": n_positions,
        "observed_families": observed,
        "n_permutations": n_permutations,
        "seed": None,  # filled in by run_test, which owns the single shared rng/seed
        "n_truncated": n_truncated,
        "null_mean": round(float(counts_expanded.mean()), 3),
        "null_p05": int(np.percentile(counts_expanded, 5)),
        "null_p50": int(np.percentile(counts_expanded, 50)),
        "null_p95": int(np.percentile(counts_expanded, 95)),
        "p_value_le_observed": round(p_le, 4),
    }
    return summary, dict(null_tally)


def run_test(
        domain_file: str,
        domains_dir: Path,
        groups: list[tuple[str, list[str] | None]],
        n_permutations: int = 5000,
        seed: int = 0,
) -> tuple[list[dict], dict[str, dict[int, int]]]:
    """Returns (summary_rows, null_tallies) -- null_tallies maps each group
    name to its own (family_count -> n) tally. One shared rng advances
    across all groups in order, so a run is fully reproducible from `seed`
    alone but no two groups draw the same underlying random stream.
    """
    _, n_positions = load_spans(domain_file, str(domains_dir))  # full-dataset n_positions
    rng = np.random.default_rng(seed)

    summary_rows: list[dict] = []
    null_tallies: dict[str, dict[int, int]] = {}
    for name, domain_types in groups:
        spans, _ = load_spans(domain_file, str(domains_dir), subset=domain_types)
        summary, tally = run_group(name, spans, n_positions, n_permutations, rng)
        summary["seed"] = seed
        summary_rows.append(summary)
        null_tallies[name] = tally
    return summary_rows, null_tallies


def write_summary(rows: list[dict], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_tally(null_tallies: dict[str, dict[int, int]], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["group", "family_count", "n"])
        for name, tally in null_tallies.items():
            for count in sorted(tally):
                writer.writerow([name, count, tally[count]])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "nyan1308" / "counts-and-chance")
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, null_tallies = run_test(
        args.domain_file, args.domains_dir, groups=GROUPS,
        n_permutations=args.n_permutations, seed=args.seed,
    )
    write_summary(rows, args.output_dir / "nyan1308_span_placement_test.tsv")
    write_tally(null_tallies, args.output_dir / "nyan1308_span_placement_null_tally.tsv")

    print(f"{args.n_permutations} permutations, seed={args.seed}")
    print(f"{'group':20} {'n_spans':>7} {'observed':>8} {'null_mean':>9} {'null_p05-p95':>13} {'p(<=obs)':>9}")
    for r in rows:
        print(
            f"{r['group']:20} {r['n_spans']:7d} {r['observed_families']:8d} "
            f"{r['null_mean']:9.2f} {r['null_p05']:5d}-{r['null_p95']:<6d} {r['p_value_le_observed']:9.4f}"
        )


if __name__ == "__main__":
    main()
