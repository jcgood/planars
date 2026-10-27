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
Drive manifest (e.g. a newly added aspiration class), and adds tabs for constructions
newly added to an existing class. Existing tabs are left untouched.

To sync param column changes to existing sheets: python -m coding sync-params --apply

To regenerate a dependent pair construction after prescreening is annotated:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexive_coreference
    python -m coding generate-sheets --lang LANG_ID --regen-construction nonpermutability:general

If position numbers have shifted since the pair tab was last generated (e.g. a position
was inserted or deleted), add --pos-remap OLD:NEW (repeatable) to carry over existing
annotations to the new row numbers:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexive_coreference \
        --pos-remap 5:6 --pos-remap 34:35

--regen-construction ABORTS instead of writing if it would silently drop an annotated
pair-row (a retired element still had a real judgment attached) -- no confirmation step
exists after this point, the row would just be gone from the Sheet. If the element was
renamed or split, run one of
    python -m coding restructure-sheets --rename-element OLD:NEW --apply
    python -m coding restructure-sheets --split-element OLD:NEW1,NEW2 --apply
first (issue #241); that carries the judgment forward and this check then passes cleanly,
since the old rows are already gone by the time --regen-construction runs. If the drop really is
intentional (e.g. a prescreening scope change, not a rename/split), add --confirm-drop:
    python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexive_coreference \
        --confirm-drop

--regen-construction rewrites the tab inside drive_door.replacing (_rebuild_tab), carrying
every answer over by the key the schema declares for the tab (planars.schema_values.row_key).
A tab whose columns are not the shape the schema gives it is refused too (its answers could
not be matched) unless --confirm-drop. --regen-construction and --regen-dependents are
separate paths from sheet creation and always act live; --apply does not gate them (their own
guards do).

Each sheet gets a Status tab (in-progress / ready-for-review dropdowns). A class that already has
a sheet but gained a construction in its diagnostics YAML gets that tab added on any --apply
run, whether or not the language also gets a brand-new class sheet.

Two-stage (pair-sheet) classes: nonpermutability (element_prescreening first, then
--regen-construction nonpermutability:general) and coreference (prescreening first, then
--regen-construction coreference:<pair construction> for each). Both prescreening filters
(scopal, referential) exclude an element by name across every position, not only the one
marked n. If an element is n at one position and y/both at another, that is an open
linguistics question (is the criterion a property of the element or of the element at a
position?), so _abort_if_criterion_diverges_by_position aborts and files or updates one
`diagnostics` GitHub issue rather than choosing a side.

--regen-dependents (run in the daily refresh) fills a dependent tab only when it has no rows to
lose: it does not exist yet, or it exists empty and its source tab is marked ready-for-review in
the Status tab. A dependent with rows is never touched (integrity-check flags it as stale
instead). It exits non-zero if any dependent failed to regenerate; the others are still tried.

Before --regen-construction overwrites a tab, the Drive door saves its current content to
coded_data/.state/regen_snapshots/ (state_files.SNAPSHOT_DIR) -- a safety net in case anything not yet downloaded via
import-sheets was lost to an interrupted run (issue #271); not something you need to act on
unless a run is actually interrupted.

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

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd
import yaml
from gspread.utils import rowcol_to_a1

from . import validate_planar as _val_planar
from . import validate_diagnostics as _val_diag
from . import biuniqueness_rows as _br
from . import people as _people
from . import issues as _issues
from . import drive_door
from .drive import (
    _load_drive_config,
    _save_drive_config,
    upload_manifest,
    create_notes_doc,
    ensure_user_permission,
)
from .drive_doorway import SpreadsheetHandle, WorksheetHandle, WorksheetNotFound, get_doorway
from .glottolog import cached_entry as _cached_glottolog, get_metadata as _fetch_glottolog
from planars.schema_values import (
    ELEMENT_ROW_COLUMNS, KEYSTONE_NAME, PAIR_ROW_KEYS, PAIR_ROW_SHAPES, STATUS_COLUMNS,
    STATUS_CONSTRUCTION_COLUMN, STATUS_PROBLEMS_COLUMN, STATUS_STATUS_COLUMN,
    STATUS_IN_PROGRESS, STATUS_READY, STATUS_TAB, STATUS_VALUES, ZONE, status_map,
    ELEMENT_ROWS, PAIR_ROWS,
    TRAILING_COLUMNS as _TRAILING_COLS, trailing_columns_for,
    header_shape, is_keystone as _is_keystone, prefill_by_label,
    row_columns, row_key, row_type, source_construction,
)
from planars.free_occurrence import bound_keystone_span
from planars.nonpermutability import is_pair_candidate


def _annotator_email(lang_id: str) -> Optional[str]:
    """Return the annotator's email for lang_id, or None if no annotator is named.

    Used to share annotation sheets/folders with a named person instead of
    "anyone with the link" — these carry unpublished research data, so access
    is restricted to named individuals rather than a link (a link is not
    access control: it can leak via a forwarded message, a public comment,
    a screenshot). The address itself lives in private planars-data; see
    `coding/people.py`.
    """
    return _people.annotator_email(lang_id)
from .schemas import (
    apply_schema_criteria, dropdown_values, load_diagnostic_classes, load_diagnostic_criteria,
    reads_from,
)
from .locked_tabs import rebuild_locked_tabs, reorder_tabs, system_tab_titles
from .make_forms import (
    build_element_index,
    category_label,
    element_rows,
    registered_labels,
    wrap_element as _wrap,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    resolve_keystone_active,
    resolve_obligatory_positions,
    planar_to_manifest_dict,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"

# Columns appended after param columns; no dropdown validation: planar.yaml's
# trailing_columns. A tab gets its language's (trailing_columns_for); every
# one that any language may have is _TRAILING_COLS.
_STATUS_TAB = STATUS_TAB
_STATUS_VALUES = STATUS_VALUES


def _create_copy_sheet(doorway, folder_id: str, lang_id: str, kind: str) -> Tuple[str, str]:
    """Create a language's planar or diagnostics Sheet (``kind``), filled from
    its source as ``sheet_spec.copy_sheet_spec`` renders it, in ``folder_id``,
    and shared with the language's annotator (if people.yaml names one) as
    ``sheet_spec.sharing_spec`` says: a reader, since the Sheet is a copy.
    Keeping it current afterwards is sync-planar's and
    sync-diagnostics-yaml's job.

    Returns (spreadsheet_id, url).
    """
    from .sheet_spec import copy_sheet_spec, sharing_spec

    tab = copy_sheet_spec(kind, lang_id, CODED_DATA).tab
    all_rows = [tab.header] + [list(r) for r in tab.rows or ()]
    identity = drive_door.lang_file(kind, lang_id)
    ss = doorway.create_spreadsheet(f"{kind.removesuffix('_sheet')}_{lang_id}",
                                    identity=identity)
    doorway.move_file(ss.id, folder_id)
    email = _annotator_email(lang_id)
    role = sharing_spec(identity).role_for(email)
    if email and role:
        doorway.create_permission(ss.id, type="user", role=role, email=email)
    ws = ss.sheet1
    ws.update(all_rows, "A1")
    from .locked_tabs import protect
    protect(ss, ws)

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
    doorway,
    planar_dir: Path,
    lang_id: str,
    folder_id: str,
    existing_lang_data: Dict,
) -> Dict:
    """Create a language's planar and diagnostics Sheets if it has none yet.

    Each is a read-only copy of its source in planars-data
    (``planar_{lang_id}.tsv``, ``diagnostics_{lang_id}.yaml``; Phase 10 unit
    11b). An existing one is left alone: sync-planar and sync-diagnostics-yaml
    keep it current, daily.

    Returns a dict with planar_spreadsheet_id/url and diagnostics_spreadsheet_id/url
    (only keys present if the source exists).
    """
    result: Dict = {}
    sources = (("planar", "planar_sheet", planar_dir / f"planar_{lang_id}.tsv"),
               ("diagnostics", "diagnostics_sheet",
                planar_dir / f"diagnostics_{lang_id}.yaml"))
    for name, kind, source in sources:
        if not source.exists():
            continue
        id_key, url_key = f"{name}_spreadsheet_id", f"{name}_spreadsheet_url"
        existing_id = existing_lang_data.get(id_key)
        if existing_id:
            result[id_key] = existing_id
            result[url_key] = existing_lang_data.get(url_key, "")
            continue
        sheet_id, url = _create_copy_sheet(doorway, folder_id, lang_id, kind)
        result[id_key], result[url_key] = sheet_id, url
        print(f"  Created {name} sheet: {url}")
    return result


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def _build_rows(
    element_index, lang_id: str, param_names: List[str], keystone_active: bool = False
) -> List[List[object]]:
    """Build sorted data rows for a sheet tab.

    Which rows, their order and the bracket-wrapping of hyphenated elements
    come from make_forms.element_rows (shared with the sheet spec).
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
    rows = []
    for element, pos_name, pos in element_rows(element_index, lang_id):
        if _is_keystone(pos_name) and not keystone_active:
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

    Reads the tab free_occurrence's reads_from.prefill_free names in
    diagnostic_classes.yaml (noninterruption/general.tsv) and sets 'free' for
    each element. Then
    applies conditional na values so annotators only fill in the columns that
    are relevant to each element:
      - free=y rows: ALL annotation columns → 'na' (free elements filtered out)
      - free=n rows: ALL annotation columns left blank for annotators
      - keystone row: ALL annotation columns → 'na' (self-referential anchor;
        free value still pulled from noninterruption)

    Warns if the noninterruption TSV is missing or elements are absent from it.
    """
    src = reads_from("free_occurrence", "prefill_free")
    (crit,) = src["criteria"]
    ni_label = f"{src['class']}/{src['construction']}.tsv"
    ni_path = CODED_DATA / lang_id / src["class"] / f"{src['construction']}.tsv"

    free_map: Dict[str, str] = {}
    if ni_path.exists():
        try:
            ni_df = pd.read_csv(ni_path, sep="\t", dtype=str, keep_default_na=False)
            if crit in ni_df.columns and "Element" in ni_df.columns:
                free_map = {
                    row["Element"]: row[crit]
                    for _, row in ni_df.iterrows()
                    if row.get(crit, "") not in ("", "NA")
                }
                if not free_map:
                    print(f"    [WARNING] {ni_label} exists but '{crit}' column is blank.")
                    print(f"              Annotate {src['class']} first, then regenerate this sheet.")
            else:
                print(f"    [WARNING] {ni_label} is missing '{crit}' or 'Element' column.")
                print(f"              {crit} column will be left blank for manual entry.")
        except Exception as exc:
            print(f"    [WARNING] Could not read {ni_label}: {exc}")
            print(f"              {crit} column will be left blank for manual entry.")
    else:
        print(f"    [WARNING] {ni_label} not found.")
        print(f"              Annotate {src['class']} first, then regenerate this sheet.")
        print(f"              {crit} column will be left blank for manual entry.")

    base = len(ELEMENT_ROW_COLUMNS)  # the row columns come before the criteria

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
        is_keystone = _is_keystone(pos_name)

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


def _prefill_by_label(rows: List[List[object]], param_names: List[str],
                      class_name: str, construction: str) -> List[List[object]]:
    """Give each blank non-keystone cell the value the construction's
    ``prefill_by_label`` names for its element's label (e.g. referential=y
    for NP{S,A} in coreference prescreening, #318 c). A label planar.yaml
    does not register raises: it is a typo, and would match nothing."""
    rules = prefill_by_label(class_name, construction)
    unknown = sorted({lab for _, labels in rules.values() for lab in labels}
                     - registered_labels())
    if unknown:
        raise ValueError(f"diagnostic_classes.yaml {class_name}/{construction} "
                         f"prefill_by_label names {unknown}, not labels in planar.yaml")
    base = len(ELEMENT_ROW_COLUMNS)
    for crit, (value, labels) in rules.items():
        if crit not in param_names:
            continue
        col = base + param_names.index(crit)
        for row in rows:
            if (not _is_keystone(str(row[1])) and row[col] == ""
                    and category_label(row[0]) in labels):
                row[col] = value
    return rows


def starting_rows(element_index, lang_id: str, class_name: str, construction: str,
                  param_names: List[str], data_dir: Path | str = "") -> List[List[object]]:
    """The rows an element-row tab starts with, before anyone annotates: one
    per planar element, with every value the tooling fills in itself — the
    keystone's na when it takes no part (keystone_active), free_occurrence's
    free copied from noninterruption, and the construction's
    prefill_by_label. The one copy of those rules: generate-sheets builds a
    tab from these rows, update-sheets adds the missing ones, and
    restructure-sheets uses them for rows with nothing to carry over.
    ``data_dir`` holds the diagnostics YAML (default: the language's
    lang_setup)."""
    ka = resolve_keystone_active(lang_id, class_name, construction, data_dir=data_dir) or False
    rows = _build_rows(element_index, lang_id, param_names, keystone_active=ka)
    if class_name == "free_occurrence":
        rows = _prefill_free_occurrence_rows(rows, param_names, lang_id)
    return _prefill_by_label(rows, param_names, class_name, construction)


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

    Which pairs are candidates is planars.nonpermutability.is_pair_candidate,
    the one statement of the rule (integrity-check's staleness check uses it too).

    Returns sorted [[Element_A, Element_B], ...] rows (no scopal — annotators fill that in).
    """
    # Build element → set of positions. Skip keystone unless keystone_active.
    # Apply the same bracket-wrapping used when writing element_prescreening rows
    # (make_forms.wrap_element, imported as _wrap) so that pair element names are
    # consistent with those in element_prescreening.tsv.
    elem_positions: Dict[str, set] = {}
    for _, (pos, pos_name, lang, element) in element_index.items():
        if lang != lang_id:
            continue
        if _is_keystone(pos_name) and not keystone_active:
            continue
        elem_positions.setdefault(_wrap(element), set()).add(pos)

    elements = sorted(elem_positions.keys())
    return [[a, b] for i, a in enumerate(elements) for b in elements[i + 1:]
            if is_pair_candidate(elem_positions[a], elem_positions[b], pos_type)]


def _abort_if_criterion_diverges_by_position(
    df: "pd.DataFrame",
    criterion: str,
    lang_id: str,
    source_label: str,
    title_label: str,
    regen_command: str,
    context_note: str,
    file_issue: bool = True,
) -> None:
    """Abort and file/update a `diagnostics` GitHub issue if any element has
    divergent `criterion` values across positions in `df` — e.g. `n` at one
    structural position, `y` or `both` at another. Returns normally (no-op)
    if nothing diverges.

    This is an unresolved linguistics question the code shouldn't guess at:
    is `criterion` a property of an element globally, or of an element at a
    specific position? First found for nonpermutability's `scopal` (issue
    #228); the identical shape recurred, unguarded, in coreference's
    `referential` (issue #285) — #228 had assumed coreference was unaffected,
    which turned out to be wrong. Shared here, used by both filters below, so
    the two can't independently drift the way #285 found they already had.
    ``file_issue=False`` aborts without filing (see ``pair_rows``).
    """
    divergent = []
    for elem, group in df.groupby("Element"):
        vals = {v.strip() for v in group[criterion]}
        if "n" in vals and vals & {"y", "both"}:
            rows = [
                f"  {row.get('Position_Name', '?')} (pos {row.get('Position_Number', '?')}): "
                f"{criterion}={row[criterion].strip() or '(blank)'}"
                for _, row in group.iterrows()
            ]
            divergent.append((elem, rows))

    if not divergent:
        return
    if not file_issue:
        raise SystemExit(f"  {source_label} for {lang_id} has elements with divergent "
                         f"{criterion} values across positions.")

    lines = [
        f"[{lang_id}] `{source_label}` has element(s) with divergent `{criterion}` values "
        f"across positions (e.g. `{criterion}=n` at one position, `{criterion}=y` or `both` at "
        f"another). Pair generation cannot proceed until this is resolved. {context_note}\n",
        "**Affected elements:**",
    ]
    for elem, rows in divergent:
        lines.append(f"\n**{elem}**")
        lines.extend(rows)
    lines += [
        "",
        f"**Action required:** Decide whether `{criterion}` is a property of an element globally "
        f"or per position, update `{source_label}` accordingly, then re-run:",
        f"`{regen_command}`",
    ]
    body = "\n".join(lines)
    title = f"[{lang_id}] {title_label}: element has divergent {criterion} values by position"
    try:
        if not _issues.available():
            raise RuntimeError("GitHub can't be reached (is gh signed in?)")
        # This guard can fire from more than one call site for the same
        # language before the underlying data is fixed. Find-or-edit by
        # exact title (not just the "diagnostics" label, which is shared with
        # unrelated issues) so repeated trips update one issue in place instead
        # of piling up duplicates -- see issue #269, filed after #266/#267 were
        # both created for the same synth0001 divergence three minutes apart.
        number, created = _issues.file_issue("diagnostics", title, body,
                                             replace=True, match_title=True)
        print(f"   GitHub issue #{number} "
              f"{'created' if created else 'updated (already open for this language)'}")
    except Exception as exc:
        print(f"   (Could not create/update GitHub issue: {exc})")
    raise SystemExit(
        f"  Aborting: {source_label} for {lang_id} has elements with divergent {criterion}\n"
        f"  values across positions. See the GitHub issue above. {context_note}"
    )


def _filter_nonperm_pairs_by_prescreening(
    pairs: List[List[str]], lang_id: str, *, file_issue: bool = True,
) -> List[List[str]]:
    """Filter candidate pairs by removing elements with scopal=n in element_prescreening.tsv.

    If element_prescreening.tsv does not exist, returns the full list with a note
    reminding the coordinator to annotate element_prescreening first.

    Aborts (and files a GitHub issue) if any element has divergent scopal values across
    positions — e.g. scopal=n at one position and scopal=y at another. This is an
    unresolved linguistics question; see issue #228.
    """
    prescreening_path = (CODED_DATA / lang_id / "nonpermutability"
                         / f"{source_construction('nonpermutability')}.tsv")
    if not prescreening_path.exists():
        print("    [NOTE] element_prescreening.tsv not found — generating unfiltered pair list.")
        print("          Annotate element_prescreening first, then re-run")
        print(f"          python -m coding generate-sheets --lang {lang_id} --apply")
        print("          to get a filtered pairs sheet.")
        return pairs

    df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)

    _abort_if_criterion_diverges_by_position(
        df, "scopal", lang_id,
        source_label="element_prescreening",
        title_label="nonpermutability",
        regen_command=f"python -m coding generate-sheets --lang {lang_id} "
                       "--regen-construction nonpermutability:general",
        context_note="See issue #228 for context.",
        file_issue=file_issue,
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
    _keystone = KEYSTONE_NAME

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
                if pos_type.get(pos_a_num) == ZONE:
                    rows.append([elem_a, pos_a_str, pos_b_str, "same", 0])
                # Same Slot position: skip (elements cannot co-occur).
                continue

            direction = "forward" if pos_b_num > pos_a_num else "backward"
            rows.append([elem_a, pos_a_str, pos_b_str, direction,
                         pos_b_num - pos_a_num])

    rows.sort(key=lambda r: r[4], reverse=True)
    return [r[:4] for r in rows]


def _filter_reflex_pairs_by_prescreening(
    pairs: List[List[str]], lang_id: str, construction_name: str = "<construction>",
    *, file_issue: bool = True,
) -> List[List[str]]:
    """Filter candidate pairs using prescreening annotations.

    Reads prescreening.tsv from the coreference class directory.
    If the file does not exist, returns empty list with instructions.
    Each pair is [Element_A, Position_A, Position_B, Direction].

    Removes rows where:
      - Element_A has referential=n (cannot serve as binder), or
      - Position_B has no referential=y elements (no potential anaphor at that position).

    Aborts (and files a GitHub issue) if any element has divergent referential values
    across positions — e.g. referential=n at one position and referential=y at another.
    This is the same unresolved-linguistics-question shape as issue #228 (there for
    nonpermutability's `scopal`); #228 assumed coreference didn't have it, which issue
    #285 found was wrong. `construction_name` is only used to name the right
    `--regen-construction` target in that issue's body, defaulting to a placeholder for
    any caller that doesn't have it handy.
    """
    prescreening_path = (CODED_DATA / lang_id / "coreference"
                         / f"{source_construction('coreference')}.tsv")
    if not prescreening_path.exists():
        print("    [NOTE] prescreening.tsv not found — pair tab left blank.")
        print("          Annotate prescreening first, then re-run:")
        print(f"          python -m coding generate-sheets --lang {lang_id} "
              "--regen-construction coreference:<construction>")
        return []

    df = pd.read_csv(prescreening_path, sep="\t", dtype=str, keep_default_na=False)

    _abort_if_criterion_diverges_by_position(
        df, "referential", lang_id,
        source_label="prescreening",
        title_label="coreference",
        regen_command=f"python -m coding generate-sheets --lang {lang_id} "
                       f"--regen-construction coreference:{construction_name}",
        context_note="See issue #228 (the original nonpermutability case) and issue "
                      "#285 for context.",
        file_issue=file_issue,
    )

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

# Issue #237's tier-2 "obligatory positions" — positions outside the
# free_occurrence-derived obligatory core (see _phrasal_accent_obligatory_core)
# treated as always present when deciding whether two accent-eligible elements
# can become linearly adjacent — are listed per language in its diagnostics
# YAML (classes.phrasal_accent.obligatory_positions; make_forms.
# resolve_obligatory_positions). Every other non-keystone Slot is treated as
# potentially absent. The keystone needs no listing: it is always in the core.
# Until 2026-10-16 this was one global constant, {v:verbstem, v:npsubj1}, a
# first guess from #237 that named an English position for every language.


def _phrasal_accent_obligatory_core(lang_id: str, keystone_pos: int) -> Tuple[int, int]:
    """Return the (left, right) Position_Number range of the obligatory core.

    Tier 1 of issue #237's adjacency algorithm: free_occurrence's minimal span
    for a bound keystone (planars.free_occurrence.bound_keystone_span, the one
    copy of that rule). For a bound keystone (free=n), the positions it
    structurally depends on (dependent-on-left/dependent-on-right) are exactly the
    positions that must be present whenever the keystone is realized — i.e. they
    can never be dropped, so they always block adjacency between elements on
    either side of them. That set is already annotated (no new annotation burden)
    once free_occurrence/general.tsv exists. Where a side lists several
    positions (any one is enough, #318), the nearest is used, so the core is
    the smallest frame the keystone can surface in; none of the listed
    positions is then individually required, so this treats more as
    obligatory than strictly is (as the contiguous range already does for
    optional positions inside it). A dependent-on cell that is not positions
    raises (validate-coding reports it to the annotator).

    Falls back to the keystone position alone (a trivial single-position "core")
    when free_occurrence/general.tsv doesn't exist yet, the keystone row is
    missing, or the keystone is free (free=y, i.e. no structural dependents) —
    in all of these cases tier 2 (the language's obligatory_positions) does all
    the obligatory-position work outside the keystone itself.
    """
    src = reads_from("phrasal_accent", "obligatory_core")
    fo_path = CODED_DATA / lang_id / src["class"] / f"{src['construction']}.tsv"
    if not fo_path.exists():
        return (keystone_pos, keystone_pos)

    try:
        df = pd.read_csv(fo_path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return (keystone_pos, keystone_pos)

    if "Position_Name" not in df.columns:
        return (keystone_pos, keystone_pos)

    _keystone = KEYSTONE_NAME
    ks_rows = df[df["Position_Name"].str.strip().str.lower() == _keystone]
    if ks_rows.empty:
        return (keystone_pos, keystone_pos)
    ks_row = ks_rows.iloc[0]

    if ks_row.get("free", "").strip() != "n":
        # free=y, blank, na, or unannotated: no structural dependents to seed
        # the core with — tier 2 handles everything outside the keystone itself.
        return (keystone_pos, keystone_pos)

    return bound_keystone_span(ks_row.get("dependent-on-left", ""),
                               ks_row.get("dependent-on-right", ""), keystone_pos)


def _phrasal_accent_obligatory_positions(
    lang_id: str, keystone_pos: int, all_positions: Dict[int, str],
    data_dir: Optional[Path] = None,
) -> Set[int]:
    """Union tier-1 (obligatory core) and tier-2 (the language's list) obligatory positions.

    A position is obligatory (can never be dropped, so it always blocks adjacency
    between elements on either side of it) if EITHER:
      - it falls inside the free_occurrence-derived obligatory core, or
      - its Position_Name is in the language's obligatory_positions.
    A listed name the planar does not have raises: it is a typo or a renamed
    position, and silently ignoring it would change which pairs exist.
    ``data_dir`` holds the diagnostics YAML (default: the language's lang_setup).
    """
    data_dir = data_dir or CODED_DATA / lang_id / "lang_setup"
    core_lo, core_hi = _phrasal_accent_obligatory_core(lang_id, keystone_pos)
    obligatory = {p for p in all_positions if core_lo <= p <= core_hi}
    by_name = {name.strip().lower(): num for num, name in all_positions.items()}
    for listed in resolve_obligatory_positions(lang_id, data_dir):
        if listed.lower() not in by_name:
            raise ValueError(
                f"diagnostics_{lang_id}.yaml: phrasal_accent.obligatory_positions names "
                f"{listed!r}, which is not a position in planar_{lang_id}.tsv")
        obligatory.add(by_name[listed.lower()])
    return obligatory


def _build_phrasal_accent_pairs(
    element_index, lang_id: str, pos_type: Dict[int, str],
    keystone_active: bool = False, *, data_dir: Optional[Path] = None,
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

      Tier 2 (outside the core): the positions the language's diagnostics
        YAML lists as phrasal_accent.obligatory_positions, treated as always
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
    _keystone = KEYSTONE_NAME

    prescreening_path = (CODED_DATA / lang_id / "phrasal_accent"
                         / f"{source_construction('phrasal_accent')}.tsv")
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

    obligatory = _phrasal_accent_obligatory_positions(lang_id, keystone_pos, all_positions,
                                                      data_dir)

    def _adjacent(pos_a: int, pos_b: int) -> bool:
        if pos_a == pos_b:
            return pos_type.get(pos_a) == ZONE
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


def pair_rows(lang_id: str, class_name: str, construction: str, *,
              planar_path: Optional[Path] = None, file_issue: bool = True) -> List[List[str]]:
    """The rows a pair tab should have, from the planar and the prescreening
    tab's imported TSV: the one builder that making, extending and
    regenerating a sheet all use, and that the Drive door's end-of-command
    check compares the tab with. Reads ``CODED_DATA``.

    ``file_issue=False``: when an element's prescreening value differs by
    position, raise SystemExit without filing the `diagnostics` issue (the
    door's check reads; it doesn't report linguistics questions)."""
    planar_path = planar_path or CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    element_index = build_element_index(planar_path.name, planar_path.parent)
    ka = resolve_keystone_active(lang_id, class_name, construction,
                                 data_dir=planar_path.parent) or False
    pos_type = _read_position_types(planar_path, lang_id)
    if class_name == "coreference":
        pairs = _build_reflex_pairs(element_index, lang_id, pos_type, keystone_active=ka)
        return _filter_reflex_pairs_by_prescreening(pairs, lang_id, construction,
                                                    file_issue=file_issue)
    if class_name == "phrasal_accent":
        return _build_phrasal_accent_pairs(element_index, lang_id, pos_type, keystone_active=ka,
                                           data_dir=planar_path.parent)
    if class_name == "nonpermutability":
        pairs = _build_nonperm_pairs(element_index, lang_id, pos_type, keystone_active=ka)
        return _filter_nonperm_pairs_by_prescreening(pairs, lang_id, file_issue=file_issue)
    raise ValueError(f"{class_name}/{construction} is not a pair tab this builder knows")


def _fill_new_tab(ss, lang_id: str, class_name: str, construction: str,
                  param_names: List[str], param_values: Dict[str, List[str]],
                  element_index, planar_path: Path) -> str:
    """Write a new construction tab's rows; return a summary for the log.

    Decided by the construction's row shape in diagnostic_classes.yaml, never
    by naming classes (hidden-facts R5; creating a sheet and adding a tab to
    one each had a 45-line chain of class names): element rows from the
    planar, pair rows from pair_rows() written by the writer for their pair
    shape, and biuniqueness_deviations' three tabs by its own builder.
    """
    if class_name == _br.CLASS_NAME:
        # elements (in-scope elements) -> morphemes -> morphs (#254).
        n = _biuniq_populate(ss, lang_id, construction, param_names, param_values, planar_path)
        return f"{n} rows, {len(param_names)} params"
    kind = row_type(class_name, construction)
    if kind == PAIR_ROWS:
        pairs = pair_rows(lang_id, class_name, construction, planar_path=planar_path)
        shape = header_shape(row_columns(class_name, construction))
        writers = {"element_pairs": _populate_tab_pairs,
                   "position_pairs": _populate_tab_reflex_pairs}
        if shape not in writers:
            raise ValueError(f"{class_name}/{construction}: no writer for pair shape {shape!r}")
        writers[shape](ss, construction, param_names, param_values, pairs,
                       trailing=trailing_columns_for(lang_id))
        return f"{len(pairs)} candidate pairs"
    if kind != ELEMENT_ROWS:
        raise ValueError(f"{class_name}/{construction}: no writer for row_type {kind!r}")
    rows = starting_rows(element_index, lang_id, class_name, construction, param_names,
                         data_dir=planar_path.parent)
    _populate_tab(ss, construction, param_names, param_values, rows,
                  trailing=trailing_columns_for(lang_id))
    return f"{len(rows)} rows, {len(param_names)} params"


def _populate_tab_pairs(
    spreadsheet: SpreadsheetHandle,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    pairs: List[List[str]],
    prefill: Optional[Dict[Tuple[str, str], Dict[str, str]]] = None,
    *,
    trailing: List[str],
) -> WorksheetHandle:
    """Create or clear a worksheet tab and populate it with pair rows.

    Like _populate_tab() but for the nonpermutability pair-row format:
    columns are Element_A, Element_B, then criterion columns, then trailing
    columns. No Position_Name, Position_Number, or keystone row.

    Args:
        spreadsheet:  the parent spreadsheet handle.
        tab_name:     worksheet title to create or clear.
        param_names:  ordered list of criterion column names (e.g. ["scopal"]).
        param_values: dict mapping criterion name to list of allowed values.
        pairs:        candidate pair rows from pair_rows() (no header).
        prefill:      optional {(Element_A, Element_B): {col: val}} dict; when
                      provided, retained pairs are pre-filled with existing values.
        trailing:     the language's trailing columns (trailing_columns_for).

    Returns:
        The populated worksheet handle.
    """
    pair_struct = PAIR_ROW_SHAPES["element_pairs"]
    num_cols = len(pair_struct) + len(param_names) + len(trailing)  # structure, params, trailing
    try:
        ws = spreadsheet.worksheet(tab_name)
        _reset_worksheet(ws, len(pairs), num_cols)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(pairs) + 2, cols=num_cols
        )

    all_cols = param_names + trailing
    header = pair_struct + all_cols
    data_rows = []
    for pair in pairs:
        pre = (prefill or {}).get(_pair_key("element_pairs", pair), {})
        data_rows.append(list(pair[:len(pair_struct)]) + [pre.get(c, "") for c in all_cols])
    ws.update([header] + data_rows, "A1")
    per_col_values = [param_values[p] for p in param_names]  # values come from criteria_for
    # Param columns start right after the pair-structure columns
    _format_and_validate(ws, len(pairs), per_col_values, col_start=len(pair_struct))
    return ws


def _pair_key(shape: str, row: Sequence) -> Tuple:
    """The key of one pair row (planar.yaml pair_row_shapes[shape].key), from a
    generated pair or a sheet row; both start with the shape's columns in order."""
    cols = PAIR_ROW_SHAPES[shape]
    return tuple(row[cols.index(k)] for k in PAIR_ROW_KEYS[shape])


def _populate_tab_reflex_pairs(
    spreadsheet: SpreadsheetHandle,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    pairs: List[List[str]],
    prefill: Optional[Dict] = None,
    *,
    trailing: List[str],
) -> WorksheetHandle:
    """Create or clear a worksheet tab and populate it with coreference pair rows.

    Column format: Element_A, Position_A, Position_B, Direction,
    then criterion columns, then trailing columns.
    Position columns use combined "N (name)" format; Direction is structural.

    Args:
        prefill: {(elem_a, pos_b_str, direction): {col: val}} — annotations
                 keyed by (Element_A, Position_B, Direction) to carry over when
                 regenerating an existing tab.
    """
    _REFLEX_STRUCT = PAIR_ROW_SHAPES["position_pairs"]
    num_cols = len(_REFLEX_STRUCT) + len(param_names) + len(trailing)
    try:
        ws = spreadsheet.worksheet(tab_name)
        _reset_worksheet(ws, len(pairs), num_cols)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(pairs) + 2, cols=num_cols
        )

    all_cols = param_names + trailing
    header = _REFLEX_STRUCT + all_cols
    data_rows = []
    for pair in pairs:
        pre = (prefill or {}).get(_pair_key("position_pairs", pair), {})
        data_rows.append(list(pair[:len(_REFLEX_STRUCT)])
                         + [pre.get(c, "") for c in all_cols])
    ws.update([header] + data_rows, "A1")
    per_col_values = [param_values[p] for p in param_names]  # values come from criteria_for
    # Param columns start right after the structural columns.
    _format_and_validate(ws, len(pairs), per_col_values, col_start=len(_REFLEX_STRUCT))
    return ws


def _populate_tab_keyed(
    spreadsheet: SpreadsheetHandle,
    tab_name: str,
    keyed_columns: List[str],
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[Dict[str, str]],
    *,
    trailing: List[str],
) -> WorksheetHandle:
    """Create or clear a worksheet tab and populate it with keyed rows.

    Like _populate_tab_pairs() but for row_type: keyed_rows (biuniqueness_deviations'
    morphemes and morphs tabs): the generator-written keyed_columns, then
    criterion columns, then trailing columns. Each row is a dict; any criterion
    or trailing value it carries (an answer carried over, or a pre-fill) is
    written, everything else is blank.
    """
    num_cols = len(keyed_columns) + len(param_names) + len(trailing)
    try:
        ws = spreadsheet.worksheet(tab_name)
        _reset_worksheet(ws, len(rows), num_cols)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=len(rows) + 2, cols=num_cols)

    header = keyed_columns + param_names + trailing
    data_rows = [[str(r.get(c, "")) for c in header] for r in rows]
    ws.update([header] + data_rows, "A1")
    per_col_values = [param_values[p] for p in param_names]  # values come from criteria_for
    _format_and_validate(ws, len(rows), per_col_values, col_start=len(keyed_columns),
                         param_notes=_build_criterion_notes(param_names))
    return ws


def _biuniq_generate(
    lang_id: str, construction: str, param_names: List[str], planar_path: Path,
):
    """Build the rows for one biuniqueness_deviations tab from its sources.

    The elements tab comes from the planar; morphemes from the imported
    elements tab; morphs from the imported morphemes tab (plus the elements
    tab). Tab names are _br.ELEMENTS/MORPHEMES/MORPHS, read from the schema.
    A missing source gives an empty tab and a note, as phrasal_accent's pair
    tab does: it fills in once the source is imported and the tab is
    regenerated.
    """
    planar_df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    if construction == _br.ELEMENTS:
        return _br.element_rows(planar_df, lang_id, param_names)

    cls_dir = CODED_DATA / lang_id / _br.CLASS_NAME
    missing = [n for n in _br.sources_of(construction) if not (cls_dir / f"{n}.tsv").exists()]
    if missing:
        print(f"    [NOTE] {_br.CLASS_NAME}/{missing[0]}.tsv not found — {construction} tab "
              f"left empty. Fill in {missing[0]}, import it, then run:\n"
              f"      python -m coding generate-sheets --lang {lang_id} "
              f"--regen-construction {_br.CLASS_NAME}:{construction}")
        return []
    read = lambda n: pd.read_csv(cls_dir / f"{n}.tsv", sep="\t", dtype=str, keep_default_na=False)
    return _br.keyed_rows(construction, read, planar_df, lang_id)


def _biuniq_populate(
    spreadsheet: SpreadsheetHandle, lang_id: str, construction: str,
    param_names: List[str], param_values: Dict[str, List[str]], planar_path: Path,
) -> int:
    """Create one biuniqueness_deviations tab on a new or extended sheet.
    Returns the number of rows written."""
    if construction != _br.ELEMENTS and construction not in _br.KEYED:
        raise ValueError(f"{_br.CLASS_NAME} has no tab named {construction!r} "
                         f"(schema: {_br.ELEMENTS}, {', '.join(_br.KEYED)})")
    rows = _biuniq_generate(lang_id, construction, param_names, planar_path)
    trailing = trailing_columns_for(lang_id)
    if construction == _br.ELEMENTS:
        _populate_tab(spreadsheet, construction, param_names, param_values, rows, trailing=trailing)
    else:
        columns, _ = _br.KEYED[construction]
        _populate_tab_keyed(spreadsheet, construction, columns, param_names, param_values, rows,
                            trailing=trailing)
    return len(rows)


def _rebuild_tab(spreadsheet: SpreadsheetHandle, lang_id: str, class_name: str,
                 construction_name: str, kept, confirm_drop: bool, if_dropped: str,
                 populate: Callable[[], None]) -> None:
    """Run ``populate`` (the rewrite of one tab) inside the Drive door's
    replacing(): the door saves the tab to state_files.SNAPSHOT_DIR first, and refuses
    (unless --confirm-drop) if an answered row's key is not in ``kept``, the
    rows whose answers the rebuild carries over (#241). ``if_dropped`` is the
    advice that ends the refusal message."""
    try:
        ws = spreadsheet.worksheet(construction_name)
    except WorksheetNotFound:
        populate()
        return
    reason = "--regen-construction rebuilds the tab with every answer carried over by key"
    try:
        with drive_door.replacing(ws, reason, kept=kept, allow_drop=confirm_drop):
            populate()
    except drive_door.AnswersWouldBeDropped as exc:
        raise SystemExit(
            f"ABORTED: regenerating {lang_id}/{class_name}/{construction_name} would drop "
            f"{len(exc.lines)} answered row(s) — no confirmation step exists after this "
            f"point, they would just be gone from the Sheet:\n" + "\n".join(exc.lines)
            + "\n\n" + if_dropped
            + f"\n  python -m coding generate-sheets --lang {lang_id} --regen-construction "
              f"{class_name}:{construction_name} --confirm-drop")


def _regen_keyed_construction(
    spreadsheet: SpreadsheetHandle, lang_id: str, class_name: str, construction_name: str,
    param_names: List[str], param_values: Dict[str, List[str]], confirm_drop: bool,
) -> None:
    """--regen-construction for a keyed_rows tab: rebuild it from its source,
    carrying every answer over by key, keeping hand-added rows; the Drive door
    refuses to drop an answered row unless confirm_drop (as for pair tabs, #241)."""
    # Imported here: restructure_sheets imports this module at load time.
    from .restructure_sheets import _get_keyed_row_constructions
    keyed = _get_keyed_row_constructions()[class_name][construction_name]
    columns, key = keyed["columns"], keyed["key"]
    try:
        existing_rows = spreadsheet.worksheet(construction_name).get_all_values()
    except WorksheetNotFound:
        existing_rows = []

    planar_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    generated = _biuniq_generate(lang_id, construction_name, param_names, planar_path)
    trailing = trailing_columns_for(lang_id)
    answer_cols = param_names + trailing
    rows, counts = _br.carry_over(generated, existing_rows, key, answer_cols)
    _rebuild_tab(
        spreadsheet, lang_id, class_name, construction_name,
        kept=[[r.get(k, "") for k in key] for r in rows], confirm_drop=confirm_drop,
        if_dropped=("Their source is no longer in the earlier tab. If that change was a "
                    "mistake, fix it there, import, and regenerate again. If the drop is "
                    "intended, re-run with --confirm-drop:"),
        populate=lambda: _populate_tab_keyed(spreadsheet, construction_name, columns,
                                             param_names, param_values, rows, trailing=trailing))
    print(f"    {construction_name}: {counts['retained']} retained, {counts['added']} added, "
          f"{counts['removed']} removed, {counts['hand_added']} hand-added kept")


# ---------------------------------------------------------------------------
# Locked tabs (Instructions, Planar Structure) are coding/locked_tabs.py's.
# ---------------------------------------------------------------------------

def _refresh_locked_tabs(spreadsheet: SpreadsheetHandle, class_name: str,
                         lang_id: str, planar_path: Path) -> None:
    """Rebuild and protect the locked tabs, printing what changed."""
    for change in rebuild_locked_tabs(spreadsheet, class_name, lang_id, planar_path):
        print(f"    Locked tab {change}")


# ---------------------------------------------------------------------------
# Status tab
# ---------------------------------------------------------------------------

def _move_status_tab_to_end(spreadsheet: SpreadsheetHandle) -> None:
    """Ensure the Status tab is the last worksheet in the spreadsheet."""
    worksheets = spreadsheet.worksheets()
    if not worksheets or worksheets[-1].title == _STATUS_TAB:
        return
    status_ws = next((w for w in worksheets if w.title == _STATUS_TAB), None)
    if status_ws is None:
        return
    ordered = [w for w in worksheets if w.title != _STATUS_TAB] + [status_ws]
    spreadsheet.reorder_worksheets(ordered)


def _status_row(construction: str, header: List[str]) -> List[str]:
    """A new Status-tab row for ``header``: the construction, in-progress,
    every other column blank."""
    values = {STATUS_CONSTRUCTION_COLUMN: construction, STATUS_STATUS_COLUMN: STATUS_IN_PROGRESS}
    return [values.get(h, "") for h in header]


def _status_column_format(sheet_id: int, start: int, end: int) -> List[dict]:
    """Bold header cells and wrapped problem text for Status-tab columns
    ``start``..``end`` (0-based, end exclusive)."""
    requests = [{"repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": start, "endColumnIndex": end},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
        "fields": "userEnteredFormat.textFormat.bold",
    }}]
    problems = STATUS_COLUMNS.index(STATUS_PROBLEMS_COLUMN)
    if start <= problems < end:
        requests.append({"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1,
                      "startColumnIndex": problems, "endColumnIndex": problems + 1},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }})
    return requests


def _create_status_tab(
    spreadsheet: SpreadsheetHandle,
    construction_names: List[str],
    apply: bool = True,
) -> List[str]:
    """Add a Status tab to a spreadsheet, or bring an existing one up to date.

    The tab's columns are `planar.yaml`'s `status_tab.columns`. Each
    construction gets one row with an 'in-progress' default and a dropdown
    for Status. If the tab already exists, adds any columns it lacks (at the
    right, in the schema's order) and any missing construction rows, and
    moves the tab to the last position. Returns what it changed (or, with
    apply=False, would change) on an existing tab; nothing is written then.
    """
    existing = {ws.title: ws for ws in spreadsheet.worksheets()}

    if _STATUS_TAB in existing:
        ws = existing[_STATUS_TAB]
        rows = ws.get_all_values()
        header = [h.strip() for h in rows[0]] if rows else []
        changes = []
        new_cols = [c for c in STATUS_COLUMNS if c not in header]
        if new_cols and header:
            changes.append(f"Status tab: add column(s) {new_cols}")
            if apply:
                start = len(header)
                if ws.col_count < start + len(new_cols):
                    ws.resize(cols=start + len(new_cols))
                ws.update([new_cols], rowcol_to_a1(1, start + 1))
                spreadsheet.batch_update({"requests": _status_column_format(
                    ws.id, start, start + len(new_cols))})
            header = header + new_cols
        current = set(status_map([header] + rows[1:]))
        missing = [c for c in construction_names if c not in current]
        if missing:
            changes.append(f"Status tab: add row(s) for {missing}")
            if apply:
                ws.append_rows([_status_row(c, header) for c in missing],
                               value_input_option="RAW")
        if apply:
            _move_status_tab_to_end(spreadsheet)
        return changes

    if not apply:
        return [f"create the Status tab ({len(construction_names)} construction(s))"]
    ws = spreadsheet.add_worksheet(title=_STATUS_TAB, rows=len(construction_names) + 2,
                                   cols=len(STATUS_COLUMNS))
    data = [_status_row(c, STATUS_COLUMNS) for c in construction_names]
    ws.update([STATUS_COLUMNS] + data, "A1")

    sheet_id = ws.id
    num_rows = len(construction_names)
    status_col = STATUS_COLUMNS.index(STATUS_STATUS_COLUMN)
    spreadsheet.batch_update({"requests": [
        # Freeze the header
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        *_status_column_format(sheet_id, 0, len(STATUS_COLUMNS)),
        # Dropdown on the Status column
        {"setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1, "endRowIndex": 1 + num_rows,
                "startColumnIndex": status_col, "endColumnIndex": status_col + 1,
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
    return []


# ---------------------------------------------------------------------------
# Sheet formatting and validation
# ---------------------------------------------------------------------------

def dropdown_request(sheet_id: int, col_idx: int, end_row: int, values,
                     strict: bool = False) -> dict:
    """The setDataValidation request that gives one criterion column, rows 2 to
    ``end_row``, the dropdown its declared ``values`` call for
    (``schemas.dropdown_values``) -- or removes any dropdown there when they
    call for none, so one left by an older rule doesn't linger.

    Non-strict by default: annotators can still type a value the list lacks;
    it is shown as invalid and caught by validate-coding (the Status column's
    dropdown is strict). Every writer of a criterion dropdown builds it here.
    """
    request: Dict[str, Any] = {"range": {
        "sheetId": sheet_id,
        "startRowIndex": 1, "endRowIndex": end_row,
        "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1,
    }}
    offered = dropdown_values(values)
    if offered is not None:
        request["rule"] = {
            "condition": {"type": "ONE_OF_LIST",
                          "values": [{"userEnteredValue": v} for v in offered]},
            "showCustomUi": True,
            "strict": strict,
        }
    return {"setDataValidation": request}


def _reset_worksheet(ws: WorksheetHandle, num_data_rows: int, num_cols: int) -> None:
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
    worksheet: WorksheetHandle,
    num_data_rows: int,
    param_values: List[List[str]],
    col_start: int = len(ELEMENT_ROW_COLUMNS),
    param_notes: Optional[List[Optional[str]]] = None,
) -> None:
    """Freeze and bold the header row; apply per-column dropdown validation and notes.

    Sends a single batch_update to the Sheets API containing:
    - a freeze request for the header row
    - a bold request for the header row
    - one dropdown validation rule per param column (none for a free-entry column)
    - one header-cell note per param column (if param_notes is provided)

    Validation is non-strict (showCustomUi=True, strict=False) so annotators
    can also type 'NA' in keystone rows without triggering a validation error.

    Args:
        worksheet: the worksheet handle to format.
        num_data_rows: number of data rows (excluding header) to validate.
        param_values: list of allowed-value lists, one entry per param column,
            in the same order as the columns.
        col_start: 0-based column index where param columns begin (default
            len(ELEMENT_ROW_COLUMNS) for standard element-row sheets; pair-row
            and keyed-row callers pass their own shape's width).
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
        requests.append(dropdown_request(sheet_id, col_idx, 1 + num_data_rows, values))
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
    spreadsheet: SpreadsheetHandle,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[List[object]],
    *,
    trailing: List[str],
) -> WorksheetHandle:
    """Create or clear a worksheet tab and populate it with data.

    If a tab named tab_name already exists it is cleared and rewritten;
    otherwise a new worksheet is created. The language's trailing columns
    are appended after the criterion columns with empty values.

    Args:
        spreadsheet: the parent spreadsheet handle.
        tab_name: worksheet title to create or clear.
        param_names: ordered list of criterion column names.
        param_values: dict mapping criterion name to list of allowed values.
        rows: data rows from starting_rows (no header).
        trailing: the language's trailing columns (trailing_columns_for).

    Returns:
        The populated worksheet handle.
    """
    num_cols = len(ELEMENT_ROW_COLUMNS) + len(param_names) + len(trailing)  # structure, params, trailing
    try:
        ws = spreadsheet.worksheet(tab_name)
        _reset_worksheet(ws, len(rows), num_cols)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=num_cols
        )

    all_cols = param_names + trailing
    header = ELEMENT_ROW_COLUMNS + all_cols
    # Pad data rows with empty trailing columns (e.g. Comments).
    all_rows = [header] + [[str(v) for v in row] + [""] * len(trailing) for row in rows]
    ws.update(all_rows, "A1")
    per_col_values = [param_values[p] for p in param_names]  # values come from criteria_for
    per_col_notes = _build_criterion_notes(param_names)
    _format_and_validate(ws, len(rows), per_col_values, param_notes=per_col_notes)
    return ws


# ---------------------------------------------------------------------------
# Analysis sheet creation
# ---------------------------------------------------------------------------

def _create_analysis_sheet(
    doorway,
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
    existing = doorway.list_files(
        q=(
            f"'{folder_id}' in parents"
            f" and name='{sheet_title}'"
            " and mimeType='application/vnd.google-apps.spreadsheet'"
            " and trashed=false"
        ),
        fields="files(id, name)",
        page_size=5,
    )
    if existing:
        ids = ", ".join(f["id"] for f in existing)
        raise SystemExit(
            f"\nERROR: A spreadsheet named \"{sheet_title}\" already exists in the Drive "
            f"folder but is not registered in the manifest for {lang_id}.\n"
            f"  Existing file ID(s): {ids}\n\n"
            f"To resolve, either:\n"
            f"  (a) Register the existing sheet: add its spreadsheet_id to the manifest, or\n"
            f"  (b) Move it to _archived/ in Drive, then re-run\n"
            f"      python -m coding generate-sheets --apply\n"
        )

    spreadsheet = doorway.create_spreadsheet(
        sheet_title, identity=drive_door.class_sheet(lang_id, class_name))
    doorway.move_file(spreadsheet.id, folder_id)
    email = _annotator_email(lang_id)
    if email:
        doorway.create_permission(spreadsheet.id, type="user", role="writer", email=email)

    default_ws = spreadsheet.sheet1
    tab_names = []

    # Each tab's criterion columns and their values: the schema's per-construction
    # `criterion:` where declared, values from the language YAML or the schema.
    constructions = apply_schema_criteria(class_name, constructions, lang_id)

    for construction, param_names, param_values in constructions:
        what = _fill_new_tab(spreadsheet, lang_id, class_name, construction, param_names,
                             param_values, element_index, planar_path)
        tab_names.append(construction)
        print(f"    Tab: {construction} ({what})")

    # Remove the default empty sheet if it wasn't one of our tabs
    if default_ws.title not in tab_names:
        spreadsheet.del_worksheet(default_ws)

    # Add the locked tabs and Status, then put every tab in its place.
    _refresh_locked_tabs(spreadsheet, class_name, lang_id, planar_path)
    _create_status_tab(spreadsheet, tab_names)
    reorder_tabs(spreadsheet, tab_names)

    # Each construction's criteria, for the manifest (the analysis notebooks
    # read them). Their allowed values stay in the diagnostics YAML only.
    construction_params = {
        construction: {"param_names": pn}
        for construction, pn, _ in constructions
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


def _coreference_key_map(
    old_keys: Iterable[Tuple[str, str, str]],
    pos_num_remap: Dict[int, int],
    new_pairs: List[List[str]],
) -> Dict[Tuple[str, str, str], Tuple[str, str, str]]:
    """Map old coreference annotation keys to new keys after position renumbering.

    When the planar structure is renumbered (positions inserted/deleted), the
    combined Position_B cells in the stored annotations carry old position numbers.
    This function translates old keys (elem_a, old_pos_b_str, old_direction) to new
    keys (elem_a, new_pos_b_str, new_direction) so that prefill lookup succeeds.

    The new direction is taken from the freshly generated pair list (which has already
    computed direction from the updated position numbers), so direction is correctly
    updated even when both pos_a and pos_b shift.

    Args:
        old_keys:      keys (Element_A, Position_B, Direction) as the tab holds them.
        pos_num_remap: {old_pos_num: new_pos_num} — typically derived from a planar diff.
        new_pairs:     freshly generated pair rows [[elem_a, pos_a_str, pos_b_str, dir], ...].

    Returns:
        {old key: new key} for every old key.  A key whose Position_B number is not
        in pos_num_remap maps to itself (safe fallback).
    """
    old_keys = list(old_keys)
    if not pos_num_remap:
        return {k: k for k in old_keys}

    # Build lookup: (elem_a, new_pos_b_num) → new_direction from generated pairs.
    pair_direction: Dict[Tuple[str, int], str] = {}
    for pair in new_pairs:
        elem_a, _pos_a_str, pos_b_str, direction = pair
        parsed = _parse_pos_cell(pos_b_str)
        if parsed:
            pair_direction[(elem_a, parsed[0])] = direction

    key_map: Dict[Tuple[str, str, str], Tuple[str, str, str]] = {}
    for key in old_keys:
        elem_a, pos_b_str, old_direction = key
        parsed = _parse_pos_cell(pos_b_str)
        if parsed is None or parsed[0] not in pos_num_remap:
            key_map[key] = key
            continue
        old_pos_b_num, pos_b_name = parsed
        new_pos_b_num = pos_num_remap[old_pos_b_num]
        new_pos_b_str = f"{new_pos_b_num} ({pos_b_name})"
        new_direction = pair_direction.get((elem_a, new_pos_b_num), old_direction)
        key_map[key] = (elem_a, new_pos_b_str, new_direction)

    return key_map


def _tab_criteria(lang_id: str, class_name: str, construction: str):
    """A tab's criterion columns and allowed values, from the language's
    diagnostics YAML through coding.schemas.criteria_for.

    --regen-construction used to read these from the manifest's cached copy,
    with typed fallbacks per class ({"scopal": ["y", "n"]}, ...): a stale copy
    plus a hidden default (Phase 10, 2026-10-12).
    """
    specs = _read_diagnostics_for_language(lang_id, CODED_DATA / lang_id / "lang_setup")
    for cls, con, names, values in specs:
        if cls == class_name and con == construction:
            return apply_schema_criteria(cls, [(con, names, values)], lang_id)[0][1:]
    raise SystemExit(f"  {class_name}:{construction} is not in diagnostics_{lang_id}.yaml; "
                     f"add it there (and run python -m coding sync-diagnostics-yaml --apply) first.")


def _regen_construction(
    doorway,
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
    if any dropped pair holds an answer (a criterion, Source or Comments),
    the Drive door refuses the rewrite (drive_door.replacing's ``kept``) and
    this function raises SystemExit instead of writing, unless confirm_drop=True (see
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
        doorway:              the Drive doorway (coding.drive_doorway.DriveDoorway).
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

    Note: before the #271 migration this opened the spreadsheet with no retry
    at all, unlike every other spreadsheet open in this file. The doorway's
    open call always retries (see its own module docstring), so this call site
    now gets the same backoff as the rest of the file -- see
    docs/data-layer-progress.md's decisions log for the full rationale.
    Opening is an idempotent read, so the added retry changes nothing about
    what gets written.
    """
    spreadsheet_id = manifest_class_info.get("spreadsheet_id")
    if not spreadsheet_id:
        raise SystemExit(f"  No spreadsheet_id in manifest for {lang_id}/{class_name}")
    spreadsheet = doorway.open_spreadsheet(spreadsheet_id)

    # keyed_rows tabs (biuniqueness_deviations' morphemes/morphs) are rebuilt
    # from their own source and keyed by their own columns, not as pairs.
    from .restructure_sheets import _get_keyed_row_constructions
    param_names, param_values = _tab_criteria(lang_id, class_name, construction_name)
    if construction_name in _get_keyed_row_constructions().get(class_name, {}):
        _regen_keyed_construction(spreadsheet, lang_id, class_name, construction_name,
                                  param_names, param_values, confirm_drop)
        return

    # Read existing tab annotations from the live Sheet, keyed by the columns
    # the schema says identify a row (planar.yaml pair_row_shapes).
    shape_cols = row_columns(class_name, construction_name)
    key_cols = row_key(class_name, construction_name)
    existing: Dict = {}
    try:
        rows = spreadsheet.worksheet(construction_name).get_all_values()
        if rows and len(rows) > 1:
            hdr = rows[0]
            if hdr[:len(shape_cols)] != shape_cols and not confirm_drop:
                # A tab of another shape can't be keyed, so its answers can't
                # be carried over.
                raise SystemExit(
                    f"ABORTED: {lang_id}/{class_name}/{construction_name}'s columns are "
                    f"{hdr}, not the {shape_cols} the schema gives this tab, so its "
                    f"answers can't be matched to the rebuilt rows. Nothing was written. "
                    f"If the old rows can go, re-run with --confirm-drop (the tab is "
                    f"saved to coded_data/.state/regen_snapshots/ before it is rewritten).")
            for row in rows[1:]:
                record = dict(zip(hdr, row))
                key = tuple(record.get(k, "") for k in key_cols)
                if any(key):
                    existing[key] = {c: v for c, v in record.items() if c not in shape_cols}
    except WorksheetNotFound:
        pass

    pairs = pair_rows(lang_id, class_name, construction_name)

    # For coreference pair tabs, remap old annotation keys when position numbers
    # have shifted (e.g. after a planar insertion/deletion). key_map takes each
    # row's key as the tab holds it now to the key its answers move to.
    key_map = {k: k for k in existing}
    if class_name == "coreference" and pos_num_remap:
        key_map = _coreference_key_map(existing, pos_num_remap, pairs)
        existing = {key_map[k]: v for k, v in existing.items()}

    new_pair_set = {tuple(p[shape_cols.index(k)] for k in key_cols) for p in pairs}
    old_pair_set = set(existing.keys())
    retained = old_pair_set & new_pair_set
    removed  = old_pair_set - new_pair_set
    added    = new_pair_set - old_pair_set

    def populate() -> None:
        if class_name == "coreference":
            _populate_tab_reflex_pairs(spreadsheet, construction_name, param_names,
                                       param_values, pairs, prefill=existing,
                                       trailing=trailing_columns_for(lang_id))
        else:
            _populate_tab_pairs(spreadsheet, construction_name, param_names, param_values,
                                pairs, prefill=existing, trailing=trailing_columns_for(lang_id))

    _rebuild_tab(
        spreadsheet, lang_id, class_name, construction_name,
        kept=[old for old, new in key_map.items() if new in new_pair_set],
        confirm_drop=confirm_drop,
        if_dropped=("If the retired element was renamed or split, run restructure-sheets "
                    "--rename-element/--split-element first — that carries the judgment "
                    "forward (as a breadcrumb for splits, verbatim for renames) and this "
                    "check will then pass cleanly, since the old rows will already be gone. "
                    "If this drop is intentional (e.g. a real prescreening scope change, not "
                    "a rename/split), re-run with --confirm-drop:"),
        populate=populate)

    print(f"    {construction_name}: {len(retained)} retained, {len(added)} added, "
          f"{len(removed)} removed")
    if removed:
        print("    The next import-sheets --apply drops the removed pairs from the "
              "local TSV (its previous version is archived).")


def _add_constructions_to_existing_sheet(
    ss: SpreadsheetHandle,
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

    Takes an already-open spreadsheet rather than a client and an ID: both
    callers hold the spreadsheet open already, and `update_sheets.py` reaches
    Drive through the doorway, where there is no client to hand over.

    Returns construction_params dict for the newly added tabs only.
    """
    # Same per-tab criteria rule as _create_analysis_sheet (coding.schemas.criteria_for).
    new_constructions = apply_schema_criteria(class_name, new_constructions, lang_id)

    construction_params: Dict = {}

    for construction, param_names, param_values in new_constructions:
        what = _fill_new_tab(ss, lang_id, class_name, construction, param_names,
                             param_values, element_index, planar_path)
        print(f"    Tab: {construction} ({what})")

        construction_params[construction] = {"param_names": param_names}

    # Refresh the locked tabs and Status, then put every tab in its place.
    planar_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    _refresh_locked_tabs(ss, class_name, lang_id, planar_path)
    system = set(system_tab_titles())
    all_ws = ss.worksheets()
    _create_status_tab(ss, [ws.title for ws in all_ws if ws.title not in system])
    # The diagnostics file's order, not the order the tabs happen to be in: a
    # tab added (or rebuilt) here may belong before an existing one.
    order = [con for cls, con, _n, _v in
             _read_diagnostics_for_language(lang_id, CODED_DATA / lang_id / "lang_setup")
             if cls == class_name]
    reorder_tabs(ss, order)

    return construction_params


def _tsv_has_rows(path: Path) -> bool:
    """True if the TSV has at least one row below its header."""
    with path.open(encoding="utf-8") as f:
        f.readline()
        return any(line.strip() for line in f)


def _source_tab_status(doorway, cls_info: dict, source_name: str) -> str:
    """The source tab's status in its sheet's Status tab ('' if unreadable)."""
    from .validate_coding import tab_statuses
    try:
        ss = doorway.open_spreadsheet(cls_info["spreadsheet_id"])
        status = tab_statuses(ss).get(source_name, "")
    except Exception as exc:
        print(f"    (could not read the Status tab: {exc})")
        return ""
    return status if isinstance(status, str) else ""


def _regen_dependents_simple(doorway, manifest: dict) -> List[str]:
    """Generate dependent constructions that have nothing in them yet.

    Safe to automate, because a tab with no rows has nothing to lose. Fires in
    two cases:
      - the dependent TSV does not exist (the tab was never generated);
      - the dependent TSV has no rows AND its source tab is marked
        'ready-for-review' in the Status tab. This is the hand-off point an
        annotator is told about (finish prescreening, mark it, and the next
        tab is filled in): before it, a partly-answered source would put rows
        in front of the annotator too early; after it, nothing else would
        notice that the empty tab is waiting (issue #254, 2026-10-12).
    A dependent with rows is never touched here; integrity-check flags it as
    stale for coordinator action instead. A source whose answers yield no rows
    is regenerated (to the same empty tab) on each run, which is harmless.

    Returns a list of "{lang_id}/{cls_name}/{dep_name}: {error}" strings, one
    per (language, dependent construction) that failed to regenerate --
    empty if all attempted regenerations succeeded. One failure deliberately
    doesn't stop the loop from trying the rest (this function's whole
    contract is per-item resilience), but until issue #283 a failure was
    only ever printed and otherwise vanished -- the caller had no way to
    know anything had gone wrong, and neither did the daily automation.
    """
    dc_classes = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    failures: List[str] = []

    for cls_name, cls_entry in dc_classes.items():
        constructions_schema = cls_entry.get("constructions", [])
        deps = [
            (c["depends_on"], c["name"])
            for c in constructions_schema
            if c.get("depends_on")
            and c.get("staleness_check") in ("element_set", "keyed_source")
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

                # A dependent with rows was deliberately generated (even if its
                # answers are blank); never overwrite it here. Staleness is
                # detected separately by integrity-check → dependent-stale.
                if dep_path.exists() and _tsv_has_rows(dep_path):
                    print(f"  [{lang_id}/{cls_name}/{dep_name}] already has rows — "
                          f"skipping auto-regeneration. Run:\n"
                          f"    python -m coding generate-sheets --lang {lang_id} "
                          f"--regen-construction {cls_name}:{dep_name}")
                    continue
                if dep_path.exists():
                    status = _source_tab_status(doorway, cls_info, source_name)
                    if status != STATUS_READY:
                        print(f"  [{lang_id}/{cls_name}/{dep_name}] empty — waiting for "
                              f"'{source_name}' to be marked ready-for-review "
                              f"(now: {status or 'unknown'})")
                        continue

                print(f"  [{lang_id}/{cls_name}/{dep_name}] regenerating from {source_name}…")
                try:
                    _regen_construction(doorway, lang_id, cls_name, dep_name, cls_info)
                except Exception as exc:
                    print(f"  ERROR: {exc}")
                    failures.append(f"{lang_id}/{cls_name}/{dep_name}: {exc}")

    return failures


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
            (the latter two only when the language has no such Sheet yet, as in
            _upload_lang_setup_as_sheets -- caller further ANDs
            needs_diagnostics_sheet with whether a diagnostics YAML exists
            locally, since that's a local-file fact this function doesn't have)
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
    needs_planar_sheet        = not bool(existing_lang_data.get("planar_spreadsheet_id"))
    needs_diagnostics_sheet   = not bool(existing_lang_data.get("diagnostics_spreadsheet_id"))

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

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding generate-sheets`."""
    ap = argparse.ArgumentParser(
        description="Create/update Google Sheets annotation forms."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="create sheets for new classes (default: dry run)",
    )
    ap.add_argument(
        "--force", action="store_true",
        help="hard error if annotation sheets already exist, instead of skipping them",
    )
    ap.add_argument(
        "--regen-construction", metavar="CLASS:CONSTRUCTION",
        help="regenerate one dependent construction tab in an existing sheet "
             "(bypasses --force protection; no new sheet is created)",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict --regen-construction to this language",
    )
    ap.add_argument(
        "--pos-remap", metavar="OLD_NUM:NEW_NUM", action="append",
        help="carry over annotations to a renumbered position for "
             "--regen-construction (repeatable)",
    )
    ap.add_argument(
        "--confirm-drop", action="store_true",
        help="confirm an intentional annotated pair-row drop for --regen-construction",
    )
    ap.add_argument(
        "--regen-dependents", action="store_true",
        help="regenerate dependent constructions with no annotation data yet (CI path)",
    )
    ap.add_argument(
        "--push-manifest", action="store_true",
        help="upload the existing local sheets_manifest.json to Drive as manifest.json "
             "(one-time migration utility)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
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
    - Creates the planar and diagnostics Sheets, read-only copies of
      planar_{lang_id}.tsv and diagnostics_{lang_id}.yaml, if the language has
      none yet (sync-planar and sync-diagnostics-yaml keep them current).
    - Creates one annotation Google Sheet per analysis class (skipping existing ones unless
      --force). Each sheet has one tab per construction with dropdown validation.
    - Uploads the merged manifest.json manifest to Drive after each language.
    - Regenerates contributor notebooks at the end.
    """
    if args is None:
        args = build_parser().parse_args()

    if args.push_manifest:
        push_manifest()
        return

    # --regen-construction CLASS:CONSTRUCTION [--lang LANG_ID]
    # Regenerate a specific dependent construction tab in an existing sheet.
    # Bypasses --force protection (no new sheet is created).
    if args.regen_construction:
        spec = args.regen_construction
        if ":" not in spec:
            raise SystemExit("Usage: --regen-construction CLASS_NAME:CONSTRUCTION_NAME")
        class_name, construction_name = spec.split(":", 1)
        lang_filter = args.lang

        # --pos-remap OLD_NUM:NEW_NUM (repeatable) — for renumbered positions.
        pos_num_remap: Dict[int, int] = {}
        for pair in (args.pos_remap or []):
            if ":" not in pair:
                raise SystemExit("--pos-remap requires 'old_num:new_num' format")
            old_s, new_s = pair.split(":", 1)
            try:
                pos_num_remap[int(old_s.strip())] = int(new_s.strip())
            except ValueError:
                raise SystemExit(f"--pos-remap values must be integers, got: {pair!r}")

        if pos_num_remap:
            print(f"Position number remap: {pos_num_remap}")

        confirm_drop = args.confirm_drop

        print("Connecting to Google APIs...")
        doorway = get_doorway()
        config = _load_drive_config()
        file_id = config.get("_planars_config_file_id")
        manifest = doorway.download_file_json(file_id) if file_id else {}

        langs = [lang_filter] if lang_filter else sorted(
            d.name for d in CODED_DATA.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
        for lang_id in langs:
            cls_info = manifest.get(lang_id, {}).get("sheets", {}).get(class_name)
            if not cls_info:
                print(f"  {lang_id}/{class_name}: not in manifest — skipping")
                continue
            print(f"\n{lang_id}/{class_name}/{construction_name}")
            _regen_construction(doorway, lang_id, class_name, construction_name, cls_info,
                                pos_num_remap=pos_num_remap or None, confirm_drop=confirm_drop)
        return

    # --regen-dependents
    # CI path: regenerate dependent constructions where no annotation data exists yet.
    if args.regen_dependents:
        # coded_data_clean_tree is enforced centrally at the python -m coding
        # dispatch chokepoint now -- see coding/preconditions.py -- not here.
        # It still guards against exactly what it always has:
        # _regen_dependents_simple reads coded_data/ (source construction
        # TSVs and the planar) as ground truth for what to regenerate, and a
        # prior step's failed auto-commit can leave it stale/reverted --
        # see issue #248's stray-row incident, caused by exactly this gap in
        # update-sheets.
        print("Connecting to Google APIs...")
        doorway = get_doorway()
        config = _load_drive_config()
        file_id = config.get("_planars_config_file_id")
        manifest = doorway.download_file_json(file_id) if file_id else {}
        failures = _regen_dependents_simple(doorway, manifest)
        if failures:
            # Issue #283: this used to return None regardless of whether any
            # regeneration failed -- the workflow step had no way to notice,
            # since a per-language exception was already caught and printed
            # inside _regen_dependents_simple. Exiting non-zero here is what
            # lets a workflow step's outcome (and, downstream, a filed
            # regen-dependents-error issue) reflect a real failure.
            print(f"\n{len(failures)} dependent construction(s) failed to regenerate:")
            for f in failures:
                print(f"  {f}")
            sys.exit(1)
        return

    force = args.force
    apply = args.apply

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    # Connect to Google once for all languages
    print("Connecting to Google APIs...")
    doorway = get_doorway()
    config = _load_drive_config()
    root_folder_id = config.get("_root_folder_id")

    # Load the existing merged config from Drive (if present) so we can update
    # it incrementally as each language is processed, preserving other languages.
    # Not routed through load_manifest(doorway): that helper has different
    # fallback semantics for the pre-#30 per-language format and does not write
    # the recovery backup below, both of which this call site needs.
    existing_config_file_id = config.get("_planars_config_file_id")
    if existing_config_file_id:
        try:
            merged_config: Dict = doorway.download_file_json(existing_config_file_id)
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

    # Preflight: resolve existing_lang_data for every language and check
    # --force against it before any language's sheets are touched. Checking
    # this one language at a time inside the main loop below meant an
    # `--apply --force` run could overwrite the first language's
    # planar/diagnostics reference sheets and only then abort on a later
    # language's existing annotation sheets -- too late for the language
    # already overwritten (Finding 15, docs/data-layer-progress.md). Every
    # language must pass this guard before any of them are touched.
    existing_lang_data_by_lang: Dict[str, Dict] = {}
    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)
        existing_lang_data: Dict = merged_config.get(lang_id, {})
        if not existing_lang_data and lang_id in config:
            # Migration: try old-format per-language manifest file
            old_fid = config[lang_id].get("manifest_file_id")
            if old_fid:
                try:
                    existing_lang_data = doorway.download_file_json(old_fid)
                except Exception:
                    pass
        existing_lang_data_by_lang[lang_id] = existing_lang_data
        _check_force_against_existing_sheets(lang_id, force, existing_lang_data)

    full_manifest: Dict = {}

    for planar_file in planar_files:
        planar_dir = planar_file.parent
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        print(f"\nLanguage:    {lang_id}")
        print(f"Planar file: {planar_file.name}")

        element_index = build_element_index(planar_file.name, planar_dir)

        # Validate the planar and diagnostics_{lang_id}.yaml. Warnings and
        # non-blocking errors (a required class not drafted yet) are printed
        # and generation goes on; a blocking error skips the language, since
        # a sheet built from a file the schema rejects (a construction the
        # class doesn't define, say) is wrong from its first row. Until
        # 2026-10-13 nothing here blocked.
        planar_df = pd.read_csv(planar_file, sep="\t")
        planar_issues = _val_planar.validate_planar_df(planar_df)
        if planar_issues:
            print(f"  Planar validation ({len(planar_issues)} issue(s)):")
            for issue in planar_issues:
                print(f"    {issue}")

        diag_issues = []
        diag_path = planar_dir / f"diagnostics_{lang_id}.yaml"
        if diag_path.exists():
            with open(diag_path, encoding="utf-8") as f:
                diag_issues = _val_diag.validate_diagnostics_yaml(yaml.safe_load(f), lang_id)
            if diag_issues:
                print(f"  Diagnostics validation ({len(diag_issues)} issue(s)):")
                for issue in diag_issues:
                    print(f"    {issue}")

        if any(i.level == "error" and i.blocking for i in planar_issues + diag_issues):
            print(f"  Skipping {lang_id}: fix the [ERROR] line(s) above in "
                  f"planar_{lang_id}.tsv / diagnostics_{lang_id}.yaml, then re-run.")
            continue

        specs = _read_diagnostics_for_language(lang_id, planar_dir)

        # Group specs by class_name -> [(construction, param_names, param_values), ...]
        all_classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            all_classes.setdefault(class_name, []).append((construction, param_names, param_values))

        print(f"Classes:     {list(all_classes.keys())}")

        # existing_lang_data was already resolved for every language in the
        # preflight pass above (which also ran the --force guard against it
        # before any language's sheets were touched) -- reuse it rather than
        # recomputing it here and re-issuing the old-format fallback's Drive
        # read a second time.
        existing_lang_data: Dict = existing_lang_data_by_lang[lang_id]

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
                print("    Create planar sheet")
            if plan["needs_diagnostics_sheet"] and diag_path_exists:
                print("    Create diagnostics sheet")
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
        folder_id = (
            existing_lang_data.get("folder_id")
            or doorway.get_or_create_folder(lang_id, parent_id=root_folder_id,
                                            identity=drive_door.folder("language", lang_id))
        )
        email = _annotator_email(lang_id)
        if email:
            try:
                # Checks first: re-granting access the annotator already has
                # fails under the drive.file scope once the folder holds files
                # the tooling didn't create, and printed a false warning.
                ensure_user_permission(doorway, folder_id, email, "reader")
            except Exception as _share_err:
                print(f"  [WARNING] Could not share folder for {lang_id}: {_share_err}")
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder:      {folder_url}")

        # Create collaborator notes doc if not already in the manifest. Its
        # name (sheet_spec.file_spec) uses the language's name from
        # languages.yaml — run `lookup-lang <lang_id>` first, or the doc is
        # named by the bare Glottocode.
        existing_notes_doc_id = existing_lang_data.get("notes_doc_id") or config.get(lang_id, {}).get("notes_doc_id")
        if not existing_notes_doc_id:
            try:
                existing_notes_doc_id = create_notes_doc(doorway, lang_id, folder_id)
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
            loader) because python -m coding lookup-lang may write a new entry
            earlier in the same session and we need the just-written state, not
            a cached snapshot.
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
                    problems = (
                        [f"name (run python -m coding lookup-lang {lid} first)"]
                        if no_name else []) + missing
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

        # The planar and diagnostics Sheets: read-only copies of their
        # sources, made here only if the language has none yet.
        input_sheet_info = _upload_lang_setup_as_sheets(
            doorway, planar_dir, lang_id, folder_id, existing_lang_data
        )

        if not force and existing_lang_data:
            existing_sheets = existing_lang_data.get("sheets", {})
            new_class_names = [c for c in all_classes if c not in existing_sheets]

            # A class that already has a sheet may still have gained a new
            # construction in its diagnostics YAML entry -- check every
            # existing class for that regardless of whether this language
            # also picked up brand-new classes this run (brand-new classes
            # are handled separately below via classes_to_create).
            added_any = False
            for cls, constructions_list in all_classes.items():
                if cls not in existing_sheets:
                    continue
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
                    doorway.open_spreadsheet(ss_id), cls, new_cons, lang_id,
                    element_index, _planar_path,
                )
                existing_cls_info.setdefault("constructions", []).extend(
                    [c for c, _, _ in new_cons]
                )
                existing_cls_info.setdefault("construction_params", {}).update(new_params)
                existing_lang_data["sheets"][cls] = existing_cls_info

            if not new_class_names:
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

        # --force was already checked against existing_lang_data for every
        # language in the preflight pass above, before any language's sheets
        # were touched -- no need to check again here.
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
                doorway, folder_id, lang_id, class_name, constructions, element_index,
                planar_path=planar_file,
            )
            lang_data["sheets"][class_name] = sheet_info
            print(f"    URL: {sheet_info['url']}\n")

        full_manifest[lang_id] = lang_data
        merged_config[lang_id] = lang_data

        # Upload the full merged config to Drive after each language so partial
        # progress is saved even if a later language fails.
        existing_config_file_id = upload_manifest(
            doorway, merged_config, root_folder_id, existing_config_file_id
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
    final_file_id = upload_manifest(
        doorway, merged_config, root_folder_id, existing_config_file_id
    )
    config["_planars_config_file_id"] = final_file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {final_file_id})")

    # Write local manifest with all languages (gitignored, kept for reference)
    MANIFEST_PATH.write_text(json.dumps(full_manifest, indent=2), encoding="utf-8")
    print(f"\nLocal manifest written to: {MANIFEST_PATH.name}")
    print(f"drive_config.json written.")

    print("\nEach language's folder and sheets are shared with the annotator named in "
          "people.yaml; for a language with none listed, add one there and re-run with --apply.")

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
    doorway = get_doorway()
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
    file_id = upload_manifest(doorway, merged_config, root_folder_id, existing_file_id)
    config["_planars_config_file_id"] = file_id
    _save_drive_config(config)
    print(f"manifest.json uploaded (id: {file_id})")
    print(f"drive_config.json written.")


if __name__ == "__main__":
    if "--push-manifest" in sys.argv:
        push_manifest()
    else:
        main()
