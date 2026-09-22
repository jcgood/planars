"""Is the per-position boundary strength boundary_strength.py reports -- and,
more specifically, the JUMP between adjacent positions -- higher than a
same-length-profile random arrangement of spans would produce by chance?

This reuses span_placement_test.py's null model exactly (same
random_replicate(), same GROUPS list, same "draw over the FULL dataset's
n_positions regardless of group" convention -- see that module's docstring
for the reasoning) but asks a different question of each replicate. That
test asks "how many maximal laminar families does this replicate produce,
compared to the observed data" -- one number per replicate. This asks "what
does this replicate's own boundary-strength CURVE look like at every
position, compared to the observed curve" -- boundary_strength.py's
strength_from_families(), computed fresh on each replicate's own spans and
families.

Two statistics are reported per (group, side, position):

  level -- the summed strength itself (boundary_strength.py's left_summed /
    right_summed), read off directly.
  jump  -- strength[p] - strength[p-1] (0 at position 1, where there is no
    p-1). A SIGNED difference, not absolute value: the claim under test
    (see NonCollaborative's Berkeley.pptx, slide 74) is specifically a RISE
    in strength at a left word-boundary candidate, not "a discontinuity in
    either direction", and the null's signed distribution is naturally
    centred near zero, so a one-sided test on the signed value is the direct
    test of that claim.

Both use the one-sided p_value_ge_observed convention (fraction of null
draws >= observed): small p = unusually strong evidence for a boundary at
that position, for that statistic. This is the mirror image of
span_placement_test.py's own p_value_le_observed (there, FEWER families is
the interesting direction; here, MORE strength is) -- see that module's
docstring for why the direction differs by question, not by inconsistency.

No raw per-draw table is kept for either statistic: only the null's mean,
5th and 95th percentiles per (group, side, position, statistic). This
mirrors the density curves in boundary_strength_density.tsv (also
precomputed percentiles/curves, not raw draws) rather than
fragmentation_null.tsv's tally (which exists because that chart draws an
actual violin from the distribution shape; a boundary-strength chart only
needs an envelope band around the observed curve).

Outputs (under results/nyan1308/boundaries/ by default):
  nyan1308_boundary_strength_test.tsv -- one row per (group, side, statistic,
    position): group, kind, label, colour, side, statistic, position,
    observed, null_mean, null_p05, null_p95, p_value_ge_observed,
    n_permutations, seed.

Usage:
  python scripts/analysis/boundary_strength_test.py
  python scripts/analysis/boundary_strength_test.py --n-permutations 2000
"""

from __future__ import annotations

import argparse
import sys
import csv
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    load_spans,
    find_conflicts,
    enumerate_maximal_laminar_families,
)
from boundary_strength import strength_from_families  # noqa: E402
from span_placement_test import GROUPS, random_replicate  # noqa: E402


def curves_from_spans(spans, n_positions: int) -> tuple[np.ndarray, np.ndarray, bool]:
    """(left_curve, right_curve, truncated): dense arrays over positions
    1..n_positions (0 where boundary_strength.strength_from_families()
    reports no span at that position), from one span set's own family
    enumeration. Shared by the observed computation and every null replicate
    so both go through the exact same steps.
    """
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    left_summed, right_summed, _left_capped, _right_capped = strength_from_families(spans, families)
    left = np.array([left_summed[p] for p in range(1, n_positions + 1)], dtype=float)
    right = np.array([right_summed[p] for p in range(1, n_positions + 1)], dtype=float)
    return left, right, truncated


def jump_curve(level: np.ndarray) -> np.ndarray:
    """strength[p] - strength[p-1], with a leading 0 (position 1 has no
    predecessor). Same length as `level` so the two statistics share one
    position index; the position-1 jump row is written out but is not a
    meaningful test (there is nothing before it to jump from).
    """
    return np.concatenate([[0.0], np.diff(level)])


def run_group(
        name: str,
        spans,
        n_positions: int,
        n_permutations: int,
        rng: np.random.Generator,
) -> tuple[list[dict], int]:
    """One group's full test: returns (rows, n_truncated). `spans` must
    already be filtered to this group (e.g. via load_spans(subset=...)) but
    n_positions is always the FULL dataset's, per span_placement_test.py's
    convention (see module docstring).
    """
    observed_left, observed_right, observed_truncated = curves_from_spans(spans, n_positions)
    if observed_truncated:
        raise RuntimeError(f"Observed family enumeration reached MAX_FAMILIES for group "
                            f"'{name}'; the real result itself would be incomplete.")
    observed = {
        ("left", "level"): observed_left,
        ("right", "level"): observed_right,
        ("left", "jump"): jump_curve(observed_left),
        ("right", "jump"): jump_curve(observed_right),
    }

    sizes = [s.size for s in spans]
    null_draws: dict[tuple[str, str], list[np.ndarray]] = {key: [] for key in observed}
    n_truncated = 0
    for _ in range(n_permutations):
        replicate = random_replicate(sizes, n_positions, rng)
        left, right, truncated = curves_from_spans(replicate, n_positions)
        if truncated:
            n_truncated += 1
        null_draws[("left", "level")].append(left)
        null_draws[("right", "level")].append(right)
        null_draws[("left", "jump")].append(jump_curve(left))
        null_draws[("right", "jump")].append(jump_curve(right))

    rows = []
    for (side, statistic), obs_curve in observed.items():
        null_matrix = np.stack(null_draws[(side, statistic)])  # (n_permutations, n_positions)
        for i, position in enumerate(range(1, n_positions + 1)):
            null_column = null_matrix[:, i]
            obs = obs_curve[i]
            p_value = float(np.mean(null_column >= obs))
            rows.append({
                "group": name,
                "side": side,
                "statistic": statistic,
                "position": position,
                "observed": obs,
                "null_mean": round(float(null_column.mean()), 3),
                "null_p05": round(float(np.percentile(null_column, 5)), 3),
                "null_p95": round(float(np.percentile(null_column, 95)), 3),
                "p_value_ge_observed": round(p_value, 4),
            })
    return rows, n_truncated


def run_test(
        domain_file: str,
        domains_dir: Path,
        groups: list[tuple[str, list[str] | None]],
        n_permutations: int = 5000,
        seed: int = 0,
) -> list[dict]:
    """Returns one flat list of rows across every group, side, statistic and
    position. One shared rng advances across all groups in order, so a run
    is fully reproducible from `seed` alone but no two groups draw the same
    underlying random stream (matches span_placement_test.py's run_test()).
    """
    _, n_positions = load_spans(domain_file, str(domains_dir))  # full-dataset n_positions
    rng = np.random.default_rng(seed)

    all_rows: list[dict] = []
    for name, domain_types in groups:
        spans, _ = load_spans(domain_file, str(domains_dir), subset=domain_types)
        rows, n_truncated = run_group(name, spans, n_positions, n_permutations, rng)
        for row in rows:
            row["n_permutations"] = n_permutations
            row["seed"] = seed
        all_rows.extend(rows)
        if n_truncated:
            print(f"  note: {n_truncated}/{n_permutations} null replicates for "
                  f"group '{name}' hit MAX_FAMILIES (used as enumerated, not discarded, "
                  f"matching span_placement_test.py's convention)")
    return all_rows


def write_tsv(rows: list[dict], path: Path):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv")
    parser.add_argument("--domains-dir", type=Path, default=REPO_DIR / "domains")
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "results" / "nyan1308" / "boundaries")
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = run_test(
        args.domain_file, args.domains_dir, groups=GROUPS,
        n_permutations=args.n_permutations, seed=args.seed,
    )
    write_tsv(rows, args.output_dir / "nyan1308_boundary_strength_test.tsv")

    print(f"\n{args.n_permutations} permutations, seed={args.seed}")
    for group in dict.fromkeys(r["group"] for r in rows):
        for side in ("left", "right"):
            for statistic in ("level", "jump"):
                group_rows = [r for r in rows if r["group"] == group and r["side"] == side
                              and r["statistic"] == statistic]
                best = min(group_rows, key=lambda r: r["p_value_ge_observed"])
                print(f"  {group:20} {side:5} {statistic:5}  smallest p at position "
                      f"{best['position']:2d}: observed={best['observed']:.1f} "
                      f"null_p95={best['null_p95']:.1f} p={best['p_value_ge_observed']:.4f}")


if __name__ == "__main__":
    main()
