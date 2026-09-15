# `planarsviz` data contract

This package separates analysis from visualization.

Python is the analytical source of truth. The Python analysis code loads the
domain TSV, validates span sizes, deduplicates spans, classifies conflicts,
and enumerates maximal laminar families. The exporter then writes a bundle for
R. R does not re-enumerate families in production rendering.

## Bundle layout

Each dataset bundle has this structure:

```text
data/
├── spans.tsv
├── tests.tsv
├── families.tsv
├── family_membership.tsv
├── conflict_pairs.tsv
├── position_labels.tsv
└── metadata.json
```

`spans.tsv` contains one row per unique positional span. `family_frequency`
counts maximal families containing the span; `convergence` counts source tests
that produced the span.

`families.tsv` contains one row per maximal family. `family_membership.tsv`
maps each family to its member spans.

`conflict_pairs.tsv` contains each unordered pair of partially overlapping
spans once.

`tests.tsv` contains active, non-commented source tests used by pooled
visualizations.

`position_labels.tsv` maps planar position numbers to display labels. If no
matching planar file is available, numeric labels are used as a deterministic
fallback.

`metadata.json` records the contract version, source checksums, dimensions,
counts, enumeration truncation status, and producer information. A renderer
must reject a bundle marked as truncated.

## Validation invariants

- Span IDs are canonical `left-right` strings.
- Span sizes equal `right - left + 1`.
- Family IDs are deterministic and ordered as `family_001`, `family_002`, etc.
- Every membership span ID exists in `spans.tsv`.
- Every conflict pair references known spans and is unordered/deduplicated.
- `n_maximal_families` equals the number of rows in `families.tsv`.
- `n_unique_spans` equals the number of rows in `spans.tsv`.
- `enumeration_truncated` must be `false` for production rendering.
