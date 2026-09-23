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
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from laminar_analysis import (  # noqa: E402
    OVERLAY_GROUPS,
    Span,
    build_parent_map,
    enumerate_maximal_laminar_families,
    find_conflicts,
    get_children,
    load_spans,
    select_representative_families,
    span_to_newick,
)
from planars_groupings import BUNDLES, FILTERS  # noqa: E402
from laminar_tree_counts import (  # noqa: E402
    CLASS_COLORS,
    CLASS_ORDER,
    collect_bundle_counts,
    collect_counts,
)
from boundary_strength import compute_boundary_strength  # noqa: E402
from class_fragmentation_test import run_test as run_fragmentation_test  # noqa: E402
from boundary_strength_test import run_test as run_boundary_strength_test  # noqa: E402
from span_placement_test import run_test as run_span_placement_test  # noqa: E402
from arbitrary_layers_test import run_test as run_arbitrary_layers_test  # noqa: E402


def forest_variants() -> list[tuple[str, list[str], str]]:
    """(forest id, domain types, colour) for every per-class forest chart.

    The per-domain-type groups come from laminar_analysis.OVERLAY_GROUPS and
    the bundles from planars_groupings.BUNDLES, so ids and colours match the
    charts that were previously drawn from nyan1308_{id}_laminar_forest.r.
    """
    variants = [(short, list(types), colour) for types, colour, short in OVERLAY_GROUPS]
    variants += [(name, list(types), colour) for name, types, colour, _ in BUNDLES]
    return variants


def export_forests(domain_file: Path, domains_dir: Path, data_dir: Path) -> None:
    """Write the trees of every per-class forest chart, exactly as drawn.

    For each variant, the same inputs the archived per-class forest scripts
    were written from: the subset's own spans and position count (the
    largest right edge *within the subset* -- e.g. [1-18] for length, not the
    dataset's 22; the analysis subsets in data/subsets/ use the full count
    instead, which would draw different trees), its maximal families, and for
    each family the Newick string, the spans in groupOTU order (by left edge,
    larger first on ties), and each span's thickness sqrt(family count)
    rounded to 4 places. R then draws these without building any topology.
    """
    forest_dir = data_dir / "forests"
    forest_dir.mkdir(parents=True, exist_ok=True)
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    index = []
    for forest_id, types, colour in forest_variants():
        # Skip a forest none of whose domain types occur in this dataset:
        # load_spans() fails on an empty subset rather than returning nothing.
        # Found by the shifted test dataset, where tonosegmental is renamed.
        if not set(types) & observed:
            continue
        spans, n_positions = load_spans(domain_file.name, str(domains_dir), subset=types)
        if not spans:
            continue
        families, truncated = enumerate_maximal_laminar_families(
            spans, find_conflicts(spans), n_positions
        )
        if truncated:
            raise RuntimeError(f"Family enumeration was truncated for forest {forest_id!r}.")
        span_family_count: dict[Span, int] = {}
        for family in families:
            for span in family:
                span_family_count[span] = span_family_count.get(span, 0) + 1
        rows = []
        for tree_number, family_set in enumerate(families, start=1):
            family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
            children = get_children(build_parent_map(family_list))
            root = max(family_list, key=lambda s: s.size)
            ordered = sorted(family_list, key=lambda s: s.left)
            rows.append({
                "tree_number": tree_number,
                "newick": span_to_newick(root, children) + ";",
                "group_spans": ";".join(f"{s.left}-{s.right}" for s in ordered),
                "strengths": ";".join(
                    str(round(span_family_count.get(s, 1) ** 0.5, 4)) for s in ordered
                ),
            })
        write_tsv(forest_dir / f"{forest_id}.tsv",
                  ["tree_number", "newick", "group_spans", "strengths"], rows)
        index.append({
            "forest_id": forest_id,
            "domain_types": types,
            "colour": colour,
            "n_positions": n_positions,
            "n_trees": len(families),
            "alpha": round(1 - 0.01 ** (1 / len(families)), 6),
        })
    (data_dir / "forests.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def tree_rows(families) -> list[dict]:
    """Per-family Newick, groupOTU span order, and each span's convergence.

    Same construction as the archived overlay scripts: spans sorted by size
    (descending) to build the tree, then by left edge for groupOTU. Thickness
    isn't stored -- the overlay charts raise convergence to a drawing-choice
    exponent, so R does that.
    """
    rows = []
    for tree_number, family_set in enumerate(families, start=1):
        family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
        children = get_children(build_parent_map(family_list))
        root = max(family_list, key=lambda s: s.size)
        ordered = sorted(family_list, key=lambda s: s.left)
        rows.append({
            "tree_number": tree_number,
            "newick": span_to_newick(root, children) + ";",
            "group_spans": ";".join(f"{s.left}-{s.right}" for s in ordered),
            "group_convergence": ";".join(str(s.convergence) for s in ordered),
        })
    return rows


def export_overlay_groups(domain_file: Path, domains_dir: Path, data_dir: Path,
                          n_positions: int | None = None) -> None:
    """Write the trees of every group the overlay charts can stack.

    One group per laminar_analysis.OVERLAY_GROUPS
    entry (the subset's families, but using the FULL dataset's position count,
    unlike the per-class forests), plus group "all" (every family of the full
    dataset, drawn in black by nyan1308_all_families_labeled.r). Groups whose
    domain types don't occur in the data are skipped.
    """
    group_dir = data_dir / "overlay_groups"
    group_dir.mkdir(parents=True, exist_ok=True)
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    _, n_positions = load_spans(domain_file.name, str(domains_dir), n_positions=n_positions)
    groups = [(short, list(types), colour) for types, colour, short in OVERLAY_GROUPS]
    groups.append(("all", None, "black"))
    index = []
    for group_id, types, colour in groups:
        if types is not None and not set(types) & observed:
            continue
        spans, _ = load_spans(domain_file.name, str(domains_dir), subset=types)
        if not spans:
            continue
        families, truncated = enumerate_maximal_laminar_families(
            spans, find_conflicts(spans), n_positions
        )
        if truncated:
            raise RuntimeError(f"Family enumeration was truncated for overlay group {group_id!r}.")
        write_tsv(group_dir / f"{group_id}.tsv",
                  ["tree_number", "newick", "group_spans", "group_convergence"], tree_rows(families))
        index.append({
            "group_id": group_id,
            "domain_types": types,
            "colour": colour,
            "n_trees": len(families),
        })
    (data_dir / "overlay_groups.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def export_highlights(dataset: str, data_dir: Path, highlights_file: Path | None) -> None:
    """Copy a dataset's named position highlights into the bundle.

    Highlights (e.g. nyan1308's orthographic word, positions 5-19, with the
    final vowel at 17 called out) are facts about the language, so they are
    data: planar_tables/highlights_<dataset>.tsv, columns highlight_id, name,
    left, right, colour (a default the chart may override), layer (later
    layers win where ranges overlap). Absent file = no highlights.
    """
    if highlights_file is None:
        candidate = REPO_DIR / "planar_tables" / f"highlights_{dataset}.tsv"
        highlights_file = candidate if candidate.exists() else None
    fields = ["highlight_id", "name", "left", "right", "colour", "layer"]
    rows = []
    if highlights_file is not None:
        with highlights_file.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    write_tsv(data_dir / "highlights.tsv", fields, rows)


def export_tree_counts(domain_file: Path, domains_dir: Path, data_dir: Path) -> None:
    """Write tree_counts.tsv: the numbers behind the tree-count bar charts.

    Calls laminar_tree_counts.collect_counts() and collect_bundle_counts()
    unchanged (docs/PLAN_planarsviz_library.md section 4.3), so the four
    count columns equal that script's nyan1308_tree_counts.tsv. Types are
    counted in its CLASS_ORDER, then any other observed type alphabetically;
    types and bundles with no tests in this dataset are left out. Added
    columns: kind (all / class / bundle), label (the bar label: the type
    title-cased as that script does, or the bundle's display name) and colour
    (the type's colour from DOMAIN_TYPE_STYLE or the fallback grey, or the
    bundle's colour); empty for the all-tests rows, whose bar colours are a
    chart choice.
    """
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    bundles = [b for b in BUNDLES if set(b[1]) & observed]
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}
    bundle_style = {name: (display, colour) for name, _types, colour, display in bundles}

    rows = []
    for row in collect_counts(domain_file.name, domains_dir, classes):
        kind = "all" if row["class"] == "all" else "class"
        rows.append(dict(row, kind=kind,
                         label="" if kind == "all" else row["class"].title(),
                         colour="" if kind == "all" else palette.get(row["class"], FALLBACK_COLOUR)))
    for row in collect_bundle_counts(domain_file.name, domains_dir, bundles):
        display, colour = bundle_style[row["class"]]
        rows.append(dict(row, kind="bundle", label=display, colour=colour))
    write_tsv(data_dir / "tree_counts.tsv",
              ["condition", "class", "n_unique_spans", "n_maximal_laminar_families",
               "kind", "label", "colour"], rows)


def export_fragmentation_test(domain_file: Path, domains_dir: Path, data_dir: Path,
                              n_permutations: int, seed: int,
                              n_positions: int | None = None) -> dict:
    """Write fragmentation_test.tsv and fragmentation_null.tsv.

    Calls class_fragmentation_test.run_test() unchanged, so the numbers equal
    that script's own committed TSVs. Groups are built from the domain types
    the data actually has, the way export_tree_counts() does, rather than from
    a fixed list -- a dataset with a type this project doesn't know still gets
    a row, with the fallback colour.

    The null draws go in as a tally (one row per distinct family count per
    group) rather than one row per draw. That is lossless for everything the
    chart and the p-value need -- only draw order is dropped, and the seed
    reproduces that -- and it is the difference between 227 rows and
    n_permutations x groups, which for nyan1308 at 5000 draws would be 40,000
    rows and a file nearly twice the size of the whole rest of the bundle.
    Decision recorded in docs/PLANARSVIZ_LIBRARY_PROGRESS.md, 2026-09-20.

    Not run unless asked: at 5000 draws this takes about four minutes against
    the 1.6 seconds the rest of the export costs, so it sits behind
    --fragmentation-permutations rather than on the default path.
    """
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    bundles = [b for b in BUNDLES if set(b[1]) & observed]
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}

    groups = [(c, [c]) for c in classes] + [(name, list(types)) for name, types, _c, _d in bundles]
    summary, null_counts = run_fragmentation_test(
        domain_file.name, domains_dir, groups=groups,
        n_permutations=n_permutations, seed=seed, n_positions=n_positions,
    )

    bundle_style = {name: (display, colour) for name, _types, colour, display in bundles}
    rows = []
    for row in summary:
        name = row["group"]
        if name in bundle_style:
            label, colour = bundle_style[name]
            kind = "bundle"
        else:
            label, colour = name.title(), palette.get(name, FALLBACK_COLOUR)
            kind = "class"
        rows.append({k: v for k, v in row.items() if k != "color"}
                    | {"kind": kind, "label": label, "colour": colour,
                       "n_permutations": n_permutations, "seed": seed})
    kind_of = {r["group"]: r["kind"] for r in rows}
    write_tsv(data_dir / "fragmentation_test.tsv",
              ["group", "kind", "label", "colour", "n_tests", "observed_families",
               "null_mean", "null_p05", "null_p95", "p_value_le_observed",
               "n_permutations", "seed"], rows)

    tally = []
    for name, counts in null_counts.items():
        for family_count, n in sorted(collections.Counter(counts).items()):
            tally.append({"group": name, "kind": kind_of[name],
                          "family_count": family_count, "n": n})
    write_tsv(data_dir / "fragmentation_null.tsv",
              ["group", "kind", "family_count", "n"], tally)
    return {"fragmentation_permutations": n_permutations, "fragmentation_seed": seed}


def export_span_placement_test(domain_file: Path, domains_dir: Path, data_dir: Path,
                               n_permutations: int, seed: int,
                               n_positions: int | None = None) -> dict:
    """Write span_placement_test.tsv and span_placement_null.tsv: does the
    real arrangement of a group's spans produce fewer laminar families than
    the same span *lengths* placed at random would?

    Calls span_placement_test.run_test() unchanged, so the numbers equal that
    script's own committed nyan1308_span_placement_test.tsv. Groups and their
    label/colour follow export_boundary_strength_test()'s convention, which
    means the same group order that script's own GROUPS uses -- "all" first,
    then the domain types in CLASS_ORDER, then the bundles. The order is
    load-bearing, not cosmetic: run_test() advances one shared random stream
    across the groups in the order given, so a different order would give
    different (still valid, but no longer comparable) null draws.

    The pooled row is labelled "All (pooled)" rather than
    export_boundary_strength_test()'s "All tests", because this test pools
    spans and that one pools tests. Each table carries its own label column
    for exactly this reason.

    Null counts go in as a tally, for the same reason and in the same shape
    as export_fragmentation_test()'s.

    Not run unless asked, for the same reason as --fragmentation-permutations:
    one family enumeration per replicate costs minutes.
    """
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    bundles = [b for b in BUNDLES if set(b[1]) & observed]
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}
    bundle_style = {name: (display, colour) for name, _types, colour, display in bundles}

    groups = [("all", None)] + [(c, [c]) for c in classes] + [(name, list(types)) for name, types, _c, _d in bundles]
    summary, null_tallies = run_span_placement_test(
        domain_file.name, domains_dir, groups=groups,
        n_permutations=n_permutations, seed=seed, n_positions=n_positions,
    )

    rows = []
    for row in summary:
        name = row["group"]
        if name == "all":
            kind, label, colour = "all", "All (pooled)", "#0072B2"
        elif name in bundle_style:
            label, colour = bundle_style[name]
            kind = "bundle"
        else:
            label, colour = name.title(), palette.get(name, FALLBACK_COLOUR)
            kind = "class"
        rows.append(dict(row) | {"kind": kind, "label": label, "colour": colour})
    write_tsv(data_dir / "span_placement_test.tsv",
              ["group", "kind", "label", "colour", "n_spans", "n_positions",
               "observed_families", "null_mean", "null_p05", "null_p50", "null_p95",
               "p_value_le_observed", "n_truncated", "n_permutations", "seed"], rows)

    kind_of = {r["group"]: r["kind"] for r in rows}
    tally = []
    for name, counts in null_tallies.items():
        for family_count in sorted(counts):
            tally.append({"group": name, "kind": kind_of[name],
                          "family_count": family_count, "n": counts[family_count]})
    write_tsv(data_dir / "span_placement_null.tsv",
              ["group", "kind", "family_count", "n"], tally)
    return {"span_placement_permutations": n_permutations, "span_placement_seed": seed}


def export_arbitrary_layers_test(domain_file: Path, domains_dir: Path, data_dir: Path,
                                 n_permutations: int, seed: int,
                                 n_positions: int | None = None) -> dict:
    """Write arbitrary_layers_test.tsv and arbitrary_layers_null.tsv: is a
    group's family count remarkable for that many spans of arbitrary size at
    arbitrary positions?

    The most naive of the three permutation nulls -- see
    arbitrary_layers_test.py's module docstring for how the three differ and
    why the weakest one is the one a raw family count is usually read against.

    Calls arbitrary_layers_test.run_test() unchanged, so the numbers equal
    that script's own committed TSVs. Group order, labels and colours follow
    export_span_placement_test() exactly, including its pooled row, and for
    the same reason: run_test() advances one shared random stream across the
    groups in the order given.

    Not run unless asked, for the same reason as --fragmentation-permutations.
    """
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    bundles = [b for b in BUNDLES if set(b[1]) & observed]
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}
    bundle_style = {name: (display, colour) for name, _types, colour, display in bundles}

    groups = [("all", None)] + [(c, [c]) for c in classes] + [(name, list(types)) for name, types, _c, _d in bundles]
    summary, null_tallies = run_arbitrary_layers_test(
        domain_file.name, domains_dir, groups=groups,
        n_permutations=n_permutations, seed=seed, n_positions=n_positions,
    )

    rows = []
    for row in summary:
        name = row["group"]
        if name == "all":
            kind, label, colour = "all", "All (pooled)", "#0072B2"
        elif name in bundle_style:
            label, colour = bundle_style[name]
            kind = "bundle"
        else:
            label, colour = name.title(), palette.get(name, FALLBACK_COLOUR)
            kind = "class"
        rows.append(dict(row) | {"kind": kind, "label": label, "colour": colour})
    write_tsv(data_dir / "arbitrary_layers_test.tsv",
              ["group", "kind", "label", "colour", "n_spans", "n_positions", "includes_root",
               "observed_families", "null_mean", "null_p05", "null_p50", "null_p95",
               "p_value_le_observed", "n_truncated", "n_permutations", "seed"], rows)

    kind_of = {r["group"]: r["kind"] for r in rows}
    tally = []
    for name, counts in null_tallies.items():
        for family_count in sorted(counts):
            tally.append({"group": name, "kind": kind_of[name],
                          "family_count": family_count, "n": counts[family_count]})
    write_tsv(data_dir / "arbitrary_layers_null.tsv",
              ["group", "kind", "family_count", "n"], tally)
    return {"arbitrary_layers_permutations": n_permutations, "arbitrary_layers_seed": seed}


def export_boundary_strength_test(domain_file: Path, domains_dir: Path, data_dir: Path,
                                  n_permutations: int, seed: int,
                                  n_positions: int | None = None) -> dict:
    """Write boundary_strength_test.tsv: is the per-position boundary
    strength (and its jump from the previous position) higher than a
    same-length-profile random arrangement would produce?

    Calls boundary_strength_test.run_test() unchanged, so the numbers equal
    that script's own committed nyan1308_boundary_strength_test.tsv. Groups
    and their label/colour follow export_fragmentation_test()'s convention
    exactly (only domain types the data actually has, only bundles with a
    type in it).

    Not run unless asked, for the same reason as
    --fragmentation-permutations: the permutation itself (one family
    enumeration per replicate, same as span_placement_test.py) costs
    minutes, not the ~2 seconds the rest of the export takes.
    """
    observed = set(
        pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")["Domain_Type"].dropna().str.strip()
    )
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    bundles = [b for b in BUNDLES if set(b[1]) & observed]
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}
    bundle_style = {name: (display, colour) for name, _types, colour, display in bundles}

    groups = [("all", None)] + [(c, [c]) for c in classes] + [(name, list(types)) for name, types, _c, _d in bundles]
    rows = run_boundary_strength_test(
        domain_file.name, domains_dir, groups=groups,
        n_permutations=n_permutations, seed=seed, n_positions=n_positions,
    )
    for row in rows:
        name = row["group"]
        if name == "all":
            row["kind"], row["label"], row["colour"] = "all", "All tests", "#000000"
        elif name in bundle_style:
            row["label"], row["colour"] = bundle_style[name]
            row["kind"] = "bundle"
        else:
            row["label"], row["colour"] = name.title(), palette.get(name, FALLBACK_COLOUR)
            row["kind"] = "class"
    write_tsv(data_dir / "boundary_strength_test.tsv",
              ["group", "kind", "label", "colour", "side", "statistic", "position", "observed",
               "null_mean", "null_p05", "null_p95", "p_value_ge_observed",
               "n_permutations", "seed"], rows)
    return {"boundary_strength_test_permutations": n_permutations, "boundary_strength_test_seed": seed}


def export_boundary_strength(domain_file: Path, domains_dir: Path, target_dir: Path,
                             subset: list[str] | None = None,
                             n_positions: int | None = None) -> None:
    """Write boundary_strength.tsv for the full data or one subset analysis.

    Calls boundary_strength.compute_boundary_strength() unchanged
    (docs/PLAN_planarsviz_library.md section 4.3), so the columns and values
    equal that script's nyan1308_boundary_strength.tsv -- and, for
    subsets/no_tono, the committed nyan1308_boundary_strength_no_tono.tsv,
    which is the same four domain types (checked 2026-09-15). One row per
    position up to the analysis's largest right edge, or up to n_positions
    when given (the full analysis passes the planar structure's count; subset
    analyses don't, which is what keeps no_tono equal to that file).
    """
    rows, _n_families = compute_boundary_strength(domain_file.name, domains_dir, subset=subset,
                                                  n_positions=n_positions)
    write_tsv(target_dir / "boundary_strength.tsv",
              ["position", "left_summed", "left_capped", "right_summed", "right_capped"], rows)

    # The distributions chart's curves: save_distribution_figure()'s
    # gaussian_kde(positions, weights=summed, bw_method=0.15) on its grid of
    # 400 points from the first position - 1 to the last + 1.
    positions = np.array([row["position"] for row in rows], dtype=float)
    grid = np.linspace(positions.min() - 1, positions.max() + 1, 400)
    density_rows = [{"x": repr(float(x))} for x in grid]
    for side in ("left", "right"):
        weights = np.array([row[f"{side}_summed"] for row in rows], dtype=float)
        values = weighted_gaussian_kde(positions, weights, grid, 0.15)
        for density_row, value in zip(density_rows, values):
            density_row[side] = "" if value is None else repr(float(value))
    write_tsv(target_dir / "boundary_strength_density.tsv", ["x", "left", "right"], density_rows)


def weighted_gaussian_kde(points, weights, grid, factor):
    """scipy.stats.gaussian_kde(points, weights=weights, bw_method=factor)(grid),
    rebuilt in numpy. It was written when scipy was missing from the
    project's environment; scipy is now a declared dependency, and
    scripts/planarsviz_checks/verify_boundary_density.py confirms this equals
    scipy's result (largest difference 1.3e-14), so the exporter keeps the
    numpy version and doesn't need scipy. scipy's rule for a numeric
    bw_method: normalise the weights to sum to 1; kernel variance = the
    weighted variance of the points (numpy.cov with aweights, bias=False)
    times factor squared; density = sum of weight x normal density centred on
    each point. Returns a list of None where scipy would refuse (no weight,
    or all weight on one point).
    """
    w = np.asarray(weights, dtype=float)
    if w.sum() <= 0 or np.count_nonzero(w) < 2:
        return [None] * len(grid)
    points = np.asarray(points, dtype=float)
    w = w / w.sum()
    variance = float(np.cov(points, aweights=w, bias=False)) * factor ** 2
    diff = grid[:, None] - points[None, :]
    kernel = np.exp(-diff ** 2 / (2 * variance)) / np.sqrt(2 * np.pi * variance)
    return list(kernel @ w)


def family_newick(family) -> str:
    """Newick string for one family, built the way every tree chart builds it:
    spans by size (largest first) for the parent map, the largest as root."""
    family_list = sorted(family, key=lambda s: s.size, reverse=True)
    root = max(family_list, key=lambda s: s.size)
    return span_to_newick(root, get_children(build_parent_map(family_list))) + ";"


def load_conflict_group_config(dataset: str, conflict_groups_file: Path | None):
    """(group_id, defining_span_id) pairs, and the file they came from.

    Which spans split the families into groups is a fact about the language
    (nyan1308's central conflict is [5-13] vs [6-17]), so it is data:
    planar_tables/conflict_groups_<dataset>.tsv, columns group_id and
    defining_span_id. One row may leave defining_span_id empty: that group
    gets every family not in another group. Absent file = no groups.
    """
    if conflict_groups_file is None:
        candidate = REPO_DIR / "planar_tables" / f"conflict_groups_{dataset}.tsv"
        conflict_groups_file = candidate if candidate.exists() else None
    if conflict_groups_file is None:
        return [], None
    with conflict_groups_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    config = [(row["group_id"].strip(), (row.get("defining_span_id") or "").strip()) for row in rows]
    if sum(not span for _, span in config) > 1:
        raise ValueError(f"Only one group may have an empty defining_span_id: {conflict_groups_file}")
    return config, conflict_groups_file


def capped_draw_order(members: list[int], families, cap: int) -> list[int]:
    """Which members of a group the conflict-groups chart draws, in order.

    Recovered 2026-09-14 from laminar_conflict_groups.r (its generator was
    never committed; the script is archived in
    OlderFiles/planarsviz_superseded/results/, and
    docs/PLAN_planarsviz_library.md section 4.1 covers it). A group
    no larger than the cap is drawn whole, in family order. A larger group is
    seeded by greedy coverage -- repeatedly the member adding the most spans
    not yet shown, ties to the lower family number, until every span in the
    group is shown -- then filled up to the cap in family order.
    """
    if cap < 1:
        raise ValueError("The conflict-group cap must be at least 1.")
    if len(members) <= cap:
        return list(members)
    in_group = set().union(*(families[i] for i in members))
    covered: set = set()
    chosen: list[int] = []
    while covered != in_group and len(chosen) < cap:
        best = max((i for i in members if i not in chosen),
                   key=lambda i: (len(families[i] - covered), -i))
        chosen.append(best)
        covered |= families[best]
    chosen += [i for i in members if i not in chosen][: cap - len(chosen)]
    return chosen


def branching_profile(family, children) -> tuple[int, int]:
    """(binary nodes, children at the widest node) for one family's tree.

    A node's children are the spans directly inside it plus the positions it
    covers that no child span covers -- what the drawn tree actually shows.
    """
    counts = []
    for span in family:
        child_spans = children.get(span, [])
        covered = {p for child in child_spans for p in range(child.left, child.right + 1)}
        exposed = sum(1 for p in range(span.left, span.right + 1) if p not in covered)
        counts.append(len(child_spans) + exposed)
    return sum(1 for n in counts if n == 2), max(counts)


def most_binary_order(families) -> list[int]:
    """Family numbers ordered by how binary their branching is, best first.

    Every observed span rests on at least one test, so the most binary tree
    is simply the one that packs in the most compatible spans and spreads
    them best. Order: most strictly binary nodes, then most tests supporting
    the tree as a whole, then the narrowest widest node, then family order.
    """
    ranked = []
    for number, family in enumerate(families):
        family_list = sorted(family, key=lambda s: s.size, reverse=True)
        children = get_children(build_parent_map(family_list))
        binary, widest = branching_profile(family_list, children)
        support = sum(span.convergence for span in family_list)
        ranked.append((-binary, -support, widest, number))
    ranked.sort()
    return [number for _, _, _, number in ranked]


def export_selections(dataset: str, families, data_dir: Path,
                      conflict_groups_file: Path | None, cap: int,
                      exemplary_k: int = 6, include_sparsest: bool = True) -> dict:
    """Write conflict_groups.tsv and selections.tsv; return metadata fields.

    conflict_groups.tsv: every family's group (group_id, defining_span_id,
    family_id) and draw_rank (empty = not drawn under the cap). A family
    containing more than one defining span goes to the first group listed.

    selections.tsv (selection, rank, family_id):
    - consensus_all and consensus_<group_id>: the family with the highest
      consensus score, the sum over its spans of each span's family count
      across ALL families. Recovered from laminar_four_trees.r and
      laminar_freqtree.r (section 4.1; unique for nyan1308). Ties, never
      seen, go to the lower family number.
    - most_binary, rank 1: the family that branches most binarily -- for
      illustrating the structure with as much branching as the evidence
      allows. See most_binary_order().
    - exemplary, ranks 1..: select_representative_families(k=exemplary_k),
      then (include_sparsest) one more beyond those -- the family drawing on
      the fewest individual tests, ties broken by fewest distinct domain
      types, if it is not already among them. The greedy-coverage selection
      has no reason to pick the sparsest family on its own -- coverage and
      consensus favour families that explain a lot, and a sparse family by
      definition doesn't -- so this is a deliberate second axis (least
      evidence) alongside the first (most representative), not something
      k + 1 on the main selection would surface. For nyan1308 the two
      sparsity criteria agree exactly: family 67 in enumeration order is the
      unique minimum on both at once, 21 tests and 3 domain types.
    """
    family_ids = [f"family_{number:03d}" for number in range(1, len(families) + 1)]
    count: dict = {}
    for family in families:
        for span in family:
            count[span] = count.get(span, 0) + 1
    score = [sum(count[span] for span in family) for family in families]

    def consensus(members):
        return max(members, key=lambda i: (score[i], -i))

    config, source = load_conflict_group_config(dataset, conflict_groups_file)
    known = {span_id(span) for family in families for span in family}
    groups: dict[str, tuple[str, list[int]]] = {}
    assigned: set[int] = set()
    for group_id, defining in config:
        if not defining:
            continue
        if defining not in known:
            raise ValueError(f"Conflict group {group_id!r}: span {defining} is not in the data.")
        members = [i for i, family in enumerate(families)
                   if i not in assigned and any(span_id(s) == defining for s in family)]
        assigned.update(members)
        groups[group_id] = (defining, members)
    for group_id, defining in config:
        if not defining:
            groups[group_id] = ("", [i for i in range(len(families)) if i not in assigned])

    group_rows = []
    selection_rows = [{"selection": "consensus_all", "rank": 1,
                       "family_id": family_ids[consensus(range(len(families)))]}]
    for group_id, _ in config:
        defining, members = groups[group_id]
        draw_rank = {i: rank for rank, i in enumerate(capped_draw_order(members, families, cap), start=1)}
        for i in members:
            group_rows.append({"group_id": group_id, "defining_span_id": defining,
                               "family_id": family_ids[i], "draw_rank": draw_rank.get(i, "")})
        if members:
            selection_rows.append({"selection": f"consensus_{group_id}", "rank": 1,
                                   "family_id": family_ids[consensus(members)]})
    for rank, family_number in enumerate(most_binary_order(families)[:1], start=1):
        selection_rows.append({"selection": "most_binary", "rank": rank,
                               "family_id": family_ids[family_number]})

    selected = select_representative_families(families, count, k=exemplary_k)
    if include_sparsest:
        def sparsity(family):
            return (len({label for s in family for label in s.labels}),
                    len({t for s in family for t in s.domain_types}))
        sparsest = min(families, key=sparsity)
        if sparsest not in selected:
            selected = selected + [sparsest]
    for rank, family in enumerate(selected, start=1):
        selection_rows.append({"selection": "exemplary", "rank": rank,
                               "family_id": family_ids[families.index(family)]})

    write_tsv(data_dir / "conflict_groups.tsv",
              ["group_id", "defining_span_id", "family_id", "draw_rank"], group_rows)
    write_tsv(data_dir / "selections.tsv", ["selection", "rank", "family_id"], selection_rows)
    return {
        "exemplary_k": exemplary_k,
        "exemplary_include_sparsest": include_sparsest,
        "conflict_group_cap": cap,
        "source_conflict_groups_file": (
            str(source.relative_to(REPO_DIR)) if source and source.is_relative_to(REPO_DIR)
            else str(source) if source else None
        ),
    }

# Domain-type display style: the order types are sorted in within a layer
# (df.plot()'s factor levels), the order they appear in a legend, and the order
# of per-type panels (facet_order, from nyan_boundary_skyline.r's facet levels
# -- a third, different order, kept as-is so that chart doesn't change). The
# first two orders are copied from domain_charts-cgpt.r (df.plot() levels,
# constituency.plot() breaks), archived under OlderFiles/planarsviz_superseded/.
# A domain type observed in the data but not listed here gets FALLBACK_COLOUR
# and sorts after the known types, alphabetically.
#
# The `colour` of each type is NOT written here: it is read from
# laminar_tree_counts.CLASS_COLORS below, which is the one place in the project
# those five colours are written down. Everything R draws in them arrives
# through this table, so the bundle is where R gets them from, but the values
# themselves have a single owner.
#
# alt_colour / colour_priority: the second palette used by the span-frequency
# chart (the archived laminar_spanchart.r, Paul Tol's "bright" colours). A span
# with several domain types takes the alt_colour of its type with the lowest
# colour_priority. Recovered from that script's data: morphosyntactic,
# phonological, tonosegmental and intonational colours and the priority
# order are exactly reproduced; length never decides a colour there (every
# length span also has a higher-priority type), so its #AA3377 (Tol purple,
# matching visualizations.md's "length = purple") is inferred, not observed.
_DOMAIN_TYPE_ORDERS: list[dict] = [
    {"domain_type": "morphosyntactic", "sort_order": 1, "legend_order": 1, "facet_order": 1,
     "alt_colour": "#EE6677", "colour_priority": 1},
    {"domain_type": "tonosegmental", "sort_order": 2, "legend_order": 5, "facet_order": 3,
     "alt_colour": "#228833", "colour_priority": 3},
    {"domain_type": "length", "sort_order": 3, "legend_order": 3, "facet_order": 5,
     "alt_colour": "#AA3377", "colour_priority": 5},
    {"domain_type": "phonological", "sort_order": 4, "legend_order": 2, "facet_order": 2,
     "alt_colour": "#4477AA", "colour_priority": 2},
    {"domain_type": "intonational", "sort_order": 5, "legend_order": 4, "facet_order": 4,
     "alt_colour": "#CCBB44", "colour_priority": 4},
]
DOMAIN_TYPE_STYLE: list[dict] = [
    dict(row, colour=CLASS_COLORS[row["domain_type"]]) for row in _DOMAIN_TYPE_ORDERS
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
            "alt_colour": FALLBACK_COLOUR,
            "colour_priority": len(DOMAIN_TYPE_STYLE) + i,
            "known": False,
        })
    return rows


def blend_colour(domain_types) -> str:
    """One colour for a span with one or more domain types.

    Copied from scripts/make_forestspans_table.py mix_hex_colors() (the
    ForestSpans chart's colours): a plain per-channel average of the pure
    domain-type colours, rounded with Python's round(). A single type gives
    its own colour exactly. One change: that function skipped types missing
    from its palette; here an unknown observed type contributes the fallback
    grey, as it does in every other chart. The synthetic root has no type and
    gets black, as an empty list did there.
    """
    palette = {row["domain_type"]: row["colour"] for row in DOMAIN_TYPE_STYLE}
    cols = [palette.get(t, FALLBACK_COLOUR) for t in sorted(domain_types) if t != "(synthetic)"]
    if not cols:
        return "#000000"
    rs = [int(c[1:3], 16) for c in cols]
    gs = [int(c[3:5], 16) for c in cols]
    bs = [int(c[5:7], 16) for c in cols]
    r, g, b = (round(sum(vals) / len(vals)) for vals in (rs, gs, bs))
    return "#%02X%02X%02X" % (r, g, b)


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


def planar_position_count(planar_file: Path | None) -> int | None:
    """Number of positions in the planar table, or None without one.

    The table's rows are its positions; load_position_labels() separately
    checks they run 1..N with no gaps.
    """
    if planar_file is None or not planar_file.exists():
        return None
    with planar_file.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle, delimiter="\t"))


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
    highlights_file: Path | None = None,
    conflict_groups_file: Path | None = None,
    conflict_group_cap: int = 12,
    exemplary_k: int = 6,
    exemplary_include_sparsest: bool = True,
    fragmentation_permutations: int = 0,
    fragmentation_seed: int = 0,
    boundary_strength_test_permutations: int = 0,
    boundary_strength_test_seed: int = 0,
    span_placement_permutations: int = 0,
    span_placement_seed: int = 0,
    arbitrary_layers_permutations: int = 0,
    arbitrary_layers_seed: int = 0,
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

    if planar_file is None:
        candidate = REPO_DIR / "planar_tables" / f"planar_{dataset}.tsv"
        planar_file = candidate if candidate.exists() else None

    # Keep the full dataset's position count for every subset.  A subset may
    # stop before the final planar position but its trees still use the full
    # root coordinate system. With a planar table, that count is the table's:
    # the axis is the planar structure, not the data, and a structure's last
    # positions may be reached by no test. Without one, the largest right edge.
    planar_n = planar_position_count(planar_file)
    full_spans, n_positions = load_spans(domain_file.name, str(domains_dir),
                                         n_positions=planar_n)
    if not full_spans:
        raise ValueError(f"No usable spans found in {domain_file}.")

    def write_analysis_tables(target_dir, spans, families, adjacency, subset_tests):
        target_dir.mkdir(parents=True, exist_ok=True)
        span_lookup = {span_id(span): span for span in spans}
        span_family_count = {
            key: sum(span in family for family in families)
            for key, span in span_lookup.items()
        }
        # Row order of the span-frequency chart (laminar_spanchart.r, whose
        # generator was never committed; recovered 2026-09-15 by matching its
        # rows): every span except the full root, sorted by family count
        # ascending; ties keep the order in which the spans are first met
        # when iterating the families in order and each family's frozenset in
        # Python's iteration order -- how laminar_analysis.report_families()
        # builds its count dict. That tie order is deterministic but
        # arbitrary; it is kept only so the chart reproduces exactly.
        first_counted: dict[str, int] = {}
        for family in families:
            for span in family:
                first_counted.setdefault(span_id(span), len(first_counted))
        charted = [
            key for key, span in span_lookup.items()
            if not (span.left == 1 and span.right == n_positions)
        ]
        charted.sort(key=lambda key: first_counted.get(key, len(first_counted)))
        charted.sort(key=lambda key: span_family_count[key])
        span_chart_rank = {key: rank for rank, key in enumerate(charted, start=1)}
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
                "span_chart_rank": span_chart_rank.get(key, ""),
                "blend_colour": blend_colour(span.domain_types),
            })
        write_tsv(target_dir / "spans.tsv", [
            "span_id", "left", "right", "size", "convergence",
            "family_frequency", "labels", "domain_types", "synthetic",
            "span_chart_rank", "blend_colour"
        ], span_rows)

        family_rows = []
        membership_rows = []
        for family_number, family in enumerate(families, start=1):
            family_id = f"family_{family_number:03d}"
            family_rows.append({
                "family_id": family_id,
                "family_number": family_number,
                "n_spans": len(family),
                "newick": family_newick(family),
            })
            for span in sorted(family, key=lambda item: (item.left, item.right)):
                membership_rows.append({"family_id": family_id, "span_id": span_id(span)})
        write_tsv(target_dir / "families.tsv", ["family_id", "family_number", "n_spans", "newick"], family_rows)
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
    selection_metadata = export_selections(dataset, families, data_dir,
                                           conflict_groups_file, conflict_group_cap,
                                           exemplary_k, exemplary_include_sparsest)

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
              ["domain_type", "colour", "sort_order", "legend_order", "facet_order",
               "alt_colour", "colour_priority", "known"],
              domain_type_rows(observed_types))

    # Off unless asked: the permutation test is minutes, the rest of the
    # export is seconds. A bundle without it simply has no fragmentation
    # tables, and plot_fragmentation_test() says so rather than failing
    # obscurely.
    fragmentation_metadata: dict = {}
    if fragmentation_permutations:
        fragmentation_metadata = export_fragmentation_test(
            domain_file, domains_dir, data_dir,
            fragmentation_permutations, fragmentation_seed, n_positions,
        )

    boundary_strength_test_metadata: dict = {}
    if boundary_strength_test_permutations:
        boundary_strength_test_metadata = export_boundary_strength_test(
            domain_file, domains_dir, data_dir,
            boundary_strength_test_permutations, boundary_strength_test_seed, n_positions,
        )

    span_placement_metadata: dict = {}
    if span_placement_permutations:
        span_placement_metadata = export_span_placement_test(
            domain_file, domains_dir, data_dir,
            span_placement_permutations, span_placement_seed, n_positions,
        )

    arbitrary_layers_metadata: dict = {}
    if arbitrary_layers_permutations:
        arbitrary_layers_metadata = export_arbitrary_layers_test(
            domain_file, domains_dir, data_dir,
            arbitrary_layers_permutations, arbitrary_layers_seed, n_positions,
        )

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
        **selection_metadata,
        **fragmentation_metadata,
        **boundary_strength_test_metadata,
        **span_placement_metadata,
        **arbitrary_layers_metadata,
        "producer": "scripts/analysis/export_planarsviz_data.py",
        "analysis_source": "scripts/analysis/laminar_analysis.py",
    }
    (data_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Fresh analyses of part of the data: one per observed domain type
    # (kind "domain_type"), and one per planars_groupings.FILTERS entry that
    # leaves out a type this dataset actually has (kind "filter"; e.g.
    # no_tono, the ForestSpans no-tonosegmental chart).
    domain_types = sorted(t.strip() for t in tests["Domain_Type"].dropna().unique())
    subset_specs = [
        (domain_type.lower().replace(" ", "_").replace("-", "_"), "domain_type", [domain_type])
        for domain_type in domain_types
    ]
    for filter_id, excluded in FILTERS:
        if set(excluded) & set(domain_types):
            subset_specs.append((filter_id, "filter", [t for t in domain_types if t not in excluded]))
    subset_index = []
    for subset_slug, subset_kind, subset_types in subset_specs:
        subset_tests = tests[tests["Domain_Type"].str.strip().isin(subset_types)].copy()
        subset_spans, _ = load_spans(
            domain_file.name, str(domains_dir), subset=subset_types
        )
        if not subset_spans:
            continue
        subset_adjacency = find_conflicts(subset_spans)
        subset_families, subset_truncated = enumerate_maximal_laminar_families(
            subset_spans, subset_adjacency, n_positions
        )
        if subset_truncated:
            raise RuntimeError(
                f"Family enumeration was truncated for subset {subset_slug!r}."
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
            "kind": subset_kind,
            "domain_type": subset_types[0] if subset_kind == "domain_type" else None,
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
            "domain_types": subset_types,
        }
        (subset_dir / "metadata.json").write_text(
            json.dumps(subset_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        export_boundary_strength(domain_file, domains_dir, subset_dir, subset_types)
        subset_index.append({
            "subset_id": subset_slug,
            "kind": subset_kind,
            "domain_type": subset_types[0] if subset_kind == "domain_type" else None,
            "domain_types": subset_types,
            "path": f"subsets/{subset_slug}",
            "n_active_tests": len(subset_tests),
            "n_unique_spans": n_observed_subset_spans,
            "n_maximal_families": len(subset_families),
        })
    (data_dir / "subsets.json").write_text(
        json.dumps(subset_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    export_forests(domain_file, domains_dir, data_dir)
    export_overlay_groups(domain_file, domains_dir, data_dir, n_positions)
    export_highlights(dataset, data_dir, highlights_file)
    export_tree_counts(domain_file, domains_dir, data_dir)
    export_boundary_strength(domain_file, domains_dir, data_dir, n_positions=n_positions)
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
    parser.add_argument(
        "--highlights-file", type=Path, default=None,
        help="TSV of named position highlights; default planar_tables/highlights_<dataset>.tsv if present",
    )
    parser.add_argument(
        "--conflict-groups-file", type=Path, default=None,
        help="TSV of group_id, defining_span_id; default planar_tables/conflict_groups_<dataset>.tsv if present",
    )
    parser.add_argument(
        "--conflict-group-cap", type=int, default=12,
        help="Most trees the conflict-groups chart draws per group (default: 12)",
    )
    parser.add_argument(
        "--exemplary-k", type=int, default=6,
        help="Representative families the exemplary-trees charts pick by coverage (default: 6)",
    )
    parser.add_argument(
        "--no-exemplary-sparsest", action="store_true",
        help="Don't add the family with the least evidence to the exemplary selection",
    )
    parser.add_argument(
        "--fragmentation-permutations", type=int, default=0, metavar="N",
        help="Also run the class-fragmentation permutation test with N draws and "
             "put its two tables in the bundle. Off by default because it is slow: "
             "5000 draws takes about four minutes against the rest of the export's "
             "1.6 seconds. Use 5000 to match the committed "
             "results/nyan1308/counts-and-chance/ files.",
    )
    parser.add_argument(
        "--fragmentation-seed", type=int, default=0,
        help="Seed for --fragmentation-permutations (default: 0, what made the committed files)",
    )
    parser.add_argument(
        "--boundary-strength-test-permutations", type=int, default=0, metavar="N",
        help="Also run the boundary-strength permutation test (is the per-position strength, "
             "and its jump from the previous position, higher than a same-length-profile random "
             "arrangement?) with N draws and put its table in the bundle. Off by default for the "
             "same reason as --fragmentation-permutations: one family enumeration per replicate, "
             "so 5000 draws takes minutes against the rest of the export's ~2 seconds. Use 5000 "
             "to match the committed results/nyan1308/boundaries/ files.",
    )
    parser.add_argument(
        "--boundary-strength-test-seed", type=int, default=0,
        help="Seed for --boundary-strength-test-permutations (default: 0, what made the committed files)",
    )
    parser.add_argument(
        "--span-placement-permutations", type=int, default=0, metavar="N",
        help="Also run the span-placement permutation test (does the real arrangement of a "
             "group's spans give fewer laminar families than those same span lengths placed at "
             "random?) with N draws and put its tables in the bundle. Off by default for the "
             "same reason as --fragmentation-permutations: one family enumeration per replicate. "
             "Use 5000 to match the committed results/nyan1308/counts-and-chance/ files.",
    )
    parser.add_argument(
        "--span-placement-seed", type=int, default=0,
        help="Seed for --span-placement-permutations (default: 0, what made the committed files)",
    )
    parser.add_argument(
        "--arbitrary-layers-permutations", type=int, default=0, metavar="N",
        help="Also run the arbitrary-layers permutation test (is a group's family count "
             "remarkable for that many spans of arbitrary size at arbitrary positions?) with N "
             "draws and put its tables in the bundle. The most naive of the three nulls: it "
             "knows only how many spans a group has, not how big they are. Off by default for "
             "the same reason as --fragmentation-permutations. Use 5000 to match the committed "
             "results/nyan1308/counts-and-chance/ files.",
    )
    parser.add_argument(
        "--arbitrary-layers-seed", type=int, default=0,
        help="Seed for --arbitrary-layers-permutations (default: 0, what made the committed files)",
    )
    args = parser.parse_args()

    bundle_dir = export_bundle(args.domain_file, args.output_dir, args.planar_file,
                               args.labels_file, args.root_element, args.language_name,
                               args.highlights_file, args.conflict_groups_file,
                               args.conflict_group_cap, args.exemplary_k,
                               not args.no_exemplary_sparsest,
                               # By name, not position: these are the tail of a long
                               # signature and each new permutation test adds a pair.
                               # Passed positionally, an addition that misses this call
                               # silently leaves the new test switched off rather than
                               # failing -- which is exactly what happened when
                               # --arbitrary-layers-permutations was added.
                               fragmentation_permutations=args.fragmentation_permutations,
                               fragmentation_seed=args.fragmentation_seed,
                               boundary_strength_test_permutations=args.boundary_strength_test_permutations,
                               boundary_strength_test_seed=args.boundary_strength_test_seed,
                               span_placement_permutations=args.span_placement_permutations,
                               span_placement_seed=args.span_placement_seed,
                               arbitrary_layers_permutations=args.arbitrary_layers_permutations,
                               arbitrary_layers_seed=args.arbitrary_layers_seed)
    print(f"Exported planarsviz bundle: {bundle_dir}")


if __name__ == "__main__":
    main()
