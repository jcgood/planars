"""What a dataset name means: its files, its settings, its planar structure.

A dataset is one structure's tests, named after its domains file
(``domains/domains_<dataset>.tsv``): nyan1308, or a CCDB structure such as
chac1251_verbal. Every script that takes a domains file works out the rest
from the name through this module, so a script run on its own analyses a
dataset exactly as its exported bundle does.

A language annotated through planars has datasets named
``<lang>_<grouping>_<selection>`` (``stan1293_types_all``), built by
laminar/planars_language.py. domain_file(), planar_file(), bundle_root()
and charts_root() say where each dataset's files are: for a planars
language, in planars-data (``coded_data/.analysis/<lang>/``) with the live
planar file; for the rest, under NonCollaborative/. Its settings come from
planars_language.py and the planar file (display name, groupings, the
keystone as root, planar type, forest axis "planar"); none of the rules
below apply to it.

dataset_settings(): each chart/analysis setting, first match wins:

1. ``planar_tables/chart_settings_<dataset>.json``, if present: optional keys
   ``language_name``, ``groupings``, ``root_position``, ``planar_type``,
   ``forest_axis``. For a language set up by hand (nyan1308 has one, for its
   display name).
2. ``planar_tables/ccdb_<dataset>.json``, written by ``import_ccdb.py`` for
   every CCDB structure: its root position, and its language name and planar
   type, shown as e.g. "Chácobo (verbal)". A CCDB structure always uses the
   ``ccdb`` groupings and draws its per-type forests over the whole planar
   structure. These are CCDB's facts, so they are read from the import's
   file rather than copied anywhere else.
3. The exporter's own defaults (value None here): root from the planar
   table's ``root`` element, ``chichewa`` groupings, titles showing the
   dataset id, axis titles saying "verbal", per-type forests stopping at
   their own last position.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from laminar.planars_groupings import GROUPINGS

REPO = Path(__file__).resolve().parents[1]
# Where Chichewa's and the CCDB structures' inputs and outputs live
# (domains/, planar_tables/, results/). Their paths are frozen
# (docs/laminar-analysis-plan.md decision 8); every module reads this one.
NC = REPO / "NonCollaborative"


def repo_relative(path: Path) -> str:
    """How a bundle records a file it read: relative to the repository root
    when it is inside it, so the record is the same wherever the command was
    run from."""
    path = Path(path).resolve()
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)

# The exporter's --groupings default, and so every dataset's unless its
# settings say otherwise.
DEFAULT_GROUPINGS = "chichewa"


def dataset_name(domain_file: str | Path) -> str:
    """``domains_<dataset>.tsv`` -> ``<dataset>``."""
    return Path(domain_file).stem.removeprefix("domains_")


def _planars(dataset: str):
    """(lang_id, grouping, selection) for a planars language's dataset, else
    None (laminar/planars_language.py says what the names mean)."""
    from laminar.planars_language import parse_dataset
    return parse_dataset(dataset)


def domain_file(dataset: str) -> Path:
    planars = _planars(dataset)
    if planars:
        from laminar.planars_language import domains_dir
        return domains_dir(planars[0]) / f"domains_{dataset}.tsv"
    return NC / "domains" / f"domains_{dataset}.tsv"


def planar_file(dataset: str) -> Path:
    planars = _planars(dataset)
    if planars:
        from laminar.planars_language import planar_file as live_planar
        return live_planar(planars[0])
    return NC / "planar_tables" / f"planar_{dataset}.tsv"


def bundle_root(dataset: str) -> Path:
    """The folder a dataset's bundle folder goes in: planars-data for a
    planars language (decision 5 of docs/laminar-analysis-plan.md), else
    NonCollaborative/results/chart_data/."""
    planars = _planars(dataset)
    if planars:
        from laminar.planars_language import analysis_dir
        return analysis_dir(planars[0]) / "chart_data"
    return NC / "results" / "chart_data"


def charts_root(dataset: str) -> Path:
    """The folder the renderer draws a dataset's charts under. For a planars
    language, a folder planars-data's .gitignore leaves out: charts are not
    committed (decision 5)."""
    planars = _planars(dataset)
    if planars:
        from laminar.planars_language import analysis_dir
        return analysis_dir(planars[0]) / "charts"
    return NC / "results"


def planar_position_count(planar_path: Path | None) -> int | None:
    """Number of positions in the planar table, or None without one.

    The table's rows are its positions; the exporter's
    load_position_labels() separately checks they run 1..N with no gaps.
    """
    if planar_path is None or not planar_path.exists():
        return None
    with planar_path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle, delimiter="\t"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_settings(dataset: str) -> dict[str, tuple[object, str]]:
    """Each setting as (value, where it came from). None means the exporter's
    own default applies."""
    settings_file = NC / "planar_tables" / f"chart_settings_{dataset}.json"
    ccdb_file = NC / "planar_tables" / f"ccdb_{dataset}.json"
    settings = {
        "language_name": (None, "exporter default (titles show the dataset id)"),
        "groupings": (None, f"exporter default ({DEFAULT_GROUPINGS})"),
        "root_position": (None, "exporter default (the planar table's root element)"),
        "planar_type": (None, "exporter default (axis titles say verbal)"),
        "forest_axis": (None, "exporter default (subset)"),
    }
    planars = _planars(dataset)
    if planars:
        from laminar import planars_language as pl
        from planars.languages import get_display_name
        lang_id, grouping, selection = planars
        source = "laminar/planars_language.py"
        by = {"types": "by domain type", "classes": "by class"}[grouping]
        settings["language_name"] = (f"{get_display_name(lang_id)}, {by}, {selection} spans",
                                     source)
        settings["groupings"] = (pl.GROUPINGS_BY[grouping], source)
        settings["root_position"] = (pl.keystone_position(lang_id), f"{source} (the keystone)")
        settings["planar_type"] = (pl.planar_type(lang_id), repo_relative(pl.planar_file(lang_id)))
        settings["forest_axis"] = ("planar", source)
        return settings
    if ccdb_file.exists():
        ccdb = read_json(ccdb_file)
        source = repo_relative(ccdb_file)
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
            sys.exit(f"{repo_relative(settings_file)}: unknown key(s) {', '.join(unknown)}; "
                     f"known keys are {', '.join(settings)}.")
        source = repo_relative(settings_file)
        for key, value in own.items():
            settings[key] = (value, source)
    return settings


def dataset_groupings(dataset: str) -> str:
    """The GROUPINGS name this dataset is analysed with."""
    return dataset_settings(dataset)["groupings"][0] or DEFAULT_GROUPINGS


# ── The standalone scripts' shared command line ─────────────────────────────

def add_dataset_arguments(parser: argparse.ArgumentParser, topic: str | None,
                          groupings: bool = True) -> None:
    """--domain-file, --domains-dir, --output-dir (unless `topic` is None:
    the script writes nothing) and --groupings (unless the script analyses
    no bundles), the same in every standalone analysis script. `topic` is
    the results/<dataset>/ folder its output goes to by default."""
    parser.add_argument("--domain-file", default="domains_nyan1308.tsv",
                        help="Domains file name inside --domains-dir; the dataset is "
                             "named after it (default domains_nyan1308.tsv).")
    parser.add_argument("--domains-dir", type=Path, default=NC / "domains")
    if topic is not None:
        parser.add_argument("--output-dir", type=Path, default=None,
                            help=f"Default results/<dataset>/{topic}/.")
    if not groupings:
        return
    parser.add_argument("--groupings", choices=sorted(GROUPINGS), default=None,
                        help="Named set of bundles (planars_groupings.GROUPINGS). "
                             "Default: the dataset's own, as its bundle uses.")


@dataclass
class DatasetRun:
    dataset: str           # e.g. nyan1308, chac1251_verbal; names the output files
    domain_path: Path      # the domains file
    bundles: list          # the GROUPINGS set's bundles
    n_positions: int | None  # the planar table's position count, None without one
    output_dir: Path


def resolve_dataset_arguments(args: argparse.Namespace, topic: str) -> DatasetRun:
    """What add_dataset_arguments()'s options mean for this run; creates the
    output folder."""
    dataset = dataset_name(args.domain_file)
    groupings = getattr(args, "groupings", None) or dataset_groupings(dataset)
    output_dir = args.output_dir or NC / "results" / dataset / topic
    output_dir.mkdir(parents=True, exist_ok=True)
    return DatasetRun(
        dataset=dataset,
        domain_path=args.domains_dir / args.domain_file,
        bundles=GROUPINGS[groupings]["bundles"],
        n_positions=planar_position_count(planar_file(dataset)),
        output_dir=output_dir,
    )
