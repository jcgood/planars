#!/usr/bin/env python3
"""Generate and upload PDF reports for all languages to Google Drive.

Run from the repo root:
    python -m coding generate-reports           # dry run — show what would be generated
    python -m coding generate-reports --apply   # generate and upload to Drive

Each language gets a report_{lang_id}.pdf in its Drive folder. The file is
created on the first run and updated in place on subsequent runs, so the URL
stays stable. PDFs render natively in the Drive viewer, making the URL
directly shareable with non-technical collaborators (#89, #94).

Requires weasyprint and kaleido (both in requirements.txt). WeasyPrint also
needs system libraries: libpango-1.0-0, libpangocairo-1.0-0, libcairo2
(installed automatically in CI; on macOS install via Homebrew: pango cairo).

Uses source="local" (reads from coded_data/ TSVs) so it works in CI without
requiring live Google Sheets access during the data collection step. Drive
access is still needed for the upload step.

Authentication: same OAuth2 setup as generate_sheets.py.
    PLANARS_OAUTH_CREDENTIALS  — path to OAuth2 Desktop App credentials
    (token cached at ~/.config/gspread/authorized_user.json after first auth)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from planars.reports import language_report_data
from planars.html_report import render_language_report_pdf
from .drive import _load_drive_config, _save_drive_config
from .drive_backend import get_backend


def _upload_pdf(backend, pdf_bytes: bytes, filename: str, folder_id: str, existing_file_id: str | None) -> str:
    """Upload (create or update) a PDF file in Drive. Returns the file ID.

    Two behaviours here differ from the project's three other "create-or-update
    a Drive file" implementations, and both are preserved deliberately (see
    docs/drive-protocol-surface.md § "Duplicate implementations to collapse"):
    the update path renames the file, and the "anyone with the link, reader"
    grant is set **only on create**. The latter means a report whose permission
    is removed by hand is never restored — unlike a notebook, which
    generate_notebooks.py reasserts on every run. Collapsing the four into one
    parameterised call is a later change, gated on all four having goldens.

    (The old code passed resumable=False to MediaIoBaseUpload; that is also the
    library default, which the seam uses, so the upload is unchanged.)
    """
    if existing_file_id:
        backend.update_file(existing_file_id, name=filename,
                            content=pdf_bytes, mimetype="application/pdf")
        return existing_file_id
    file_id = backend.create_file(filename, parents=[folder_id],
                                  content=pdf_bytes, mimetype="application/pdf")
    backend.create_permission(file_id, type="anyone", role="reader")
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
            print(f"  report_{lang_id}.pdf")
        print("\nRun with --apply to generate and upload.")
        return

    drive_config = _load_drive_config()
    backend = get_backend()

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

        pdf_bytes = render_language_report_pdf(data)
        filename = f"report_{lang_id}.pdf"
        # Migrate legacy key report_html_file_id → report_file_id if present
        lang_cfg = drive_config.get(lang_id, {})
        existing = lang_cfg.get("report_file_id") or lang_cfg.get("report_html_file_id")

        try:
            file_id = _upload_pdf(backend, pdf_bytes, filename, folder_id, existing)
        except Exception as e:
            print(f"upload ERROR: {e}")
            continue

        drive_config.setdefault(lang_id, {})["report_file_id"] = file_id
        drive_config[lang_id].pop("report_html_file_id", None)
        action = "updated" if existing else "created"
        print(f"{action}. https://drive.google.com/file/d/{file_id}/view")

    _save_drive_config(drive_config)
    print("\nDone. drive_config.json updated.")


def main() -> None:
    """Entry point for `python -m coding generate-reports`."""
    _run(apply="--apply" in sys.argv)


if __name__ == "__main__":
    main()
