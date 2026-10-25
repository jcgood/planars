"""Draw each language's contributor charts and put them in its Drive folder.

Run from the repo root:
    python -m coding laminar-charts                  # dry run: which languages would be drawn
    python -m coding laminar-charts --apply          # draw and upload
    python -m coding laminar-charts --lang stan1293 --apply --force

docs/laminar-analysis-plan.md decision 6, Phase 4b. For contributors
checking their own data: for each language annotated through planars, two
PDFs in its Drive folder, ``charts_by_class_{lang}.pdf`` and
``charts_by_type_{lang}.pdf`` (``sheet_spec.file_spec``, kind ``charts``),
each every chart of that dataset drawn without the permutation tests, with
the date and how complete the annotation was above every page. What is drawn
and how is ``laminar/contributor_charts.py``; this command decides when and
does the uploading.

**When.** A language is drawn when what its charts come from has changed
since they were last drawn (``contributor_charts.fingerprint``: its spans,
its planar file, the chart code), or when either PDF is missing from
``drive_config.json``. What each language was last drawn from is
``state_files.LAMINAR_CHARTS_STATE_PATH``, written through the local-file
door after both PDFs are uploaded, so a run that fails partway draws that
language again next time. ``--force`` draws regardless. A language whose
annotation gives no spans yet is skipped.

**Uploads** go through the doorway (``drive.create_or_update_file``):
created on the first run, updated in place after that, so the links stay
the same. They carry no sharing of their own: the language folder already
lets its annotator read them (``sheet_spec`` sharing rule for ``charts``).
File IDs are saved to ``drive_config.json`` after each upload.

A language that fails (its spans can't be read, R fails, an upload fails)
is reported and skipped, the others still run, and the command exits
non-zero at the end, so a workflow running it fails and says so.

Needs R and the packages ``planarsviz/DESCRIPTION`` lists when anything is
to be drawn (checked first: ``laminar.charts.preflight``); a dry run needs
neither, nor Drive access.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import drive_door, file_door, state_files
from .drive import _load_drive_config, _save_drive_config, create_or_update_file
from .drive_doorway import get_doorway

ROOT = Path(__file__).resolve().parent.parent


def _languages(only: str | None) -> list[str]:
    """Every language annotated through planars (it has a planar file), or
    just `only`."""
    from laminar.planars_language import planar_file
    coded = ROOT / "coded_data"
    langs = sorted(d.name for d in coded.iterdir()
                   if d.is_dir() and not d.name.startswith(".") and planar_file(d.name).exists())
    if only is None:
        return langs
    if only not in langs:
        sys.exit(f"{only}: not a language annotated through planars here "
                 f"(no coded_data/{only}/lang_setup/planar_{only}.tsv). Languages: {', '.join(langs)}")
    return [only]


def _load_state() -> dict:
    path = state_files.LAMINAR_CHARTS_STATE_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _file_key(grouping: str) -> str:
    return f"charts_{grouping}_file_id"


def _run(apply: bool, only: str | None, force: bool) -> None:
    from laminar import contributor_charts as cc
    from laminar.planars_language import NoSpansYet, SpanTableError, span_table
    from planars.languages import get_display_name

    print(f"{'DRY RUN — ' if not apply else ''}Contributor charts")
    state = _load_state()
    drive_config = _load_drive_config()
    failed: list[str] = []
    to_draw = []
    for lang_id in _languages(only):
        name = get_display_name(lang_id)
        try:
            table = span_table(lang_id)
            fingerprint = cc.fingerprint(lang_id, table)
        except NoSpansYet:
            print(f"  {name}: no spans yet, nothing to draw")
            continue
        except (SpanTableError, cc.DrawingFailed) as exc:
            print(f"  {name}: ERROR: {exc}")
            failed.append(lang_id)
            continue
        ids = drive_config.get(lang_id, {})
        missing = [g for g in cc.CONTRIBUTOR_DATASETS if not ids.get(_file_key(g))]
        if force:
            why = "--force"
        elif missing:
            why = "not on Drive yet"
        elif state.get(lang_id, {}).get("fingerprint") != fingerprint:
            why = "spans, planar or chart code changed"
        else:
            print(f"  {name}: up to date (drawn {state[lang_id].get('drawn')})")
            continue
        print(f"  {name}: {'drawing' if apply else 'would draw'} ({why})")
        to_draw.append((lang_id, table, fingerprint))

    if not apply:
        if to_draw:
            print("\nRun with --apply to draw and upload.")
        _finish(failed)
        return
    if to_draw:
        from laminar.charts import preflight
        preflight(None, apply=True)
        doorway = get_doorway()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for lang_id, table, fingerprint in to_draw:
        name = get_display_name(lang_id)
        folder_id = drive_config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            print(f"  [{lang_id}] ERROR: no folder_id in drive_config.json")
            failed.append(lang_id)
            continue
        try:
            with tempfile.TemporaryDirectory() as work:
                drawn = cc.draw(lang_id, Path(work), date, table=table)
            for d in drawn:
                existing = drive_config[lang_id].get(_file_key(d.grouping))
                file_id = create_or_update_file(doorway, d.pdf, folder_id, existing,
                                                identity=drive_door.charts(d.grouping, lang_id))
                drive_config[lang_id][_file_key(d.grouping)] = file_id
                # Saved after every upload, so a later failure can't lose
                # this file's ID and make the next run create a second one.
                _save_drive_config(drive_config)
                print(f"  [{lang_id}] {d.dataset}: {d.n_charts} charts, "
                      f"{'updated' if existing else 'created'}. "
                      f"https://drive.google.com/file/d/{file_id}/view")
        except Exception as exc:
            print(f"  [{lang_id}] ERROR: {exc}")
            failed.append(lang_id)
            continue
        state[lang_id] = {"fingerprint": fingerprint, "drawn": date,
                          "charts": {d.dataset: d.n_charts for d in drawn}}
        file_door.write_state(file_door.laminar_charts_state(),
                              json.dumps(state, indent=2, sort_keys=True) + "\n")
        print(f"  {name}: done.")
    _finish(failed)


def _finish(failed: list[str]) -> None:
    if failed:
        sys.exit(f"\nFailed for {', '.join(failed)}; the other languages ran. "
                 "The messages above say what went wrong.")
    print("\nDone.")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding laminar-charts`."""
    ap = argparse.ArgumentParser(
        description="Draw each language's contributor charts (by class, by domain type) "
                    "and put them in its Drive folder, when its spans have changed.")
    ap.add_argument("--apply", action="store_true",
                    help="draw and upload (default: dry run, saying which languages would be drawn)")
    ap.add_argument("--lang", metavar="LANG_ID", help="only this language")
    ap.add_argument("--force", action="store_true",
                    help="draw even when nothing has changed since the last drawing")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding laminar-charts`."""
    if args is None:
        args = build_parser().parse_args()
    _run(apply=args.apply, only=args.lang, force=args.force)


if __name__ == "__main__":
    main()
