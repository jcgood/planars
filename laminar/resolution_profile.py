"""Resolution and conflict density across every stretch of the planar
structure, real domain or not, and where they jump. A companion to resolution_test.py, which tests one
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
  - conflict density (plan decision 11): of the pairs of domains lying
    within the stretch (itself included), the share that conflict -- the
    density of the conflict graph on them. Computed on the distinct spans,
    not the trees: it measures how far the tests' domains disagree about
    one tree there, which a per-tree average such as resolution cannot see.
    Undefined under two domains.
All three are compared with span_placement_test.py's null (the same span
lengths at random positions, the trees rebuilt), so a value is read against
what a stretch of that size and place gets by chance; edge stretches hold
fewer random domains than middle ones.

Quantal or gradual (Jeff, 2026-11-15; we do not assume where words are):
the hypothesis is that conflict changes in jumps at some edges, not
gradually. It is measured at the junctures, counting each conflict once. A
conflicting pair lies over its smallest common stretch (leftmost left edge
to rightmost right edge), and spans every juncture inside it; a juncture's
`share` is the conflicting pairs spanning it over all conflicting pairs, so
the null (whose random spans conflict more often) is compared on the same
scale. A wall is a position where the share changes sharply from the
juncture before it to the one after: `change` at a position, less the
null's mean change there (`excess_change`), which removes what geometry
gives (edge junctures are spanned less by chance). The quantal statistic is
the largest |excess_change| over the positions, against the largest in each
null replicate scored the same way (a maximum, so it is corrected for
looking at every position); p_largest_ge is the share of replicates whose
largest is at least as large. Per-position p_abs_excess_ge values are
uncorrected.

The per-step `marginal_conflict` in the jumps file (of the pairs a
one-position step adds, the share that conflict) is descriptive only: a
conflict is counted again in every stretch that first takes it in, and most
steps add one or two pairs, so it is not a test. (A Gini over those steps
was the first quantal test, 2026-11-15, and was dropped for that reason;
laminar/INDEX.md.)

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
  <dataset>_conflict_junctures.tsv    -- one row per juncture: conflicting
                                         pairs spanning it, and the change
                                         passing the position to its left
  <dataset>_conflict_quantal.tsv      -- one row: the largest change
                                         against the null's largest
The profile's conflict columns are n_domains, conflict_density,
null_conflict_density_mean, p_conflict_density_ge; the jumps file's are
added_pairs, marginal_conflict, null_marginal_mean, excess_marginal; the
positions file's are n_steps_scored and the mean, min and max
excess_marginal.

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


def conflict_matrix(spans) -> np.ndarray:
    """m x m: True where two spans cross (classify_pair's 'conflict')."""
    left = np.array([s.left for s in spans])
    right = np.array([s.right for s in spans])
    one_way = ((left[:, None] < left[None, :]) & (left[None, :] <= right[:, None])
               & (right[:, None] < right[None, :]))
    return one_way | one_way.T


def conflict_grids(spans, n_positions: int) -> tuple[np.ndarray, np.ndarray]:
    """For every stretch [a, b] (index [a-1, b-1]): the number of domains
    lying within it, the stretch itself included, and the number of pairs of
    those domains that conflict. Computed on the spans, not the trees."""
    pos = np.arange(1, n_positions + 1)
    left = np.array([s.left for s in spans])[None, None, :]
    right = np.array([s.right for s in spans])[None, None, :]
    within = ((left >= pos[:, None, None]) & (right <= pos[None, :, None])).astype(np.int64)
    conflicts = conflict_matrix(spans).astype(np.int64)
    n_domains = within.sum(axis=2)
    n_conflicts = np.einsum("abs,st,abt->ab", within, conflicts, within) // 2
    return n_domains, n_conflicts


def pairs(n_domains: np.ndarray) -> np.ndarray:
    return n_domains * (n_domains - 1) // 2


def density_grid(n_domains: np.ndarray, n_conflicts: np.ndarray) -> np.ndarray:
    """Conflict density: conflicting pairs over all pairs; NaN under 2 domains."""
    p = pairs(n_domains)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(p > 0, n_conflicts / np.where(p > 0, p, 1), np.nan)


def marginal_conflict(n_domains: np.ndarray, n_conflicts: np.ndarray, old: tuple, new: tuple):
    """Of the pairs a step adds (each involving at least one newly included
    domain), the share that conflict. Works on a stack of grids too (leading
    axis = replicates). NaN where the step adds no pair."""
    added_pairs = pairs(n_domains[..., new[0], new[1]]) - pairs(n_domains[..., old[0], old[1]])
    added_conflicts = n_conflicts[..., new[0], new[1]] - n_conflicts[..., old[0], old[1]]
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(added_pairs > 0, added_conflicts / np.where(added_pairs > 0, added_pairs, 1), np.nan)


def juncture_counts(spans, n_positions: int) -> tuple[np.ndarray, int]:
    """For each juncture j|j+1 (index j-1, j = 1 .. N-1): the conflicting
    pairs whose smallest common stretch -- from the leftmost of the two left
    edges to the rightmost of the two right edges -- spans it. Each pair is
    counted once per juncture, however many stretches hold it. Also returns
    the number of conflicting pairs."""
    i, j = np.nonzero(np.triu(conflict_matrix(spans), k=1))
    left = np.array([s.left for s in spans])
    right = np.array([s.right for s in spans])
    hull_left = np.minimum(left[i], left[j])
    hull_right = np.maximum(right[i], right[j])
    junctures = np.arange(1, n_positions)[:, None]
    counts = ((hull_left[None, :] <= junctures) & (hull_right[None, :] > junctures)).sum(axis=1)
    return counts, len(i)


def juncture_shares(counts: np.ndarray, n_pairs) -> np.ndarray:
    """Counts over the number of conflicting pairs (last axis = junctures);
    NaN where there are none. Works on a stack (leading axis = replicates,
    `n_pairs` one per replicate)."""
    counts = np.asarray(counts, dtype=float)
    total = np.asarray(n_pairs, dtype=float)[..., None]
    return np.where(total > 0, counts / np.where(total > 0, total, 1), np.nan)


def juncture_test(spans, n_positions: int, null_junct: np.ndarray, null_pairs: np.ndarray,
                  n_permutations: int, seed: int) -> tuple[list[dict], dict]:
    """Where conflict starts and stops: the share of conflicting pairs
    spanning each juncture, its change from one juncture to the next, and
    the largest such change against the null's largest (the quantal test).
    Replicates with no conflict have no shares and are left out."""
    counts, n_pairs = juncture_counts(spans, n_positions)
    share = juncture_shares(counts, n_pairs)
    null_share = juncture_shares(null_junct, null_pairs)
    null_share = null_share[~np.isnan(null_share[:, 0])]
    change = np.diff(share)
    null_change = np.diff(null_share, axis=1)
    null_change_mean = null_change.mean(axis=0)
    excess = change - null_change_mean
    null_excess = np.abs(null_change - null_change_mean)

    rows = []
    for k in range(n_positions - 1):
        ns = null_share[:, k]
        row = {"juncture": f"{k + 1}|{k + 2}", "left_position": k + 1,
               "conflicts": int(counts[k]), "share": round(float(share[k]), 4),
               "null_share_mean": round(float(ns.mean()), 4),
               "null_share_lo": round(float(np.percentile(ns, 5)), 4),
               "null_share_hi": round(float(np.percentile(ns, 95)), 4),
               "p_share_ge": round(float(np.mean(ns >= share[k] - 1e-12)), 4),
               "p_share_le": round(float(np.mean(ns <= share[k] + 1e-12)), 4)}
        if k == 0:
            row.update(position_passed="", change="", null_change_mean="", excess_change="", p_abs_excess_ge="")
        else:
            c = k - 1
            row.update(position_passed=k + 1, change=round(float(change[c]), 4),
                       null_change_mean=round(float(null_change_mean[c]), 4),
                       excess_change=round(float(excess[c]), 4),
                       p_abs_excess_ge=round(float(np.mean(null_excess[:, c] >= abs(excess[c]) - 1e-12)), 4))
        rows.append(row)

    largest = int(np.argmax(np.abs(excess)))
    null_max = null_excess.max(axis=1)
    observed = float(abs(excess[largest]))
    quantal = {"n_conflicting_pairs": n_pairs, "largest_excess_change": round(float(excess[largest]), 4),
               "at_position": largest + 2, "null_largest_mean": round(float(null_max.mean()), 4),
               "null_largest_hi": round(float(np.percentile(null_max, 95)), 4),
               "p_largest_ge": round(float(np.mean(null_max >= observed - 1e-12)), 4),
               "n_cliffs_beyond_null_largest_hi": int(np.sum(np.abs(excess) > np.percentile(null_max, 95))),
               "n_replicates_scored": len(null_share), "n_permutations": n_permutations, "seed": seed}
    return rows, quantal


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
                n_positions: int | None = None) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    spans, n_positions = load_spans(domain_file, str(domains_dir), n_positions=n_positions)
    families, truncated = enumerate_maximal_laminar_families(spans, find_conflicts(spans), n_positions)
    if truncated:
        raise RuntimeError("The observed family enumeration reached MAX_FAMILIES.")
    inside, crossing, present = family_grids(families, n_positions)
    res = resolution_grid(inside, n_positions)
    tests = {(s.left, s.right): s.convergence for s in spans}
    n_dom, n_conf = conflict_grids(spans, n_positions)
    dens = density_grid(n_dom, n_conf)

    rng = np.random.default_rng(seed)
    sizes = [s.size for s in spans]
    null_res = np.empty((n_permutations, n_positions, n_positions))
    null_cross = np.empty((n_permutations, n_positions, n_positions))
    null_dom = np.empty((n_permutations, n_positions, n_positions), dtype=np.int64)
    null_conf = np.empty((n_permutations, n_positions, n_positions), dtype=np.int64)
    null_junct = np.empty((n_permutations, n_positions - 1), dtype=np.int64)
    null_pairs = np.empty(n_permutations, dtype=np.int64)
    n_truncated = 0
    for i in range(n_permutations):
        replicate = random_replicate(sizes, n_positions, rng)
        fams, trunc = enumerate_maximal_laminar_families(replicate, find_conflicts(replicate), n_positions)
        n_truncated += trunc
        r_inside, r_cross, _ = family_grids(fams, n_positions)
        null_res[i] = resolution_grid(r_inside, n_positions)
        null_cross[i] = r_cross
        null_dom[i], null_conf[i] = conflict_grids(replicate, n_positions)
        null_junct[i], null_pairs[i] = juncture_counts(replicate, n_positions)
    null_dens = density_grid(null_dom, null_conf)

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
                   p_crossing_le=round(float(np.mean(nc <= crossing[i, j] + 1e-12)), 4))
        nd = null_dens[:, i, j]
        nd = nd[~np.isnan(nd)]
        row.update(n_domains=int(n_dom[i, j]))
        if np.isnan(dens[i, j]) or len(nd) == 0:
            row.update(conflict_density="", null_conflict_density_mean="", p_conflict_density_ge="")
        else:
            row.update(conflict_density=round(float(dens[i, j]), 4),
                       null_conflict_density_mean=round(float(nd.mean()), 4),
                       p_conflict_density_ge=round(float(np.mean(nd >= dens[i, j] - 1e-12)), 4))
        row.update(n_truncated=n_truncated, n_permutations=n_permutations, seed=seed)
        profile.append(row)

    jumps = []
    for a, b in stretches(n_positions):
        for side, (a2, b2), added in (("right", (a, b + 1), b + 1), ("left", (a - 1, b), a - 1)):
            if not (1 <= a2 and b2 <= n_positions) or b - a + 1 < 3:
                continue
            i, j, i2, j2 = a - 1, b - 1, a2 - 1, b2 - 1
            obs = res[i2, j2] - res[i, j]
            null = float(np.mean(null_res[:, i2, j2] - null_res[:, i, j]))
            row = {"from": f"{a}-{b}", "to": f"{a2}-{b2}", "side": side, "added": added,
                   "resolution_change": round(float(obs), 4),
                   "null_change": round(null, 4),
                   "excess_change": round(float(obs - null), 4),
                   "crossing_change": round(float(crossing[i2, j2] - crossing[i, j]), 3)}
            marg = float(marginal_conflict(n_dom, n_conf, (i, j), (i2, j2)))
            null_marg = marginal_conflict(null_dom, null_conf, (i, j), (i2, j2))
            defined = null_marg[~np.isnan(null_marg)]
            null_mean = float(defined.mean()) if len(defined) else float("nan")
            row["added_pairs"] = int(pairs(n_dom[i2, j2]) - pairs(n_dom[i, j]))
            if np.isnan(marg) or np.isnan(null_mean):
                row.update(marginal_conflict="", null_marginal_mean="", excess_marginal="")
            else:
                row.update(marginal_conflict=round(marg, 4),
                           null_marginal_mean=round(null_mean, 4),
                           excess_marginal=round(marg - null_mean, 4))
            jumps.append(row)

    junctures, quantal = juncture_test(spans, n_positions, null_junct, null_pairs, n_permutations, seed)

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
            scored = [r["excess_marginal"] for r in steps if r["excess_marginal"] != ""]
            positions[-1].update(
                n_steps_scored=len(scored),
                mean_excess_marginal=round(float(np.mean(scored)), 4) if scored else "",
                min_excess_marginal=round(float(np.min(scored)), 4) if scored else "",
                max_excess_marginal=round(float(np.max(scored)), 4) if scored else "")
    return profile, jumps, positions, junctures, quantal


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
    profile, jumps, positions, junctures, quantal = run_profile(
        args.domain_file, args.domains_dir, n_permutations=args.n_permutations, seed=args.seed,
        n_positions=run.n_positions)
    stem = run.output_dir / run.dataset
    write_tsv(Path(f"{stem}_resolution_profile.tsv"), profile)
    write_tsv(Path(f"{stem}_resolution_jumps.tsv"), jumps)
    write_tsv(Path(f"{stem}_resolution_positions.tsv"), positions)
    write_tsv(Path(f"{stem}_conflict_junctures.tsv"), junctures)
    write_tsv(Path(f"{stem}_conflict_quantal.tsv"), [quantal])
    print(f"{len(profile)} stretches, {len(jumps)} steps, written to {run.output_dir}")
    print(f"Quantal test: largest change in conflict share {quantal['largest_excess_change']} beyond chance, "
          f"passing position {quantal['at_position']}; chance's largest averages {quantal['null_largest_mean']} "
          f"(95th percentile {quantal['null_largest_hi']}), p = {quantal['p_largest_ge']}; "
          f"{quantal['n_cliffs_beyond_null_largest_hi']} changes beyond that percentile")


if __name__ == "__main__":
    main()
