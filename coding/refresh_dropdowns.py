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
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import load_manifest, _load_drive_config
from .drive_backend import get_backend
from .make_forms import _read_diagnostics_for_language
from .schemas import load_diagnostic_classes
from .generate_sheets import _format_and_validate, _TRAILING_COLS


def _coreference_pair_criterion_map() -> Dict[str, str]:
    """Return {construction_name: criterion_name} for coreference pair constructions."""
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    return {
        con["name"]: con["criterion"]
        for con in (classes.get("coreference", {}).get("constructions") or [])
        if isinstance(con, dict) and "criterion" in con
    }


def _fresh_param_values(
    class_name: str,
    construction: str,
    construction_criteria: Dict[str, List[str]],
    coref_pair_map: Dict[str, str],
) -> Dict[str, List[str]]:
    """Derive fresh param_values for ONE construction from the diagnostics YAML.

    ``construction_criteria`` must be the criteria declared for this
    construction specifically. Passing a whole class's criteria here was
    issue #272: classes that declare per-construction criteria (``segmental``
    has ``aspiration_prominence`` and ``flapping``; ``phrasal_accent`` has
    ``prescreening`` and ``general``) had every construction resolved against
    the *first* one's values, so the rest fell through to a generic ``[y, n]``.
    That would have narrowed ``flapping`` from ``[y, n, both, na]`` and
    ``joint_accent`` from ``[always, sometimes, never]`` — the latter offering
    an annotator nothing but wrong answers.
    """
    # nonpermutability element_prescreening always uses [y, n, both]
    if class_name == "nonpermutability" and construction == "element_prescreening":
        return {"scopal": ["y", "n", "both"]}

    # coreference pair constructions each own a single criterion. The language
    # YAML lists all three for the whole class; diagnostic_classes.yaml is what
    # says which one belongs to this construction.
    if class_name == "coreference" and construction in coref_pair_map:
        crit = coref_pair_map[construction]
        return {crit: construction_criteria.get(crit, ["y", "n"])}

    # coreference prescreening is always referential=[y, n]
    if class_name == "coreference" and construction == "prescreening":
        return {"referential": ["y", "n"]}

    # Standard case: exactly what the YAML declares for this construction.
    return dict(construction_criteria)


def _detect_col_start(header: List[str], param_names: List[str]) -> int:
    """Return the 0-based column index where criterion columns begin."""
    for i, col in enumerate(header):
        if col in param_names:
            return i
    return 3  # fallback: standard element-row layout


def _resolve_criterion_columns(
    header: List[str],
    fresh: Dict[str, List[str]],
    class_criteria: Dict[str, List[str]],
) -> Tuple[Optional[int], List[List[str]], Optional[str]]:
    """Work out which columns get dropdowns, reading the SHEET, not the manifest.

    Returns ``(col_start, per_column_values, error)``. On any doubt it returns
    an error string and writes nothing, rather than guessing.

    This is the second half of issue #272. The old code took the *count* of
    dropdown columns from the manifest's ``param_names`` while taking their
    *start* from the header. When those disagreed — as on synth0001's
    coreference prescreening tab, whose manifest entry still listed the three
    pair criteria while the sheet had a single ``referential`` column — it
    wrote one dropdown per manifest entry starting at the header's offset, and
    ran off the end of the criteria onto ``Source`` and ``Comments``: y/n
    dropdowns on the two free-text columns an annotator writes prose in.

    The sheet's own header is authoritative for which columns exist. The
    diagnostics YAML is authoritative for what values each one allows. Neither
    job belongs to the manifest, which is bookkeeping and can go stale.
    """
    trailing = [header.index(c) for c in _TRAILING_COLS if c in header]
    end = min(trailing) if trailing else len(header)

    known = set(fresh) | set(class_criteria)
    col_start = _detect_col_start(header, known)
    if col_start >= end:
        return None, [], (
            f"no criterion columns between column {col_start} and "
            f"{_TRAILING_COLS[0] if trailing else 'end of header'}"
        )

    names = header[col_start:end]
    per_col: List[List[str]] = []
    for name in names:
        # fresh first (this construction's own criteria), then the class's —
        # a sibling construction's criterion column left behind on this tab is
        # still a real criterion and should keep its real values.
        values = fresh.get(name) or class_criteria.get(name)
        if not values:
            return None, [], (
                f"column {header.index(name)} is {name!r}, which is not a "
                f"criterion of this class — refusing to write a dropdown onto "
                f"it. Known criteria: {sorted(known)}"
            )
        per_col.append(values)
    return col_start, per_col, None


def main() -> None:
    apply = "--apply" in sys.argv
    lang_filter = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        lang_filter = sys.argv[idx + 1]

    backend = get_backend()
    manifest = load_manifest(backend)
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

        # Criteria are per (class, construction) — NOT shared across a class.
        # Keying this by class alone and letting the first construction win was
        # half of issue #272; see _fresh_param_values.
        criteria_by_construction: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
        class_criteria_union: Dict[str, Dict[str, List[str]]] = {}
        for cls, con, _crit_names, crit_values in diag_rows:
            criteria_by_construction[(cls, con)] = crit_values
            # The union is only a fallback, for naming the values of a criterion
            # column that belongs to a sibling construction of the same class.
            class_criteria_union.setdefault(cls, {}).update(crit_values)

        for class_name, sheet_info in lang_data["sheets"].items():
            spreadsheet_id = sheet_info.get("spreadsheet_id")
            if not spreadsheet_id:
                continue

            construction_params = sheet_info.get("construction_params", {})
            constructions = sheet_info.get("constructions", [])
            class_criteria = class_criteria_union.get(class_name, {})

            print(f"\n  [{lang_id}] {class_name}")

            if apply:
                try:
                    ss = backend.open_spreadsheet(spreadsheet_id)
                except Exception as e:
                    print(f"    Could not open spreadsheet: {e}")
                    continue

            manifest_updated = False

            for construction in constructions:
                if construction in ("Status",):
                    continue

                cp = construction_params.get(construction, {})
                construction_criteria = criteria_by_construction.get(
                    (class_name, construction), {})
                if not construction_criteria:
                    print(f"    {construction}: not in the diagnostics YAML — skipping")
                    continue

                fresh = _fresh_param_values(
                    class_name, construction, construction_criteria, coref_pair_map,
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
                    col_start, per_col, error = _resolve_criterion_columns(
                        header, fresh, class_criteria)
                    if error:
                        print(f"    {construction}: SKIPPED — {error}")
                        continue
                    num_rows = max(ws.row_count - 1, 1)
                    _format_and_validate(ws, num_rows, per_col, col_start=col_start)
                    written = header[col_start:col_start + len(per_col)]
                    print(f"    {construction}: refreshed {written}")

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
        # Upload updated manifest to Drive.
        #
        # This is the fourth independent "write manifest.json" implementation in
        # the codebase (docs/drive-protocol-surface.md flags it). The migration
        # routes its *transport* through the seam but deliberately preserves its
        # behaviour: no key reordering, and no create-if-missing fallback, unlike
        # drive._upload_planars_config. Collapsing the four is a separate change
        # that needs snapshots for all of them first.
        import json
        manifest_file_id = drive_config.get("_planars_config_file_id")
        if manifest_file_id:
            content = json.dumps(manifest, indent=2).encode()
            backend.update_file(manifest_file_id, content=content,
                                mimetype="application/json")
            print("\nManifest updated on Drive.")
        else:
            print("\n[WARNING] _planars_config_file_id not set — manifest not uploaded.")

    print("\nDone.")
