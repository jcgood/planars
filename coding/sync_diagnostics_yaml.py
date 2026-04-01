#!/usr/bin/env python3
"""Sync between diagnostics YAML (source of truth) and diagnostics TSV (derived artifact).

Phase 2 — YAML → TSV direction only.
Phase 3 will add --from-tsv (TSV → YAML) for round-tripping collaborator changes.

Usage:
    python -m coding sync-diagnostics-yaml                        # dry run (all languages)
    python -m coding sync-diagnostics-yaml --lang stan1293        # dry run (one language)
    python -m coding sync-diagnostics-yaml --apply                # write TSVs
    python -m coding sync-diagnostics-yaml --apply --lang arao1248

The TSV is always generated fresh from the YAML — any direct edits to the TSV
will be overwritten.  To propose changes, edit the YAML and run with --apply.

Each language must have a diagnostics_{lang_id}.yaml in its planar_input/ folder.
Languages with no YAML are skipped (they still use the TSV directly).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"


from .make_forms import (
    _resolve_diagnostics_yaml_path,
    _yaml_to_tsv_df,
    _dump_diagnostics_yaml,
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


def _sync_one(lang_id: str, apply: bool) -> bool:
    """Sync YAML → TSV for one language. Returns True if changes were made (or would be)."""
    # Resolve paths relative to the language's planar_input folder
    planar_dir = CODED_DATA / lang_id / "planar_input"
    yaml_path  = planar_dir / f"diagnostics_{lang_id}.yaml"
    tsv_path   = planar_dir / f"diagnostics_{lang_id}.tsv"

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    # Validate before generating
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


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
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
    for lang_id in languages:
        changed += _sync_one(lang_id, apply)

    print()
    if apply:
        print(f"Done: {changed} TSV(s) updated.")
    else:
        print(f"Dry run complete: {changed} TSV(s) would be updated.")
