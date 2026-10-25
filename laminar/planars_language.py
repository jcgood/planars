"""Connect a language annotated through planars to the laminar analysis.

``python -m laminar.planars_language stan1293`` (dry run) / ``--apply``.

The analysis reads a domains file (one row per test: Test_Labels,
Domain_Type, Left_Edge, Right_Edge, Size); Chichewa's and the CCDB
structures' were written by hand or imported. For a planars language this
module builds them from the annotation, through
``planars.reports.language_spans`` (the one place spans are derived), so
nothing is copied by hand and every run reflects the current data.

**Datasets.** One planars language gives eight datasets, named
``<lang>_<grouping>_<selection>`` (docs/laminar-analysis-plan.md decisions 1,
2 and 4; every one is computed on every run):

- grouping ``types``: Domain_Type is the class's domain type and subtype
  from schemas/diagnostic_classes.yaml (``phonological-prosodic``); analysed
  with the ``planars_types`` groupings. ``classes``: Domain_Type is the class
  name; ``planars_classes`` groupings.
- selection (``SELECTIONS``): ``all`` every span; ``complete`` the spans
  built from complete positions (every element satisfies the span rule),
  plus the spans of classes with no complete/partial distinction;
  ``partial`` the same with partial positions; ``distinct`` every span, but
  a construction's spans that coincide (its strict and loose spans the
  same, or its partial and complete) count once -- provisional readings of
  decision 2, to revisit once English's charts are drawn.

**Labels.** A class's span labels repeat across its constructions
(``fill strict complete`` once per subspanrepetition construction), so a
label gets its construction in brackets when the class has more than one.
Labels must come out unique; a repeat fails rather than merging two tests.

**Weights** (decision 3). Each partial span carries three weights, from the
positions it gains over its complete counterpart and each one's *k of n*
(``planars.reports._span_rows``): ``Weight_Mean_Ratio`` (the average k/n,
each position counting equally; the default), ``Weight_Weakest`` (the lowest
k/n) and ``Weight_Element_Share`` (all k over all n). A span that gains
nothing, and every complete span, has weight 1. ``Gained_Positions`` lists
them (``28:9/10 29:21/30``) so another weighting can be computed later. A
loose span's gap is gained with k = 0. The analysis carries the weights
without using them; they reach the bundle because the exporter copies every
column of the domains file into its ``tests.tsv``.

**Where.** Inside the planars-data clone, since the spans derive from
unpublished annotation (decision 5): ``coded_data/.analysis/<lang>/domains/``,
beside the language's folders, not inside it, where the tooling would read
a new folder as a class. They are working files: planars-data's
.gitignore leaves ``.analysis/`` out, and nothing here commits them.
Beside each domains file, ``source_<dataset>.json``
records the planars-data commit (and whether the clone had uncommitted
changes), how complete the annotation is (``language_completeness``), and
which annotated classes give no spans yet; the exporter puts it in the
bundle's metadata, so a chart drawn mid-annotation says so. The planar
table is the language's live planar file, read where it is.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from laminar.datasets import REPO, repo_relative
from laminar.planars_groupings import planars_domain_type
from planars.languages import get_display_name
from planars.reports import language_completeness, language_spans
from planars.schema_values import class_domain_types, is_keystone

CODED_DATA = REPO / "coded_data"

GROUPINGS_BY = {"types": "planars_types", "classes": "planars_classes"}
SELECTIONS = ("all", "complete", "partial", "distinct")

# The domains file's columns: the five the analysis reads, then the ones it
# carries for the record.
DOMAIN_COLUMNS = ["Test_Labels", "Domain_Type", "Left_Edge", "Right_Edge", "Size",
                  "Class", "Construction", "Span_Key", "Position_Basis",
                  "Weight_Mean_Ratio", "Weight_Weakest", "Weight_Element_Share",
                  "Gained_Positions", "Same_Span_As"]


def analysis_dir(lang_id: str) -> Path:
    return CODED_DATA / ".analysis" / lang_id


def domains_dir(lang_id: str) -> Path:
    return analysis_dir(lang_id) / "domains"


def planar_file(lang_id: str) -> Path:
    return CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"


def dataset_name(lang_id: str, grouping: str, selection: str) -> str:
    return f"{lang_id}_{grouping}_{selection}"


def parse_dataset(dataset: str) -> tuple[str, str, str] | None:
    """(lang_id, grouping, selection) for a planars dataset name, None for any
    other dataset. Only the full pattern counts: a CCDB structure can start
    with a planars language's code (arao1248_verbal)."""
    parts = dataset.split("_")
    if len(parts) != 3 or parts[1] not in GROUPINGS_BY or parts[2] not in SELECTIONS:
        return None
    if not planar_file(parts[0]).exists():
        return None
    return parts[0], parts[1], parts[2]


def dataset_names(lang_id: str) -> list[str]:
    """Every dataset one planars language gives, in a fixed order."""
    return [dataset_name(lang_id, g, s) for g in GROUPINGS_BY for s in SELECTIONS]


def keystone_position(lang_id: str) -> int:
    """The keystone's position in the live planar file: the analysis's root."""
    planar = pd.read_csv(planar_file(lang_id), sep="\t", dtype=str, keep_default_na=False)
    rows = planar[planar["Position_Name"].map(is_keystone)]
    if len(rows) != 1:
        sys.exit(f"{repo_relative(planar_file(lang_id))}: expected one keystone row, found {len(rows)}.")
    return int(rows["Position"].iloc[0])


def planar_type(lang_id: str) -> str:
    planar = pd.read_csv(planar_file(lang_id), sep="\t", dtype=str, keep_default_na=False)
    kinds = sorted(set(planar["Planar_Type"]))
    if len(kinds) != 1:
        sys.exit(f"{repo_relative(planar_file(lang_id))}: expected one Planar_Type, found {kinds}.")
    return kinds[0]


# ── The span table ──────────────────────────────────────────────────────────

def _weights(gained: list[tuple[int, int, int]]) -> tuple[float, float, float]:
    """(mean ratio, weakest position, element share) of a span's gained
    positions; (1, 1, 1) when it gains none."""
    if not gained:
        return 1.0, 1.0, 1.0
    ratios = [k / n for _p, k, n in gained]
    share = sum(k for _p, k, _n in gained) / sum(n for _p, _k, n in gained)
    return (round(sum(ratios) / len(ratios), 4), round(min(ratios), 4), round(share, 4))


def span_table(lang_id: str) -> pd.DataFrame:
    """Every span the language's annotation gives, one row per test, with
    both groupings' Domain_Type (``Domain_Type_types``, ``Domain_Type_classes``)
    and the record columns of DOMAIN_COLUMNS."""
    spans, _meta = language_spans(lang_id, source="local", repo_root=REPO)
    if spans.empty:
        sys.exit(f"{get_display_name(lang_id)}: the annotation gives no spans yet.")
    types = class_domain_types()
    unknown = sorted(set(spans["Analysis"]) - set(types))
    if unknown:
        sys.exit(f"Classes with spans but no entry in schemas/diagnostic_classes.yaml: {unknown}")

    table = spans.rename(columns={"Analysis": "Class"}).copy()
    table["Domain_Type_types"] = [planars_domain_type(*types[c]) for c in table["Class"]]
    table["Domain_Type_classes"] = table["Class"]
    constructions = table.groupby("Class")["Construction"].nunique()
    table["Test_Labels"] = [
        f"{label} ({construction})" if constructions[cls] > 1 else label
        for label, cls, construction in zip(table["Test_Labels"], table["Class"], table["Construction"])
    ]
    repeated = table["Test_Labels"][table["Test_Labels"].duplicated()].tolist()
    if repeated:
        sys.exit(f"Span labels repeat, so two tests would merge: {sorted(set(repeated))}")
    weights = [_weights(g) for g in table["Gained_Positions"]]
    table["Weight_Mean_Ratio"] = [w[0] for w in weights]
    table["Weight_Weakest"] = [w[1] for w in weights]
    table["Weight_Element_Share"] = [w[2] for w in weights]
    table["Gained_Positions"] = [" ".join(f"{p}:{k}/{n}" for p, k, n in g)
                                 for g in table["Gained_Positions"]]
    table["Same_Span_As"] = ""
    return table


def select(table: pd.DataFrame, selection: str) -> pd.DataFrame:
    """The rows of `table` one selection keeps (SELECTIONS; see the module
    docstring)."""
    if selection == "all":
        return table
    if selection == "complete":
        return table[table["Position_Basis"].isin(["complete", ""])]
    if selection == "partial":
        return table[table["Position_Basis"].isin(["partial", ""])]
    if selection == "distinct":
        kept, merged = [], {}
        first: dict[tuple, int] = {}
        for index, row in table.iterrows():
            key = (row["Class"], row["Construction"], row["Left_Edge"], row["Right_Edge"])
            if key in first:
                merged.setdefault(first[key], []).append(row["Test_Labels"])
            else:
                first[key] = index
                kept.append(index)
        out = table.loc[kept].copy()
        out["Same_Span_As"] = [" | ".join(merged.get(i, [])) for i in kept]
        return out
    raise ValueError(f"Unknown selection {selection!r}; known: {SELECTIONS}")


def domains_frame(table: pd.DataFrame, grouping: str) -> pd.DataFrame:
    """A selection of the span table as a domains file for one grouping."""
    out = table.copy()
    out["Domain_Type"] = out[f"Domain_Type_{grouping}"]
    return out[DOMAIN_COLUMNS]


# ── What the bundle records about its source ────────────────────────────────

def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(CODED_DATA), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def source_record(lang_id: str, grouping: str, selection: str, table: pd.DataFrame) -> dict:
    completeness = language_completeness(lang_id, source="local", repo_root=REPO)
    by_construction = {}
    filled = total = 0
    for cls, constructions in completeness.items():
        for construction, stats in constructions.items():
            if stats.get("missing"):
                by_construction[f"{cls}/{construction}"] = "not yet imported"
            elif stats.get("error"):
                by_construction[f"{cls}/{construction}"] = f"unreadable: {stats['error']}"
            else:
                by_construction[f"{cls}/{construction}"] = f"{stats['filled']}/{stats['total']} cells"
                filled += stats["filled"]
                total += stats["total"]
    return {
        "language": lang_id,
        "language_name": get_display_name(lang_id),
        "grouping": grouping,
        "groupings": GROUPINGS_BY[grouping],
        "selection": selection,
        "planars_data_commit": _git("rev-parse", "HEAD"),
        "planars_data_uncommitted_changes": bool(_git("status", "--porcelain", "--", lang_id)),
        "planar_file": repo_relative(planar_file(lang_id)),
        "annotation_cells_filled": filled,
        "annotation_cells_total": total,
        "annotation_by_construction": by_construction,
        "annotated_classes_without_spans": sorted(set(completeness) - set(table["Class"])),
    }


# ── Writing ─────────────────────────────────────────────────────────────────

def write_inputs(lang_id: str, apply: bool) -> list[str]:
    """Build every dataset's domains file and source record for `lang_id`,
    write those that differ when `apply`, and return the dataset names."""
    table = span_table(lang_id)
    out_dir = domains_dir(lang_id)
    for grouping in GROUPINGS_BY:
        for selection in SELECTIONS:
            dataset = dataset_name(lang_id, grouping, selection)
            frame = domains_frame(select(table, selection), grouping)
            files = {
                out_dir / f"domains_{dataset}.tsv": frame.to_csv(sep="\t", index=False),
                out_dir / f"source_{dataset}.json":
                    json.dumps(source_record(lang_id, grouping, selection, table),
                               indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            }
            for path, text in files.items():
                same = path.exists() and path.read_text(encoding="utf-8") == text
                verb = "unchanged" if same else ("wrote" if apply else "would write")
                print(f"  {verb:12s} {repo_relative(path)}"
                      + (f"  ({len(frame)} tests)" if path.suffix == ".tsv" else ""))
                if apply and not same:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
    return dataset_names(lang_id)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m laminar.planars_language",
        description="Write a planars language's domains files for the laminar analysis "
                    "(every grouping x selection) into coded_data/.analysis/<lang>/.")
    parser.add_argument("lang_id", help="Glottocode, e.g. stan1293")
    parser.add_argument("--apply", action="store_true", help="Write. Without it, only say what would be written.")
    args = parser.parse_args(argv)
    if not planar_file(args.lang_id).exists():
        sys.exit(f"{args.lang_id}: no planar file at {repo_relative(planar_file(args.lang_id))}; "
                 "is coded_data/ cloned and current?")
    print(f"{get_display_name(args.lang_id)}:")
    write_inputs(args.lang_id, args.apply)
    if not args.apply:
        print("\nNothing was written. Add --apply to write.")


if __name__ == "__main__":
    main()
