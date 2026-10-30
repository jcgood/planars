"""Report data collection and span extraction for planars.

This module is the data layer for all downstream analysis:
  - Span collection (the primary analytical output)
  - Annotation completeness
  - Sheet status
  - Per-language report bundles

Spans are the operationalization of constituency diagnostic test results and
are the central data product of the pipeline. They feed chart rendering
(planars.charts), tree traversal algorithms, CLDF export (#84), R-based
analysis, and HTML reports. All span collection lives here; planars.charts
imports from this module, not the reverse.

Every function reads a folder laid out like the repo root (``repo_root``,
holding ``coded_data/{lang_id}/…``): the coordinator's own checkout, or, in
Colab, the folder ``planars.from_sheets`` writes the sheets into.

Typical usage (coordinator CLI)
---------------------------------
    from planars.reports import project_spans, language_report_data
    from pathlib import Path

    repo_root = Path(".")
    df, lang_meta = project_spans(repo_root)
    data = language_report_data("arao1248", repo_root)

Typical usage (Colab)
---------------------------------
    from planars.from_sheets import open_language
    from planars.reports import language_spans, language_report_data, print_class_reports

    lang = open_language("arao1248", drive_svc, gc)   # the sheets, found by label
    df, lang_meta = language_spans("arao1248", lang.root)
    data = language_report_data("arao1248", lang.root, status=lang.status)
    print_class_reports(lang.root, "arao1248")

Until unit 11c-5 (2026-10-29) the notebooks read the sheets here instead
(``source="sheets"``, with the list of sheet IDs the manifest on Drive kept,
which went stale); they now find them by label (docs/ownership-design.md
§ 6 item 7).
"""

from __future__ import annotations

import datetime
import importlib
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml
import pandas as pd
from importlib.resources import files as _res_files

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint
from planars import metrical as _metrical
from planars import nonpermutability as _nonperm
from planars import coreference as _coreference
from planars import free_occurrence as _freeoc
from planars import biuniqueness_deviations as _biuniq
from planars import repair as _repair
from planars import segmental as _segmental
from planars import tonal as _tonal
from planars import tonosegmental as _tonoseg
from planars import intonational as _inton
from planars import pausing as _pausing
from planars import proform as _proform
from planars import play_language as _play
from planars import idiom as _idiom
from planars.languages import get_display_name
from planars.spans import gained_position_counts
from planars.schema_values import (
    ELEMENT_ROWS, TRAILING_COLUMNS, is_keystone, row_columns, row_type,
)

# ---------------------------------------------------------------------------
# Span label constants
# Loaded from schemas/terms.yaml (span_label_map section). check-codebook
# (coding/check_codebook.py) imports them from here to check every key
# against the derive functions' result dicts.
# ---------------------------------------------------------------------------

def _load_span_label_map() -> dict:
    text = _res_files("schemas").joinpath("terms.yaml").read_text(encoding="utf-8")
    return (yaml.safe_load(text) or {}).get("span_label_map", {})

_span_map = _load_span_label_map()

_CISC_SPANS           = list(_span_map.get("ciscategorial", {}).items())
_NONINT_SPANS         = list(_span_map.get("noninterruption", {}).items())
_METRICAL_BLOCKED_SPANS = list(_span_map.get("metrical", {}).items())
_NONPERM_SPANS        = list(_span_map.get("nonpermutability", {}).items())
_COREFERENCE_SPANS         = list(_span_map.get("coreference", {}).items())
_FREEOC_SPANS         = list(_span_map.get("free_occurrence", {}).items())

# Standard 4-span pattern shared by most simple modules.
_SIMPLE_SPANS         = list(_span_map.get("simple_variants", {}).items())

_subspan_map    = _span_map.get("subspanrepetition", {})
_SUBSPAN_CATS   = _subspan_map.get("categories", {})
_SUBSPAN_VARIANTS = list(_subspan_map.get("variants", {}).items())

# Short prefix overrides for simple analyses (e.g. "seg" instead of "segmental").
_SIMPLE_PREFIXES = _span_map.get("simple_prefix_overrides", {})

_BIUNIQ_MAP      = _span_map.get("biuniqueness_deviations", {})
_BIUNIQ_PREFIX   = _BIUNIQ_MAP.get("prefix", "biuniq")
_BIUNIQ_VARIANTS = list(_BIUNIQ_MAP.get("variants", {}).items())


# ---------------------------------------------------------------------------
# Row extraction helpers
# ---------------------------------------------------------------------------

def _span_row(lang_id, analysis, label, key, result):
    """One span row: `key` is the span's key in the derive function's result."""
    l, r = result[key]
    return {"Language": lang_id, "Test_Labels": label, "Analysis": analysis,
            "Span_Key": key, "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1}


def _rows_from_cisc(result, lang_id):
    return [_span_row(lang_id, "ciscategorial", label, key, result)
            for key, label in _CISC_SPANS]


def _rows_from_subspan(result, lang_id):
    return [_span_row(lang_id, "subspanrepetition", f"{short} {vlabel}",
                      f"{variant}_{cat}_span", result)
            for cat, short in _SUBSPAN_CATS.items()
            for variant, vlabel in _SUBSPAN_VARIANTS]


def _rows_from_nonint(result, lang_id):
    return [_span_row(lang_id, "noninterruption", label, key, result)
            for key, label in _NONINT_SPANS]


def _rows_from_metrical(result, lang_id):
    return [_span_row(lang_id, "metrical", label, key, result)
            for key, label in _METRICAL_BLOCKED_SPANS]


def _rows_from_biuniq(result, lang_id):
    """One pair of rows (raw, anchored) per biuniqueness deviation domain.

    Not a fixed label set like the other classes: a language has as many
    domains as it has deviating morphemes. Labels come from terms.yaml's
    span_label_map.biuniqueness_deviations.
    """
    rows = []
    for d in result["domains"]:
        where = f"{d['morpheme']}@{d['position_name']}" if d["position_name"] else d["morpheme"]
        for key, variant in _BIUNIQ_VARIANTS:
            rows.append(_span_row(lang_id, "biuniqueness_deviations",
                                  f"{_BIUNIQ_PREFIX} {d['type']} {where} {variant}", key, d))
    return rows


def _make_simple_rows(analysis_name, span_list=None, prefix=None):
    """Factory: returns a row function for modules with a standard span set."""
    if span_list is None:
        span_list = _SIMPLE_SPANS
    if prefix is None:
        prefix = _SIMPLE_PREFIXES.get(analysis_name, analysis_name)

    def _fn(result, lang_id):
        return [_span_row(lang_id, analysis_name, f"{prefix} {label}", key, result)
                for key, label in span_list]

    return _fn


# ---------------------------------------------------------------------------
# Analysis class registry
#
# Maps class name → (derive_fn, row_fn). This is the single source of truth
# for which analyses exist and how to run them. planars.charts imports this
# registry to auto-assign colors; it does not duplicate it.
# ---------------------------------------------------------------------------

_CLASS_HANDLERS = {
    "ciscategorial":     (_cisc.derive_v_ciscategorial_fractures,     _rows_from_cisc),
    "subspanrepetition": (_subspan.derive_subspanrepetition_spans,    _rows_from_subspan),
    "noninterruption":   (_nonint.derive_noninterruption_domains,     _rows_from_nonint),
    "metrical":          (_metrical.derive_metrical_domains,           _rows_from_metrical),
    "nonpermutability":  (_nonperm.derive_nonpermutability_domains,   _make_simple_rows("nonpermutability", _NONPERM_SPANS)),
    "coreference":       (_coreference.derive_coreference_domains,    _make_simple_rows("coreference", _COREFERENCE_SPANS)),
    "free_occurrence":   (_freeoc.derive_free_occurrence_spans,       _make_simple_rows("free_occurrence", _FREEOC_SPANS)),
    "biuniqueness_deviations": (_biuniq.derive_biuniqueness_deviations_domains, _rows_from_biuniq),
    "repair":            (_repair.derive_repair_domains,              _make_simple_rows("repair")),
    "segmental":         (_segmental.derive_segmental_domains,        _make_simple_rows("segmental")),
    "tonal":             (_tonal.derive_tonal_domains,                _make_simple_rows("tonal")),
    "tonosegmental":     (_tonoseg.derive_tonosegmental_domains,      _make_simple_rows("tonosegmental")),
    "intonational":      (_inton.derive_intonational_domains,         _make_simple_rows("intonational")),
    "pausing":           (_pausing.derive_pausing_domains,            _make_simple_rows("pausing")),
    "proform":           (_proform.derive_proform_domains,            _make_simple_rows("proform")),
    "play_language":     (_play.derive_play_language_domains,         _make_simple_rows("play_language")),
    "idiom":             (_idiom.derive_idiom_domains,                _make_simple_rows("idiom")),
}

# ---------------------------------------------------------------------------
# Partial spans and their weights (docs/laminar-analysis-plan.md decision 3)
#
# For each class: {partial span key: (complete counterpart key, counts key)}.
# A partial span lets in positions where only some elements satisfy the span
# rule; its counterpart is the same span built from positions where every
# element does. The counts key names the result's {position: (k, n)}
# (planars.spans.position_sets_from_element_mask). A class with {} has no
# partial/complete distinction (its spans come from pairs or other rules).
# Every class in _CLASS_HANDLERS must be listed: an unlisted one fails at
# import rather than passing as unweighted.
#
# metrical is the reverse of the rest: its "complete" span is the wider one
# (it stops only where every element blocks), so that is its partial span here.
# ---------------------------------------------------------------------------

_STANDARD_WEIGHTS = {
    "strict_partial_span": ("strict_complete_span", "position_counts"),
    "loose_partial_span":  ("loose_complete_span",  "position_counts"),
}

_WEIGHTED_SPANS: Dict[str, Dict[str, Tuple[str, str]]] = {
    "ciscategorial":     _STANDARD_WEIGHTS,
    "subspanrepetition": {
        f"{variant}_partial_{cat}_span": (f"{variant}_complete_{cat}_span", f"{cat}_position_counts")
        for cat in _SUBSPAN_CATS for variant in ("strict", "loose")
    },
    "noninterruption": {
        "no_free_partial_span":     ("no_free_complete_span",     "no_free_position_counts"),
        "single_free_partial_span": ("single_free_complete_span", "single_free_position_counts"),
    },
    "metrical": {
        "minimal_complete_span": ("minimal_partial_span", "minimal_position_counts"),
        "maximal_complete_span": ("maximal_partial_span", "maximal_position_counts"),
    },
    "nonpermutability":        {},
    "coreference":             {},
    "free_occurrence":         {},
    "biuniqueness_deviations": {},
    "repair":                  _STANDARD_WEIGHTS,
    "segmental":               _STANDARD_WEIGHTS,
    "tonal":                   _STANDARD_WEIGHTS,
    "tonosegmental":           _STANDARD_WEIGHTS,
    "intonational":            _STANDARD_WEIGHTS,
    "pausing":                 _STANDARD_WEIGHTS,
    "proform":                 _STANDARD_WEIGHTS,
    "play_language":           _STANDARD_WEIGHTS,
    "idiom":                   _STANDARD_WEIGHTS,
}
if set(_WEIGHTED_SPANS) != set(_CLASS_HANDLERS):
    raise RuntimeError(
        "planars/reports.py: _WEIGHTED_SPANS must list exactly the classes in _CLASS_HANDLERS; "
        f"missing {sorted(set(_CLASS_HANDLERS) - set(_WEIGHTED_SPANS))}, "
        f"extra {sorted(set(_WEIGHTED_SPANS) - set(_CLASS_HANDLERS))}")


def _span_rows(class_name: str, construction: str, result: dict, lang_id: str) -> list:
    """The class's span rows for one construction, each with its construction,
    whether it is built from complete or partial positions (Position_Basis:
    "complete", "partial", or "" for a class without the distinction), and,
    for a partial span, the positions it gains over its complete counterpart
    with their k of n (Gained_Positions: [(position, k, n), ...])."""
    _derive_fn, row_fn = _CLASS_HANDLERS[class_name]
    weighted = _WEIGHTED_SPANS[class_name]
    counterparts = {counterpart for counterpart, _counts in weighted.values()}
    rows = row_fn(result, lang_id)
    for row in rows:
        key = row["Span_Key"]
        row["Construction"] = construction
        if key in weighted:
            counterpart, counts_key = weighted[key]
            row["Position_Basis"] = "partial"
            row["Gained_Positions"] = gained_position_counts(
                result[key], result[counterpart], result[counts_key])
        else:
            row["Position_Basis"] = "complete" if key in counterparts else ""
            row["Gained_Positions"] = []
    return rows

def span_constructions(class_name: str) -> Optional[frozenset]:
    """The class's constructions that produce spans, or None if every one does.

    Read from schemas/diagnostic_classes.yaml: a feeder construction (one that
    only decides what goes into a later tab, e.g. element_prescreening) says
    `produces_spans: false` there. This is the one reader of that field; until
    2026-10-12 three analysis modules each hand-listed their span tabs instead
    (Phase 10 unit 4, hidden-facts entry D-1b).
    """
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    classes = {c["name"]: c for c in (yaml.safe_load(text) or {}).get("classes", [])}
    constructions = [c for c in (classes.get(class_name, {}).get("constructions") or [])
                     if isinstance(c, dict)]
    if not any(c.get("produces_spans") is False for c in constructions):
        return None
    return frozenset(c["name"] for c in constructions if c.get("produces_spans") is not False)


# For classes with multi-construction workflows, only these constructions
# produce span rows. Others (e.g. element_prescreening) are upstream inputs
# and must not be passed to the class's derive function. A class absent here
# has no feeder tabs.
_REPORTABLE_CONSTRUCTIONS: Dict[str, frozenset] = {
    name: spans for name in _CLASS_HANDLERS
    if (spans := span_constructions(name)) is not None
}


# ---------------------------------------------------------------------------
# Span collection (primary analytical output)
# ---------------------------------------------------------------------------

def project_spans(repo_root) -> Tuple[pd.DataFrame, dict]:
    """Collect spans for all languages under ``repo_root/coded_data``.

    Returns (DataFrame, lang_meta) where:
      DataFrame columns: Language, Test_Labels, Analysis, Span_Key, Left_Edge,
        Right_Edge, Size, Construction, Position_Basis, Gained_Positions
        (see _span_rows; Test_Labels repeat across a class's constructions,
        so a span is identified by Analysis + Construction + Span_Key)
      lang_meta: {lang_id: {"keystone_pos": int, "pos_to_name": {int: str}}}

    Each language has its own independent planar structure and position numbering.
    lang_meta is needed for chart rendering and tree traversal.

    For R or other downstream consumers, write the DataFrame to TSV:
        df.to_csv("spans.tsv", sep="\\t", index=False)
    """
    return _collect_spans(Path(repo_root))


def language_spans(lang_id: str, repo_root) -> Tuple[pd.DataFrame, dict]:
    """Collect spans for one language.

    Returns (DataFrame, lang_meta) with the same structure as project_spans,
    but restricted to lang_id. More efficient than project_spans for single-
    language use because it only processes that language's TSVs.

    lang_meta is a single-entry dict: {lang_id: {"keystone_pos": int, "pos_to_name": dict}}
    """
    return _collect_spans(Path(repo_root), lang_id=lang_id)


def _lang_dirs(repo_root: Path, lang_id: Optional[str] = None) -> list:
    """The language folders under ``repo_root/coded_data`` (just ``lang_id``'s
    if given)."""
    coded_data = Path(repo_root) / "coded_data"
    if lang_id is not None:
        return [coded_data / lang_id]
    return sorted(d for d in coded_data.iterdir()
                  if d.is_dir() and not d.name.startswith("."))


def _span_tabs(lang_dir: Path):
    """(class_name, construction, tsv) for every tab that produces spans, in
    the order of ``_CLASS_HANDLERS``."""
    for class_name in _CLASS_HANDLERS:
        class_dir = lang_dir / class_name
        if not class_dir.exists():
            continue
        allowed = _REPORTABLE_CONSTRUCTIONS.get(class_name)
        for tsv in sorted(class_dir.glob("*.tsv")):
            if allowed is None or tsv.stem in allowed:
                yield class_name, tsv.stem, tsv


def _collect_spans(repo_root: Path, lang_id: Optional[str] = None):
    """Internal: collect spans from coded_data/ TSVs.

    If lang_id is given, process only that language's directory.
    """
    rows = []
    lang_meta = {}

    for lang_dir in _lang_dirs(repo_root, lang_id):
        if not lang_dir.is_dir():
            continue
        lid = lang_dir.name
        for class_name, construction, tsv in _span_tabs(lang_dir):
            derive_fn = _CLASS_HANDLERS[class_name][0]
            result = derive_fn(tsv, strict=False)
            rows.extend(_span_rows(class_name, construction, result, lid))
            if lid not in lang_meta:
                lang_meta[lid] = {
                    "keystone_pos": result["keystone_position"],
                    "pos_to_name":  result["position_number_to_name"],
                }

    return pd.DataFrame(rows), lang_meta


def _class_display_names() -> Dict[str, str]:
    """``{class_name: display_name}`` from schemas/diagnostic_classes.yaml."""
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    return {c["name"]: c.get("display_name") or c["name"]
            for c in (yaml.safe_load(text) or {}).get("classes", [])}


def print_class_reports(repo_root, lang_id: Optional[str] = None) -> None:
    """Print each analysis's own summary (its module's ``format_result``)
    for every tab that produces spans, class by class: one language's, or
    every language's. What the Colab notebooks show under "Results by test";
    the classes come from the folders present, so a notebook names none."""
    names = _class_display_names()
    rule = "─" * 60
    found_any = False
    for lang_dir in _lang_dirs(repo_root, lang_id):
        if not lang_dir.is_dir():
            continue
        for class_name, construction, tsv in _span_tabs(lang_dir):
            found_any = True
            print(f"\n{rule}\n  {names.get(class_name, class_name)}  "
                  f"[{lang_dir.name}]  —  {construction}\n{rule}")
            module = importlib.import_module(f"planars.{class_name}")
            try:
                result = _CLASS_HANDLERS[class_name][0](tsv, strict=False)
                print(module.format_result(result))
            except Exception as e:
                print(f"  (No result for this tab yet: {e})")
    if not found_any:
        print("No annotation tabs found.")


# ---------------------------------------------------------------------------
# Completeness helpers
# ---------------------------------------------------------------------------

def _read_expected_constructions(lang_dir: Path) -> Dict[str, list]:
    """Read diagnostics_{lang_id}.yaml and return {class_name: [constructions]}.

    Returns {} if the language has no diagnostics file yet; a file that
    cannot be read raises (a broken file is never reported as "nothing
    expected"). Used by language_completeness to determine Layer 1
    completeness: which constructions are expected but not yet present in
    coded_data/.
    """
    lang_id = lang_dir.name
    diag_path = lang_dir / "lang_setup" / f"diagnostics_{lang_id}.yaml"
    if not diag_path.exists():
        return {}
    with open(diag_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    result: Dict[str, list] = {}
    for class_name, class_data in (data.get("classes") or {}).items():
        constructions = [str(c).strip() for c in (class_data or {}).get("constructions") or []
                         if str(c).strip()]
        if constructions:
            result[class_name] = constructions
    return result

# Trailing sheet columns that are not annotation criteria (e.g. free-text notes),
# from schemas/planar.yaml.
_TRAILING_COLS = set(TRAILING_COLUMNS)

def _criterion_cols_only(criterion_cols: list) -> list:
    """Filter out trailing columns (e.g. Comments) from criterion_cols."""
    return [c for c in criterion_cols if c not in _TRAILING_COLS]


def _tab_completeness(data_df: pd.DataFrame, criterion_cols: list) -> dict:
    """Completeness stats for one annotation tab.

    data_df must already exclude keystone rows (``_rows_completeness`` does).
    criterion_cols is the non-structural column list — trailing cols
    (Comments) are excluded automatically.

    Returns {"total": int, "filled": int, "blank": int}.

    Note: coding/validate_coding.py has a similar function, annotation_status(),
    which also counts blanks but calls validate_annotation_rows() to do so — making
    it dependent on coding/ internals. This version works directly from the loaded
    DataFrame and lives in planars/ so it is available in Colab (pip-installed).
    """
    cols = _criterion_cols_only(criterion_cols)
    if not cols or data_df.empty:
        return {"total": 0, "filled": 0, "blank": 0}
    total = len(data_df) * len(cols)
    blank = int(sum((data_df[c] == "").sum() for c in cols))
    return {"total": total, "filled": total - blank, "blank": blank}


def _rows_completeness(class_name: str, construction: str,
                       header: list, data_rows: list) -> dict:
    """Completeness of one tab from its header and rows, whatever its row
    shape. Criterion columns are the header minus the columns the schema says
    identify its rows (``row_columns``) and the trailing columns; on an
    element-row tab the keystone row is left out, as load_filled_tsv does.

    One rule for every tab since 2026-10-13. Before, a pair tab was recognised
    by ``header[0] == "Element_A"`` and only Element_A/Element_B were
    excluded, so a coreference tab counted its always-filled Position_A,
    Position_B and Direction as criteria; local pair and keyed TSVs, and the
    biuniqueness elements tab (no keystone row by design), went through the
    element-row loader and were reported as errors."""
    key_cols = row_columns(class_name, construction)
    width = len(header)
    rows = [(list(r) + [""] * width)[:width] for r in data_rows]
    df = pd.DataFrame(rows, columns=header) if rows else pd.DataFrame(columns=header)
    if row_type(class_name, construction) == ELEMENT_ROWS and "Position_Name" in df.columns:
        df = df[~df["Position_Name"].map(is_keystone)]
    crit_cols = [c for c in header if c and c not in key_cols and c not in _TRAILING_COLS]
    return _tab_completeness(df, crit_cols)


# ---------------------------------------------------------------------------
# Public API — completeness
# ---------------------------------------------------------------------------

def language_completeness(lang_id: str, repo_root) -> Dict[str, Dict[str, dict]]:
    """Per-construction completeness stats for one language.

    Covers three layers:
      Layer 1 — construction completeness: constructions declared in
        diagnostics_{lang_id}.yaml but not yet present in coded_data/ are
        included with {"total": 0, "filled": 0, "blank": 0, "missing": True}.
        (In Colab there is no diagnostics file, so only the tabs the sheets
        have are listed.)
      Layer 2 — cell completeness: for present TSVs, counts filled vs. blank
        criterion cells (excluding Comments and structural columns).
      Layer 3 — structural completeness: not covered here; use validate-coding.

    Returns:
        {class_name: {construction: {"total": int, "filled": int, "blank": int}}}

    Extra keys in the per-construction dict:
        "missing": True  — construction expected but TSV not yet present (Layer 1)
        "error": str     — TSV present but could not be loaded
    """
    lang_dir = Path(repo_root) / "coded_data" / lang_id

    # Layer 1: expected constructions from diagnostics_{lang_id}.yaml.
    expected = _read_expected_constructions(lang_dir)

    # Collect all class names: declared in diagnostics + present in coded_data.
    present_dirs = {
        d.name for d in lang_dir.iterdir()
        if d.is_dir() and d.name not in {"lang_setup", "archive"}
    } if lang_dir.exists() else set()
    all_class_names = sorted(set(expected.keys()) | present_dirs)

    result: Dict[str, Dict[str, dict]] = {}
    for class_name in all_class_names:
        class_dir = lang_dir / class_name
        exp_constructions = expected.get(class_name, [])
        actual: Dict[str, Path] = (
            {tsv.stem: tsv for tsv in sorted(class_dir.glob("*.tsv"))}
            if class_dir.exists() else {}
        )
        # Ordered union: expected first (preserving diagnostics order), then extras.
        seen: set = set()
        ordered: list = []
        for c in exp_constructions:
            if c not in seen:
                ordered.append(c)
                seen.add(c)
        for c in sorted(actual):
            if c not in seen:
                ordered.append(c)
                seen.add(c)
        if not ordered:
            continue
        constructions: Dict[str, dict] = {}
        for construction in ordered:
            if construction in actual:
                try:
                    tsv = pd.read_csv(actual[construction], sep="\t", dtype=str,
                                      keep_default_na=False)
                    constructions[construction] = _rows_completeness(
                        class_name, construction, list(tsv.columns), tsv.values.tolist())
                except Exception as e:
                    constructions[construction] = {
                        "total": 0, "filled": 0, "blank": 0, "error": str(e)
                    }
            else:
                # Expected by diagnostics but not yet present in coded_data (Layer 1).
                constructions[construction] = {
                    "total": 0, "filled": 0, "blank": 0, "missing": True
                }
        result[class_name] = constructions
    return result


def completeness_summary(completeness: Dict[str, Dict[str, dict]]) -> dict:
    """language_completeness()'s result in brief, as the laminar bundles and
    the chapters record it: ``{"filled": int, "total": int, "by_construction":
    {"class/construction": "423/423 cells" | "not yet imported" |
    "unreadable: …"}}``. A construction not yet imported or unreadable
    counts towards neither total."""
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
    return {"filled": filled, "total": total, "by_construction": by_construction}


def project_completeness(repo_root) -> Dict[str, Dict[str, Dict[str, dict]]]:
    """Per-language, per-construction completeness for the whole project.

    Returns:
        {lang_id: {class_name: {construction: {"total": int, "filled": int, "blank": int}}}}
    """
    return {lang_dir.name: language_completeness(lang_dir.name, repo_root)
            for lang_dir in _lang_dirs(repo_root)}


def print_completeness(completeness: Dict[str, Dict[str, dict]],
                       status: Optional[Dict[str, Dict[str, str]]] = None) -> bool:
    """Print one language's ``language_completeness`` a line per construction,
    each with its review status from ``status`` (``from_sheets.Language.status``)
    when given. Returns whether every construction is complete."""
    status = status or {}
    all_complete = True
    for class_name, constructions in sorted(completeness.items()):
        for construction, stats in sorted(constructions.items()):
            label = f"{class_name} / {construction}"
            badge = status.get(class_name, {}).get(construction, "")
            badge_str = f"  [{badge}]" if badge else ""
            if "error" in stats:
                print(f"  {label:<45}  ERROR: {stats['error']}")
                all_complete = False
            elif stats.get("missing"):
                print(f"  {label:<45}  no tab yet")
                all_complete = False
            elif stats["blank"] == 0:
                print(f"  {label:<45}  {stats['filled']}/{stats['total']} filled  ✓{badge_str}")
            else:
                print(f"  {label:<45}  {stats['filled']}/{stats['total']} filled  "
                      f"⚠  {stats['blank']} blank{badge_str}")
                all_complete = False
    return all_complete


# ---------------------------------------------------------------------------
# Public API — report bundle
# ---------------------------------------------------------------------------

def language_report_data(
    lang_id: str,
    repo_root,
    status: Optional[Dict[str, Dict[str, str]]] = None,
) -> dict:
    """Aggregated report bundle for one language.

    ``status`` is each class sheet's Status tab, when the caller has read
    it (``planars.from_sheets``).

    Returns a dict with keys:
        lang_id:        str — the Glottocode
        display_name:   str — "Name [glottocode]" if in languages.yaml, else bare code
        generated_at:   datetime.datetime — UTC timestamp
        completeness:   dict — from language_completeness()
        status:         dict or None — the ``status`` given, else None
        spans:          pd.DataFrame or None — span rows for this language;
                        columns as project_spans() describes. Write to TSV
                        for R or other consumers.
        lang_meta:      dict or None — {"keystone_pos": int, "pos_to_name": dict}
                        needed for chart rendering and tree traversal.

    Any None value means "not available" rather than an error.
    """
    display_name = get_display_name(lang_id)
    generated_at = datetime.datetime.now(datetime.timezone.utc)

    completeness = language_completeness(lang_id, repo_root)

    spans = None
    lang_meta_entry = None
    try:
        df, lm = language_spans(lang_id, repo_root)
        spans = df if not df.empty else None
        lang_meta_entry = lm.get(lang_id)
    except Exception:
        pass

    return {
        "lang_id": lang_id,
        "display_name": display_name,
        "generated_at": generated_at,
        "completeness": completeness,
        "status": status,
        "spans": spans,
        "lang_meta": lang_meta_entry,
    }
