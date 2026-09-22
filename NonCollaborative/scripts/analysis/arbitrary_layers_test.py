"""Is a group's laminar-family count unusual for that many *arbitrary*
layers -- spans of arbitrary size at arbitrary positions?

This is the third and most naive of the project's three permutation tests,
and the differences between them are the point:

  class_fragmentation_test.py shuffles which domain-type LABEL sits on which
  test, holding every span exactly where it is. It asks "is this group's
  family count surprising given how many tests it has?"

  span_placement_test.py holds each span's own LENGTH fixed and randomizes
  only its position. It asks "given these exact sizes, do the real positions
  matter?"

  This one randomizes SIZE AND POSITION together: every legal interval of
  size >= 2 is equally likely. It knows nothing at all about what real
  linguistic domains look like -- only how many of them there are. It asks
  "is this count remarkable for a set of this many arbitrary spans?"

Each is a strictly weaker null than the one before it, and the weakest is the
one that most resembles how a raw family count is usually read aloud. That
matters: a headline like "69 families out of 47 trillion possible trees"
compares against the space of all trees, which makes any real dataset's count
look tiny almost by construction. This test supplies the baseline that
comparison is missing.

WHAT COUNTS AS A LAYER, AND THE ROOT. A group's null draw has exactly as many
spans as the group really has, so observed and null are directly comparable on
count. One further detail keeps them comparable: if a group's real spans
include the full-structure span [1, n_positions] -- nyan1308's pooled set does,
since synthetic_root is False for it -- then the null fixes that same span and
draws the rest freely. A group whose real spans do not include it draws all of
them freely. Either way the null and the observed set agree on how many spans
there are and on whether one of them covers everything, so the only thing that
varies is the arbitrary sizes and positions of the rest.

Every group draws over the FULL dataset's n_positions, not its own observed
range -- the same convention span_placement_test.py, run_domain_overlay() and
compute_boundary_strength() already follow, and what keeps the groups
comparable with each other.

One-sided p-value (p_value_le_observed): the fraction of null replicates whose
family count is <= the observed one, the same direction and column name the
other two tests use, so small always means "unusually laminar" regardless of
which test produced it.

THE FAMILY CAP. laminar_analysis.MAX_FAMILIES is a module-level safeguard set
to 1000. Fully arbitrary intervals cross far more chaotically than real
linguistic domains do, and 1000 truncates this null badly -- a truncated draw
is counted as its cap rather than its real value, which biases every summary
statistic downward. `raised_family_cap()` below lifts it for the duration of a
run and puts it back afterwards, so no other caller in the same process is
affected. `n_truncated` still reports any draw that hit the raised cap.

Run from NonCollaborative/:
  python scripts/analysis/arbitrary_layers_test.py
  python scripts/analysis/arbitrary_layers_test.py --n-permutations 1000
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import laminar_analysis  # noqa: E402
from laminar_analysis import (  # noqa: E402
    Span,
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)
from planars_groupings import BUNDLES  # noqa: E402

CLASS_ORDER = ["morphosyntactic", "phonological", "tonosegmental", "intonational", "length"]

# Same shape and order as span_placement_test.py's GROUPS. The order is
# load-bearing: run_test() advances one shared random stream across the groups
# in the order given.
GROUPS: list[tuple[str, list[str] | None]] = (
    [("all", None)]
    + [(cls, [cls]) for cls in CLASS_ORDER]
    + [(name, subset) for name, subset, _color, _display in BUNDLES]
)

# Enough headroom that an arbitrary-interval draw is essentially never
# truncated. The scratch work this grew out of found draws into the high
# hundreds; 50,000 leaves two orders of magnitude of margin.
RAISED_MAX_FAMILIES = 50_000


@contextlib.contextmanager
def raised_family_cap(cap: int = RAISED_MAX_FAMILIES):
    """Raise laminar_analysis.MAX_FAMILIES for the duration, then restore it.

    A plain monkeypatch would leak into every other caller sharing the module
    in this process -- the exporter imports it too. Restoring on the way out
    keeps this test's need from becoming everyone's.
    """
    previous = laminar_analysis.MAX_FAMILIES
    laminar_analysis.MAX_FAMILIES = cap
    try:
        yield
    finally:
        laminar_analysis.MAX_FAMILIES = previous


def legal_intervals(n_positions: int, exclude: set[tuple[int, int]] = frozenset()) -> list[tuple[int, int]]:
    """Every interval of size >= 2 on the structure, minus `exclude`.

    Size >= 2 matches the real pipeline's own filter: a one-position span
    conflicts with nothing and so cannot affect a family count.
    """
    return [
        (left, right)
        for left in range(1, n_positions + 1)
        for right in range(left + 1, n_positions + 1)
        if (left, right) not in exclude
    ]


def random_replicate(n_spans: int, n_positions: int, keep_root: bool,
                     pool: list[tuple[int, int]], rng: np.random.Generator) -> list[Span]:
    """One null draw: `n_spans` distinct arbitrary spans over the structure.

    When `keep_root`, the full-structure span is one of them and the other
    n_spans - 1 are drawn from `pool` (which excludes it); otherwise all
    n_spans come from `pool`. Drawn without replacement, so a replicate always
    has exactly n_spans distinct spans, like the real set it stands in for.
    """
    n_free = n_spans - 1 if keep_root else n_spans
    picks = rng.choice(len(pool), size=n_free, replace=False)
    spans = [Span(*pool[int(i)]) for i in picks]
    if keep_root:
        spans.append(Span(1, n_positions))
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
    """One group's full test: returns (summary_dict, null_tally).

    `spans` must already be filtered to this group; `n_positions` is always
    the full dataset's, per the module docstring.
    """
    observed, observed_truncated = family_count(spans, n_positions)
    if observed_truncated:
        raise RuntimeError(f"Observed family enumeration reached MAX_FAMILIES for group "
                           f"'{name}'; the real result itself would be incomplete.")

    root = (1, n_positions)
    keep_root = any((s.left, s.right) == root for s in spans)
    pool = legal_intervals(n_positions, exclude={root})

    null_tally: dict[int, int] = Counter()
    n_truncated = 0
    for _ in range(n_permutations):
        replicate = random_replicate(len(spans), n_positions, keep_root, pool, rng)
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
        "includes_root": "y" if keep_root else "n",
        "observed_families": observed,
        "n_permutations": n_permutations,
        "seed": None,  # filled in by run_test, which owns the shared rng/seed
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
    """Returns (summary_rows, null_tallies), the same shape as
    span_placement_test.run_test().

    One shared rng advances across all groups in the order given, so a run is
    reproducible from `seed` alone but no two groups draw the same stream --
    which is why the group order is part of what the numbers mean.
    """
    _, n_positions = load_spans(domain_file, str(domains_dir))  # full-dataset n_positions
    rng = np.random.default_rng(seed)

    summary_rows: list[dict] = []
    null_tallies: dict[str, dict[int, int]] = {}
    with raised_family_cap():
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
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path,
                        default=REPO_DIR / "results" / "counts-and-chance")
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    dataset = args.domain_file.replace("domains_", "").replace(".tsv", "")
    rows, tallies = run_test(args.domain_file, args.domains_dir, GROUPS,
                             args.n_permutations, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / f"{dataset}_arbitrary_layers_test.tsv"
    tally_path = args.output_dir / f"{dataset}_arbitrary_layers_null_tally.tsv"
    write_summary(rows, summary_path)
    write_tally(tallies, tally_path)

    for row in rows:
        print(f"{row['group']:22} n_spans={row['n_spans']:3}  observed={row['observed_families']:5}  "
              f"null mean={row['null_mean']:8.1f}  p05/p50/p95={row['null_p05']}/{row['null_p50']}/{row['null_p95']}  "
              f"p(<=obs)={row['p_value_le_observed']:.4f}"
              + (f"  TRUNCATED {row['n_truncated']}" if row["n_truncated"] else ""))
    print(f"\nwrote {summary_path}\nwrote {tally_path}")


if __name__ == "__main__":
    main()
