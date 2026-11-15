"""How strong is each domain? Three measures for every observed span, read
side by side: the tests for and against it, a shuffle test, and a bootstrap.

Why this exists: a span's *family share* (how many of the maximal laminar
families contain it, e.g. 5-17 in 37 of nyan1308's 69) counts trees, and the
number of trees is set by the combinatorics of conflicts. A span crossed by
one weakly supported span can be missing from half the trees. These measures
count tests instead.

1. Tests for and against (no randomness).
   - tests_for: the tests whose domain is exactly this span (its convergence).
   - tests_against: the tests whose domain crosses it (partially overlaps,
     neither nested nor disjoint), so that no tree can contain both.
   - concordance: tests_for / (tests_for + tests_against). It plays the part
     of the site concordance factor in phylogenomics (Minh, Hahn & Lanfear
     2020): the share of the informative evidence that agrees with a clade.
     Crossing is character incompatibility in the sense of Le Quesne (1969)
     and Estabrook, Johnson & McMorris (1976): two characters (here, tests)
     that no single tree can accommodate together.

2. Shuffle test: is the span crossed less than chance would cross it?
   Hold the span's own tests where they are; give every other test a new,
   uniformly random position with the same length (a legal left edge, so it
   stays inside the structure); count the tests that now cross the span.
   p_le_observed is the share of shuffles with as few crossing tests as
   observed or fewer: small means the real tests stay out of this span's way
   more than randomly placed tests of the same lengths would. Every span is
   tested at its own size and position, so no size threshold is chosen after
   looking at the data. A span nothing can cross (the whole structure,
   1..N) has null_max_against = 0 and p = 1: it is reported as untestable,
   not as evidence (its 100% family share is the same special case).
   Tests are shuffled one by one, not by span, because only pairwise
   crossing is counted (no tree enumeration), so it is cheap; two tests that
   coincide in the data are placed independently. 26 spans are tested at
   once in nyan1308, so p_holm gives Holm's (1979) adjustment for that.

3. Bootstrap: how stable is the span, given the tests that happened to be
   coded? Felsenstein's (1985) phylogenetic bootstrap, after Efron (1979):
   resample the tests with replacement (same number), rebuild the spans and
   the maximal laminar families from the resample, and record each observed
   span's family share in it (0 when no resampled test produces it).
   - boot_present: share of replicates in which some test produces the span;
   - boot_majority: share in which it is in more than half the replicate's
     trees, i.e. in its majority-rule consensus (Margush & McMorris 1981);
     the closest analogue of a clade's bootstrap support;
   - boot_share_mean, boot_share_lo, boot_share_hi: the family share's mean
     and its central 95% interval (2.5th and 97.5th percentiles) across
     replicates.
   A replicate whose enumeration stops at laminar_analysis.MAX_FAMILIES is
   counted in n_truncated (its shares come from the families found so far).
   A domain resting on one test is left out of a resample about 37% of the
   time ((1 - 1/n)^n for n tests), so its bootstrap support cannot go much
   above 0.63 however uncontested it is: read boot_present beside it. This
   is the bootstrap's known weakness with clades supported by a single
   character.

References: NonCollaborative/REFERENCES.md, "Support for a domain".

Outputs (under results/<dataset>/counts-and-chance/ by default):
  <dataset>_domain_support.tsv  -- one row per observed span, all three
                                   measures, with n_permutations,
                                   n_bootstrap and seed

Usage (from anywhere; the dataset and its planar table follow from
--domain-file, see datasets.py):
  python -m laminar.domain_support
  python -m laminar.domain_support --domain-file domains_chac1251_verbal.tsv
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np

from laminar.datasets import add_dataset_arguments, resolve_dataset_arguments
from laminar.laminar_analysis import (
    Span,
    aggregate_spans,
    classify_pair,
    enumerate_maximal_laminar_families,
    find_conflicts,
    load_domain_dataframe,
    load_spans,
)

FIELDS = [
    "span_id", "left", "right", "size",
    "tests_for", "tests_against", "concordance", "crossing_spans", "family_share",
    "null_mean_against", "null_max_against", "p_le_observed", "p_holm",
    "boot_present", "boot_majority", "boot_share_mean", "boot_share_lo", "boot_share_hi",
    "n_truncated", "n_permutations", "n_bootstrap", "seed",
]


def span_id(span: Span) -> str:
    return f"{span.left}-{span.right}"


def crosses(left: np.ndarray, right: np.ndarray, span: Span) -> np.ndarray:
    """Which intervals [left, right] cross `span` (partial overlap). The
    vectorised form of classify_pair(...) == "conflict"."""
    overlap = (left <= span.right) & (right >= span.left)
    nested = ((left <= span.left) & (right >= span.right)) | ((left >= span.left) & (right <= span.right))
    return overlap & ~nested


def family_shares(spans: list[Span], n_positions: int) -> tuple[dict[tuple[int, int], float], bool]:
    """Each span's share of the maximal laminar families of `spans`, keyed
    by (left, right), and whether the enumeration was truncated."""
    families, truncated = enumerate_maximal_laminar_families(spans, find_conflicts(spans), n_positions)
    counts: Counter = Counter()
    for family in families:
        for span in family:
            counts[(span.left, span.right)] += 1
    return {key: n / len(families) for key, n in counts.items()}, truncated


def holm(p_values: list[float]) -> list[float]:
    """Holm's (1979) step-down adjustment, in the input order."""
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def run_support(domain_file: str, domains_dir: Path, n_permutations: int = 5000,
                n_bootstrap: int = 1000, seed: int = 0,
                n_positions: int | None = None) -> list[dict]:
    """One row per observed span (FIELDS). One rng, seeded once, serves the
    shuffles and then the bootstrap, so a run is reproducible from `seed`."""
    spans, n_positions = load_spans(domain_file, str(domains_dir), n_positions=n_positions)
    tests = load_domain_dataframe(domain_file, str(domains_dir))
    left = tests["Left_Edge"].to_numpy(dtype=int)
    right = tests["Right_Edge"].to_numpy(dtype=int)
    size = right - left + 1
    observed_shares, truncated = family_shares(spans, n_positions)
    if truncated:
        raise RuntimeError("The observed family enumeration reached MAX_FAMILIES; "
                           "family shares would be incomplete.")
    rng = np.random.default_rng(seed)

    rows = []
    for span in spans:
        own = (left == span.left) & (right == span.right)
        others = ~own
        against = int(crosses(left[others], right[others], span).sum())
        crossing = [s for s in spans if classify_pair(s, span) == "conflict"]
        # Every other test, n_permutations times: a uniformly random legal
        # left edge for its own length.
        other_sizes = size[others]
        lefts = rng.integers(1, n_positions - other_sizes + 2, size=(n_permutations, len(other_sizes)))
        rights = lefts + other_sizes - 1
        null_against = crosses(lefts, rights, span).sum(axis=1)
        rows.append({
            "span_id": span_id(span), "left": span.left, "right": span.right, "size": span.size,
            "tests_for": span.convergence, "tests_against": against,
            "concordance": round(span.convergence / (span.convergence + against), 4),
            "crossing_spans": " ".join(span_id(s) for s in crossing),
            "family_share": round(observed_shares[(span.left, span.right)], 4),
            "null_mean_against": round(float(null_against.mean()), 3),
            "null_max_against": int(null_against.max()),
            "p_le_observed": round(float(np.mean(null_against <= against)), 4),
        })
    for row, adjusted in zip(rows, holm([r["p_le_observed"] for r in rows])):
        row["p_holm"] = round(adjusted, 4)

    # Bootstrap over tests (Felsenstein 1985).
    keys = [(s.left, s.right) for s in spans]
    shares = np.zeros((n_bootstrap, len(spans)))
    present = np.zeros((n_bootstrap, len(spans)), dtype=bool)
    n_truncated = 0
    for b in range(n_bootstrap):
        sample = tests.iloc[rng.integers(0, len(tests), size=len(tests))]
        replicate = aggregate_spans(sample)
        replicate_keys = {(s.left, s.right) for s in replicate}
        replicate_shares, truncated = family_shares(replicate, n_positions)
        n_truncated += truncated
        for j, key in enumerate(keys):
            present[b, j] = key in replicate_keys
            shares[b, j] = replicate_shares.get(key, 0.0)
    for j, row in enumerate(rows):
        row.update({
            "boot_present": round(float(present[:, j].mean()), 4),
            "boot_majority": round(float((shares[:, j] > 0.5).mean()), 4),
            "boot_share_mean": round(float(shares[:, j].mean()), 4),
            "boot_share_lo": round(float(np.percentile(shares[:, j], 2.5)), 4),
            "boot_share_hi": round(float(np.percentile(shares[:, j], 97.5)), 4),
            "n_truncated": n_truncated, "n_permutations": n_permutations,
            "n_bootstrap": n_bootstrap, "seed": seed,
        })
    return rows


def write_rows(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_dataset_arguments(parser, "counts-and-chance", groupings=False)
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run = resolve_dataset_arguments(args, "counts-and-chance")
    rows = run_support(args.domain_file, args.domains_dir, n_permutations=args.n_permutations,
                       n_bootstrap=args.n_bootstrap, seed=args.seed, n_positions=run.n_positions)
    path = run.output_dir / f"{run.dataset}_domain_support.tsv"
    write_rows(rows, path)
    print(f"{args.n_permutations} shuffles, {args.n_bootstrap} bootstrap replicates, seed={args.seed}; "
          f"wrote {path}")
    print(f"{'span':>6} {'for':>4} {'against':>7} {'conc':>5} {'trees':>6} {'p(<=obs)':>8} "
          f"{'boot maj':>8} {'share 95%':>12}")
    for r in sorted(rows, key=lambda r: (-r["size"], r["left"])):
        print(f"{r['span_id']:>6} {r['tests_for']:4d} {r['tests_against']:7d} {r['concordance']:5.2f} "
              f"{r['family_share']:6.2f} {r['p_le_observed']:8.4f} {r['boot_majority']:8.2f} "
              f"{r['boot_share_lo']:5.2f}-{r['boot_share_hi']:<5.2f}")


if __name__ == "__main__":
    main()
