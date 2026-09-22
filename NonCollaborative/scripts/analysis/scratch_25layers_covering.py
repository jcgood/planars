"""SCRATCH -- not part of the project, not exported yet.

Jeff's question: given 25 "layers" (spans) over the Chichewa planar
structure (n_positions = 22, matching nyan1308), one of which must be the
full-span root [1-22] and the other 24 free to vary in size and placement:

  (A) What's the most laminarly FRAGMENTED covering achievable with those
      25 layers -- i.e. how high can the maximal-laminar-family count go?
  (B) Is 69 (nyan1308's real, observed count, from 26 domains not 25 --
      see NOTE below) more or less than "chance" would produce for 25
      arbitrary layers?

Both questions reuse the SAME validated machinery the real analysis uses
(laminar_analysis.find_conflicts / enumerate_maximal_laminar_families) --
this script is a different way of feeding it inputs, not a new algorithm.

NOTE ON "25": nyan1308 actually has 26 distinct observed domains (one of
which already is the full [1-22] span -- synthetic_root is False for it),
producing the 69 families the talk reports. Jeff said "25 layers, like we
have" -- read here as 25 TOTAL layers (1 fixed root + 24 free), one less
than nyan1308's real 26, not as a typo for 26. If that's wrong, the N_FREE
constant below is the one knob to change.

(B)'s null is DELIBERATELY more naive than span_placement_test.py's: that
test holds each span's real LENGTH fixed and randomizes only position (a
"given these exact sizes, does position matter" question). This one
randomizes BOTH size and position -- every legal size>=2 interval is
equally likely -- because "arbitrary" is what Jeff asked for: a baseline
with no information at all about what sizes real linguistic domains have,
a strictly weaker/more permissive null than the one already in the
project.

(A) has no closed-form computed here -- the conflict graph induced by
crossing intervals is a circle graph, and the maximum number of maximal
independent sets a 24-vertex circle graph realizable this way can have
isn't something I derived analytically. Handled empirically instead: a
few hand-built "maximally crossing" candidates, plus randomized local
search using the real family-count function as the objective. Whatever
this finds is a LOWER BOUND on the true maximum (search found at least
this many), not a certified answer.

MAX_FAMILIES (laminar_analysis.py's module-level safeguard, 1000) is
raised here via monkeypatch -- fully arbitrary random intervals cross far
more chaotically than real linguistic domains do, and 1000 turned out to
be too low to let the (B) simulation run without truncation. Only ever
touches this script's own import of the module, not the committed file.

Usage:
  python laminar_25layers.py
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

PROJECT_ANALYSIS_DIR = Path("/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis")
sys.path.insert(0, str(PROJECT_ANALYSIS_DIR))

import laminar_analysis  # noqa: E402
laminar_analysis.MAX_FAMILIES = 50_000  # see module docstring above

from laminar_analysis import Span, find_conflicts, enumerate_maximal_laminar_families  # noqa: E402

N_POSITIONS = 22
N_FREE = 24  # + the fixed root = 25 total layers
ROOT = Span(1, N_POSITIONS)

ALL_LEGAL_INTERVALS = [
    (l, r)
    for l in range(1, N_POSITIONS + 1)
    for r in range(l + 1, N_POSITIONS + 1)  # size >= 2, matches the real pipeline's own filter
    if not (l == 1 and r == N_POSITIONS)     # excludes the root itself from the free pool
]


def family_count(spans: list[Span]) -> tuple[int, bool]:
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, N_POSITIONS)
    return len(families), truncated


def random_arbitrary_spans(rng: random.Random) -> list[Span]:
    """N_FREE distinct legal intervals, uniformly at random over ALL legal
    size>=2 intervals (not just the real data's own length multiset) --
    the "arbitrary layers" null for question (B).
    """
    chosen = rng.sample(ALL_LEGAL_INTERVALS, N_FREE)
    return [ROOT] + [Span(l, r) for l, r in chosen]


# ══════════════════════════════════════════════════════════════════════════
# (B) Is 69 more or less than chance for 25 fully arbitrary layers?
# ══════════════════════════════════════════════════════════════════════════

def run_chance_baseline(n_draws: int, seed: int = 0):
    rng = random.Random(seed)
    counts = []
    n_truncated = 0
    start = time.time()
    for i in range(n_draws):
        spans = random_arbitrary_spans(rng)
        count, truncated = family_count(spans)
        if truncated:
            n_truncated += 1
        counts.append(count)
        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{n_draws} draws, {time.time() - start:.0f}s elapsed", file=sys.stderr)
    counts.sort()
    return counts, n_truncated


def summarize_chance_baseline(counts: list[int], n_truncated: int, observed: int = 69):
    n = len(counts)
    mean = sum(counts) / n

    def percentile(p):
        idx = min(n - 1, int(p / 100 * n))
        return counts[idx]

    p_le = sum(1 for c in counts if c <= observed) / n
    print(f"\n=== (B) Chance baseline: {n} draws of 25 fully arbitrary layers "
          f"(1 fixed root + {N_FREE} random size/position spans) ===")
    if n_truncated:
        print(f"  WARNING: {n_truncated}/{n} draws hit the raised MAX_FAMILIES cap "
              f"({laminar_analysis.MAX_FAMILIES}) and are undercounted.")
    print(f"  mean family count:   {mean:.1f}")
    print(f"  min / p05 / median / p95 / max: "
          f"{counts[0]} / {percentile(5)} / {percentile(50)} / {percentile(95)} / {counts[-1]}")
    print(f"  observed (nyan1308, real data, pooled): {observed}")
    print(f"  P(chance <= {observed}) = {p_le:.4f}  "
          f"({'unusually LAMINAR/tree-like' if p_le < 0.05 else 'not distinguishable from chance'} "
          f"at the conventional 0.05 threshold, same p_value_le_observed convention as "
          f"span_placement_test.py / class_fragmentation_test.py)")


# ══════════════════════════════════════════════════════════════════════════
# (A) Most laminarly fragmented covering achievable with 25 layers
# ══════════════════════════════════════════════════════════════════════════

def ladder_candidate(window: int, step: int) -> list[Span]:
    """A sliding-window "ladder" of overlapping intervals -- a classic way
    to maximize pairwise crossings: consecutive windows of fixed size that
    each cross the next (share some but not all positions). Returns as many
    as fit before running past N_POSITIONS, up to N_FREE.
    """
    spans = []
    left = 1
    while left + window - 1 <= N_POSITIONS and len(spans) < N_FREE:
        spans.append(Span(left, left + window - 1))
        left += step
    return spans


def two_scale_ladder() -> list[Span]:
    """Two interleaved ladders at different window sizes -- crosses not
    just within each ladder but across the two scales too, on the theory
    that mixing scales creates more distinct conflict-graph structure than
    one uniform ladder can.
    """
    a = ladder_candidate(window=8, step=1)
    b = ladder_candidate(window=5, step=2)
    combined = list(dict.fromkeys(a + b))  # dedupe, preserve order
    return combined[:N_FREE]


def random_restart_search(rng: random.Random, n_restarts: int, n_steps: int):
    """Randomized local search: start from a random arbitrary configuration,
    repeatedly try swapping ONE free span for a new random legal interval,
    keep the swap if it doesn't lower the family count (sideways moves
    allowed, to escape flat local optima), track the best seen.
    """
    best_count = -1
    best_spans: list[Span] | None = None
    for restart in range(n_restarts):
        free = list(rng.sample(ALL_LEGAL_INTERVALS, N_FREE))
        current, _ = family_count([ROOT] + [Span(l, r) for l, r in free])
        for _ in range(n_steps):
            i = rng.randrange(N_FREE)
            candidate_lr = rng.choice(ALL_LEGAL_INTERVALS)
            trial = free.copy()
            trial[i] = candidate_lr
            if len(set(trial)) < N_FREE:
                continue  # would collide with an existing span; skip
            trial_count, truncated = family_count([ROOT] + [Span(l, r) for l, r in trial])
            if truncated:
                continue
            if trial_count >= current:
                free, current = trial, trial_count
        if current > best_count:
            best_count = current
            best_spans = [ROOT] + [Span(l, r) for l, r in free]
        print(f"  restart {restart + 1}/{n_restarts}: reached {current}, best so far {best_count}",
              file=sys.stderr)
    return best_count, best_spans


def run_fragmentation_search():
    print(f"\n=== (A) Most laminarly fragmented covering search, "
          f"{N_FREE} free spans + 1 root over {N_POSITIONS} positions ===")

    candidates = {
        "single ladder (window=8, step=1)": ladder_candidate(window=8, step=1),
        "single ladder (window=4, step=1)": ladder_candidate(window=4, step=1),
        "two-scale ladder": two_scale_ladder(),
    }
    for name, free_spans in candidates.items():
        if len(free_spans) < N_FREE:
            print(f"  {name}: only produced {len(free_spans)}/{N_FREE} spans, padding with random legal ones")
            rng = random.Random(0)
            pool = [s for s in ALL_LEGAL_INTERVALS if Span(*s) not in free_spans]
            while len(free_spans) < N_FREE:
                free_spans.append(Span(*rng.choice(pool)))
        count, truncated = family_count([ROOT] + free_spans[:N_FREE])
        flag = " (TRUNCATED, undercount)" if truncated else ""
        print(f"  {name}: {count} families{flag}")

    print("  randomized local search (60 restarts x 400 steps)...", file=sys.stderr)
    rng = random.Random(1)
    best_count, best_spans = random_restart_search(rng, n_restarts=60, n_steps=400)
    print(f"\n  best found by local search: {best_count} families")
    if best_spans:
        ordered = sorted(best_spans, key=lambda s: (s.left, s.right))
        print(f"  spans: {[(s.left, s.right) for s in ordered]}")
    print(f"\n  compare: nyan1308's real 26-domain data (69 families) vs. this search's "
          f"best {N_FREE}-free-span construction ({best_count} families)")


if __name__ == "__main__":
    run_fragmentation_search()
    counts, n_truncated = run_chance_baseline(n_draws=3000, seed=0)
    summarize_chance_baseline(counts, n_truncated)
