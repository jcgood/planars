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

Typical usage (coordinator CLI)
---------------------------------
    from planars.reports import project_spans, language_report_data
    from pathlib import Path

    repo_root = Path(".")
    df, lang_meta = project_spans(source="local", repo_root=repo_root)
    data = language_report_data("arao1248", source="local", repo_root=repo_root)

Typical usage (Colab)
---------------------------------
    from planars.reports import project_spans, language_report_data

    df, lang_meta = project_spans(source="sheets", gc=gc, manifest=manifest)
    data = language_report_data("arao1248", source="sheets", gc=gc, manifest=manifest)
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint
from planars import metrical as _metrical
from planars import nonpermutability as _nonperm
from planars import free_occurrence as _freeoc
from planars import biuniqueness as _biuniq
from planars import repair as _repair
from planars import segmental as _segmental
from planars import suprasegmental as _supra
from planars import pausing as _pausing
from planars import proform as _proform
from planars import play_language as _play
from planars import idiom as _idiom
from planars.io import load_filled_tsv, load_filled_sheet
from planars.languages import get_display_name

# ---------------------------------------------------------------------------
# Span label constants (used here and re-exported by planars.charts for
# backward compatibility with callers such as coding/check_codebook.py)
# ---------------------------------------------------------------------------

_CISC_SPANS = [
    ("strict_complete_span", "cisc strict complete"),
    ("loose_complete_span",  "cisc loose complete"),
    ("strict_partial_span",  "cisc strict partial"),
    ("loose_partial_span",   "cisc loose partial"),
]

_SUBSPAN_CATS = {
    "maximum_fillable":          "fill",
    "maximum_widescope_left":    "ws-L",
    "maximum_widescope_right":   "ws-R",
    "maximum_narrowscope_left":  "ns-L",
    "maximum_narrowscope_right": "ns-R",
}
_SUBSPAN_VARIANTS = [
    ("strict_complete", "strict complete"),
    ("loose_complete",  "loose complete"),
    ("strict_partial",  "strict partial"),
    ("loose_partial",   "loose partial"),
]

_NONINT_SPANS = [
    ("no_free_complete_span",    "no-free complete"),
    ("no_free_partial_span",     "no-free partial"),
    ("single_free_complete_span","1-free complete"),
    ("single_free_partial_span", "1-free partial"),
]

_METRICAL_BLOCKED_SPANS = [
    ("minimal_partial_span",  "metr minimal partial"),
    ("minimal_complete_span", "metr minimal complete"),
    ("maximal_partial_span",  "metr maximal partial"),
    ("maximal_complete_span", "metr maximal complete"),
]

_SEGMENTAL_BLOCKED_SPANS = [
    ("minimal_partial_span",  "seg minimal partial"),
    ("minimal_complete_span", "seg minimal complete"),
    ("maximal_partial_span",  "seg maximal partial"),
    ("maximal_complete_span", "seg maximal complete"),
]

# Standard 4-span pattern shared by most simple modules.
_SIMPLE_SPANS = [
    ("strict_complete_span", "strict complete"),
    ("loose_complete_span",  "loose complete"),
    ("strict_partial_span",  "strict partial"),
    ("loose_partial_span",   "loose partial"),
]

_NONPERM_SPANS = [
    ("strict_complete_span",   "strict complete"),
    ("strict_partial_span",    "strict partial"),
    ("flexible_complete_span", "flexible complete"),
    ("flexible_partial_span",  "flexible partial"),
]


# ---------------------------------------------------------------------------
# Row extraction helpers
# ---------------------------------------------------------------------------

def _rows_from_cisc(result, lang_id):
    rows = []
    for key, label in _CISC_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "ciscategorial",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_subspan(result, lang_id):
    rows = []
    for cat, short in _SUBSPAN_CATS.items():
        for variant, vlabel in _SUBSPAN_VARIANTS:
            l, r = result[f"{variant}_{cat}_span"]
            rows.append({"Language": lang_id, "Test_Labels": f"{short} {vlabel}",
                         "Analysis": "subspanrepetition",
                         "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_nonint(result, lang_id):
    rows = []
    for key, label in _NONINT_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "noninterruption",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_metrical(result, lang_id):
    rows = []
    if result.get("domain_logic") == "blocked":
        span_list = _METRICAL_BLOCKED_SPANS
    else:
        span_list = _SIMPLE_SPANS
    for key, label in span_list:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "metrical",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_segmental(result, lang_id):
    rows = []
    if result.get("domain_logic") == "blocked":
        span_list = _SEGMENTAL_BLOCKED_SPANS
    else:
        span_list = _SIMPLE_SPANS
    for key, label in span_list:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "segmental",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _make_simple_rows(analysis_name, span_list=None):
    """Factory: returns a row function for modules with a standard span set."""
    if span_list is None:
        span_list = _SIMPLE_SPANS

    def _fn(result, lang_id):
        rows = []
        for key, label in span_list:
            l, r = result[key]
            rows.append({"Language": lang_id,
                         "Test_Labels": f"{analysis_name} {label}",
                         "Analysis": analysis_name,
                         "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
        return rows

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
    "free_occurrence":   (_freeoc.derive_free_occurrence_spans,       _make_simple_rows("free_occurrence")),
    "biuniqueness":      (_biuniq.derive_biuniqueness_domains,        _make_simple_rows("biuniqueness")),
    "repair":            (_repair.derive_repair_domains,              _make_simple_rows("repair")),
    "segmental":         (_segmental.derive_segmental_domains,        _rows_from_segmental),
    "suprasegmental":    (_supra.derive_suprasegmental_domains,       _make_simple_rows("suprasegmental")),
    "pausing":           (_pausing.derive_pausing_domains,            _make_simple_rows("pausing")),
    "proform":           (_proform.derive_proform_domains,            _make_simple_rows("proform")),
    "play_language":     (_play.derive_play_language_domains,         _make_simple_rows("play_language")),
    "idiom":             (_idiom.derive_idiom_domains,                _make_simple_rows("idiom")),
}


# ---------------------------------------------------------------------------
# Span collection (primary analytical output)
# ---------------------------------------------------------------------------

def project_spans(
    source: str = "local",
    repo_root=None,
    gc=None,
    manifest: Optional[dict] = None,
) -> Tuple[pd.DataFrame, dict]:
    """Collect spans for all languages.

    Returns (DataFrame, lang_meta) where:
      DataFrame columns: Language, Test_Labels, Analysis, Left_Edge, Right_Edge, Size
      lang_meta: {lang_id: {"keystone_pos": int, "pos_to_name": {int: str}}}

    Each language has its own independent planar structure and position numbering.
    lang_meta is needed for chart rendering and tree traversal.

    For R or other downstream consumers, write the DataFrame to TSV:
        df.to_csv("spans.tsv", sep="\\t", index=False)
    """
    if source == "local":
        if repo_root is None:
            raise ValueError("repo_root is required when source='local'")
        return _collect_spans_local(Path(repo_root))
    elif source == "sheets":
        if gc is None or manifest is None:
            raise ValueError("gc and manifest are required when source='sheets'")
        return _collect_spans_sheets(gc, manifest)
    else:
        raise ValueError(f"Unknown source: {source!r}. Expected 'local' or 'sheets'.")


def language_spans(
    lang_id: str,
    source: str = "local",
    repo_root=None,
    gc=None,
    manifest: Optional[dict] = None,
) -> Tuple[pd.DataFrame, dict]:
    """Collect spans for one language.

    Returns (DataFrame, lang_meta) with the same structure as project_spans,
    but restricted to lang_id. More efficient than project_spans for single-
    language use because it only processes that language's TSVs/sheets.

    lang_meta is a single-entry dict: {lang_id: {"keystone_pos": int, "pos_to_name": dict}}
    """
    if source == "local":
        if repo_root is None:
            raise ValueError("repo_root is required when source='local'")
        return _collect_spans_local(Path(repo_root), lang_id=lang_id)
    elif source == "sheets":
        if gc is None or manifest is None:
            raise ValueError("gc and manifest are required when source='sheets'")
        return _collect_spans_sheets(gc, manifest, lang_id=lang_id)
    else:
        raise ValueError(f"Unknown source: {source!r}. Expected 'local' or 'sheets'.")


def _collect_spans_local(repo_root: Path, lang_id: Optional[str] = None):
    """Internal: collect spans from coded_data/ TSVs.

    If lang_id is given, process only that language's directory.
    """
    rows = []
    lang_meta = {}

    coded_data = repo_root / "coded_data"
    if lang_id is not None:
        lang_dirs = [coded_data / lang_id]
    else:
        lang_dirs = sorted(
            d for d in coded_data.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    for lang_dir in lang_dirs:
        if not lang_dir.is_dir():
            continue
        lid = lang_dir.name
        for class_name, (derive_fn, row_fn) in _CLASS_HANDLERS.items():
            class_dir = lang_dir / class_name
            if not class_dir.exists():
                continue
            for tsv in sorted(class_dir.glob("*.tsv")):
                result = derive_fn(tsv, strict=False)
                rows.extend(row_fn(result, lid))
                if lid not in lang_meta:
                    lang_meta[lid] = {
                        "keystone_pos": result["keystone_position"],
                        "pos_to_name":  result["position_number_to_name"],
                    }

    return pd.DataFrame(rows), lang_meta


def _collect_spans_sheets(gc, manifest, lang_id: Optional[str] = None):
    """Internal: collect spans directly from Google Sheets.

    If lang_id is given, process only that language's manifest entry.
    """
    rows = []
    lang_meta = {}

    items = (
        [(lang_id, manifest[lang_id])] if lang_id is not None
        else manifest.items()
    )

    for lid, lang_data in items:
        for class_name, (derive_fn, row_fn) in _CLASS_HANDLERS.items():
            sheet_info = lang_data.get("sheets", {}).get(class_name)
            if not sheet_info:
                continue
            try:
                ss = gc.open_by_key(sheet_info["spreadsheet_id"])
            except Exception as e:
                print(f"  WARNING: could not open {class_name} sheet for {lid}: {e}")
                continue
            construction_params = sheet_info.get("construction_params", {})
            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except Exception:
                    print(f"  WARNING: tab '{construction}' not found in {class_name} sheet")
                    continue
                required = set(
                    construction_params.get(construction, {}).get("param_names", [])
                )
                loaded = load_filled_sheet(ws, required_criteria=required, strict=False)
                result = derive_fn(_data=loaded, strict=False)
                rows.extend(row_fn(result, lid))
                if lid not in lang_meta:
                    lang_meta[lid] = {
                        "keystone_pos": result["keystone_position"],
                        "pos_to_name":  result["position_number_to_name"],
                    }

    return pd.DataFrame(rows), lang_meta


# Backward-compatible aliases matching the names previously exported by charts.py.
# New code should prefer project_spans() / language_spans().
def collect_all_spans(repo_root) -> Tuple[pd.DataFrame, dict]:
    """Run all analyses over coded_data/ and return (DataFrame, lang_meta).

    Deprecated alias for project_spans(source="local", repo_root=repo_root).
    Kept for backward compatibility with notebooks and check_codebook.py.
    """
    return project_spans(source="local", repo_root=repo_root)


def collect_all_spans_from_sheets(gc, manifest) -> Tuple[pd.DataFrame, dict]:
    """Run all analyses directly from Google Sheets and return (DataFrame, lang_meta).

    Deprecated alias for project_spans(source="sheets", gc=gc, manifest=manifest).
    Kept for backward compatibility with notebooks and Colab workflows.
    """
    return project_spans(source="sheets", gc=gc, manifest=manifest)


# ---------------------------------------------------------------------------
# Completeness helpers
# ---------------------------------------------------------------------------

# Columns that are structural (position metadata), not criterion values.
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


def _read_expected_constructions(lang_dir: Path) -> Dict[str, list]:
    """Read diagnostics_{lang_id}.tsv and return {class_name: [constructions]}.

    Returns {} if the diagnostics file is absent or cannot be parsed.
    Used by language_completeness to determine Layer 1 completeness: which
    constructions are expected but not yet present in coded_data/.
    """
    lang_id = lang_dir.name
    diag_path = lang_dir / "planar_input" / f"diagnostics_{lang_id}.tsv"
    if not diag_path.exists():
        return {}
    try:
        df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        result: Dict[str, list] = {}
        for _, row in df.iterrows():
            class_name = str(row.get("Class", "")).strip()
            constructions_raw = str(row.get("Constructions", "")).strip()
            if not class_name or not constructions_raw:
                continue
            constructions = [c.strip() for c in constructions_raw.split(",") if c.strip()]
            if constructions:
                result.setdefault(class_name, []).extend(constructions)
        return result
    except Exception:
        return {}

# Trailing sheet columns that are not annotation criteria (e.g. free-text notes).
# Matches the definition in coding/generate_sheets.py.
_TRAILING_COLS = {"Comments"}

# Name of the per-spreadsheet tab that records construction review status.
_STATUS_TAB = "Status"


def _criterion_cols_only(criterion_cols: list) -> list:
    """Filter out trailing columns (e.g. Comments) from criterion_cols."""
    return [c for c in criterion_cols if c not in _TRAILING_COLS]


def _tab_completeness(data_df: pd.DataFrame, criterion_cols: list) -> dict:
    """Completeness stats for one annotation tab.

    data_df must already exclude keystone rows (as returned by load_filled_tsv
    or load_filled_sheet). criterion_cols is the full non-structural column list
    from the same loader — trailing cols (Comments) are excluded automatically.

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


# ---------------------------------------------------------------------------
# Public API — completeness
# ---------------------------------------------------------------------------

def language_completeness(
    lang_id: str,
    source: str = "local",
    repo_root=None,
    gc=None,
    manifest: Optional[dict] = None,
) -> Dict[str, Dict[str, dict]]:
    """Per-construction completeness stats for one language.

    Covers three layers for source="local":
      Layer 1 — construction completeness: constructions declared in
        diagnostics_{lang_id}.tsv but not yet present in coded_data/ are
        included with {"total": 0, "filled": 0, "blank": 0, "missing": True}.
      Layer 2 — cell completeness: for present TSVs, counts filled vs. blank
        criterion cells (excluding Comments and structural columns).
      Layer 3 — structural completeness: not covered here; use validate-coding.

    Returns:
        {class_name: {construction: {"total": int, "filled": int, "blank": int}}}

    Extra keys in the per-construction dict:
        "missing": True  — construction expected but TSV not yet present (Layer 1)
        "error": str     — TSV present but could not be loaded
    """
    if source == "local":
        if repo_root is None:
            raise ValueError("repo_root is required when source='local'")
        lang_dir = Path(repo_root) / "coded_data" / lang_id

        # Layer 1: expected constructions from diagnostics_{lang_id}.tsv.
        expected = _read_expected_constructions(lang_dir)

        # Collect all class names: declared in diagnostics + present in coded_data.
        present_dirs = {
            d.name for d in lang_dir.iterdir()
            if d.is_dir() and d.name not in {"planar_input", "archive"}
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
                        data_df, _, _, crit_cols, _ = load_filled_tsv(
                            actual[construction], required_criteria=set(), strict=False
                        )
                        constructions[construction] = _tab_completeness(data_df, crit_cols)
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

    elif source == "sheets":
        if gc is None or manifest is None:
            raise ValueError("gc and manifest are required when source='sheets'")
        lang_data = manifest.get(lang_id, {})
        result = {}
        for class_name, sheet_info in lang_data.get("sheets", {}).items():
            try:
                ss = gc.open_by_key(sheet_info["spreadsheet_id"])
            except Exception as e:
                result[class_name] = {"_error": str(e)}
                continue
            construction_params = sheet_info.get("construction_params", {})
            constructions = {}
            for construction in sheet_info.get("constructions", []):
                try:
                    ws = ss.worksheet(construction)
                except Exception:
                    continue
                required = set(
                    construction_params.get(construction, {}).get("param_names", [])
                )
                try:
                    data_df, _, _, crit_cols, _ = load_filled_sheet(
                        ws, required_criteria=required, strict=False
                    )
                    constructions[construction] = _tab_completeness(data_df, crit_cols)
                except Exception as e:
                    constructions[construction] = {
                        "total": 0, "filled": 0, "blank": 0, "error": str(e)
                    }
            if constructions:
                result[class_name] = constructions
        return result

    else:
        raise ValueError(f"Unknown source: {source!r}. Expected 'local' or 'sheets'.")


def project_completeness(
    source: str = "local",
    repo_root=None,
    gc=None,
    manifest: Optional[dict] = None,
) -> Dict[str, Dict[str, Dict[str, dict]]]:
    """Per-language, per-construction completeness for the whole project.

    Returns:
        {lang_id: {class_name: {construction: {"total": int, "filled": int, "blank": int}}}}
    """
    if source == "local":
        if repo_root is None:
            raise ValueError("repo_root is required when source='local'")
        coded_data = Path(repo_root) / "coded_data"
        return {
            lang_dir.name: language_completeness(
                lang_dir.name, source="local", repo_root=repo_root
            )
            for lang_dir in sorted(coded_data.iterdir())
            if lang_dir.is_dir() and not lang_dir.name.startswith(".")
        }
    elif source == "sheets":
        if gc is None or manifest is None:
            raise ValueError("gc and manifest are required when source='sheets'")
        return {
            lang_id: language_completeness(
                lang_id, source="sheets", gc=gc, manifest=manifest
            )
            for lang_id in sorted(manifest)
        }
    else:
        raise ValueError(f"Unknown source: {source!r}. Expected 'local' or 'sheets'.")


# ---------------------------------------------------------------------------
# Public API — status
# ---------------------------------------------------------------------------

def language_status(lang_id: str, gc, manifest: dict) -> Dict[str, Dict[str, str]]:
    """Status tab contents for one language (Google Sheets only).

    Reads the Status tab from each annotation spreadsheet for lang_id.

    Returns:
        {class_name: {construction: status_string}}
        e.g. {"ciscategorial": {"general": "ready-for-review"}}

    Note: coding/import_sheets.py has _read_status_tab() which does the same
    per-spreadsheet read. That function can't be imported here because planars/
    must not depend on coding/ (Colab installs only planars/). The logic is
    simple enough to inline; keep the two in sync if the Status tab format changes.
    """
    lang_data = manifest.get(lang_id, {})
    result: Dict[str, Dict[str, str]] = {}
    for class_name, sheet_info in lang_data.get("sheets", {}).items():
        try:
            ss = gc.open_by_key(sheet_info["spreadsheet_id"])
        except Exception:
            continue
        try:
            ws = ss.worksheet(_STATUS_TAB)
        except Exception:
            continue
        rows = ws.get_all_values()
        if len(rows) < 2:
            continue
        result[class_name] = {
            row[0].strip(): row[1].strip()
            for row in rows[1:]
            if len(row) >= 2 and row[0].strip()
        }
    return result


# ---------------------------------------------------------------------------
# Public API — report bundle
# ---------------------------------------------------------------------------

def language_report_data(
    lang_id: str,
    source: str = "local",
    repo_root=None,
    gc=None,
    manifest: Optional[dict] = None,
) -> dict:
    """Aggregated report bundle for one language.

    Returns a dict with keys:
        lang_id:        str — the Glottocode
        display_name:   str — "Name [glottocode]" if in languages.yaml, else bare code
        generated_at:   datetime.datetime — UTC timestamp
        completeness:   dict — from language_completeness()
        status:         dict or None — from language_status() (None for source="local")
        spans:          pd.DataFrame or None — span rows for this language;
                        columns: Language, Test_Labels, Analysis, Left_Edge,
                        Right_Edge, Size. Write to TSV for R or other consumers.
        lang_meta:      dict or None — {"keystone_pos": int, "pos_to_name": dict}
                        needed for chart rendering and tree traversal.

    Any None value means "not available" rather than an error.
    """
    display_name = get_display_name(lang_id)
    generated_at = datetime.datetime.now(datetime.timezone.utc)

    completeness = language_completeness(
        lang_id, source=source, repo_root=repo_root, gc=gc, manifest=manifest
    )

    status = None
    if source == "sheets" and gc is not None and manifest is not None:
        status = language_status(lang_id, gc, manifest)

    spans = None
    lang_meta_entry = None
    try:
        df, lm = language_spans(
            lang_id, source=source, repo_root=repo_root, gc=gc, manifest=manifest
        )
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
