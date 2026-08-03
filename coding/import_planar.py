"""import-planar — sync the planar spreadsheet between Drive and local TSV.

Run from the repo root:
    # Sheet -> TSV (default direction): download and sync locally
    python -m coding import-planar              # dry run: show what would change
    python -m coding import-planar --apply      # write updated planar TSVs
    python -m coding import-planar --lang LANG  # restrict to one language

    # TSV -> Sheet: push local planar TSV changes up to the Drive spreadsheet
    python -m coding import-planar --to-sheet             # dry run (all languages)
    python -m coding import-planar --to-sheet --apply     # upload to Sheet
    python -m coding import-planar --to-sheet --lang LANG

Sheet -> TSV (default):
    Reads the planar spreadsheet for each language (identified by
    planar_spreadsheet_id in drive_config.json), compares to the local
    planar_{lang_id}.tsv, and writes updated TSVs when content has changed.
    Archives the old file before overwriting.

    When --apply is used and changes are found, writes /tmp/planar_changes.json
    with structured diff information used by the data-refresh workflow to build
    the planar-changed issue body.

TSV -> Sheet (--to-sheet):
    The mirror direction, for when planar_{lang_id}.tsv is edited locally (e.g.
    by restructure-sheets --split-element/--rename-map/--rename-class, which
    read the local TSV as their source of truth). Uploads local content to the
    Drive spreadsheet so it doesn't go stale and get silently reverted by the
    next scheduled import-planar --apply (see issue #248 — that's exactly what
    happened to the #236 pronoun split). restructure-sheets --apply calls this
    automatically; run it by hand only if you edited the planar TSV some other
    way.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

# Where --apply leaves the structured diff for the data-refresh workflow, which
# reads this exact path to build the planar-changed issue body. Named rather
# than written inline so a test can point it somewhere harmless — a test suite
# that clobbers the real file would hand the workflow a diff nobody made.
PLANAR_CHANGES_PATH = Path("/tmp/planar_changes.json")


# ---------------------------------------------------------------------------
# Archive helper (same pattern as import_sheets._archive_tsv)
# ---------------------------------------------------------------------------

def _archive_tsv(path: Path, timestamp: str) -> Path:
    archive_dir = path.parent.parent / "archive" / path.parent.name
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / f"{path.stem}_{timestamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


# ---------------------------------------------------------------------------
# Sheet reading
# ---------------------------------------------------------------------------

def _read_sheet_df(ws, canonical_cols: list[str]) -> pd.DataFrame:
    from .drive import _with_retry
    rows = _with_retry(lambda: ws.get_all_values())
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    df = pd.DataFrame(data, columns=headers, dtype=str).fillna("")
    # Keep only the canonical TSV columns; fill any missing with ""
    return df.reindex(columns=canonical_cols, fill_value="")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda col: col.str.strip() if col.dtype == object else col).fillna("")


# ---------------------------------------------------------------------------
# Diff analysis
# ---------------------------------------------------------------------------

def _diff_positions(old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    """Compare position numbers and names between old and new planars."""
    def pos_map(df):
        result = {}
        for _, row in df.iterrows():
            raw = str(row.get("Position", "")).strip()
            if raw.isdigit():
                result[int(raw)] = str(row.get("Position_Name", "")).strip()
        return result

    old = pos_map(old_df)
    new = pos_map(new_df)

    added = {n: new[n] for n in sorted(set(new) - set(old))}
    deleted = {n: old[n] for n in sorted(set(old) - set(new))}
    renamed = {
        n: (old[n], new[n])
        for n in sorted(set(old) & set(new))
        if old[n] != new[n]
    }

    # Infer pos-remap pairs by matching position names across numberings
    old_by_name = {v: k for k, v in old.items()}
    new_by_name = {v: k for k, v in new.items()}
    remaps = sorted(
        (old_by_name[name], new_by_name[name])
        for name in old_by_name
        if name in new_by_name and old_by_name[name] != new_by_name[name]
    )

    return {
        "added": {str(k): v for k, v in added.items()},
        "deleted": {str(k): v for k, v in deleted.items()},
        "renamed": {str(k): list(v) for k, v in renamed.items()},
        "remaps": [[o, n] for o, n in remaps],
    }


def _recommend(diff: dict, lang_id: str) -> str:
    if diff["deleted"] or diff["renamed"] or diff["remaps"]:
        flags = " ".join(f"--rename-map {o}:{n}" for o, n in diff["remaps"])
        note = "  # verify remap flags before running" if diff["remaps"] else ""
        cmd = f"python -m coding restructure-sheets --lang {lang_id}"
        if flags:
            cmd += f" {flags}"
        cmd += " --apply"
        if note:
            cmd += note
        return cmd
    elif diff["added"]:
        return "python -m coding update-sheets --apply"
    else:
        return "(content-only changes — no sheet structural updates needed)"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def import_planar(lang_ids: list[str] | None = None, apply: bool = False) -> list[str]:
    """Download planar spreadsheets from Drive and sync to local TSVs.

    Returns list of language IDs whose planars changed.
    """
    from .drive import _load_drive_config, _with_retry
    from .drive_doorway import get_doorway

    cfg = _load_drive_config()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    all_changes: dict[str, dict] = {}
    written_files: list[Path] = []

    for lang_id, lang_cfg in cfg.items():
        if lang_id.startswith("_"):
            continue
        if lang_ids and lang_id not in lang_ids:
            continue

        sheet_id = lang_cfg.get("planar_spreadsheet_id")
        if not sheet_id:
            continue

        tsv_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
        if not tsv_path.exists():
            print(f"\n{lang_id}: no local planar TSV — skipping")
            continue

        print(f"\n{lang_id}", flush=True)

        try:
            ss = get_doorway().open_spreadsheet(sheet_id)
            ws = _with_retry(lambda: ss.sheet1)
            old_df = pd.read_csv(tsv_path, sep="\t", dtype=str).fillna("")
            new_df = _read_sheet_df(ws, list(old_df.columns))
        except Exception as exc:
            print(f"  ERROR reading planar sheet: {exc}")
            continue

        if new_df.empty:
            print("  planar sheet is empty — skipping")
            continue

        if _normalize(old_df).equals(_normalize(new_df)):
            print("  up to date")
            continue

        diff = _diff_positions(old_df, new_df)
        rec = _recommend(diff, lang_id)

        for n, name in diff["added"].items():
            print(f"  + position {n} ({name})")
        for n, name in diff["deleted"].items():
            print(f"  - position {n} ({name})")
        for n, (old_name, new_name) in diff["renamed"].items():
            print(f"  ~ position {n}: {old_name} → {new_name}")
        if not any([diff["added"], diff["deleted"], diff["renamed"]]):
            print("  (content-only changes)")
        print(f"  → {rec}")

        all_changes[lang_id] = {"diff": diff, "recommendation": rec}

        if apply:
            archived = _archive_tsv(tsv_path, timestamp)
            print(f"  archived → archive/lang_setup/{archived.name}")
            new_df.to_csv(tsv_path, sep="\t", index=False)
            print(f"  wrote planar_{lang_id}.tsv")
            written_files.extend([tsv_path, archived])

    if apply and all_changes:
        PLANAR_CHANGES_PATH.write_text(json.dumps(all_changes, indent=2))
        from .drive import _autocommit_data
        langs = ", ".join(sorted(all_changes.keys()))
        _autocommit_data(
            written_files,
            f"data: import planar for {langs} from Google Sheets {datetime.now(timezone.utc).date().isoformat()}",
        )
    elif not apply and all_changes:
        print("\nDry run — rerun with --apply to write changes.")

    return list(all_changes.keys())


# ---------------------------------------------------------------------------
# TSV -> Sheet (push local planar changes up to Drive)
# ---------------------------------------------------------------------------

def push_planar_to_sheet(lang_id: str, cfg: dict, apply: bool) -> bool:
    """Push local planar_{lang_id}.tsv to the Drive planar spreadsheet.

    Mirror of the download direction in import_planar(): reads the local TSV,
    diffs it against the live Sheet, and on apply clears+rewrites the Sheet to
    match. Returns True if a change was made (or would be, in dry-run).
    """
    from .drive import _with_retry
    from .drive_doorway import get_doorway

    lang_cfg = cfg.get(lang_id, {})
    sheet_id = lang_cfg.get("planar_spreadsheet_id")
    if not sheet_id:
        print(f"  [{lang_id}] No planar_spreadsheet_id in drive_config.json — skipping")
        return False

    tsv_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    if not tsv_path.exists():
        print(f"  [{lang_id}] No local planar TSV — skipping")
        return False

    local_df = pd.read_csv(tsv_path, sep="\t", dtype=str).fillna("")

    try:
        ss = get_doorway().open_spreadsheet(sheet_id)
        ws = _with_retry(lambda: ss.sheet1)
        sheet_df = _read_sheet_df(ws, list(local_df.columns))
    except Exception as exc:
        print(f"  [{lang_id}] ERROR reading planar sheet: {exc}")
        return False

    if _normalize(local_df).equals(_normalize(sheet_df)):
        print(f"  [{lang_id}] Sheet already up to date")
        return False

    diff = _diff_positions(sheet_df, local_df)
    for n, name in diff["added"].items():
        print(f"  [{lang_id}]   + position {n} ({name})")
    for n, name in diff["deleted"].items():
        print(f"  [{lang_id}]   - position {n} ({name})")
    for n, (old_name, new_name) in diff["renamed"].items():
        print(f"  [{lang_id}]   ~ position {n}: {old_name} -> {new_name}")
    if not any([diff["added"], diff["deleted"], diff["renamed"]]):
        print(f"  [{lang_id}]   (content-only changes)")

    if apply:
        new_rows = [list(local_df.columns)] + [list(row) for _, row in local_df.iterrows()]
        _with_retry(ws.clear)
        _with_retry(lambda: ws.update(new_rows, "A1"))
        print(f"  [{lang_id}] Updated -> planar Sheet")
    else:
        print(f"  [{lang_id}] Would update -> planar Sheet (use --apply to write)")

    return True


def push_planars_to_sheets(lang_ids: list[str] | None = None, apply: bool = False) -> list[str]:
    """Push local planar TSVs to their Drive spreadsheets for all (or selected) languages.

    Returns list of language IDs whose Sheet changed (or would change).
    """
    from .drive import _load_drive_config

    cfg = _load_drive_config()

    changed = []
    for lang_id in cfg:
        if lang_id.startswith("_"):
            continue
        if lang_ids and lang_id not in lang_ids:
            continue
        print(f"\n{lang_id}", flush=True)
        if push_planar_to_sheet(lang_id, cfg, apply):
            changed.append(lang_id)

    if not apply and changed:
        print("\nDry run — rerun with --apply to write changes.")

    return changed


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sync the planar spreadsheet between Drive and local TSV."
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", action="append", dest="langs",
        help="restrict to this language (repeatable)",
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
    )
    ap.add_argument(
        "--to-sheet", action="store_true",
        help="push local planar TSV changes up to the Drive spreadsheet "
             "(default direction is Sheet -> TSV)",
    )
    args = ap.parse_args()
    if args.to_sheet:
        push_planars_to_sheets(lang_ids=args.langs, apply=args.apply)
    else:
        import_planar(lang_ids=args.langs, apply=args.apply)
    sys.exit(0)
