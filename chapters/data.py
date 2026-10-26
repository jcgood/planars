"""Everything a language's chapter cites, gathered at one data version.

``chapter_data(lang_id, version=None)`` is Phase 1 of
docs/chapter-generation-plan.md: one function that reads a language's
sources and returns them as named values and tables, so a fragment or a
sentence cites a value by name and never types it. Nothing here writes
anything or produces LaTeX; Phase 2's templates read what it returns.

**Data version.** ``version=None`` reads the planars-data clone
(``coded_data/``) as it is, recording its commit and whether it has
uncommitted changes for the language. ``version="<commit>"`` reads that
commit instead, from a copy git writes into a temporary folder
(``git archive``), so the clone is never touched and a chapter can be
rebuilt exactly from the commit its ``data.lock`` names. The schemas and
the span rules are the code's (this checkout of planars), recorded as
``planars_commit``.

**Values** are one flat dictionary, every key starting with the language's
Glottocode (``stan1293.planar.positions``), so an introduction or results
chapter citing several languages has one namespace. The groups:

- ``<L>.language.*``: name, glottocode, iso639_3, family, author,
  annotator, display_name, examples (its example style)
  (schemas/languages.yaml);
- ``<L>.data.*``: commit, commit_short (its first 12 characters), date
  (the planars-data commit's date), and ``planars_commit``;
- ``<L>.planar.*``: positions, zones, slots, keystone (its position
  number), type (the planar file);
- ``<L>.diagnostics.*``: classes, constructions (diagnostics_<L>.yaml);
- ``<L>.annotation.*``: filled, total, percent (language_completeness,
  through planars.reports.completeness_summary);
- ``<L>.spans.*``: total (span rows), distinct (distinct left/right pairs);
- ``<L>.span.<class>.<construction>.<span_key>.*``: left, right, size,
  left_name, right_name, and range (``9--20``, what a ``\\claim`` about a
  span states) (planars.reports.language_spans; the span key is the derive
  function's, e.g. ``strict_complete_span``);
- ``<L>.analysis.<grouping>.<selection>.*``: positions, tests, spans,
  families, conflict_pairs, and for each permutation test in the bundle
  (fragmentation, span_placement, arbitrary_layers) and each group,
  ``<test>.<group>.observed``, ``.null_mean``, ``.p_value``.

**Tables** (pandas DataFrames): ``planar`` (the planar file), ``diagnostics``
(one row per class and construction, in the schema's class order, with its
domain type and criteria as ``{criterion: [values]}``), ``completeness`` (one row per construction),
``spans`` (language_spans' rows), ``examples`` (every annotation row with
an Example, its row identified by the schema's row columns, with its Gloss,
Translation and Source; ``split_examples`` splits a row into its examples,
and ``missing`` lists a glossed row whose cells don't pair up).

**The analysis** comes from the laminar bundles in the clone's
``.analysis/<L>/chart_data/`` (working files, never committed; the weekly
full analysis, laminar plan 4d, will keep them current). A bundle is used
only when it was drawn from the same spans and planar file as the version
being read: the domains file this version gives, rebuilt here, must have
the hash the bundle records (``source_domain_sha256``), and likewise the
planar file. Otherwise its values are left out and ``missing`` says why,
so a chapter never mixes numbers from two versions of the data.

**missing** lists, in plain words, everything a chapter might expect that
this version lacks: a bundle not drawn, drawn from other data, or without
its permutation tests; annotated classes that give no spans yet.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd
import yaml

from laminar import planars_language as _pl
from laminar.datasets import REPO, bundle_root
from planars.languages import get_display_name, get_entry
from planars.reports import completeness_summary, language_completeness, language_spans
from planars.schema_values import (EXAMPLE_SEPARATOR, SLOT, ZONE, class_domain_types,
                                   example_style, is_keystone, row_columns,
                                   trailing_columns_for)

CODED_DATA = REPO / "coded_data"

# The permutation tests whose per-group results become values: bundle file
# stem -> the name used in value keys. The boundary-strength test is per
# position, a table for a figure rather than values.
PERMUTATION_TESTS = {
    "fragmentation_test": "fragmentation",
    "span_placement_test": "span_placement",
    "arbitrary_layers_test": "arbitrary_layers",
}

# Bundle metadata field -> value name.
BUNDLE_COUNTS = {
    "n_positions": "positions",
    "n_active_tests": "tests",
    "n_unique_spans": "spans",
    "n_maximal_families": "families",
    "n_conflict_pairs": "conflict_pairs",
}

EXAMPLE_COLUMN = "Example"
GLOSS_COLUMN = "Gloss"
TRANSLATION_COLUMN = "Translation"
SOURCE_COLUMN = "Source"


class ChapterDataError(Exception):
    """The language's sources can't be read as a chapter's; the message says why."""


@dataclass
class ChapterData:
    lang_id: str
    version: dict                      # planars_data_commit, uncommitted_changes, planars_commit, date
    values: dict = field(default_factory=dict)
    tables: dict = field(default_factory=dict)
    bundles: dict = field(default_factory=dict)   # dataset -> bundle data folder, for figures
    missing: list = field(default_factory=list)


# ── The data version ────────────────────────────────────────────────────────

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


@contextlib.contextmanager
def data_at(version: Optional[str]) -> Iterator[Path]:
    """A folder whose ``coded_data/`` holds planars-data at `version` (a
    commit, tag or branch), or the repository itself for None (the clone
    as it is). The copy is deleted on leaving."""
    if version is None:
        yield REPO
        return
    try:
        archive = subprocess.run(["git", "-C", str(CODED_DATA), "archive", "--format=tar", version],
                                 capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        raise ChapterDataError(
            f"planars-data has no version {version!r} (git said: "
            f"{e.stderr.decode(errors='replace').strip()}). {_fetch_advice()}")
    with tempfile.TemporaryDirectory(prefix="chapter_data_") as tmp:
        root = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(root / "coded_data", filter="data")
        yield root


def commit_of(version: Optional[str]) -> str:
    """The planars-data commit `version` names (None: the clone's HEAD)."""
    try:
        return _git(CODED_DATA, "rev-parse", "--verify", f"{version or 'HEAD'}^{{commit}}")
    except subprocess.CalledProcessError:
        raise ChapterDataError(f"planars-data has no version {version!r}. {_fetch_advice()}")


def _fetch_advice() -> str:
    """What to do about a missing version: a shallow copy (a GitHub
    checkout without fetch-depth: 0) has no older versions at all."""
    try:
        shallow = _git(CODED_DATA, "rev-parse", "--is-shallow-repository") == "true"
    except subprocess.CalledProcessError:
        shallow = False
    if shallow:
        return ("coded_data/ is a shallow copy holding only recent versions: fetch its whole "
                "history (git -C coded_data fetch --unshallow; on GitHub, check it out with "
                "fetch-depth: 0).")
    return "Pull coded_data/ first if it is new."


def _version_record(lang_id: str, version: Optional[str]) -> dict:
    # A coded_data/ that is a plain copy, not a clone, would make git answer
    # for the planars repository around it, and the chapter would name a
    # planars commit as its data version.
    try:
        top = Path(_git(CODED_DATA, "rev-parse", "--show-toplevel")).resolve()
    except subprocess.CalledProcessError:
        top = None
    if top != CODED_DATA.resolve():
        raise ChapterDataError(
            "coded_data/ is not a clone of planars-data, so its data version can't be "
            "named. Clone it there (docs/coordinator-guide.md, setup).")
    commit = commit_of(version)
    return {
        "planars_data_commit": commit,
        "date": _git(CODED_DATA, "log", "-1", "--format=%cs", commit),
        "uncommitted_changes": (bool(_git(CODED_DATA, "status", "--porcelain", "--", lang_id))
                                if version is None else False),
        "planars_commit": _git(REPO, "rev-parse", "HEAD"),
    }


# ── Reading each source ─────────────────────────────────────────────────────

def _language_values(lang_id: str) -> dict:
    entry = get_entry(lang_id)
    if entry is None:
        raise ChapterDataError(f"{lang_id} has no entry in schemas/languages.yaml.")
    glottolog, meta = entry.get("glottolog") or {}, entry.get("meta") or {}
    return {
        "name": meta.get("language") or glottolog.get("name", ""),
        "glottocode": lang_id,
        "iso639_3": glottolog.get("iso639_3", ""),
        "family": glottolog.get("family", ""),
        "author": meta.get("author", ""),
        "annotator": meta.get("annotator", ""),
        "display_name": get_display_name(lang_id),
        "examples": example_style(lang_id),
    }


def _planar(lang_dir: Path, lang_id: str) -> tuple[pd.DataFrame, dict]:
    path = lang_dir / "lang_setup" / f"planar_{lang_id}.tsv"
    if not path.exists():
        raise ChapterDataError(f"{lang_id} has no planar file at this version ({path.name}).")
    planar = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    keystone = planar[planar["Position_Name"].map(is_keystone)]
    kinds = sorted(set(planar["Planar_Type"]))
    if len(keystone) != 1 or len(kinds) != 1:
        raise ChapterDataError(f"{path.name}: expected one keystone row and one Planar_Type, "
                               f"found {len(keystone)} and {kinds}.")
    unknown = sorted(set(planar["Position_Type"]) - {ZONE, SLOT})
    if unknown:
        raise ChapterDataError(f"{path.name}: unknown Position_Type {unknown}.")
    return planar, {
        "positions": len(planar),
        "zones": int((planar["Position_Type"] == ZONE).sum()),
        "slots": int((planar["Position_Type"] == SLOT).sum()),
        "keystone": int(keystone["Position"].iloc[0]),
        "type": kinds[0],
    }


def _diagnostics(lang_dir: Path, lang_id: str) -> pd.DataFrame:
    """One row per class and construction of diagnostics_<L>.yaml, in the
    schema's class order. A class the schema doesn't know fails."""
    path = lang_dir / "lang_setup" / f"diagnostics_{lang_id}.yaml"
    if not path.exists():
        raise ChapterDataError(f"{lang_id} has no diagnostics file at this version ({path.name}).")
    classes = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("classes") or {}
    types = class_domain_types()
    unknown = sorted(set(classes) - set(types))
    if unknown:
        raise ChapterDataError(f"{path.name}: classes not in schemas/diagnostic_classes.yaml: {unknown}")
    rows = []
    for cls in (c for c in types if c in classes):
        spec = classes[cls] or {}
        domain_type, subtype = types[cls]
        for construction in spec.get("constructions") or []:
            criteria = (spec.get("construction_criteria") or {}).get(construction) or spec.get("criteria") or {}
            rows.append({"Class": cls, "Domain_Type": domain_type, "Domain_Subtype": subtype or "",
                         "Construction": construction,
                         "Criteria": {name: [str(v) for v in values or []]
                                      for name, values in criteria.items()}})
    return pd.DataFrame(rows, columns=["Class", "Domain_Type", "Domain_Subtype", "Construction", "Criteria"])


def _completeness(lang_id: str, root: Path) -> tuple[pd.DataFrame, dict]:
    completeness = language_completeness(lang_id, source="local", repo_root=root)
    rows = []
    for cls, constructions in completeness.items():
        for construction, stats in constructions.items():
            state = ("not yet imported" if stats.get("missing")
                     else f"unreadable: {stats['error']}" if stats.get("error") else "")
            rows.append({"Class": cls, "Construction": construction, "Filled": stats["filled"],
                         "Total": stats["total"], "State": state})
    summary = completeness_summary(completeness)
    percent = round(100 * summary["filled"] / summary["total"], 1) if summary["total"] else 0.0
    table = pd.DataFrame(rows, columns=["Class", "Construction", "Filled", "Total", "State"])
    return table, {"filled": summary["filled"], "total": summary["total"], "percent": percent}


def is_glossed(lang_id: str) -> bool:
    """Whether `lang_id`'s examples carry a gloss and translation: its
    example style keeps the Gloss column (schemas/planar.yaml example_styles)."""
    return GLOSS_COLUMN in trailing_columns_for(lang_id)


def split_examples(row: dict, glossed: bool) -> tuple[list, bool]:
    """The examples in one annotation row, as [{form, gloss, translation}],
    each cell split on EXAMPLE_SEPARATOR. For a glossed language, False when
    the Gloss or Translation cell doesn't hold one entry per example; the
    examples then come without them, so nothing is paired wrongly."""
    split = lambda cell: [x.strip() for x in str(cell).split(EXAMPLE_SEPARATOR) if x.strip()]
    forms = split(row["Example"])
    if not glossed:
        return [{"form": f, "gloss": "", "translation": ""} for f in forms], True
    glosses, translations = split(row[GLOSS_COLUMN]), split(row[TRANSLATION_COLUMN])
    if len(glosses) != len(forms) or len(translations) != len(forms):
        return [{"form": f, "gloss": "", "translation": ""} for f in forms], False
    return [{"form": f, "gloss": g, "translation": t}
            for f, g, t in zip(forms, glosses, translations)], True


def _examples(lang_dir: Path) -> pd.DataFrame:
    """Every annotation row with an Example, identified by its row columns
    (schema_values.row_columns) joined with " | ", with its Gloss and
    Translation (blank where the tab has no such column)."""
    rows = []
    for cls in class_domain_types():
        class_dir = lang_dir / cls
        if not class_dir.is_dir():
            continue
        for tsv in sorted(class_dir.glob("*.tsv")):
            data = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False)
            if EXAMPLE_COLUMN not in data.columns:
                continue
            key = [c for c in row_columns(cls, tsv.stem) if c in data.columns]
            for _i, row in data[data[EXAMPLE_COLUMN].str.strip() != ""].iterrows():
                rows.append({"Class": cls, "Construction": tsv.stem,
                             "Row": " | ".join(row[c] for c in key),
                             "Example": row[EXAMPLE_COLUMN].strip(),
                             GLOSS_COLUMN: row.get(GLOSS_COLUMN, "").strip(),
                             TRANSLATION_COLUMN: row.get(TRANSLATION_COLUMN, "").strip(),
                             "Source": row.get(SOURCE_COLUMN, "").strip()})
    return pd.DataFrame(rows, columns=["Class", "Construction", "Row", "Example", GLOSS_COLUMN,
                                       TRANSLATION_COLUMN, "Source"])


def _span_values(spans: pd.DataFrame, pos_to_name: dict) -> dict:
    values = {"spans.total": len(spans),
              "spans.distinct": len(spans[["Left_Edge", "Right_Edge"]].drop_duplicates())
                                if len(spans) else 0}
    for _i, row in spans.iterrows():
        base = f"span.{row['Analysis']}.{row['Construction']}.{row['Span_Key']}"
        left, right = int(row["Left_Edge"]), int(row["Right_Edge"])
        values.update({f"{base}.left": left, f"{base}.right": right, f"{base}.size": int(row["Size"]),
                       f"{base}.range": f"{left}--{right}",
                       f"{base}.left_name": pos_to_name.get(left, ""),
                       f"{base}.right_name": pos_to_name.get(right, "")})
    return values


# ── The analysis bundles ────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _analysis(lang_id: str, root: Path, chapter: ChapterData) -> None:
    """Values from each of the language's laminar bundles that was drawn from
    the same spans and planar file as this version (module docstring)."""
    try:
        table = _pl.span_table(lang_id, repo_root=root)
    except _pl.NoSpansYet:
        chapter.missing.append("The annotation gives no spans yet, so there is no analysis.")
        return
    planar_text = (root / "coded_data" / lang_id / "lang_setup" / f"planar_{lang_id}.tsv").read_text(encoding="utf-8")
    not_drawn, other_data, without_tests = [], {}, {}
    for dataset in _pl.dataset_names(lang_id):
        _lang, grouping, selection = _pl.parse_dataset(dataset)
        folder = bundle_root(dataset) / dataset / "data"
        metadata_path = folder / "metadata.json"
        if not metadata_path.exists():
            not_drawn.append(dataset)
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        domains_text = _pl.domains_frame(_pl.select(table, selection), grouping).to_csv(sep="\t", index=False)
        if (metadata.get("source_domain_sha256") != _sha256(domains_text)
                or metadata.get("source_planar_sha256") != _sha256(planar_text)):
            drawn_from = (metadata.get("planars_source") or {}).get("planars_data_commit", "unknown")
            other_data.setdefault(drawn_from[:12], []).append(dataset)
            continue
        chapter.bundles[dataset] = folder
        base = f"analysis.{grouping}.{selection}"
        for field_name, name in BUNDLE_COUNTS.items():
            chapter.values[f"{lang_id}.{base}.{name}"] = metadata[field_name]
        absent = []
        for stem, test in PERMUTATION_TESTS.items():
            path = folder / f"{stem}.tsv"
            if not path.exists():
                absent.append(test)
                continue
            results = pd.read_csv(path, sep="\t", keep_default_na=False)
            for _i, row in results.iterrows():
                key = f"{lang_id}.{base}.{test}.{row['group']}"
                chapter.values[f"{key}.observed"] = int(row["observed_families"])
                chapter.values[f"{key}.null_mean"] = float(row["null_mean"])
                chapter.values[f"{key}.p_value"] = float(row["p_value_le_observed"])
        if absent:
            without_tests[dataset] = absent
    if not_drawn:
        chapter.missing.append(f"No analysis drawn for {', '.join(not_drawn)} "
                               f"(python -m laminar charts --lang {lang_id} --apply draws them).")
    for commit, datasets in other_data.items():
        chapter.missing.append(
            f"The analysis of {', '.join(datasets)} was drawn from other spans or another "
            f"planar file (planars-data {commit}), so its numbers are left out: read the "
            f"chapter at that version, or redraw the analysis from this one.")
    for dataset, absent in without_tests.items():
        chapter.missing.append(f"The {dataset} analysis has no permutation tests "
                               f"({', '.join(absent)}); the weekly full analysis adds them.")


# ── The one entry point ─────────────────────────────────────────────────────

def chapter_data(lang_id: str, version: Optional[str] = None) -> ChapterData:
    """Everything `lang_id`'s chapter cites, read at planars-data `version`
    (None: the clone as it is). See the module docstring."""
    chapter = ChapterData(lang_id=lang_id, version=_version_record(lang_id, version))
    values = {f"language.{k}": v for k, v in _language_values(lang_id).items()}
    values.update({"data.commit": chapter.version["planars_data_commit"],
                   "data.commit_short": chapter.version["planars_data_commit"][:12],
                   "data.date": chapter.version["date"],
                   "data.planars_commit": chapter.version["planars_commit"]})
    with data_at(version) as root:
        lang_dir = root / "coded_data" / lang_id
        planar, planar_values = _planar(lang_dir, lang_id)
        values.update({f"planar.{k}": v for k, v in planar_values.items()})
        diagnostics = _diagnostics(lang_dir, lang_id)
        values["diagnostics.classes"] = diagnostics["Class"].nunique()
        values["diagnostics.constructions"] = len(diagnostics)
        completeness, annotation = _completeness(lang_id, root)
        values.update({f"annotation.{k}": v for k, v in annotation.items()})
        spans, meta = language_spans(lang_id, source="local", repo_root=root)
        pos_to_name = (meta.get(lang_id) or {}).get("pos_to_name", {})
        values.update(_span_values(spans, pos_to_name))
        without_spans = sorted(set(completeness["Class"]) - set(spans.get("Analysis", [])))
        if without_spans:
            chapter.missing.append("Annotated classes that give no spans yet: "
                                   + ", ".join(without_spans) + ".")
        chapter.values.update({f"{lang_id}.{k}": v for k, v in values.items()})
        examples = _examples(lang_dir)
        chapter.tables = {"planar": planar, "diagnostics": diagnostics, "completeness": completeness,
                          "spans": spans, "examples": examples}
        glossed = is_glossed(lang_id)
        unpaired = [f"{r['Class']}/{r['Construction']} {r['Row']}" for _i, r in examples.iterrows()
                    if not split_examples(r, glossed)[1]]
        if unpaired:
            chapter.missing.append(
                f"{len(unpaired)} annotation row(s) whose Gloss or Translation doesn't hold one "
                f"entry per example (separated by {EXAMPLE_SEPARATOR!r}), so their "
                f"examples are printed without them: " + "; ".join(unpaired))
        _analysis(lang_id, root, chapter)
    return chapter
