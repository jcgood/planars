#!/usr/bin/env python3
"""Create the ConstituencyTypology root Drive folder and migrate global files into it.

Run once after the initial generate-sheets setup to establish a shared root folder
that houses the coordinator notebook and manifest.json — files that span all
languages and do not belong in any single language folder.

    python -m coding setup-root-folder

What this does:
  1. Creates (or finds) a Drive folder named 'ConstituencyTypology' at the Drive root
  2. Sets Viewer permissions on it (anyone with the link can view)
  3. Moves all existing language folders into the root folder
  4. Renames language folders from 'planars — {lang_id}' to plain '{lang_id}'
  5. Moves manifest.json to the root folder (if it exists on Drive)
  6. Moves all_languages.ipynb to the root folder (if it exists on Drive)
  7. Saves _root_folder_id to drive_config.json

Moving a folder in Drive does not break existing shares — contributor links remain
valid after the move. After running this, new language folders created by generate-sheets
will also be placed inside the root folder automatically.

Re-running is safe: if _root_folder_id is already set, the script reports the
existing folder and exits without making changes.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from .generate_sheets import (
    _get_clients,
    _load_drive_config,
    _save_drive_config,
    _move_to_folder,
)

_ROOT_FOLDER_NAME = "ConstituencyTypology"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_root_folder(drive) -> str:
    """Find or create the ConstituencyTypology folder at the Drive root level.

    Searches Drive for a folder with the right name that has no parent in our
    namespace (i.e. lives at the top level of My Drive). If multiple matches
    exist, returns the first. If none exist, creates one.

    Returns:
        The folder ID.
    """
    results = drive.files().list(
        q=(
            f"name='{_ROOT_FOLDER_NAME}'"
            " and mimeType='application/vnd.google-apps.folder'"
            " and trashed=false"
        ),
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if files:
        folder_id = files[0]["id"]
        print(f"Found existing folder '{_ROOT_FOLDER_NAME}' (id: {folder_id})")
        return folder_id
    folder = drive.files().create(
        body={"name": _ROOT_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    folder_id = folder["id"]
    print(f"Created folder '{_ROOT_FOLDER_NAME}' (id: {folder_id})")
    return folder_id


def _set_viewer_permissions(drive, file_id: str) -> None:
    """Share a file or folder as view-only with anyone who has the link."""
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields="id",
    ).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding setup-root-folder`.

    Fully idempotent: safe to re-run at any time. Each step checks the current
    Drive state before acting and skips anything already in order. Re-run this
    command whenever:
      - A new language folder was created outside the normal generate-sheets
        workflow and needs to be moved into the root folder.
      - A language folder still has the old 'planars — {lang_id}' naming
        convention and needs to be renamed.
      - You want to verify the Drive structure is correctly set up.
    """
    config = _load_drive_config()

    print("Connecting to Google APIs...")
    _, drive = _get_clients()

    # Step 1: Create or find the root folder
    root_id = _get_or_create_root_folder(drive)
    folder_url = f"https://drive.google.com/drive/folders/{root_id}"

    # Step 2: Set Viewer permissions so coordinators can share the link
    _set_viewer_permissions(drive, root_id)
    print(f"Viewer permissions set on root folder.")

    # Step 3: Move any language folders not yet inside the root folder.
    # Handles the initial migration and any folders added outside the normal
    # generate-sheets workflow. Moving does not break existing shares —
    # contributor links remain valid because folder IDs don't change.
    lang_ids = [k for k in config if not k.startswith("_") and isinstance(config[k], dict)]
    for lang_id in sorted(lang_ids):
        lang_folder_id = config[lang_id].get("folder_id")
        if not lang_folder_id:
            print(f"No folder_id for '{lang_id}' in drive_config.json — skipping.")
            continue
        file_info = drive.files().get(fileId=lang_folder_id, fields="parents").execute()
        if root_id in file_info.get("parents", []):
            print(f"Language folder '{lang_id}' already inside root folder — skipping.")
        else:
            _move_to_folder(drive, lang_folder_id, root_id)
            print(f"Moved language folder '{lang_id}' (id: {lang_folder_id}) into root folder.")

    # Step 4: Rename any language folder that still has the old 'planars — {lang_id}'
    # naming convention. That prefix was used when folders lived at the Drive root
    # to make them easy to find; inside ConstituencyTypology it is redundant.
    for lang_id in sorted(lang_ids):
        lang_folder_id = config[lang_id].get("folder_id")
        if not lang_folder_id:
            continue
        file_info = drive.files().get(fileId=lang_folder_id, fields="name").execute()
        current_name = file_info.get("name", "")
        if current_name == lang_id:
            print(f"Language folder '{lang_id}' already has correct name — skipping.")
        else:
            drive.files().update(
                fileId=lang_folder_id, body={"name": lang_id}, fields="id, name"
            ).execute()
            print(f"Renamed '{current_name}' → '{lang_id}'.")

    # Step 5a: Move manifest.json to root folder (if it exists)
    planars_config_id = config.get("_planars_config_file_id")
    if planars_config_id:
        fi = drive.files().get(fileId=planars_config_id, fields="parents").execute()
        if root_id in fi.get("parents", []):
            print("manifest.json already in root folder — skipping.")
        else:
            _move_to_folder(drive, planars_config_id, root_id)
            print(f"Moved manifest.json (id: {planars_config_id}) to root folder.")
    else:
        print("No manifest.json found in drive_config.json — skipping.")
        print("  (Run python -m coding generate-notebooks --apply to create it.)")

    # Step 5b: Move all_languages.ipynb to root folder (if it exists)
    all_langs_id = config.get("_all_languages_notebook_file_id")
    if all_langs_id:
        fi = drive.files().get(fileId=all_langs_id, fields="parents").execute()
        if root_id in fi.get("parents", []):
            print("all_languages.ipynb already in root folder — skipping.")
        else:
            _move_to_folder(drive, all_langs_id, root_id)
            print(f"Moved all_languages.ipynb (id: {all_langs_id}) to root folder.")
    else:
        print("No all_languages.ipynb found in drive_config.json — skipping.")
        print("  (Run python -m coding generate-notebooks --apply to create it.)")

    # Step 6: Save root folder ID (no-op if already set)
    config["_root_folder_id"] = root_id
    _save_drive_config(config)

    print(f"\nDone. drive_config.json updated with _root_folder_id.")
    print(f"Root folder: {folder_url}")
    print(
        "\nNext steps:"
        "\n  - All language folders are now inside ConstituencyTypology."
        "\n  - Existing contributor shares are unaffected (folder IDs did not change)."
        "\n  - New language folders will be created inside this root folder automatically."
        "\n  - Share the root folder URL with coordinators who need access to all_languages.ipynb."
        "\n  - Run python -m coding generate-notebooks --apply to regenerate notebooks"
        "\n    (confirms manifest.json points to the correct location)."
    )


if __name__ == "__main__":
    main()
