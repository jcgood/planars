#!/usr/bin/env python3
"""Sync between diagnostics YAML (source of truth) and diagnostics TSV (derived artifact).

Usage:
    # YAML → TSV (default direction): regenerate TSV from YAML
    python -m coding sync-diagnostics-yaml                        # dry run (all languages)
    python -m coding sync-diagnostics-yaml --lang stan1293        # dry run (one language)
    python -m coding sync-diagnostics-yaml --apply                # write TSVs

    # TSV → YAML: propose changes from TSV back to YAML
    python -m coding sync-diagnostics-yaml --from-tsv             # dry run (all languages)
    python -m coding sync-diagnostics-yaml --from-tsv --apply     # write YAML updates
    python -m coding sync-diagnostics-yaml --from-tsv --lang stan1293

YAML is the authoritative source of truth; TSV is a derived artifact.

YAML → TSV (--to-tsv, the default):
    The TSV is always generated fresh from the YAML. Direct edits to the TSV
    are overwritten. To change diagnostics, edit the YAML and run --apply.

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
    DATA_DIR,
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
    errors   = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

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


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    from_tsv = "--from-tsv" in args
    lang_filter: Optional[str] = None

    if "--lang" in args:
        idx = args.index("--lang")
        if idx + 1 >= len(args):
            print("ERROR: --lang requires a language ID argument")
            sys.exit(1)
        lang_filter = args[idx + 1]

    if not apply:
        print("Dry run — use --apply to write changes.\n")

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
