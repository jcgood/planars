#!/usr/bin/env python3
"""Generate per-language contributor and report notebooks and the all-languages coordinator notebook.

Run from the repo root:
    python -m coding generate-notebooks           # dry run — show what would be generated
    python -m coding generate-notebooks --apply   # generate and upload to Drive

What this does, for every language with a planar file and a Drive folder:
  1. Generates domains_{lang_id}.ipynb from the contributor template, with
     LANG_ID baked in; uploads it to the language's Drive folder
  2. Generates report_{lang_id}.ipynb from the report template, with LANG_ID
     and FOLDER_ID baked in; uploads it to the language's Drive folder.
     Running this notebook generates and uploads report_{lang_id}.html with a
     stable URL for sharing with non-technical collaborators.
  3. Generates all_languages.ipynb from the coordinator template (nothing
     baked in); uploads it to the root folder
  4. Sets Viewer ("anyone with link") permissions on all uploaded notebooks
     (every run, through drive.create_or_update_shared_file, which the PDF
     upload in generate_reports.py also uses; it adds the grant only if
     none exists, so repeat runs don't pile up duplicates)
  5. Updates drive_config.json with notebook file IDs for future updates,
     saved after each individual upload so a crash cannot lose the IDs of
     earlier uploads and make a retry create duplicate files

The notebooks find a language's sheets by the labels the tooling puts on
them (``planars.from_sheets``), and the package works out which tests a
language has from the tabs it finds (``planars.reports.print_class_reports``).
So a notebook holds no list of sheets or classes, and a new sheet or class
needs no new notebook. The daily refresh runs this command so a template
change reaches every notebook the same day. Until unit 11c-5 (2026-10-29)
the notebooks read the sheet IDs from a manifest on Drive, and a cell per
class was generated here from each language's diagnostics.

Templates live in notebooks/templates/ (substitution only):
  domains_boilerplate.ipynb      — contributor template
  report_boilerplate.ipynb       — report template (generates HTML for John)
  all_languages_boilerplate.ipynb — coordinator template

There was a validation notebook too (validation_{lang_id}.ipynb), retired
2026-10-23: it checked cells against a copy of the allowed values kept in the
manifest, which went stale, and against element-row rules on every tab. The
daily refresh lists every cell that needs fixing on each sheet's Status tab
instead (#309).

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "notebooks" / "templates"
CODED_DATA = ROOT / "coded_data"

from .make_forms import _infer_language_id_from_planar_filename
from .drive import _load_drive_config, _save_drive_config, create_or_update_shared_file
from .drive_doorway import get_doorway
from . import drive_door
from .sheet_spec import file_spec


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
    touching Drive. In apply mode, uploads the per-language contributor and
    report notebooks and the coordinator notebook.

    Args:
        apply: if True, connect to Drive and upload; if False, dry-run only.
    """
    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")
    lang_ids = [_infer_language_id_from_planar_filename(p.name) for p in planar_files]

    drive_config = _load_drive_config()
    global_folder_id = _get_global_folder_id(drive_config)

    print(f"{'DRY RUN — ' if not apply else ''}Notebook generation")
    print(f"Languages: {lang_ids}")

    if not global_folder_id:
        raise SystemExit(
            "No _root_folder_id in drive_config.json. Run setup-root-folder first."
        )

    # A language with no Drive folder recorded gets no notebooks at all — they
    # have nowhere to go. Said here, before the lists, so the dry run and the
    # apply run name the same set of languages: the dry run used to promise
    # three notebooks for every language and only mention the omission once
    # --apply had already run.
    uploadable = [lang_id for lang_id in lang_ids
                  if drive_config.get(lang_id, {}).get("folder_id")]
    no_folder = [lang_id for lang_id in lang_ids if lang_id not in uploadable]
    if no_folder:
        print(f"\nNo Drive folder recorded, so no notebooks: {no_folder}")
        print("  Run python -m coding generate-sheets --apply to create their "
              "folders first.")

    if not apply:
        print("\nContributor notebooks (one per language):")
        named = lambda name, lang=None: file_spec(drive_door.notebook(name, lang)).name
        for lang_id in uploadable:
            print(f"  {named('domains', lang_id)}")
        print("\nReport notebooks (one per language — generates shareable HTML for collaborators):")
        for lang_id in uploadable:
            print(f"  {named('report', lang_id)}")
        print(f"\nCoordinator notebook (all languages):")
        print(f"  {named('all_languages')}")
        print("\nRun with --apply to generate and upload.")
        return

    doorway = get_doorway()

    # Generate and upload contributor notebook for each language
    contributor_template = _load_template("domains_boilerplate.ipynb")
    for lang_id in uploadable:
        folder_id = drive_config[lang_id]["folder_id"]
        nb = _substitute_tokens(contributor_template, {
            "LANG_ID": lang_id,
            "LANG_DISPLAY": _lang_display(lang_id),
        })
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
    nb = _load_template("all_languages_boilerplate.ipynb")
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
