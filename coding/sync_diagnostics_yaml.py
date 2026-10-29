#!/usr/bin/env python3
"""Bring each language's diagnostics Sheet up to date with its diagnostics YAML.

Usage:
    python -m coding sync-diagnostics-yaml                        # dry run (all languages)
    python -m coding sync-diagnostics-yaml --lang stan1293        # dry run (one language)
    python -m coding sync-diagnostics-yaml --apply                # update the Sheets

The YAML is the diagnostics' one home; the Sheet is a read-only copy made
from it for the annotator, and nothing is read back from it (Phase 10 unit
11b). The coordinator edits the YAML (by hand, or with ``accept-proposal``
from the language's proposal sheet). Until 2026-10-27 the command also
wrote a ``diagnostics_{lang_id}.tsv`` copy beside the YAML, and the Sheet
direction was ``--to-sheet``; the TSV was deleted (ownership-design Q5) and
its readers read the YAML through ``make_forms._read_diagnostics_for_language``.

Every language with a YAML is validated, including one with no Sheet yet,
and the command exits non-zero when any has a blocking validation error (the
daily refresh files a `diagnostics-yaml-error` issue on that). Only blocking
errors stop a language; a non-blocking one (e.g. a required class not yet
drafted) does not withhold the sync. The Sheet's tab is protected every run
(``locked_tabs.protect``).

`coded_data_clean_tree` (for `.yaml`) is enforced centrally by
preconditions.py before an `--apply` run reads coded_data/.
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


from .make_forms import _yaml_to_grid_df
from .validate_diagnostics import validate_diagnostics_yaml


def _discover_languages() -> List[str]:
    """Return language IDs that have a diagnostics YAML in coded_data/."""
    langs = []
    for yaml_path in sorted(CODED_DATA.glob("*/lang_setup/diagnostics_*.yaml")):
        lang_id = yaml_path.stem.replace("diagnostics_", "", 1)
        langs.append(lang_id)
    return langs


def _load_valid_yaml(lang_id: str, error_langs: List[str]) -> Optional[dict]:
    """The language's diagnostics YAML, or None if it is missing or has a
    blocking validation error (then the language is added to error_langs, so
    main() exits non-zero and the error reaches the daily refresh's issue
    rather than only a log nobody reads, issue #283)."""
    yaml_path = CODED_DATA / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
    if not yaml_path.exists():
        print(f"  [{lang_id}] No YAML found — skipping")
        return None
    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    issues = validate_diagnostics_yaml(yaml_data, lang_id)
    errors = [i for i in issues if i.level == "error"]
    # Gate on blocking errors only: a non-blocking one (e.g. "required class
    # not yet drafted", blocking=False by design -- see ValidationIssue's
    # docstring) must not withhold the push (arao1248's proform class, #279,
    # would otherwise be a false alarm on every daily run).
    for w in (i for i in issues if i.level == "warning"):
        print(f"  [{lang_id}] WARNING {w.location}: {w.message}")
    for e in errors:
        print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
    if any(e.blocking for e in errors):
        print(f"  [{lang_id}] Skipping — fix errors above before uploading.")
        error_langs.append(lang_id)
        return None
    return yaml_data


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


def _sync_to_sheet(lang_id: str, config: dict, apply: bool, error_langs: List[str]) -> bool:
    """Sync YAML → Google Sheet for one language.

    Validates the YAML, renders it as rows, compares them with the
    diagnostics Sheet, and with ``apply`` rewrites the Sheet if they differ.
    The Sheet is the tooling's (annotators read it), so nothing on it is lost.
    Returns True if changes were made (or would be).
    """
    from .drive_doorway import get_doorway

    yaml_data = _load_valid_yaml(lang_id, error_langs)
    if yaml_data is None:
        return False

    diag_id = config.get(lang_id, {}).get("diagnostics_spreadsheet_id")
    if not diag_id:
        print(f"  [{lang_id}] No diagnostics_spreadsheet_id in the ID file — skipping")
        return False

    new_df = _yaml_to_grid_df(yaml_data, lang_id)

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


def _apply_command(lang_filter: Optional[str]) -> str:
    """This same run, with --apply — the exact line to copy after a dry run.

    Built from the flags actually passed rather than named as "--apply", so
    nobody has to reassemble the invocation they just made from memory.
    """
    parts = ["python -m coding sync-diagnostics-yaml"]
    if lang_filter:
        parts.append(f"--lang {lang_filter}")
    parts.append("--apply")
    return " ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding sync-diagnostics-yaml`."""
    ap = argparse.ArgumentParser(
        description="Bring each diagnostics Sheet up to date with its diagnostics YAML."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
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
    lang_filter: Optional[str] = args.lang

    # coded_data_clean_tree is enforced centrally at the command dispatch
    # chokepoint (coding/preconditions.py), not here: a prior step's failed
    # commit could leave a stale YAML on disk for this command to copy.
    if not apply:
        print("Dry run — nothing is written.\n")

    from . import drive, drive_ids
    print("Connecting to Google APIs...")
    config = drive._load_drive_config()
    if not drive_ids.languages(config):
        raise SystemExit("The ID file has no languages. Run python -m coding generate-sheets --apply first.")
    languages = ([lang_filter] if lang_filter
                 else sorted(set(drive_ids.languages(config)) | set(_discover_languages())))
    changed = 0
    error_langs: List[str] = []
    for lang_id in languages:
        changed += _sync_to_sheet(lang_id, config, apply, error_langs)
    print()
    if apply:
        print(f"Done: {changed} Sheet(s) updated.")
    else:
        print(f"Dry run complete: {changed} Sheet(s) would be updated.")
        if changed:
            print(f"  → run: {_apply_command(lang_filter)}")
    if error_langs:
        print(f"\n{len(error_langs)} language(s) had blocking validation errors: "
              f"{', '.join(sorted(error_langs))}")
        sys.exit(1)
