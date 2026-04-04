#!/usr/bin/env python3
"""Project-wide integrity check for the planars annotation pipeline.

Runs six sections of checks and prints a structured report:

  PLANAR STRUCTURE       — validates planar_*.tsv for each language
  DIAGNOSTICS            — validates diagnostics_*.tsv for each language
  CODEBOOK CONSISTENCY   — cross-checks diagnostics TSVs against schema files
  ANALYSIS CONSISTENCY   — validates analysis modules match diagnostic_criteria.yaml
  ANNOTATION SHEETS      — checks live sheet structure (requires --sheets)
  NEEDS REVIEW           — surfaces [NEEDS REVIEW] / [PLACEHOLDER] markers

Exit code 0 if no errors; 1 if any errors (warnings do not fail).

Usage:
    python -m coding integrity-check
    python -m coding integrity-check --lang arao1248
    python -m coding integrity-check --sheets
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

from .validate import ValidationIssue
from .validate_planar import validate_planar_df
from .validate_diagnostics import validate_diagnostics_df
from .check_codebook import (
    _load_codebook,
    _load_diagnostic_classes,
    _check_required_criteria,
    _check_diagnostics_vs_classes,
    _check_chart_keys,
)
from .schemas import load_planar_schema
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
        planar_dir = CODED_DATA / lang_id / "planar_input"
        lang = _lang_label(lang_id)

        if not planar_dir.exists():
            print(_fail(f"{lang}  —  no planar_input/ directory"))
            total_e += 1
            continue

        planar_files = sorted(planar_dir.glob("planar_*.tsv"))
        if not planar_files:
            print(_fail(f"{lang}  —  no planar_*.tsv found"))
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

    return total_e, total_w


def _section_diagnostics(lang_ids: List[str]) -> Tuple[int, int]:
    print(_section("DIAGNOSTICS"))
    total_e = total_w = 0

    for lang_id in lang_ids:
        diag_path = CODED_DATA / lang_id / "planar_input" / f"diagnostics_{lang_id}.tsv"
        lang = _lang_label(lang_id)

        if not diag_path.exists():
            print(_fail(f"{lang}  —  diagnostics_{lang_id}.tsv not found"))
            total_e += 1
            continue

        try:
            df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
        except Exception as exc:
            print(_fail(f"{lang}  —  could not read diagnostics file: {exc}"))
            total_e += 1
            continue

        issues = validate_diagnostics_df(df, lang_id)
        label = f"{lang:<34}  diagnostics_{lang_id}.tsv"
        e, w = _print_issues(issues, label)
        total_e += e
        total_w += w

    return total_e, total_w


def _section_codebook(diag_classes: dict) -> Tuple[int, int]:
    print(_section("CODEBOOK CONSISTENCY"))

    errs_classes = _check_diagnostics_vs_classes(diag_classes)

    if errs_classes:
        print(_fail("diagnostics TSVs vs. diagnostic_classes.yaml"))
        for e in errs_classes:
            print(_sub(e))
    else:
        print(_ok("diagnostics TSVs match diagnostic_classes.yaml"))

    return len(errs_classes), 0


def _section_analysis(codebook: dict) -> Tuple[int, int]:
    print(_section("ANALYSIS CONSISTENCY"))

    errs_req  = _check_required_criteria(codebook)
    errs_keys = _check_chart_keys()

    if errs_req:
        print(_fail("Module _REQUIRED_CRITERIA vs. diagnostic_criteria.yaml"))
        for e in errs_req:
            print(_sub(e))
    else:
        print(_ok("Module _REQUIRED_CRITERIA all defined in diagnostic_criteria.yaml"))

    if errs_keys:
        print(_fail("Chart span keys vs. derive function result dicts"))
        for e in errs_keys:
            print(_sub(e))
    else:
        print(_ok("All chart span keys match derive function result dicts"))

    return len(errs_req) + len(errs_keys), 0


def _stale_manifest_classes(manifest: dict, lang_ids: List[str]) -> List[Tuple[str, str]]:
    """Return (lang_id, class_name) pairs that are in the manifest but absent from diagnostics.

    Reads local diagnostics_{lang}.yaml (or .tsv fallback) — no Sheet API calls.
    """
    stale = []
    for lang_id in lang_ids:
        sheets_info = manifest.get(lang_id, {}).get("sheets", {})
        if not sheets_info:
            continue
        yaml_path = CODED_DATA / lang_id / "planar_input" / f"diagnostics_{lang_id}.yaml"
        tsv_path  = CODED_DATA / lang_id / "planar_input" / f"diagnostics_{lang_id}.tsv"
        if yaml_path.exists():
            with open(yaml_path, encoding="utf-8") as _f:
                _diag = _yaml.safe_load(_f)
            active = set((_diag or {}).get("classes", {}).keys())
        elif tsv_path.exists():
            _df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
            active = set(_df["Class"].unique()) if "Class" in _df.columns else set()
        else:
            continue
        for cls in sorted(set(sheets_info.keys()) - active):
            stale.append((lang_id, cls))
    return stale


def _section_sheets(lang_ids: List[str]) -> Tuple[int, int]:
    print(_section("ANNOTATION SHEETS"))

    try:
        from .drive import _get_clients, _load_manifest_from_drive, _with_retry
    except ImportError as exc:
        print(_warn(f"Could not import sheet utilities: {exc}"))
        return 0, 1

    try:
        gc, drive_svc = _get_clients()
        manifest = _load_manifest_from_drive(drive_svc)
    except Exception as exc:
        print(_fail(f"Could not connect to Google Sheets: {exc}"))
        return 1, 0

    _STRUCTURAL = {"Element", "Position_Name", "Position_Number"}
    _TRAILING   = set(load_planar_schema().get("trailing_columns", ["Source", "Comments"]))

    total_e = total_w = 0

    for lang_id in lang_ids:
        lang = _lang_label(lang_id)
        lang_data = manifest.get(lang_id)

        if not lang_data:
            print(_warn(f"{lang}  —  not in Drive manifest"))
            total_w += 1
            continue

        # Check project metadata completeness against languages.yaml (source of truth).
        lang_entry = _LANGUAGES.get(lang_id, {})
        meta = lang_entry.get("meta", {})
        _KEY_META = tuple(_LANGUAGES.get("required_meta_fields", ["source", "author"]))
        missing_meta = [f for f in _KEY_META if not meta.get(f)]
        if not lang_entry:
            print(_warn(f"{lang}  —  not in schemas/languages.yaml (run lookup-lang to add)"))
            total_w += 1
        elif not meta:
            print(_warn(f"{lang}  —  meta block missing from languages.yaml (run lookup-lang to scaffold)"))
            total_w += 1
        elif missing_meta:
            print(_warn(f"{lang}  —  languages.yaml meta incomplete: {', '.join(missing_meta)} not set"))
            total_w += 1

        sheets_info = lang_data.get("sheets", {})
        if not sheets_info:
            print(_warn(f"{lang}  —  no sheets in manifest"))
            total_w += 1
            continue

        # Check for stale manifest entries via shared helper (no Sheet API calls).
        for _, stale_cls in _stale_manifest_classes(manifest, [lang_id]):
            print(_warn(f"{lang} · {stale_cls}  —  in manifest but not in diagnostics — run prune-manifest"))
            total_w += 1

        for class_name, sheet_info in sorted(sheets_info.items()):
            try:
                ss = _with_retry(lambda: gc.open_by_key(sheet_info["spreadsheet_id"]))
            except Exception as exc:
                print(_fail(f"{lang} · {class_name}  —  could not open spreadsheet: {exc}"))
                total_e += 1
                continue

            try:
                tab_titles = {ws.title for ws in _with_retry(lambda: ss.worksheets())}
            except Exception as exc:
                print(_fail(f"{lang} · {class_name}  —  could not list worksheets: {exc}"))
                total_e += 1
                continue
            construction_params = sheet_info.get("construction_params", {})

            for construction in sheet_info.get("constructions", []):
                label = f"{lang} · {class_name} · {construction}"

                if construction not in tab_titles:
                    print(_fail(f"{label}  —  tab missing from spreadsheet"))
                    total_e += 1
                    continue

                try:
                    ws     = _with_retry(lambda: ss.worksheet(construction))
                    header = _with_retry(lambda: ws.row_values(1))
                except Exception as exc:
                    print(_fail(f"{label}  —  could not read header: {exc}"))
                    total_e += 1
                    continue

                expected = construction_params.get(construction, {}).get("param_names", [])
                actual   = [c for c in header if c not in _STRUCTURAL and c not in _TRAILING]

                # Warn on stale lifecycle columns left from --split or --merge operations.
                stale = [c for c in actual if c.startswith("_split_") or c.startswith("_merged_")]
                if stale:
                    print(_warn(label))
                    for col in stale:
                        prefix = "_split_" if col.startswith("_split_") else "_merged_"
                        op = "split" if prefix == "_split_" else "merge"
                        print(_sub(f"stale {op} column '{col}' — remap values then remove manually"))
                    total_w += 1
                elif actual != expected:
                    print(_warn(label))
                    print(_sub(f"expected criteria columns: {expected}"))
                    print(_sub(f"actual criteria columns:   {actual}"))
                    total_w += 1
                else:
                    print(_ok(label))

    return total_e, total_w


def _section_needs_review(codebook: dict, diag_classes: dict) -> None:
    print(_section("NEEDS REVIEW / PLACEHOLDERS"))

    flagged = []
    for analysis in codebook.get("analyses", []):
        name = analysis["name"]
        for field in ("description", "qualification_rule"):
            text = analysis.get(field, "")
            if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                flagged.append(f"diagnostic_criteria.yaml [{name}]: {field}")
                break
        for crit in analysis.get("diagnostic_criteria", []):
            for field in ("description",):
                text = crit.get(field, "")
                if "[NEEDS REVIEW]" in text or "[PLACEHOLDER]" in text:
                    flagged.append(f"diagnostic_criteria.yaml [{name}/{crit['name']}]: {field}")
                    break

    for cls in diag_classes.values():
        status = str(cls.get("status", ""))
        if "[NEEDS REVIEW]" in status or "[PLACEHOLDER]" in status:
            flagged.append(f"diagnostic_classes.yaml [{cls['name']}]: status")

    if flagged:
        print(_warn(f"{len(flagged)} entry(ies) marked [NEEDS REVIEW] or [PLACEHOLDER]:"))
        for entry in flagged:
            print(_sub(entry))
    else:
        print(_ok("No [NEEDS REVIEW] or [PLACEHOLDER] entries"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
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
        help="Fast standalone check: flag manifest classes absent from diagnostics YAML. "
             "Requires Drive access but makes no Sheet API calls. Used by data-refresh.",
    )
    args = parser.parse_args()

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
        from .drive import _get_clients, _load_manifest_from_drive
        try:
            _, drive_svc = _get_clients()
            manifest = _load_manifest_from_drive(drive_svc)
        except Exception as exc:
            # Drive unavailable — skip silently rather than filing a misleading
            # stale-manifest issue. import-sheets will file an import-error issue
            # if Drive is genuinely down.
            print(f"WARNING: Could not load manifest ({exc}) — skipping stale manifest check.")
            return
        stale = _stale_manifest_classes(manifest, lang_ids)
        if stale:
            print(f"STALE MANIFEST ENTRIES ({len(stale)}) — run prune-manifest --apply to clean up:")
            for lang_id, cls in stale:
                print(f"  {_lang_label(lang_id)} · {cls}")
            sys.exit(1)
        else:
            print("No stale manifest entries.")
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
