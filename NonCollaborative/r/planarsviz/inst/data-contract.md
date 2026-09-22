# `planarsviz` data contract

This package separates analysis from visualization.

Python is the analytical source of truth. The Python analysis code loads the
domain TSV, validates span sizes, deduplicates spans, classifies conflicts,
and enumerates maximal laminar families. The exporter
(`scripts/analysis/export_planarsviz_data.py`) then writes a bundle for R.
R does not re-enumerate families, build tree topology, or choose which
families to show: those come from the bundle.

Facts about a language (position labels, root position, domain types,
highlighted ranges, the spans that define conflict groups) are data in the
bundle, never literals in R.

## Bundle layout

```text
data/
├── metadata.json
├── tests.tsv
├── spans.tsv
├── families.tsv
├── family_membership.tsv
├── conflict_pairs.tsv
├── position_labels.tsv
├── domain_types.tsv
├── highlights.tsv
├── conflict_groups.tsv
├── selections.tsv
├── subsets.json            subsets/<domain type>/  (same tables, one type)
├── forests.json            forests/<forest id>.tsv
└── overlay_groups.json     overlay_groups/<group id>.tsv
```

`tests.tsv` contains active, non-commented source tests (with their source
row number) used by pooled visualizations.

`spans.tsv` has one row per unique positional span. `family_frequency` counts
maximal families containing the span; `convergence` counts source tests that
produced the span. `synthetic` is `True` only for a full root
`[1-n_positions]` that no test produced but the family enumeration adds to
every family; it is not counted as an observed span. `span_chart_rank` is the
span-frequency chart's row order (empty for the full root). `blend_colour` is
the per-channel average of the span's domain-type colours (black for the
synthetic root), used by the ForestSpans chart.

`subsets.json` lists fresh analyses of part of the data, each in
`subsets/<subset_id>/` with the same tables as `data/`: `kind` `domain_type`
(one per observed type) or `filter` (every observed type except those a
filter in `scripts/analysis/planars_groupings.py` leaves out, e.g. `no_tono`;
exported only when the data has a type to leave out). Their spans, families
and counts are recomputed, not filtered from the full analysis.

`families.tsv` has one row per maximal family: `family_id`, `family_number`,
`n_spans`, and `newick` (the family's tree; tips are position numbers,
internal nodes `left-right`). `family_membership.tsv` maps each family to its
member spans.

`conflict_pairs.tsv` contains each unordered pair of partially overlapping
spans once.

`position_labels.tsv` maps planar position numbers to display labels: from
an explicit labels file, else the planar table's `Position_Label`, else the
numbers.

`domain_types.tsv`: per domain type, `colour`, `sort_order`, `legend_order`,
`facet_order`, `alt_colour`, `colour_priority`, and `known` (`False` = seen in
the data but not in the exporter's style table; it gets a fallback grey).

`highlights.tsv`: named position ranges (`highlight_id`, `name`, `left`,
`right`, `colour`, `layer`; later layers win where ranges overlap). May be
empty.

`conflict_groups.tsv`: every family's group (`group_id`, `defining_span_id`
— empty for the group of all remaining families — `family_id`) and
`draw_rank` (empty = not drawn under `metadata.conflict_group_cap`). May be
empty.

`selections.tsv` (`selection`, `rank`, `family_id`): `consensus_all` and
`consensus_<group_id>`, the family with the highest sum of its spans' family
counts across all families; `most_binary`, the family whose tree branches
most binarily (most strictly binary nodes, then most tests supporting the
tree, then the narrowest widest node); `exemplary`, ranks 1.., the representative
families chosen by greedy coverage (`metadata.exemplary_k` of them) plus,
when `metadata.exemplary_include_sparsest`, the family drawing on the
fewest tests.

`tree_counts.tsv`: the numbers behind the tree-count bar charts, from
`laminar_tree_counts.py`'s `collect_counts()` and `collect_bundle_counts()`
(`condition` all_tests / without_adjacent_spans, `class`, `n_unique_spans`,
`n_maximal_laminar_families`), plus `kind` (all / class / bundle), `label`
and `colour` for the bars. Types and bundles with no tests in the data are
left out.

`boundary_strength.tsv` (in `data/` and in every `subsets/<id>/`): per
position, how strongly it is a left or right constituent edge across the
analysis's maximal families, from `boundary_strength.py`'s
`compute_boundary_strength()`: `left_summed`/`right_summed` (sum over spans
starting/ending there of each span's family count) and
`left_capped`/`right_capped` (families with at least one such span).
Beside it, `boundary_strength_density.tsv` (`x`, `left`, `right`): the
weighted density curves of the summed strengths drawn by the distributions
chart, on 400 points from the first position − 1 to the last + 1; a side
is empty when it has fewer than two positions with any strength.

`fragmentation_test.tsv` and `fragmentation_null.tsv` (in `data/` only, and
**only when the bundle was exported with `--fragmentation-permutations`** —
the test takes minutes where the rest of the export takes seconds, so a
bundle without these two tables is normal and the chart says so rather than
failing). From `class_fragmentation_test.py`'s `run_test()`.

`fragmentation_test.tsv` is one row per group, a group being either a single
domain type (`kind` class) or one of `planars_groupings.BUNDLES` (`kind`
bundle): `group`, `kind`, `label` and `colour` for the row, `n_tests`,
`observed_families`, then the null's `null_mean`, `null_p05`, `null_p95` and
the one-sided `p_value_le_observed` (fraction of permutations with family
count <= observed; small = unusually laminar -- same convention and column
name as `span_placement_test.py`'s own p-value), then `n_permutations` and
`seed`, which record the run that produced the numbers. Groups follow
`tree_counts.tsv`'s
convention: only domain types the data actually has, and only bundles with a
type in it.

`fragmentation_null.tsv` is the null distributions as a **tally**, not one
row per draw: `group`, `kind`, `family_count`, `n`, where `n` is how many of
the `n_permutations` draws gave that count. This is lossless for everything
the chart and the p-value need — only draw order is dropped, and the seed
reproduces that — and it is the difference between 227 rows and 40,000 for
nyan1308 at 5000 draws. A reader that wants one row per draw expands it;
`read_planars_fragmentation_null()` does that by default, which is also how
the chart gets a violin identical to the one the original script drew.

`span_placement_test.tsv` and `span_placement_null.tsv` (in `data/` only, and
**only when the bundle was exported with `--span-placement-permutations`** —
same reason as the fragmentation tables). From `span_placement_test.py`'s
`run_test()`: does the real arrangement of a group's spans give fewer
laminar families than those same span *lengths* placed at random would?

`span_placement_test.tsv` is one row per group, a group being the pooled
dataset (`kind` all), a single domain type (`kind` class) or one of
`planars_groupings.BUNDLES` (`kind` bundle): `group`, `kind`, `label`,
`colour`, `n_spans`, `n_positions`, `observed_families`, the null's
`null_mean`, `null_p05`, `null_p50`, `null_p95`, the one-sided
`p_value_le_observed` (same direction and column name as
`fragmentation_test.tsv`'s), `n_truncated`, then `n_permutations` and `seed`.

**The row order is load-bearing, not cosmetic.** `run_test()` advances one
shared random stream across the groups in the order it is given them, so the
exporter passes them in `span_placement_test.py`'s own order — pooled first,
then the domain types in `CLASS_ORDER`, then the bundles — and a different
order would give different, still valid but no longer comparable, draws.

`span_placement_null.tsv` is the null distributions as a tally, the same
shape and for the same reason as `fragmentation_null.tsv`: `group`, `kind`,
`family_count`, `n`. Unlike that one it is **not** expanded back to one row
per draw, because this chart draws the tally directly as bars and weights its
own density curve by `n`.

The pooled row's `label` is `All (pooled)` where
`boundary_strength_test.tsv`'s is `All tests`: this test pools spans and that
one pools tests. Each table carries its own `label` column for exactly that
reason.

`arbitrary_layers_test.tsv` and `arbitrary_layers_null.tsv` (in `data/` only,
and **only when the bundle was exported with
`--arbitrary-layers-permutations`**). From `arbitrary_layers_test.py`'s
`run_test()`: is a group's family count remarkable for that many spans of
arbitrary size at arbitrary positions?

Same columns, same group order and the same load-bearing ordering rule as
`span_placement_test.tsv`, plus one: **`includes_root`** (`y`/`n`), whether
that group's real spans contain the full-structure span. When they do, the
null fixes that span and draws the rest freely; when they do not, it draws all
of them freely. The column records which, because it is what keeps a group's
null and its observed set comparable — same span count, same presence or
absence of a span covering everything, with only the arbitrary sizes and
positions varying.

**This is the weakest of the three nulls**, and the ordering is the point:
`fragmentation_test.tsv` shuffles domain-type labels with every span fixed in
place, `span_placement_test.tsv` holds each span's real length and randomizes
its position, and this one randomizes size and position together, knowing only
how many spans a group has. A raw family count read aloud is implicitly being
compared against something like this null, which is why it is worth having
measured rather than assumed.

`boundary_strength_test.tsv` (in `data/` only, and **only when the bundle
was exported with `--boundary-strength-test-permutations`** — same reason
as the fragmentation tables: one family enumeration per replicate, so it
takes minutes where the rest of the export takes seconds). From
`boundary_strength_test.py`'s `run_test()`: whether `boundary_strength.tsv`'s
per-position strength, and its jump from the previous position, is higher
than a same-length-profile random arrangement of spans would produce.

One row per (group, side, statistic, position): `group`, `kind` (`all` /
class / bundle), `label`, `colour` for the row; `side` (`left` / `right`);
`statistic` (`level` — the summed strength itself, or `jump` —
`strength[p] - strength[p-1]`, signed, 0 at position 1); `position`;
`observed`; the null's `null_mean`, `null_p05`, `null_p95`; the one-sided
`p_value_ge_observed` (fraction of permutations with a value >= observed;
small = unusually strong boundary evidence — the mirror image of
`fragmentation_test.tsv`'s `p_value_le_observed`, since here MORE strength
is the interesting direction); then `n_permutations` and `seed`. Unlike
`fragmentation_null.tsv`, there is no raw-draw table: only the null's
percentiles are kept, the same choice already made for
`boundary_strength_density.tsv`'s curves, since the chart needs an envelope
band around the observed curve rather than a distribution shape.

`forests.json` / `forests/<id>.tsv`: the trees of each per-class forest
(Newick, span order, thickness), computed with the class's own position
count. `overlay_groups.json` / `overlay_groups/<id>.tsv`: the trees of each
overlay group (Newick, span order, convergence), computed with the full
dataset's position count.

`metadata.json` records the contract version, source files and checksums,
`language_name`, `root_position`, `n_positions`, counts, `synthetic_root`,
`conflict_group_cap`, and enumeration truncation status. A renderer must
reject a bundle marked as truncated.

## Validation invariants

- Span IDs are canonical `left-right` strings.
- Span sizes equal `right - left + 1`.
- Family IDs are deterministic and ordered as `family_001`, `family_002`, etc.
- Every membership span ID exists in `spans.tsv`.
- Every conflict pair references known spans and is unordered/deduplicated.
- `n_maximal_families` equals the number of rows in `families.tsv`.
- `n_unique_spans` equals the number of non-synthetic rows in `spans.tsv`.
- `n_positions` equals the number of rows in `position_labels.tsv`.
- `enumeration_truncated` must be `false` for production rendering.
- When `fragmentation_null.tsv` is present, each group's `n` values sum to
  that group's `n_permutations` in `fragmentation_test.tsv`, and every group
  in one table appears in the other with the same `kind`.
- When `boundary_strength_test.tsv` is present, every group has exactly
  `n_positions` rows for each of `(side, statistic)` — four combinations —
  and `statistic == "jump"` rows at `position == 1` carry `observed == 0`
  (there is no position 0 to jump from).
