#!/usr/bin/env python3
"""Capture live Drive/Sheets state to local fixtures. READ-ONLY.

    python -m coding capture-drive-state            # dry run: report what would be captured
    python -m coding capture-drive-state --apply    # write fixtures
    python -m coding capture-drive-state --apply --lang stan1293

Phase 0a of the data layer plan (docs/data-layer-implementation-plan.md).
Produces the fixtures the fake Drive doorway replays, so every command can be
tested end-to-end with no network.

**This command never writes to Drive.** It opens spreadsheets, reads values and
metadata, and writes only to the local fixture directory. It is the one live
Drive call permitted before Phase 9, and it is read-only.

Two halves, refrozen together
-----------------------------
The tests run each command against two saved inputs: the Sheets (recorded
here into ``coded_data/.test_fixtures/drive_state/``) and the language
folders as they stood locally (copied here into
``coded_data/.test_fixtures/coded_data/``). They must come from the same
moment, or a command under test sees "changes" between them that no one made.
So ``--apply`` replaces both for every language it captures, and nothing else
refreshes either. With ``--lang`` the other languages' entries are kept; for
a captured language, the recording of a sheet no longer in the manifest is
deleted (one whose capture just failed is kept as the last good copy). Never
normalise or hand-edit a saved file: re-run the capture. Until 2026-10-10
only the Sheets half was saved and the tests read the live folders, so Adam's
ordinary annotation work turned CI red.

Both halves live in planars-data, which is private, because they are real
annotation content and planars is public. After ``--apply``, regenerate the
saved test outputs, review the diff, and commit inside ``coded_data/``.

Why raw responses
-----------------
The plan requires the fake to be built from *recorded real responses* rather
than from the gspread documentation, because the API's subtleties are exactly
what gets guessed wrong. That only works if capture preserves what the API
actually returned. So:

**Nothing here normalizes, pads, trims, or rectangularizes.** In particular,
``get_all_values()`` returns ragged rows for partially-filled annotation tabs
and rectangular rows for fully-written ones, and different call sites in
``coding/`` depend on each behaviour (``generate_sheets.py`` guards for ragged
rows; ``import_sheets.py`` feeds the response straight into a DataFrame and
would break on them). A fake built from tidied fixtures would be uniformly
rectangular, silently fail to exercise the guarded paths, and give false
confidence. See docs/drive-protocol-surface.md § "Subtleties most likely to be
guessed wrong". If you are tempted to clean up a fixture, don't -- the mess is
the signal.

Each sheet's own grants are recorded too (not its owner's, not those it
inherits from its folder), so the fake starts shared as the live sheet is.
A person is recorded by the name people.yaml gives them, never by address;
the fake gives that name the address people.yaml has, which in tests is the
placeholder.

Tab order is likewise recorded as returned, not sorted: several code paths in
``generate_sheets.py`` detect ordering drift, and their failure mode when fed a
wrongly-ordered fake is silent.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .drive import (
    _download_file_json,
    _get_clients,
    _load_drive_config,
    _open_spreadsheet,
)
from .drive_door import _retry

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
# Inside planars-data (private), not tests/: this is real annotation content,
# and planars is a public repo. Dot-prefixed so nothing that lists language
# folders mistakes it for a language.
FIXTURE_ROOT = CODED_DATA / ".test_fixtures"
FIXTURE_DIR = FIXTURE_ROOT / "drive_state"
FROZEN_CODED_DATA = FIXTURE_ROOT / "coded_data"

# Spreadsheet roles recorded per language from the manifest/drive_config, beyond
# the per-class annotation sheets.
_SINGLETON_SHEET_KEYS = ("planar_spreadsheet_id", "diagnostics_spreadsheet_id")


def _capture_worksheet(ws, developer_metadata: List[Dict]) -> Dict:
    """Record one worksheet exactly as the API returned it.

    Deliberately does not pad, trim, or otherwise regularise ``values``.
    """
    values = _retry(ws.get_all_values)
    return {
        # The tab's labels (the Drive door's planars_tab_kind/planars_tab).
        "developer_metadata": developer_metadata,
        "title": ws.title,
        "sheet_id": ws.id,
        # Declared grid size, which is NOT the same as the used range and not
        # the same as len(values) -- callers that resize or insert dimensions
        # care about the declared size specifically.
        "row_count": ws.row_count,
        "col_count": ws.col_count,
        "values": values,
        # Recorded so a fake can reproduce raggedness faithfully rather than
        # inferring it, and so drift in fixture tidiness is detectable.
        "_shape": {
            "n_rows": len(values),
            "row_widths": [len(r) for r in values],
            "ragged": len({len(r) for r in values}) > 1,
        },
    }


def _capture_spreadsheet(gc, drive, spreadsheet_id: str, role: str) -> Dict:
    ss = _open_spreadsheet(gc, spreadsheet_id)
    # Order matters: worksheets() returns live tab order and several code paths
    # detect ordering drift from it. Do not sort.
    worksheets = _retry(ss.worksheets)
    meta = _retry(lambda: ss.fetch_sheet_metadata(params={
        "fields": "sheets(properties(sheetId),developerMetadata)"}))
    # Sorted by key: Google returns a tab's labels in no fixed order, and an
    # unsorted capture made every refreeze diff show them all as changed.
    tab_metadata = {s["properties"]["sheetId"]: sorted(
                        s.get("developerMetadata", []),
                        key=lambda m: (m.get("metadataKey", ""), m.get("metadataId", 0)))
                    for s in meta.get("sheets", [])}
    properties = _retry(lambda: drive.files().get(
        fileId=spreadsheet_id, fields="properties").execute()).get("properties", {})
    return {
        "role": role,
        "spreadsheet_id": spreadsheet_id,
        "title": ss.title,
        # The sheet's identity label (Drive properties; coding/drive_door.py),
        # sorted for the same reason as the tab labels.
        "properties": dict(sorted(properties.items())),
        "tab_order": [ws.title for ws in worksheets],
        "worksheets": [_capture_worksheet(ws, tab_metadata.get(ws.id, []))
                       for ws in worksheets],
        # Which tabs are locked (coding/locked_tabs.py), so the fake starts
        # from the same protections the live sheet has. Who may edit a
        # protected range is left out: it is the owner, by address, and
        # people are recorded by name or not at all.
        "protected_ranges": [{k: v for k, v in p.items()
                              if k not in ("editors", "requestingUserCanEdit")}
                             for ws in worksheets
                             for p in _retry(lambda: ss.list_protected_ranges(ws.id))],
        # Who the sheet is shared with (the owner left out; a grant inherited
        # from its folder marked so), so the fake starts from the same sharing.
        "permissions": _own_grants(drive, spreadsheet_id),
    }


def _own_grants(drive, file_id: str) -> List[Dict]:
    """A file's grants, the owner's left out, each person recorded by the
    name people.yaml gives them (None if it has none), never by address. A
    grant the file only inherits from its folder is marked ``inherited``:
    the sharing check counts it as access but not as the file's own
    (sheet_spec.sharing_differences). Until 2026-10-24 inherited grants were
    left out, so the stand-in Drive saw no access for a coordinator whose own
    grant Drive had dropped as redundant with the folder's."""
    from .people import name_for_email
    from .sheet_spec import is_own_grant
    perms = _retry(lambda: drive.permissions().list(
        fileId=file_id,
        fields="permissions(id,type,role,emailAddress,permissionDetails)").execute())
    grants = []
    for p in perms.get("permissions", []):
        if p.get("role") == "owner":
            continue
        grant = {"id": p["id"], "type": p["type"], "role": p["role"]}
        if p["type"] == "user":
            grant["person"] = name_for_email(p.get("emailAddress"))
        if not is_own_grant(p):
            grant["inherited"] = True
        grants.append(grant)
    return grants


def _plan(manifest: Dict, langs: List[str]) -> List[tuple]:
    """Return [(lang_id, role, spreadsheet_id), ...] to capture. No network."""
    targets = []
    for lang_id in langs:
        entry = manifest.get(lang_id, {})
        for key in _SINGLETON_SHEET_KEYS:
            if entry.get(key):
                targets.append((lang_id, key.replace("_spreadsheet_id", ""), entry[key]))
        for class_name, info in sorted((entry.get("sheets") or {}).items()):
            sid = info.get("spreadsheet_id") or info.get("id")
            if sid:
                targets.append((lang_id, f"class:{class_name}", sid))
    return targets


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding capture-drive-state`."""
    ap = argparse.ArgumentParser(
        description="Capture live Drive/Sheets state to local fixtures. READ-ONLY."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write fixtures (default: dry run, reports what would be captured)",
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

    print("Connecting to Google APIs (read-only)...")
    gc, drive = _get_clients()
    config = _load_drive_config()
    file_id = config.get("_planars_config_file_id")
    manifest = _download_file_json(drive, file_id) if file_id else {}
    if not manifest:
        raise SystemExit("No manifest found on Drive — nothing to capture.")

    langs = [lang_filter] if lang_filter else sorted(
        k for k, v in manifest.items() if isinstance(v, dict) and not k.startswith("_")
    )
    targets = _plan(manifest, langs)

    if not apply:
        print(f"\nDRY RUN — would capture {len(targets)} spreadsheet(s) "
              f"across {len(langs)} language(s) into {FIXTURE_DIR.relative_to(ROOT)}:\n")
        for lang_id, role, sid in targets:
            print(f"  {lang_id:<12} {role:<34} {sid}")
        print(f"\nand replace the frozen local folders in "
              f"{FROZEN_CODED_DATA.relative_to(ROOT)} for: {', '.join(langs)}")
        print("\nNo Drive writes occur in either mode; --apply only writes local files.")
        print("Re-run with --apply to write fixtures.")
        return

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    # The manifest is Drive state too, and the fake needs it: it is what every
    # command reads to learn which spreadsheet holds which class. Recorded
    # verbatim, same rule as everything else here.
    (FIXTURE_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    captured, failed = [], []

    for lang_id, role, sid in targets:
        label = f"{lang_id}/{role}"
        try:
            print(f"  capturing {label} ...")
            data = _capture_spreadsheet(gc, drive, sid, role)
        except Exception as exc:
            # Keep going: a partial fixture set is far more useful than none,
            # and a single unreadable sheet should not lose the whole run.
            print(f"    ERROR: {exc}")
            failed.append((label, str(exc)))
            continue

        out = FIXTURE_DIR / lang_id / f"{role.replace(':', '_')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        captured.append({
            "lang_id": lang_id, "role": role, "spreadsheet_id": sid,
            # Relative to FIXTURE_DIR, so the folder can move without edits.
            "path": str(out.relative_to(FIXTURE_DIR)),
            "tabs": len(data["worksheets"]),
            "ragged_tabs": sum(1 for w in data["worksheets"] if w["_shape"]["ragged"]),
        })

    # With --lang, keep the other languages' entries: rewriting the index from
    # this run alone would silently drop them from every test.
    index_path = FIXTURE_DIR / "index.json"
    kept = []
    if index_path.exists():
        previous = json.loads(index_path.read_text(encoding="utf-8"))
        kept = [e for e in previous.get("spreadsheets", []) if e["lang_id"] not in langs]
    index = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "note": "Raw recorded API responses. Do not normalise, pad, or tidy — "
                "see coding/capture_drive_state.py for why raggedness is load-bearing.",
        "manifest": "manifest.json",
        "spreadsheets": kept + captured,
        "failed": failed,
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    # A recording of a sheet the manifest no longer lists (a retired class)
    # would otherwise sit here forever with nothing pointing at it. One whose
    # capture just failed is kept, as the last good copy.
    written = {e["path"] for e in captured}
    failed_labels = {label for label, _ in failed}
    for lang_id in langs:
        for old in sorted((FIXTURE_DIR / lang_id).glob("*.json")):
            rel = str(old.relative_to(FIXTURE_DIR))
            role = old.stem.replace("class_", "class:", 1)
            if rel not in written and f"{lang_id}/{role}" not in failed_labels:
                old.unlink()
                print(f"  removed {rel} (no longer in the manifest)")

    # The other half: the language folders as they stand locally right now.
    for lang_id in langs:
        src = CODED_DATA / lang_id
        dest = FROZEN_CODED_DATA / lang_id
        if dest.exists():
            shutil.rmtree(dest)
        if src.exists():
            shutil.copytree(src, dest)
        else:
            print(f"  [WARNING] no local folder {src.relative_to(ROOT)} to freeze")

    total_tabs = sum(c["tabs"] for c in captured)
    total_ragged = sum(c["ragged_tabs"] for c in captured)
    print(f"\nCaptured {len(captured)} spreadsheet(s), {total_tabs} tab(s) "
          f"— {total_ragged} ragged.")
    if failed:
        print(f"{len(failed)} failed: " + ", ".join(l for l, _ in failed))
    print(f"Fixtures written to {FIXTURE_DIR.relative_to(ROOT)}")
    print(f"Local folders frozen to {FROZEN_CODED_DATA.relative_to(ROOT)}: {', '.join(langs)}")
    print("No Drive writes were performed.")
    print("\nNext: regenerate the saved test outputs, review the diff, then commit")
    print("the new fixtures inside coded_data/ (planars-data):")
    print("  PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/")
    print("  git diff tests/snapshots/coordinator/")
    print("  git -C coded_data add .test_fixtures")
    print("  git -C coded_data commit -m 'Refreeze test fixtures'")


if __name__ == "__main__":
    main()
