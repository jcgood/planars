#!/usr/bin/env python3
"""Project-wide integrity check for the planars annotation pipeline.

Runs ten sections of checks and prints a structured report:

  PLANAR STRUCTURE               — validates planar_*.tsv for each language
  DIAGNOSTICS                    — validates diagnostics_*.yaml for each language
  CODEBOOK CONSISTENCY           — cross-checks the diagnostics files against schema files
  ANALYSIS CONSISTENCY           — validates analysis modules match diagnostic_criteria.yaml
  CROSS-SHEET CONSISTENCY        — checks free values agree across related annotation sheets
  DEPENDENT CONSTRUCTION STALENESS — pair-row constructions (nonpermutability/general,
                                    coreference's three, phrasal_accent/general) compared
                                    by row key with the rows the generator would make now
                                    (sheet_spec.expected_row_keys -> generate_sheets.pair_rows,
                                    the builder regeneration and the Drive door use; no copy
                                    of any class's scope rule lives here), AND, since issue
                                    #241, by position number: a pair-row can name a position
                                    number superseded by a structural change elsewhere in
                                    the planar (see _find_stale_position_cells/
                                    _suggest_position_remap). When recoverable, prints
                                    ready-to-use --pos-remap flags. Keyed tabs
                                    (biuniqueness_deviations' morphemes/morphs) are
                                    compared by row key (_keyed_staleness).
  ANNOTATION SHEETS             — checks live sheet structure and dropdown drift (requires --sheets)
  SHARING                        — every labelled Drive file's own grants against its sharing
                                    rule (sheet_spec.sharing_spec): catches access changed by hand
                                    in the Drive window, which the Drive door never sees.
  NEEDS REVIEW / PLACEHOLDERS    — surfaces [NEEDS REVIEW] / [PLACEHOLDER] / [NEEDS COORDINATOR
                                    INPUT] markers (check_codebook.needs_review_entries)

Exit code 0 if no errors; 1 if any errors (warnings do not fail).

Writes nothing. Drive is reached through the doorway, by two independent
read-only entry points: --sheets (open each spreadsheet, list its tabs, read
its header, comparing the tabs and criteria columns with the diagnostics YAML)
and --check-manifest (the ID file and the YAML, no Drive calls; the name is
older than the ID file, and the manifest it once read was deleted in unit
11c-5).

Usage:
    python -m coding integrity-check
    python -m coding integrity-check --lang arao1248
    python -m coding integrity-check --sheets

Two fast standalone modes run one check only (used by the daily refresh):
    python -m coding integrity-check --check-manifest    # class sheets whose class left diagnostics
    python -m coding integrity-check --check-dependents  # stale dependent constructions
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .sheet_spec import class_sheet_spec, expected_row_keys, parked_operation
from .validate import ValidationIssue
from .validate_planar import validate_planar_df
from .validate_diagnostics import validate_diagnostics_yaml
from .check_codebook import (
    _load_codebook,
    _load_diagnostic_classes,
    _check_required_criteria,
    _check_diagnostics_vs_classes,
    _check_chart_keys,
    needs_review_entries,
)
from planars import drive_labels
from planars.schema_values import (
    ELEMENT_ROW_COLUMNS, PAIR_ROW_SHAPES, STATUS_READY, TRAILING_COLUMNS,
)
from .restructure_sheets import (
    _PAIR_POS_COLS, _get_keyed_row_constructions, _get_pair_row_constructions,
)
from .glottolog import is_synthetic
import yaml as _yaml

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

_WIDTH = 72


def _section(title: str) -> str:
    bar = "─" * (_WIDTH - len(title) - 4)
    return f"\n── {title} {bar}"


def _ok(msg: str) -> str:
    return f"  ✓  {msg}"


def _fail(msg: str) -> str:
    return f"  ✗  {msg}"


def _warn(msg: str) -> str:
    return f"  ⚠  {msg}"


def _sub(msg: str) -> str:
    return f"       {msg}"


def _load_languages_yaml() -> dict:
    """Load schemas/languages.yaml, returning {} on any error.

    Not loaded via coding.schemas (the shared cached loader module) because
    languages.yaml is written to by ``lookup-lang`` mid-session. A cached
    loader would return stale data after a write. Each caller reads it fresh.
    """
    path = ROOT / "schemas" / "languages.yaml"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return _yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


_LANGUAGES: dict = {}  # module-level cache populated on first call


def _lang_label(lang_id: str) -> str:
    global _LANGUAGES
    if not _LANGUAGES:
        _LANGUAGES = _load_languages_yaml()
    name = _LANGUAGES.get(lang_id, {}).get("glottolog", {}).get("name")
    return f"{name} [{lang_id}]" if name else lang_id


def _print_issues(issues: List[ValidationIssue], label: str) -> Tuple[int, int]:
    """Print a label line with ✓/✗/⚠ prefix, then sub-lines for issues.

    Returns (errors, warnings).
    """
    errs  = [i for i in issues if i.level == "error"]
    warns = [i for i in issues if i.level == "warning"]
    if errs:
        print(_fail(label))
        for i in errs:
            print(_sub(f"[ERROR] {i.location}: {i.message}"))
        for i in warns:
            print(_sub(f"[WARNING] {i.location}: {i.message}"))
    elif warns:
        print(_warn(label))
        for i in warns:
            print(_sub(f"[WARNING] {i.location}: {i.message}"))
    else:
        print(_ok(label))
    return len(errs), len(warns)


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _section_planar(lang_ids: List[str]) -> Tuple[int, int]:
    print(_section("PLANAR STRUCTURE"))
    total_e = total_w = 0

    for lang_id in lang_ids:
        planar_dir = CODED_DATA / lang_id / "lang_setup"
        lang = _lang_label(lang_id)

        if not planar_dir.exists():
            print(_fail(f"{lang}  —  no lang_setup/ directory"))
            print(_sub(f"→ Language onboarding is incomplete."))
            print(_sub(f"  See docs/coordinator-guide.md § 'Onboarding a new language'."))
            total_e += 1
            continue

        planar_files = sorted(planar_dir.glob("planar_*.tsv"))
        if not planar_files:
            print(_fail(f"{lang}  —  no planar_*.tsv found in lang_setup/"))
            print(_sub(f"→ Add the planar TSV: coded_data/{lang_id}/lang_setup/planar_{lang_id}-YYYYMMDD.tsv"))
            print(_sub(f"  See docs/coordinator-guide.md § 'Onboarding a new language'."))
            total_e += 1
            continue

        planar_path = planar_files[-1]
        try:
            df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
        except Exception as exc:
            print(_fail(f"{lang}  —  {planar_path.name}: {exc}"))
            total_e += 1
            continue

        issues = validate_planar_df(df)
        label = f"{lang:<34}  {planar_path.name}"
        e, w = _print_issues(issues, label)
        total_e += e
        total_w += w

        # (A file-date comparison of nonpermutability TSVs against the planar
        # stood here until 2026-10-13. It compared when git last wrote each
        # file, not what they hold, so it warned on languages nobody had
        # touched, and its advice -- generate-sheets --apply -- skips classes
        # that already have sheets. Staleness is checked by content instead:
        # the DEPENDENT CONSTRUCTION STALENESS section below, and update-sheets'
        # daily sheet-drift check for elements added to the planar.)

    return total_e, total_w


def _section_diagnostics(lang_ids: List[str]) -> Tuple[int, int]:
    print(_section("DIAGNOSTICS"))
    total_e = total_w = 0

    for lang_id in lang_ids:
        diag_path = CODED_DATA / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
        lang = _lang_label(lang_id)

        if not diag_path.exists():
            print(_fail(f"{lang}  —  diagnostics_{lang_id}.yaml not found"))
            print(_sub("→ Language onboarding is incomplete."))
            print(_sub(f"  Create coded_data/{lang_id}/lang_setup/diagnostics_{lang_id}.yaml."))
            print(_sub("  See docs/coordinator-guide.md § 'Onboarding a new language'."))
            total_e += 1
            continue

        try:
            with open(diag_path, encoding="utf-8") as f:
                data = _yaml.safe_load(f)
        except Exception as exc:
            print(_fail(f"{lang}  —  could not read diagnostics file: {exc}"))
            total_e += 1
            continue

        issues = validate_diagnostics_yaml(data, lang_id)
        label = f"{lang:<34}  diagnostics_{lang_id}.yaml"
        e, w = _print_issues(issues, label)
        total_e += e
        total_w += w

    return total_e, total_w


def _section_codebook(diag_classes: dict) -> Tuple[int, int]:
    print(_section("CODEBOOK CONSISTENCY"))

    errs_classes = _check_diagnostics_vs_classes(diag_classes)

    if errs_classes:
        print(_fail("diagnostics files vs. diagnostic_classes.yaml"))
        for e in errs_classes:
            print(_sub(e))
    else:
        print(_ok("diagnostics files match diagnostic_classes.yaml"))

    return len(errs_classes), 0


def _section_analysis(codebook: dict) -> Tuple[int, int]:
    print(_section("ANALYSIS CONSISTENCY"))

    errs_req  = _check_required_criteria(codebook)
    errs_keys = _check_chart_keys()

    if errs_req:
        print(_fail("Module _REQUIRED_CRITERIA vs. diagnostic_criteria.yaml"))
        for e in errs_req:
            print(_sub(e))
        print(_sub("→ Add the missing criterion to schemas/diagnostic_criteria.yaml,"))
        print(_sub("  then run: python -m coding check-codebook"))
    else:
        print(_ok("Module _REQUIRED_CRITERIA all defined in diagnostic_criteria.yaml"))

    if errs_keys:
        print(_fail("Chart span keys vs. derive function result dicts"))
        for e in errs_keys:
            print(_sub(e))
        print(_sub("→ Fix the mismatched key in the module's derive_*() return dict or in"))
        print(_sub("  schemas/terms.yaml (span_label_map), then run: pytest"))
    else:
        print(_ok("All chart span keys match derive function result dicts"))

    return len(errs_req) + len(errs_keys), 0


def _stale_manifest_classes(config: dict, lang_ids: List[str]) -> List[Tuple[str, str]]:
    """Return (lang_id, class_name) pairs recorded with a class sheet in the ID
    file (drive_config.json) but absent from the language's diagnostics YAML.

    Reads the ID file's contents (``config``) and local diagnostics_{lang}.yaml
    — no Drive calls. A language without a YAML is skipped (the DIAGNOSTICS
    section reports it).
    """
    from . import drive_ids
    stale = []
    for lang_id in lang_ids:
        sheets_info = drive_ids.class_sheets(config, lang_id)
        if not sheets_info:
            continue
        yaml_path = CODED_DATA / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
        if not yaml_path.exists():
            continue
        with open(yaml_path, encoding="utf-8") as _f:
            _diag = _yaml.safe_load(_f)
        active = set(((_diag or {}).get("classes") or {}).keys())
        for cls in sorted(set(sheets_info.keys()) - active):
            stale.append((lang_id, cls))
    return stale


def _section_sheets(lang_ids: List[str]) -> Tuple[int, int]:
    print(_section("ANNOTATION SHEETS"))

    try:
        from . import drive, drive_ids
        from .drive_doorway import get_doorway
        from .make_forms import _read_diagnostics_for_language
    except ImportError as exc:
        print(_warn(f"Could not import sheet utilities: {exc}"))
        return 0, 1

    try:
        doorway = get_doorway()
        config = drive._load_drive_config()
    except Exception as exc:
        print(_fail(f"Could not connect to Google Sheets: {exc}"))
        return 1, 0

    _STRUCTURAL       = set(ELEMENT_ROW_COLUMNS)
    _PAIR_STRUCTURAL  = set().union(*PAIR_ROW_SHAPES.values())
    _TRAILING         = set(TRAILING_COLUMNS)

    # Which constructions use pair_rows layout -- read via the shared helper
    # (same one validate_coding.py/import_sheets.py/generate_status_sheet.py
    # use), not recomputed locally, so this can't silently drift from theirs
    # the way import_sheets.py's hardcoded list once did (issue #275). Fixed
    # 2026-08-16, found reviewing this section for
    # data_dependency_schema/operations.yaml -- previously correct, but
    # duplicated rather than shared.
    _pair_row_constructions = _get_pair_row_constructions()
    _keyed_row_constructions = _get_keyed_row_constructions()

    total_e = total_w = 0

    for lang_id in lang_ids:
        lang = _lang_label(lang_id)
        sheet_ids = drive_ids.class_sheets(config, lang_id)

        if lang_id not in drive_ids.languages(config):
            print(_warn(f"{lang}  —  not in the ID file"))
            total_w += 1
            continue

        # Check project metadata completeness against languages.yaml (source of truth).
        lang_entry = _LANGUAGES.get(lang_id, {})
        meta = lang_entry.get("meta", {})
        _KEY_META = tuple(_LANGUAGES.get("required_meta_fields", ["source", "author"]))
        missing_meta = [f for f in _KEY_META if not meta.get(f)]
        if is_synthetic(lang_id):
            pass  # a synthetic test language has no languages.yaml entry, by design
        elif not lang_entry:
            print(_warn(f"{lang}  —  not in schemas/languages.yaml "
                        f"(run python -m coding lookup-lang {lang} to add)"))
            total_w += 1
        elif not meta:
            print(_warn(f"{lang}  —  meta block missing from languages.yaml "
                        f"(run python -m coding lookup-lang {lang} to scaffold)"))
            total_w += 1
        elif missing_meta:
            print(_warn(f"{lang}  —  languages.yaml meta incomplete: {', '.join(missing_meta)} not set"))
            total_w += 1

        if not sheet_ids:
            print(_warn(f"{lang}  —  no class sheets in the ID file"))
            total_w += 1
            continue

        # Check for retired classes still recorded (no Sheet API calls).
        for _, stale_cls in _stale_manifest_classes(config, [lang_id]):
            print(_warn(f"{lang} · {stale_cls}  —  in the ID file but not in diagnostics"))
            print(_sub(f"→ run: python -m coding prune-manifest --apply"))
            total_w += 1

        # What each tab should hold comes from the diagnostics YAML.
        try:
            diag_rows = _read_diagnostics_for_language(
                lang_id, CODED_DATA / lang_id / "lang_setup")
        except Exception as exc:
            print(_warn(f"{lang}  —  could not read diagnostics YAML: {exc}"))
            total_w += 1
            diag_rows = []
        yaml_tabs: dict = {}
        for cls, con, names, _vals in diag_rows:
            yaml_tabs.setdefault(cls, {})[con] = list(names)

        for class_name, sheet_id in sorted(sheet_ids.items()):
            try:
                ss = doorway.open_spreadsheet(sheet_id)
            except Exception as exc:
                print(_fail(f"{lang} · {class_name}  —  could not open spreadsheet: {exc}"))
                total_e += 1
                continue

            try:
                tab_titles = {ws.title for ws in ss.worksheets()}
            except Exception as exc:
                print(_fail(f"{lang} · {class_name}  —  could not list worksheets: {exc}"))
                total_e += 1
                continue
            class_tabs = yaml_tabs.get(class_name, {})

            for construction in class_tabs:
                label = f"{lang} · {class_name} · {construction}"

                if construction not in tab_titles:
                    print(_fail(f"{label}  —  tab missing from spreadsheet"))
                    total_e += 1
                    continue

                try:
                    ws     = ss.worksheet(construction)
                    header = ws.row_values(1)
                except Exception as exc:
                    print(_fail(f"{label}  —  could not read header: {exc}"))
                    total_e += 1
                    continue

                expected = class_tabs[construction]
                is_pair_row = construction in _pair_row_constructions.get(class_name, set())
                keyed = _keyed_row_constructions.get(class_name, {}).get(construction)
                if keyed:
                    _skip = set(keyed["columns"])
                else:
                    _skip = (_STRUCTURAL | _PAIR_STRUCTURAL) if is_pair_row else _STRUCTURAL
                actual   = [c for c in header if c not in _skip and c not in _TRAILING]

                # Warn on stale lifecycle columns left from --split or --merge operations.
                stale = [c for c in actual if parked_operation(c)]
                if stale:
                    print(_warn(label))
                    for col in stale:
                        print(_sub(f"stale {parked_operation(col)} column '{col}'"))
                    print(_sub(f"→ Remap any cell values from the stale column(s) to the current"))
                    print(_sub(f"  criterion column(s) in the Google Sheet, then delete the stale"))
                    print(_sub(f"  column(s) manually, then re-run"))
                    print(_sub(f"  python -m coding integrity-check --sheets to confirm."))
                    total_w += 1
                elif actual != expected:
                    print(_warn(label))
                    print(_sub(f"expected criteria columns: {expected}"))
                    print(_sub(f"actual criteria columns:   {actual}"))
                    print(_sub(f"→ run: python -m coding sync-params --apply"))
                    total_w += 1
                else:
                    print(_ok(label))

    return total_e, total_w


def _section_cross_sheet_consistency(lang_ids: List[str]) -> Tuple[int, int]:
    """Check that free values agree between noninterruption and free_occurrence sheets.

    free is re-coded independently in each sheet (use noninterruption as reference).
    Differences are expected to be rare but warrant coordinator review. Reported as
    warnings, not errors — divergent coding does not block analysis.
    """
    print(_section("CROSS-SHEET CONSISTENCY"))

    from planars.io import load_filled_tsv
    from .schemas import reads_from

    total_w = 0
    any_checked = False
    # Which tab free_occurrence's free values are checked against, and which
    # column: diagnostic_classes.yaml's reads_from.free_agreement.
    src = reads_from("free_occurrence", "free_agreement")
    (free,) = src["criteria"]

    for lang_id in lang_ids:
        ni_path = CODED_DATA / lang_id / src["class"] / f"{src['construction']}.tsv"
        fo_path = CODED_DATA / lang_id / "free_occurrence" / "general.tsv"
        if not ni_path.exists() or not fo_path.exists():
            continue

        any_checked = True
        label = f"{lang_id}: {src['class']} vs free_occurrence ({free} column)"
        try:
            ni_data, _, _, _, _ = load_filled_tsv(ni_path, {free}, strict=False)
            fo_data, _, _, _, _ = load_filled_tsv(fo_path, {free}, strict=False)
        except Exception as exc:
            print(_warn(f"{label} — could not load: {exc}"))
            total_w += 1
            continue

        ni_free = ni_data.set_index("Element")[free].to_dict() if free in ni_data.columns else {}
        fo_free = fo_data.set_index("Element")[free].to_dict() if free in fo_data.columns else {}

        mismatches = []
        for elem in sorted(set(ni_free) & set(fo_free)):
            nv, fv = ni_free[elem], fo_free[elem]
            if nv not in ("", "na", "?") and fv not in ("", "na", "?") and nv != fv:
                mismatches.append(f"{elem}: {src['class']}={nv!r}, free_occurrence={fv!r}")

        if mismatches:
            print(_warn(f"{label}"))
            for m in mismatches:
                print(_sub(m))
            print(_sub("→ Verify in the annotation sheets; update the incorrect value."))
            total_w += len(mismatches)
        else:
            print(_ok(label))

    if not any_checked:
        print(f"  (no languages have both {src['class']} and free_occurrence TSVs)")

    return 0, total_w


def _planar_position_names(lang_id: str) -> dict:
    """{Position (int) -> Position_Name} for a language's current planar structure."""
    path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    out = {}
    for _, row in df.iterrows():
        try:
            out[int(row["Position"])] = row["Position_Name"].strip()
        except (ValueError, KeyError):
            continue
    return out


def _find_stale_position_cells(
    df: pd.DataFrame, position_names: dict, cols: Tuple[str, ...] = _PAIR_POS_COLS
) -> List[Tuple[int, str]]:
    """Return sorted, deduplicated (old_num, old_name) pairs for every
    Position_A/Position_B cell (format "N (name)") whose embedded number no
    longer names the same position in the current planar structure.

    This catches a class of drift that pure element-identity comparison
    (source_set/dep_set above) cannot see at all: a pair-row can reference an
    element that's still validly in scope, at a position number that's since
    been superseded by a structural insertion/deletion elsewhere in the
    planar -- the row looks fine by element identity, but silently points at
    the wrong (or a since-repurposed) position. Discovered 2026-07-31 when
    stan1293's coreference pairs turned out to reference v:obj-part/v:rec by
    position numbers that predate v:obj-R's insertion, apparently since the
    sheets were first generated -- invisible to every check before this one,
    including the guard in generate_sheets.py's _regen_construction, which
    only surfaces it as a side effect of someone actually trying to
    regenerate (see issue #241 discussion). This is the proactive version.
    """
    from .restructure_sheets import _parse_position_cell
    stale = set()
    for col in cols:
        if col not in df.columns:
            continue
        for val in df[col]:
            parsed = _parse_position_cell(val)
            if parsed is None:
                continue
            num, name = parsed
            if position_names.get(num) != name:
                stale.add((num, name))
    return sorted(stale)


def _suggest_position_remap(
    stale_cells: List[Tuple[int, str]], position_names: dict
) -> Tuple[dict, List[Tuple[int, str]]]:
    """Split stale (old_num, old_name) pairs into a recoverable remap and an
    unresolvable leftover.

    remap: {old_num: new_num} wherever old_name still exists somewhere in the
    current planar (just renumbered) -- directly usable as --pos-remap flags.
    unresolvable: (old_num, old_name) pairs whose name isn't in the current
    planar at all -- not a renumbering, the position was genuinely renamed or
    removed; --pos-remap can't fix these, needs coordinator judgment
    (--rename-map, or accept the loss via --confirm-drop).
    """
    name_to_current_num = {name: num for num, name in position_names.items()}
    remap: dict = {}
    unresolvable: List[Tuple[int, str]] = []
    for old_num, old_name in stale_cells:
        new_num = name_to_current_num.get(old_name)
        if new_num is not None:
            remap[old_num] = new_num
        else:
            unresolvable.append((old_num, old_name))
    return remap, unresolvable


def _keyed_staleness(lang_id: str, cls_name: str, con: dict):
    """(keys the source now calls for but the tab lacks, generated keys the
    source no longer calls for), or None if there is nothing to compare yet
    (source or dependent not imported). An empty dependent whose source
    already calls for rows returns ("empty", n): not stale, just not filled
    yet — the daily refresh fills it once the source tab is marked
    ready-for-review (generate_sheets._regen_dependents_simple)."""
    from . import biuniqueness_rows as _br
    if cls_name != _br.CLASS_NAME or con["name"] not in _br.KEYED:
        return None
    cls_dir = CODED_DATA / lang_id / cls_name
    dep_path = cls_dir / f"{con['name']}.tsv"
    planar_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    if not dep_path.exists() or not planar_path.exists() or not all(
            (cls_dir / f"{n}.tsv").exists() for n in _br.sources_of(con["name"])):
        return None
    read = lambda p: pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    dep = read(dep_path)
    generated = _br.keyed_rows(con["name"], lambda tab: read(cls_dir / f"{tab}.tsv"),
                               read(planar_path), lang_id)
    if dep.empty:
        return ("empty", len(generated)) if generated else None
    _, key = _br.KEYED[con["name"]]
    want = {" / ".join(g[k] for k in key) for g in generated}
    have = {" / ".join(str(r[k]) for k in key) for _, r in dep.iterrows()
            if str(r.get("Origin", "")).strip() in _br.GENERATED_ORIGINS}
    return want - have, have - want


def _section_dependent_construction_staleness(
    lang_ids: List[str],
    diag_classes: dict,
) -> Tuple[int, int]:
    """Check for stale dependent constructions.

    First, keyed_source dependents (biuniqueness_deviations' morphemes/morphs)
    are compared by row key (_keyed_staleness). Then, for each class with
    constructions[].depends_on and staleness_check=element_set (the pair tabs):
    compare the rows the generator would make now (sheet_spec.expected_row_keys,
    i.e. generate_sheets.pair_rows) with the imported dependent TSV's rows, by
    the tab's row key. Any difference means regeneration would add or drop rows
    — e.g. an element was promoted (n→y) or demoted (y→n) in the source sheet
    since the dependent was last generated.
    """
    print(_section("DEPENDENT CONSTRUCTION STALENESS"))

    total_e = 0
    any_checked = False

    # keyed_source dependents (biuniqueness_deviations' morphemes/morphs, #254):
    # rebuild the tab from its imported source and compare row keys with the
    # imported dependent. Hand-added rows are the annotator's own and never stale.
    for cls_name, cls_entry in diag_classes.items():
        for con in cls_entry.get("constructions", []) or []:
            if not (con.get("depends_on") and con.get("staleness_check") == "keyed_source"):
                continue
            for lang_id in lang_ids:
                result = _keyed_staleness(lang_id, cls_name, con)
                if result is None:
                    continue
                any_checked = True
                label = f"{_lang_label(lang_id)}: {cls_name}/{con['depends_on']} → {con['name']}"
                if result[0] == "empty":
                    print(_ok(f"{label}: empty, {result[1]} row(s) waiting — filled by the "
                              f"daily refresh once '{con['depends_on']}' is marked "
                              f"{STATUS_READY}"))
                    continue
                added, removed = result
                if added or removed:
                    print(_fail(label))
                    if removed:
                        print(_sub(f"rows whose source is gone ({len(removed)}): "
                                   f"{sorted(removed)[:5]}{' …' if len(removed) > 5 else ''}"))
                    if added:
                        print(_sub(f"rows the source now calls for ({len(added)}): "
                                   f"{sorted(added)[:5]}{' …' if len(added) > 5 else ''}"))
                    print(_sub(f"→ Run: python -m coding generate-sheets --lang {lang_id} "
                               f"--regen-construction {cls_name}:{con['name']}"))
                    total_e += 1
                else:
                    print(_ok(label))

    for cls_name, cls_entry in diag_classes.items():
        constructions_schema = cls_entry.get("constructions", [])
        deps = [
            (c["depends_on"], c["name"])
            for c in constructions_schema
            if c.get("depends_on") and c.get("staleness_check") == "element_set"
        ]
        if not deps:
            continue

        for lang_id in lang_ids:
            for source_name, dep_name in deps:
                source_path = CODED_DATA / lang_id / cls_name / f"{source_name}.tsv"
                dep_path    = CODED_DATA / lang_id / cls_name / f"{dep_name}.tsv"

                if not source_path.exists() or not dep_path.exists():
                    continue

                any_checked = True
                label = f"{_lang_label(lang_id)}: {cls_name}/{source_name} → {dep_name}"

                try:
                    dep_df = pd.read_csv(dep_path, sep="\t", dtype=str, keep_default_na=False)
                except Exception as exc:
                    print(_warn(f"{label} — could not load: {exc}"))
                    total_e += 1
                    continue
                if dep_df.empty:
                    continue  # dependent not yet populated; skip

                # The rows the tab should have come from the generator itself
                # (sheet_spec.expected_row_keys -> generate_sheets.pair_rows),
                # the same builder regeneration and the Drive door use. This
                # check used to keep its own copy of each class's scope rule,
                # which went wrong whenever the generator's rule moved on
                # (#285 for coreference; 2026-10-27 for phrasal_accent, whose
                # adjacency step it never had).
                spec_tab = class_sheet_spec(lang_id, cls_name, CODED_DATA).tab(dep_name)
                want = expected_row_keys(lang_id, cls_name, spec_tab, CODED_DATA)
                if want is None:
                    print(_warn(f"{label} — not compared: an element's answer in "
                                f"{source_name} differs by position, so the generator "
                                f"won't guess which pairs this tab should have"))
                    continue
                missing_cols = [k for k in spec_tab.row_key if k not in dep_df.columns]
                if missing_cols:
                    print(_warn(f"{label} — imported TSV lacks {missing_cols}"))
                    total_e += 1
                    continue
                have = {tuple(str(r[k]).strip() for k in spec_tab.row_key)
                        for _, r in dep_df.iterrows()}
                removed = {" / ".join(k) for k in have - want}
                added   = {" / ".join(k) for k in want - have}

                # Position-number drift: independent of element-identity comparison
                # above (see _find_stale_position_cells's docstring) -- a pair-row
                # can be element-identity-correct and still reference the wrong
                # position number if the planar structure changed shape (insertion/
                # deletion) since the pair-row was last generated.
                position_names = _planar_position_names(lang_id)
                stale_cells = _find_stale_position_cells(dep_df, position_names)
                pos_remap, pos_unresolvable = _suggest_position_remap(stale_cells, position_names)

                if removed or added or pos_remap or pos_unresolvable:
                    print(_fail(label))
                    if removed:
                        preview = sorted(removed)[:5]
                        suffix = " …" if len(removed) > 5 else ""
                        print(_sub(f"pairs the source no longer calls for ({len(removed)}): {preview}{suffix}"))
                    if added:
                        preview = sorted(added)[:5]
                        suffix = " …" if len(added) > 5 else ""
                        print(_sub(f"pairs the source now calls for ({len(added)}): {preview}{suffix}"))
                    if pos_remap:
                        remap_preview = ", ".join(f"{o}→{n}" for o, n in sorted(pos_remap.items())[:5])
                        suffix = " …" if len(pos_remap) > 5 else ""
                        print(_sub(f"position number(s) stale, renumbered since last generated "
                                   f"({len(pos_remap)}): {remap_preview}{suffix}"))
                    if pos_unresolvable:
                        preview = sorted(pos_unresolvable)[:5]
                        suffix = " …" if len(pos_unresolvable) > 5 else ""
                        print(_sub(f"position number(s) stale, no matching name in current planar "
                                   f"— not fixable by --pos-remap ({len(pos_unresolvable)}): "
                                   f"{preview}{suffix}"))
                    if pos_remap and not (removed or added or pos_unresolvable):
                        remap_flags = " ".join(f"--pos-remap {o}:{n}" for o, n in sorted(pos_remap.items()))
                        print(_sub(f"→ Run: python -m coding generate-sheets --lang {lang_id} "
                                   f"--regen-construction {cls_name}:{dep_name} {remap_flags}"))
                    else:
                        print(_sub(f"→ Run: python -m coding generate-sheets --lang {lang_id} "
                                   f"--regen-construction {cls_name}:{dep_name}"
                                   + (" (add --pos-remap flags first — see above)" if pos_remap else "")))
                    total_e += 1
                else:
                    print(_ok(label))

    if not any_checked:
        print("  (no languages have dependent construction TSV pairs to check)")

    return total_e, 0


def _section_sharing() -> Tuple[int, int]:
    """Compare the live grants of every file the tooling made (found by its
    identity label) with its sharing rule (`sheet_spec.sharing_spec`).

    The Drive door checks every grant the tooling makes; this catches the
    ones made by hand in the Drive window, which pass no door. Each
    difference is an error: someone has access the rule doesn't give them,
    or lacks access it does. People are named, never shown by address.
    """
    print(_section("SHARING"))

    from .drive_door import ARCHIVED, KINDS, STATE_LABEL, Identity
    from .drive_doorway import get_doorway
    from .sheet_spec import sharing_differences, sharing_spec

    try:
        doorway = get_doorway()
        files = []
        for kind in KINDS:
            files += doorway.list_files(
                q=f"properties has {{ key='{drive_labels.KIND}' and value='{kind}' }} "
                  "and trashed=false",
                fields="files(id,name,properties)")
    except Exception as exc:
        # Drive unavailable: skip; import-sheets files an import-error issue
        # if Drive is down, so this section needn't too.
        print(f"  (could not list Drive files: {exc} — skipping)")
        return 0, 0

    errors = 0
    for f in sorted(files, key=lambda f: f["name"]):
        props = f.get("properties") or {}
        identity = Identity.from_labels(props)
        if identity is None:
            errors += 1
            print(_fail(f"{f['name']!r} carries a label that names no kind of file: {props}"))
            continue
        spec = sharing_spec(identity, archived=props.get(STATE_LABEL) == ARCHIVED)
        grants = doorway.list_permissions(
            f["id"], fields="permissions(id,type,role,emailAddress,permissionDetails)")
        differences = sharing_differences(spec, grants)
        if differences:
            errors += 1
            print(_fail(f"{f['name']} ({identity.describe()}): " + "; ".join(differences)))
    if errors:
        print(_sub("→ Change the sharing in the Drive window (Share), or, if the "
                   "access is right, change the rule in coding/sheet_spec.py (_SHARING)."))
    else:
        print(_ok(f"{len(files)} file(s) shared as their sharing rule says"))
    return errors, 0


def _section_needs_review(codebook: dict, diag_classes: dict) -> None:
    print(_section("NEEDS REVIEW / PLACEHOLDERS"))

    flagged = needs_review_entries(codebook, diag_classes)
    if flagged:
        print(_warn(f"{len(flagged)} entry(ies) waiting on review or a coordinator decision:"))
        for entry in flagged:
            print(_sub(entry))
        print(_sub("→ Edit the relevant schema file to resolve each entry."))
        print(_sub("  Promoting a module status out of [AUTO-DERIVED] requires coordinator"))
        print(_sub("  sign-off. See docs/coordinator-guide.md § 'Reviewing a span rule"))
        print(_sub("  with the domain expert'."))
    else:
        print(_ok("No [NEEDS REVIEW] or [PLACEHOLDER] entries"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding integrity-check`."""
    parser = argparse.ArgumentParser(
        prog="python -m coding integrity-check",
        description="Run a full integrity check on the planars annotation pipeline.",
    )
    parser.add_argument(
        "--lang",
        help="Restrict per-language checks to this language ID only",
    )
    parser.add_argument(
        "--sheets",
        action="store_true",
        help="Also check live Google Sheets structure (requires OAuth credentials)",
    )
    parser.add_argument(
        "--check-manifest",
        action="store_true",
        help="Fast standalone check: flag classes recorded with a sheet in the ID file "
             "(drive_config.json) but absent from the diagnostics YAML. Reads only local "
             "files; no Drive calls. Used by data-refresh (stale-manifest issue).",
    )
    parser.add_argument(
        "--check-dependents",
        action="store_true",
        help="Fast standalone check: flag dependent constructions whose element sets "
             "are out of sync with their source construction TSV. Used by data-refresh "
             "to file a dedicated dependent-stale issue.",
    )
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()

    # Discover language IDs
    if args.lang:
        lang_ids = [args.lang]
    else:
        lang_ids = sorted(
            d.name for d in CODED_DATA.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    # --check-manifest: lightweight standalone mode, no Sheet API calls.
    if args.check_manifest:
        from . import drive
        # A local file: one that can't be read is a real error, so it fails
        # the step (and its issue shows why) rather than being skipped.
        config = drive._load_drive_config()
        stale = _stale_manifest_classes(config, lang_ids)
        if stale:
            print(f"CLASS SHEETS NOT IN DIAGNOSTICS ({len(stale)}) — "
                  f"run python -m coding prune-manifest --apply to retire them:")
            for lang_id, cls in stale:
                print(f"  {_lang_label(lang_id)} · {cls}")
            sys.exit(1)
        else:
            print("No class sheets recorded for classes absent from diagnostics.")
        return

    # --check-dependents: lightweight standalone mode for dependent construction staleness.
    if args.check_dependents:
        diag_classes = _load_diagnostic_classes()
        e, _ = _section_dependent_construction_staleness(lang_ids, diag_classes)
        if e:
            sys.exit(1)
        return

    # Header
    today = date.today().isoformat()
    print("═" * _WIDTH)
    print(f"  PLANARS INTEGRITY CHECK  —  {today}")
    print("═" * _WIDTH)

    codebook    = _load_codebook()
    diag_classes = _load_diagnostic_classes()

    total_e = total_w = 0

    e, w = _section_planar(lang_ids)
    total_e += e; total_w += w

    e, w = _section_diagnostics(lang_ids)
    total_e += e; total_w += w

    e, w = _section_codebook(diag_classes)
    total_e += e; total_w += w

    e, w = _section_analysis(codebook)
    total_e += e; total_w += w

    e, w = _section_cross_sheet_consistency(lang_ids)
    total_e += e; total_w += w

    e, w = _section_dependent_construction_staleness(lang_ids, diag_classes)
    total_e += e; total_w += w

    e, w = _section_sharing()
    total_e += e; total_w += w

    if args.sheets:
        e, w = _section_sheets(lang_ids)
        total_e += e; total_w += w
    else:
        print(_section("ANNOTATION SHEETS"))
        print("  (skipped — pass --sheets to check live sheet structure)")

    _section_needs_review(codebook, diag_classes)

    # Footer
    print()
    print("═" * _WIDTH)
    if total_e:
        print(f"  ✗  {total_e} error(s)  ·  {total_w} warning(s)")
    else:
        print(f"  ✓  All checks passed  ·  {total_w} warning(s)")
    print("═" * _WIDTH)

    if total_e:
        sys.exit(1)


if __name__ == "__main__":
    main()
