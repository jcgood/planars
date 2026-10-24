"""Draw every chart for a dataset: export its bundle, then render it.

``python -m laminar charts``. Drawing a dataset by hand means two commands,
the exporter (``laminar/export_planarsviz_data.py``) and the renderer
(``laminar/render_planarsviz.R``), with options between them that have to
agree: the dataset's files, its root position, its groupings, its display
name and the four permutation tests. This command works all of that out
from the dataset name, prints the two commands in full, and with
``--apply`` runs them. It holds no analysis or drawing code of its own and
adds no setting the two scripts don't already have.

Where each setting comes from (a dataset's own settings file, its CCDB
import file, or the exporter's defaults) is ``laminar/datasets.py``'s
dataset_settings(), which the standalone analysis scripts read too. The
domains file, planar table, display labels, highlights and conflict groups
are found by the exporter itself from the dataset name.

Bundles go to ``NonCollaborative/results/chart_data/<dataset>/``; charts to
``NonCollaborative/results/<dataset>/<topic>/``. Runs from anywhere: both
scripts run from the repository root, and a bundle records the files it
read relative to that root.

``--ccdb`` does the same for every CCDB structure (each one
``import_ccdb.py`` wrote a ``planar_tables/ccdb_<Planar_ID>.json`` for),
several at a time. A structure that fails does not stop the others. Each
one's full output goes to ``NonCollaborative/results/ccdb_batch/<Planar_ID>.log``
and a summary to ``results/ccdb_batch/summary.md``, saying per structure:

- whether the export and render worked, and which charts failed, with the
  renderer's reason;
- which kinds of chart it has none of, when other structures do (the
  renderer leaves a chart out when the bundle has nothing for it, e.g. no
  conflict groups -- normal, but worth knowing);
- anything worth a look before trusting a chart: very few families, a family
  with more spans than the 26 letters two charts name spans with, very long
  structures, characters in a title or label the standard PDF fonts can't
  draw (those charts are drawn with Quartz, or cairo off a Mac), truncated
  permutation draws.

``--summary-only`` rewrites that summary from the logs and bundles already
there, without running anything.

Usage:
    python -m laminar charts chac1251_verbal            # dry run
    python -m laminar charts chac1251_verbal --apply
    python -m laminar charts nyan1308 --apply --formats pdf,png
    python -m laminar charts mart1259_verbal --apply --no-permutations
    python -m laminar charts chac1251_verbal --apply --plots pooled_plot,spanchart
    python -m laminar charts --ccdb                     # dry run: list what would run
    python -m laminar charts --ccdb --apply             # all 21, four at a time
    python -m laminar charts --ccdb --apply --only chac1251_nominal,mart1259_verbal
    python -m laminar charts --ccdb --summary-only
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from laminar.datasets import NC, REPO, dataset_settings

# The four permutation tests, each switched on by its own exporter flag. A
# re-export without one of them drops that test's tables from the bundle, so
# they are always passed together.
PERMUTATION_FLAGS = [
    "--fragmentation-permutations",
    "--boundary-strength-test-permutations",
    "--span-placement-permutations",
    "--arbitrary-layers-permutations",
]
# One table each test writes, to tell whether a bundle already has them.
PERMUTATION_TABLES = [
    "fragmentation_test.tsv",
    "boundary_strength_test.tsv",
    "span_placement_test.tsv",
    "arbitrary_layers_test.tsv",
]

BATCH_DIR = NC / "results" / "ccdb_batch"

# What counts as worth a look in the CCDB summary. Each threshold is where a
# chart is known to start misbehaving (see CCDB_PLANARSVIZ_PROGRESS.md
# "Likely trouble"); the first run's two commonest notes -- boundary
# strengths under the overlay's every-50 gridlines, and test labels too long
# for the pooled canvas -- were fixed in the charts, so they are no longer
# reported.
FEW_FAMILIES = 2           # exemplary and conflict-group charts have little to show
SPAN_LETTER_LIMIT = 26     # ghost_trees.R / conflict_groups.R name spans a..z
LONG_STRUCTURE = 40        # positions; widest canvases and longest label rows


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


# ── One dataset ─────────────────────────────────────────────────────────────

def export_command(dataset: str, settings: dict, permutations: int) -> list[str]:
    cmd = [sys.executable, "-m", "laminar.export_planarsviz_data",
           "--domain-file", rel(NC / "domains" / f"domains_{dataset}.tsv")]
    flags = {"groupings": "--groupings", "root_position": "--root-position",
             "language_name": "--language-name", "planar_type": "--planar-type",
             "forest_axis": "--forest-axis"}
    for key, flag in flags.items():
        value = settings[key][0]
        if value is not None:
            cmd += [flag, str(value)]
    if permutations:
        for flag in PERMUTATION_FLAGS:
            cmd += [flag, str(permutations)]
    return cmd


def render_command(dataset: str, formats: str | None, plots: str | None) -> list[str]:
    cmd = ["Rscript", "laminar/render_planarsviz.R",
           "--bundle", rel(NC / "results" / "chart_data" / dataset),
           "--output", rel(NC / "results")]
    if formats:
        cmd += ["--formats", formats]
    if plots:
        cmd += ["--plots", plots]
    return cmd


def run(cmd: list[str], label: str) -> None:
    print(f"\n== {label} ==\n{shlex.join(cmd)}", flush=True)
    start = time.monotonic()
    completed = subprocess.run(cmd, cwd=REPO)
    elapsed = time.monotonic() - start
    if completed.returncode != 0:
        sys.exit(f"{label} failed (exit code {completed.returncode}) after {elapsed:.0f} s; "
                 "nothing after it was run.")
    print(f"{label} finished in {elapsed:.0f} s.", flush=True)


def draw_one(args: argparse.Namespace) -> None:
    dataset = args.dataset
    domain_file = NC / "domains" / f"domains_{dataset}.tsv"
    planar_file = NC / "planar_tables" / f"planar_{dataset}.tsv"
    missing = [p for p in (domain_file, planar_file) if not p.exists()]
    if missing:
        sys.exit("Can't draw " + dataset + ": missing " +
                 " and ".join(rel(p) for p in missing) +
                 ". A CCDB structure gets both from `python -m laminar.import_ccdb --apply`; "
                 "a language set up by hand needs both written first.")
    if args.apply and shutil.which("Rscript") is None:
        sys.exit("Rscript is not on the PATH, so the charts can't be rendered.")

    permutations = 0 if args.no_permutations else args.permutations
    settings = dataset_settings(dataset)
    export_cmd = export_command(dataset, settings, permutations)
    render_cmd = render_command(dataset, args.formats, args.plots)

    print(f"Dataset {dataset}")
    for key, (value, source) in settings.items():
        shown = "-" if value is None else value
        print(f"  {key:14s} {shown!s:32s} from {source}")
    print(f"  {'permutations':14s} {permutations if permutations else 'off'!s:32s} "
          f"{'all four tests' if permutations else ''}")

    bundle_data = NC / "results" / "chart_data" / dataset / "data"
    had_tests = [t for t in PERMUTATION_TABLES if (bundle_data / t).exists()]
    if not permutations and had_tests:
        print(f"\nNote: the current bundle has permutation-test tables ({', '.join(had_tests)}); "
              "exporting without the tests removes them, and their charts with them.")

    if not args.apply:
        print("\nWould run, from the repository root:\n")
        print("  " + shlex.join(export_cmd))
        print("  " + shlex.join(render_cmd))
        print("\nNothing was run. Add --apply to run both.")
        return

    run(export_cmd, "Export")
    run(render_cmd, "Render")
    print(f"\nBundle: {rel(NC / 'results' / 'chart_data' / dataset)}/   "
          f"Charts: {rel(NC / 'results' / dataset)}/")


# ── Every CCDB structure ────────────────────────────────────────────────────

def pdf_can_draw(char: str) -> bool:
    """Whether R's default PDF device can draw this character. Its standard
    fonts use the Windows Latin-1 encoding; anything outside it (IPA such as
    ʔ or ɛ, a separate combining accent) would come out as a period, so the
    renderer draws a chart containing one with Quartz (cairo off a Mac)."""
    try:
        char.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def ccdb_datasets() -> list[str]:
    return sorted(p.stem[len("ccdb_"):] for p in (NC / "planar_tables").glob("ccdb_*.json"))


def one_dataset_args(dataset: str, args: argparse.Namespace) -> list[str]:
    """The `charts <dataset>` options a --ccdb run passes on to each structure."""
    extra = [dataset, "--apply"]
    if args.permutations_given:
        extra += ["--permutations", str(args.permutations)]
    if args.no_permutations:
        extra.append("--no-permutations")
    if args.formats:
        extra += ["--formats", args.formats]
    return extra


def run_in_batch(dataset: str, args: argparse.Namespace) -> tuple[str, int, float]:
    cmd = [sys.executable, "-m", "laminar", "charts", *one_dataset_args(dataset, args)]
    log = BATCH_DIR / f"{dataset}.log"
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as out:
        out.write("$ " + " ".join(cmd) + "\n")
        out.flush()
        code = subprocess.run(cmd, cwd=REPO, stdout=out, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - start
    with log.open("a", encoding="utf-8") as out:
        out.write(f"\n[batch] exit code {code} after {elapsed:.0f} s\n")
    print(f"{dataset}: exit {code} after {elapsed:.0f} s", flush=True)
    return dataset, code, elapsed


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def chart_kind(name: str) -> str:
    """A chart name with its numbers taken out, so tree 3 of one forest and
    tree 7 of another count as the same kind of chart."""
    name = re.sub(r"_tree_\d+$", "_tree_N", name)
    return re.sub(r"exemplary_trees_(slide_)?\d+", r"exemplary_trees_\1N", name)


def parse_log(log: Path) -> dict:
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    result = {"ran": bool(text), "exit": None, "seconds": None, "export_ok": False,
              "render_line": None, "failed": {}}
    if m := re.search(r"\[batch\] exit code (-?\d+) after (\d+) s", text):
        result["exit"], result["seconds"] = int(m.group(1)), int(m.group(2))
    result["export_ok"] = "Export finished in" in text
    if m := re.search(r"^(\d+ files for \d+ of \d+ charts.*?);", text, re.M):
        result["render_line"] = m.group(1)
    for m in re.finditer(r"^FAILED (\S+): (.*)$", text, re.M):
        result["failed"][m.group(1)] = m.group(2)
    if not result["export_ok"] and text:
        # The last few lines are where a Python traceback ends.
        result["tail"] = "\n".join(text.rstrip().splitlines()[-6:])
    return result


def bundle_notes(dataset: str) -> tuple[dict, list[str]]:
    data = NC / "results" / "chart_data" / dataset / "data"
    meta_path = data / "metadata.json"
    if not meta_path.exists():
        return {}, ["no bundle"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    notes = []
    n_fam = meta.get("n_maximal_families", 0)
    if n_fam <= FEW_FAMILIES:
        notes.append(f"only {n_fam} famil{'y' if n_fam == 1 else 'ies'}: exemplary and "
                     "conflict-group charts have little to show")
    largest = max((int(r["n_spans"]) for r in read_tsv(data / "families.tsv")), default=0)
    if largest > SPAN_LETTER_LIMIT:
        notes.append(f"largest family has {largest} spans, more than the {SPAN_LETTER_LIMIT} "
                     "letters ghost_trees/conflict_groups name spans with")
    if meta.get("n_positions", 0) > LONG_STRUCTURE:
        notes.append(f"{meta['n_positions']} positions: check label crowding")
    labels = [r["Test_Labels"] for r in read_tsv(data / "tests.tsv")]
    drawn = labels + [meta.get("language_name") or ""]
    undrawable = sorted({c for text in drawn for c in text if not pdf_can_draw(c)})
    if undrawable:
        notes.append("text the standard PDF fonts can't draw (" + " ".join(undrawable) +
                     "): the renderer draws the charts that show it with Quartz (cairo off a Mac); "
                     "check their fonts look right")
    for table in ("span_placement_test.tsv", "arbitrary_layers_test.tsv"):
        truncated = [r["group"] for r in read_tsv(data / table) if int(r.get("n_truncated") or 0)]
        if truncated:
            notes.append(f"{table}: truncated draws in {', '.join(truncated)}")
    if meta.get("root_position_source") != "--root-position":
        notes.append(f"root position from {meta.get('root_position_source')}, not CCDB's overlaps.tsv")
    return meta, notes


def rendered_kinds(dataset: str) -> set[str]:
    manifest = NC / "results" / dataset / f"{dataset}_planarsviz_manifest.tsv"
    return {chart_kind(r["chart"]) for r in read_tsv(manifest)}


def write_summary(datasets: list[str]) -> Path:
    rows = []
    for ds in datasets:
        log = parse_log(BATCH_DIR / f"{ds}.log")
        meta, notes = bundle_notes(ds)
        rows.append((ds, log, meta, notes, rendered_kinds(ds) | {chart_kind(c) for c in log["failed"]}))
    all_kinds = set().union(*(r[4] for r in rows)) if rows else set()

    lines = ["# CCDB batch: all structures through planarsviz", "",
             "Written by `python -m laminar charts --ccdb`; each structure's full output is "
             "in the `.log` beside this file.", "",
             "| Structure | Positions | Tests | Families | Export | Charts | Minutes |",
             "|---|---|---|---|---|---|---|"]
    for ds, log, meta, notes, _ in rows:
        if not log["ran"]:
            status, charts = "not run", ""
        else:
            status = "ok" if log["export_ok"] else "**failed**"
            charts = log["render_line"] or ""
            if log["failed"]:
                charts += f"; **{len(log['failed'])} failed**"
        minutes = f"{log['seconds'] / 60:.1f}" if log["seconds"] is not None else ""
        lines.append(f"| {ds} | {meta.get('n_positions', '')} | {meta.get('n_active_tests', '')} | "
                     f"{meta.get('n_maximal_families', '')} | {status} | {charts} | {minutes} |")

    failures = [(ds, log) for ds, log, *_ in rows if log["ran"] and (log["failed"] or not log["export_ok"])]
    lines += ["", "## What failed", ""]
    if not failures:
        lines.append("Nothing.")
    for ds, log in failures:
        if not log["export_ok"]:
            lines += [f"- **{ds}**: export failed:", "", "  ```", *("  " + l for l in log.get("tail", "").splitlines()), "  ```"]
        for chart, reason in log["failed"].items():
            lines.append(f"- **{ds}** `{chart}`: {reason}")

    # Grouped by chart, since one fix to a chart function fixes it everywhere.
    by_kind: dict[str, list[str]] = {}
    for ds, log, _, _, kinds in rows:
        if log["ran"] and log["export_ok"]:
            for kind in sorted(all_kinds - kinds):
                by_kind.setdefault(kind, []).append(ds)
    lines += ["", "## Charts a structure has none of (the bundle had nothing for them)", ""]
    lines += [f"- `{k}`: {', '.join(v)}" for k, v in sorted(by_kind.items())] or ["None."]

    lines += ["", "## Worth a look", ""]
    noted = [(ds, notes) for ds, _, _, notes, _ in rows if notes]
    lines += [f"- **{ds}**: " + "; ".join(notes) for ds, notes in noted] or ["Nothing."]

    path = BATCH_DIR / "summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def draw_ccdb(args: argparse.Namespace) -> None:
    datasets = ccdb_datasets()
    if args.only:
        wanted = args.only.split(",")
        unknown = sorted(set(wanted) - set(datasets))
        if unknown:
            sys.exit(f"Not a CCDB structure: {', '.join(unknown)}. `python -m laminar.import_ccdb "
                     "--apply` writes one planar_tables/ccdb_<Planar_ID>.json each.")
        datasets = [d for d in datasets if d in wanted]

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    if args.summary_only:
        print(f"Summary: {rel(write_summary(ccdb_datasets()))}")
        return
    if not args.apply:
        print(f"Would run, from the repository root, {args.jobs} at a time:\n")
        for ds in datasets:
            print("  python -m laminar charts " + " ".join(one_dataset_args(ds, args)))
        print(f"\n{len(datasets)} structures. Nothing was run. Add --apply to run them.")
        return

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda ds: run_in_batch(ds, args), datasets))
    print(f"\nAll {len(datasets)} done in {(time.monotonic() - start) / 60:.1f} min.")
    # The summary covers every structure, so an --only run's results sit
    # beside the earlier runs' rather than replacing them.
    print(f"Summary: {rel(write_summary(ccdb_datasets()))}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m laminar charts",
        description="Export a dataset's chart bundle and render all its charts "
                    "(or, with --ccdb, every CCDB structure's).")
    parser.add_argument("dataset", nargs="?", help="Dataset name, e.g. nyan1308 or chac1251_verbal")
    parser.add_argument("--ccdb", action="store_true",
                        help="Every CCDB structure instead of one dataset, several at a time, "
                             "with a summary in results/ccdb_batch/summary.md.")
    parser.add_argument("--apply", action="store_true",
                        help="Run. Without it, only print what would run.")
    parser.add_argument("--permutations", type=int, default=None, metavar="N",
                        help="Draws for each of the four permutation tests (default 5000, "
                             "what the committed bundles use).")
    parser.add_argument("--no-permutations", action="store_true",
                        help="Skip the four permutation tests: the export takes seconds "
                             "instead of minutes, but the bundle then has none of their "
                             "tables or charts.")
    parser.add_argument("--formats", help="Passed to the renderer, e.g. pdf,png (default pdf).")
    parser.add_argument("--plots", help="Passed to the renderer: only these charts "
                                        "(names as render_planarsviz.R --list prints them). "
                                        "One dataset only.")
    parser.add_argument("--only", help="With --ccdb: comma-separated Planar_IDs instead of all.")
    parser.add_argument("--jobs", type=int, default=4,
                        help="With --ccdb: structures run at once (default 4).")
    parser.add_argument("--summary-only", action="store_true",
                        help="With --ccdb: rewrite the summary from the existing logs and "
                             "bundles; run nothing.")
    args = parser.parse_args(argv)

    args.permutations_given = args.permutations is not None
    if args.permutations is None:
        args.permutations = 5000
    if args.ccdb == bool(args.dataset):
        parser.error("give either a dataset name or --ccdb, not both or neither")
    if not args.ccdb and (args.only or args.summary_only):
        parser.error("--only and --summary-only go with --ccdb")
    if args.ccdb and args.plots:
        parser.error("--plots is for one dataset; leave it out with --ccdb")

    if args.ccdb:
        draw_ccdb(args)
    else:
        draw_one(args)


if __name__ == "__main__":
    main()
