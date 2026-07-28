# Laminar Family Analysis — Scripts Guide

## Overview

This directory contains Python scripts for analyzing constituency domains via **laminar family enumeration**. Given a set of observed domain spans over a planar morphosyntactic template, the analysis computes ALL maximal laminar families and tests three hypotheses about constituency structure.

**Key script**: `laminar_analysis.py` — does all the heavy lifting.

## What is a Laminar Family?

A laminar family is a collection of spans where every pair is either:
- **Nested** (one contains the other), or
- **Disjoint** (they share no positions)

No partial overlaps are allowed. Crucially, a laminar family IS a rooted tree — containment relationships define a unique valid hierarchy.

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

Place domain span TSVs in `../domains/` with filename `domains_{lang_id}.tsv`:

```
Position_Name	Element	Domain_Type	Span_Start	Span_End	Test_Name	Criterion	Value
v:verbstem	root	morphosyntactic	10	10	ciscategorial	complete_domains	1
v:verbstem	root	morphosyntactic	8	16	coreference	bindee_domain	reflexivization
...
```

Each row = one span from one test. The script will:
- Extract unique (Span_Start, Span_End, Domain_Type) tuples
- Group by domain type for conflict analysis

### Running

```bash
cd scripts
python laminar_analysis.py ../domains/domains_{lang_id}.tsv
```

Outputs:
- `results/{lang_id}_laminar_forest.r` — ggtree visualization of all families
- `results/{lang_id}_laminar_analysis.md` — summary table, findings, span occurrence
- Console: conflict counts, family statistics, robustness analysis

### Options

Check `laminar_analysis.py --help` for command-line flags (if implemented).

## Output Artifacts

### R Visualization Files (Generated)

**`laminar_forest.r`**
- All N maximal families rendered as a forest of dendrograms
- Branch thickness = √(number of families span appears in)
- Spans in all families → heaviest lines
- Alpha transparency: all trees together approach black

**`laminar_overlay.r`**
- Same families, grouped and colored by domain type
- Overlay visualization for conflict analysis

**`laminar_conflict_groups.r`**
- Families categorized by conflict properties
- Panels A, B, C = different conflict patterns observed

### Markdown Summary (`{lang_id}_laminar_analysis.md`)

- Data summary: # spans, # conflicts, # conflict pairs
- Result: how many maximal families found
- **Span occurrence table**: which spans appear in how many families
  - Robustness metric: span in all families = structurally robust
  - Span in few families = contingent on conflict resolution elsewhere
- Interpretation against the three hypotheses

## Example Workflow

```bash
# 1. Prepare domain TSV for Nyangatom
# (domains_nyan1308.tsv already exists)

# 2. Run analysis
python laminar_analysis.py ../domains/domains_nyan1308.tsv

# 3. Inspect results
cat ../results/nyan1308_laminar_analysis.md

# 4. Render visualizations in R
cd ../results
Rscript nyan1308_laminar_forest.r  # produces nyan1308_laminar_forest.pdf
Rscript nyan1308_laminar_conflict_groups.r  # produces nyan1308_conflict_groups.pdf
```

## Key Functions in `laminar_analysis.py`

- `load_spans()` — read domain TSV, extract unique (start, end, type) tuples
- `pairwise_relationships()` — classify all span pairs as nested/disjoint/conflict
- `bron_kerbosch()` — enumerate all maximal independent sets
- `build_parent_map()` — assign parents (tree construction)
- `span_to_newick()` — recursive Newick encoder (proper branching trees)
- `write_ggtree_forest()` — generate `laminar_forest.r` visualization code
- `write_ggtree_overlay()` — generate overlay visualization code

## Troubleshooting

**"No maximal families found"**
- Check that domain TSV has valid Span_Start/Span_End columns
- Verify at least one span exists

**"Only 1 family (but I expected conflicts)"**
- All observed spans are mutually compatible — perfect tree support
- This is actually strong support for the Tree hypothesis!

**R script won't render**
- Ensure `ggplot2`, `ape`, `ggtree`, `patchwork` are installed:
  ```R
  install.packages(c("ggplot2", "ape", "ggtree", "patchwork"))
  ```

## See Also

- `treeTraversal.py` — earlier exploratory version (less efficient, different output format)
- `../results/nyan1308_laminar_analysis.md` — example output summary
- `../results/laminar_*.r` — generated visualization scripts
- Good (draft) — "Domains of linearization, constituency, and wordhood in Chichewa"
