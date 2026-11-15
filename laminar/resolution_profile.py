"""Resolution across every stretch of the planar structure, real domain or
not, and where it jumps. A companion to resolution_test.py, which tests one
region chosen in advance; this one looks at all of them, to find where
structure starts or stops (Jeff, 2026-11-15).

A stretch is any [a, b] with 1 <= a < b <= N: the 26 domains the tests found
in nyan1308 are stretches, and so are the ~200 that no test picks out (the
"logical" ones). For each stretch, averaged over the trees (maximal laminar
families):
  - resolution: the domains lying strictly inside it over the most it could
    hold. A stretch of k positions holds at most k - 2 domains besides
    itself (resolution is undefined for k = 2). The stretch itself is left
    out so that a real domain and a logical stretch of the same positions
    are measured alike; whether it is a domain is reported separately
    (is_domain, tree_share). This is Colless's (1980) consensus index
    applied to a part of the tree, as in resolution_test.py.
  - crossing: domains that overlap the stretch without nesting with it. A
    stretch nothing crosses is compatible with every tree, which is the
    character-compatibility idea (Le Quesne 1969; Estabrook, Johnson &
    McMorris 1976) turned round: a logical stretch with no crossing is a
    domain the tests would allow but none found.
Both are compared with span_placement_test.py's null (the same span lengths
at random positions, the trees rebuilt), so a value is read against what a
stretch of that size and place gets by chance; edge stretches hold fewer
random domains than middle ones.

Discontinuities: a stretch grown by one position (right edge out, or left
edge out) is compared with the one it grew from. `excess_change` is the
observed change in resolution less the null's average change for the same
step, so a large negative value is a position whose addition makes a
stretch much flatter than chance would. The jumps file lists every step;
the positions file averages them by the position added and the side it was
added on, which is where a boundary would show as a run of large values.

Outputs (under results/<dataset>/counts-and-chance/ by default):
  <dataset>_resolution_profile.tsv    -- one row per stretch
  <dataset>_resolution_jumps.tsv      -- one row per one-position step
  <dataset>_resolution_positions.tsv  -- steps averaged by position added

Usage (from anywhere):
  python -m laminar.resolution_profile
  python -m laminar.resolution_profile --n-permutations 1000
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from laminar.datasets import add_dataset_arguments, resolve_dataset_arguments
from laminar.laminar_analysis import enumerate_maximal_laminar_families, find_conflicts, load_spans
from laminar.span_placement_test import random_replicate


def family_grids(families, n_positions: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean over `families` of, for every stretch [a, b] (index [a-1, b-1]):
    domains strictly inside, domains crossing, and whether it is a domain."""
    pos = np.arange(1, n_positions + 1)
    a = pos[:, None, None]
    b = pos[None, :, None]
    inside = np.zeros((n_positions, n_positions))
    crossing = np.zeros((n_positions, n_positions))
    present = np.zeros((n_positions, n_positions))
    for family in families:
        left = np.array([s.left for s in family])[None, None, :]
        right = np.array([s.right for s in family])[None, None, :]
        within = (left >= a) & (right <= b)
        same = (left == a) & (right == b)
        inside += (within & ~same).sum(axis=2)
        present += same.any(axis=2)
        crossing += (((left < a) & (right >= a) & (right < b))
                     | ((left > a) & (left <= b) & (right > b))).sum(axis=2)
    n = len(families)
    return inside / n, crossing / n, present / n


def resolution_grid(inside: np.ndarray, n_positions: int) -> np.ndarray:
    size = np.arange(n_positions)[None, :] - np.arange(n_positions)[:, None] + 1
    with np.errstate(divide="ignore", invalid="ignore"):
        res = inside / (size - 2)
    res[size < 3] = np.nan
    return res


def stretches(n_positions: int):
    for a in range(1, n_positions + 1):
        for b in range(a + 1, n_positions + 1):
            yield a, b


def run_profile(domain_file: str, domains_dir: Path, n_permutations: int = 5000, seed: int = 0,
                n_positions: int | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    spans, n_positions = load_spans(domain_file, str(domains_dir), n_positions=n_positions)
    families, truncated = enumerate_maximal_laminar_families(spans, find_conflicts(spans), n_positions)
    if truncated:
        raise RuntimeError("The observed family enumeration reached MAX_FAMILIES.")
    inside, crossing, present = family_grids(families, n_positions)
    res = resolution_grid(inside, n_positions)
    tests = {(s.left, s.right): s.convergence for s in spans}

    rng = np.random.default_rng(seed)
    sizes = [s.size for s in spans]
    null_res = np.empty((n_permutations, n_positions, n_positions))
    null_cross = np.empty((n_permutations, n_positions, n_positions))
    n_truncated = 0
    for i in range(n_permutations):
        replicate = random_replicate(sizes, n_positions, rng)
        fams, trunc = enumerate_maximal_laminar_families(replicate, find_conflicts(replicate), n_positions)
        n_truncated += trunc
        r_inside, r_cross, _ = family_grids(fams, n_positions)
        null_res[i] = resolution_grid(r_inside, n_positions)
        null_cross[i] = r_cross

    profile = []
    for a, b in stretches(n_positions):
        i, j = a - 1, b - 1
        row = {"left": a, "right": b, "size": b - a + 1,
               "is_domain": (a, b) in tests, "tests": tests.get((a, b), 0),
               "tree_share": round(float(present[i, j]), 4)}
        if b - a + 1 >= 3:
            nr = null_res[:, i, j]
            row.update(resolution=round(float(res[i, j]), 4),
                       null_resolution_mean=round(float(nr.mean()), 4),
                       null_resolution_lo=round(float(np.percentile(nr, 5)), 4),
                       null_resolution_hi=round(float(np.percentile(nr, 95)), 4),
                       p_resolution_le=round(float(np.mean(nr <= res[i, j] + 1e-12)), 4),
                       p_resolution_ge=round(float(np.mean(nr >= res[i, j] - 1e-12)), 4))
        else:
            row.update(resolution="", null_resolution_mean="", null_resolution_lo="",
                       null_resolution_hi="", p_resolution_le="", p_resolution_ge="")
        nc = null_cross[:, i, j]
        row.update(crossing=round(float(crossing[i, j]), 3),
                   null_crossing_mean=round(float(nc.mean()), 3),
                   p_crossing_le=round(float(np.mean(nc <= crossing[i, j] + 1e-12)), 4),
                   n_truncated=n_truncated, n_permutations=n_permutations, seed=seed)
        profile.append(row)

    jumps = []
    for a, b in stretches(n_positions):
        for side, (a2, b2), added in (("right", (a, b + 1), b + 1), ("left", (a - 1, b), a - 1)):
            if not (1 <= a2 and b2 <= n_positions) or b - a + 1 < 3:
                continue
            i, j, i2, j2 = a - 1, b - 1, a2 - 1, b2 - 1
            obs = res[i2, j2] - res[i, j]
            null = float(np.mean(null_res[:, i2, j2] - null_res[:, i, j]))
            jumps.append({"from": f"{a}-{b}", "to": f"{a2}-{b2}", "side": side, "added": added,
                          "resolution_change": round(float(obs), 4),
                          "null_change": round(null, 4),
                          "excess_change": round(float(obs - null), 4),
                          "crossing_change": round(float(crossing[i2, j2] - crossing[i, j]), 3)})

    positions = []
    for side in ("right", "left"):
        for p in range(1, n_positions + 1):
            steps = [r for r in jumps if r["side"] == side and r["added"] == p]
            if not steps:
                continue
            excess = np.array([r["excess_change"] for r in steps])
            positions.append({"side": side, "added": p, "n_steps": len(steps),
                              "mean_excess_change": round(float(excess.mean()), 4),
                              "min_excess_change": round(float(excess.min()), 4),
                              "mean_crossing_change": round(float(np.mean([r["crossing_change"] for r in steps])), 3)})
    return profile, jumps, positions


def write_tsv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_dataset_arguments(parser, "counts-and-chance", groupings=False)
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run = resolve_dataset_arguments(args, "counts-and-chance")
    profile, jumps, positions = run_profile(args.domain_file, args.domains_dir,
                                            n_permutations=args.n_permutations, seed=args.seed,
                                            n_positions=run.n_positions)
    stem = run.output_dir / run.dataset
    write_tsv(Path(f"{stem}_resolution_profile.tsv"), profile)
    write_tsv(Path(f"{stem}_resolution_jumps.tsv"), jumps)
    write_tsv(Path(f"{stem}_resolution_positions.tsv"), positions)
    print(f"{len(profile)} stretches, {len(jumps)} steps, written to {run.output_dir}")


if __name__ == "__main__":
    main()
