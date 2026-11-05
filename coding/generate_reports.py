#!/usr/bin/env python3
"""Generate and upload PDF reports for all languages to Google Drive.

Run from the repo root:
    python -m coding generate-reports           # dry run — show what would be generated
    python -m coding generate-reports --apply   # generate and upload to Drive

Each language gets a report_{lang_id}.pdf in its Drive folder. The file is
created on the first run and updated in place on subsequent runs, so the URL
stays stable. PDFs render natively in the Drive viewer, making the URL
directly shareable with non-technical collaborators (#89, #94). The upload
is `drive.create_or_update_shared_file` (shared with generate_notebooks.py):
"anyone with the link, reader" is reasserted on every run, so a report whose
share was removed by hand is restored without piling up duplicate grants.

`drive_config.json` is saved after every language, and a failure on one
language (no Drive folder, collecting data, rendering the PDF, uploading) is
printed and skipped, so the languages after it still get their reports. An
``--apply`` run then files (rewriting the open one) or closes one
``reports-error`` issue naming each failed language and its stage, never the
reason (it can quote the annotation, and the repository is public), and exits
non-zero if any language failed.

Requires weasyprint and kaleido (both in requirements.txt). WeasyPrint also
needs system libraries: libpango-1.0-0, libpangocairo-1.0-0, libcairo2
(installed automatically in CI; on macOS install via Homebrew: pango cairo).

Under its date, each report says what it was drawn from
(``versions.stamp_text``: the code version, and the schemas' and the
language's versions and change-log positions; Phase 10 unit 18).

Reads the imported coded_data/ TSVs, so it works in CI without live Google
Sheets access during the data collection step. Drive access is still needed
for the upload step.

Authentication: same OAuth2 setup as generate_sheets.py.
    PLANARS_OAUTH_CREDENTIALS  — path to OAuth2 Desktop App credentials
    (token cached at ~/.config/gspread/authorized_user.json after first auth)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from coding import versions
from planars.reports import language_report_data
from planars.html_report import render_language_report_pdf
from .drive import _load_drive_config, _save_drive_config, create_or_update_shared_file
from .drive_doorway import get_doorway
from . import drive_door
from .sheet_spec import file_spec

# PDF upload (create-or-update, renamed on update, shared "anyone with the
# link, reader" on every run) is drive.create_or_update_shared_file, shared
# with generate_notebooks.py's notebook upload since the two collapsed under
# issue #276. Before this, sharing was set only on create here, so a report
# whose permission was removed by hand was never restored — unlike a
# notebook, which generate_notebooks.py already reasserted every run. Both
# now go through the same idempotent check (drive.ensure_anyone_permission),
# so reports self-heal too, without piling up duplicate grants on a normal
# repeat run.
#
# (The old code passed resumable=False to MediaIoBaseUpload; that is also the
# library default, which the doorway uses, so the upload is unchanged.)


ISSUE_LABEL = "reports-error"


def _run(apply: bool) -> list[tuple[str, str]]:
    """Generate (and with ``apply`` upload) each language's report. Returns
    the languages that failed, each with the stage it failed at."""
    failed: list[tuple[str, str]] = []
    lang_dirs = sorted(
        d for d in CODED_DATA.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    lang_ids = [d.name for d in lang_dirs]

    print(f"{'DRY RUN — ' if not apply else ''}Report generation")
    print(f"Languages: {lang_ids}")

    if not apply:
        for lang_id in lang_ids:
            print(f"  {file_spec(drive_door.lang_file('report', lang_id)).name}")
        print("\nRun with --apply to generate and upload.")
        return failed

    drive_config = _load_drive_config()
    doorway = get_doorway()

    for lang_id in lang_ids:
        folder_id = drive_config.get(lang_id, {}).get("folder_id")
        if not folder_id:
            print(f"  [{lang_id}] No folder_id in drive_config — skipping")
            failed.append((lang_id, "finding its Drive folder (no folder_id in drive_config.json)"))
            continue

        print(f"  [{lang_id}] Collecting data...", end=" ", flush=True)
        try:
            data = language_report_data(lang_id, ROOT)
            # What it was drawn from, under the date (Phase 10 unit 18).
            data["drawn_from"] = versions.stamp_text(versions.stamp([lang_id], drawn=False))
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append((lang_id, "collecting its data"))
            continue

        try:
            pdf_bytes = render_language_report_pdf(data)
        except Exception as e:
            print(f"render ERROR: {e}")
            failed.append((lang_id, "drawing the PDF"))
            continue
        # Migrate legacy key report_html_file_id → report_file_id if present
        lang_cfg = drive_config.get(lang_id, {})
        existing = lang_cfg.get("report_file_id") or lang_cfg.get("report_html_file_id")

        try:
            file_id = create_or_update_shared_file(
                doorway, pdf_bytes, folder_id, existing,
                identity=drive_door.lang_file("report", lang_id))
        except Exception as e:
            print(f"upload ERROR: {e}")
            failed.append((lang_id, "uploading to Drive"))
            continue

        drive_config.setdefault(lang_id, {})["report_file_id"] = file_id
        drive_config[lang_id].pop("report_html_file_id", None)
        # Save after every language, not once at the end -- a crash on a
        # later language must not lose an earlier language's already-
        # successful upload's new file ID, or a retry creates a duplicate
        # file instead of updating the existing one (issue #280).
        _save_drive_config(drive_config)
        action = "updated" if existing else "created"
        print(f"{action}. https://drive.google.com/file/d/{file_id}/view")

    print("\nDone. drive_config.json updated.")
    return failed


def issue_body(failed: list[tuple[str, str]], date: str) -> str:
    """The reports-error issue: which languages and at what stage. Never the
    reason, which can quote the annotation (this repository is public)."""
    from planars.languages import get_display_name
    lines = "\n".join(f"- {get_display_name(lang)}: failed while {stage}"
                      for lang, stage in failed)
    return (
        f"## Reports not updated — {date}\n\n"
        "After today's daily refresh, these languages' PDF reports could not be made or "
        "put on Drive, so their Drive folders still hold the previous ones:\n\n"
        f"{lines}\n\n"
        "The reason is left out here, since it can quote the annotation and this "
        "repository is public. To see it, pull coded_data/ and run:\n\n"
        "```bash\npython -m coding generate-reports --apply\n```\n\n"
        "## What to do\n\n"
        "Fix the cause, then run that command (or wait for the next daily refresh, "
        "which runs it). This issue closes by itself when a run updates every "
        "language's report.\n")


def _report(failed: list[tuple[str, str]]) -> None:
    """File, rewrite or close the reports-error issue (--apply runs only)."""
    from datetime import datetime, timezone
    from . import issues
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if failed:
        number, created = issues.file_issue(ISSUE_LABEL, f"Reports not updated ({date})",
                                            issue_body(failed, date), replace=True)
        print(f"{'Filed' if created else 'Updated'} issue #{number} ({ISSUE_LABEL}).")
    else:
        closed = issues.close_open(ISSUE_LABEL, f"Every language's report updated on {date} — closing.")
        if closed:
            print(f"Closed {', '.join(f'#{n}' for n in closed)} ({ISSUE_LABEL}).")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding generate-reports`."""
    ap = argparse.ArgumentParser(
        description="Generate and upload PDF reports for all languages to Drive."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="generate and upload to Drive, and file or close the reports-error issue "
             "(default: dry run)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding generate-reports`."""
    if args is None:
        args = build_parser().parse_args()
    failed = _run(apply=args.apply)
    if args.apply:
        _report(failed)
    if failed:
        sys.exit(f"\nFailed for {', '.join(lang for lang, _ in failed)}; the other "
                 "languages ran. The lines above say at what stage.")


if __name__ == "__main__":
    main()
