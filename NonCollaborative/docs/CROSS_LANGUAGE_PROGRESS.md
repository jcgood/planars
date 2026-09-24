# Charts across languages — progress

Plan: `docs/PLAN_cross_language_charts.md`. This file is the current state;
update it at every step boundary, in the same commit.

## Where things stand (2026-09-23)

- **Built (2026-09-23):** the bundle, the charts, the summary table,
  their checks and docs (see "As built" below). The four §5 questions are
  answered (next section).
- **Next:** Jeff looks at the charts in `results/cross_language/` (or
  catalogue §19) and cuts or changes what doesn't earn its place. After
  that: freeze reference images for the charts he keeps, and write the short
  "what the cross-language charts show" page the plan's §4.5 asks for —
  left until then because it describes charts that may still change.

## As built (2026-09-23)

- `scripts/analysis/export_cross_language.py` writes
  `results/chart_data/cross_language/data/` (seven tables +
  `metadata.json`) and `results/cross_language/cross_language_summary.md` /
  `.tex`. It reads the 22 bundles and re-runs no analysis. The one thing it
  computes on its own is chart C's label shuffle (5000, seed 0). It refuses
  a bundle exported without the permutation flags.
- `planarsviz/R/cross_language.R`: `read_planars_cross_language()` and
  seven charts in `results/cross_language/`: tree-likeness (three variants:
  all tests, syntax side, phonology side), families against size, divide,
  side p-values, edges, convergence. `render_planarsviz.R` recognises the
  bundle by `data/structures.tsv`.
- Checks: `tests/test_planarsviz_cross_language_bundle.py` (no R needed, so
  CI runs it) checks that every structure is present once and that no input
  bundle has changed since export. It also recomputes the ratios, conflict
  counts and boundary profile from chac1251_verbal and nyan1308. A separate
  Sonnet agent, which didn't read the exporter or the R code, recomputed
  every table for chac1251_verbal, nyan1308 and iyoj1235_verbal, plus the
  across-structure tests and names for all 22: no mismatches. Its own
  label shuffle gave p-values within 0.01 of the bundle's. The nyan1308
  renderer check passes, so its 137 charts are unchanged. styler, lintr and
  roxygen are clean.
- Decisions made while building (Opus; open to Jeff's revision):
  - **Chart C's rule.** A span's sides are its domain types' sides. A
    conflict counts as *across* the divide only when the two spans' sides are
    disjoint, so any span on both sides counts as within. The baseline is the
    share of all span pairs that are across. That is exactly the mean of
    the label shuffle, which gives the p-value.
  - **The tree-likeness chart comes in three variants** (all / syntax
    side / phonology side), because the split turned out to be the most
    striking result (below).
  - **Chart E only shows spans picked out by at least two tests**, and
    only the top three convergence levels. In San Martín Duraznos Mixtec
    verbal, every span is picked out by exactly one test, so it shows none.
  - **Output folder:** `results/cross_language/`, not the plan's
    `results/cross-language/`. The renderer names the folder after the
    dataset, and the bundle is `cross_language`.
  - **Language names:** the CCDB import JSON stores accents as separate
    combining characters. PDFs drew them beside the letter ("Martiń"), so
    the exporter composes them. The per-language bundles already had the
    composed form, so their charts are not affected.

## What the charts show (first reading, 2026-09-23)

All caveated: the structures share test batteries, authors and sometimes
language families, so no across-structure p-value treats them as
independent cases.

- **Tree hypothesis, pooled:** 17 of 22 below the span-placement null's
  median (sign test p = 0.008, Fisher p = 3e-5); 19 of 22 on the
  arbitrary-layers null (p = 0.0004, Fisher 8e-7).
- **Split by side, the tree-likeness is almost all on the syntax side.**
  Syntax side: 15 below / 3 above / 4 at the median (sign p = 0.004,
  Fisher 2e-5). Phonology side: 8 / 6 / 8 (sign p = 0.40, Fisher 0.89).
  The syntax side's p-value is lower in 18 of 22 structures. Part of this
  is size: phonology sides often have too few spans for the null to give
  fewer families, which pins their p-values near 1.
- **Divide hypothesis (chart C):** mixed. Conflicts fall across the divide
  more than chance in Chorote (p = 0.004), Oklahoma Cherokee (0.021) and
  San Martín Duraznos Mixtec nominal (0.040). Most structures show no
  excess, and Chácobo verbal runs strongly the other way (4 of 32 across
  against 33% expected). Three structures (Mebengokre, Martinican, Central
  Alaskan Yupik) have no span that is phonology-only, so they can't be
  tested.
- **Families against size:** the plan's guess that Blackfoot and San Martín
  Duraznos Mixtec verbal are more fragmented than their size predicts
  doesn't hold. Both are inside the arbitrary-layers null's 5th–95th
  percentile, and no structure is above it. The outliers are all on the
  tree-like side: South Bolivian Quechua, Araona, Hup verbal, Chácobo
  nominal, Yukuna, Chorote, Ayautla, Oklahoma Cherokee.
- **Edges (chart D):** a structure's single strongest edge is usually a left
  edge (18 of 22). In 10 of those 18 it sits within two positions left of
  the root. The rest are spread from 3 to 16 positions out.

## Jeff's answers to the plan's §5 questions (2026-09-23)

1. **Include nyan1308:** yes, visibly marked as the one structure not from
   CCDB. For chart C, it uses its own existing groupings
   (`planars_groupings.py`): the syntax side is morphosyntactic,
   tonosegmental and length (`syntaxlike`), the phonology side phonological
   and intonational (`phonologylike`). The question as first put said
   tonosegmental and length would count as phonological *and* that this was
   the `phonologylike` grouping, which contradict each other; Jeff settled it
   for the existing groupings when asked again.
2. **Indeterminate spans in chart C:** count them with syntax, i.e. as
   morphosyntactic (not left out, as the plan recommended).
3. **What counts as one:** each of the 22 structures is its own case
   throughout; no second count with one structure per language (the plan
   had recommended both).
4. **A pooled test across structures:** report both the sign count (how
   many fall below the null median, with its binomial p) and a combined
   p-value from the 22 per-structure p-values (e.g. Fisher's method), each
   caveated that structures share test batteries, authors and in some
   cases language families (the plan had recommended the sign count only).
