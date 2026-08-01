#!/usr/bin/env python3
"""Generate Google Sheets annotation forms from planar structure and diagnostics.

Run from the repo root:
    python -m coding generate-sheets                    # dry run — report what would be created
    python -m coding generate-sheets --apply             # create sheets for new classes only
    python -m coding generate-sheets --apply --force     # blocked with a hard error if annotation sheets already exist

Dry-run by default, like every other mutating command in this project (see
docs/tooling-design.md) — no Drive writes happen without --apply. On the first run
(with --apply), creates one Google Sheet per analysis class with one tab per
construction. On subsequent runs, only creates sheets for classes not yet in the
Drive manifest (e.g. a newly added aspiration class). Existing sheets are left
untouched.

To sync param column changes to existing sheets: python -m coding sync-params --apply

To regenerate a dependent pair construction after prescreening is annotated:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexivization
    python -m coding generate-sheets --lang LANG_ID --regen-construction nonpermutability:general

If position numbers have shifted since the pair tab was last generated (e.g. a position
was inserted or deleted), add --pos-remap OLD:NEW (repeatable) to carry over existing
annotations to the new row numbers:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexivization \
        --pos-remap 5:6 --pos-remap 34:35

--regen-construction ABORTS instead of writing if it would silently drop an annotated
pair-row (a retired element still had a real judgment attached) -- no confirmation step
exists after this point, the row would just be gone from the Sheet. If the element was
renamed or split, run restructure-sheets --rename-element/--split-element first (issue
#241); that carries the judgment forward and this check then passes cleanly, since the
old rows are already gone by the time --regen-construction runs. If the drop really is
intentional (e.g. a prescreening scope change, not a rename/split), add --confirm-drop:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexivization \
        --confirm-drop

Requires:
    pip install gspread google-auth google-api-python-client

Authentication (OAuth2 — recommended for personal Google accounts):
    1. In Google Cloud Console, create an OAuth2 Desktop App credential.
    2. Download the JSON and save it to PLANARS_OAUTH_CREDENTIALS path
       (default: ~/.config/planars/oauth_credentials.json).
    3. On first run a browser window opens for authorization; the token is
       cached at ~/.config/gspread/authorized_user.json for subsequent runs.

    Optional env vars:
        PLANARS_OAUTH_CREDENTIALS  path to the OAuth client-secret JSON
                                   (default: ~/.config/planars/oauth_credentials.json)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

import pandas as pd

from . import validate_planar as _val_planar
from . import validate_diagnostics as _val_diag
from .drive import (
    _check_coded_data_clean,
    _get_clients,
    _load_drive_config,
    _save_drive_config,
    _open_spreadsheet,
    _upload_planars_config,
    _download_file_json,
    _get_or_create_folder,
    _share_anyone_with_link,
    _share_with_person,
    _move_to_folder,
    _with_retry,
    _get_docs_client,
    _create_notes_doc,
    DRIVE_CONFIG_PATH,
)
from .glottolog import cached_entry as _cached_glottolog, get_metadata as _fetch_glottolog
from planars.languages import get_display_name as _get_display_name, get_entry as _get_language_entry
from planars.free_occurrence import _parse_pos_ref


def _annotator_email(lang_id: str) -> Optional[str]:
    """Return the annotator's email for lang_id from languages.yaml, or None if unset.

    Used to share annotation sheets/folders with a named person instead of
    "anyone with the link" — see _share_with_person's docstring for why.
    """
    entry = _get_language_entry(lang_id)
    if not entry:
        return None
    return entry.get("meta", {}).get("annotator_email") or None
from .schemas import load_planar_schema, load_diagnostic_classes, load_diagnostic_criteria
from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    resolve_keystone_active,
    planar_to_manifest_dict,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"

# Columns appended after param columns on every tab; no dropdown validation.
# Source of truth: schemas/planar.yaml trailing_columns.
_TRAILING_COLS = load_planar_schema().get("trailing_columns", ["Source", "Comments"])
_STATUS_TAB = "Status"
_STATUS_VALUES = ["in-progress", "ready-for-review"]
_INSTRUCTIONS_TAB = "Instructions"
_PLANAR_REF_TAB = "Planar Structure"
# System tabs always appear at the end of the sheet, in this order:
_SYSTEM_TAB_ORDER = [_PLANAR_REF_TAB, _INSTRUCTIONS_TAB, _STATUS_TAB]


def _create_or_update_tsv_sheet(
    gc: gspread.Client,
    drive,
    folder_id: str,
    name: str,
    tsv_path: Path,
    lang_id: str,
    existing_id: str = None,
) -> Tuple[str, str]:
    """Create or overwrite a Google Sheet with the contents of a TSV file.

    If existing_id is given, clears and rewrites that sheet; otherwise creates a new one,
    moves it to folder_id, and shares it with the language's annotator (if one is on
    file in languages.yaml) as a named editor.

    Returns (spreadsheet_id, url).
    """
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    all_rows = [list(df.columns)] + [list(row) for _, row in df.iterrows()]

    if existing_id:
        ss = _open_spreadsheet(gc, existing_id)
        ws = _with_retry(lambda: ss.sheet1)
        _with_retry(ws.clear)
    else:
        ss = gc.create(name)
        _move_to_folder(drive, ss.id, folder_id)
        email = _annotator_email(lang_id)
        if email:
            _share_with_person(drive, ss.id, email, role="writer")
        ws = _with_retry(lambda: ss.sheet1)

    _with_retry(lambda: ws.update(all_rows, "A1"))

    # Bold and freeze the header row.
    ss.batch_update({"requests": [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": ws.id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
    ]})

    return ss.id, ss.url


def _upload_lang_setup_as_sheets(
    gc: gspread.Client,
    drive,
    planar_dir: Path,
    lang_id: str,
    folder_id: str,
    existing_lang_data: Dict,
    force: bool = False,
) -> Dict:
    """Upload planar_*.tsv and diagnostics_{lang_id}.tsv as editable Google Sheets.

    Google Sheets is the source of truth for planar structure and diagnostics; local TSVs
    are downstream copies produced by import-sheets. This function pushes the current local
    TSV state to Sheets on initial setup, or on --force to propagate intentional edits.

    Skips a file if its sheet ID is already in existing_lang_data and force=False.

    Returns a dict with planar_spreadsheet_id/url and diagnostics_spreadsheet_id/url
    for any sheets that were created or updated (only keys present if the file exists).
    """
    result: Dict = {}

    planar_files = sorted(planar_dir.glob("planar_*.tsv"))
    if planar_files:
        planar_path = planar_files[-1]   # most recent
        existing_id = existing_lang_data.get("planar_spreadsheet_id")
        if existing_id and not force:
            print(f"  Planar sheet exists — skipping (use --force to overwrite)")
            result["planar_spreadsheet_id"]  = existing_id
            result["planar_spreadsheet_url"] = existing_lang_data.get("planar_spreadsheet_url", "")
        else:
            sheet_id, url = _create_or_update_tsv_sheet(
                gc, drive, folder_id,
                name=f"planar_{lang_id}",
                tsv_path=planar_path,
                lang_id=lang_id,
                existing_id=existing_id,
            )
            result["planar_spreadsheet_id"]  = sheet_id
            result["planar_spreadsheet_url"] = url
            action = "Updated" if existing_id else "Created"
            print(f"  {action} planar sheet: {url}")

    diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
    if diag_path.exists():
        existing_id = existing_lang_data.get("diagnostics_spreadsheet_id")
        if existing_id and not force:
            print(f"  Diagnostics sheet exists — skipping (use --force to overwrite)")
            result["diagnostics_spreadsheet_id"]  = existing_id
            result["diagnostics_spreadsheet_url"] = existing_lang_data.get("diagnostics_spreadsheet_url", "")
        else:
            sheet_id, url = _create_or_update_tsv_sheet(
                gc, drive, folder_id,
                name=f"diagnostics_{lang_id}",
                tsv_path=diag_path,
                lang_id=lang_id,
                existing_id=existing_id,
            )
            result["diagnostics_spreadsheet_id"]  = sheet_id
            result["diagnostics_spreadsheet_url"] = url
            action = "Updated" if existing_id else "Created"
            print(f"  {action} diagnostics sheet: {url}")

    return result


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def _build_rows(
    element_index, lang_id: str, param_names: List[str], keystone_active: bool = False
) -> List[List[object]]:
    """Build sorted data rows for a sheet tab.

    Rows are sorted by (position_number, element_name) so annotators see the
    planar structure in order. Elements with leading/trailing hyphens are wrapped
    in brackets to prevent Excel/Sheets from interpreting them as formulas.
    Keystone (v:verbstem) rows get 'NA' in all param columns when keystone_active
    is False (default); when True they get '' so annotators fill in real values.

    Args:
        element_index: ElementIndex from build_element_index.
        lang_id: language ID to filter the index.
        param_names: ordered list of criterion column names.
        keystone_active: if True, keystone rows start blank like all other rows.

    Returns:
        List of rows (without the header), each a list:
        [element, position_name, position_number, *criterion_values].
    """
    items = [
        (pos, element, pos_name)
        for _, (pos, pos_name, lang, element) in element_index.items()
        if lang == lang_id
    ]
    items_sorted = sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))

    rows = []
    for pos, element, pos_name in items_sorted:
        element = element.strip()
        # Wrap hyphen-prefixed/suffixed elements to prevent Sheets formula parsing.
        if element.startswith("-") or element.endswith("-"):
            element = f"[{element}]"
        if pos_name.strip().lower() == "v:verbstem" and not keystone_active:
            rows.append([element, pos_name, pos] + ["NA"] * len(param_names))
        else:
            rows.append([element, pos_name, pos] + [""] * len(param_names))
    return rows


# ---------------------------------------------------------------------------
# Free occurrence pre-filling
# ---------------------------------------------------------------------------

def _prefill_free_occurrence_rows(
    rows: List[List[object]],
    param_names: List[str],
    lang_id: str,
) -> List[List[object]]:
    """Pre-fill free_occurrence rows from the noninterruption TSV.

    Reads noninterruption/general.tsv and sets 'free' for each element. Then
    applies conditional na values so annotators only fill in the columns that
    are relevant to each element:
      - free=y rows: ALL annotation columns → 'na' (free elements filtered out)
      - free=n rows: ALL annotation columns left blank for annotators
      - keystone row: ALL annotation columns → 'na' (self-referential anchor;
        free value still pulled from noninterruption)

    Warns if the noninterruption TSV is missing or elements are absent from it.
    """
    ni_path = CODED_DATA / lang_id / "noninterruption" / "general.tsv"

    free_map: Dict[str, str] = {}
    if ni_path.exists():
        try:
            ni_df = pd.read_csv(ni_path, sep="\t", dtype=str, keep_default_na=False)
            if "free" in ni_df.columns and "Element" in ni_df.columns:
                free_map = {
                    row["Element"]: row["free"]
                    for _, row in ni_df.iterrows()
                    if row.get("free", "") not in ("", "NA")
                }
                if not free_map:
                    print("    [WARNING] noninterruption/general.tsv exists but 'free' column is blank.")
                    print("              Annotate noninterruption first, then regenerate this sheet.")
            else:
                print("    [WARNING] noninterruption/general.tsv is missing 'free' or 'Element' column.")
                print("              free column will be left blank for manual entry.")
        except Exception as exc:
            print(f"    [WARNING] Could not read noninterruption/general.tsv: {exc}")
            print("              free column will be left blank for manual entry.")
    else:
        print("    [WARNING] noninterruption/general.tsv not found.")
        print("              Annotate noninterruption first, then regenerate this sheet.")
        print("              free column will be left blank for manual entry.")

    base = 3  # Element, Position_Name, Position_Number

    def _col(name: str):
        return base + param_names.index(name) if name in param_names else None

    free_col     = _col("free")
    left_col     = _col("left-edge-of-free-form")
    right_col    = _col("right-edge-of-free-form")
    dep_left_col = _col("dependent-on-left")
    dep_right_col = _col("dependent-on-right")

    missing: List[str] = []
    updated: List[List[object]] = []

    for row in rows:
        row = list(row)
        element  = str(row[0])
        pos_name = str(row[1]) if len(row) > 1 else ""
        is_keystone = pos_name.strip().lower() == "v:verbstem"

        if is_keystone:
            # Keystone: pull free from noninterruption ONLY if it's a real value (y/n).
            # noninterruption marks the keystone na for free (not applicable there);
            # free_occurrence needs a real y/n to compute the minimal span, so leave
            # it blank here if the noninterruption value is na or missing.
            if free_col is not None and free_map:
                ks_free = free_map.get(element, "")
                if ks_free and ks_free not in ("na", "n/a"):
                    row[free_col] = ks_free
            for col in (left_col, right_col, dep_left_col, dep_right_col):
                if col is not None:
                    row[col] = "na"
        else:
            free_val = free_map.get(element, "")
            if not free_val and free_map:
                missing.append(element)

            if free_col is not None:
                row[free_col] = free_val

            if free_val == "y":
                # Free elements: all annotation columns are na (filtered out).
                for col in (left_col, right_col, dep_left_col, dep_right_col):
                    if col is not None:
                        row[col] = "na"
            # free=n: leave all annotation columns blank for annotators.

        updated.append(row)

    if missing:
        print(f"    [WARNING] Elements not found in noninterruption TSV: {missing}")
        print("              free column left blank for those elements.")

    return updated


# ---------------------------------------------------------------------------
# Nonpermutability pair generation (Option C)
# ---------------------------------------------------------------------------

def _read_position_types(planar_path: Path, lang_id: str) -> Dict[int, str]:
    """Return {position_number: "Slot" | "Zone"} for the given language.

    Reads the Position_Type column from the planar TSV. Used by
    _build_nonperm_pairs to identify which positions permit variable ordering.
    """
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id]
    return {int(row["Position"]): row["Position_Type"] for _, row in df.iterrows()}


def _build_nonperm_pairs(  # noqa: too-many-branches
    element_index, lang_id: str, pos_type: Dict[int, str],
    keystone_active: bool = False,
) -> List[List[str]]:
    """Generate candidate variable-order element pairs (Option C algorithm).

    A pair (A, B) is included as a candidate if the planar structure permits
    either relative ordering. Pairs whose order is always fixed by structure
    are excluded.

    When keystone_active is False (default), the keystone (v:verbstem) is
    excluded from all pairs. When True, the keystone is included so that its
    variable ordering relative to other elements (e.g. verb–adverb permutation)
    can be annotated.

    Inclusion rules:
    - INCLUDE if A and B share a Zone position (within-zone permutation).
    - EXCLUDE if all of A's positions are strictly before all of B's, or vice versa.
    - EXCLUDE if A and B occupy exactly the same Slot position(s) only (same slot,
      fixed co-occurrence order by convention).
    - INCLUDE otherwise (A's positions straddle B's, or B's straddle A's).

    Returns sorted [[Element_A, Element_B], ...] rows (no scopal — annotators fill that in).
    """
    _keystone = load_planar_schema().get("keystone_position_name", "v:verbstem")

    # Build element → set of positions. Skip keystone unless keystone_active.
    # Apply the same bracket-wrapping used when writing element_prescreening rows
    # so that pair element names are consistent with those in element_prescreening.tsv.
    def _wrap(e: str) -> str:
        return f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e

    elem_positions: Dict[str, set] = {}
    for _, (pos, pos_name, lang, element) in element_index.items():
        if lang != lang_id:
            continue
        if pos_name.strip().lower() == _keystone and not keystone_active:
            continue
        elem_positions.setdefault(_wrap(element), set()).add(pos)

    elements = sorted(elem_positions.keys())
    pairs = []
    for i, a in enumerate(elements):
        for b in elements[i + 1:]:
            pos_a = elem_positions[a]
            pos_b = elem_positions[b]
            shared = pos_a & pos_b

            # Shared Zone: variable ordering within the zone
            if any(pos_type.get(p) == "Zone" for p in shared):
                pairs.append([a, b])
                continue

            # Fixed order: all of A strictly before all of B (or vice versa)
            if max(pos_a) < min(pos_b) or max(pos_b) < min(pos_a):
                continue

            # Same Slot(s) only, no Zone, no straddling: fixed by convention
            if pos_a == pos_b and all(pos_type.get(p) == "Slot" for p in pos_a):
                continue

            # Straddling or complex overlap: variable order is structurally possible
            pairs.append([a, b])

    return pairs


def _filter_nonperm_pairs_by_prescreening(
    pairs: List[List[str]], lang_id: str
) -> List[List[str]]:
    """Filter candidate pairs by removing elements with scopal=n in element_prescreening.tsv.

    If element_prescreening.tsv does not exist, returns the full list with a note
    reminding the coordinator to annotate element_prescreening first.

    Aborts (and files a GitHub issue) if any element has divergent scopal values across
    positions — e.g. scopal=n at one position and scopal=y at another. This is an
    unresolved linguistics question; see issue #228.
    """
    prescreening_path = CODED_DATA / lang_id / "nonpermutability" / "element_prescreening.tsv"
    if not prescreening_path.exists():
        print("    [NOTE] element_prescreening.tsv not found — generating unfiltered pair list.")
        print("          Annotate element_prescreening first, then re-run generate-sheets --apply to get")
        print("          a filtered pairs sheet.")
        return pairs

    df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)

    # Guard: detect elements whose scopal values diverge across positions.
    divergent = []
    for elem, group in df.groupby("Element"):
        vals = {v.strip() for v in group["scopal"]}
        if "n" in vals and vals & {"y", "both"}:
            rows = [
                f"  {row.get('Position_Name', '?')} (pos {row.get('Position_Number', '?')}): "
                f"scopal={row['scopal'].strip() or '(blank)'}"
                for _, row in group.iterrows()
            ]
            divergent.append((elem, rows))

    if divergent:
        import subprocess as _sp
        lines = [
            f"[{lang_id}] `element_prescreening` has element(s) with divergent `scopal` values "
            f"across positions (e.g. `scopal=n` at one position, `scopal=y` or `both` at another). "
            f"Pair generation cannot proceed until this is resolved. See issue #228 for context.\n",
            "**Affected elements:**",
        ]
        for elem, rows in divergent:
            lines.append(f"\n**{elem}**")
            lines.extend(rows)
        lines += [
            "",
            "**Action required:** Decide whether `scopal` is a property of an element globally "
            "or per position, update `element_prescreening` accordingly, then re-run:",
            f"`python -m coding generate-sheets --lang {lang_id} --regen-construction nonpermutability:general`",
        ]
        body = "\n".join(lines)
        body_file = ROOT / "nonperm_scopal_conflict.tmp"
        body_file.write_text(body, encoding="utf-8")
        try:
            _sp.run(["gh", "auth", "status"], capture_output=True, check=True)
            r = _sp.run(
                ["gh", "issue", "create",
                 "--title", f"[{lang_id}] nonpermutability: element has divergent scopal values by position",
                 "--label", "diagnostics",
                 "--body-file", str(body_file)],
                capture_output=True, text=True, check=True,
            )
            print(f"   GitHub issue created: {r.stdout.strip()}")
        except Exception as exc:
            print(f"   (Could not create GitHub issue: {exc})")
        finally:
            body_file.unlink(missing_ok=True)
        raise SystemExit(
            f"  Aborting: element_prescreening for {lang_id} has elements with divergent scopal\n"
            f"  values across positions. See the GitHub issue above and issue #228 for context."
        )

    excluded = {
        row["Element"]
        for _, row in df.iterrows()
        if row.get("scopal", "").strip() == "n"
    }
    filtered = [p for p in pairs if p[0] not in excluded and p[1] not in excluded]
    print(f"    [element_prescreening] {len(excluded)} element(s) with scopal=n excluded")
    print(f"    [element_prescreening] {len(pairs)} → {len(filtered)} pairs after filtering")
    return filtered


def _build_reflex_pairs(
    element_index, lang_id: str, pos_type: Dict[int, str],
    keystone_active: bool = False,
) -> List[List[str]]:
    """Generate (Element_A, Position_A, Position_B, Direction) rows for coreference annotation.

    Returns [[elem_a, pos_a_str, pos_b_str, direction], ...]
    sorted by (pos_b_num − pos_a_num) descending (greatest forward span first).
    Position columns use combined format "N (name)" e.g. "5 (v:npsubj1)".
    Direction: 'forward' (pos_b > pos_a), 'backward' (pos_b < pos_a),
               'same' (same Zone position — antecedent and anaphor co-occur).
    Same-Slot same-position pairs are excluded.

    When keystone_active is False (default), the keystone is excluded from pairs.
    """
    _keystone = load_planar_schema().get("keystone_position_name", "v:verbstem")

    def _wrap(e: str) -> str:
        return f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e

    def _pos_str(num: int, name: str) -> str:
        return f"{num} ({name})"

    # elem → (pos_num, pos_name) using minimum position number
    elem_pos: Dict[str, Tuple[int, str]] = {}
    # all positions in this language: pos_num → pos_name
    all_pos: Dict[int, str] = {}

    for _, (pos, pos_name, lang, element) in element_index.items():
        if lang != lang_id:
            continue
        if pos_name.strip().lower() == _keystone and not keystone_active:
            continue
        e = _wrap(element)
        if e not in elem_pos or pos < elem_pos[e][0]:
            elem_pos[e] = (pos, pos_name)
        all_pos[pos] = pos_name

    rows = []  # each: [elem_a, pos_a_str, pos_b_str, direction, sort_key]

    for elem_a, (pos_a_num, pos_a_name) in sorted(elem_pos.items()):
        pos_a_str = _pos_str(pos_a_num, pos_a_name)

        for pos_b_num in sorted(all_pos):
            pos_b_name = all_pos[pos_b_num]
            pos_b_str  = _pos_str(pos_b_num, pos_b_name)

            if pos_a_num == pos_b_num:
                if pos_type.get(pos_a_num) == "Zone":
                    rows.append([elem_a, pos_a_str, pos_b_str, "same", 0])
                # Same Slot position: skip (elements cannot co-occur).
                continue

            direction = "forward" if pos_b_num > pos_a_num else "backward"
            rows.append([elem_a, pos_a_str, pos_b_str, direction,
                         pos_b_num - pos_a_num])

    rows.sort(key=lambda r: r[4], reverse=True)
    return [r[:4] for r in rows]


def _filter_reflex_pairs_by_prescreening(
    pairs: List[List[str]], lang_id: str
) -> List[List[str]]:
    """Filter candidate pairs using prescreening annotations.

    Reads prescreening.tsv from the coreference class directory.
    If the file does not exist, returns empty list with instructions.
    Each pair is [Element_A, Position_A, Position_B, Direction].

    Removes rows where:
      - Element_A has referential=n (cannot serve as binder), or
      - Position_B has no referential=y elements (no potential anaphor at that position).
    """
    prescreening_path = CODED_DATA / lang_id / "coreference" / "prescreening.tsv"
    if not prescreening_path.exists():
        print("    [NOTE] prescreening.tsv not found — pair tab left blank.")
        print("          Annotate prescreening first, then re-run:")
        print(f"          python -m coding generate-sheets --lang {lang_id} "
              "--regen-construction coreference:<construction>")
        return []

    df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)

    excluded_elements: set = {
        row["Element"]
        for _, row in df.iterrows()
        if row.get("referential", "").strip() == "n"
    }
    referential_positions: set = set()
    for _, row in df.iterrows():
        if row.get("referential", "").strip() == "y":
            try:
                referential_positions.add(int(row["Position_Number"]))
            except (ValueError, KeyError):
                pass

    def _pos_num(pos_str: str) -> int:
        return int(pos_str.split()[0])

    # p[0] = Element_A, p[2] = Position_B (combined "N (name)" string)
    filtered = [
        p for p in pairs
        if p[0] not in excluded_elements
        and _pos_num(p[2]) in referential_positions
    ]
    print(f"    [prescreening] {len(excluded_elements)} element(s) excluded")
    print(f"    [prescreening] {len(pairs)} → {len(filtered)} pairs after filtering")
    return filtered


# ---------------------------------------------------------------------------
# Phrasal accent pair generation (issue #237 — two-tier obligatory-core compromise)
# ---------------------------------------------------------------------------

# Coordinator-confirmed "obligatory positions" list — issue #237's tier-2 fallback,
# used for any position that falls OUTSIDE the free_occurrence-derived obligatory
# core (see _phrasal_accent_obligatory_core). Every other non-keystone Slot is
# treated as potentially absent when deciding whether two accent-eligible elements
# can become linearly adjacent.
#
# THIS IS A FIRST GUESS, NOT A VALIDATED COORDINATOR DECISION. It is lifted
# directly from issue #237's original tentative example set ("verbstem, subject,
# maybe verb inflection") and is expected to need per-language correction as real
# phrasal_accent data comes back. Edit freely — this constant is deliberately kept
# separate from the adjacency logic below so it can be adjusted without needing to
# understand the rest of the algorithm. v:verbstem is included trivially (the
# keystone is always present by definition); v:npsubj1 (subject) is the other
# member of the original tentative list.
_OBLIGATORY_POSITIONS_DEFAULT = {"v:verbstem", "v:npsubj1"}
_OBLIGATORY_POSITIONS_DEFAULT_NORM = {p.strip().lower() for p in _OBLIGATORY_POSITIONS_DEFAULT}


def _phrasal_accent_obligatory_core(lang_id: str, keystone_pos: int) -> Tuple[int, int]:
    """Return the (left, right) Position_Number range of the obligatory core.

    Tier 1 of issue #237's adjacency algorithm: reuses free_occurrence's minimal
    free-occurrence span logic (planars/free_occurrence.py lines ~114-140) rather
    than reimplementing it. For a bound keystone (free=n), the positions it
    structurally depends on (dependent-on-left/dependent-on-right) are exactly the
    positions that must be present whenever the keystone is realized — i.e. they
    can never be dropped, so they always block adjacency between elements on
    either side of them. That set is already annotated (no new annotation burden)
    once free_occurrence/general.tsv exists.

    Falls back to the keystone position alone (a trivial single-position "core")
    when free_occurrence/general.tsv doesn't exist yet, the keystone row is
    missing, or the keystone is free (free=y, i.e. no structural dependents) —
    in all of these cases tier 2 (_OBLIGATORY_POSITIONS_DEFAULT) does all the
    obligatory-position work outside the keystone itself.
    """
    fo_path = CODED_DATA / lang_id / "free_occurrence" / "general.tsv"
    if not fo_path.exists():
        return (keystone_pos, keystone_pos)

    try:
        df = pd.read_csv(fo_path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return (keystone_pos, keystone_pos)

    if "Position_Name" not in df.columns:
        return (keystone_pos, keystone_pos)

    _keystone = load_planar_schema().get("keystone_position_name", "v:verbstem")
    ks_rows = df[df["Position_Name"].str.strip().str.lower() == _keystone]
    if ks_rows.empty:
        return (keystone_pos, keystone_pos)
    ks_row = ks_rows.iloc[0]

    if ks_row.get("free", "").strip() != "n":
        # free=y, blank, na, or unannotated: no structural dependents to seed
        # the core with — tier 2 handles everything outside the keystone itself.
        return (keystone_pos, keystone_pos)

    dep_l = _parse_pos_ref(ks_row.get("dependent-on-left", ""))
    dep_r = _parse_pos_ref(ks_row.get("dependent-on-right", ""))
    left  = dep_l if dep_l is not None else keystone_pos
    right = dep_r if dep_r is not None else keystone_pos
    return (min(left, keystone_pos), max(right, keystone_pos))


def _phrasal_accent_obligatory_positions(
    lang_id: str, keystone_pos: int, all_positions: Dict[int, str],
) -> Set[int]:
    """Union tier-1 (obligatory core) and tier-2 (coordinator list) obligatory positions.

    A position is obligatory (can never be dropped, so it always blocks adjacency
    between elements on either side of it) if EITHER:
      - it falls inside the free_occurrence-derived obligatory core, or
      - its Position_Name is in _OBLIGATORY_POSITIONS_DEFAULT.
    """
    core_lo, core_hi = _phrasal_accent_obligatory_core(lang_id, keystone_pos)
    obligatory = {p for p in all_positions if core_lo <= p <= core_hi}
    for pos_num, pos_name in all_positions.items():
        if pos_name.strip().lower() in _OBLIGATORY_POSITIONS_DEFAULT_NORM:
            obligatory.add(pos_num)
    return obligatory


def _build_phrasal_accent_pairs(
    element_index, lang_id: str, pos_type: Dict[int, str],
    keystone_active: bool = False,
) -> List[List[str]]:
    """Generate candidate joint_accent element pairs for phrasal_accent's `general` tab.

    Candidates are accent-eligible elements (accented=y or both in
    phrasal_accent/prescreening.tsv) restricted to pairs that can become linearly
    adjacent once optional intervening material is absent — issue #237's two-tier
    "obligatory core" compromise:

      Tier 1 (near the keystone): _phrasal_accent_obligatory_core reuses
        free_occurrence's already-annotated dependent-on-left/dependent-on-right
        data for a bound keystone to find the obligatory core — the contiguous
        Position_Number range the keystone structurally requires in order to be
        uttered at all. Every position inside that range is obligatory.

      Tier 2 (outside the core): _OBLIGATORY_POSITIONS_DEFAULT, a
        coordinator-confirmed starting list of positions treated as always
        present. Every other non-keystone Slot is treated as potentially absent.

    Two elements are a candidate pair if no obligatory position (by either tier)
    falls strictly between their Position_Numbers, OR they share a Zone position
    (co-occurring elements can be linearly adjacent to each other within the
    zone). Same-Slot pairs are excluded — elements at the same Slot are
    alternatives, never co-occurring, so "adjacent" is undefined for them.

    Unlike nonpermutability's structural pair list (meaningful even before
    prescreening is annotated), the accent-eligible/ineligible distinction here
    is not a narrowing filter on an otherwise-valid set — without it there is no
    way to know which elements are even pairing candidates. So if
    phrasal_accent/prescreening.tsv does not exist yet, this prints a note and
    returns [] (mirroring _filter_reflex_pairs_by_prescreening's behavior)
    rather than generating an unfiltered (and here, meaningless) pair list.

    Does NOT implement corrective-accent exclusion — that's an annotation-time
    instruction to the annotator (see the class's sheet_instructions in
    diagnostic_classes.yaml), not a property of which structural pairs exist.

    Returns sorted [[Element_A, Element_B], ...] rows (no joint_accent —
    annotators fill that in).
    """
    _keystone = load_planar_schema().get("keystone_position_name", "v:verbstem")

    prescreening_path = CODED_DATA / lang_id / "phrasal_accent" / "prescreening.tsv"
    if not prescreening_path.exists():
        print("    [NOTE] phrasal_accent/prescreening.tsv not found — pair tab left blank.")
        print("          Annotate prescreening first, then re-run:")
        print(f"          python -m coding generate-sheets --lang {lang_id} "
              "--regen-construction phrasal_accent:general")
        return []

    presc_df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)
    eligible_elements = {
        row["Element"]
        for _, row in presc_df.iterrows()
        if row.get("accented", "").strip() in ("y", "both")
    }

    def _wrap(e: str) -> str:
        return f"[{e}]" if (e.startswith("-") or e.endswith("-")) else e

    # element -> set of positions, accent-eligible elements only. all_positions
    # covers every position in the language's planar structure regardless of
    # eligibility — needed to compute the obligatory-position set, since a
    # position occupied only by ineligible elements can still block adjacency.
    elem_positions: Dict[str, set] = {}
    all_positions: Dict[int, str] = {}
    keystone_pos: Optional[int] = None

    for _, (pos, pos_name, lang, element) in element_index.items():
        if lang != lang_id:
            continue
        all_positions[pos] = pos_name
        if pos_name.strip().lower() == _keystone:
            keystone_pos = pos
            if not keystone_active:
                continue
        wrapped = _wrap(element)
        if wrapped in eligible_elements:
            elem_positions.setdefault(wrapped, set()).add(pos)

    if keystone_pos is None:
        print(f"    [WARNING] No {_keystone} position found for {lang_id}; "
              "cannot compute the obligatory core.")
        return []

    obligatory = _phrasal_accent_obligatory_positions(lang_id, keystone_pos, all_positions)

    def _adjacent(pos_a: int, pos_b: int) -> bool:
        if pos_a == pos_b:
            return pos_type.get(pos_a) == "Zone"
        lo, hi = min(pos_a, pos_b), max(pos_a, pos_b)
        return not any(lo < p < hi for p in obligatory)

    elements = sorted(elem_positions.keys())
    pairs = []
    for i, a in enumerate(elements):
        for b in elements[i + 1:]:
            if any(_adjacent(pa, pb) for pa in elem_positions[a] for pb in elem_positions[b]):
                pairs.append([a, b])

    print(f"    [prescreening] {len(eligible_elements)} accent-eligible element(s)")
    print(f"    [obligatory core] {_keystone} core positions "
          f"{_phrasal_accent_obligatory_core(lang_id, keystone_pos)}")
    print(f"    [adjacency] {len(pairs)} candidate pairs")
    return pairs


def _populate_tab_pairs(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    pairs: List[List[str]],
    prefill: Optional[Dict[Tuple[str, str], Dict[str, str]]] = None,
) -> gspread.Worksheet:
    """Create or clear a worksheet tab and populate it with pair rows.

    Like _populate_tab() but for the nonpermutability pair-row format:
    columns are Element_A, Element_B, then criterion columns, then trailing
    columns. No Position_Name, Position_Number, or keystone row.

    Args:
        spreadsheet:  the parent gspread Spreadsheet.
        tab_name:     worksheet title to create or clear.
        param_names:  ordered list of criterion column names (e.g. ["scopal"]).
        param_values: dict mapping criterion name to list of allowed values.
        pairs:        candidate pair rows from _build_nonperm_pairs (no header).
        prefill:      optional {(Element_A, Element_B): {col: val}} dict; when
                      provided, retained pairs are pre-filled with existing values.

    Returns:
        The populated gspread Worksheet.
    """
    num_cols = 2 + len(param_names) + len(_TRAILING_COLS)  # Element_A, Element_B, params, trailing
    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(tab_name))
        _reset_worksheet(ws, len(pairs), num_cols)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(pairs) + 2, cols=num_cols
        )

    all_cols = param_names + _TRAILING_COLS
    header = ["Element_A", "Element_B"] + all_cols
    data_rows = []
    for pair in pairs:
        a, b = pair[0], pair[1]
        pre = (prefill or {}).get((a, b), {})
        data_rows.append([a, b] + [pre.get(c, "") for c in all_cols])
    ws.update([header] + data_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    # Param columns start at index 2 (after Element_A, Element_B)
    _format_and_validate(ws, len(pairs), per_col_values, col_start=2)
    return ws


def _populate_tab_reflex_pairs(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    pairs: List[List[str]],
    prefill: Optional[Dict] = None,
) -> gspread.Worksheet:
    """Create or clear a worksheet tab and populate it with coreference pair rows.

    Column format: Element_A, Position_A, Position_B, Direction,
    then criterion columns, then trailing columns.
    Position columns use combined "N (name)" format; Direction is structural.

    Args:
        prefill: {(elem_a, pos_b_str, direction): {col: val}} — annotations
                 keyed by (Element_A, Position_B, Direction) to carry over when
                 regenerating an existing tab.
    """
    _REFLEX_STRUCT = ["Element_A", "Position_A", "Position_B", "Direction"]
    num_cols = len(_REFLEX_STRUCT) + len(param_names) + len(_TRAILING_COLS)
    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(tab_name))
        _reset_worksheet(ws, len(pairs), num_cols)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(pairs) + 2, cols=num_cols
        )

    all_cols = param_names + _TRAILING_COLS
    header = _REFLEX_STRUCT + all_cols
    data_rows = []
    for pair in pairs:
        elem_a, pos_a, pos_b, direction = pair
        pre = (prefill or {}).get((elem_a, pos_b, direction), {})
        data_rows.append([elem_a, pos_a, pos_b, direction]
                         + [pre.get(c, "") for c in all_cols])
    ws.update([header] + data_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    # Param columns start at index 4 (after the 4 structural columns).
    _format_and_validate(ws, len(pairs), per_col_values, col_start=4)
    return ws


# ---------------------------------------------------------------------------
# Instructions tab (for classes with dependent constructions)
# ---------------------------------------------------------------------------

def _maybe_create_instructions_tab(
    spreadsheet: gspread.Spreadsheet,
    class_name: str,
) -> None:
    """Add an Instructions tab if the class has any construction with depends_on."""
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    class_entry = classes.get(class_name, {})
    constructions_schema = class_entry.get("constructions", [])
    if not any(c.get("depends_on") for c in constructions_schema):
        return
    _create_instructions_tab(spreadsheet, class_entry, constructions_schema)


def _create_instructions_tab(
    spreadsheet: gspread.Spreadsheet,
    class_entry: dict,
    constructions_schema: list,
) -> None:
    """Create a read-only Instructions tab explaining the multi-stage annotation workflow."""
    display_name = class_entry.get("display_name", class_entry.get("name", "")).upper()
    sheet_instructions = class_entry.get("sheet_instructions", "").strip()

    rows: List[List[str]] = []
    rows.append([f"{display_name} — ANNOTATION INSTRUCTIONS"])
    rows.append([""])

    # Generic dependency-order section
    step = 1
    for c in constructions_schema:
        name = c.get("name", "")
        depends_on = c.get("depends_on")
        row_type = c.get("row_type", "element")

        rows.append([f"STEP {step} — {name}"])
        if row_type == "pair_rows" and depends_on:
            rows.append([f"  This tab is generated after {depends_on} is imported."])
            rows.append([f"  Do NOT annotate it until the coordinator confirms regeneration is complete."])
        else:
            rows.append([f"  Annotate each element row in this tab."])
            if depends_on is None and any(cc.get("depends_on") == name for cc in constructions_schema):
                rows.append([f"  When finished: mark '{name}' as 'ready-for-review' in the Status tab."])
                rows.append([f"  The coordinator will then regenerate the dependent tab."])
        rows.append([""])
        step += 1

    # Class-specific guidance from sheet_instructions field
    if sheet_instructions:
        rows.append(["DETAILS"])
        rows.append([""])
        for line in sheet_instructions.splitlines():
            rows.append([line])

    existing = {ws.title: ws for ws in _with_retry(spreadsheet.worksheets)}
    if _INSTRUCTIONS_TAB in existing:
        ws = existing[_INSTRUCTIONS_TAB]
        ws.clear()
        ws.update(rows, "A1")
    else:
        ws = spreadsheet.add_worksheet(
            title=_INSTRUCTIONS_TAB, rows=len(rows) + 2, cols=1
        )
        ws.update(rows, "A1")

    sheet_id = ws.id
    bold_rows = [0] + [i for i, r in enumerate(rows) if r and (r[0].startswith("STEP ") or r[0] == "DETAILS")]
    requests = [
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r, "endRowIndex": r + 1,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }}
        for r in bold_rows
    ] + [
        {"repeatCell": {
            "range": {"sheetId": sheet_id},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 620},
            "fields": "pixelSize",
        }},
    ]
    spreadsheet.batch_update({"requests": requests})
    print(f"    Instructions tab created")


# ---------------------------------------------------------------------------
# Planar structure reference tab
# ---------------------------------------------------------------------------

def _create_planar_reference_tab(
    spreadsheet: gspread.Spreadsheet,
    planar_path: Path,
    lang_id: str,
) -> None:
    """Create or refresh a read-only Planar Structure reference tab.

    Displays position number, name, type, and element inventory so annotators
    can look up position information without leaving the spreadsheet.
    """
    df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    df = df[df["Language_ID"] == lang_id].copy()
    df = df.sort_values("Position", key=lambda s: pd.to_numeric(s, errors="coerce"))

    header = ["Position", "Position_Name", "Position_Type", "Elements"]
    rows: List[List[str]] = [header]
    for _, row in df.iterrows():
        rows.append([
            row.get("Position", ""),
            row.get("Position_Name", ""),
            row.get("Position_Type", ""),
            row.get("Elements", ""),
        ])

    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(_PLANAR_REF_TAB))
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=_PLANAR_REF_TAB, rows=len(rows) + 2, cols=len(header) + 1
        )

    ws.update(rows, "A1")
    sheet_id = ws.id
    _with_retry(lambda: spreadsheet.batch_update({"requests": [
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
    ]}))


def _maybe_create_planar_reference_tab(
    spreadsheet: gspread.Spreadsheet,
    class_name: str,
    planar_path: Path,
    lang_id: str,
) -> bool:
    """Create a Planar Structure tab if the class opts in via diagnostic_classes.yaml.

    Returns True if the tab was created.
    """
    classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    if classes.get(class_name, {}).get("include_planar_reference_tab"):
        _create_planar_reference_tab(spreadsheet, planar_path, lang_id)
        return True
    return False


def _reorder_system_tabs(spreadsheet: gspread.Spreadsheet) -> None:
    """Reorder tabs so system tabs appear last: Planar Structure → Instructions → Status."""
    all_ws = _with_retry(lambda: spreadsheet.worksheets())
    ws_by_title = {ws.title: ws for ws in all_ws}
    non_system = [ws for ws in all_ws if ws.title not in _SYSTEM_TAB_ORDER]
    system = [ws_by_title[t] for t in _SYSTEM_TAB_ORDER if t in ws_by_title]
    ordered = non_system + system
    if [ws.title for ws in all_ws] != [ws.title for ws in ordered]:
        _with_retry(lambda: spreadsheet.reorder_worksheets(ordered))


# ---------------------------------------------------------------------------
# Status tab
# ---------------------------------------------------------------------------

def _move_status_tab_to_end(spreadsheet: gspread.Spreadsheet) -> None:
    """Ensure the Status tab is the last worksheet in the spreadsheet."""
    worksheets = _with_retry(spreadsheet.worksheets)
    if not worksheets or worksheets[-1].title == _STATUS_TAB:
        return
    status_ws = next((w for w in worksheets if w.title == _STATUS_TAB), None)
    if status_ws is None:
        return
    ordered = [w for w in worksheets if w.title != _STATUS_TAB] + [status_ws]
    spreadsheet.reorder_worksheets(ordered)


def _create_status_tab(
    spreadsheet: gspread.Spreadsheet,
    construction_names: List[str],
) -> None:
    """Add a Status tab to a spreadsheet, or update an existing one.

    The tab has two columns: Construction and Status. Each construction gets
    one row with an 'in-progress' default and a dropdown for Status.
    If the tab already exists, adds any missing construction rows and moves
    the tab to the last position.
    """
    existing = {ws.title: ws for ws in _with_retry(spreadsheet.worksheets)}

    if _STATUS_TAB in existing:
        ws = existing[_STATUS_TAB]
        rows = _with_retry(ws.get_all_values)
        current_constructions = {r[0] for r in rows[1:] if r} if len(rows) > 1 else set()
        missing = [c for c in construction_names if c not in current_constructions]
        if missing:
            ws.append_rows([[c, "in-progress"] for c in missing], value_input_option="RAW")
        _move_status_tab_to_end(spreadsheet)
        return

    ws = spreadsheet.add_worksheet(title=_STATUS_TAB, rows=len(construction_names) + 2, cols=2)
    header = [["Construction", "Status"]]
    data = [[c, "in-progress"] for c in construction_names]
    ws.update(header + data, "A1")

    sheet_id = ws.id
    num_rows = len(construction_names)
    spreadsheet.batch_update({"requests": [
        # Freeze + bold header
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        # Dropdown on Status column (col B = index 1)
        {"setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1, "endRowIndex": 1 + num_rows,
                "startColumnIndex": 1, "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in _STATUS_VALUES],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }},
    ]})
    _move_status_tab_to_end(spreadsheet)
    print(f"    Status tab created ({len(construction_names)} construction(s))")


# ---------------------------------------------------------------------------
# Sheet formatting and validation
# ---------------------------------------------------------------------------

def _reset_worksheet(ws: gspread.Worksheet, num_data_rows: int, num_cols: int) -> None:
    """Clear values, reset all cell formatting, and resize to exact dimensions.

    ws.clear() alone only erases cell values — background colors (e.g. pink
    highlights written by validate-coding) and extra rows/columns left over from
    a previously larger dataset both persist. This function fully resets the
    worksheet so the next write starts from a clean slate.
    """
    ws.clear()
    sheet_id = ws.id
    ws.spreadsheet.batch_update({"requests": [
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "rowCount": max(num_data_rows + 1, 2),
                        "columnCount": max(num_cols, 1),
                    },
                },
                "fields": "gridProperties.rowCount,gridProperties.columnCount",
            }
        },
    ]})


def _build_criterion_notes(param_names: List[str]) -> List[Optional[str]]:
    """Return one note string per criterion name, or None if not in codebook.

    Looks up each criterion in diagnostic_criteria.yaml and returns the prose
    description, whitespace-normalised. Used to populate Google Sheets header
    cell notes so annotators can hover over a column name to read its definition.
    """
    cb = load_diagnostic_criteria()
    index: Dict[str, str] = {}
    for analysis in cb.get("analyses", []):
        for crit in analysis.get("diagnostic_criteria", []):
            if isinstance(crit, dict) and "name" in crit:
                desc = crit.get("description", "").strip()
                if desc:
                    index[crit["name"]] = " ".join(desc.split())
    return [index.get(p) for p in param_names]


def _format_and_validate(
    worksheet: gspread.Worksheet,
    num_data_rows: int,
    param_values: List[List[str]],
    col_start: int = 3,
    param_notes: Optional[List[Optional[str]]] = None,
) -> None:
    """Freeze and bold the header row; apply per-column dropdown validation and notes.

    Sends a single batch_update to the Sheets API containing:
    - a freeze request for the header row
    - a bold request for the header row
    - one dropdown validation rule per param column
    - one header-cell note per param column (if param_notes is provided)

    Validation is non-strict (showCustomUi=True, strict=False) so annotators
    can also type 'NA' in keystone rows without triggering a validation error.

    Args:
        worksheet: the gspread Worksheet to format.
        num_data_rows: number of data rows (excluding header) to validate.
        param_values: list of allowed-value lists, one entry per param column,
            in the same order as the columns.
        col_start: 0-based column index where param columns begin (default 3
            for standard element-row sheets; 2 for pair-row sheets).
        param_notes: optional list of note strings (one per param column, None
            to skip a column). When provided, each note is written to the
            corresponding header cell so annotators can hover to read the
            criterion definition.
    """
    sheet_id = worksheet.id
    requests = [
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Bold header row
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {"textFormat": {"bold": True}}
                },
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
    ]
    for col_offset, values in enumerate(param_values):
        col_idx = col_start + col_offset
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + num_data_rows,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in values],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })
    if param_notes:
        for col_offset, note in enumerate(param_notes):
            if note:
                col_idx = col_start + col_offset
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1,
                        },
                        "cell": {"note": note},
                        "fields": "note",
                    }
                })
    worksheet.spreadsheet.batch_update({"requests": requests})


# ---------------------------------------------------------------------------
# Tab population
# ---------------------------------------------------------------------------

def _populate_tab(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[List[object]],
) -> gspread.Worksheet:
    """Create or clear a worksheet tab and populate it with data.

    If a tab named tab_name already exists it is cleared and rewritten;
    otherwise a new worksheet is created. Trailing columns (_TRAILING_COLS)
    are appended after the criterion columns with empty values.

    Args:
        spreadsheet: the parent gspread Spreadsheet.
        tab_name: worksheet title to create or clear.
        param_names: ordered list of criterion column names.
        param_values: dict mapping criterion name to list of allowed values.
        rows: data rows from _build_rows (no header).

    Returns:
        The populated gspread Worksheet.
    """
    num_cols = 3 + len(param_names) + len(_TRAILING_COLS)  # Element, Position_Name, Position_Number, params, trailing
    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(tab_name))
        _reset_worksheet(ws, len(rows), num_cols)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=num_cols
        )

    all_cols = param_names + _TRAILING_COLS
    header = ["Element", "Position_Name", "Position_Number"] + all_cols
    # Pad data rows with empty trailing columns (e.g. Comments).
    all_rows = [header] + [[str(v) for v in row] + [""] * len(_TRAILING_COLS) for row in rows]
    ws.update(all_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    per_col_notes = _build_criterion_notes(param_names)
    _format_and_validate(ws, len(rows), per_col_values, param_notes=per_col_notes)
    return ws


# ---------------------------------------------------------------------------
# Analysis sheet creation
# ---------------------------------------------------------------------------

def _create_analysis_sheet(
    gc: gspread.Client,
    drive,
    folder_id: str,
    lang_id: str,
    class_name: str,
    constructions: List[Tuple[str, List[str], Dict[str, List[str]]]],
    element_index,
    planar_path: Path,
) -> Dict:
    """Create a Google Sheet for one analysis class with one tab per construction."""
    sheet_title = f"{class_name}_{lang_id}"
    print(f"  Creating: {sheet_title}")

    # Guard: abort if a same-named spreadsheet already exists in the folder but is not
    # registered in the manifest.  _check_force_against_existing_sheets only fires when the
    # manifest already has an entry for this class; this check covers the case where the
    # manifest entry is absent (e.g. after prune-manifest or during debugging iterations).
    existing = drive.files().list(
        q=(
            f"'{folder_id}' in parents"
            f" and name='{sheet_title}'"
            " and mimeType='application/vnd.google-apps.spreadsheet'"
            " and trashed=false"
        ),
        fields="files(id, name)",
        pageSize=5,
    ).execute().get("files", [])
    if existing:
        ids = ", ".join(f["id"] for f in existing)
        raise SystemExit(
            f"\nERROR: A spreadsheet named \"{sheet_title}\" already exists in the Drive "
            f"folder but is not registered in the manifest for {lang_id}.\n"
            f"  Existing file ID(s): {ids}\n\n"
            f"To resolve, either:\n"
            f"  (a) Register the existing sheet: add its spreadsheet_id to the manifest, or\n"
            f"  (b) Move it to _archived/ in Drive, then re-run generate-sheets --apply\n"
        )

    spreadsheet = gc.create(sheet_title)
    _move_to_folder(drive, spreadsheet.id, folder_id)
    email = _annotator_email(lang_id)
    if email:
        _share_with_person(drive, spreadsheet.id, email, role="writer")

    default_ws = spreadsheet.sheet1
    tab_names = []

    # For nonpermutability, override element_prescreening param_values to {y, n, both}.
    # The diagnostics YAML records [y, n] for scopal (used by the pairs tab);
    # element_prescreening needs the third value so the manifest stores the right dropdown.
    if class_name == "nonpermutability":
        constructions = [
            (c, pn, {"scopal": ["y", "n", "both"]} if c == "element_prescreening" else pv)
            for c, pn, pv in constructions
        ]

    # For coreference, each construction uses a specific criterion derived from the schema
    # (diagnostic_classes.yaml constructions[].criterion). The diagnostics YAML records
    # all pair-level criteria at the class level, so we remap here per construction.
    # prescreening always uses referential=[y, n] regardless of the class criteria.
    _dc_classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    _COREFERENCE_PAIR_CRITERION = {
        con["name"]: con["criterion"]
        for con in (_dc_classes.get("coreference", {}).get("constructions") or [])
        if isinstance(con, dict) and "criterion" in con
    }
    if class_name == "coreference":
        new_constructions = []
        for c, pn, pv in constructions:
            if c == "prescreening":
                new_constructions.append((c, ["referential"], {"referential": ["y", "n"]}))
            elif c in _COREFERENCE_PAIR_CRITERION:
                crit = _COREFERENCE_PAIR_CRITERION[c]
                new_constructions.append((c, [crit], {crit: pv.get(crit, ["y", "n"])}))
            else:
                new_constructions.append((c, pn, pv))
        constructions = new_constructions

    # For phrasal_accent, apply the same defensive remap as coreference above: the
    # schema declares a `criterion` per construction (prescreening reuses metrical's
    # `accented`; general uses the new `joint_accent`, per diagnostic_classes.yaml
    # issue #237). If the language's diagnostics YAML already uses construction_criteria
    # (the recommended pattern for classes whose constructions have non-overlapping
    # criteria — see CLAUDE.md), this remap is a no-op; it only does real work if a
    # coordinator instead declared both criteria under the class-level shared `criteria`
    # key, in which case it splits them back apart per construction the same way the
    # coreference block does above.
    _PHRASAL_ACCENT_PAIR_CRITERION = {
        con["name"]: con["criterion"]
        for con in (_dc_classes.get("phrasal_accent", {}).get("constructions") or [])
        if isinstance(con, dict) and "criterion" in con
    }
    if class_name == "phrasal_accent":
        new_constructions = []
        for c, pn, pv in constructions:
            if c == "prescreening":
                new_constructions.append(
                    (c, ["accented"], {"accented": pv.get("accented", ["y", "n", "both"])})
                )
            elif c in _PHRASAL_ACCENT_PAIR_CRITERION:
                crit = _PHRASAL_ACCENT_PAIR_CRITERION[c]
                new_constructions.append(
                    (c, [crit], {crit: pv.get(crit, ["always", "sometimes", "never"])})
                )
            else:
                new_constructions.append((c, pn, pv))
        constructions = new_constructions

    for construction, param_names, param_values in constructions:
        if class_name == "nonpermutability" and construction == "element_prescreening":
            # Step 1: element-level pre-filter sheet.
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(spreadsheet, construction, param_names, param_values, rows)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "nonpermutability":
            # Step 2: candidate pair sheet (general), filtered if prescreening.tsv exists.
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            pos_type = _read_position_types(planar_path, lang_id)
            pairs = _build_nonperm_pairs(element_index, lang_id, pos_type,
                                         keystone_active=ka)
            pairs = _filter_nonperm_pairs_by_prescreening(pairs, lang_id)
            _populate_tab_pairs(spreadsheet, construction, param_names, param_values, pairs)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        elif class_name == "coreference" and construction == "prescreening":
            # Stage 1: element-level prescreening sheet.
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(spreadsheet, construction, param_names, param_values, rows)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "coreference":
            # Stage 2: pair sheet filtered by prescreening.
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            pos_type = _read_position_types(planar_path, lang_id)
            pairs = _build_reflex_pairs(element_index, lang_id, pos_type, keystone_active=ka)
            pairs = _filter_reflex_pairs_by_prescreening(pairs, lang_id)
            _populate_tab_reflex_pairs(spreadsheet, construction, param_names, param_values, pairs)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        elif class_name == "phrasal_accent" and construction == "prescreening":
            # Stage 1: element-level prescreening sheet (reuses metrical's `accented`).
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(spreadsheet, construction, param_names, param_values, rows)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "phrasal_accent":
            # Stage 2: pair sheet restricted to accent-eligible x accent-eligible
            # elements, adjacency-filtered via the two-tier obligatory-core
            # compromise (issue #237).
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            pos_type = _read_position_types(planar_path, lang_id)
            pairs = _build_phrasal_accent_pairs(element_index, lang_id, pos_type,
                                                keystone_active=ka)
            _populate_tab_pairs(spreadsheet, construction, param_names, param_values, pairs)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        else:
            ka = resolve_keystone_active(lang_id, class_name, construction,
                                         data_dir=planar_path.parent) or False
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            if class_name == "free_occurrence":
                rows = _prefill_free_occurrence_rows(rows, param_names, lang_id)
            _populate_tab(spreadsheet, construction, param_names, param_values, rows)
            tab_names.append(construction)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")

    # Remove the default empty sheet if it wasn't one of our tabs
    if default_ws.title not in tab_names:
        spreadsheet.del_worksheet(default_ws)

    # Add system tabs (Planar Structure → Instructions → Status) and reorder.
    created_ref = _maybe_create_planar_reference_tab(spreadsheet, class_name, planar_path, lang_id)
    if created_ref:
        print(f"    Tab: {_PLANAR_REF_TAB} (planar reference)")
    _maybe_create_instructions_tab(spreadsheet, class_name)
    _create_status_tab(spreadsheet, tab_names)
    _reorder_system_tabs(spreadsheet)

    # Build per-construction param_values map for the manifest
    construction_params = {
        construction: {"param_names": pn, "param_values": pv}
        for construction, pn, pv in constructions
    }

    return {
        "spreadsheet_id": spreadsheet.id,
        "url": spreadsheet.url,
        "constructions": tab_names,
        "construction_params": construction_params,
    }


# ---------------------------------------------------------------------------
# Construction regeneration (--regen-construction / --regen-dependents)
# ---------------------------------------------------------------------------

def _parse_pos_cell(cell: str) -> Optional[Tuple[int, str]]:
    """Parse a combined position cell '5 (v:npsubj1)' → (5, 'v:npsubj1').

    Returns None if the cell value does not match the expected format.
    Used for position-number remapping when the planar structure is renumbered.
    """
    m = re.match(r"^(\d+)\s+\((.+)\)\s*$", cell.strip())
    if m:
        return int(m.group(1)), m.group(2)
    return None


def _remap_coreference_prefill(
    existing: Dict[Tuple[str, str, str], Dict[str, str]],
    pos_num_remap: Dict[int, int],
    new_pairs: List[List[str]],
) -> Dict[Tuple[str, str, str], Dict[str, str]]:
    """Remap old coreference annotation keys to new keys after position renumbering.

    When the planar structure is renumbered (positions inserted/deleted), the
    combined Position_B cells in the stored annotations carry old position numbers.
    This function translates old keys (elem_a, old_pos_b_str, old_direction) to new
    keys (elem_a, new_pos_b_str, new_direction) so that prefill lookup succeeds.

    The new direction is taken from the freshly generated pair list (which has already
    computed direction from the updated position numbers), so direction is correctly
    updated even when both pos_a and pos_b shift.

    Args:
        existing:      annotation dict keyed by (Element_A, Position_B, Direction).
        pos_num_remap: {old_pos_num: new_pos_num} — typically derived from a planar diff.
        new_pairs:     freshly generated pair rows [[elem_a, pos_a_str, pos_b_str, dir], ...].

    Returns:
        New annotation dict with remapped keys.  Entries whose Position_B number is not
        in pos_num_remap are kept with their original key (safe fallback).
    """
    if not pos_num_remap:
        return existing

    # Build lookup: (elem_a, new_pos_b_num) → new_direction from generated pairs.
    pair_direction: Dict[Tuple[str, int], str] = {}
    for pair in new_pairs:
        elem_a, _pos_a_str, pos_b_str, direction = pair
        parsed = _parse_pos_cell(pos_b_str)
        if parsed:
            pair_direction[(elem_a, parsed[0])] = direction

    remapped: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for (elem_a, pos_b_str, old_direction), vals in existing.items():
        parsed = _parse_pos_cell(pos_b_str)
        if parsed is None or parsed[0] not in pos_num_remap:
            remapped[(elem_a, pos_b_str, old_direction)] = vals
            continue
        old_pos_b_num, pos_b_name = parsed
        new_pos_b_num = pos_num_remap[old_pos_b_num]
        new_pos_b_str = f"{new_pos_b_num} ({pos_b_name})"
        new_direction = pair_direction.get((elem_a, new_pos_b_num), old_direction)
        remapped[(elem_a, new_pos_b_str, new_direction)] = vals

    return remapped


def _find_annotated_drops(
    removed: Set[Tuple],
    existing: Dict[Tuple, Dict[str, str]],
    criterion_col: str,
) -> List[Tuple[Tuple, str, str, str]]:
    """Return the subset of `removed` pair-keys that carry real annotation.

    _regen_construction overwrites the live Sheet with only the newly computed
    candidate pair set -- anything in `removed` is gone from the Sheet the
    instant it runs, with no confirmation step (the later import-sheets ->
    apply-pending flow only syncs the *local TSV* to match the already-
    overwritten Sheet; it is not a gate on the original write). This is the
    check that makes that write refuse to happen when it would silently
    destroy a real judgment -- see issue #241's design discussion.

    Returns a list of (key, criterion_value, source, comments) for every
    dropped pair whose criterion column is non-blank, i.e. actually annotated
    (not just an unfilled placeholder row).
    """
    drops = []
    for key in removed:
        vals = existing.get(key, {})
        crit_val = (vals.get(criterion_col) or "").strip()
        if crit_val:
            drops.append((key, crit_val, vals.get("Source", ""), vals.get("Comments", "")))
    return drops


def _format_annotated_drop(class_name: str, key: Tuple, crit_val: str, source: str, comments: str) -> str:
    """Human-readable one-line description of a dropped annotated pair, for the abort message."""
    if class_name == "coreference":
        elem_a, pos_b, direction = key
        identity = f"{elem_a!r} -> pos_b={pos_b} ({direction})"
    else:
        elem_a, elem_b = key
        identity = f"{elem_a!r} x {elem_b!r}"
    line = f"  {identity}: {crit_val!r}"
    if source:
        line += f"; Source: {source}"
    if comments:
        line += f"; Comments: {comments}"
    return line


def _regen_construction(
    gc: gspread.Client,
    lang_id: str,
    class_name: str,
    construction_name: str,
    manifest_class_info: dict,
    pos_num_remap: Optional[Dict[int, int]] = None,
    confirm_drop: bool = False,
) -> None:
    """Regenerate a dependent construction tab in an existing spreadsheet.

    Reads the current tab content from the live Sheet so any unimported
    annotations are preserved. Retained pairs keep their existing values;
    added pairs get blank rows. Removed pairs are dropped from the Sheet by
    this call, immediately, with no further confirmation step downstream --
    if any dropped pair carries a real (non-blank) annotation, this function
    raises SystemExit instead of writing, unless confirm_drop=True (see
    issue #241: an earlier version of this function let --regen-construction
    silently destroy annotated judgments whenever an element was retired
    without --split-element having been run first; call order should never
    be a precondition for not losing data). The error lists exactly what
    would be dropped so the coordinator can either run
    restructure-sheets --split-element/--rename-element first (if the
    element was renamed or split -- this naturally clears the guard, since
    the old rows are already gone from `existing` by the time this runs) or
    re-run with confirm_drop=True (--confirm-drop on the CLI) if the drop is
    a legitimate scope change, not data loss.

    Args:
        gc:                   authenticated gspread Client.
        lang_id:              language ID (e.g. 'stan1293').
        class_name:           analysis class (e.g. 'nonpermutability').
        construction_name:    dependent construction to regenerate (e.g. 'general').
        manifest_class_info:  the sheet entry from the manifest for this class.
        pos_num_remap:        optional {old_pos_num: new_pos_num} for carrying over
                              annotations when position numbers have shifted (e.g. after
                              a position was inserted or deleted in the planar).  Pass via
                              --pos-remap old:new on the CLI.  Only applies to coreference
                              pair constructions; ignored for nonpermutability and
                              phrasal_accent.
        confirm_drop:         must be True to proceed if any dropped pair is annotated.
    """
    spreadsheet_id = manifest_class_info.get("spreadsheet_id")
    if not spreadsheet_id:
        raise SystemExit(f"  No spreadsheet_id in manifest for {lang_id}/{class_name}")
    spreadsheet = gc.open_by_key(spreadsheet_id)

    # Read existing tab annotations from the live Sheet.
    existing: Dict = {}
    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(construction_name))
        rows = _with_retry(ws.get_all_values)
        if rows and len(rows) > 1:
            hdr = rows[0]
            is_reflex_fmt = class_name == "coreference" and "Position_A" in hdr and "Element_B" not in hdr
            for row in rows[1:]:
                if is_reflex_fmt:
                    # Format: Element_A, Position_A, Position_B, Direction, ...
                    if len(row) >= 4 and row[0] and row[2]:
                        existing[(row[0], row[2], row[3])] = dict(zip(hdr[4:], row[4:]))
                else:
                    if len(row) >= 2 and row[0] and row[1]:
                        existing[(row[0], row[1])] = dict(zip(hdr[2:], row[2:]))
    except gspread.WorksheetNotFound:
        pass

    # Get param_names and param_values from the manifest.
    cp = manifest_class_info.get("construction_params", {}).get(construction_name, {})
    if class_name == "coreference":
        _dc = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
        _pair_crit = {
            con["name"]: con["criterion"]
            for con in (_dc.get("coreference", {}).get("constructions") or [])
            if isinstance(con, dict) and "criterion" in con
        }
        _default_crit = _pair_crit.get(construction_name, "reflexive_allowed")
        param_names  = cp.get("param_names",  [_default_crit])
        param_values = cp.get("param_values", {_default_crit: ["y", "n"]})
    elif class_name == "phrasal_accent":
        param_names  = cp.get("param_names",  ["joint_accent"])
        param_values = cp.get("param_values", {"joint_accent": ["always", "sometimes", "never"]})
    else:
        param_names  = cp.get("param_names",  ["scopal"])
        param_values = cp.get("param_values", {"scopal": ["y", "n"]})

    # Generate new filtered pair list.
    planar_path   = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    element_index = build_element_index(f"planar_{lang_id}.tsv", planar_path.parent)
    ka            = resolve_keystone_active(lang_id, class_name, construction_name,
                                            data_dir=planar_path.parent) or False
    pos_type = _read_position_types(planar_path, lang_id)
    if class_name == "coreference":
        pairs = _build_reflex_pairs(element_index, lang_id, pos_type, keystone_active=ka)
        pairs = _filter_reflex_pairs_by_prescreening(pairs, lang_id)
    elif class_name == "phrasal_accent":
        pairs = _build_phrasal_accent_pairs(element_index, lang_id, pos_type, keystone_active=ka)
    else:
        pairs = _build_nonperm_pairs(element_index, lang_id, pos_type, keystone_active=ka)
        pairs = _filter_nonperm_pairs_by_prescreening(pairs, lang_id)

    # For coreference pair tabs, remap old annotation keys when position numbers
    # have shifted (e.g. after a planar insertion/deletion).
    if class_name == "coreference" and pos_num_remap:
        existing = _remap_coreference_prefill(existing, pos_num_remap, pairs)

    if class_name == "coreference":
        # Key: (elem_a, pos_b_str, direction)
        new_pair_set = {(p[0], p[2], p[3]) for p in pairs}
    else:
        new_pair_set = {(p[0], p[1]) for p in pairs}
    old_pair_set = set(existing.keys())
    retained = old_pair_set & new_pair_set
    removed  = old_pair_set - new_pair_set
    added    = new_pair_set - old_pair_set

    annotated_drops = _find_annotated_drops(removed, existing, param_names[0])
    if annotated_drops and not confirm_drop:
        lines = [_format_annotated_drop(class_name, *drop) for drop in annotated_drops]
        raise SystemExit(
            f"ABORTED: regenerating {lang_id}/{class_name}/{construction_name} would "
            f"silently drop {len(annotated_drops)} annotated pair-row(s) — no confirmation "
            f"step exists after this point, they would just be gone from the Sheet:\n"
            + "\n".join(lines)
            + "\n\nIf the retired element was renamed or split, run "
              "restructure-sheets --rename-element/--split-element first — that carries "
              "the judgment forward (as a breadcrumb for splits, verbatim for renames) and "
              "this check will then pass cleanly, since the old rows will already be gone. "
              "If this drop is intentional (e.g. a real prescreening scope change, not a "
              "rename/split), re-run with --confirm-drop to proceed."
        )

    if class_name == "coreference":
        _populate_tab_reflex_pairs(spreadsheet, construction_name, param_names,
                                   param_values, pairs, prefill=existing)
    else:
        _populate_tab_pairs(spreadsheet, construction_name, param_names, param_values,
                            pairs, prefill=existing)

    print(f"    {construction_name}: {len(retained)} retained, {len(added)} added, "
          f"{len(removed)} removed")
    if removed:
        print(f"    Removed pairs will surface via import-sheets --apply → apply-pending.")


def _add_constructions_to_existing_sheet(
    gc: gspread.Client,
    spreadsheet_id: str,
    class_name: str,
    new_constructions: List[Tuple[str, List[str], Dict[str, List[str]]]],
    lang_id: str,
    element_index,
    planar_path: Path,
) -> Dict:
    """Add new construction tabs to an already-existing spreadsheet.

    Used when a class already has a sheet but new constructions have been added
    to the diagnostics YAML since the sheet was created. Applies the same
    class-specific overrides as _create_analysis_sheet.

    Returns construction_params dict for the newly added tabs only.
    """
    ss = _with_retry(lambda: gc.open_by_key(spreadsheet_id))

    # Apply class-specific overrides to new constructions.
    if class_name == "nonpermutability":
        new_constructions = [
            (c, pn, {"scopal": ["y", "n", "both"]} if c == "element_prescreening" else pv)
            for c, pn, pv in new_constructions
        ]
    if class_name == "coreference":
        _dc = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
        _pair_crit = {
            con["name"]: con["criterion"]
            for con in (_dc.get("coreference", {}).get("constructions") or [])
            if isinstance(con, dict) and "criterion" in con
        }
        updated = []
        for c, pn, pv in new_constructions:
            if c == "prescreening":
                updated.append((c, ["referential"], {"referential": ["y", "n"]}))
            elif c in _pair_crit:
                crit = _pair_crit[c]
                updated.append((c, [crit], {crit: pv.get(crit, ["y", "n"])}))
            else:
                updated.append((c, pn, pv))
        new_constructions = updated

    # Defensive remap mirroring the coreference block above — see the matching
    # comment in _create_analysis_sheet for why this is a no-op when the language
    # YAML already uses construction_criteria (issue #237).
    if class_name == "phrasal_accent":
        _dc = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
        _pair_crit = {
            con["name"]: con["criterion"]
            for con in (_dc.get("phrasal_accent", {}).get("constructions") or [])
            if isinstance(con, dict) and "criterion" in con
        }
        updated = []
        for c, pn, pv in new_constructions:
            if c == "prescreening":
                updated.append((c, ["accented"], {"accented": pv.get("accented", ["y", "n", "both"])}))
            elif c in _pair_crit:
                crit = _pair_crit[c]
                updated.append((c, [crit], {crit: pv.get(crit, ["always", "sometimes", "never"])}))
            else:
                updated.append((c, pn, pv))
        new_constructions = updated

    pos_type = _read_position_types(planar_path, lang_id)
    construction_params: Dict = {}

    for construction, param_names, param_values in new_constructions:
        ka = resolve_keystone_active(lang_id, class_name, construction,
                                     data_dir=planar_path.parent) or False
        if class_name == "nonpermutability" and construction == "element_prescreening":
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(ss, construction, param_names, param_values, rows)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "nonpermutability":
            pairs = _build_nonperm_pairs(element_index, lang_id, pos_type, keystone_active=ka)
            pairs = _filter_nonperm_pairs_by_prescreening(pairs, lang_id)
            _populate_tab_pairs(ss, construction, param_names, param_values, pairs)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        elif class_name == "coreference" and construction == "prescreening":
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(ss, construction, param_names, param_values, rows)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "coreference":
            pairs = _build_reflex_pairs(element_index, lang_id, pos_type, keystone_active=ka)
            pairs = _filter_reflex_pairs_by_prescreening(pairs, lang_id)
            _populate_tab_reflex_pairs(ss, construction, param_names, param_values, pairs)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        elif class_name == "phrasal_accent" and construction == "prescreening":
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            _populate_tab(ss, construction, param_names, param_values, rows)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")
        elif class_name == "phrasal_accent":
            pairs = _build_phrasal_accent_pairs(element_index, lang_id, pos_type,
                                                keystone_active=ka)
            _populate_tab_pairs(ss, construction, param_names, param_values, pairs)
            print(f"    Tab: {construction} ({len(pairs)} candidate pairs)")
        else:
            rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
            if class_name == "free_occurrence":
                rows = _prefill_free_occurrence_rows(rows, param_names, lang_id)
            _populate_tab(ss, construction, param_names, param_values, rows)
            print(f"    Tab: {construction} ({len(rows)} rows, {len(param_names)} params)")

        construction_params[construction] = {
            "param_names": param_names,
            "param_values": param_values,
        }

    # Refresh system tabs and reorder: constructions → Planar Structure → Instructions → Status.
    planar_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    created_ref = _maybe_create_planar_reference_tab(ss, class_name, planar_path, lang_id)
    if created_ref:
        print(f"    Tab: {_PLANAR_REF_TAB} (planar reference)")
    _maybe_create_instructions_tab(ss, class_name)
    all_ws = _with_retry(lambda: ss.worksheets())
    non_system = [t for t in [ws.title for ws in all_ws] if t not in _SYSTEM_TAB_ORDER]
    _create_status_tab(ss, non_system)
    _reorder_system_tabs(ss)

    return construction_params


def _regen_dependents_simple(gc: gspread.Client, manifest: dict) -> None:
    """Regenerate dependent constructions where the dependent TSV has no annotation data.

    Safe to automate: only fires when the dependent TSV does not exist or contains
    no annotated values. If the dependent TSV has data, skips and lets
    integrity-check flag it for manual coordinator action.
    """
    dc_classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}

    for cls_name, cls_entry in dc_classes.items():
        constructions_schema = cls_entry.get("constructions", [])
        deps = [
            (c["depends_on"], c["name"])
            for c in constructions_schema
            if c.get("depends_on") and c.get("staleness_check") == "element_set"
        ]
        if not deps:
            continue

        for lang_id in sorted(d.name for d in CODED_DATA.iterdir()
                               if d.is_dir() and not d.name.startswith(".")):
            lang_manifest = manifest.get(lang_id, {})
            cls_info = lang_manifest.get("sheets", {}).get(cls_name)
            if not cls_info:
                continue

            for source_name, dep_name in deps:
                source_path = CODED_DATA / lang_id / cls_name / f"{source_name}.tsv"
                dep_path    = CODED_DATA / lang_id / cls_name / f"{dep_name}.tsv"

                if not source_path.exists():
                    continue  # source not yet imported; nothing to do

                # Safe to auto-regenerate only when the dependent TSV does not
                # yet exist. Once the TSV exists (even with blank annotation
                # values), the row structure was deliberately generated; skip
                # to avoid overwriting it on every data-refresh run. Staleness
                # is detected separately by integrity-check → dependent-stale.
                if dep_path.exists():
                    print(f"  [{lang_id}/{cls_name}/{dep_name}] already exists — "
                          f"skipping auto-regeneration. Run:\n"
                          f"    python -m coding generate-sheets --lang {lang_id} "
                          f"--regen-construction {cls_name}:{dep_name}")
                    continue

                print(f"  [{lang_id}/{cls_name}/{dep_name}] regenerating from {source_name}…")
                try:
                    _regen_construction(gc, lang_id, cls_name, dep_name, cls_info)
                except Exception as exc:
                    print(f"  ERROR: {exc}")


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

def _plan_language_creation(
    all_classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]],
    existing_lang_data: Dict,
    force: bool,
) -> Dict:
    """Determine what generate-sheets would create/update for one language, using
    only already-fetched manifest data (existing_lang_data) -- no live Drive calls.

    This is the dry-run/--apply gate's pure-logic core (issue: generate-sheets had
    no dry-run mode at all before this, unlike every other mutating command in the
    project -- see docs/tooling-design.md's "dry-run by default" principle). Used
    both to decide whether main()'s dry-run branch has anything to report for this
    language, and to build that report.

    Returns a dict:
        needs_folder / needs_notes_doc / needs_planar_sheet / needs_diagnostics_sheet: bool
            (the latter two are True whenever force=True, matching
            _upload_lang_setup_as_sheets' own "existing_id and not force: skip" logic --
            caller further ANDs needs_diagnostics_sheet with whether a diagnostics TSV
            exists locally, since that's a local-file fact this function doesn't have)
        new_classes: sorted list of class names with no existing sheet at all
        new_constructions: {class_name: [construction, ...]} for constructions newly
            added to an EXISTING class's sheet (not counted again under new_classes)
        anything: True if any of the above would cause a write
    """
    existing_sheets = existing_lang_data.get("sheets", {})
    new_classes = sorted(c for c in all_classes if c not in existing_sheets)

    new_constructions: Dict[str, List[str]] = {}
    for cls, constructions_list in all_classes.items():
        if cls in new_classes:
            continue  # whole class is new; its constructions are covered there
        existing_cons = set(existing_sheets.get(cls, {}).get("constructions", []))
        added = [c for c, _, _ in constructions_list if c not in existing_cons]
        if added:
            new_constructions[cls] = added

    needs_folder             = not bool(existing_lang_data.get("folder_id"))
    needs_notes_doc           = not bool(existing_lang_data.get("notes_doc_id"))
    needs_planar_sheet        = force or not bool(existing_lang_data.get("planar_spreadsheet_id"))
    needs_diagnostics_sheet   = force or not bool(existing_lang_data.get("diagnostics_spreadsheet_id"))

    anything = (
        needs_folder or needs_notes_doc or needs_planar_sheet or needs_diagnostics_sheet
        or bool(new_classes) or bool(new_constructions)
    )
    return {
        "needs_folder": needs_folder,
        "needs_notes_doc": needs_notes_doc,
        "needs_planar_sheet": needs_planar_sheet,
        "needs_diagnostics_sheet": needs_diagnostics_sheet,
        "new_classes": new_classes,
        "new_constructions": new_constructions,
        "anything": anything,
    }


def _check_force_against_existing_sheets(
    lang_id: str, force: bool, existing_lang_data: Dict
) -> None:
    """Raise SystemExit if --force is attempted on a language with existing annotation sheets.

    Annotation data is irreplaceable. --force must never recreate sheets that
    already have IDs in the manifest, as that would orphan the filled sheets.
    """
    if force and existing_lang_data.get("sheets"):
        existing_sheet_classes = list(existing_lang_data["sheets"].keys())
        print(
            f"\nERROR: --force refused for {lang_id}.\n"
            f"  Existing annotation sheets: {existing_sheet_classes}\n"
            "  Destroying annotation sheets is not allowed. Annotated data is\n"
            "  irreplaceable. If you need to restructure sheets, use:\n"
            "    python -m coding restructure-sheets --apply\n"
            "  To add new classes only (no destruction), omit --force."
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding generate-sheets`.

    Dry-run by default: without --apply, reports what would be created/updated per
    language (_plan_language_creation, using only already-fetched manifest data —
    no Drive writes) and moves on. This did not exist before -- generate-sheets was
    the one mutating command in the project with no dry-run gate at all, unlike
    restructure-sheets/sync-params/update-sheets/sync-diagnostics-yaml, in direct
    tension with docs/tooling-design.md's "dry-run by default" principle. Fixed
    after an accidental live creation during a session that assumed omitting
    --apply was safe, by analogy with every other command.

    With --apply, iterates over all planar_*.tsv files in coded_data/*/lang_setup/
    and for each language:
    - Creates planar_*.tsv and diagnostics_{lang_id}.tsv as editable Google Sheets (source of
      truth). Skips files whose sheet IDs are already in the manifest unless --force.
    - Creates one annotation Google Sheet per analysis class (skipping existing ones unless
      --force). Each sheet has one tab per construction with dropdown validation.
    - Uploads the merged manifest.json manifest to Drive after each language.
    - Regenerates contributor notebooks at the end.
    """
    if "--push-manifest" in sys.argv:
        push_manifest()
        return

    # --regen-construction CLASS:CONSTRUCTION [--lang LANG_ID]
    # Regenerate a specific dependent construction tab in an existing sheet.
    # Bypasses --force protection (no new sheet is created).
    if "--regen-construction" in sys.argv:
        idx = sys.argv.index("--regen-construction")
        spec = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if ":" not in spec:
            raise SystemExit("Usage: --regen-construction CLASS_NAME:CONSTRUCTION_NAME")
        class_name, construction_name = spec.split(":", 1)
        lang_idx = sys.argv.index("--lang") if "--lang" in sys.argv else -1
        lang_filter = sys.argv[lang_idx + 1] if lang_idx >= 0 else None

        # --pos-remap OLD_NUM:NEW_NUM (repeatable) — for renumbered positions.
        pos_num_remap: Dict[int, int] = {}
        argv = sys.argv[:]
        i = 0
        while i < len(argv):
            if argv[i] == "--pos-remap" and i + 1 < len(argv):
                pair = argv[i + 1]
                if ":" not in pair:
                    raise SystemExit("--pos-remap requires 'old_num:new_num' format")
                old_s, new_s = pair.split(":", 1)
                try:
                    pos_num_remap[int(old_s.strip())] = int(new_s.strip())
                except ValueError:
                    raise SystemExit(f"--pos-remap values must be integers, got: {pair!r}")
                i += 2
            else:
                i += 1

        if pos_num_remap:
            print(f"Position number remap: {pos_num_remap}")

        confirm_drop = "--confirm-drop" in sys.argv

        print("Connecting to Google APIs...")
        gc, drive = _get_clients()
        config = _load_drive_config()
        file_id = config.get("_planars_config_file_id")
        manifest = _download_file_json(drive, file_id) if file_id else {}

        langs = [lang_filter] if lang_filter else sorted(
            d.name for d in CODED_DATA.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
        for lang_id in langs:
            cls_info = manifest.get(lang_id, {}).get("sheets", {}).get(class_name)
            if not cls_info:
                print(f"  {lang_id}/{class_name}: not in manifest — skipping")
                continue
            print(f"\n{lang_id}/{class_name}/{construction_name}")
            _regen_construction(gc, lang_id, class_name, construction_name, cls_info,
                                pos_num_remap=pos_num_remap or None, confirm_drop=confirm_drop)
        return

    # --regen-dependents
    # CI path: regenerate dependent constructions where no annotation data exists yet.
    if "--regen-dependents" in sys.argv:
        # _regen_dependents_simple reads coded_data/ (source construction TSVs
        # and the planar) as ground truth for what to regenerate. Refuse if a
        # prior step's failed auto-commit left it in a stale/reverted state —
        # see issue #248's stray-row incident, caused by exactly this gap in
        # update-sheets.
        _check_coded_data_clean(extensions=(".tsv",))
        print("Connecting to Google APIs...")
        gc, drive = _get_clients()
        config = _load_drive_config()
        file_id = config.get("_planars_config_file_id")
        manifest = _download_file_json(drive, file_id) if file_id else {}
        _regen_dependents_simple(gc, manifest)
        return

    force = "--force" in sys.argv
    apply = "--apply" in sys.argv

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    # Connect to Google once for all languages
    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    docs = _get_docs_client(gc)
    config = _load_drive_config()
    root_folder_id = config.get("_root_folder_id")

    # Load the existing merged config from Drive (if present) so we can update
    # it incrementally as each language is processed, preserving other languages.
    existing_config_file_id = config.get("_planars_config_file_id")
    if existing_config_file_id:
        try:
            merged_config: Dict = _download_file_json(drive, existing_config_file_id)
            # Back up the raw downloaded manifest before any mutations so it can
            # be used for recovery if something goes wrong during this run.
            _manifest_backup = ROOT / "manifest_backup.json"
            _manifest_backup.write_text(json.dumps(merged_config, indent=2), encoding="utf-8")
            print(f"Manifest backed up to manifest_backup.json ({len(merged_config)} language(s))")
            # If it's old-format (just folder_ids, no sheets), start fresh.
            if not any("sheets" in v for v in merged_config.values() if isinstance(v, dict)):
                merged_config = {}
        except Exception:
            merged_config = {}
    else:
        merged_config = {}

    full_manifest: Dict = {}

    for planar_file in planar_files:
        planar_dir = planar_file.parent
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        print(f"\nLanguage:    {lang_id}")
        print(f"Planar file: {planar_file.name}")

        element_index = build_element_index(planar_file.name, planar_dir)

        # Validate planar structure; warn but do not block sheet generation.
        planar_df = pd.read_csv(planar_file, sep="\t")
        planar_issues = _val_planar.validate_planar_df(planar_df)
        if planar_issues:
            print(f"  Planar validation ({len(planar_issues)} issue(s)):")
            for issue in planar_issues:
                print(f"    {issue}")

        # Validate diagnostics_{lang_id}.tsv; warn but do not block sheet generation.
        diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
        if diag_path.exists():
            diag_df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
            diag_issues = _val_diag.validate_diagnostics_df(diag_df, lang_id)
            if diag_issues:
                print(f"  Diagnostics validation ({len(diag_issues)} issue(s)):")
                for issue in diag_issues:
                    print(f"    {issue}")

        specs = _read_diagnostics_for_language(lang_id, planar_dir)

        # Group specs by class_name -> [(construction, param_names, param_values), ...]
        all_classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            all_classes.setdefault(class_name, []).append((construction, param_names, param_values))

        print(f"Classes:     {list(all_classes.keys())}")

        # Load existing data early (from the manifest already fetched above -- no
        # live call yet) so we can plan what would be created/updated before
        # touching Drive at all.
        existing_lang_data: Dict = merged_config.get(lang_id, {})
        if not existing_lang_data and lang_id in config:
            # Migration: try old-format per-language manifest file
            old_fid = config[lang_id].get("manifest_file_id")
            if old_fid:
                try:
                    existing_lang_data = _download_file_json(drive, old_fid)
                except Exception:
                    pass

        # Dry-run gate: report what would happen using only manifest/local data,
        # with no Drive writes, unless --apply is given. See docs/tooling-design.md's
        # "dry-run by default" principle -- generate-sheets previously had no such
        # gate at all, unlike every other mutating command in this project.
        diag_path_exists = diag_path.exists()
        plan = _plan_language_creation(all_classes, existing_lang_data, force)
        plan_anything = plan["anything"] or (plan["needs_diagnostics_sheet"] and diag_path_exists)
        if plan_anything and not apply:
            print("  DRY RUN — would create/update:")
            if plan["needs_folder"]:
                print(f"    Drive folder for {lang_id}")
            if plan["needs_notes_doc"]:
                print(f"    Collaborator notes doc")
            if plan["needs_planar_sheet"]:
                action = "Overwrite" if existing_lang_data.get("planar_spreadsheet_id") else "Create"
                print(f"    {action} planar sheet")
            if plan["needs_diagnostics_sheet"] and diag_path_exists:
                action = "Overwrite" if existing_lang_data.get("diagnostics_spreadsheet_id") else "Create"
                print(f"    {action} diagnostics sheet")
            if plan["new_classes"]:
                print(f"    New class sheet(s): {plan['new_classes']}")
            if plan["new_constructions"]:
                for cls, cons in plan["new_constructions"].items():
                    print(f"    New construction(s) in existing '{cls}' sheet: {cons}")
            print("  Run with --apply to make these changes.")
            continue
        if not plan_anything:
            print(f"  All classes already have sheets. Skipping {lang_id}.\n"
                  "  (use --force to regenerate)")
            continue

        # Resolve/create Drive folder.
        folder_id = existing_lang_data.get("folder_id") or _get_or_create_folder(
            drive, lang_id, parent_id=root_folder_id
        )
        email = _annotator_email(lang_id)
        if email:
            try:
                _share_with_person(drive, folder_id, email, role="reader")
            except Exception as _share_err:
                print(f"  [WARNING] Could not share folder for {lang_id}: {_share_err}")
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder:      {folder_url}")

        # Create collaborator notes doc if not already in the manifest.
        # _get_display_name reads glottolog_cache.json — run `lookup-lang <lang_id>`
        # first if the cache is empty (doc will fall back to notes_{lang_id} otherwise).
        existing_notes_doc_id = existing_lang_data.get("notes_doc_id") or config.get(lang_id, {}).get("notes_doc_id")
        if not existing_notes_doc_id:
            try:
                existing_notes_doc_id = _create_notes_doc(drive, lang_id, folder_id, _get_display_name(lang_id))
                print(f"Notes doc:   https://docs.google.com/document/d/{existing_notes_doc_id}")
            except Exception as _notes_err:
                print(f"  [WARNING] Could not create notes doc for {lang_id}: {_notes_err}")
                existing_notes_doc_id = None
        else:
            print(f"Notes doc:   (existing) https://docs.google.com/document/d/{existing_notes_doc_id}")

        # Safety check: if the manifest has no entry for this language but
        # drive_config.json shows it was previously set up (has a folder_id),
        # the manifest is almost certainly stale — not a genuinely new language.
        # Creating sheets now would produce empty sheets that overwrite annotation data.
        # Abort unless --force is explicitly passed.
        if not existing_lang_data and not force:
            established = config.get(lang_id, {})
            if established.get("folder_id"):
                raise SystemExit(
                    f"\nERROR: The Drive manifest has no entry for '{lang_id}', but "
                    f"drive_config.json records it as an established language "
                    f"(folder_id: {established['folder_id']}).\n"
                    f"This almost certainly means the manifest is stale or was accidentally "
                    f"replaced with an empty file — NOT that the sheets are genuinely new.\n"
                    f"\nCreating sheets now would produce empty sheets and destroy annotation data.\n"
                    f"\nTo recover: check manifest_backup.json (written at the start of this run)\n"
                    f"or inspect the Drive manifest directly (file id: {existing_config_file_id}).\n"
                    f"\nTo force recreation of all sheets (DESTRUCTIVE — data will be lost): "
                    f"use --force."
                )

        def _sync_language_metadata(lang_data: dict, lid: str) -> None:
            """Copy glottolog + meta blocks from languages.yaml into the Drive manifest entry.

            languages.yaml is the source of truth.  The Drive manifest carries a
            copy so the data lives near the annotation sheets.  If the language is
            not yet in languages.yaml, falls back to glottolog_cache.json and warns.

            Reads languages.yaml directly by path (not via coding.schemas cached
            loader) because lookup-lang may write a new entry earlier in the same
            session and we need the just-written state, not a cached snapshot.
            """
            import yaml as _yaml
            _lang_yaml = ROOT / "schemas" / "languages.yaml"
            _langs = {}
            if _lang_yaml.exists():
                with open(_lang_yaml, encoding="utf-8") as _f:
                    _langs = _yaml.safe_load(_f) or {}
            entry = _langs.get(lid)
            if entry:
                if "glottolog" in entry:
                    lang_data["glottolog"] = entry["glottolog"]
                if "meta" in entry:
                    lang_data["meta"] = entry["meta"]
                # Warn if key meta fields are blank — display names will be wrong
                # in Drive folders and notebooks until they are filled in.
                meta = entry.get("meta") or {}
                glottolog = entry.get("glottolog") or {}
                missing = [f for f in ("source", "author") if not meta.get(f)]
                no_name = not glottolog.get("name")
                if missing or no_name:
                    problems = (["name (run lookup-lang first)"] if no_name else []) + missing
                    print(
                        f"  [{lid}] WARNING: languages.yaml meta incomplete "
                        f"(missing: {', '.join(problems)}).\n"
                        f"    Display names may be incorrect in Drive folders and notebooks.\n"
                        f"    Fill in the meta block and commit before sharing notebooks with contributors."
                    )
            else:
                print(
                    f"  [{lid}] WARNING: not found in schemas/languages.yaml. "
                    f"Run 'python -m coding lookup-lang {lid}' before running generate-sheets."
                )
                glotto = _cached_glottolog(lid)
                if not glotto:
                    try:
                        glotto = _fetch_glottolog(lid)
                    except Exception as exc:
                        print(f"  [{lid}] WARNING: Could not fetch Glottolog metadata: {exc}")
                if glotto:
                    lang_data["glottolog"] = {
                        "name":      glotto["name"],
                        "iso639_3":  glotto["iso639_3"],
                        "family":    glotto["classification"][0]["name"] if glotto["classification"] else None,
                        "latitude":  glotto["latitude"],
                        "longitude": glotto["longitude"],
                    }

        # Upload planar and diagnostics as editable Google Sheets (source of truth).
        # Skips files whose sheet IDs are already in the manifest unless --force.
        input_sheet_info = _upload_lang_setup_as_sheets(
            gc, drive, planar_dir, lang_id, folder_id, existing_lang_data, force=force
        )

        if not force and existing_lang_data:
            existing_sheets = existing_lang_data.get("sheets", {})
            new_class_names = [c for c in all_classes if c not in existing_sheets]
            if not new_class_names:
                # Even when all classes exist, new constructions may have been added
                # to an existing class's diagnostics YAML. Add their tabs now.
                added_any = False
                for cls, constructions_list in all_classes.items():
                    existing_cls_info = existing_sheets.get(cls, {})
                    existing_cons = set(existing_cls_info.get("constructions", []))
                    new_cons = [(c, pn, pv) for c, pn, pv in constructions_list
                                if c not in existing_cons]
                    if not new_cons:
                        continue
                    added_any = True
                    print(f"  [{cls}] new construction(s): {[c for c,_,_ in new_cons]}")
                    ss_id = existing_cls_info["spreadsheet_id"]
                    _planar_path = planar_dir / f"planar_{lang_id}.tsv"
                    new_params = _add_constructions_to_existing_sheet(
                        gc, ss_id, cls, new_cons, lang_id, element_index, _planar_path,
                    )
                    existing_cls_info.setdefault("constructions", []).extend(
                        [c for c, _, _ in new_cons]
                    )
                    existing_cls_info.setdefault("construction_params", {}).update(new_params)
                    existing_lang_data["sheets"][cls] = existing_cls_info

                if not added_any:
                    print(
                        f"  All classes already have sheets. Skipping {lang_id}.\n"
                        "  (use --force to regenerate)"
                    )
                existing_lang_data["folder_id"] = folder_id
                if existing_notes_doc_id:
                    existing_lang_data["notes_doc_id"] = existing_notes_doc_id
                existing_lang_data.update(input_sheet_info)
                _sync_language_metadata(existing_lang_data, lang_id)
                config.setdefault(lang_id, {})["folder_id"] = folder_id
                if existing_notes_doc_id:
                    config[lang_id]["notes_doc_id"] = existing_notes_doc_id
                _save_drive_config(config)
                full_manifest[lang_id] = existing_lang_data
                merged_config[lang_id] = existing_lang_data
                continue
            print(f"Existing:    {list(existing_sheets.keys())}")
            print(f"New:         {new_class_names}")

        _check_force_against_existing_sheets(lang_id, force, existing_lang_data)

        classes_to_create = {
            k: v for k, v in all_classes.items()
            if k not in existing_lang_data.get("sheets", {})
        }

        # Build lang_data starting from existing data (or fresh), always include folder_id.
        lang_data: Dict = existing_lang_data or {"folder_url": folder_url, "sheets": {}}
        lang_data["folder_id"] = folder_id
        if existing_notes_doc_id:
            lang_data["notes_doc_id"] = existing_notes_doc_id
        lang_data.update(input_sheet_info)  # store planar/diagnostics spreadsheet IDs
        lang_data["planar"] = planar_to_manifest_dict(planar_file, lang_id)

        _sync_language_metadata(lang_data, lang_id)

        # Create one sheet per new analysis class
        for class_name, constructions in classes_to_create.items():
            sheet_info = _create_analysis_sheet(
                gc, drive, folder_id, lang_id, class_name, constructions, element_index,
                planar_path=planar_file,
            )
            lang_data["sheets"][class_name] = sheet_info
            print(f"    URL: {sheet_info['url']}\n")

        full_manifest[lang_id] = lang_data
        merged_config[lang_id] = lang_data

        # Upload the full merged config to Drive after each language so partial
        # progress is saved even if a later language fails.
        existing_config_file_id = _upload_planars_config(
            drive, merged_config, root_folder_id, existing_config_file_id
        )
        config["_planars_config_file_id"] = existing_config_file_id
        config.setdefault(lang_id, {})["folder_id"] = folder_id
        # Mirror planar/diagnostics sheet IDs into drive_config.json so they are
        # available locally without fetching the full manifest from Drive.
        for key in ("planar_spreadsheet_id", "planar_spreadsheet_url",
                    "diagnostics_spreadsheet_id", "diagnostics_spreadsheet_url"):
            if key in input_sheet_info:
                config[lang_id][key] = input_sheet_info[key]
        if existing_notes_doc_id:
            config[lang_id]["notes_doc_id"] = existing_notes_doc_id
        # Remove stale per-language manifest_file_id (superseded by merged config).
        config[lang_id].pop("manifest_file_id", None)
        _save_drive_config(config)
        print(f"manifest.json updated on Drive (id: {existing_config_file_id})")

    if not apply:
        print("\nRun with --apply to make these changes.")
        return

    # Upload merged config once more after the loop to capture any skipped languages
    # that were added to merged_config but didn't trigger an in-loop upload.
    final_file_id = _upload_planars_config(
        drive, merged_config, root_folder_id, existing_config_file_id
    )
    config["_planars_config_file_id"] = final_file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {final_file_id})")

    # Write local manifest with all languages (gitignored, kept for reference)
    MANIFEST_PATH.write_text(json.dumps(full_manifest, indent=2), encoding="utf-8")
    print(f"\nLocal manifest written to: {MANIFEST_PATH.name}")
    print(f"drive_config.json written.")

    print(f"\nShare each language folder with your specialist (see folder URLs above).")

    from .generate_notebooks import regenerate_notebooks
    regenerate_notebooks()


def push_manifest() -> None:
    """Upload the existing local sheets_manifest.json to Drive as merged manifest.json.

    One-time migration utility. Run with:
        python -m coding generate-sheets --push-manifest
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "sheets_manifest.json not found. Nothing to push.\n"
            "Run python -m coding generate-sheets --apply first to create sheets."
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print("Connecting to Google APIs...")
    _, drive = _get_clients()
    config = _load_drive_config()

    # Enrich manifest with folder_id from drive_config before uploading.
    merged_config: Dict = {}
    for lang_id, lang_data in manifest.items():
        entry = dict(lang_data)
        folder_url = entry.get("folder_url", "")
        folder_id = config.get(lang_id, {}).get("folder_id") or (
            folder_url.rstrip("/").rsplit("/", 1)[-1] if folder_url else ""
        )
        entry["folder_id"] = folder_id
        config.setdefault(lang_id, {})["folder_id"] = folder_id
        config[lang_id].pop("manifest_file_id", None)
        merged_config[lang_id] = entry

    root_folder_id = config.get("_root_folder_id")
    existing_file_id = config.get("_planars_config_file_id")
    file_id = _upload_planars_config(drive, merged_config, root_folder_id, existing_file_id)
    config["_planars_config_file_id"] = file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {file_id})")
    print(f"drive_config.json written.")


if __name__ == "__main__":
    if "--push-manifest" in sys.argv:
        push_manifest()
    else:
        main()
