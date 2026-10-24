#!/usr/bin/env python3
"""Sync between diagnostics YAML (source of truth) and diagnostics TSV/Sheet.

Usage:
    # YAML → TSV (default direction): regenerate TSV from YAML
    python -m coding sync-diagnostics-yaml                        # dry run (all languages)
    python -m coding sync-diagnostics-yaml --lang stan1293        # dry run (one language)
    python -m coding sync-diagnostics-yaml --apply                # write TSVs

    # YAML → Google Sheet: bring the diagnostics Sheet up to date
    python -m coding sync-diagnostics-yaml --to-sheet             # dry run (all languages)
    python -m coding sync-diagnostics-yaml --to-sheet --apply     # upload to Sheet
    python -m coding sync-diagnostics-yaml --to-sheet --lang stan1293

The YAML is the diagnostics' one editable home; the TSV and the Sheet are
copies made from it, and nothing is read back from either (Phase 10 unit 11b).
The coordinator edits the YAML (by hand, or with ``accept-proposal`` from the
language's proposal sheet).

YAML → TSV (default):
    The TSV is always generated fresh from the YAML. Direct edits to the TSV
    are overwritten.

YAML → Sheet (--to-sheet):
    Renders the YAML as rows and writes them to the diagnostics Sheet, a
    read-only copy for the annotator, if they differ (daily in the refresh).

Each language must have a diagnostics_{lang_id}.yaml in its lang_setup/
folder to participate. Languages without YAML are skipped.

Exit status: both directions exit non-zero when any language has a blocking
validation error (the daily refresh files a `diagnostics-yaml-error` issue on
that). Only blocking errors stop a language; a non-blocking one (e.g. a
required class not yet drafted) does not withhold the sync.

`coded_data_clean_tree` (for `.yaml` and `.tsv`) is enforced centrally by
preconditions.py before an `--apply` run reads coded_data/.

The TSV is written through the local-file door (coding/file_door.py), which
keeps the previous version in archive/lang_setup/, logs the change in the
language's changes.tsv, and commits it in planars-data when the command ends.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"


from .make_forms import _yaml_to_tsv_df
from .validate_diagnostics import validate_diagnostics_yaml
from . import file_door


def _discover_languages() -> List[str]:
    """Return language IDs that have a diagnostics YAML in coded_data/."""
    langs = []
    for yaml_path in sorted(CODED_DATA.glob("*/lang_setup/diagnostics_*.yaml")):
        lang_id = yaml_path.stem.replace("diagnostics_", "", 1)
        langs.append(lang_id)
    return langs


def _sync_to_tsv(lang_id: str, apply: bool, error_langs: List[str]) -> bool:
    """Sync YAML → TSV for one language. Returns True if changes were made (or would be).

    A language whose YAML fails validation is appended to error_langs rather
    than only being skipped locally — main() exits non-zero if it's
    non-empty, so a blocking error here reaches the daily automation's exit
    code instead of only ever appearing in a log nobody reads (issue #283).
    """
    yaml_path  = file_door.diagnostics_yaml(lang_id).path
    tsv_path   = file_door.diagnostics_tsv(lang_id).path

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    issues = validate_diagnostics_yaml(yaml_data, lang_id)
    errors   = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    blocking_errors = [e for e in errors if e.blocking]

    for w in warnings:
        print(f"  [{lang_id}] WARNING {w.location}: {w.message}")
    for e in errors:
        print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
    if blocking_errors:
        print(f"  [{lang_id}] Skipping — fix errors above before applying.")
        error_langs.append(lang_id)
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
        file_door.write(file_door.diagnostics_tsv(lang_id), new_content,
                        why="regenerated from the diagnostics file")
    return True


def _describe_changes(current_df: pd.DataFrame, new_df: pd.DataFrame) -> List[str]:
    """Say what would move if the Sheet were overwritten from the YAML.

    This is the only look the coordinator gets before a sheet is replaced, so
    it has to name everything that is about to change.

    Most classes occupy one row. Some occupy one row per construction, because
    their constructions ask different questions and so declare different
    criteria — `segmental` splits into `aspiration_prominence` and `flapping`,
    `phrasal_accent` into `prescreening` and `general`. For those, comparing
    one row per class is not enough: until 2026-08-02 this compared each
    class's *first* row only, so an edit to `segmental / flapping` was uploaded
    and never mentioned, and deleting a whole row of a two-row class printed
    nothing at all. See docs/data-layer-progress.md, finding 5.

    So a class with one row on each side is still reported by class name — that
    was right, and naming its construction list would only add noise. A class
    with several rows is reported per construction.
    """
    def classes(df: pd.DataFrame) -> set:
        return set(df.get("Class", pd.Series(dtype=str)).tolist())

    def rows_of(df: pd.DataFrame, class_name: str) -> List[Dict]:
        return [r.to_dict() for _, r in df[df["Class"] == class_name].iterrows()]

    def by_construction(rows: List[Dict]) -> Dict[str, Dict]:
        return {row["Constructions"]: row for row in rows}

    # A sheet whose header is wrong enough to be missing this column still gets
    # a report, one line per class, rather than an exception.
    per_construction = ("Constructions" in current_df.columns
                        and "Constructions" in new_df.columns)

    current_classes, new_classes = classes(current_df), classes(new_df)
    lines = [f"- removed: {c}" for c in sorted(current_classes - new_classes)]
    lines += [f"+ added:   {c}" for c in sorted(new_classes - current_classes)]

    for c in sorted(current_classes & new_classes):
        old_rows, new_rows = rows_of(current_df, c), rows_of(new_df, c)
        if not per_construction or (len(old_rows) == 1 and len(new_rows) == 1):
            if old_rows != new_rows:
                lines.append(f"~ changed: {c}")
            continue
        old_by, new_by = by_construction(old_rows), by_construction(new_rows)
        for k in sorted(set(old_by) - set(new_by)):
            lines.append(f"- removed: {c} / {k}")
        for k in sorted(set(new_by) - set(old_by)):
            lines.append(f"+ added:   {c} / {k}")
        for k in sorted(set(old_by) & set(new_by)):
            if old_by[k] != new_by[k]:
                lines.append(f"~ changed: {c} / {k}")
    return lines


def _sync_to_sheet(lang_id: str, manifest: dict, apply: bool, error_langs: List[str]) -> bool:
    """Sync YAML → Google Sheet for one language.

    Renders the YAML as rows, compares them with the diagnostics Sheet, and
    with ``apply`` rewrites the Sheet if they differ. The Sheet is the
    tooling's (annotators read it), so nothing on it is lost.

    Returns True if changes were made (or would be). A language whose YAML
    fails validation is appended to error_langs — same reasoning as
    _sync_to_tsv above (issue #283): this direction had the identical gap,
    found and fixed alongside it rather than left for a second pass.
    """
    from .drive_doorway import get_doorway

    lang_data = manifest.get(lang_id, {})
    diag_id = lang_data.get("diagnostics_spreadsheet_id")
    if not diag_id:
        print(f"  [{lang_id}] No diagnostics_spreadsheet_id in manifest — skipping")
        return False

    planar_dir = CODED_DATA / lang_id / "lang_setup"
    yaml_path = planar_dir / f"diagnostics_{lang_id}.yaml"

    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return False

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    issues = validate_diagnostics_yaml(yaml_data, lang_id)
    errors = [i for i in issues if i.level == "error"]
    # Gate on blocking errors only, matching _sync_to_tsv above -- this used
    # to gate on every error regardless of .blocking, which meant a
    # non-blocking one (e.g. "required class not yet drafted", blocking=False
    # by design -- see ValidationIssue's docstring) silently withheld the
    # Sheet push it was explicitly designed not to withhold. Harmless while
    # errors were invisible either way; found fixing issue #283, since wiring
    # up an exit code on top of the old logic would have turned a known,
    # already-tracked gap (arao1248's proform class, issue #279) into a false
    # alarm on every daily run.
    blocking_errors = [e for e in errors if e.blocking]
    for e in errors:
        print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
    if blocking_errors:
        print(f"  [{lang_id}] Skipping — fix errors above before uploading.")
        error_langs.append(lang_id)
        return False

    new_df = _yaml_to_tsv_df(yaml_data, lang_id)

    try:
        ss = get_doorway().open_spreadsheet(diag_id)
        current_rows = ss.sheet1.get_all_values()
    except Exception as e:
        print(f"  [{lang_id}] Could not read Sheet: {e}")
        return False

    # Read-only for everyone but its owner, coordinators included (they are
    # writers on the root folder); checked every run.
    from .locked_tabs import protect
    if protect(ss, ss.sheet1, apply):
        print(f"  [{lang_id}] {'Protected' if apply else 'Would protect'} the diagnostics Sheet")

    if current_rows:
        current_df = pd.DataFrame(
            current_rows[1:], columns=current_rows[0], dtype=str
        ).fillna("")
        if current_df.reset_index(drop=True).equals(new_df.reset_index(drop=True)):
            print(f"  [{lang_id}] Sheet already up to date")
            return False
        for line in _describe_changes(current_df, new_df):
            print(f"  [{lang_id}]   {line}")
    else:
        print(f"  [{lang_id}]   (sheet is empty — will populate from YAML)")

    if apply:
        new_rows = [list(new_df.columns)] + [list(row) for _, row in new_df.iterrows()]
        ws = ss.sheet1
        ws.clear()
        ws.update(new_rows, "A1")
        print(f"  [{lang_id}] Updated → diagnostics Sheet")
    else:
        print(f"  [{lang_id}] Would update → diagnostics Sheet")

    return True


def _apply_command(to_sheet: bool, lang_filter: Optional[str]) -> str:
    """This same run, with --apply — the exact line to copy after a dry run.

    Built from the flags actually passed rather than named as "--apply", so
    nobody has to reassemble the invocation they just made from memory.
    """
    parts = ["python -m coding sync-diagnostics-yaml"]
    if to_sheet:
        parts.append("--to-sheet")
    if lang_filter:
        parts.append(f"--lang {lang_filter}")
    parts.append("--apply")
    return " ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding sync-diagnostics-yaml`."""
    ap = argparse.ArgumentParser(
        description="Copy each diagnostics YAML to its TSV, or to its Sheet."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
    )
    ap.add_argument(
        "--to-sheet", action="store_true",
        help="push YAML to the live diagnostics Sheet instead of the local TSV",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    to_sheet = args.to_sheet
    lang_filter: Optional[str] = args.lang

    # coded_data_clean_tree is enforced centrally at the command dispatch
    # chokepoint (coding/preconditions.py), not here: a prior step's failed
    # commit could leave a stale YAML on disk for this command to copy.
    run_line = _apply_command(to_sheet, lang_filter)
    if not apply:
        print("Dry run — nothing is written.\n")

    if to_sheet:
        # Upload direction requires Google API access.
        from .drive import load_manifest
        from .drive_doorway import get_doorway
        print("Connecting to Google APIs...")
        manifest = load_manifest(get_doorway())
        if not manifest:
            raise SystemExit("No manifest found. Run python -m coding generate-sheets --apply first.")
        languages = [lang_filter] if lang_filter else list(manifest.keys())
        changed = 0
        error_langs: List[str] = []
        for lang_id in sorted(languages):
            changed += _sync_to_sheet(lang_id, manifest, apply, error_langs)
        print()
        if apply:
            print(f"Done: {changed} Sheet(s) updated.")
        else:
            print(f"Dry run complete: {changed} Sheet(s) would be updated.")
            if changed:
                print(f"  → run: {run_line}")
        if error_langs:
            print(f"\n{len(error_langs)} language(s) had blocking validation errors: "
                  f"{', '.join(sorted(error_langs))}")
            sys.exit(1)
        return

    languages = [lang_filter] if lang_filter else _discover_languages()

    if not languages:
        print("No languages with diagnostics YAML found.")
        sys.exit(0)

    changed = 0
    error_langs: List[str] = []
    for lang_id in languages:
        changed += _sync_to_tsv(lang_id, apply, error_langs)

    print()
    if apply:
        print(f"Done: {changed} TSV file(s) updated.")
    else:
        print(f"Dry run complete: {changed} TSV file(s) would be updated.")
        if changed:
            print(f"  → run: {run_line}")
    if error_langs:
        print(f"\n{len(error_langs)} language(s) had blocking validation errors: "
              f"{', '.join(sorted(error_langs))}")
        sys.exit(1)
