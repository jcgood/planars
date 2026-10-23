"""Make every class sheet's dropdowns match the codebook, without touching data.

Reads each sheet's real dropdowns and compares each column with its spec
(``sheet_spec.class_sheet_spec``: a criterion's allowed values from the
diagnostics YAML, no dropdown on the row columns, Example/Source/Comments, or
a criterion whose values include a placeholder such as <position_number>,
``schemas.dropdown_values``; the Status column's values on the Status tab).
A column whose dropdown differs on any data row is rewritten whole, or its
dropdown removed. Runs daily in the refresh, so a sheet can't keep offering a
list the codebook has moved past (#322: the English sheets still offered the
y/n default list removed 2026-10-12, so annotators couldn't pick both, na or
unclear, and a typed position number showed as invalid). Until 2026-10-23
this command compared the manifest's record of the values with the YAML and
never looked at the sheet; it still brings that record up to date
(integrity-check reads it), uploading the manifest through
``drive.upload_manifest``, the writer every command shares (it creates a
fresh manifest if the recorded file is lost).

``_resolve_criterion_columns`` and ``_fresh_param_values`` (#272) are also
used by update-sheets and integrity-check: which columns hold criteria comes
from the sheet's own header, what each allows from the diagnostics YAML, never
from the manifest.

Run from the repo root:
    python -m coding refresh-dropdowns           # dry run: list what differs
    python -m coding refresh-dropdowns --apply   # fix it
    python -m coding refresh-dropdowns --lang stan1293 --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import load_manifest, upload_manifest, _load_drive_config, _save_drive_config
from .drive_doorway import get_doorway
from .make_forms import _read_diagnostics_for_language
from .schemas import criteria_for
from planars.schema_values import STATUS_TAB
from .generate_sheets import dropdown_request
from .sheet_spec import STATUS, ClassSheetSpec, class_sheet_spec
from planars.schema_values import TRAILING_COLUMNS as _TRAILING_COLS


def _fresh_param_values(
    class_name: str,
    construction: str,
    construction_criteria: Dict[str, List[str]],
    lang_id: str = "",
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

    Which criterion a construction owns, and its values, come from
    ``coding.schemas.criteria_for`` — the one copy of that rule (until
    2026-10-12 this function carried its own per-class blocks).
    """
    return criteria_for(class_name, construction, list(construction_criteria),
                        construction_criteria, lang_id)[1]


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


_DROPDOWN_FIELDS = ("sheets(properties(title,sheetId,gridProperties(rowCount)),"
                    "data(rowData(values(formattedValue,dataValidation))))")


def _offered(cell: dict) -> Optional[Tuple[str, ...]]:
    """The values a cell's dropdown offers, None when it has none."""
    rule = cell.get("dataValidation")
    if not rule:
        return None
    return tuple(v.get("userEnteredValue", "")
                 for v in rule.get("condition", {}).get("values", []))


def _describe(values: Optional[Tuple[str, ...]]) -> str:
    return ", ".join(values) if values else "no dropdown"


def wrong_dropdowns(ss, spec: ClassSheetSpec) -> List[Tuple[str, dict]]:
    """Each column of ``ss`` whose dropdown differs from ``spec`` on any row
    with something in its first column: ``(message, request)``, the request
    rewriting the whole column. One read per spreadsheet."""
    meta = ss.fetch_sheet_metadata(params={"includeGridData": "true",
                                           "fields": _DROPDOWN_FIELDS})
    by_title = {t.title: t for t in spec.tabs if t.columns}
    out = []
    for sheet in meta.get("sheets", []):
        props = sheet["properties"]
        tab = by_title.get(props["title"])
        if tab is None:
            continue
        rows = (sheet.get("data") or [{}])[0].get("rowData", [])
        if len(rows) < 2:
            continue
        header = [c.get("formattedValue", "") for c in rows[0].get("values", [])]
        data = [r.get("values", []) for r in rows[1:]
                if r.get("values") and r["values"][0].get("formattedValue", "")]
        end_row = props.get("gridProperties", {}).get("rowCount", len(rows))
        for col in tab.columns:
            if col.name not in header:
                continue  # a missing or extra column is the door's and sheet-drift's to report
            c = header.index(col.name)
            seen = {_offered(r[c] if c < len(r) else {}) for r in data}
            if not seen or seen == {col.allowed}:
                continue
            now = " / ".join(sorted(_describe(v) for v in seen))
            request = dropdown_request(props["sheetId"], c, end_row, col.allowed,
                                       strict=tab.kind == STATUS)
            out.append((f"{tab.title} '{col.name}': {now} → {_describe(col.allowed)}", request))
    return out


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding refresh-dropdowns`."""
    ap = argparse.ArgumentParser(
        description="Refresh criterion dropdown validation on existing sheets."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="push updated dropdowns (default: dry run)",
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
    lang_filter = args.lang

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    drive_config = _load_drive_config()

    print(f"{'DRY RUN — ' if not apply else ''}Refreshing sheet dropdowns")
    if not apply:
        print("(run with --apply to push changes)\n")

    any_changes = False
    manifest_changed = False
    failed: List[str] = []

    for lang_id, lang_data in manifest.items():
        if lang_filter and lang_id != lang_filter:
            continue
        if "sheets" not in lang_data:
            continue

        # Read fresh diagnostics for this language
        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        if not list(lang_setup_dir.glob("planar_*.tsv")):
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue

        try:
            diag_rows = _read_diagnostics_for_language(lang_id, lang_setup_dir)
        except Exception as e:
            print(f"\n[{lang_id}] Could not read diagnostics: {e} — skipping")
            continue

        # Criteria are per (class, construction) — NOT shared across a class.
        # Keying this by class alone and letting the first construction win was
        # half of issue #272; see _fresh_param_values.
        criteria_by_construction: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
        for cls, con, _crit_names, crit_values in diag_rows:
            criteria_by_construction[(cls, con)] = crit_values

        for class_name, sheet_info in lang_data["sheets"].items():
            spreadsheet_id = sheet_info.get("spreadsheet_id")
            if not spreadsheet_id:
                continue

            print(f"\n  [{lang_id}] {class_name}")
            try:
                spec = class_sheet_spec(lang_id, class_name, CODED_DATA)
            except Exception as e:
                print(f"    No spec for this sheet ({e})")
                failed.append(f"{lang_id}/{class_name}")
                continue
            try:
                ss = doorway.open_spreadsheet(spreadsheet_id)
            except Exception as e:
                print(f"    Could not open spreadsheet: {e}")
                failed.append(f"{lang_id}/{class_name}")
                continue

            fixes = wrong_dropdowns(ss, spec)
            for message, _ in fixes:
                print(f"    {message}")
            if not fixes:
                print("    dropdowns match")
            any_changes = any_changes or bool(fixes)
            if apply and fixes:
                ss.batch_update({"requests": [request for _, request in fixes]})

            # The manifest's record of each construction's values, which
            # integrity-check compares with the YAML.
            for construction in sheet_info.get("constructions", []):
                construction_criteria = criteria_by_construction.get(
                    (class_name, construction), {})
                if construction == STATUS_TAB or not construction_criteria:
                    continue
                fresh = _fresh_param_values(
                    class_name, construction, construction_criteria, lang_id)
                cp = sheet_info.setdefault("construction_params", {}).setdefault(construction, {})
                if cp.get("param_values") != fresh:
                    manifest_changed = True
                    cp["param_values"] = fresh

    if not apply:
        if any_changes:
            print("\nRun with --apply to fix these dropdowns.")
        else:
            print("\nAll dropdowns match the codebook.")
    elif manifest_changed:
        # Upload updated manifest to Drive through the same shared writer
        # every other command uses (generate_sheets, sync_params,
        # update_sheets, import_sheets, restructure_sheets). Before this, this
        # file kept its own inline copy with no key reordering and no
        # create-if-missing fallback — a lost _planars_config_file_id meant it
        # gave up with a warning instead of creating a fresh manifest.json the
        # way every other writer does. Collapsed under issue #276.
        existing_file_id = drive_config.get("_planars_config_file_id")
        root_folder_id = drive_config.get("_root_folder_id")
        file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
        drive_config["_planars_config_file_id"] = file_id
        _save_drive_config(drive_config)
        print("\nManifest updated on Drive.")

    if failed:
        print(f"\nNot checked: {', '.join(failed)}")
        sys.exit(1)
    print("\nDone.")
