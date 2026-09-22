"""Exploratory -- describe the fragmented covering max_fragmentation_search.py
finds: an ASCII bracket diagram, plus a look at whether the conflict graph is
one big tangle or several smaller independent clusters (the latter would
explain a high family count combinatorially: independent clusters MULTIPLY
their own option counts together).

The covering hardcoded below is the 1238-family one found at the OLD, wrong
layer count of 25. nyan1308 has 26 domains, and the search was corrected to
match on 2026-09-22, so re-run the search and paste its new best in before
reading anything into this at 26 layers.
"""
import sys
sys.path.insert(0, "/Users/jcgood/gitrepos/planars/NonCollaborative/scripts/analysis")
from laminar_analysis import Span, find_conflicts, enumerate_maximal_laminar_families

N_POSITIONS = 22
SPANS = [(1, 5), (1, 17), (1, 19), (1, 21), (1, 22), (2, 3), (2, 7), (2, 18), (3, 4), (5, 8),
         (6, 9), (9, 12), (9, 16), (9, 19), (9, 21), (9, 22), (10, 13), (10, 17), (11, 14),
         (12, 15), (13, 17), (15, 18), (19, 21), (19, 22), (20, 22)]
spans = [Span(l, r) for l, r in SPANS]

print(f"{len(spans)} spans total (including the fixed root 1-22)\n")

print("=== ASCII bracket diagram (sorted by left edge, then size) ===")
print("    " + "".join(str((p % 10)) for p in range(1, N_POSITIONS + 1)))
for s in sorted(spans, key=lambda s: (s.left, s.right)):
    row = ["."] * N_POSITIONS
    row[s.left - 1] = "["
    row[s.right - 1] = "]"
    for p in range(s.left, s.right - 1):
        row[p] = "-"
    print(f"{s.left:2d}-{s.right:<2d} " + "".join(row))

adjacency = find_conflicts(spans)
print(f"\n=== Conflict graph ===")
print(f"{len(adjacency)}/{len(spans)} spans are in at least one conflict")
n_conflict_pairs = sum(len(v) for v in adjacency.values()) // 2
print(f"{n_conflict_pairs} conflicting pairs total (out of {len(spans)*(len(spans)-1)//2} possible pairs)")

# connected components of the conflict graph (root excluded -- it conflicts
# with nothing, it's compatible with everything by construction)
non_root = [s for s in spans if not (s.left == 1 and s.right == N_POSITIONS)]
seen = set()
components = []
for s in non_root:
    if s in seen:
        continue
    stack = [s]
    comp = set()
    while stack:
        cur = stack.pop()
        if cur in comp:
            continue
        comp.add(cur)
        for nb in adjacency.get(cur, ()):
            if nb not in comp:
                stack.append(nb)
    seen |= comp
    components.append(comp)

# spans touching nothing (isolated -- always in, compatible with everyone)
isolated = [s for s in non_root if not adjacency.get(s)]
conflicted_components = [c for c in components if len(c) > 1]

print(f"\n{len(isolated)} spans conflict with nothing (always included, free of charge): "
      f"{sorted((s.left, s.right) for s in isolated)}")
print(f"{len(conflicted_components)} separate conflict clusters (connected components with >1 span):")
for i, comp in enumerate(sorted(conflicted_components, key=len, reverse=True), 1):
    comp_spans = sorted((s.left, s.right) for s in comp)
    sub_adjacency = {s: {n for n in adjacency.get(s, ()) if n in comp} for s in comp}
    sub_families, trunc = enumerate_maximal_laminar_families(list(comp), sub_adjacency, N_POSITIONS)
    print(f"  cluster {i}: {len(comp)} spans, {len(sub_families)} ways to resolve it on its own "
          f"{'(TRUNCATED)' if trunc else ''} -- {comp_spans}")

total, truncated = enumerate_maximal_laminar_families(spans, adjacency, N_POSITIONS)
print(f"\nFull family count: {len(total)}{' (TRUNCATED)' if truncated else ''}")
product_of_clusters = 1
for comp in conflicted_components:
    sub_adjacency = {s: {n for n in adjacency.get(s, ()) if n in comp} for s in comp}
    sub_families, _ = enumerate_maximal_laminar_families(list(comp), sub_adjacency, N_POSITIONS)
    product_of_clusters *= len(sub_families)
print(f"Product of each cluster's own option count: {product_of_clusters} "
      f"(will roughly match the full count if clusters are truly independent of each other)")
