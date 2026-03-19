#!/usr/bin/env python3
"""Generate per-language contributor notebooks and the all-languages coordinator notebook.

Run from the repo root:
    python -m coding generate-notebooks           # dry run — show what would be generated
    python -m coding generate-notebooks --apply   # generate and upload to Drive

What this does:
  1. Reads diagnostics.tsv for each language to discover analysis classes
  2. Builds/updates planars_config.json on Drive (maps lang_id → folder_id)
  3. Generates domains_{lang_id}.ipynb for each language from the contributor template,
     with CONFIG_FILE_ID and LANG_ID baked in; uploads to each language's Drive folder
  4. Generates all_languages.ipynb from the coordinator template, with per-class cells
     inserted from the union of all languages' diagnostics; uploads to Drive
  5. Sets Viewer ("anyone with link") permissions on all uploaded notebooks
  6. Updates drive_config.json with notebook file IDs for future updates

Templates live in notebooks/templates/:
  domains_boilerplate.ipynb      — contributor template (substitution only)
  all_languages_boilerplate.ipynb — coordinator template (substitution + cell generation)

Class cells are generated from diagnostics.tsv, not the templates, so adding a new
analysis class automatically includes it the next time generate-notebooks is run.
Each analysis module must define a `derive` alias pointing to its primary derive function
(see e.g. planars/ciscategorial.py) for this to work correctly.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import copy
import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "notebooks" / "templates"
CODED_DATA = ROOT / "coded_data"

from googleapiclient.http import MediaIoBaseUpload

from . import make_forms as _mf
from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .generate_sheets import (
    _get_clients,
    _load_drive_config,
    _save_drive_config,
)

# Human-readable display names for notebook section headers.
# Add an entry here whenever a new analysis class is introduced.
_CLASS_DISPLAY_NAMES = {
    "ciscategorial":    "Ciscategorial",
    "subspanrepetition": "Subspan Repetition",
    "noninterruption":  "Noninterruption",
    "stress":           "Stress",
    "aspiration":       "Aspiration",
}

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
        cell["source"] = [
            _replace_tokens(line, tokens) for line in cell["source"]
        ]
    return nb


def _replace_tokens(text: str, tokens: Dict[str, str]) -> str:
    """Replace all {{KEY}} placeholders in text with the corresponding values."""
    for token, value in tokens.items():
        text = text.replace("{{" + token + "}}", value)
    return text


# ---------------------------------------------------------------------------
# Per-class cell generation (coordinator notebook only)
# ---------------------------------------------------------------------------

def _display_name(class_name: str) -> str:
    """Return the human-readable display name for an analysis class."""
    return _CLASS_DISPLAY_NAMES.get(class_name, class_name.capitalize())


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
    for cell in nb["cells"]:
        if cell.get("source") == [_CLASS_CELLS_MARKER]:
            new_cells.extend(class_cells)
        else:
            new_cells.append(cell)
    nb["cells"] = new_cells
    return nb


# ---------------------------------------------------------------------------
# Drive upload helpers
# ---------------------------------------------------------------------------

def _upload_file(
    drive,
    content: bytes,
    filename: str,
    mimetype: str,
    folder_id: str,
    existing_file_id: Optional[str] = None,
) -> str:
    """Upload (create or update) a file in Drive. Returns the file ID."""
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mimetype)
    if existing_file_id:
        drive.files().update(
            fileId=existing_file_id,
            body={"name": filename},
            media_body=media,
        ).execute()
        return existing_file_id
    else:
        result = drive.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        return result["id"]


def _set_viewer_permissions(drive, file_id: str) -> None:
    """Share a file as view-only with anyone who has the link."""
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields="id",
    ).execute()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _get_global_folder_id(drive_config: dict) -> Optional[str]:
    """Return the folder ID for global files (planars_config.json, all_languages.ipynb).

    Lookup order:
    1. ``_root_folder_id`` — set by ``python -m coding setup-root-folder``; the
       ConstituencyTypology folder that houses all coordinator-level files.
    2. ``_global_folder_id`` — legacy fallback key (kept for backward compatibility).
    3. First language folder alphabetically — original default before the root
       folder was introduced; used only when neither key above is present.
    """
    if "_root_folder_id" in drive_config:
        return drive_config["_root_folder_id"]
    if "_global_folder_id" in drive_config:
        return drive_config["_global_folder_id"]
    for lang_id in sorted(drive_config):
        if lang_id.startswith("_"):
            continue
        data = drive_config.get(lang_id, {})
        if isinstance(data, dict) and data.get("folder_id"):
            return data["folder_id"]
    return None


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _run_generation(apply: bool) -> None:
    """Core logic for notebook generation.

    In dry-run mode (apply=False) prints what would be generated without
    touching Drive. In apply mode, uploads planars_config.json, per-language
    contributor notebooks, and the coordinator notebook.

    Args:
        apply: if True, connect to Drive and upload; if False, dry-run only.
    """
    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")

    # Read diagnostics for each language to get ordered class lists
    lang_classes: Dict[str, List[str]] = {}
    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)
        _mf.DATA_DIR = str(planar_file.parent)
        specs = _read_diagnostics_for_language(lang_id)
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

    # planars_config.json on Drive is maintained by generate-sheets and the sheet
    # modification scripts. generate-notebooks only needs its file ID to bake into
    # the notebooks — it does not write to planars_config.json itself.
    config_file_id = drive_config.get("_planars_config_file_id")
    if not config_file_id:
        raise SystemExit(
            "No _planars_config_file_id in drive_config.json. "
            "Run python -m coding generate-sheets first."
        )

    if not apply:
        print("\nContributor notebooks (one per language, includes per-class report sections):")
        for lang_id, classes in lang_classes.items():
            print(f"  domains_{lang_id}.ipynb — {classes}")
        print(f"\nCoordinator notebook (all languages):")
        print(f"  all_languages.ipynb — {all_classes}")
        print("\nRun with --apply to generate and upload.")
        return

    _, drive = _get_clients()
    print(f"\nUsing planars_config.json (id: {config_file_id})")

    # Generate and upload contributor notebook for each language
    contributor_template = _load_template("domains_boilerplate.ipynb")
    for lang_id, classes in lang_classes.items():
        folder_id = drive_config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            print(f"  [{lang_id}] No folder_id in drive_config — skipping")
            continue
        nb = _substitute_tokens(contributor_template, {
            "LANG_ID": lang_id,
            "CONFIG_FILE_ID": config_file_id,
        })
        nb = _insert_class_cells(nb, _generate_class_cells(classes))
        nb_bytes = json.dumps(nb, indent=1).encode()
        filename = f"domains_{lang_id}.ipynb"
        file_id = _upload_file(
            drive, nb_bytes, filename, "application/json", folder_id,
            drive_config.get(lang_id, {}).get("domains_notebook_file_id"),
        )
        _set_viewer_permissions(drive, file_id)
        drive_config.setdefault(lang_id, {})["domains_notebook_file_id"] = file_id
        print(f"  [{lang_id}] Uploaded {filename} (viewer)")

    # Generate and upload coordinator notebook
    coordinator_template = _load_template("all_languages_boilerplate.ipynb")
    nb = _substitute_tokens(coordinator_template, {"CONFIG_FILE_ID": config_file_id})
    nb = _insert_class_cells(nb, _generate_class_cells(all_classes))
    nb_bytes = json.dumps(nb, indent=1).encode()
    coord_file_id = _upload_file(
        drive, nb_bytes, "all_languages.ipynb", "application/json", global_folder_id,
        drive_config.get("_all_languages_notebook_file_id"),
    )
    _set_viewer_permissions(drive, coord_file_id)
    drive_config["_all_languages_notebook_file_id"] = coord_file_id
    print(f"\nUploaded all_languages.ipynb (viewer)")

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

def main() -> None:
    """Entry point for `python -m coding generate-notebooks`."""
    _run_generation(apply="--apply" in sys.argv)


if __name__ == "__main__":
    main()
