# Laminar Family Analysis — Scripts Guide

## Overview

This directory contains Python scripts for analyzing constituency domains via **laminar family enumeration**. Given a set of observed domain spans over a planar morphosyntactic template, the analysis computes ALL maximal laminar families and tests three hypotheses about constituency structure.

**Key script**: `analysis/laminar_analysis.py` — does all the heavy lifting.

**Paths and commands in this file are relative to `NonCollaborative/`**, which
is where they are meant to be run from.

The charts are drawn by the `planarsviz` R package, which reads an exported
data bundle rather than re-deriving anything — see "Output" below for the two
commands. The bundle's contract is `r/planarsviz/inst/data-contract.md`.

## What is a Laminar Family?

A laminar family is a collection of spans where every pair is either:
- **Nested** (one contains the other), or
- **Disjoint** (they share no positions)

No partial overlaps are allowed. A laminar family induces a rooted
containment tree once a root span is supplied; without a root, it may be a
forest.

Laminar families are the right mathematical object for testing three hypotheses from Good's draft on Chichewa:

1. **Tree hypothesis** — Do all constituency diagnostics nest within each other?
2. **Morphosyntax/phonology divide hypothesis** — Are conflicts between domain types but not within them?
3. **Word hypothesis** — Do diagnostics converge on a consistently small word span?

## Algorithm: Maximal Laminar Family Enumeration

### Four-Phase Approach

**Phase 1: Conflict detection** (O(n²))
- For every pair of observed spans, classify as:
  - `nested` — compatible, can coexist
  - `disjoint` — compatible, can coexist
  - `conflict` — partial overlap, CANNOT coexist
- Build a **conflict graph**: nodes = spans, edges = conflicting pairs

**Phase 2: Enumerate maximal independent sets** (Bron-Kerbosch algorithm)
- Each maximal independent set = one maximal laminar family
- A maximal independent set is a set of mutually compatible spans that cannot be extended
- Output: all distinct maximal families

**Phase 3: Tree construction** (O(n²) per family)
- For each family, build parent map: each span's parent = smallest span that properly contains it
- Output: proper branching trees (Newick format)

**Phase 4: Analysis**
- Number of families → quantitative test of Tree hypothesis
  - 1 family = perfect nesting (strong support)
  - N families = N valid interpretations of the data
- Spans in all families → structurally robust word-domain candidates
- Conflict patterns → test of morphosyntax/phonology divide

## How to Run

### Input

Domain span TSVs live in `domains/`, named `domains_{lang_id}.tsv`, with these
six columns:

```
Test_Labels	Domain_Type	Left_Edge	Right_Edge	Size	Notes
FreeOccurrence-Minimal-AFF/IMP2s	length	10	17	8
FreeOccurrence-Maximal-AFF/IMP2s	length	9	17	9
...
```

Each row is one span from one test. Loading it (`load_spans()`):

- `Size` must equal `Right_Edge - Left_Edge + 1`, or the load fails outright.
- Rows whose `Test_Labels` starts with `#` are dropped — the `#DummyRoot`
  placeholder convention in the CCDB data.
- Size-1 spans are dropped: one position cannot be a domain.
- Rows with the same `[Left_Edge, Right_Edge]` become one `Span`, which keeps
  every contributing test label and every domain type involved.

### Running

```bash
python scripts/analysis/laminar_analysis.py
```

from `NonCollaborative/`. It takes no arguments: it prints the four-phase
report for nyan1308 — pooled, then one domain type at a time, then the three
bundles. For a different file or subset, call `main()` from Python:

```python
import sys; sys.path.insert(0, "scripts/analysis")
from laminar_analysis import main
result = main(domain_file="domains_arao1248.tsv", show_trees=False)
result["n_families"]
```

`main()` writes nothing to disk. It returns `spans`, `adjacency`, `families`,
`span_family_count`, `n_families` and `truncated`.

## Output

**The console report** is the whole of this script's own output: conflict
counts and which pairs conflict, the family count, each family's tree (up to
`max_trees_to_show`), and the span-occurrence table — which spans appear in
how many families, with the ones in *all* families marked. A span in every
family is structurally robust; a span in few is contingent on how conflicts
elsewhere get resolved.

**The charts** come from somewhere else. The analysis exports a data bundle
and the `planarsviz` R package draws from it:

```bash
python scripts/analysis/export_planarsviz_data.py \
  --domain-file domains/domains_nyan1308.tsv \
  --output-dir results/planarsviz --language-name Chichewa

Rscript scripts/render_planarsviz.R \
  --bundle results/planarsviz/nyan1308 --output results
```

Until the 2026-09-20 cutover, `laminar_analysis.py` wrote the R scripts for
those charts itself. It no longer does: the generators were removed and the
scripts they wrote are archived in `OlderFiles/planarsviz_superseded/`,
where the porting checks still run them to prove the package draws the same
thing. `docs/planarsviz_charts.md` catalogues every chart;
`results/visualizations.md` says what each one shows.

## Key Functions in `laminar_analysis.py`

- `load_domain_dataframe()` — read and clean the TSV, one row per test, each
  keeping its own `Domain_Type`. Use this when you need the per-row labels —
  a permutation test over which label sits on which row, say.
- `aggregate_spans()` — turn those rows into unique `Span`s.
- `load_spans()` — the two above in sequence, with an optional domain-type
  subset in between. The usual entry point.
- `classify_pair()` / `find_conflicts()` — classify span pairs as
  nested/disjoint/conflict; build the conflict graph
- `enumerate_maximal_laminar_families()` — all maximal laminar families, via
  `_bron_kerbosch()` (maximal independent sets of the conflict graph)
- `build_parent_map()` / `get_children()` — tree construction
- `span_to_newick()` — recursive Newick encoder (proper branching trees)
- `select_representative_families()` — greedy-coverage pick of k structurally
  diverse families, ties broken toward consensus. The exporter calls it for
  the exemplary-tree charts.
- `OVERLAY_GROUPS` — one entry per domain type: which types, what colour, and
  the short id its charts are named after. The exporter reads it.

The conflict-groups, four-trees, frequency-tree and span charts never had a
committed generator at all; their family-selection rules were recovered from
the archived scripts themselves and now live in the exporter — see
`docs/PLAN_planarsviz_library.md` §4.1.

## Troubleshooting

**"No maximal families found"**
- Check the TSV has `Left_Edge` and `Right_Edge` columns with real values
- Check at least one span survives the load: size-1 spans and `#`-prefixed
  rows are both dropped, so a file of only those loads to nothing

**"Size mismatch in ..."**
- `Size` must equal `Right_Edge - Left_Edge + 1` on every row. The loader
  refuses the file rather than guessing, and names the offending rows.

**"Only 1 family (but I expected conflicts)"**
- All observed spans are mutually compatible — perfect tree support
- This is actually strong support for the Tree hypothesis!

**A chart won't render**
- `scripts/render_planarsviz.R` installs the package into a temporary library
  itself, so there is no install step to remember — but the package's own
  dependencies must be there. They are listed in `r/planarsviz/DESCRIPTION`;
  the tree charts also need `ape` and `ggtree`, under `Suggests` because the
  other charts do not.
- Run it from `NonCollaborative/`, and make sure the bundle exists: the
  renderer draws from `results/planarsviz/<dataset>/`, not from the TSV.

## See Also

- `scripts/INDEX.md` — every script under `analysis/`, `verification/`,
  `exploratory/` and `planarsviz_checks/`, one entry each
- `results/visualizations.md` — what each artifact in `results/` shows and
  how to make it again
- `docs/planarsviz_charts.md` — the chart catalogue: every chart the
  package draws, its call, options and canvas
- `docs/VERIFICATION.md` — the two independent algorithms that both
  confirm 69 maximal families for nyan1308
- `scripts/exploratory/treeTraversal.py` — the earlier enumerator this replaced
  (slower, and undercounts: 16 families where the correct answer is 69)
- `results/laminar-families/nyan1308_laminar_analysis.md` — a written summary from
  2026-04-18, not generated by anything
- Good (draft) — "Domains of linearization, constituency, and wordhood in Chichewa"
