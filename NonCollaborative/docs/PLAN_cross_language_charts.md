# Plan: charts and summaries across languages

Status: drafted and built 2026-09-23; waiting on Jeff's cuts. Current state is
`docs/CROSS_LANGUAGE_PROGRESS.md`; this file says what and why.

## 1. What we are doing

Every structure now has its own bundle and charts: nyan1308 and the 21 CCDB
structures, 22 in all (`results/chart_data/<dataset>/`). Nothing yet sets them
side by side. This work adds one **cross-language bundle**, built only by
reading the 22 existing bundles, and a set of charts and one summary table
drawn from it. The charts are chosen to bear on the project's three
hypotheses (root `CLAUDE.md`): the Tree hypothesis (spans nest), the
morphosyntax/phonology divide (deviations from nesting fall between the two
classes, not within them), and the Word hypothesis (some tests converge on a
small span that partitions the larger domain).

Jeff asked for this 2026-09-23 ("definitely do charts and summaries across
languages; try to guess some good ones"). The charts below are Claude's
guesses: propose them, draw them, and let Jeff cut what doesn't earn its
place.

## 2. What is already known (from the committed bundles, 2026-09-23)

- Sizes vary a lot: 12–46 positions, 12–95 tests (CCDB 12–38; nyan1308
  95), 2–69 families.
- **A first cross-language pattern:** in 17 of the 22 structures, the
  observed family count (all tests pooled) is below the span-placement
  null's mean, i.e. more tree-like than randomly placed spans of the same
  lengths. Pooled p below 0.05 in 5 on that null (Araona, Ayautla Mazatec,
  Hup verbal, South Bolivian Quechua, Yukuna) and in 8 on the weaker
  arbitrary-layers null (those five plus Chácobo nominal, Oklahoma
  Cherokee, Chorote). The most tree-like is South Bolivian Quechua (3
  families where chance gives about 15, no draw as low). The five running
  the other way: Teotitlán del Valle Zapotec verbal (p = 0.96), Blackfoot
  (0.93), Martinican (0.76), Teotitlán nominal (0.76), San Martín Duraznos
  Mixtec verbal (0.62). No single structure settles anything; the spread
  across 22 might.
- Language names come from `planar_tables/ccdb_<Planar_ID>.json`; don't
  write them from memory (a first draft of this plan got four wrong).
- Every bundle already holds what the charts below need:
  `metadata.json` (counts, root position, planar type), `tree_counts.tsv`
  (families per domain type), `spans.tsv` (each span's edges, convergence,
  domain types), `conflict_pairs.tsv`, `boundary_strength.tsv`, and the four
  permutation-test tables with their null summaries.

## 3. Proposed charts, most useful first

**A. Tree-likeness across languages (the headline).** One row per
structure, ordered by effect: the observed family count against its
span-placement null, drawn as observed ÷ null median on a log axis with the
null's 5th–95th percentile as a bar, so 1 means "what chance gives" whatever
the structure's size. A second mark for the arbitrary-layers null. p-value at
the right. Answers: across languages, are tests more tree-like than chance?

**B. Families against size.** Scatter: number of distinct spans (x) against
families (y, log), one point per structure, shaped by planar type (verbal /
nominal), labelled. With the arbitrary-layers null's median as a reference
band, the outliers (Blackfoot: 31 families on 14 positions; San Martín
Duraznos Mixtec verbal: 40) stand out as more fragmented than their size
predicts, and South Bolivian Quechua as less.

**C. The divide: where do the conflicts fall?** For each structure, the share
of conflicting span pairs that are *between* a morphosyntactic and a
phonological span, against the share expected if conflicts ignored class
(from the number of spans of each class). Hypothesis (ii) predicts
between-class conflicts above expectation. Computed from `conflict_pairs.tsv`
and `spans.tsv`; spans carrying both types, and `indeterminate` spans, need a
rule (see §5). A companion panel: per-class span-placement p-values,
morphosyntactic against phonological, one line per structure — is one class
consistently more tree-like?

**D. Edges around the root.** A heatmap with one row per structure and
positions re-numbered relative to the root (root = 0), coloured by boundary
strength scaled within each structure, left edges and right edges as two
panels. Positions where the boundary-strength test's jump is significant are
marked. Answers: do strong edges line up at the same distance from the verb
root across languages (Chácobo verbal: positions 6–7, just left of the root)?

**E. Word-sized convergence.** For each structure, its most convergent spans
(most tests picking out exactly that span), drawn as segments on the same
root-aligned axis as D, width by convergence. The Word hypothesis predicts a
recurring small span around the root; this shows whether one recurs and how
big it is relative to the structure.

**F. Summary table.** One row per structure: language, planar type,
positions, tests, distinct spans, families (all, and per domain type), the
pooled p-value of each of the three family-count tests, the strongest edge
(position relative to root), and the most convergent span. Written as TSV
(`results/cross-language/cross_language_summary.tsv`), Markdown, and LaTeX
in the style of `make_forestspans_table.py`.

Worth trying only if the above work: a small-multiples grid of every
structure's `laminar_overlay` at thumbnail size, for a visual overview.

## 4. How it is built

Follow the illustrations bundle (catalogue §17, phase E), the one existing
bundle with no single language behind it:

1. **`scripts/analysis/export_cross_language.py`** reads every
   `results/chart_data/<dataset>/data/` (skipping `illustrations` and
   `shifted_nyan`), and writes `results/chart_data/cross_language/data/`:
   one tidy table per chart plus `metadata.json` listing each input
   bundle's dataset and a hash of its `metadata.json`, so a stale
   cross-language bundle can be detected. **It re-runs no analysis**:
   everything it writes is read or arithmetically derived from bundle
   tables. Dry run by default, `--apply` to write.
2. **R:** `planarsviz/R/cross_language.R` with
   `read_planars_cross_language()` and one `plot_cross_language_*()` per
   chart; each sets `planarsviz_size` and `planarsviz_folder` (`""`: the
   charts land flat in `results/cross-language/`, as illustrations do).
   Contract entries in `planarsviz/inst/data-contract.md`, roxygen docs,
   catalogue section, styler and lintr clean.
3. **Renderer:** `render_planarsviz.R --bundle results/chart_data/cross_language`
   recognises the bundle kind and draws its charts.
4. **Checks:** a bundle test (every structure present once; ratios and
   shares recomputed independently from two or three source bundles), and
   the renderer check still reporting nyan1308's 137 charts unchanged.
5. **Docs:** catalogue section, guide, `results/visualizations.md`,
   `scripts/INDEX.md`, this folder's `CLAUDE.md`; a short "what the
   cross-language charts show" section in the tutorial or its own page.

## 5. Questions for Jeff (ask one at a time, before building)

1. **Include nyan1308?** Its tests are coded with five domain types
   (tonosegmental, intonational, length besides the two main ones), CCDB's
   with morphosyntactic / phonological / indeterminate. Recommendation:
   include it, visibly marked, treating tonosegmental, intonational and length
   as phonological for chart C only (its `phonologylike` bundle).
2. **Indeterminate spans in chart C.** Recommendation: leave them out of
   the between/within count (they belong to neither side), and report how
   many conflicts that drops per structure.
3. **What counts as one language** in any statement across structures
   (Chácobo, San Martín Duraznos Mixtec, Hup, Teotitlán del Valle Zapotec
   each have a verbal and a nominal structure). Recommendation: charts show
   every structure; any count across languages ("17 of 22 below chance") is
   given both per structure and with one structure per language.
4. **A pooled test across languages** (e.g. a sign test on "below the
   null median", or combining p-values). Recommendation: report the sign
   count with its binomial p, clearly caveated (structures share test
   batteries, authors and in some cases families), and no combined p-value.

## 6. Who does what

The main session (Opus) settles §5 with Jeff, designs the bundle tables
and the chart-C rule, and judges every chart. Sonnet agents: the exporter
from a fully specified table list (then an independent agent recomputes the
numbers from two source bundles without reading the exporter); the R
functions one chart per agent once the tables exist (each in its own
worktree, each required to pass styler, lintr, roxygen and the renderer
check); doc drafts. At most 6 agents at once.

## 7. What not to do

- Don't re-run or change any per-language analysis or bundle; read them.
- Don't change nyan1308's charts (renderer check must stay clean).
- Don't state a cross-language result in the docs without its caveats
  (§5.3–5.4).
