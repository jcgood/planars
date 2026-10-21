#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python -m coding import-sheets              # dry run: report what would be written
    python -m coding import-sheets --apply      # write TSVs when content has changed
    python -m coding import-sheets --apply --overwrite-existing  # rewrite even if the cells match

Reads the manifest from Drive (via drive_config.json), downloads each sheet
tab, validates values, and writes {construction}.tsv to
coded_data/{lang_id}/{class_name}/.

Every file is written through the local-file door (coding/file_door.py): a
TSV whose downloaded content is unchanged is skipped; a changed one's
previous version goes to coded_data/{lang_id}/archive/{class_name}/, the
change goes in the language's changes.tsv, and the files written are
committed and pushed in planars-data when the command ends. Refuses to run
with --apply while coded_data/ has uncommitted changes (precondition
coded_data_clean_tree, checked by the dispatcher).

Exits non-zero only when the import itself broke: a class's spreadsheet
could not be opened, or a tab is missing from it. Invalid values are not an
import failure (issue #309): they are printed here, graded by
validate_coding.needs_fixing, and reported by validate-coding (run at the
end of an --apply that wrote anything, and daily by sheet-validation.yml),
which lists them in each sheet's Status tab.

What happens depends on each tab's Status:
  ready-for-review  imported in full; problems printed; destructive changes
                    go to pending_changes.json (and a pending-changes issue)
                    for apply-pending, not straight into the TSV.
  in-progress       imported as a backup with warnings suppressed; missing
                    rows or columns, or a large drop in filled cells, file a
                    collaborator-check issue instead. --ignore-status treats
                    every tab as ready-for-review.

A changed diagnostics TSV is diffed against the language's YAML
(sync_diagnostics_yaml's --from-tsv logic); ambiguous differences go to
diagnostics_drift.json, which the daily refresh turns into a
diagnostics-drift issue.

Side effect: invalid cells are highlighted pink in the Google Sheet during
import (same behaviour as validate-coding), on every tab whatever its Status.
This write-back happens even without --apply and even when the local TSV is
skipped.

Authentication: same OAuth2 setup as generate_sheets.py (see drive.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd

from .drive import (
    load_manifest, upload_manifest,
    _load_drive_config, _save_drive_config,
)
from .drive_doorway import get_doorway, WorksheetNotFound
from planars.schema_values import STATUS_IN_PROGRESS, STATUS_READY, is_keystone
from .restructure_sheets import _get_keyed_row_constructions, _get_pair_row_constructions
from . import file_door, issues
from . import validate_coding as _val
from .validate import ValidationIssue
from .validate_planar import validate_planar_df as _validate_planar_df
from .validate_diagnostics import validate_diagnostics_df as _validate_diagnostics_df
from .make_forms import (
    _diff_diagnostics_tsv_yaml,
    resolve_keystone_active,
    resolve_keystone_na_criteria,
    planar_to_manifest_dict,
)

ERROR_DIR    = ROOT / "import_errors"
from .apply_pending import _load_pending, _save_pending  # noqa: E402

# The share of an in-progress tab's filled cells (in rows present before and
# after) that may disappear in one import before it files a collaborator-check
# issue. A policy setting, not a linguistic fact; the one place it is stated
# (hidden-facts M4). schemas/issue_labels.yaml's prose says ">10%".
COLLABORATOR_CHECK_DECREASE = 0.10

# Re-export constants so external code that imported them directly still works.
_STRUCTURAL_COLS      = _val._STRUCTURAL_COLS
_PAIR_STRUCTURAL_COLS = _val._PAIR_STRUCTURAL_COLS
_TRAILING_COLS        = _val._TRAILING_COLS


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """The construction's annotation TSV under coded_data/ (the local-file door's path)."""
    return file_door.annotation(lang_id, class_name, construction).path


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _highlight_invalid_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Delegate to validate_coding.highlight_cells."""
    _val.highlight_cells(ws, bad_cells)


def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_annotation_rows.

    Returns (records, issues, bad_cells).
    """
    records, issues = _val.validate_annotation_rows(
        rows, expected_params, tab_name, param_values,
        keystone_active=keystone_active,
        keystone_na_criteria=keystone_na_criteria,
        class_name=class_name, lang_id=lang_id,
    )
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


def _validate_pair_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_pair_rows for pair-row tabs.

    Returns (records, issues, bad_cells) in the same format as _validate_tab.
    """
    records, issues = _val.validate_pair_rows(rows, expected_params, tab_name, param_values,
                                              class_name=class_name, lang_id=lang_id)
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


def _validate_keyed_tab(
    rows: List[List[str]],
    keyed: Dict,
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_keyed_rows for keyed-row tabs
    (biuniqueness_deviations' morphemes/morphs). Same return format as _validate_tab."""
    header = rows[0] if rows else []
    expected_params = [c for c in header[len(keyed["columns"]):] if c not in _TRAILING_COLS]
    records, issues = _val.validate_keyed_rows(
        rows, keyed["columns"], expected_params, tab_name, param_values,
        keyed.get("blank_ok_when"), class_name=class_name, lang_id=lang_id)
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _tsv_content_changed(path: Path, header: List[str], records: List[Dict]) -> bool:
    """Return True if the new header+records differ from the existing file at path.

    A different header (a column added, removed or moved on the sheet) is a
    change. Otherwise compares cell text element-wise after normalising
    NaN → "". Returns True when content differs or the file cannot be parsed.

    The header check came first only on 2026-10-13: before, the old file was
    lined up to the new header before comparing, which threw away any column
    the sheet no longer had — so a column deleted on the sheet never left the
    local file (synth0001's coreference tabs kept two dead columns for months).
    """
    try:
        existing = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return True
    if list(existing.columns) != list(header):
        return True
    new_df = pd.DataFrame(records).reindex(columns=header).fillna("")
    existing = existing.reindex(columns=header).fillna("")
    if existing.shape != new_df.shape:
        return True
    # Compare cell text, not DataFrames: DataFrame.equals also compares column
    # dtypes, and a tab with a header but no rows reads from disk as string
    # columns but builds from an empty record list as float columns -- so an
    # empty tab always looked "changed" and was re-archived on every import.
    return existing.astype(str).values.tolist() != new_df.astype(str).values.tolist()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_error_report(lang_id: str, lines: List[str], timestamp: str) -> Path:
    """Write warning lines to import_errors/{lang_id}_{timestamp}.txt."""
    ERROR_DIR.mkdir(exist_ok=True)
    report_path = ERROR_DIR / f"{lang_id}_{timestamp}.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Planar / diagnostics Sheet download and change detection
# ---------------------------------------------------------------------------

def _read_sheet_as_df(doorway, spreadsheet_id: str) -> Optional[pd.DataFrame]:
    """Download sheet1 of a Google Sheet and return as a DataFrame, or None if empty."""
    ss = doorway.open_spreadsheet(spreadsheet_id)
    rows = ss.sheet1.get_all_values()
    if not rows:
        return None
    return pd.DataFrame(rows[1:], columns=rows[0], dtype=str).fillna("")


def _position_list(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Return [(position_number, position_name), ...] from a planar DataFrame."""
    return list(zip(df.get("Position", pd.Series(dtype=str)).astype(str),
                    df.get("Position_Name", pd.Series(dtype=str)).astype(str)))


def _parse_criteria_names(criteria_str: str) -> List[str]:
    """Extract criterion names (stripping brace-syntax values) from a criteria cell."""
    return [s.split("{")[0].strip() for s in criteria_str.split(",") if s.strip()]


def _detect_planar_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    lang_id: str,
) -> Tuple[Set[str], List[Dict]]:
    """Compare old and new planar DataFrames for structural changes.

    Returns (safe_commands, pending_entries).
    safe_commands: set of CLI command strings that can be auto-applied.
    pending_entries: list of dicts for pending_changes.json (destructive changes).
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []

    old_positions = _position_list(old_df)
    new_positions = _position_list(new_df)

    if old_positions == new_positions:
        return safe_cmds, pending  # no structural change; overwrite freely

    old_names = [p[1] for p in old_positions]
    new_names = [p[1] for p in new_positions]
    added_names   = set(new_names) - set(old_names)
    removed_names = set(old_names) - set(new_names)

    if added_names and not removed_names:
        # Check old positions appear in same relative order within new list
        it = iter(old_names)
        cur = next(it, None)
        for name in new_names:
            if cur and name == cur:
                cur = next(it, None)
        in_order = cur is None
        if in_order:
            print(f"  [planar] New positions: {sorted(added_names)} — queuing update-sheets")
            safe_cmds.add("python -m coding update-sheets --apply")
            return safe_cmds, pending

    # Deletions or reordering — destructive
    diff_parts: List[str] = []
    if removed_names:
        diff_parts.append(f"Removed positions: {sorted(removed_names)}")
    if added_names:
        diff_parts.append(f"Added positions (alongside removals/reorder): {sorted(added_names)}")
    if not removed_names and not added_names:
        diff_parts.append("Position order changed")
    diff_parts.append(f"Old order: {' | '.join(old_names)}")
    diff_parts.append(f"New order: {' | '.join(new_names)}")

    pending.append({
        "lang_id": lang_id,
        "change_type": "planar_deletion_or_reorder",
        "description": "Planar structure has deleted or reordered positions — restructure-sheets required",
        "diff_summary": "\n".join(diff_parts),
        "command": "python -m coding restructure-sheets --apply",
    })
    return safe_cmds, pending


def _detect_diagnostics_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    lang_id: str,
    sheets_data: Optional[Dict] = None,
) -> Tuple[Set[str], List[Dict]]:
    """Compare old and new diagnostics DataFrames for changes to criteria and constructions.

    Returns (safe_commands, pending_entries).
    sheets_data: mapping of class_name → sheet info dict (from manifest) used to record
    spreadsheet IDs in new-construction pending entries for later Drive verification.
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []

    def _parse_row(row) -> Tuple[Set[str], Set[str]]:
        criteria = set(_parse_criteria_names(str(row.get("Criteria", ""))))
        constructions = {c.strip() for c in str(row.get("Constructions", "")).split(",") if c.strip()}
        return criteria, constructions

    old_by_class: Dict[str, Tuple[Set, Set]] = {}
    for _, row in old_df.iterrows():
        cls = str(row.get("Class", "")).strip()
        if cls:
            old_by_class[cls] = _parse_row(row)

    new_by_class: Dict[str, Tuple[Set, Set]] = {}
    for _, row in new_df.iterrows():
        cls = str(row.get("Class", "")).strip()
        if cls:
            new_by_class[cls] = _parse_row(row)

    all_classes = set(old_by_class) | set(new_by_class)
    for cls in sorted(all_classes):
        if cls not in old_by_class:
            print(f"  [diagnostics] New class '{cls}' — queuing generate-sheets")
            safe_cmds.add("python -m coding generate-sheets --apply")
            continue
        if cls not in new_by_class:
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_class_removed",
                "class_name": cls,
                "description": f"Analysis class '{cls}' removed from diagnostics_{lang_id}.tsv — requires YAML update and manifest cleanup",
                "diff_summary": (
                    f"Class '{cls}' was present in the old diagnostics but not in the new download.\n"
                    f"Steps to resolve:\n"
                    f"  1. Remove '{cls}' from coded_data/{lang_id}/lang_setup/diagnostics_{lang_id}.yaml\n"
                    f"  2. python -m coding sync-diagnostics-yaml --apply --lang {lang_id}\n"
                    f"  3. python -m coding prune-manifest --apply\n"
                    f"     (archives local TSVs for '{cls}' and removes stale manifest entry;\n"
                    f"     skipping this causes import-sheets to keep re-importing the old sheet)"
                ),
                "command": "python -m coding prune-manifest --apply",
            })
            continue

        old_criteria, old_constructions = old_by_class[cls]
        new_criteria, new_constructions = new_by_class[cls]

        added_criteria   = new_criteria   - old_criteria
        removed_criteria = old_criteria   - new_criteria
        added_cons       = new_constructions - old_constructions
        removed_cons     = old_constructions - new_constructions

        if added_criteria:
            print(f"  [diagnostics/{cls}] New criteria: {sorted(added_criteria)} — queuing sync-params")
            safe_cmds.add("python -m coding sync-params --apply")

        if removed_criteria:
            diff = (
                f"Class '{cls}': criteria removed: {sorted(removed_criteria)}\n"
                f"If renamed: python -m coding sync-params --rename old:new --apply\n"
                f"If removed: python -m coding sync-params --remove --apply"
            )
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_criteria_removed",
                "description": f"Criteria removed from class '{cls}' — rename or removal required",
                "diff_summary": diff,
                "command": "python -m coding sync-params --remove --apply",
            })

        if added_cons:
            sheet_id = (sheets_data or {}).get(cls, {}).get("spreadsheet_id", "")
            cons_list = sorted(added_cons)
            diff = (
                f"Class '{cls}': new construction(s): {cons_list}\n"
                f"A new tab must be added to the existing Google Sheet for this class.\n"
                f"This cannot be automated without archiving existing annotations.\n"
                f"Options:\n"
                f"  1. Open the Google Sheet for '{cls}' / '{lang_id}' and add the tab(s)\n"
                f"     manually, then set each to 'ready-for-review'.\n"
                f"  2. Or run: python -m coding generate-sheets --force --apply\n"
                f"     WARNING: --force archives ALL existing annotations for '{cls}'\n"
                f"     and recreates the sheet from scratch.\n"
                f"This entry will remain open until the tab(s) are verified in the Sheet."
            )
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_new_construction",
                "class_name": cls,
                "new_constructions": cons_list,
                "spreadsheet_id": sheet_id,
                "instructions_shown": False,
                "description": f"New construction(s) in class '{cls}' — new sheet tab required: {cons_list}",
                "diff_summary": diff,
                "command": "",
            })

        if removed_cons:
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_construction_removed",
                "description": f"Construction(s) removed from class '{cls}'",
                "diff_summary": f"Class '{cls}': removed: {sorted(removed_cons)}",
                "command": "python -m coding sync-params --apply",
            })

    return safe_cmds, pending


DRIFT_PATH = ROOT / "diagnostics_drift.json"


def _check_yaml_drift(lang_id: str, tsv_df: pd.DataFrame) -> List[Dict]:
    """Diff a diagnostics TSV against the language's YAML and return ambiguous entries.

    Returns a list of ambiguous change dicts (unknown classes/criteria, class removals)
    that require coordinator review. Deterministic changes are intentionally not returned
    here — they are handled by ``sync-diagnostics-yaml --from-tsv --apply``.

    Returns an empty list if no YAML exists for this language or no ambiguous drift found.
    """
    import yaml as _yaml
    yaml_path = file_door.diagnostics_yaml(lang_id).path
    if not yaml_path.exists():
        return []
    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = _yaml.safe_load(f)
    _det, ambiguous = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, lang_id)
    return ambiguous


def _append_pending_changes(new_entries: List[Dict]) -> None:
    """Append new_entries to pending_changes.json, preserving existing entries.

    A file that can't be read stops the import rather than being written
    over: until 2026-10-20 it was silently replaced, losing every entry
    waiting for review."""
    if not new_entries:
        return
    _save_pending(_load_pending() + new_entries)


def _notify_pending_changes(entries: List[Dict]) -> None:
    """Create or update a GitHub issue when pending_changes.json has new entries.

    Skips quietly if GitHub can't be reached — the warning printed to stdout
    is always the primary notification.
    """
    if not issues.available():
        return

    # Build issue body
    lines = [
        f"{len(entries)} destructive change(s) detected by `import-sheets` and written "
        f"to `pending_changes.json`. Run `python -m coding apply-pending` to review "
        f"and apply each change.\n"
    ]
    for e in entries:
        lines.append(f"### {e.get('lang_id', '?')} — {e.get('description', '')}")
        diff = e.get("diff_summary", "").strip()
        if diff:
            lines.append(f"```\n{diff}\n```")
        cmd = e.get("command", "")
        if cmd:
            lines.append(f"Command: `{cmd}`")
        lines.append("")

    try:
        number, created = issues.file_issue(
            "pending-changes",
            "Pending destructive changes require coordinator approval",
            "\n".join(lines))
        print(f"   GitHub issue #{number} "
              f"{'created' if created else 'updated with new pending changes'}.")
    except Exception as exc:
        print(f"   (Could not create GitHub issue: {exc})")


def _detect_collaborator_anomalies(
    out_path: Path,
    header: List[str],
    records: List[Dict],
    expected_params: List[str],
    lang_id: str,
    class_name: str,
    construction: str,
) -> List[str]:
    """Detect structural anomalies in an in-progress sheet vs the existing local TSV.

    Checks:
      A: Missing rows — (Element, Position_Number) keys present in local TSV
         but absent from the downloaded sheet.
      B: Missing/renamed param columns — columns in the local TSV header that
         no longer appear in the downloaded sheet.
      D: >10% annotated-cell decrease — significant value loss in matching rows.

    Returns a list of human-readable anomaly description strings (empty if none).
    Skips the check if no local TSV exists yet (first backup).
    """
    if not out_path.exists():
        return []
    try:
        old_df = pd.read_csv(out_path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return []

    anomalies: List[str] = []

    # A: Missing rows
    if "Element" in old_df.columns and "Position_Number" in old_df.columns:
        old_keys = {
            (str(r["Element"]).strip(), str(r["Position_Number"]).strip())
            for _, r in old_df.iterrows()
        }
        new_keys = {
            (r.get("Element", "").strip(), r.get("Position_Number", "").strip())
            for r in records
        }
        missing = old_keys - new_keys
        if missing:
            samples = sorted(f"{el} (pos {pos})" for el, pos in missing)
            suffix = "..." if len(samples) > 5 else ""
            anomalies.append(
                f"Missing rows: {len(missing)} row(s) present in local TSV absent from "
                f"sheet: {', '.join(samples[:5])}{suffix}"
            )

    # B: Missing/renamed param columns
    if expected_params:
        trailing_set = set(_TRAILING_COLS)
        old_params = [
            c for c in old_df.columns
            if c not in _STRUCTURAL_COLS and c not in trailing_set
        ]
        missing_cols = [c for c in old_params if c not in header]
        if missing_cols:
            anomalies.append(
                f"Missing columns: param column(s) in local TSV absent from sheet: "
                f"{missing_cols}"
            )

    # D: >10% annotated-cell decrease (restricted to rows present in both)
    if expected_params and "Element" in old_df.columns and "Position_Number" in old_df.columns:
        old_key_to_row: Dict[tuple, object] = {}
        for _, row in old_df.iterrows():
            if is_keystone(row.get("Position_Name", "")):
                continue
            key = (str(row.get("Element", "")).strip(), str(row.get("Position_Number", "")).strip())
            old_key_to_row[key] = row

        new_key_to_row: Dict[tuple, Dict] = {}
        for r in records:
            if is_keystone(r.get("Position_Name", "")):
                continue
            key = (r.get("Element", "").strip(), r.get("Position_Number", "").strip())
            new_key_to_row[key] = r

        common_keys = set(old_key_to_row) & set(new_key_to_row)
        if common_keys:
            old_params_in_df = [p for p in expected_params if p in old_df.columns]
            old_annotated = sum(
                1 for key in common_keys
                for p in old_params_in_df
                if str(old_key_to_row[key].get(p, "")).strip() not in ("", "na", "?")
            )
            new_annotated = sum(
                1 for key in common_keys
                for p in expected_params
                if new_key_to_row[key].get(p, "").strip() not in ("", "na", "?")
            )
            if old_annotated > 0:
                decrease = (old_annotated - new_annotated) / old_annotated
                if decrease > COLLABORATOR_CHECK_DECREASE:
                    anomalies.append(
                        f"Annotated-cell decrease: {old_annotated} → {new_annotated} "
                        f"({decrease:.0%} decrease, threshold {COLLABORATOR_CHECK_DECREASE:.0%})"
                    )

    return anomalies


def _notify_collaborator_check(entries: List[Dict]) -> None:
    """Create or update a GitHub collaborator-check issue for in-progress anomalies.

    Anomalies (missing rows, missing columns, >10% cell decrease) in in-progress
    sheets are coordinator-facing signals, not blocking errors. The coordinator
    should verify with the collaborator whether the change was intentional.
    """
    if not issues.available():
        return

    lines = [
        f"{len(entries)} in-progress sheet(s) have structural anomalies that warrant a "
        f"check with the collaborator. These sheets are still marked `in-progress` so "
        f"no pipeline action is blocked — but the coordinator should verify that the "
        f"changes are intentional.\n"
    ]
    for e in entries:
        lines.append(f"### {e['lang_id']} / {e['class_name']} / {e['construction']}")
        for a in e["anomalies"]:
            lines.append(f"- {a}")
        lines.append("")

    try:
        number, created = issues.file_issue(
            "collaborator-check",
            "In-progress sheet anomalies — verify with collaborator",
            "\n".join(lines))
        print(f"   GitHub issue #{number} {'created' if created else 'updated'} "
              "(collaborator-check).")
    except Exception as exc:
        print(f"   (Could not create GitHub issue: {exc})")


def _download_lang_setup_sheets(
    doorway,
    lang_id: str,
    lang_data: Dict,
    apply: bool = True,
) -> Tuple[Set[str], List[Dict], List[Dict]]:
    """Download planar and diagnostics Sheets for one language to local TSVs.

    Validates the downloaded data before writing. Detects structural changes
    and classifies them as safe (auto-applicable) or destructive (pending).
    Writes go through the local-file door, which keeps the previous version.

    Returns (safe_commands, pending_entries, drift_entries).
    drift_entries contains ambiguous TSV→YAML differences for coordinator review.
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []
    drift_entries: List[Dict] = []

    # --- Planar sheet ---
    planar_id = lang_data.get("planar_spreadsheet_id")
    if planar_id:
        new_df = _read_sheet_as_df(doorway, planar_id)
        if new_df is not None:
            issues = _validate_planar_df(new_df)
            errors = [i for i in issues if i.level == "error"]
            if errors:
                print(f"  [planar] Validation errors — skipping download:")
                for i in errors:
                    print(f"    {i}")
            else:
                for i in issues:
                    print(f"  [planar] WARNING: {i}")

                target = file_door.planar(lang_id)
                out_path = target.path
                if out_path.exists():
                    old_df = pd.read_csv(out_path, sep="\t", dtype=str, keep_default_na=False)
                    s, p = _detect_planar_changes(old_df, new_df, lang_id)
                    safe_cmds |= s
                    pending   += p
                    content_changed = not old_df.reset_index(drop=True).equals(
                        new_df.reset_index(drop=True)
                    )
                else:
                    content_changed = True
                if not content_changed:
                    print(f"  [planar] No changes → {out_path.name}")
                elif apply:
                    file_door.write(target, file_door.frame_text(new_df),
                                    why="downloaded from the planar Sheet")
                    print(f"  [planar] Downloaded → {out_path.name}")
                else:
                    action = "Would overwrite (changed)" if out_path.exists() else "Would create"
                    print(f"  [planar] {action} → {out_path.name}")

    # --- Diagnostics sheet ---
    diag_id = lang_data.get("diagnostics_spreadsheet_id")
    if diag_id:
        new_df = _read_sheet_as_df(doorway, diag_id)
        if new_df is not None:
            issues = _validate_diagnostics_df(new_df, lang_id)
            errors = [i for i in issues if i.level == "error"]
            # Gate on blocking errors only (issue #283) -- this used to gate
            # on every level=="error" issue regardless of .blocking, which
            # meant a non-blocking one (a required class not yet drafted,
            # blocking=False by design -- see ValidationIssue's docstring)
            # silently skipped the whole diagnostics Sheet download, every
            # run, for as long as the gap stayed open. Confirmed actually
            # happening to arao1248 (issue #279's already-tracked missing
            # proform class) before this fix.
            blocking_errors = [e for e in errors if e.blocking]
            if blocking_errors:
                print(f"  [diagnostics] Validation errors — skipping download:")
                for i in blocking_errors:
                    print(f"    {i}")
            else:
                for i in issues:
                    if i.level == "error":
                        print(f"  [diagnostics] ERROR (non-blocking): {i}")
                    else:
                        print(f"  [diagnostics] WARNING: {i}")

                target = file_door.diagnostics_tsv(lang_id)
                diag_path = target.path
                if diag_path.exists():
                    old_df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
                    s, p = _detect_diagnostics_changes(old_df, new_df, lang_id, lang_data.get("sheets", {}))
                    safe_cmds |= s
                    pending   += p
                    content_changed = not old_df.reset_index(drop=True).equals(
                        new_df.reset_index(drop=True)
                    )
                else:
                    content_changed = True
                if not content_changed:
                    print(f"  [diagnostics] No changes → {diag_path.name}")
                elif apply:
                    file_door.write(target, file_door.frame_text(new_df),
                                    why="downloaded from the diagnostics Sheet")
                    print(f"  [diagnostics] Downloaded → {diag_path.name}")
                else:
                    action = "Would overwrite (changed)" if diag_path.exists() else "Would create"
                    print(f"  [diagnostics] {action} → {diag_path.name}")

                # --- YAML drift check ---
                # Compare the freshly-downloaded TSV against the YAML (if one exists).
                # Only ambiguous changes are returned; deterministic ones are handled by
                # sync-diagnostics-yaml --from-tsv --apply.
                ambiguous = _check_yaml_drift(lang_id, new_df)
                if ambiguous:
                    print(f"  [diagnostics] {len(ambiguous)} ambiguous YAML drift item(s) — see diagnostics_drift.json")
                    drift_entries.append({"lang_id": lang_id, "ambiguous": ambiguous})

    return safe_cmds, pending, drift_entries


def _verify_manifest_sheet_ids(doorway, manifest: Dict) -> None:
    """Abort if any annotation spreadsheet ID in the manifest is inaccessible.

    Protects against writing TSVs from a stale or corrupted manifest that
    points to wrong (empty, deleted, or duplicate) spreadsheets. Runs a
    lightweight Drive metadata fetch for each sheet ID — no sheet content
    is downloaded at this stage.
    """
    bad: List[str] = []
    for lang_id, lang_data in manifest.items():
        if not isinstance(lang_data, dict):
            continue
        for class_name, sheet_info in lang_data.get("sheets", {}).items():
            if not isinstance(sheet_info, dict):
                continue
            spreadsheet_id = sheet_info.get("spreadsheet_id")
            if not spreadsheet_id:
                continue
            try:
                doorway.get_file(spreadsheet_id, fields="id,trashed")
            except Exception as e:
                bad.append(f"  {lang_id}/{class_name}: {spreadsheet_id} — {e}")
    if bad:
        print("ERROR: Manifest contains inaccessible spreadsheet IDs:")
        for line in bad:
            print(line)
        print("The manifest may be stale or point to deleted/moved sheets.")
        print("→ Run: python -m coding integrity-check --sheets")
        print("  This will list which spreadsheet IDs are unreachable and what to do next.")
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding import-sheets`."""
    ap = argparse.ArgumentParser(
        description="Download filled annotation sheets to TSVs."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write TSVs (default: dry run)",
    )
    ap.add_argument(
        "--overwrite-existing", action="store_true", dest="force",
        help="rewrite a TSV even when its cells match the sheet (e.g. to bring its "
             "formatting in line); a file whose bytes are already identical is "
             "never rewritten",
    )
    ap.add_argument(
        "--ignore-status", action="store_true",
        help="treat all tabs as ready-for-review, regardless of their Status tab",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding import-sheets`.

    Dry-run by default — pass --apply to write any TSVs. Loads the manifest
    from Drive, downloads each construction tab, validates values, and writes
    filled TSVs under coded_data/{lang_id}/{class_name}/. Compares downloaded
    content to the existing file: if changed, writes the new one through the
    local-file door (which archives the old); if unchanged, skips with "No
    changes". --overwrite-existing rewrites a file whose cells match but whose
    text differs; the door never rewrites identical bytes.
    Writes an error report to import_errors/ if any warnings are generated.
    """
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    force = args.force
    ignore_status = args.ignore_status
    lang_filter = args.lang
    timestamp = file_door.stamp()

    if not apply:
        print("DRY RUN — pass --apply to write TSVs.\n")

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here.
    print("Connecting to Google...")
    doorway = get_doorway()
    manifest = load_manifest(doorway)

    if apply:
        _verify_manifest_sheet_ids(doorway, manifest)

    total_files = 0
    in_progress_files = 0
    total_warnings = 0
    # Problems that mean the import itself broke, and make this command exit
    # non-zero so the daily refresh files an import-error issue (#283): a
    # class's spreadsheet couldn't be opened, or a tab is missing from a
    # sheet. Problems in the data (an invalid value on a ready-for-review tab)
    # are not counted here since #309: validate-coding reports them, to the
    # annotator (the sheet's Status tab) and in a sheet-validation issue.
    total_import_errors = 0
    all_safe_cmds: Set[str] = set()
    all_pending: List[Dict] = []
    all_drift: List[Dict] = []
    all_collaborator_check: List[Dict] = []
    pair_row_constructions = _get_pair_row_constructions()
    keyed_row_constructions = _get_keyed_row_constructions()

    for lang_id, lang_data in manifest.items():
        if lang_filter and lang_id != lang_filter:
            continue
        print(f"\nLanguage: {lang_id}")
        lang_warning_lines: List[str] = []
        lang_param_map = _val._load_param_map(lang_id)

        # Download planar and diagnostics Sheets to local TSVs; detect changes.
        s, p, d = _download_lang_setup_sheets(doorway, lang_id, lang_data, apply)
        all_safe_cmds |= s
        all_pending   += p
        all_drift     += d
        if apply and p:
            # Write this language's destructive changes immediately rather than
            # accumulating in all_pending for a single end-of-run write -- a
            # crash while a later language is still being processed must not
            # lose an earlier language's already-detected changes (issue #280).
            # _append_pending_changes reads-then-writes, so calling it once per
            # language is equivalent to one call at the end when nothing fails.
            _append_pending_changes(p)

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            try:
                ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
            except Exception as e:
                msg = f"[{class_name}] could not open spreadsheet {sheet_info['spreadsheet_id']!r} for {lang_id}: {e}"
                print(f"    ERROR: {msg}")
                lang_warning_lines.append(f"ERROR: {msg}")
                total_import_errors += 1
                continue

            status_map = _val.tab_statuses(ss)
            if not status_map and not ignore_status:
                print(f"    (no Status tab found — importing all constructions)")

            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except WorksheetNotFound:
                    msg = f"[{class_name}/{construction}] tab not found in sheet, skipping"
                    print(f"    ERROR: {msg}")
                    lang_warning_lines.append(f"ERROR: {msg}")
                    total_import_errors += 1
                    continue

                # Determine tab status. In-progress sheets are imported for backup
                # and validation (pink highlighting), but pipeline warnings are
                # suppressed and anomalies are raised as collaborator-check rather
                # than pending-changes. --ignore-status treats all tabs as ready.
                tab_status = STATUS_READY
                if not ignore_status and status_map:
                    tab_status = status_map.get(construction, STATUS_IN_PROGRESS)
                in_progress = (tab_status != STATUS_READY)

                rows = ws.get_all_values()

                header = rows[0] if rows else []

                # Per-param allowed values: the language's diagnostics YAML through
                # coding.schemas.criteria_for — the same source validate-coding
                # uses — not the manifest's cached copy (Phase 10, 2026-10-12).
                param_values = lang_param_map.get(class_name, {}).get(construction, {}).get("values")

                # Which constructions have pair rows comes from the schema, not
                # from a list written out here. This used to name only
                # nonpermutability and coreference, and so missed
                # phrasal_accent/general — which validate-coding, reading the
                # schema, treated as pair rows all along. Two places deciding
                # the same thing and disagreeing is the defect this project
                # keeps hitting; validate_coding.revalidate_sheets is the pattern copied.
                is_pair_tab = construction in pair_row_constructions.get(class_name, set())
                keyed = keyed_row_constructions.get(class_name, {}).get(construction)
                if keyed:
                    expected_params = [c for c in header[len(keyed["columns"]):]
                                       if c not in _TRAILING_COLS]
                    records, found, bad_cells =_validate_keyed_tab(
                        rows, keyed, construction, param_values,
                        class_name=class_name, lang_id=lang_id,
                    )
                elif is_pair_tab:
                    expected_params = (
                        [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    records, found, bad_cells =_validate_pair_tab(
                        rows, expected_params, construction, param_values,
                        class_name=class_name, lang_id=lang_id,
                    )
                else:
                    expected_params = (
                        [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    ka = resolve_keystone_active(
                        lang_id, class_name, construction,
                        data_dir=file_door.planar(lang_id).path.parent,
                    )
                    kna = resolve_keystone_na_criteria(class_name)
                    records, found, bad_cells =_validate_tab(
                        rows, expected_params, construction, param_values,
                        keystone_active=bool(ka),
                        keystone_na_criteria=kna,
                        class_name=class_name, lang_id=lang_id,
                    )

                if bad_cells:
                    try:
                        _highlight_invalid_cells(ws, bad_cells)
                    except Exception as e:
                        print(f"    WARNING: could not highlight cells: {e}")

                # For ready-for-review tabs, show what is wrong (structural and
                # invalid-value), graded by validate_coding's one rule against
                # the tab's real Status (--ignore-status changes what is
                # imported, not how serious a value is). For in-progress tabs,
                # say nothing — partial or invalid annotation is expected there.
                # None of it stops the import (#309).
                if not in_progress:
                    shown = [i for i in _val.grade(found, status_map.get(construction, STATUS_IN_PROGRESS))
                             if i.kind != _val.BLANK]
                    for i in shown:
                        print(f"    {i}")
                        lang_warning_lines.append(f"[{class_name}/{construction}] {i}")
                    total_warnings += len(shown)
                else:
                    print(f"    [{construction}] status: {tab_status!r} — importing for backup")

                out_path = _get_output_path(lang_id, class_name, construction)
                out_name = out_path.name
                dest = f"coded_data/{lang_id}/{class_name}/{out_name}"
                label = " [backup]" if in_progress else ""

                if not apply:
                    if out_path.exists():
                        changed = _tsv_content_changed(out_path, header, records)
                        action = "Would overwrite (changed)" if changed else "No changes"
                    else:
                        action = "Would create"
                    print(f"    [{construction}]{label} {action} → {dest}")
                    continue

                if out_path.exists():
                    if not force and not _tsv_content_changed(out_path, header, records):
                        print(f"    [{construction}]{label} No changes → {dest}")
                        continue

                    if in_progress:
                        anomalies = _detect_collaborator_anomalies(
                            out_path, header, records, expected_params,
                            lang_id, class_name, construction,
                        )
                        if anomalies:
                            all_collaborator_check.append({
                                "lang_id": lang_id,
                                "class_name": class_name,
                                "construction": construction,
                                "anomalies": anomalies,
                            })
                            for a in anomalies:
                                print(f"    [{construction}] ANOMALY: {a}")

                # The door keeps the previous version in archive/{class}/ and
                # logs the change in the language's changes.tsv.
                file_door.write(file_door.annotation(lang_id, class_name, construction),
                                file_door.tsv_text(header, records),
                                why=f"imported from the annotator's sheet ({tab_status})")

                # Count rows with at least one blank param cell (for status line).
                # Pair-row and keyed-row sheets have no keystone; element-row
                # sheets exclude it.
                if is_pair_tab or keyed:
                    blank_count = sum(
                        1 for r in records
                        if any(r.get(p, "") == "" for p in expected_params)
                    )
                else:
                    blank_count = sum(
                        1 for r in records
                        if not is_keystone(r.get("Position_Name", ""))
                        and any(r.get(p, "") == "" for p in expected_params)
                    )
                status = f"{len(records)} rows"
                if blank_count:
                    status += f", {blank_count} blank param cells"
                print(f"    [{construction}]{label} {status} → {dest}")
                if in_progress:
                    in_progress_files += 1
                else:
                    total_files += 1

        if lang_warning_lines:
            report_path = _write_error_report(lang_id, lang_warning_lines, timestamp)
            print(f"\n  Error report: {report_path.relative_to(ROOT)}")

    backup_part = f", {in_progress_files} in-progress backup(s)" if in_progress_files else ""
    print(f"\nDone. {total_files} file(s) written{backup_part}, {total_warnings} warning(s).")

    # Sync glottolog + meta from languages.yaml into the Drive manifest.
    # Read fresh each run — not via coding.schemas cached loader — because
    # lookup-lang may have written a new languages.yaml entry earlier in the
    # same session and we need the just-written state, not a cached snapshot.
    import yaml as _yaml
    _lang_yaml = ROOT / "schemas" / "languages.yaml"
    _langs = {}
    if _lang_yaml.exists():
        with open(_lang_yaml, encoding="utf-8") as _f:
            _langs = _yaml.safe_load(_f) or {}
    manifest_changed = False
    for lid, entry in manifest.items():
        if lid.startswith("_") or not isinstance(entry, dict):
            continue
        lang_entry = _langs.get(lid)
        if lang_entry:
            if entry.get("glottolog") != lang_entry.get("glottolog") or \
               entry.get("meta") != lang_entry.get("meta"):
                entry["glottolog"] = lang_entry.get("glottolog", {})
                entry["meta"] = lang_entry.get("meta", {})
                manifest_changed = True
        # Refresh planar structure so Colab source='sheets' can derive nonpermutability spans.
        planar_file = file_door.planar(lid).path
        if planar_file.exists():
            new_planar = planar_to_manifest_dict(planar_file, lid)
            if entry.get("planar") != new_planar:
                entry["planar"] = new_planar
                manifest_changed = True
    if manifest_changed and apply:
        drive_cfg = _load_drive_config()
        file_id = drive_cfg.get("_planars_config_file_id")
        root_id = drive_cfg.get("_root_folder_id")
        new_id = upload_manifest(doorway, manifest, root_id, file_id)
        if new_id != file_id:
            drive_cfg["_planars_config_file_id"] = new_id
            _save_drive_config(drive_cfg)
        print("manifest.json updated on Drive with languages.yaml metadata.")
    elif manifest_changed:
        print("(manifest.json has pending metadata changes — re-run with --apply to write)")

    # Destructive changes were already written to pending_changes.json
    # incrementally, per language, above (issue #280) -- this is summary/
    # notification only, not a write.
    if all_pending:
        if apply:
            print(f"\n⚠  {len(all_pending)} destructive change(s) written to pending_changes.json")
            print("   Review and apply with: python -m coding apply-pending")
            _notify_pending_changes(all_pending)
        else:
            print(f"\n⚠  {len(all_pending)} destructive change(s) detected (dry run — pass --apply to write pending_changes.json):")
            for e in all_pending:
                print(f"   {e.get('lang_id', '?')}: {e.get('description', '')}")

    # Raise collaborator-check issue if any in-progress anomalies were detected.
    if all_collaborator_check:
        if apply:
            print(f"\n⚠  {len(all_collaborator_check)} in-progress sheet(s) have anomalies — verify with collaborator")
            _notify_collaborator_check(all_collaborator_check)
        else:
            print(f"\n⚠  {len(all_collaborator_check)} in-progress sheet(s) have anomalies (dry run):")
            for e in all_collaborator_check:
                print(f"   {e['lang_id']}/{e['class_name']}/{e['construction']}: "
                      f"{len(e['anomalies'])} anomaly(s)")

    # Write ambiguous YAML drift entries for coordinator review.
    if all_drift:
        print(f"\n⚠  {len(all_drift)} language(s) have ambiguous YAML drift — see diagnostics_drift.json")
        print("   Resolve with: python -m coding sync-diagnostics-yaml --from-tsv --apply")
        if apply:
            DRIFT_PATH.write_text(
                json.dumps(all_drift, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            print("   (dry run — pass --apply to write diagnostics_drift.json)")

    # Auto-apply safe downstream commands (new elements → update-sheets, etc.)
    if all_safe_cmds:
        if apply:
            print(f"\nAuto-applying {len(all_safe_cmds)} safe downstream command(s):")
            import importlib
            for cmd in sorted(all_safe_cmds):
                print(f"  {cmd}")
                parts = cmd.split()
                # parts: ["python", "-m", "coding", "<command>", ...]
                mod_name = "coding." + parts[3].replace("-", "_")
                extra_args = parts[4:]
                sys.argv = [parts[3]] + extra_args
                mod = importlib.import_module(mod_name)
                mod.main()
        else:
            print(f"\nSafe downstream commands detected (dry run — pass --apply to auto-apply):")
            for cmd in sorted(all_safe_cmds):
                print(f"  {cmd}")

    if apply and (total_files > 0 or in_progress_files > 0):
        print("\n--- Revalidating sheets ---")
        from .validate_coding import revalidate_sheets
        lang_ids = [lang_filter] if lang_filter else None
        revalidate_sheets(lang_ids=lang_ids)

    if total_import_errors:
        # Issue #283: these used to never affect the exit code, so the daily
        # refresh's import-error issue never fired for them -- only a hard
        # crash did. Checked last, after every other step above, so one
        # unreadable sheet doesn't cut short pending-changes/notification/
        # revalidation work this run should still do regardless.
        print(f"\n{total_import_errors} sheet(s) or tab(s) could not be read — see ERROR lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
