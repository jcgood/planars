"""What a dataset name means: its files, its settings, its planar structure.

A dataset is one structure's tests, named after its domains file
(``domains/domains_<dataset>.tsv``): nyan1308, or a CCDB structure such as
chac1251_verbal. Every script that takes a domains file works out the rest
from the name through this module, so a script run on its own analyses a
dataset exactly as its exported bundle does.

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

from planars_groupings import GROUPINGS

NC = Path(__file__).resolve().parents[2]

# The exporter's --groupings default, and so every dataset's unless its
# settings say otherwise.
DEFAULT_GROUPINGS = "chichewa"


def dataset_name(domain_file: str | Path) -> str:
    """``domains_<dataset>.tsv`` -> ``<dataset>``."""
    return Path(domain_file).stem.removeprefix("domains_")


def planar_file(dataset: str) -> Path:
    return NC / "planar_tables" / f"planar_{dataset}.tsv"


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
