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
counts across all families; `exemplary`, ranks 1.., the representative
families chosen by greedy coverage (`metadata.exemplary_k` of them) plus,
when `metadata.exemplary_include_sparsest`, the family drawing on the
fewest tests.

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
