"""The weekly full analysis: every dataset, with the four permutation tests.

Run from the repo root:
    python -m coding laminar-analysis                    # dry run: what is behind its data
    python -m coding laminar-analysis --plan --apply --github-output FILE
    python -m coding laminar-analysis --lang stan1293 --dataset stan1293_types_all --apply
    python -m coding laminar-analysis --report '<planned JSON>' --apply

docs/laminar-analysis-plan.md decision 6, Phase 4d. The contributor charts
(laminar-charts, daily) leave the permutation tests out, since they take
nearly all the time; this runs them, once a week, for every dataset of every
language whose spans changed. ``.github/workflows/laminar-analysis.yml`` runs
it in three steps, one job each:

1. **``--plan``**: which (language, dataset) pairs are behind their data.
   With ``--apply`` it also makes each such language's ``analysis`` folder
   on Drive (inside its language folder; ID in ``drive_config.json``), so
   the parallel jobs never race to make it, and writes the list for the
   workflow (``--github-output``: ``matrix=`` and ``count=`` lines). Only
   language and dataset names are written: the list goes into the public log.
2. **``--lang L --dataset D``**, one job per pair, side by side: builds the
   dataset from the annotation in a temporary folder, exports it with the
   four tests (``PERMUTATIONS`` draws each, seed 0, as ``python -m laminar
   charts`` does), draws it, uploads one PDF, ``analysis_{grouping}_{selection}_{lang}.pdf``
   (Drive kind ``analysis_charts``; ``laminar/contributor_charts.draw_dataset``),
   into the analysis folder, and then commits the bundle to planars-data
   through the local-file door, under ``.bundles/{lang}/{dataset}/``
   (``file_door.BundleFile``; plan decision 5 and the 2026-11-01 decision
   to keep full bundles there for now). The PDF is found by its label each
   time, not by an ID in drive_config.json, so parallel jobs never write
   that file at once.
3. **``--report``**, after every job has finished: each planned pair whose
   committed bundle the job did not replace (its fingerprint is still the
   one the plan saw, carried in the list as ``was``) failed, as did each
   language whose spans could not be read. Files (or rewrites) one
   ``laminar-analysis-error`` issue naming them, or closes it when none did.

**Behind its data** means the dataset's fingerprint (its domains file, the
planar file, the chart code's git version and ``PERMUTATIONS``) differs from
the one in its committed bundle's ``run.json``, or there is no bundle. The
bundle is the record: there is no separate state file to fall out of step
with it. ``run.json`` is written last, after the upload, so a job that fails
partway leaves the pair behind and it runs again next week.

**Which languages.** Every language annotated through planars (it has a
planar file) and with spans, except the made-up test languages (IDs starting
``synth``; Jeff, 2026-11-01): the daily contributor charts still draw those.

**Bundles outgrow planars-data** at 30-40 languages (the raw permutation
draws are rewritten whole on any span change). The plan's answer is #333 (a
small results file per language committed, the full bundle zipped on Drive).
So no one has to remember it, ``--plan --apply`` files a ``design`` issue
(``MOVE_TITLE``, once) when the run would leave bundles for a third language.

**Nothing from the annotation reaches the output.** The workflow's log and
the issue are public (the repository is): whatever the span code, exporter
and renderer print is held back, and a failure says only the language,
dataset and stage, with the command that shows the reason locally.
"""
from __future__ import annotations

import argparse
import hashlib
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
ISSUE_LABEL = "laminar-analysis-error"
PERMUTATIONS = 5000          # draws per test; laminar/charts.py's default
RUN_RECORD = "run.json"      # in each committed bundle, written last
MOVE_LABEL = "design"
MOVE_TITLE = "Weekly analysis bundles: move them out of planars-data (#333)"
MOVE_AT = 3                  # languages with bundles at which the move is filed


@dataclass(frozen=True)
class Pair:
    """One (language, dataset); `was` is its committed bundle's fingerprint
    when the run was planned ("" for none), how the report tells whether
    the job replaced it."""
    lang_id: str
    dataset: str
    was: str = ""

    @property
    def part(self) -> str:
        """The dataset less its language: ``types_all`` (the Drive name)."""
        return self.dataset.removeprefix(f"{self.lang_id}_")

    def as_dict(self) -> dict:
        return {"lang": self.lang_id, "dataset": self.dataset, "was": self.was}


@contextmanager
def _private():
    """Hold back whatever is printed inside: it can come from the annotation."""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        yield


def _see_why(pair: Pair) -> str:
    return f"python -m laminar charts {pair.dataset} --apply"


def _see_why_lang(lang_id: str) -> str:
    return f"python -m laminar charts --lang {lang_id}"


def _languages(only: str | None) -> list[str]:
    """The languages the weekly run covers: laminar-charts' list less the
    made-up ones."""
    from .laminar_charts import _languages as annotated
    return [lang for lang in annotated(only) if not lang.startswith("synth")]


# ── Behind its data ─────────────────────────────────────────────────────────

def fingerprint(lang_id: str, dataset: str, table) -> str:
    """What one dataset's analysis is computed from, as one hash."""
    from laminar import contributor_charts as cc
    from laminar.planars_language import domains_frame, parse_dataset, planar_file, select
    _lang, grouping, selection = parse_dataset(dataset)
    digest = hashlib.sha256()
    digest.update(domains_frame(select(table, selection), grouping)
                  .to_csv(sep="\t", index=False).encode("utf-8"))
    digest.update(planar_file(lang_id).read_bytes())
    digest.update(cc.code_version().encode("utf-8"))
    digest.update(str(PERMUTATIONS).encode("utf-8"))
    return digest.hexdigest()


def committed_run(pair: Pair) -> dict:
    """The committed bundle's run record, or {} when there is none."""
    path = file_door.BundleFile(pair.lang_id, pair.dataset, RUN_RECORD).path
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def behind(only: str | None = None) -> tuple[list[tuple[Pair, str, str]], list[str], list[str]]:
    """Every (pair, fingerprint, why) behind its data; a line for each
    language left out (no spans yet, or its spans could not be read); and
    the languages whose spans could not be read."""
    from laminar.planars_language import NoSpansYet, dataset_names, span_table
    from planars.languages import get_display_name
    out, notes, unreadable = [], [], []
    for lang_id in _languages(only):
        try:
            with _private():
                table = span_table(lang_id)
                prints = {d: fingerprint(lang_id, d, table) for d in dataset_names(lang_id)}
        except NoSpansYet:
            notes.append(f"{get_display_name(lang_id)}: no spans yet, nothing to analyse")
            continue
        except Exception:
            notes.append(f"{get_display_name(lang_id)}: reading its spans failed. To see why, "
                         f"run: {_see_why_lang(lang_id)}")
            unreadable.append(lang_id)
            continue
        for dataset, fp in prints.items():
            was = committed_run(Pair(lang_id, dataset)).get("fingerprint", "")
            if not was:
                out.append((Pair(lang_id, dataset, was), fp, "no bundle yet"))
            elif was != fp:
                out.append((Pair(lang_id, dataset, was), fp, "spans, planar or code changed"))
    return out, notes, unreadable


# ── 1. The plan ─────────────────────────────────────────────────────────────

def plan(apply: bool, only: str | None, github_output: Path | None) -> list[Pair]:
    print(f"{'DRY RUN — ' if not apply else ''}Weekly analysis: what is behind its data")
    stale, notes, _unreadable = behind(only)
    for note in notes:
        print(f"  {note}")
    for pair, _fp, why in stale:
        print(f"  {pair.dataset}: {'to run' if apply else 'would run'} ({why})")
    if not stale:
        print("  every dataset is up to date")
    pairs = [p for p, _f, _w in stale]
    if apply and pairs:
        _make_analysis_folders(sorted({p.lang_id for p in pairs}))
        _file_move_issue(sorted({p.lang_id for p in pairs}))
    if github_output is not None:
        matrix = json.dumps({"include": [p.as_dict() for p in pairs]})
        with github_output.open("a", encoding="utf-8") as f:
            f.write(f"matrix={matrix}\ncount={len(pairs)}\n")
    if not apply and pairs:
        print("\nThe weekly workflow (laminar-analysis.yml) runs each one; to run one here: "
              "python -m coding laminar-analysis --lang LANG_ID --dataset DATASET --apply")
    return pairs


def _make_analysis_folders(langs: list[str]) -> None:
    """Each language's analysis folder on Drive, made once, before the
    parallel jobs that fill it."""
    config = _load_drive_config()
    doorway = None
    for lang_id in langs:
        if config.get(lang_id, {}).get("analysis_folder_id"):
            continue
        doorway = doorway or get_doorway()
        _folder_id(doorway, config, lang_id)


def _folder_id(doorway, config: dict, lang_id: str) -> str:
    """The language's analysis folder, made inside its language folder if
    there is none yet (and its ID saved)."""
    from .sheet_spec import ANALYSIS_FOLDER_NAME
    entry = config.get(lang_id, {})
    if entry.get("analysis_folder_id"):
        return entry["analysis_folder_id"]
    if not entry.get("folder_id"):
        raise RuntimeError(f"{lang_id} has no folder_id in drive_config.json")
    folder_id = doorway.get_or_create_folder(ANALYSIS_FOLDER_NAME, entry["folder_id"],
                                             identity=drive_door.folder("analysis", lang_id))
    entry["analysis_folder_id"] = folder_id
    _save_drive_config(config)
    print(f"  [{lang_id}] analysis folder: https://drive.google.com/drive/folders/{folder_id}")
    return folder_id


def _file_move_issue(planned_langs: list[str]) -> None:
    """When this run would leave bundles for MOVE_AT languages or more, file
    the move to a results file (#333) as a design issue, once."""
    langs = sorted(set(file_door.bundle_languages()) | set(planned_langs))
    if len(langs) < MOVE_AT or issues.find_open(MOVE_LABEL, title=MOVE_TITLE) is not None:
        return
    from planars.languages import get_display_name
    body = (
        "## Time to move the analysis bundles out of planars-data\n\n"
        f"This week's analysis leaves full bundles in planars-data's `.bundles/` for "
        f"{len(langs)} languages ({', '.join(get_display_name(l) for l in langs)}). The raw "
        "permutation draws are rewritten whole whenever a language's spans change, so "
        "planars-data's history grows fast from here.\n\n"
        "## What to do\n\n"
        "Build the move planned in #333 (docs/laminar-analysis-plan.md Phase 4d, "
        "\"Bundles\"): a small committed results file per language, the full bundle zipped "
        "in the Drive analysis folder. Then close this issue.\n")
    number = issues.create(MOVE_LABEL, MOVE_TITLE, body)
    print(f"Filed issue #{number} ({MOVE_LABEL}): bundles for {len(langs)} languages.")


# ── 2. One dataset ──────────────────────────────────────────────────────────

def run_one(pair: Pair, apply: bool, force: bool) -> str | None:
    """Analyse one dataset. Returns None, or the stage that failed."""
    from laminar import contributor_charts as cc
    from laminar.planars_language import NoSpansYet, parse_dataset, span_table

    if parse_dataset(pair.dataset) is None or not pair.dataset.startswith(f"{pair.lang_id}_"):
        sys.exit(f"{pair.dataset}: not a dataset of {pair.lang_id} "
                 "(<lang>_<types|classes>_<all|complete|partial|distinct>)")
    print(f"{'DRY RUN — ' if not apply else ''}Weekly analysis: {pair.dataset}")
    try:
        with _private():
            table = span_table(pair.lang_id)
            fp = fingerprint(pair.lang_id, pair.dataset, table)
    except NoSpansYet:
        print("  no spans yet, nothing to analyse")
        return None
    except Exception:
        return "reading its spans"
    if not force and committed_run(pair).get("fingerprint") == fp:
        print(f"  up to date (run {committed_run(pair).get('date')})")
        return None
    if not apply:
        print(f"  would run, with {PERMUTATIONS} draws per test (about an hour)")
        return None
    from laminar.charts import preflight
    try:
        preflight(None, apply=True)
    except SystemExit as exc:
        print(f"  {exc}")
        return "setting up R"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as work:
        try:
            with _private():
                drawn = cc.draw_dataset(pair.lang_id, pair.dataset, Path(work), date, table,
                                        permutations=PERMUTATIONS)
        except Exception:
            return "analysing and drawing"
        try:
            file_id = _upload(pair, drawn.pdf)
        except Exception as exc:
            print(f"  uploading failed: {type(exc).__name__}: {exc}")
            return "uploading"
        print(f"  {drawn.n_charts} charts: https://drive.google.com/file/d/{file_id}/view")
        n = _commit_bundle(pair, Path(work) / "chart_data" / pair.dataset,
                           {"fingerprint": fp, "date": date, "permutations": PERMUTATIONS,
                            "charts": drawn.n_charts})
    print(f"  bundle: {n} file(s) changed in planars-data "
          f".bundles/{pair.lang_id}/{pair.dataset}/")
    return None


def _upload(pair: Pair, pdf: bytes) -> str:
    """Create or update the dataset's PDF in the analysis folder. The file
    is found by its label, so no file ID is stored."""
    doorway = get_doorway()
    folder_id = _folder_id(doorway, _load_drive_config(), pair.lang_id)
    identity = drive_door.analysis_charts(pair.part, pair.lang_id)
    clauses = [f"properties has {{ key='{k}' and value='{v}' }}"
               for k, v in identity.labels().items()]
    found = [f for f in doorway.list_files(" and ".join(clauses + ["trashed=false"]),
                                           fields="files(id, name, properties)")
             if (f.get("properties") or {}).get(drive_door.STATE_LABEL) != drive_door.ARCHIVED]
    return create_or_update_file(doorway, pdf, folder_id, found[0]["id"] if found else None,
                                 identity=identity)


def _commit_bundle(pair: Pair, bundle: Path, record: dict) -> int:
    """Put the new bundle in planars-data: every file it has, none it no
    longer has, and the run record last. Returns how many files changed."""
    new = {str(p.relative_to(bundle)): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    if RUN_RECORD in new:
        raise RuntimeError(f"the exporter wrote a {RUN_RECORD}, the name kept for the run record")
    changed = 0
    for rel in file_door.bundle_files(pair.lang_id, pair.dataset):
        if rel not in new and rel != RUN_RECORD:
            changed += file_door.remove_bundle(file_door.BundleFile(pair.lang_id, pair.dataset, rel))
    for rel, content in sorted(new.items()):
        changed += file_door.write_bundle(file_door.BundleFile(pair.lang_id, pair.dataset, rel),
                                          content)
    changed += file_door.write_bundle(file_door.BundleFile(pair.lang_id, pair.dataset, RUN_RECORD),
                                      json.dumps(record, indent=2, sort_keys=True) + "\n")
    return changed


# ── 3. The report ───────────────────────────────────────────────────────────

def report(planned: list[Pair], apply: bool, run_url: str | None) -> bool:
    """File or close the issue. Failed: each planned pair whose job did not
    replace its bundle (not "still behind its data": a daily refresh during
    the run can move the data on after a job finished), and each language
    whose spans could not be read, so the plan left it out. True if
    anything failed."""
    failed = [p for p in planned if committed_run(p).get("fingerprint", "") == p.was]
    unreadable = behind()[2]
    print(f"Weekly analysis: {len(planned) - len(failed)} of {len(planned)} dataset(s) brought "
          "up to date" + (f"; not: {', '.join(p.dataset for p in failed)}" if failed else ""))
    if unreadable:
        print(f"Spans could not be read, so not analysed: {', '.join(unreadable)}")
    if not apply:
        return bool(failed or unreadable)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if failed or unreadable:
        number, created = issues.file_issue(ISSUE_LABEL, f"Weekly analysis not finished ({date})",
                                            issue_body(failed, unreadable, date, run_url),
                                            replace=True)
        print(f"{'Filed' if created else 'Updated'} issue #{number} ({ISSUE_LABEL}).")
    else:
        closed = issues.close_open(ISSUE_LABEL, f"Every dataset analysed on {date} — closing.")
        if closed:
            print(f"Closed {', '.join(f'#{n}' for n in closed)} ({ISSUE_LABEL}).")
    return bool(failed or unreadable)


def issue_body(failed: list[Pair], unreadable: list[str], date: str, run_url: str | None) -> str:
    """Which datasets and languages, and where to look. Never the reason
    itself, which can quote the annotation (this repository is public)."""
    from planars.languages import get_display_name
    lines = [f"- {get_display_name(p.lang_id)}: `{p.dataset}`" for p in failed]
    lines += [f"- {get_display_name(lang)}: every dataset (its spans could not be read)"
              for lang in unreadable]
    commands = "\n".join([_see_why(p) for p in failed] + [_see_why_lang(l) for l in unreadable])
    where = f" ([the run]({run_url}))" if run_url else ""
    return (
        f"## Weekly analysis not finished — {date}\n\n"
        f"This week's analysis{where} did not bring these datasets up to date, so their "
        "bundles in planars-data and their PDFs in the language's Drive `analysis` folder are "
        f"from an earlier run:\n\n" + "\n".join(lines) + "\n\n"
        "Each dataset's job log in the run says at what stage it failed (reading the spans, "
        "analysing and drawing, uploading, setting up R). The reason is left out, since it "
        "can quote the annotation and this repository is public. To see it, on a machine set "
        "up for the charts (coordinator guide § \"5. Laminar charts for a language\"), pull "
        f"coded_data/ and run:\n\n```bash\n{commands}\n```\n\n"
        "## What to do\n\n"
        "Fix the cause, then run the workflow again: `gh workflow run laminar-analysis.yml` "
        "(or wait for next week's run). This issue closes by itself when a run brings every "
        "dataset up to date.\n")


# ── Command line ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding laminar-analysis`."""
    ap = argparse.ArgumentParser(
        description="The weekly full analysis: every dataset of every language whose spans "
                    "changed, with the four permutation tests; bundles to planars-data, "
                    "charts to the language's Drive analysis folder.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true",
                      help="list the datasets behind their data (the default); with --apply, "
                           "also make the analysis folders on Drive")
    mode.add_argument("--dataset", metavar="DATASET",
                      help="analyse this one dataset (needs --lang)")
    mode.add_argument("--report", metavar="PLANNED_JSON",
                      help="after the jobs: the planned pairs ({\"include\": [{\"lang\", "
                           "\"dataset\", \"was\"}, ...]}, --plan's list) whose bundle was not "
                           "replaced failed")
    ap.add_argument("--lang", metavar="LANG_ID", help="only this language")
    ap.add_argument("--apply", action="store_true",
                    help="write: Drive, planars-data, issues (default: dry run)")
    ap.add_argument("--force", action="store_true",
                    help="with --dataset: run even when the bundle is up to date")
    ap.add_argument("--github-output", type=Path, metavar="FILE",
                    help="with --plan: append matrix= and count= lines here (GITHUB_OUTPUT)")
    ap.add_argument("--run-url", help="with --report: the workflow run, for the issue")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding laminar-analysis`."""
    if args is None:
        args = build_parser().parse_args()
    if args.dataset:
        if not args.lang:
            sys.exit("--dataset needs --lang.")
        pair = Pair(args.lang, args.dataset)
        stage = run_one(pair, args.apply, args.force)
        if stage:
            sys.exit(f"\n{pair.dataset}: {stage} failed. The reason is held back (it can quote "
                     f"the annotation). To see it locally: {_see_why(pair)}")
    elif args.report is not None:
        planned = [Pair(d["lang"], d["dataset"], d.get("was", ""))
                   for d in json.loads(args.report or '{"include": []}')["include"]]
        if report(planned, args.apply, args.run_url):
            sys.exit(1)
    else:
        plan(args.apply, args.lang, args.github_output)
    print("\nDone.")


if __name__ == "__main__":
    main()
