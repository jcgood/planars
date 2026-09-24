"""Draw every chart for one language: export its bundle, then render it.

Drawing a language by hand means two commands -- the exporter
(``scripts/analysis/export_planarsviz_data.py``) and the renderer
(``scripts/render_planarsviz.R``) -- with options between them that have to
agree: the dataset's files, its root position, its groupings, its display
name, and the four permutation tests. This command works all of that out
from the dataset name, prints the two commands in full, and with
``--apply`` runs them. It holds no analysis or drawing code of its own and
adds no setting the two scripts don't already have (plan
``docs/PLAN_ccdb_planarsviz.md`` step 3a).

Where each setting comes from, first match wins:

1. ``planar_tables/chart_settings_<dataset>.json``, if present: optional keys
   ``language_name``, ``groupings``, ``root_position``, ``planar_type``,
   ``forest_axis``.
   For a language set up by hand (nyan1308 has one, for its display name).
2. ``planar_tables/ccdb_<dataset>.json``, written by
   ``scripts/analysis/import_ccdb.py`` for every CCDB structure: its root
   position, and its language name and planar type, shown as e.g.
   "Chácobo (verbal)"; the planar type also goes into axis titles
   ("Positions on the nominal planar structure"). A CCDB structure always
   uses the ``ccdb`` groupings and draws its per-type forests over the whole
   planar structure (``--forest-axis planar``). These are CCDB's facts, so they are read
   from the import's file rather than copied anywhere else.
3. The exporter's own defaults: root from the planar table's ``root``
   element, ``chichewa`` groupings, titles showing the dataset id, axis
   titles saying "verbal", per-type forests stopping at their own last
   position.

The domains file, planar table, display labels, highlights and conflict
groups are found by the exporter itself from the dataset name
(``domains/domains_<dataset>.tsv``, ``planar_tables/..._<dataset>.tsv``).

Bundles go to ``results/chart_data/<dataset>/``; charts to
``results/<dataset>/<topic>/``, beside every other language's. Runs from
anywhere: both scripts are run from ``NonCollaborative/``, which is what the
committed bundles record.

Usage:
    python scripts/planarsviz_language.py chac1251_verbal            # dry run
    python scripts/planarsviz_language.py chac1251_verbal --apply
    python scripts/planarsviz_language.py nyan1308 --apply --formats pdf,png
    python scripts/planarsviz_language.py mart1259_verbal --apply --no-permutations
    python scripts/planarsviz_language.py chac1251_verbal --apply --plots pooled_plot,spanchart
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

NC = Path(__file__).resolve().parents[1]

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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_settings(dataset: str) -> dict[str, tuple[object, str]]:
    """Each setting as (value, where it came from). None means the exporter's
    own default applies."""
    settings_file = NC / "planar_tables" / f"chart_settings_{dataset}.json"
    ccdb_file = NC / "planar_tables" / f"ccdb_{dataset}.json"
    settings = {
        "language_name": (None, "exporter default (titles show the dataset id)"),
        "groupings": (None, "exporter default (chichewa)"),
        "root_position": (None, "exporter default (the planar table's root element)"),
        "planar_type": (None, "exporter default (axis titles say verbal)"),
        "forest_axis": (None, "exporter default (subset)"),
    }
    if ccdb_file.exists():
        ccdb = read_json(ccdb_file)
        source = str(ccdb_file.relative_to(NC))
        settings["language_name"] = (f"{ccdb['language_name']} ({ccdb['planar_type']})", source)
        settings["groupings"] = ("ccdb", source)
        settings["planar_type"] = (ccdb["planar_type"], source)
        settings["forest_axis"] = ("planar", source)
        if ccdb.get("root_position") is not None:
            settings["root_position"] = (int(ccdb["root_position"]), source)
    if settings_file.exists():
        own = read_json(settings_file)
        unknown = sorted(set(own) - set(settings))
        if unknown:
            sys.exit(f"{settings_file.relative_to(NC)}: unknown key(s) {', '.join(unknown)}; "
                     f"known keys are {', '.join(settings)}.")
        source = str(settings_file.relative_to(NC))
        for key, value in own.items():
            settings[key] = (value, source)
    return settings


def export_command(dataset: str, settings: dict, permutations: int) -> list[str]:
    cmd = [sys.executable, "scripts/analysis/export_planarsviz_data.py",
           "--domain-file", f"domains/domains_{dataset}.tsv"]
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
    cmd = ["Rscript", "scripts/render_planarsviz.R",
           "--bundle", f"results/chart_data/{dataset}", "--output", "results"]
    if formats:
        cmd += ["--formats", formats]
    if plots:
        cmd += ["--plots", plots]
    return cmd


def run(cmd: list[str], label: str) -> None:
    print(f"\n== {label} ==\n{shlex.join(cmd)}", flush=True)
    start = time.monotonic()
    completed = subprocess.run(cmd, cwd=NC)
    elapsed = time.monotonic() - start
    if completed.returncode != 0:
        sys.exit(f"{label} failed (exit code {completed.returncode}) after {elapsed:.0f} s; "
                 "nothing after it was run.")
    print(f"{label} finished in {elapsed:.0f} s.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export one language's chart bundle and render all its charts.")
    parser.add_argument("dataset", help="Dataset name, e.g. nyan1308 or chac1251_verbal")
    parser.add_argument("--apply", action="store_true",
                        help="Run both commands. Without it, only print what would run.")
    parser.add_argument("--permutations", type=int, default=5000, metavar="N",
                        help="Draws for each of the four permutation tests (default 5000, "
                             "what the committed bundles use).")
    parser.add_argument("--no-permutations", action="store_true",
                        help="Skip the four permutation tests: the export takes seconds "
                             "instead of minutes, but the bundle then has none of their "
                             "tables or charts.")
    parser.add_argument("--formats", help="Passed to the renderer, e.g. pdf,png (default pdf).")
    parser.add_argument("--plots", help="Passed to the renderer: only these charts "
                                        "(names as render_planarsviz.R --list prints them).")
    args = parser.parse_args()

    dataset = args.dataset
    domain_file = NC / "domains" / f"domains_{dataset}.tsv"
    planar_file = NC / "planar_tables" / f"planar_{dataset}.tsv"
    missing = [p for p in (domain_file, planar_file) if not p.exists()]
    if missing:
        sys.exit("Can't draw " + dataset + ": missing " +
                 " and ".join(str(p.relative_to(NC)) for p in missing) +
                 ". A CCDB structure gets both from scripts/analysis/import_ccdb.py; "
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
        print(f"\nWould run, from {NC.name}/:\n")
        print("  " + shlex.join(export_cmd))
        print("  " + shlex.join(render_cmd))
        print("\nNothing was run. Add --apply to run both.")
        return

    run(export_cmd, "Export")
    run(render_cmd, "Render")
    print(f"\nBundle: results/chart_data/{dataset}/   Charts: results/{dataset}/")


if __name__ == "__main__":
    main()
