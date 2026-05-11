"""Refresh dropdown validation on existing Google Sheets without touching data.

Use this when criterion allowed-value lists change (e.g. a new value added to
diagnostic_criteria.yaml) and existing sheets need their dropdowns updated.
Safer than restructure-sheets: no archiving, no data changes, no new URLs.

Run from the repo root:
    python -m coding refresh-dropdowns           # dry run
    python -m coding refresh-dropdowns --apply   # push updated dropdowns
    python -m coding refresh-dropdowns --lang stan1293 --apply
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import _get_clients, _load_manifest_from_drive, _save_drive_config, _load_drive_config
from .make_forms import _read_diagnostics_for_language
from .schemas import load_diagnostic_classes
from .generate_sheets import _format_and_validate


def _coreference_pair_criterion_map() -> Dict[str, str]:
    """Return {construction_name: criterion_name} for coreference pair constructions."""
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    return {
        con["name"]: con["criterion"]
        for con in (classes.get("coreference", {}).get("constructions") or [])
        if isinstance(con, dict) and "criterion" in con
    }


def _fresh_param_values(
    lang_id: str,
    class_name: str,
    construction: str,
    param_names: List[str],
    class_criteria: Dict[str, List[str]],
    coref_pair_map: Dict[str, str],
) -> Dict[str, List[str]]:
    """Derive fresh param_values for one construction from the diagnostics YAML."""
    # nonpermutability element_prescreening always uses [y, n, both]
    if class_name == "nonpermutability" and construction == "element_prescreening":
        return {"scopal": ["y", "n", "both"]}

    # coreference pair constructions each own a single criterion
    if class_name == "coreference" and construction in coref_pair_map:
        crit = coref_pair_map[construction]
        return {crit: class_criteria.get(crit, ["y", "n"])}

    # coreference prescreening is always referential=[y, n]
    if class_name == "coreference" and construction == "prescreening":
        return {"referential": ["y", "n"]}

    # Standard case
    return {p: class_criteria.get(p, ["y", "n"]) for p in param_names}


def _detect_col_start(header: List[str], param_names: List[str]) -> int:
    """Return the 0-based column index where param columns begin."""
    for i, col in enumerate(header):
        if col in param_names:
            return i
    return 3  # fallback: standard element-row layout


def main() -> None:
    apply = "--apply" in sys.argv
    lang_filter = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        lang_filter = sys.argv[idx + 1]

    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)
    drive_config = _load_drive_config()
    coref_pair_map = _coreference_pair_criterion_map()

    print(f"{'DRY RUN — ' if not apply else ''}Refreshing sheet dropdowns")
    if not apply:
        print("(run with --apply to push changes)\n")

    any_changes = False

    for lang_id, lang_data in manifest.items():
        if lang_filter and lang_id != lang_filter:
            continue
        if "sheets" not in lang_data:
            continue

        # Read fresh diagnostics for this language
        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        planar_files = list(lang_setup_dir.glob("planar_*.tsv"))
        if not planar_files:
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue
        planar_filename = planar_files[0].name

        try:
            diag_rows = _read_diagnostics_for_language(lang_id, lang_setup_dir)
        except Exception as e:
            print(f"\n[{lang_id}] Could not read diagnostics: {e} — skipping")
            continue

        # Build {class_name: criterion_values} — criteria are shared across constructions
        class_criteria_map: Dict[str, Dict[str, List[str]]] = {}
        for cls, _con, _crit_names, crit_values in diag_rows:
            if cls not in class_criteria_map:
                class_criteria_map[cls] = crit_values

        for class_name, sheet_info in lang_data["sheets"].items():
            spreadsheet_id = sheet_info.get("spreadsheet_id")
            if not spreadsheet_id:
                continue

            construction_params = sheet_info.get("construction_params", {})
            constructions = sheet_info.get("constructions", [])
            class_criteria = class_criteria_map.get(class_name, {})

            print(f"\n  [{lang_id}] {class_name}")

            if apply:
                try:
                    ss = gc.open_by_key(spreadsheet_id)
                except Exception as e:
                    print(f"    Could not open spreadsheet: {e}")
                    continue

            manifest_updated = False

            for construction in constructions:
                if construction in ("Status",):
                    continue

                cp = construction_params.get(construction, {})
                param_names: List[str] = cp.get("param_names", [])
                if not param_names:
                    print(f"    {construction}: no param_names in manifest — skipping")
                    continue

                fresh = _fresh_param_values(
                    lang_id, class_name, construction,
                    param_names, class_criteria, coref_pair_map,
                )
                stored = cp.get("param_values", {})

                changed = fresh != stored
                status = "→ would update" if changed else "up to date"
                print(f"    {construction}: {stored} {status if not changed else f'→ {fresh}'}")

                if changed:
                    any_changes = True

                if apply and changed:
                    from .drive import _with_retry
                    try:
                        ws = _with_retry(lambda c=construction: ss.worksheet(c))
                    except Exception:
                        print(f"    [{construction}] tab not found — skipping")
                        continue

                    header = _with_retry(lambda w=ws: w.row_values(1))
                    col_start = _detect_col_start(header, param_names)
                    per_col = [fresh.get(p, ["y", "n"]) for p in param_names]
                    num_rows = max(ws.row_count - 1, 1)
                    _format_and_validate(ws, num_rows, per_col, col_start=col_start)
                    print(f"    {construction}: refreshed")

                    # Update manifest's stored param_values
                    sheet_info["construction_params"][construction]["param_values"] = fresh
                    manifest_updated = True

    if not apply:
        if any_changes:
            print("\nRun with --apply to push the updated dropdowns.")
        else:
            print("\nAll dropdowns are up to date.")
        return

    if any_changes:
        # Upload updated manifest to Drive
        import json
        manifest_file_id = drive_config.get("_planars_config_file_id")
        if manifest_file_id:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            content = json.dumps(manifest, indent=2).encode()
            drive.files().update(
                fileId=manifest_file_id,
                media_body=MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json"),
            ).execute()
            print("\nManifest updated on Drive.")
        else:
            print("\n[WARNING] _planars_config_file_id not set — manifest not uploaded.")

    print("\nDone.")
