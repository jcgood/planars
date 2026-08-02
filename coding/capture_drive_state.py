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

Tab order is likewise recorded as returned, not sorted: several code paths in
``generate_sheets.py`` detect ordering drift, and their failure mode when fed a
wrongly-ordered fake is silent.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .drive import (
    _download_file_json,
    _get_clients,
    _load_drive_config,
    _open_spreadsheet,
    _with_retry,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "drive_state"

# Spreadsheet roles recorded per language from the manifest/drive_config, beyond
# the per-class annotation sheets.
_SINGLETON_SHEET_KEYS = ("planar_spreadsheet_id", "diagnostics_spreadsheet_id")


def _capture_worksheet(ws) -> Dict:
    """Record one worksheet exactly as the API returned it.

    Deliberately does not pad, trim, or otherwise regularise ``values``.
    """
    values = _with_retry(ws.get_all_values)
    return {
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


def _capture_spreadsheet(gc, spreadsheet_id: str, role: str) -> Dict:
    ss = _open_spreadsheet(gc, spreadsheet_id)
    # Order matters: worksheets() returns live tab order and several code paths
    # detect ordering drift from it. Do not sort.
    worksheets = _with_retry(ss.worksheets)
    return {
        "role": role,
        "spreadsheet_id": spreadsheet_id,
        "title": ss.title,
        "tab_order": [ws.title for ws in worksheets],
        "worksheets": [_capture_worksheet(ws) for ws in worksheets],
    }


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


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    lang_filter = args[args.index("--lang") + 1] if "--lang" in args else None

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
            data = _capture_spreadsheet(gc, sid, role)
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
            "path": str(out.relative_to(ROOT)),
            "tabs": len(data["worksheets"]),
            "ragged_tabs": sum(1 for w in data["worksheets"] if w["_shape"]["ragged"]),
        })

    index = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "note": "Raw recorded API responses. Do not normalise, pad, or tidy — "
                "see coding/capture_drive_state.py for why raggedness is load-bearing.",
        "manifest": "tests/fixtures/drive_state/manifest.json",
        "spreadsheets": captured,
        "failed": failed,
    }
    (FIXTURE_DIR / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    total_tabs = sum(c["tabs"] for c in captured)
    total_ragged = sum(c["ragged_tabs"] for c in captured)
    print(f"\nCaptured {len(captured)} spreadsheet(s), {total_tabs} tab(s) "
          f"— {total_ragged} ragged.")
    if failed:
        print(f"{len(failed)} failed: " + ", ".join(l for l, _ in failed))
    print(f"Fixtures written to {FIXTURE_DIR.relative_to(ROOT)}")
    print("No Drive writes were performed.")


if __name__ == "__main__":
    main()
