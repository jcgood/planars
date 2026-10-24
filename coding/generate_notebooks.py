#!/usr/bin/env python3
"""Generate per-language contributor and report notebooks and the all-languages coordinator notebook.

Run from the repo root:
    python -m coding generate-notebooks           # dry run — show what would be generated
    python -m coding generate-notebooks --apply   # generate and upload to Drive

What this does:
  1. Reads diagnostics_{lang_id}.yaml (or its TSV, if there is no YAML) for each
     language to discover analysis classes
  2. Looks up the file ID of manifest.json on Drive (kept up to date by
     generate-sheets and the sheet modification commands; this command only
     reads its ID and does not write it)
  3. Generates domains_{lang_id}.ipynb for each language from the contributor template,
     with CONFIG_FILE_ID and LANG_ID baked in; uploads to each language's Drive folder
  4. Generates report_{lang_id}.ipynb for each language from the report template,
     with CONFIG_FILE_ID, LANG_ID, and FOLDER_ID baked in; uploads to each language's
     Drive folder. Running this notebook generates and uploads report_{lang_id}.html
     with a stable URL for sharing with non-technical collaborators.
  5. Generates all_languages.ipynb from the coordinator template, with per-class cells
     inserted from the union of all languages' diagnostics; uploads to Drive
  6. Sets Viewer ("anyone with link") permissions on all uploaded notebooks
     (every run, through drive.create_or_update_shared_file, which the PDF
     upload in generate_reports.py also uses; it adds the grant only if
     none exists, so repeat runs don't pile up duplicates)
  7. Updates drive_config.json with notebook file IDs for future updates,
     saved after each individual upload so a crash cannot lose the IDs of
     earlier uploads and make a retry create duplicate files

Templates live in notebooks/templates/:
  domains_boilerplate.ipynb      — contributor template (substitution only)
  report_boilerplate.ipynb       — report template (substitution only; generates HTML for John)
  all_languages_boilerplate.ipynb — coordinator template (substitution + cell generation)

There was a validation notebook too (validation_{lang_id}.ipynb), retired
2026-10-23: it checked cells against a copy of the allowed values kept in the
manifest, which went stale, and against element-row rules on every tab. The
daily refresh lists every cell that needs fixing on each sheet's Status tab
instead (#309).

Class cells are generated from the language's diagnostics file, not the templates, so adding a new
analysis class automatically includes it the next time generate-notebooks is run.
Each analysis module must define a `derive` alias pointing to its primary derive function
(see e.g. planars/ciscategorial.py) for this to work correctly.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "notebooks" / "templates"
CODED_DATA = ROOT / "coded_data"

from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .drive import _load_drive_config, _save_drive_config, create_or_update_shared_file
from .drive_doorway import get_doorway
from . import drive_door
from .schemas import load_diagnostic_classes
from .sheet_spec import file_spec

# Marker placed in all_languages_boilerplate.ipynb to indicate where
# generated per-class cells should be inserted.
_CLASS_CELLS_MARKER = "# __CLASS_CELLS_MARKER__\n"


# ---------------------------------------------------------------------------
# Template loading and token substitution
# ---------------------------------------------------------------------------

def _load_template(name: str) -> dict:
    """Load a boilerplate notebook from notebooks/templates/."""
    path = TEMPLATES_DIR / name
    with open(path) as f:
        return json.load(f)


def _substitute_tokens(nb: dict, tokens: Dict[str, str]) -> dict:
    """Replace {{TOKEN}} placeholders in all cell sources. Returns a deep copy."""
    nb = copy.deepcopy(nb)
    for cell in nb["cells"]:
        src = cell["source"]
        if isinstance(src, str):
            cell["source"] = _replace_tokens(src, tokens)
        else:
            cell["source"] = [_replace_tokens(line, tokens) for line in src]
    return nb


def _replace_tokens(text: str, tokens: Dict[str, str]) -> str:
    """Replace all {{KEY}} placeholders in text with the corresponding values."""
    for token, value in tokens.items():
        text = text.replace("{{" + token + "}}", value)
    return text


def _lang_display(lang_id: str) -> str:
    """Return 'Name [glottocode]' from languages.yaml, else the bare glottocode.

    Reads languages.yaml directly (not via coding.schemas cached loader) because
    lookup-lang may write a new entry earlier in the same session and we need
    the just-written state, not a cached snapshot.
    """
    import yaml as _yaml
    _lang_yaml = ROOT / "schemas" / "languages.yaml"
    if _lang_yaml.exists():
        with open(_lang_yaml, encoding="utf-8") as _f:
            _langs = _yaml.safe_load(_f) or {}
        entry = _langs.get(lang_id, {})
        name = entry.get("glottolog", {}).get("name")
        if name:
            return f"{name} [{lang_id}]"
    return lang_id


# ---------------------------------------------------------------------------
# Per-class cell generation (coordinator notebook only)
# ---------------------------------------------------------------------------

def _display_name(class_name: str) -> str:
    """Return the class's ``display_name`` from diagnostic_classes.yaml, for
    notebook section headers. Raises if the class is missing or has none."""
    for cls in load_diagnostic_classes().get("classes", []):
        if cls.get("name") == class_name:
            if not cls.get("display_name"):
                raise ValueError(f"diagnostic_classes.yaml class {class_name!r} has no display_name")
            return cls["display_name"]
    raise ValueError(f"diagnostic_classes.yaml has no class {class_name!r}")


def _make_code_cell(source: str) -> dict:
    """Build a Jupyter code cell dict from a source string."""
    lines = source.splitlines(keepends=True)
    # Jupyter convention: the last line of a cell's source must not end with '\n'.
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def _make_markdown_cell(source: str) -> dict:
    """Build a Jupyter markdown cell dict from a source string."""
    lines = source.splitlines(keepends=True)
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines,
    }


def _generate_class_cells(class_names: List[str]) -> List[dict]:
    """Generate a markdown header + code cell pair for each analysis class.

    The code cell uses each module's standard `derive` alias so that no
    per-class name mapping is needed here. See planars/<module>.py for the alias.
    """
    cells = []
    for class_name in class_names:
        name = _display_name(class_name)
        cells.append(_make_markdown_cell(f"---\n## {name}"))
        code_cell = _make_code_cell(
            f"#@title {name}\n"
            f"from planars import {class_name}\n"
            f"show_class_reports(gc, manifest, '{class_name}', "
            f"{class_name}.derive, {class_name}.format_result)"
        )
        code_cell["metadata"]["cellView"] = "form"
        cells.append(code_cell)
    return cells


def _insert_class_cells(nb: dict, class_cells: List[dict]) -> dict:
    """Replace the marker cell in the template with generated per-class cells."""
    nb = copy.deepcopy(nb)
    new_cells = []
    marker = _CLASS_CELLS_MARKER.strip()
    for cell in nb["cells"]:
        src = cell.get("source")
        src_text = src if isinstance(src, str) else "".join(src)
        if src_text.strip() == marker:
            new_cells.extend(class_cells)
        else:
            new_cells.append(cell)
    nb["cells"] = new_cells
    return nb


# ---------------------------------------------------------------------------
# Drive upload helpers
# ---------------------------------------------------------------------------
#
# Notebook upload (create-or-update, renamed on update, shared "anyone with
# the link, reader" on every run) is `drive.create_or_update_shared_file`,
# shared with `generate_reports.py`'s PDF upload since the two collapsed
# under issue #276. It calls `drive.ensure_anyone_permission` internally,
# which is what makes "reshare on every run" safe: it skips creating a
# second grant when one already exists, so a normal repeat run adds nothing
# and only a manually-revoked share gets restored.

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _get_global_folder_id(drive_config: dict) -> Optional[str]:
    """Return the folder ID for global files (all_languages.ipynb): the root
    folder, ``_root_folder_id``, set by ``python -m coding setup-root-folder``.

    Until 2026-10-19 this fell back to a legacy ``_global_folder_id`` key and
    then to the first language folder, which put the all-languages notebook
    in one language's folder; the Drive door's file spec (it sits in the root
    folder) refused that. No config has used either since the root folder
    was introduced, so the command now stops and says to run
    setup-root-folder instead.
    """
    return drive_config.get("_root_folder_id")


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _run_generation(apply: bool) -> None:
    """Core logic for notebook generation.

    In dry-run mode (apply=False) prints what would be generated without
    touching Drive. In apply mode, uploads manifest.json, per-language
    contributor notebooks, and the coordinator notebook.

    Args:
        apply: if True, connect to Drive and upload; if False, dry-run only.
    """
    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    # Read diagnostics for each language to get ordered class lists
    lang_classes: Dict[str, List[str]] = {}
    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)
        specs = _read_diagnostics_for_language(lang_id, planar_file.parent)
        seen: Dict[str, bool] = {}
        for class_name, _, _, _ in specs:
            if class_name not in seen:
                seen[class_name] = True
        lang_classes[lang_id] = list(seen.keys())

    # Union of all classes across all languages, preserving first-seen order
    all_classes: List[str] = []
    seen_global: set = set()
    for classes in lang_classes.values():
        for c in classes:
            if c not in seen_global:
                all_classes.append(c)
                seen_global.add(c)

    drive_config = _load_drive_config()
    global_folder_id = _get_global_folder_id(drive_config)

    print(f"{'DRY RUN — ' if not apply else ''}Notebook generation")
    print(f"Languages:              {list(lang_classes.keys())}")
    print(f"Classes (all langs):    {all_classes}")

    if not global_folder_id:
        raise SystemExit(
            "No _root_folder_id in drive_config.json. Run setup-root-folder first."
        )

    # manifest.json on Drive is maintained by generate-sheets and the sheet
    # modification scripts. generate-notebooks only needs its file ID to bake into
    # the notebooks — it does not write to manifest.json itself.
    config_file_id = drive_config.get("_planars_config_file_id")
    if not config_file_id:
        raise SystemExit(
            "No _planars_config_file_id in drive_config.json. "
            "Run python -m coding generate-sheets --apply first."
        )

    # A language with no Drive folder recorded gets no notebooks at all — they
    # have nowhere to go. Said here, before the lists, so the dry run and the
    # apply run name the same set of languages: the dry run used to promise
    # three notebooks for every language and only mention the omission once
    # --apply had already run.
    uploadable = {lang_id: classes for lang_id, classes in lang_classes.items()
                  if drive_config.get(lang_id, {}).get("folder_id")}
    no_folder = [lang_id for lang_id in lang_classes if lang_id not in uploadable]
    if no_folder:
        print(f"\nNo Drive folder recorded, so no notebooks: {no_folder}")
        print("  Run python -m coding generate-sheets --apply to create their "
              "folders first.")

    if not apply:
        print("\nContributor notebooks (one per language, includes per-class report sections):")
        named = lambda name, lang=None: file_spec(drive_door.notebook(name, lang)).name
        for lang_id, classes in uploadable.items():
            print(f"  {named('domains', lang_id)} — {classes}")
        print("\nReport notebooks (one per language — generates shareable HTML for collaborators):")
        for lang_id in uploadable:
            print(f"  {named('report', lang_id)}")
        print(f"\nCoordinator notebook (all languages):")
        print(f"  {named('all_languages')} — {all_classes}")
        print("\nRun with --apply to generate and upload.")
        return

    doorway = get_doorway()
    print(f"\nUsing manifest.json (id: {config_file_id})")

    # Generate and upload contributor notebook for each language
    contributor_template = _load_template("domains_boilerplate.ipynb")
    for lang_id, classes in uploadable.items():
        folder_id = drive_config[lang_id]["folder_id"]
        nb = _substitute_tokens(contributor_template, {
            "LANG_ID": lang_id,
            "LANG_DISPLAY": _lang_display(lang_id),
            "CONFIG_FILE_ID": config_file_id,
        })
        nb = _insert_class_cells(nb, _generate_class_cells(classes))
        nb_bytes = json.dumps(nb, indent=1).encode()
        identity = drive_door.notebook("domains", lang_id)
        filename = file_spec(identity).name
        file_id = create_or_update_shared_file(
            doorway, nb_bytes, folder_id,
            drive_config.get(lang_id, {}).get("domains_notebook_file_id"),
            identity=identity,
        )
        drive_config.setdefault(lang_id, {})["domains_notebook_file_id"] = file_id
        # Save after every upload, not once at the end -- a crash partway
        # through the loops below must not lose an already-successful
        # upload's new file ID, or a retry creates a duplicate file instead
        # of updating the existing one (issue #280).
        _save_drive_config(drive_config)
        print(f"  [{lang_id}] Uploaded {filename} (viewer)")

    # Generate and upload report notebook for each language
    report_template = _load_template("report_boilerplate.ipynb")
    for lang_id in uploadable:
        folder_id = drive_config[lang_id]["folder_id"]
        nb = _substitute_tokens(report_template, {
            "LANG_ID":        lang_id,
            "LANG_DISPLAY":   _lang_display(lang_id),
            "CONFIG_FILE_ID": config_file_id,
            "FOLDER_ID":      folder_id,
        })
        nb_bytes = json.dumps(nb, indent=1).encode()
        identity = drive_door.notebook("report", lang_id)
        filename = file_spec(identity).name
        file_id = create_or_update_shared_file(
            doorway, nb_bytes, folder_id,
            drive_config.get(lang_id, {}).get("report_notebook_file_id"),
            identity=identity,
        )
        drive_config.setdefault(lang_id, {})["report_notebook_file_id"] = file_id
        _save_drive_config(drive_config)
        print(f"  [{lang_id}] Uploaded {filename} (viewer)")

    # Generate and upload coordinator notebook
    coordinator_template = _load_template("all_languages_boilerplate.ipynb")
    nb = _substitute_tokens(coordinator_template, {"CONFIG_FILE_ID": config_file_id})
    nb = _insert_class_cells(nb, _generate_class_cells(all_classes))
    nb_bytes = json.dumps(nb, indent=1).encode()
    identity = drive_door.notebook("all_languages")
    coord_file_id = create_or_update_shared_file(
        doorway, nb_bytes, global_folder_id,
        drive_config.get("_all_languages_notebook_file_id"),
        identity=identity,
    )
    drive_config["_all_languages_notebook_file_id"] = coord_file_id
    print(f"\nUploaded {file_spec(identity).name} (viewer)")

    _save_drive_config(drive_config)
    print("\nDone. drive_config.json updated.")


def regenerate_notebooks() -> None:
    """Generate and upload notebooks in apply mode.

    Called by generate_sheets, sync_params, and restructure_sheets after
    --apply operations that may have changed diagnostics or folder structure.
    """
    print("\n--- Regenerating notebooks ---")
    _run_generation(apply=True)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding generate-notebooks`."""
    ap = argparse.ArgumentParser(
        description="Generate and upload contributor + coordinator notebooks."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="generate and upload to Drive (default: dry run)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding generate-notebooks`."""
    if args is None:
        args = build_parser().parse_args()
    _run_generation(apply=args.apply)


if __name__ == "__main__":
    main()
