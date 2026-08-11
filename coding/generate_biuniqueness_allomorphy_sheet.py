#!/usr/bin/env python3
"""Generate the allomorphy prescreening sheet (issue #254 Part 2c).

Background: the biuniqueness/allomorphy mechanism (#249, #58, #254) is being built
and tested entirely on `synth0001` before touching real data. The
Biuniqueness_Scope column in planar_{lang_id}.tsv (filled / open_category /
excluded, per element) decides which elements appear here; it was added by #254
Part 2a and backfilled onto synth0001 by Part 2b. This script reads those flags and
writes the prescreening tab: a real Drive Sheet where the coordinator and Adam do a
first coarse pass over every in-scope element.

Prescreening, not "Stage 1"
---------------------------
#254 describes this pipeline as Stage 0 → 1 → 2, and that numbering collides with
the one already in diagnostic_classes.yaml, where "Stage 1" glosses the
*prescreening* construction of nonpermutability, coreference and phrasal_accent —
their first step, not their second. This pipeline counted the planar column as
Stage 0, so its Stage 1 was the second step: same label, off by one, two pipelines.

Renamed 2026-08-02 to the word the project already had. It is the same job those
prescreening tabs do — an element-level first pass whose answers decide what rows
the next sheet has — so it takes the same name, and the numbering goes away with
it. What #254 calls Stage 0 is just the planar column; what it calls Stage 2 will
be a second tab in this spreadsheet, named when Part 2e builds it.

Which biuniqueness deviation this is
------------------------------------
Biuniqueness is a one-to-one match between form and meaning, and it fails in two
directions. This screens one of them; the other is a class already:

  biuniqueness_exponence   one meaning carried by several pieces at once, in
                           different positions (circumfixes are the two-piece
                           case). A class in diagnostic_classes.yaml, with a
                           criterion, a qualification rule, and a span.
  biuniqueness_allomorphy  one meaning carried by different forms depending on
                           context. This file. Not a class — see below.

Both were called "biuniqueness" until 2026-08-02, when the class took the
narrower name it had always meant and this work took the other half.

Why this isn't a class
----------------------
Three reasons, in order of how hard they are to work around:

1. No span. Every class in diagnostic_classes.yaml earns its place by feeding a
   qualification_rule and a span computation. How allomorphy feeds one is #254
   Part 2i — an open question. Adding a class now would mean writing down an
   answer nobody has.
2. `Members` grows the inventory rather than filtering it. A prescreening tab
   narrows an existing row set (which elements are accent-eligible, so which
   pairs to generate). `Members` asks for forms that are not in the planar at
   all, and the member-expansion tab (#254 Part 2e) turns each into its own row.
   Nothing in the pipeline lets an annotation add lexical items downstream.
3. Which column applies depends on the row. `filled` rows want has_allomorphs,
   `open_category` rows want Members. The diagnostics YAML gives one criterion
   set per construction, applied to every row alike; `construction_criteria`
   varies by construction, nothing varies by row.

If (1) is ever settled, the has_allomorphs half is prescreening-shaped and could
become a construction. `Members` probably never fits.

The cost of staying outside: none of the standard machinery applies. import-sheets
does not collect this sheet, validate-coding does not check it, it is not under
the manifest's `sheets`, and nothing archives it on change. It is write-only
until the member-expansion tab exists. Mirrors generate_status_sheet.py's
precedent of a purpose-built generator using drive.py's primitives directly.

Row shape: one row per (Position_Name, Element) pair where Biuniqueness_Scope is not
"excluded". Two annotation columns cover both scope values, since which one applies is
row-dependent (see banner written into the sheet):
    - Biuniqueness_Scope == "filled":        fill has_allomorphs (y/n); leave Members blank.
    - Biuniqueness_Scope == "open_category":  fill Members (comma-separated candidate
                                               forms); leave has_allomorphs blank. The
                                               member-expansion tab (#254 Part 2e, not yet
                                               built) turns each listed member into its
                                               own row.

Run from the repo root:
    python -m coding generate-biuniqueness-allomorphy-sheet --lang synth0001            # dry run
    python -m coding generate-biuniqueness-allomorphy-sheet --lang synth0001 --apply

Re-running with --apply regenerates the existing biuniqueness_allomorphy_{lang_id}
spreadsheet in place (found by name within the language's Drive folder) rather than
minting a new URL, same convention as generate_status_sheet.py. has_allomorphs/
Members/Notes are carried over by (Position_Name, Element) rather than wiped —
only elements no longer in scope lose their annotation.

Sharing: shared as writer with Adam's email (adamjamesrosstallman@gmail.com) — issue
#254 Part 2d/2j explicitly names Adam as exercising this flow. synth0001 has no
per-language annotator_email in languages.yaml (it's a synthetic test language, not a
real onboarded one), so the usual _annotator_email() lookup doesn't apply here.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
MANIFEST_PATH = ROOT / "sheets_manifest.json"

import pandas as pd

from .drive import (
    load_manifest,
    upload_manifest,
    get_or_create_spreadsheet,
    _with_retry,
    _load_drive_config,
    _save_drive_config,
)
from .drive_doorway import get_doorway
from .validate_planar import _tokenize_elements

_ADAM_EMAIL = "adamjamesrosstallman@gmail.com"
_HEADER = ["Position_Name", "Element", "Biuniqueness_Scope", "has_allomorphs", "Members", "Notes"]
_HAS_ALLOMORPHS_COL = _HEADER.index("has_allomorphs")


# ---------------------------------------------------------------------------
# Pure logic: no API calls (unit tested)
# ---------------------------------------------------------------------------

def _build_prescreening_rows(planar_df: pd.DataFrame) -> List[Dict[str, str]]:
    """Return one row dict per (Position_Name, Element) with Biuniqueness_Scope != excluded.

    Raises ValueError if the Biuniqueness_Scope column is absent (backfill not run
    yet — see migrations/backfill_biuniqueness_scope_synth0001.py, #254 Part 2b) or
    has drifted out of token-alignment with Elements.
    """
    if "Biuniqueness_Scope" not in planar_df.columns:
        raise ValueError(
            "planar_df has no Biuniqueness_Scope column — run the Part 2b backfill "
            "migration for this language first (see #254)"
        )

    rows: List[Dict[str, str]] = []
    for _, row in planar_df.iterrows():
        position_name = str(row.get("Position_Name", "")).strip()
        elements = _tokenize_elements(str(row.get("Elements", "")).strip())
        scopes = _tokenize_elements(str(row.get("Biuniqueness_Scope", "")).strip())
        if len(elements) != len(scopes):
            raise ValueError(
                f"row '{position_name}': Elements has {len(elements)} token(s) but "
                f"Biuniqueness_Scope has {len(scopes)} — backfill has drifted; "
                f"re-run the migration or fix by hand"
            )
        for element, scope in zip(elements, scopes):
            if scope == "excluded":
                continue
            rows.append({"position_name": position_name, "element": element, "scope": scope})
    return rows


def _rows_to_sheet_values(
    rows: List[Dict[str, str]],
    existing: Dict[Tuple[str, str], Dict[str, str]] = None,
) -> List[List[str]]:
    """Header + data rows. has_allomorphs/Members/Notes are carried over from
    `existing` (keyed by (Position_Name, Element)) when a row's key is still
    present; blank for rows with no prior annotation (new elements) or no
    `existing` at all (first run).
    """
    existing = existing or {}
    values = [_HEADER]
    for r in rows:
        prior = existing.get((r["position_name"], r["element"]), {})
        values.append([
            r["position_name"], r["element"], r["scope"],
            prior.get("has_allomorphs", ""), prior.get("Members", ""), prior.get("Notes", ""),
        ])
    return values


def _banner_rows() -> List[List[str]]:
    """Instructions written above the header row (issue #254 Part 2c/2d)."""
    return [
        ["ALLOMORPHY PRESCREENING — a first pass over every in-scope element "
         "(allomorphy is a biuniqueness deviation; issue #254 Part 2). "
         "For each row below, fill in ONE of the two annotation columns depending "
         "on that row's Biuniqueness_Scope:"],
        ["  Biuniqueness_Scope = 'filled':        fill has_allomorphs (y/n). Leave Members blank."],
        ["  Biuniqueness_Scope = 'open_category':  fill Members with a comma-separated list of "
         "specific candidate forms in this category worth checking (e.g. for AD-S: probably, "
         "certainly, ...). Leave has_allomorphs blank."],
        ["Use Notes for anything else worth flagging. Message the coordinator when this tab is done."],
        [""],
    ]


# ---------------------------------------------------------------------------
# Drive helpers (API calls — not unit tested; see docs/tooling-design.md)
# ---------------------------------------------------------------------------

def _existing_annotations(ws) -> Dict[Tuple[str, str], Dict[str, str]]:
    """Read the current tab's has_allomorphs/Members/Notes, keyed by
    (Position_Name, Element). Returns {} for a brand-new/empty tab.

    Locates the header row by content (matching _HEADER) rather than assuming
    a fixed offset, so a banner-text change doesn't silently break carry-over.
    """
    values = _with_retry(ws.get_all_values)
    try:
        header_idx = values.index(_HEADER)
    except ValueError:
        return {}
    annotations: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in values[header_idx + 1:]:
        if len(row) < 2 or not row[0]:
            continue
        annotations[(row[0], row[1])] = {
            "has_allomorphs": row[3] if len(row) > 3 else "",
            "Members": row[4] if len(row) > 4 else "",
            "Notes": row[5] if len(row) > 5 else "",
        }
    return annotations


def _write_prescreening_tab(ss, rows: List[Dict[str, str]]):
    """Write banner + header + data rows, freeze/bold the header, and add the
    has_allomorphs y/n dropdown. has_allomorphs/Members/Notes are carried over
    from whatever the tab already had, keyed by (Position_Name, Element) — a
    structural regeneration (planar changed) must not silently discard
    annotation Adam already entered, the same principle every other
    sheet-generation path in this project follows. Only rows for elements no
    longer in scope lose their annotation, since there's no new row to carry
    it to. Structural content (Position_Name/Element/Biuniqueness_Scope) is
    always rebuilt fresh from the current planar, same as before.
    """
    ws = _with_retry(lambda: ss.sheet1)
    if ws.title != "prescreening":
        _with_retry(lambda: ws.update_title("prescreening"))
    existing = _existing_annotations(ws)
    ws.clear()

    banner = _banner_rows()
    header_row_idx = len(banner)
    values = banner + _rows_to_sheet_values(rows, existing)
    n_cols = len(_HEADER)
    n_data_rows = len(rows)

    _with_retry(lambda: ws.resize(rows=max(len(values) + 2, 10), cols=n_cols))
    _with_retry(lambda: ws.update(values, "A1", raw=False))

    requests = [
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": header_row_idx + 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": header_row_idx, "endRowIndex": header_row_idx + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": n_cols},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }},
        *[
            {"mergeCells": {
                "range": {"sheetId": ws.id, "startRowIndex": i, "endRowIndex": i + 1,
                          "startColumnIndex": 0, "endColumnIndex": n_cols},
                "mergeType": "MERGE_ALL",
            }}
            for i in range(len(banner) - 1)
        ],
        {"setDataValidation": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": header_row_idx + 1, "endRowIndex": header_row_idx + 1 + n_data_rows,
                "startColumnIndex": _HAS_ALLOMORPHS_COL, "endColumnIndex": _HAS_ALLOMORPHS_COL + 1,
            },
            "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ("y", "n")]},
                "showCustomUi": True,
                "strict": False,
            },
        }},
        {"repeatCell": {
            "range": {"sheetId": ws.id},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }},
    ]
    _with_retry(lambda: ss.batch_update({"requests": requests}))
    return ws


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding generate-biuniqueness-allomorphy-sheet`."""
    apply = "--apply" in sys.argv
    if "--lang" not in sys.argv:
        raise SystemExit("Usage: generate-biuniqueness-allomorphy-sheet --lang LANG_ID [--apply]")
    lang_id = sys.argv[sys.argv.index("--lang") + 1]

    lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
    planar_path = lang_setup_dir / f"planar_{lang_id}.tsv"
    if not planar_path.exists():
        raise SystemExit(f"No planar_{lang_id}.tsv found under {lang_setup_dir}")

    planar_df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    try:
        rows = _build_prescreening_rows(planar_df)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    n_filled = sum(1 for r in rows if r["scope"] == "filled")
    n_open = sum(1 for r in rows if r["scope"] == "open_category")
    print(f"{'DRY RUN — ' if not apply else ''}Allomorphy prescreening for {lang_id}: "
          f"{len(rows)} row(s) ({n_filled} filled, {n_open} open_category)")
    for r in rows:
        print(f"    {r['position_name']:24s} {r['element']:20s} {r['scope']}")

    if not apply:
        print("\nRun with --apply to create/update the sheet on Drive.")
        return

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    lang_data = manifest.get(lang_id)
    if not lang_data or not lang_data.get("folder_id"):
        raise SystemExit(f"No Drive folder found for {lang_id} in the manifest — run python -m coding generate-sheets --apply first.")

    sheet_name = f"biuniqueness_allomorphy_{lang_id}"
    ss, created = get_or_create_spreadsheet(
        doorway, lang_data["folder_id"], sheet_name)
    _write_prescreening_tab(ss, rows)
    # Named person, not "anyone with the link" — see drive._share_with_person
    # for why unpublished research data is shared this way.
    doorway.create_permission(ss.id, type="user", role="writer",
                              email=_ADAM_EMAIL, notify=False)
    action = "Created" if created else "Updated"
    print(f"\n{action}: {ss.url}")

    if lang_data.get("biuniqueness_allomorphy_spreadsheet_id") != ss.id:
        lang_data["biuniqueness_allomorphy_spreadsheet_id"] = ss.id
        lang_data["biuniqueness_allomorphy_url"] = ss.url
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        config = _load_drive_config()
        existing_file_id = config.get("_planars_config_file_id")
        root_folder_id = config.get("_root_folder_id")
        file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
        config["_planars_config_file_id"] = file_id
        _save_drive_config(config)
        print("Manifest updated on Drive (biuniqueness_allomorphy_spreadsheet_id/url).")


if __name__ == "__main__":
    main()
