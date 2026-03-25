#!/usr/bin/env python3
"""Generate and upload HTML reports for all languages to Google Drive.

Run from the repo root:
    python -m coding generate-reports           # dry run — show what would be generated
    python -m coding generate-reports --apply   # generate and upload to Drive

Each language gets a report_{lang_id}.html in its Drive folder. The file is
created on the first run and updated in place on subsequent runs, so the URL
stays stable. Intended for non-technical collaborators (#89).

Uses source="local" (reads from coded_data/ TSVs) so it works in CI without
requiring live Google Sheets access during the data collection step. Drive
access is still needed for the upload step.

Authentication: same OAuth2 setup as generate_sheets.py.
    PLANARS_OAUTH_CREDENTIALS  — path to OAuth2 Desktop App credentials
    (token cached at ~/.config/gspread/authorized_user.json after first auth)
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from googleapiclient.http import MediaIoBaseUpload

from planars.reports import language_report_data
from planars.html_report import render_language_report
from .generate_sheets import _get_clients, _load_drive_config, _save_drive_config


def _upload_html(drive, html: str, filename: str, folder_id: str, existing_file_id: str | None) -> str:
    """Upload (create or update) an HTML file in Drive. Returns the file ID."""
    media = MediaIoBaseUpload(
        io.BytesIO(html.encode("utf-8")), mimetype="text/html", resumable=False
    )
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
        file_id = result["id"]
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
        return file_id


def _run(apply: bool) -> None:
    lang_dirs = sorted(
        d for d in CODED_DATA.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    lang_ids = [d.name for d in lang_dirs]

    print(f"{'DRY RUN — ' if not apply else ''}Report generation")
    print(f"Languages: {lang_ids}")

    if not apply:
        for lang_id in lang_ids:
            print(f"  report_{lang_id}.html")
        print("\nRun with --apply to generate and upload.")
        return

    drive_config = _load_drive_config()
    _, drive = _get_clients()

    for lang_id in lang_ids:
        folder_id = drive_config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            print(f"  [{lang_id}] No folder_id in drive_config — skipping")
            continue

        print(f"  [{lang_id}] Collecting data...", end=" ", flush=True)
        try:
            data = language_report_data(lang_id, source="local", repo_root=ROOT)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        html = render_language_report(data)
        filename = f"report_{lang_id}.html"
        existing = drive_config.get(lang_id, {}).get("report_html_file_id")

        try:
            file_id = _upload_html(drive, html, filename, folder_id, existing)
        except Exception as e:
            print(f"upload ERROR: {e}")
            continue

        drive_config.setdefault(lang_id, {})["report_html_file_id"] = file_id
        action = "updated" if existing else "created"
        print(f"{action}. https://drive.google.com/file/d/{file_id}/view")

    _save_drive_config(drive_config)
    print("\nDone. drive_config.json updated.")


def main() -> None:
    """Entry point for `python -m coding generate-reports`."""
    _run(apply="--apply" in sys.argv)


if __name__ == "__main__":
    main()
