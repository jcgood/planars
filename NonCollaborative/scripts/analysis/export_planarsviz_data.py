"""Export validated laminar-analysis data for the ``planarsviz`` R package.

This is an adapter, not a second family-enumeration implementation.  The
validated functions in ``laminar_analysis.py`` remain responsible for loading
spans, detecting conflicts, and enumerating maximal laminar families.  This
script serializes those results into a small, inspectable data bundle for R.

Example:
    python scripts/analysis/export_planarsviz_data.py \
        --domain-file domains_nyan1308.tsv \
        --output-dir results/planarsviz
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    Span,
    enumerate_maximal_laminar_families,
    find_conflicts,
    load_spans,
)

# Domain-type display style: colour, the order types are sorted in within a
# layer (df.plot()'s factor levels), the order they appear in a legend, and the
# order of per-type panels (facet_order, from nyan_boundary_skyline.r's facet
# levels -- a third, different order, kept as-is so that chart doesn't change).
# Colours and the first two orders are copied from scripts/domain_charts-cgpt.r
# (group.colors, df.plot() levels, constituency.plot() breaks). This is the
# one place R gets them from. A domain type observed in the data but not listed
# here gets FALLBACK_COLOUR and sorts after the known types, alphabetically.
DOMAIN_TYPE_STYLE: list[dict] = [
    {"domain_type": "morphosyntactic", "colour": "#BC3C29", "sort_order": 1, "legend_order": 1, "facet_order": 1},
    {"domain_type": "tonosegmental", "colour": "#0072B5", "sort_order": 2, "legend_order": 5, "facet_order": 3},
    {"domain_type": "length", "colour": "#E18727", "sort_order": 3, "legend_order": 3, "facet_order": 5},
    {"domain_type": "phonological", "colour": "#20845E", "sort_order": 4, "legend_order": 2, "facet_order": 2},
    {"domain_type": "intonational", "colour": "#7876B1", "sort_order": 5, "legend_order": 4, "facet_order": 4},
]
FALLBACK_COLOUR = "#7F7F7F"


def domain_type_rows(observed: list[str]) -> list[dict]:
    """Style rows for every known domain type plus any unknown observed one."""
    rows = [dict(row, known=True) for row in DOMAIN_TYPE_STYLE]
    known = {row["domain_type"] for row in rows}
    extra = sorted(t for t in observed if t not in known)
    for i, domain_type in enumerate(extra, start=1):
        rows.append({
            "domain_type": domain_type,
            "colour": FALLBACK_COLOUR,
            "sort_order": len(DOMAIN_TYPE_STYLE) + i,
            "legend_order": len(DOMAIN_TYPE_STYLE) + i,
            "facet_order": len(DOMAIN_TYPE_STYLE) + i,
            "known": False,
        })
    return rows


def with_synthetic_root(spans: list[Span], n_positions: int) -> tuple[list[Span], bool]:
    """Add the synthetic full root [1..n_positions] when no observed span covers it.

    enumerate_maximal_laminar_families() puts that synthetic root into every
    family, so the span table must list it too or memberships would name a
    span the table doesn't have. It is flagged `synthetic` in spans.tsv and
    excluded from observed-span counts. Found by the shifted test dataset,
    whose data starts at position 3: nyan1308 never needed it because its
    [1-22] span is observed.
    """
    if any(span.left == 1 and span.right == n_positions for span in spans):
        return spans, False
    root = Span(1, n_positions, labels=("(root)",),
                domain_types=frozenset(["(synthetic)"]), convergence=0)
    return spans + [root], True


def load_root_position(planar_file: Path | None, root_element: str) -> int | None:
    """Position whose planar-table Elements value is `root_element`, if any."""
    if planar_file is None or not planar_file.exists():
        return None
    with planar_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    matches = [int(row["Position"]) for row in rows
               if (row.get("Elements") or "").strip() == root_element]
    if len(matches) > 1:
        raise ValueError(f"More than one {root_element!r} position in {planar_file}: {matches}")
    return matches[0] if matches else None


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write deterministic tab-separated rows."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def span_id(span: Span) -> str:
    return f"{span.left}-{span.right}"


def load_position_labels(planar_file: Path | None, n_positions: int,
                         labels_file: Path | None = None) -> list[dict]:
    """Load display labels for positions 1..n_positions.

    Priority: an explicit two-column labels file (position, label) — used when
    a dataset's chart labels differ from its planar table's short slot codes,
    as nyan1308's do; then the planar table's Position_Label column; then
    numeric labels.
    """
    if labels_file is not None:
        with labels_file.open(encoding="utf-8", newline="") as handle:
            labels = [
                {"position": int(row["position"]), "label": row["label"]}
                for row in csv.DictReader(handle, delimiter="\t")
            ]
        labels.sort(key=lambda row: row["position"])
        if [r["position"] for r in labels] != list(range(1, n_positions + 1)):
            raise ValueError(f"Labels file does not contain positions 1..{n_positions}: {labels_file}")
        return labels
    if planar_file is None or not planar_file.exists():
        return [
            {"position": position, "label": str(position)}
            for position in range(1, n_positions + 1)
        ]

    with planar_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    labels = [
        {"position": int(row["Position"]), "label": row["Position_Label"]}
        for row in rows
    ]
    labels.sort(key=lambda row: row["position"])
    if len(labels) != n_positions or [r["position"] for r in labels] != list(range(1, n_positions + 1)):
        raise ValueError(f"Planar file does not contain positions 1..{n_positions}: {planar_file}")
    return labels


def export_bundle(
    domain_file: Path,
    output_root: Path,
    planar_file: Path | None = None,
    labels_file: Path | None = None,
    root_element: str = "root",
    language_name: str | None = None,
) -> Path:
    """Export one validated domain dataset and return its bundle directory.

    In addition to the all-domain bundle, export one nested bundle for each
    observed ``Domain_Type``.  All family results are produced by the same
    analysis functions; this file only serializes their results.
    """
    if not domain_file.exists():
        raise FileNotFoundError(domain_file)

    dataset = domain_file.stem.removeprefix("domains_")
    domains_dir = domain_file.parent
    bundle_dir = output_root / dataset
    data_dir = bundle_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    tests = pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")
    active_source_rows = [
        line_number
        for line_number, line in enumerate(domain_file.read_text(encoding="utf-8").splitlines(), start=1)
        if line_number > 1 and line.strip() and not line.startswith("#")
    ]
    if len(active_source_rows) != len(tests):
        raise ValueError("Could not align active tests with source TSV rows.")
    tests.insert(0, "source_row", active_source_rows)
    tests.to_csv(data_dir / "tests.tsv", sep="\t", index=False)

    # Keep the full dataset's position count for every subset.  A subset may
    # stop before the final planar position but its trees still use the full
    # observed root coordinate system.
    full_spans, n_positions = load_spans(domain_file.name, str(domains_dir))
    if not full_spans:
        raise ValueError(f"No usable spans found in {domain_file}.")

    def write_analysis_tables(target_dir, spans, families, adjacency, subset_tests):
        target_dir.mkdir(parents=True, exist_ok=True)
        span_lookup = {span_id(span): span for span in spans}
        span_family_count = {
            key: sum(span in family for family in families)
            for key, span in span_lookup.items()
        }
        span_rows = []
        for key in sorted(span_lookup, key=lambda value: tuple(map(int, value.split("-")))):
            span = span_lookup[key]
            span_rows.append({
                "span_id": key,
                "left": span.left,
                "right": span.right,
                "size": span.size,
                "convergence": span.convergence,
                "family_frequency": span_family_count[key],
                "labels": "|".join(span.labels),
                "domain_types": "|".join(sorted(span.domain_types)),
                "synthetic": span.domain_types == frozenset(["(synthetic)"]),
            })
        write_tsv(target_dir / "spans.tsv", [
            "span_id", "left", "right", "size", "convergence",
            "family_frequency", "labels", "domain_types", "synthetic"
        ], span_rows)

        family_rows = []
        membership_rows = []
        for family_number, family in enumerate(families, start=1):
            family_id = f"family_{family_number:03d}"
            family_rows.append({
                "family_id": family_id,
                "family_number": family_number,
                "n_spans": len(family),
            })
            for span in sorted(family, key=lambda item: (item.left, item.right)):
                membership_rows.append({"family_id": family_id, "span_id": span_id(span)})
        write_tsv(target_dir / "families.tsv", ["family_id", "family_number", "n_spans"], family_rows)
        write_tsv(target_dir / "family_membership.tsv", ["family_id", "span_id"], membership_rows)

        conflict_rows = []
        for left, neighbors in adjacency.items():
            for right in neighbors:
                left_id, right_id = span_id(left), span_id(right)
                if left_id < right_id:
                    conflict_rows.append({"span_id_a": left_id, "span_id_b": right_id})
        conflict_rows.sort(key=lambda row: (row["span_id_a"], row["span_id_b"]))
        write_tsv(target_dir / "conflict_pairs.tsv", ["span_id_a", "span_id_b"], conflict_rows)
        subset_tests.to_csv(target_dir / "tests.tsv", sep="\t", index=False)
        return span_family_count, conflict_rows

    spans, _ = full_spans, n_positions
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    if truncated:
        raise RuntimeError("Family enumeration was truncated; refusing to export incomplete data.")
    table_spans, synthetic_root = with_synthetic_root(spans, n_positions)
    span_family_count, conflict_rows = write_analysis_tables(data_dir, table_spans, families, adjacency, tests)
    synthetic_id = f"1-{n_positions}" if synthetic_root else None

    if planar_file is None:
        candidate = REPO_DIR / "planar_tables" / f"planar_{dataset}.tsv"
        planar_file = candidate if candidate.exists() else None
    # Display labels come from an explicit labels file when given (nyan1308's
    # chart labels differ from its planar table's slot codes); never from a
    # dataset-name special case.
    if labels_file is None:
        candidate = REPO_DIR / "planar_tables" / f"display_labels_{dataset}.tsv"
        labels_file = candidate if candidate.exists() else None
    position_rows = load_position_labels(planar_file, n_positions, labels_file)
    write_tsv(data_dir / "position_labels.tsv", ["position", "label"], position_rows)
    root_position = load_root_position(planar_file, root_element)
    observed_types = sorted(t.strip() for t in tests["Domain_Type"].dropna().unique())
    write_tsv(data_dir / "domain_types.tsv",
              ["domain_type", "colour", "sort_order", "legend_order", "facet_order", "known"],
              domain_type_rows(observed_types))

    metadata = {
        "contract_version": "0.2.0",
        "dataset": dataset,
        "language_name": language_name,
        "source_domain_file": str(domain_file),
        "source_domain_sha256": sha256_file(domain_file),
        "source_planar_file": (
            str(planar_file.relative_to(REPO_DIR))
            if planar_file and planar_file.is_relative_to(REPO_DIR)
            else str(planar_file) if planar_file else None
        ),
        "source_planar_sha256": sha256_file(planar_file) if planar_file else None,
        "source_labels_file": (
            str(labels_file.relative_to(REPO_DIR))
            if labels_file and labels_file.is_relative_to(REPO_DIR)
            else str(labels_file) if labels_file else None
        ),
        "root_element": root_element,
        "root_position": root_position,
        "n_positions": n_positions,
        "n_active_tests": len(tests),
        "n_unique_spans": len(spans),
        "synthetic_root": synthetic_root,
        "n_conflict_pairs": len(conflict_rows),
        "n_maximal_families": len(families),
        "n_universal_spans": sum(
            frequency == len(families)
            for key, frequency in span_family_count.items() if key != synthetic_id
        ),
        "enumeration_truncated": truncated,
        "producer": "scripts/analysis/export_planarsviz_data.py",
        "analysis_source": "scripts/analysis/laminar_analysis.py",
    }
    (data_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Domain-type-specific family analyses for exact laminar overlays.
    domain_types = sorted(t.strip() for t in tests["Domain_Type"].dropna().unique())
    subset_index = []
    for domain_type in domain_types:
        subset_slug = domain_type.lower().replace(" ", "_").replace("-", "_")
        subset_tests = tests[tests["Domain_Type"].str.strip() == domain_type].copy()
        subset_spans, _ = load_spans(
            domain_file.name, str(domains_dir), subset=[domain_type]
        )
        if not subset_spans:
            continue
        subset_adjacency = find_conflicts(subset_spans)
        subset_families, subset_truncated = enumerate_maximal_laminar_families(
            subset_spans, subset_adjacency, n_positions
        )
        if subset_truncated:
            raise RuntimeError(
                f"Family enumeration was truncated for domain subset {domain_type!r}."
            )
        # Subset analyses use the full dataset's coordinate system.  When a
        # subset has no observed full-span root, the analysis adds a synthetic
        # root to every family; export it as a span too so memberships remain
        # self-contained and directly readable by R.
        n_observed_subset_spans = len(subset_spans)
        subset_spans, subset_synthetic = with_synthetic_root(subset_spans, n_positions)
        subset_synthetic_id = f"1-{n_positions}" if subset_synthetic else None
        subset_dir = data_dir / "subsets" / subset_slug
        subset_frequency, subset_conflicts = write_analysis_tables(
            subset_dir, subset_spans, subset_families, subset_adjacency, subset_tests
        )
        subset_metadata = {
            "contract_version": "0.2.0",
            "dataset": dataset,
            "subset_id": subset_slug,
            "domain_type": domain_type,
            "source_domain_file": str(domain_file),
            "source_domain_sha256": sha256_file(domain_file),
            "n_positions": n_positions,
            "n_active_tests": len(subset_tests),
            "n_unique_spans": n_observed_subset_spans,
            "synthetic_root": subset_synthetic,
            "n_conflict_pairs": len(subset_conflicts),
            "n_maximal_families": len(subset_families),
            "n_universal_spans": sum(
                frequency == len(subset_families)
                for key, frequency in subset_frequency.items() if key != subset_synthetic_id
            ),
            "enumeration_truncated": subset_truncated,
            "domain_types": [domain_type],
        }
        (subset_dir / "metadata.json").write_text(
            json.dumps(subset_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        subset_index.append({
            "subset_id": subset_slug,
            "domain_type": domain_type,
            "path": f"subsets/{subset_slug}",
            "n_active_tests": len(subset_tests),
            "n_unique_spans": n_observed_subset_spans,
            "n_maximal_families": len(subset_families),
        })
    (data_dir / "subsets.json").write_text(
        json.dumps(subset_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-file", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=REPO_DIR / "results" / "planarsviz"
    )
    parser.add_argument("--planar-file", type=Path, default=None)
    parser.add_argument(
        "--labels-file", type=Path, default=None,
        help="TSV with position and label columns; default planar_tables/display_labels_<dataset>.tsv if present",
    )
    parser.add_argument(
        "--root-element", default="root",
        help="Elements value marking the root position in the planar table (default: root)",
    )
    parser.add_argument(
        "--language-name", default=None,
        help="Human-readable language name for chart titles, e.g. Chichewa (titles fall back to the dataset id)",
    )
    args = parser.parse_args()

    bundle_dir = export_bundle(args.domain_file, args.output_dir, args.planar_file,
                               args.labels_file, args.root_element, args.language_name)
    print(f"Exported planarsviz bundle: {bundle_dir}")


if __name__ == "__main__":
    main()
