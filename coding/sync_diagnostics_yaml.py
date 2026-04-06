#!/usr/bin/env python3
"""Sync between diagnostics YAML (source of truth) and diagnostics TSV/Sheet.

Usage:
    # YAML → TSV (default direction): regenerate TSV from YAML
    python -m coding sync-diagnostics-yaml                        # dry run (all languages)
    python -m coding sync-diagnostics-yaml --lang stan1293        # dry run (one language)
    python -m coding sync-diagnostics-yaml --apply                # write TSVs

    # YAML → Google Sheet: push YAML changes back to the diagnostics Sheet
    python -m coding sync-diagnostics-yaml --to-sheet             # dry run (all languages)
    python -m coding sync-diagnostics-yaml --to-sheet --apply     # upload to Sheet
    python -m coding sync-diagnostics-yaml --to-sheet --lang stan1293

    # TSV → YAML: propose changes from TSV back to YAML
    python -m coding sync-diagnostics-yaml --from-tsv             # dry run (all languages)
    python -m coding sync-diagnostics-yaml --from-tsv --apply     # write YAML updates
    python -m coding sync-diagnostics-yaml --from-tsv --lang stan1293

YAML is the authoritative source of truth; TSV is a derived artifact.

YAML → TSV (default):
    The TSV is always generated fresh from the YAML. Direct edits to the TSV
    are overwritten. To change diagnostics, edit the YAML and run --apply.

YAML → Sheet (--to-sheet):
    Reads the YAML, generates the TSV representation, and uploads it to the
    diagnostics Google Sheet (overwriting stale content). Requires Drive access.
    Run this after renaming classes or criteria in the YAML so the Sheet stays
    in sync and import-sheets no longer detects false drift.

TSV → YAML (--from-tsv):
    Diffs the TSV against the YAML and categorises changes:
    - Deterministic (auto-applied): class_added, construction_added/removed,
      criterion_added/removed, criterion_values_changed — all against known
      schema entries in diagnostic_classes.yaml / diagnostic_criteria.yaml.
    - Ambiguous (flagged for review): unknown classes or criteria not in the
      schema; class removals (may be intentional retirements).
    Deterministic changes are applied to the YAML automatically when --apply
    is given. Ambiguous changes are printed and written to
    diagnostics_drift.json for coordinator review.

Each language must have a diagnostics_{lang_id}.yaml in its planar_input/
folder to participate. Languages without YAML are skipped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"


from .make_forms import (
    _resolve_diagnostics_yaml_path,
    _yaml_to_tsv_df,
    _tsv_df_to_yaml,
    _dump_diagnostics_yaml,
    _diff_diagnostics_tsv_yaml,
    _apply_yaml_diff,
)
from .validate_diagnostics import validate_diagnostics_yaml


def _discover_languages() -> List[str]:
    """Return language IDs that have a diagnostics YAML in coded_data/."""
    langs = []
    for yaml_path in sorted(CODED_DATA.glob("*/planar_input/diagnostics_*.yaml")):
        lang_id = yaml_path.stem.replace("diagnostics_", "", 1)
        langs.append(lang_id)
    return langs


def _sync_to_tsv(lang_id: str, apply: bool) -> bool:
    """Sync YAML → TSV for one language. Returns True if changes were made (or would be)."""
    planar_dir = CODED_DATA / lang_id / "planar_input"
    yaml_path  = planar_dir / f"diagnostics_{lang_id}.yaml"
    tsv_path   = planar_dir / f"diagnostics_{lang_id}.tsv"

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    issues = validate_diagnostics_yaml(yaml_data, lang_id)
    errors   = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    for w in warnings:
        print(f"  [{lang_id}] WARNING {w.location}: {w.message}")
    if errors:
        for e in errors:
            print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
        print(f"  [{lang_id}] Skipping — fix errors above before applying.")
        return False

    new_df = _yaml_to_tsv_df(yaml_data, lang_id)
    new_content = new_df.to_csv(sep="\t", index=False)

    if tsv_path.exists():
        old_content = tsv_path.read_text(encoding="utf-8")
        if old_content == new_content:
            print(f"  [{lang_id}] TSV already up to date")
            return False
        action = "Updated" if apply else "Would update"
    else:
        action = "Created" if apply else "Would create"

    print(f"  [{lang_id}] {action} → {tsv_path.name}")
    if apply:
        tsv_path.write_text(new_content, encoding="utf-8")
    return True


def _sync_from_tsv(lang_id: str, apply: bool, drift_entries: List[Dict]) -> bool:
    """Sync TSV → YAML for one language. Returns True if the YAML was (or would be) changed.

    Deterministic changes are auto-applied; ambiguous changes are appended to
    drift_entries for the caller to write to diagnostics_drift.json.
    """
    planar_dir = CODED_DATA / lang_id / "planar_input"
    yaml_path  = planar_dir / f"diagnostics_{lang_id}.yaml"
    tsv_path   = planar_dir / f"diagnostics_{lang_id}.tsv"

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping (cannot propose to non-existent YAML)")
        return False

    if not tsv_path.exists():
        print(f"  [{lang_id}] No TSV found — nothing to diff")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    tsv_df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)

    deterministic, ambiguous = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, lang_id)

    if not deterministic and not ambiguous:
        print(f"  [{lang_id}] No differences found")
        return False

    if deterministic:
        kinds = [c["kind"] for c in deterministic]
        print(f"  [{lang_id}] Deterministic changes ({len(deterministic)}): {', '.join(kinds)}")
        if apply:
            new_yaml = _apply_yaml_diff(yaml_data, deterministic)
            yaml_path.write_text(_dump_diagnostics_yaml(new_yaml), encoding="utf-8")
            print(f"  [{lang_id}] YAML updated.")
        else:
            print(f"  [{lang_id}] (dry run — use --apply to write)")

    if ambiguous:
        print(f"  [{lang_id}] Ambiguous changes ({len(ambiguous)}) — flagged for review:")
        for change in ambiguous:
            kind = change["kind"]
            class_name = change["class_name"]
            suggestions = change.get("suggestions", [])
            hint = f" (suggestions: {suggestions})" if suggestions else ""
            print(f"    {kind}: {class_name}{hint}")
        drift_entries.append({"lang_id": lang_id, "ambiguous": ambiguous})

    return bool(deterministic)


def _sync_to_sheet(lang_id: str, gc, manifest: dict, apply: bool) -> bool:
    """Sync YAML → Google Sheet for one language.

    Reads the YAML, generates the TSV representation, compares it against the
    live diagnostics Sheet, and optionally overwrites it. This is the upload
    direction — the mirror of import-sheets downloading the diagnostics Sheet.

    Use this when YAML class names or criteria have changed locally and the
    Google Sheet is stale. Running this in data-refresh after sync-diagnostics-yaml
    --apply keeps the Sheet in continuous sync with the YAML.

    Returns True if changes were made (or would be).
    """
    from .drive import _open_spreadsheet, _with_retry

    lang_data = manifest.get(lang_id, {})
    diag_id = lang_data.get("diagnostics_spreadsheet_id")
    if not diag_id:
        print(f"  [{lang_id}] No diagnostics_spreadsheet_id in manifest — skipping")
        return False

    planar_dir = CODED_DATA / lang_id / "planar_input"
    yaml_path = planar_dir / f"diagnostics_{lang_id}.yaml"

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    issues = validate_diagnostics_yaml(yaml_data, lang_id)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        for e in errors:
            print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
        print(f"  [{lang_id}] Skipping — fix errors above before uploading.")
        return False

    new_df = _yaml_to_tsv_df(yaml_data, lang_id)

    try:
        ss = _open_spreadsheet(gc, diag_id)
        current_rows = _with_retry(ss.sheet1.get_all_values)
    except Exception as e:
        print(f"  [{lang_id}] Could not read Sheet: {e}")
        return False

    if current_rows:
        current_df = pd.DataFrame(
            current_rows[1:], columns=current_rows[0], dtype=str
        ).fillna("")
        if current_df.reset_index(drop=True).equals(new_df.reset_index(drop=True)):
            print(f"  [{lang_id}] Sheet already up to date")
            return False
        # Show row-level diff so coordinator can review before applying.
        current_classes = set(current_df.get("Class", pd.Series(dtype=str)).tolist())
        new_classes = set(new_df.get("Class", pd.Series(dtype=str)).tolist())
        for c in sorted(current_classes - new_classes):
            print(f"  [{lang_id}]   - removed: {c}")
        for c in sorted(new_classes - current_classes):
            print(f"  [{lang_id}]   + added:   {c}")
        for c in sorted(current_classes & new_classes):
            old_row = current_df[current_df["Class"] == c].iloc[0].to_dict()
            new_row = new_df[new_df["Class"] == c].iloc[0].to_dict()
            if old_row != new_row:
                print(f"  [{lang_id}]   ~ changed: {c}")
    else:
        print(f"  [{lang_id}]   (sheet is empty — will populate from YAML)")

    if apply:
        new_rows = [list(new_df.columns)] + [list(row) for _, row in new_df.iterrows()]
        ss.sheet1.clear()
        ss.sheet1.update(new_rows, "A1")
        print(f"  [{lang_id}] Updated → diagnostics Sheet")
    else:
        print(f"  [{lang_id}] Would update → diagnostics Sheet (use --apply to write)")

    return True


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    from_tsv = "--from-tsv" in args
    to_sheet = "--to-sheet" in args
    lang_filter: Optional[str] = None

    if "--lang" in args:
        idx = args.index("--lang")
        if idx + 1 >= len(args):
            print("ERROR: --lang requires a language ID argument")
            sys.exit(1)
        lang_filter = args[idx + 1]

    if not apply:
        print("Dry run — use --apply to write changes.\n")

    if to_sheet:
        # Upload direction requires Google API access.
        from .drive import _get_clients, _load_manifest_from_drive
        print("Connecting to Google APIs...")
        gc, drive = _get_clients()
        manifest = _load_manifest_from_drive(drive)
        if not manifest:
            raise SystemExit("No manifest found. Run generate-sheets first.")
        languages = [lang_filter] if lang_filter else list(manifest.keys())
        changed = 0
        for lang_id in sorted(languages):
            changed += _sync_to_sheet(lang_id, gc, manifest, apply)
        print()
        if apply:
            print(f"Done: {changed} Sheet(s) updated.")
        else:
            print(f"Dry run complete: {changed} Sheet(s) would be updated.")
        return

    languages = [lang_filter] if lang_filter else _discover_languages()

    if not languages:
        print("No languages with diagnostics YAML found.")
        sys.exit(0)

    changed = 0
    if from_tsv:
        drift_entries: List[Dict] = []
        for lang_id in languages:
            changed += _sync_from_tsv(lang_id, apply, drift_entries)
        if drift_entries:
            drift_path = ROOT / "diagnostics_drift.json"
            print(f"\nAmbiguous changes written to {drift_path.name} for coordinator review.")
            if apply:
                drift_path.write_text(
                    json.dumps(drift_entries, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
    else:
        for lang_id in languages:
            changed += _sync_to_tsv(lang_id, apply)

    print()
    direction = "YAML" if from_tsv else "TSV"
    if apply:
        print(f"Done: {changed} {direction} file(s) updated.")
    else:
        print(f"Dry run complete: {changed} {direction} file(s) would be updated.")
