#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python -m coding import-sheets              # dry run: report what would be written
    python -m coding import-sheets --apply      # write TSVs when content has changed
    python -m coding import-sheets --apply --overwrite-existing  # force overwrite even if unchanged

Reads the manifest from Drive (via drive_config.json), downloads each sheet
tab, validates values, and writes {construction}.tsv to
coded_data/{lang_id}/{class_name}/.

Side effect: invalid cells are highlighted pink in the Google Sheet during
import (same behaviour as validate-coding). This write-back happens even
without --apply and even when the local TSV is skipped.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd
import gspread

from .drive import (
    _get_clients, _load_manifest_from_drive, _open_spreadsheet,
    _upload_planars_config, _load_drive_config, _save_drive_config,
    _with_retry,
)
from .generate_sheets import _STATUS_TAB, _STATUS_VALUES
from . import validate_coding as _val
from .validate_planar import validate_planar_df as _validate_planar_df
from .validate_diagnostics import validate_diagnostics_df as _validate_diagnostics_df
from .make_forms import (
    _diff_diagnostics_tsv_yaml,
    resolve_keystone_active,
    resolve_keystone_na_criteria,
)

ERROR_DIR    = ROOT / "import_errors"
PENDING_PATH = ROOT / "pending_changes.json"

# Re-export constants so external code that imported them directly still works.
_STRUCTURAL_COLS      = _val._STRUCTURAL_COLS
_PAIR_STRUCTURAL_COLS = _val._PAIR_STRUCTURAL_COLS
_TRAILING_COLS        = _val._TRAILING_COLS
_DEFAULT_EXPECTED     = _val._DEFAULT_EXPECTED


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """Return the output TSV path under coded_data/, creating directories as needed."""
    folder = ROOT / "coded_data" / lang_id / class_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{construction}.tsv"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _highlight_invalid_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Delegate to validate.highlight_cells (kept for backwards compatibility)."""
    _val.highlight_cells(ws, bad_cells)


def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
) -> Tuple[List[Dict], List[str], List[Tuple[int, int]]]:
    """Delegate to validate.validate_annotation_rows (kept for backwards compatibility).

    Returns (records, warnings, bad_cells) in the original format.
    """
    records, issues = _val.validate_annotation_rows(
        rows, expected_params, tab_name, param_values,
        keystone_active=keystone_active,
        keystone_na_criteria=keystone_na_criteria,
    )
    warnings  = [str(i) for i in issues]
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, warnings, bad_cells


def _validate_pair_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
) -> Tuple[List[Dict], List[str], List[Tuple[int, int]]]:
    """Delegate to validate.validate_pair_rows for nonpermutability pair-row sheets.

    Returns (records, warnings, bad_cells) in the same format as _validate_tab.
    """
    records, issues = _val.validate_pair_rows(rows, expected_params, tab_name, param_values)
    warnings  = [str(i) for i in issues]
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, warnings, bad_cells


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _archive_tsv(path: Path, timestamp: str) -> Path:
    """Copy path to the per-language archive directory with a timestamp suffix.

    Archives to coded_data/{lang}/archive/{class}/{stem}_{timestamp}.tsv so that
    retired class directories can be removed cleanly after pruning.
    Creates intermediate directories if absent. Returns the archive path.
    """
    archive_dir = path.parent.parent / "archive" / path.parent.name
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{path.stem}_{timestamp}{path.suffix}"
    shutil.copy2(path, archive_path)
    return archive_path


def _tsv_content_changed(path: Path, header: List[str], records: List[Dict]) -> bool:
    """Return True if the new header+records differ from the existing file at path.

    Reads the existing file into a DataFrame, aligns columns to the new header
    (filling missing columns with ""), and compares element-wise after normalising
    NaN → "".  Returns True when content differs or the file cannot be parsed.
    """
    try:
        existing = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return True
    new_df = pd.DataFrame(records).reindex(columns=header).fillna("")
    existing = existing.reindex(columns=header).fillna("")
    if existing.shape != new_df.shape:
        return True
    return not existing.reset_index(drop=True).equals(new_df.reset_index(drop=True))


def _write_tsv(path: Path, header: List[str], records: List[Dict]) -> None:
    """Write records to a tab-separated file with the given header order.

    Extra keys in records beyond the header are silently ignored
    (extrasaction='ignore').
    """
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, delimiter="\t",
            extrasaction="ignore", quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(records)


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

def _read_sheet_as_df(gc: gspread.Client, spreadsheet_id: str) -> Optional[pd.DataFrame]:
    """Download sheet1 of a Google Sheet and return as a DataFrame, or None if empty."""
    ss = _open_spreadsheet(gc, spreadsheet_id)
    rows = _with_retry(ss.sheet1.get_all_values)
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
            safe_cmds.add("python -m coding generate-sheets")
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
                f"  2. Or run: python -m coding generate-sheets --force\n"
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
    yaml_path = ROOT / "coded_data" / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
    if not yaml_path.exists():
        return []
    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = _yaml.safe_load(f)
    _det, ambiguous = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, lang_id)
    return ambiguous


def _read_status_tab(ss: gspread.Spreadsheet) -> Dict[str, str]:
    """Return {construction: status} from the Status tab, or {} if absent."""
    try:
        ws = _with_retry(lambda: ss.worksheet(_STATUS_TAB))
    except gspread.WorksheetNotFound:
        return {}
    rows = _with_retry(ws.get_all_values)
    if len(rows) < 2:
        return {}
    return {row[0].strip(): row[1].strip() for row in rows[1:] if len(row) >= 2 and row[0].strip()}


def _append_pending_changes(new_entries: List[Dict]) -> None:
    """Append new_entries to pending_changes.json, preserving existing entries."""
    if not new_entries:
        return
    existing: List[Dict] = []
    if PENDING_PATH.exists():
        try:
            existing = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    PENDING_PATH.write_text(
        json.dumps(existing + new_entries, indent=2), encoding="utf-8"
    )


def _notify_pending_changes(entries: List[Dict]) -> None:
    """Create or update a GitHub issue when pending_changes.json has new entries.

    Requires `gh` CLI to be installed and authenticated. Silently skips if not
    available — the warning printed to stdout is always the primary notification.
    """
    import subprocess as _sp

    # Check gh is available
    try:
        _sp.run(["gh", "auth", "status"], capture_output=True, check=True)
    except Exception:
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

    body = "\n".join(lines)
    body_file = ROOT / "pending_changes_issue.tmp"
    body_file.write_text(body, encoding="utf-8")

    try:
        # Check for an existing open pending-changes issue
        result = _sp.run(
            ["gh", "issue", "list", "--label", "pending-changes",
             "--state", "open", "--json", "number", "--jq", ".[0].number"],
            capture_output=True, text=True,
        )
        existing_num = result.stdout.strip()
        if existing_num and existing_num != "null":
            _sp.run(
                ["gh", "issue", "comment", existing_num, "--body-file", str(body_file)],
                check=True,
            )
            print(f"   GitHub issue #{existing_num} updated with new pending changes.")
        else:
            r = _sp.run(
                ["gh", "issue", "create",
                 "--title", f"Pending destructive changes require coordinator approval",
                 "--label", "pending-changes",
                 "--body-file", str(body_file)],
                capture_output=True, text=True, check=True,
            )
            print(f"   GitHub issue created: {r.stdout.strip()}")
    except Exception as exc:
        print(f"   (Could not create GitHub issue: {exc})")
    finally:
        body_file.unlink(missing_ok=True)


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
            if str(row.get("Position_Name", "")).lower() == "v:verbstem":
                continue
            key = (str(row.get("Element", "")).strip(), str(row.get("Position_Number", "")).strip())
            old_key_to_row[key] = row

        new_key_to_row: Dict[tuple, Dict] = {}
        for r in records:
            if r.get("Position_Name", "").lower() == "v:verbstem":
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
                if decrease > 0.10:
                    anomalies.append(
                        f"Annotated-cell decrease: {old_annotated} → {new_annotated} "
                        f"({decrease:.0%} decrease, threshold 10%)"
                    )

    return anomalies


def _notify_collaborator_check(entries: List[Dict]) -> None:
    """Create or update a GitHub collaborator-check issue for in-progress anomalies.

    Anomalies (missing rows, missing columns, >10% cell decrease) in in-progress
    sheets are coordinator-facing signals, not blocking errors. The coordinator
    should verify with the collaborator whether the change was intentional.
    """
    import subprocess as _sp
    try:
        _sp.run(["gh", "auth", "status"], capture_output=True, check=True)
    except Exception:
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

    body = "\n".join(lines)
    body_file = ROOT / "collaborator_check_issue.tmp"
    body_file.write_text(body, encoding="utf-8")

    try:
        result = _sp.run(
            ["gh", "issue", "list", "--label", "collaborator-check",
             "--state", "open", "--json", "number", "--jq", ".[0].number"],
            capture_output=True, text=True,
        )
        existing_num = result.stdout.strip()
        if existing_num and existing_num != "null":
            _sp.run(
                ["gh", "issue", "comment", existing_num, "--body-file", str(body_file)],
                check=True,
            )
            print(f"   GitHub issue #{existing_num} updated (collaborator-check).")
        else:
            r = _sp.run(
                ["gh", "issue", "create",
                 "--title", "In-progress sheet anomalies — verify with collaborator",
                 "--label", "collaborator-check",
                 "--body-file", str(body_file)],
                capture_output=True, text=True, check=True,
            )
            print(f"   GitHub issue created: {r.stdout.strip()}")
    except Exception as exc:
        print(f"   (Could not create GitHub issue: {exc})")
    finally:
        body_file.unlink(missing_ok=True)


def _download_lang_setup_sheets(
    gc: gspread.Client,
    lang_id: str,
    lang_data: Dict,
    timestamp: str = "",
    apply: bool = True,
) -> Tuple[Set[str], List[Dict], List[Dict]]:
    """Download planar and diagnostics Sheets for one language to local TSVs.

    Validates the downloaded data before writing. Detects structural changes
    and classifies them as safe (auto-applicable) or destructive (pending).

    Returns (safe_commands, pending_entries, drift_entries).
    drift_entries contains ambiguous TSV→YAML differences for coordinator review.
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []
    drift_entries: List[Dict] = []

    planar_dir = ROOT / "coded_data" / lang_id / "lang_setup"

    # --- Planar sheet ---
    planar_id = lang_data.get("planar_spreadsheet_id")
    if planar_id:
        new_df = _read_sheet_as_df(gc, planar_id)
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

                out_path = planar_dir / f"planar_{lang_id}.tsv"
                existing = sorted(planar_dir.glob("planar_*.tsv")) if planar_dir.exists() else []
                old_file = existing[-1] if existing else None
                if old_file:
                    old_df = pd.read_csv(old_file, sep="\t", dtype=str).fillna("")
                    s, p = _detect_planar_changes(old_df, new_df, lang_id)
                    safe_cmds |= s
                    pending   += p
                    content_changed = not old_df.reset_index(drop=True).equals(
                        new_df.reset_index(drop=True)
                    )
                    if apply:
                        if content_changed:
                            if timestamp:
                                archived = _archive_tsv(old_file, timestamp)
                                print(f"  [planar] Archived existing → archive/{archived.name}")
                            if old_file != out_path:
                                old_file.unlink()
                            planar_dir.mkdir(parents=True, exist_ok=True)
                            new_df.to_csv(out_path, sep="\t", index=False)
                            print(f"  [planar] Downloaded → {out_path.name}")
                        else:
                            if old_file != out_path:
                                old_file.rename(out_path)
                                print(f"  [planar] Renamed → {out_path.name}")
                            else:
                                print(f"  [planar] No changes → {out_path.name}")
                    else:
                        action = "Would overwrite (changed)" if content_changed else "No changes"
                        print(f"  [planar] {action} → {out_path.name}")
                else:
                    if apply:
                        planar_dir.mkdir(parents=True, exist_ok=True)
                        new_df.to_csv(out_path, sep="\t", index=False)
                        print(f"  [planar] Downloaded → {out_path.name}")
                    else:
                        print(f"  [planar] Would create → {out_path.name}")

    # --- Diagnostics sheet ---
    diag_id = lang_data.get("diagnostics_spreadsheet_id")
    if diag_id:
        new_df = _read_sheet_as_df(gc, diag_id)
        if new_df is not None:
            issues = _validate_diagnostics_df(new_df, lang_id)
            errors = [i for i in issues if i.level == "error"]
            if errors:
                print(f"  [diagnostics] Validation errors — skipping download:")
                for i in errors:
                    print(f"    {i}")
            else:
                for i in issues:
                    print(f"  [diagnostics] WARNING: {i}")

                diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
                if diag_path.exists():
                    old_df = pd.read_csv(diag_path, sep="\t", dtype=str).fillna("")
                    s, p = _detect_diagnostics_changes(old_df, new_df, lang_id, lang_data.get("sheets", {}))
                    safe_cmds |= s
                    pending   += p
                    content_changed = not old_df.reset_index(drop=True).equals(
                        new_df.reset_index(drop=True)
                    )
                    if apply:
                        if content_changed:
                            if timestamp:
                                archived = _archive_tsv(diag_path, timestamp)
                                print(f"  [diagnostics] Archived existing → archive/{archived.name}")
                            planar_dir.mkdir(parents=True, exist_ok=True)
                            new_df.to_csv(diag_path, sep="\t", index=False)
                            print(f"  [diagnostics] Downloaded → {diag_path.name}")
                        else:
                            print(f"  [diagnostics] No changes → {diag_path.name}")
                    else:
                        action = "Would overwrite (changed)" if content_changed else "No changes"
                        print(f"  [diagnostics] {action} → {diag_path.name}")
                elif apply:
                    planar_dir.mkdir(parents=True, exist_ok=True)
                    new_df.to_csv(diag_path, sep="\t", index=False)
                    print(f"  [diagnostics] Downloaded → {diag_path.name}")
                else:
                    print(f"  [diagnostics] Would create → {diag_path.name}")

                # --- YAML drift check ---
                # Compare the freshly-downloaded TSV against the YAML (if one exists).
                # Only ambiguous changes are returned; deterministic ones are handled by
                # sync-diagnostics-yaml --from-tsv --apply.
                ambiguous = _check_yaml_drift(lang_id, new_df)
                if ambiguous:
                    print(f"  [diagnostics] {len(ambiguous)} ambiguous YAML drift item(s) — see diagnostics_drift.json")
                    drift_entries.append({"lang_id": lang_id, "ambiguous": ambiguous})

    return safe_cmds, pending, drift_entries


def _verify_manifest_sheet_ids(drive, manifest: Dict) -> None:
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
                drive.files().get(fileId=spreadsheet_id, fields="id,trashed").execute()
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


def _check_coded_data_clean(coded_data_dir: Optional[Path] = None) -> None:
    """Abort if coded_data/ git repo has uncommitted changes to annotation TSVs.

    Protects against import-sheets overwriting local edits that have not yet
    been committed. Silently skips the check if coded_data/ is not a git repo
    (e.g. CI environments that check out the data separately).

    coded_data_dir: override path for testing (defaults to ROOT/coded_data).
    """
    coded_data = coded_data_dir or ROOT / "coded_data"
    if not (coded_data / ".git").exists():
        return
    result = subprocess.run(
        ["git", "-C", str(coded_data), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return  # git not available or not a repo; skip check
    dirty_lines = [
        line for line in result.stdout.splitlines()
        if line.strip() and line[3:].strip().endswith(".tsv")
    ]
    if dirty_lines:
        print("ERROR: coded_data/ has uncommitted changes to annotation TSVs:")
        for line in dirty_lines:
            print(f"  {line}")
        print("Commit or stash these changes before running import-sheets.")
        raise SystemExit(1)


def main() -> None:
    """Entry point for `python -m coding import-sheets`.

    Dry-run by default — pass --apply to write any TSVs. Loads the manifest
    from Drive, downloads each construction tab, validates values, and writes
    filled TSVs under coded_data/{lang_id}/{class_name}/. Compares downloaded
    content to the existing file: if changed, archives the old file and writes
    the new one; if unchanged, skips with "No changes". Pass --overwrite-existing
    to force overwrite even when content is identical.
    Writes an error report to import_errors/ if any warnings are generated.
    """
    apply = "--apply" in sys.argv
    force = "--overwrite-existing" in sys.argv
    ignore_status = "--ignore-status" in sys.argv
    lang_filter = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not apply:
        print("DRY RUN — pass --apply to write TSVs.\n")

    if apply:
        _check_coded_data_clean()

    print("Connecting to Google...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    if apply:
        _verify_manifest_sheet_ids(drive, manifest)

    total_files = 0
    in_progress_files = 0
    total_warnings = 0
    all_safe_cmds: Set[str] = set()
    all_pending: List[Dict] = []
    all_drift: List[Dict] = []
    all_collaborator_check: List[Dict] = []

    for lang_id, lang_data in manifest.items():
        if lang_filter and lang_id != lang_filter:
            continue
        print(f"\nLanguage: {lang_id}")
        lang_warning_lines: List[str] = []

        # Download planar and diagnostics Sheets to local TSVs; detect changes.
        s, p, d = _download_lang_setup_sheets(gc, lang_id, lang_data, timestamp, apply)
        all_safe_cmds |= s
        all_pending   += p
        all_drift     += d

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            status_map = _read_status_tab(ss)
            if not status_map and not ignore_status:
                print(f"    (no Status tab found — importing all constructions)")

            for construction in sheet_info["constructions"]:
                try:
                    ws = _with_retry(lambda: ss.worksheet(construction))
                except gspread.WorksheetNotFound:
                    msg = f"[{class_name}/{construction}] tab not found in sheet, skipping"
                    print(f"    WARNING: {msg}")
                    lang_warning_lines.append(f"WARNING: {msg}")
                    total_warnings += 1
                    continue

                # Determine tab status. In-progress sheets are imported for backup
                # and validation (pink highlighting), but pipeline warnings are
                # suppressed and anomalies are raised as collaborator-check rather
                # than pending-changes. --ignore-status treats all tabs as ready.
                tab_status = "ready-for-review"
                if not ignore_status and status_map:
                    tab_status = status_map.get(construction, "in-progress")
                in_progress = (tab_status != "ready-for-review")

                rows = _with_retry(ws.get_all_values)

                header = rows[0] if rows else []

                # Per-param allowed values from manifest (if present)
                construction_params = sheet_info.get("construction_params", {})
                param_values = construction_params.get(construction, {}).get("param_values")

                if class_name == "nonpermutability" and construction != "element_prescreening":
                    expected_params = (
                        [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    records, warnings, bad_cells = _validate_pair_tab(
                        rows, expected_params, construction, param_values,
                    )
                else:
                    expected_params = (
                        [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    ka = resolve_keystone_active(
                        lang_id, class_name, construction,
                        data_dir=ROOT / "coded_data" / lang_id / "lang_setup",
                    )
                    kna = resolve_keystone_na_criteria(class_name)
                    records, warnings, bad_cells = _validate_tab(
                        rows, expected_params, construction, param_values,
                        keystone_active=bool(ka),
                        keystone_na_criteria=kna,
                    )

                if bad_cells:
                    try:
                        _highlight_invalid_cells(ws, bad_cells)
                    except Exception as e:
                        print(f"    WARNING: could not highlight cells: {e}")

                # For ready-for-review tabs, surface blocking warnings (structural
                # and invalid-value). For in-progress tabs, suppress all warnings —
                # partial or invalid annotation is expected and not yet actionable.
                if not in_progress:
                    blocking_warnings = [w for w in warnings if "blank value" not in w]
                    for w in blocking_warnings:
                        print(f"    WARNING: {w}")
                        lang_warning_lines.append(f"[{class_name}/{construction}] {w}")
                    total_warnings += len(blocking_warnings)
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

                    archived = _archive_tsv(out_path, timestamp)
                    print(f"    [{construction}] Archived existing → coded_data/{lang_id}/archive/{class_name}/{archived.name}")

                _write_tsv(out_path, header, records)

                # Count rows with at least one blank param cell (for status line).
                # Pair-row sheets have no keystone; element-row sheets exclude it.
                if class_name == "nonpermutability" and construction != "element_prescreening":
                    blank_count = sum(
                        1 for r in records
                        if any(r.get(p, "") == "" for p in expected_params)
                    )
                else:
                    blank_count = sum(
                        1 for r in records
                        if r.get("Position_Name", "").lower() != "v:verbstem"
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
    if apply and (total_files > 0 or in_progress_files > 0):
        print("\nNext: commit and push coded_data/ before pushing planars:")
        print("  git -C coded_data add -A")
        print("  git -C coded_data commit -m 'data(...): ...'")
        print("  git -C coded_data push")

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
    if manifest_changed and apply:
        drive_cfg = _load_drive_config()
        file_id = drive_cfg.get("_planars_config_file_id")
        root_id = drive_cfg.get("_root_folder_id")
        new_id = _upload_planars_config(drive, manifest, root_id, file_id)
        if new_id != file_id:
            drive_cfg["_planars_config_file_id"] = new_id
            _save_drive_config(drive_cfg)
        print("manifest.json updated on Drive with languages.yaml metadata.")
    elif manifest_changed:
        print("(manifest.json has pending metadata changes — re-run with --apply to write)")

    # Write destructive changes to pending_changes.json for coordinator review.
    if all_pending:
        if apply:
            _append_pending_changes(all_pending)
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


if __name__ == "__main__":
    main()
