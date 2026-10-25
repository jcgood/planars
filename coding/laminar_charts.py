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
does the uploading. ``.github/workflows/laminar-charts.yml`` runs it with
``--apply`` after each daily refresh (Phase 4c).

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
File IDs are saved to ``drive_config.json`` after each upload. When a PDF
is created (so it has a new link), the language's status sheet is rebuilt
at once (``generate-status-sheet --lang LANG --apply``), since it links
each PDF and the daily refresh rebuilds it before this runs.

A language that fails (its spans can't be read, R fails, an upload fails)
is reported and skipped, the others still run, and the command exits
non-zero at the end, so a workflow running it fails and says so.

**Nothing from the annotation reaches the output.** The workflow's log is
public (the repository is), so whatever the span code, the exporter or the
renderer print (element names, span labels, R's messages) is held back
(``_private``), and a failure says only which language failed and at what
stage, with the command that shows the reason on a coordinator's machine
(``python -m laminar.contributor_charts``). Upload errors and R setup
problems say nothing about the annotation and are shown.

**The issue.** A run over every language with ``--apply`` files (or
rewrites) one ``laminar-charts-error`` issue listing the languages that
failed, and closes it when none did. A ``--lang`` run leaves the issue as
it is, since it saw only one language.

Needs R and the packages ``planarsviz/DESCRIPTION`` lists when anything is
to be drawn (checked first: ``laminar.charts.preflight``; if they are
missing, every language to be drawn counts as failed); a dry run needs
neither, nor Drive access.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import drive_door, file_door, issues, state_files
from .drive import _load_drive_config, _save_drive_config, create_or_update_file
from .drive_doorway import get_doorway

ROOT = Path(__file__).resolve().parent.parent
ISSUE_LABEL = "laminar-charts-error"


@dataclass
class Failure:
    """One language that wasn't drawn: at what stage, and (only when it says
    nothing about the annotation) why."""
    lang_id: str
    stage: str
    detail: str = ""

    def line(self) -> str:
        from planars.languages import get_display_name
        return (f"{get_display_name(self.lang_id)}: {self.stage} failed"
                + (f": {self.detail}" if self.detail else ""))


@contextmanager
def _private():
    """Hold back whatever is printed inside: it can come from the annotation."""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        yield


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


def chart_links(lang_config: dict) -> list[tuple[str, str]]:
    """(label, URL) for each of a language's chart PDFs already on Drive,
    from its drive_config.json entry; for the status sheet's banner."""
    from laminar.contributor_charts import CONTRIBUTOR_DATASETS, GROUPING_WORDS
    return [(f"Charts {GROUPING_WORDS[g]}",
             f"https://drive.google.com/file/d/{lang_config[_file_key(g)]}/view")
            for g in CONTRIBUTOR_DATASETS if lang_config.get(_file_key(g))]


def _see_why(lang_id: str) -> str:
    return f"python -m laminar.contributor_charts {lang_id} /tmp/charts_{lang_id}"


def _run(apply: bool, only: str | None, force: bool) -> list[Failure]:
    from laminar import contributor_charts as cc
    from laminar.planars_language import NoSpansYet, span_table
    from planars.languages import get_display_name

    print(f"{'DRY RUN — ' if not apply else ''}Contributor charts")
    state = _load_state()
    drive_config = _load_drive_config()
    failed: list[Failure] = []
    to_draw = []
    for lang_id in _languages(only):
        name = get_display_name(lang_id)
        try:
            with _private():
                table = span_table(lang_id)
                fingerprint = cc.fingerprint(lang_id, table)
        except NoSpansYet:
            print(f"  {name}: no spans yet, nothing to draw")
            continue
        except Exception:
            failed.append(Failure(lang_id, "reading its spans"))
            print(f"  {failed[-1].line()}")
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
        return failed
    if to_draw:
        from laminar.charts import preflight
        try:
            preflight(None, apply=True)
        except SystemExit as exc:
            # R or its packages are missing: says nothing about the annotation.
            print(f"  {exc}")
            failed += [Failure(lang_id, "setting up R", str(exc).splitlines()[-1].lstrip("- "))
                       for lang_id, _t, _f in to_draw]
            return failed
        doorway = get_doorway()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for lang_id, table, fingerprint in to_draw:
        name = get_display_name(lang_id)
        folder_id = drive_config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            failed.append(Failure(lang_id, "uploading", "no folder_id in drive_config.json"))
            print(f"  {failed[-1].line()}")
            continue
        try:
            with tempfile.TemporaryDirectory() as work, _private():
                drawn = cc.draw(lang_id, Path(work), date, table=table)
        except Exception:
            failed.append(Failure(lang_id, "drawing"))
            print(f"  {failed[-1].line()}. To see why, run: {_see_why(lang_id)}")
            continue
        created = False
        try:
            for d in drawn:
                existing = drive_config[lang_id].get(_file_key(d.grouping))
                created = created or not existing
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
            failed.append(Failure(lang_id, "uploading", f"{type(exc).__name__}: {exc}"))
            print(f"  {failed[-1].line()}")
            continue
        state[lang_id] = {"fingerprint": fingerprint, "drawn": date,
                          "charts": {d.dataset: d.n_charts for d in drawn}}
        file_door.write_state(file_door.laminar_charts_state(),
                              json.dumps(state, indent=2, sort_keys=True) + "\n")
        if created:
            failure = _link_on_status_sheet(lang_id)
            if failure:
                failed.append(failure)
                print(f"  {failure.line()}")
                continue
        print(f"  {name}: done.")
    return failed


def _link_on_status_sheet(lang_id: str) -> Failure | None:
    """A chart PDF was created, so it has a new link: rebuild the language's
    status sheet now, which links each PDF (generate_status_sheet), rather
    than leave the link to the next daily refresh. Run as its own command,
    as the daily refresh runs it. Its output is held back like the rest."""
    import subprocess
    done = subprocess.run([sys.executable, "-m", "coding", "generate-status-sheet",
                           "--lang", lang_id, "--apply"],
                          cwd=ROOT, capture_output=True, text=True)
    if done.returncode == 0:
        print(f"  [{lang_id}] status sheet now links the charts.")
        return None
    return Failure(lang_id, "linking the charts on its status sheet",
                   f"run python -m coding generate-status-sheet --lang {lang_id} --apply")


def issue_body(failed: list[Failure], date: str) -> str:
    """The laminar-charts-error issue: which languages, at what stage, and
    the command that shows why. Never the reason itself when it could come
    from the annotation (this repository is public)."""
    lines = "\n".join(f"- {f.line()}" for f in failed)
    commands = "\n".join(_see_why(f.lang_id) for f in failed if f.stage in
                         ("reading its spans", "drawing"))
    see = ("\n\nThe reason is left out here, since it can quote the annotation and this "
           "repository is public. To see it, on a machine set up for the charts "
           "(coordinator guide § \"5. Laminar charts for a language\"), pull coded_data/ "
           f"and run:\n\n```bash\n{commands}\n```" if commands else "")
    return (
        f"## Contributor charts not drawn — {date}\n\n"
        "After today's daily refresh, these languages' charts could not be drawn or put "
        "on Drive, so their Drive folders still hold the previous ones:\n\n"
        f"{lines}{see}\n\n"
        "## What to do\n\n"
        "Fix the cause, then run `python -m coding laminar-charts --apply` (or wait for "
        "the next daily refresh, which runs it). This issue closes by itself when a run "
        "draws every language that needs it.\n")


def _report(failed: list[Failure], apply: bool, only: str | None) -> None:
    """File, rewrite or close the laminar-charts-error issue (full --apply runs only)."""
    if not apply:
        return
    if only is not None:
        print(f"(--lang: the {ISSUE_LABEL} issue is left as it is.)")
        return
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if failed:
        number, created = issues.file_issue(ISSUE_LABEL, f"Contributor charts not drawn ({date})",
                                            issue_body(failed, date), replace=True)
        print(f"{'Filed' if created else 'Updated'} issue #{number} ({ISSUE_LABEL}).")
    else:
        closed = issues.close_open(ISSUE_LABEL, f"Every language's charts drawn on {date} — closing.")
        if closed:
            print(f"Closed {', '.join(f'#{n}' for n in closed)} ({ISSUE_LABEL}).")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding laminar-charts`."""
    ap = argparse.ArgumentParser(
        description="Draw each language's contributor charts (by class, by domain type) "
                    "and put them in its Drive folder, when its spans have changed.")
    ap.add_argument("--apply", action="store_true",
                    help="draw and upload, and file or close the laminar-charts-error issue "
                         "(default: dry run, saying which languages would be drawn)")
    ap.add_argument("--lang", metavar="LANG_ID", help="only this language")
    ap.add_argument("--force", action="store_true",
                    help="draw even when nothing has changed since the last drawing")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding laminar-charts`."""
    if args is None:
        args = build_parser().parse_args()
    failed = _run(apply=args.apply, only=args.lang, force=args.force)
    _report(failed, args.apply, args.lang)
    if failed:
        sys.exit(f"\nFailed for {', '.join(f.lang_id for f in failed)}; the other languages "
                 "ran. The lines above say at what stage.")
    print("\nDone.")


if __name__ == "__main__":
    main()
