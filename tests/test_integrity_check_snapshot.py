"""Snapshot tests for `python -m coding integrity-check`'s Drive section, run
against the fake.

File 14 of 18 migrated to the Drive doorway (#271). Its Drive footprint is
confined to two independent, read-only entry points: `_section_sheets` (the
`--sheets` flag, opening each language's class spreadsheets and comparing live
tab titles/headers against the diagnostics YAML) and `main()`'s
`--check-stale-sheets` fast path (reads the ID file and the YAML only, no Drive
calls at all -- used by the daily `data-refresh` workflow). Neither ever writes: this file only opens
spreadsheets, lists worksheet titles, and reads header rows, reporting
mismatches as printed warnings/errors. Every scenario below asserts
`doorway.mutations == []` for exactly that reason.

**How the pre-migration baseline was taken.** As for every file after the
first, a real-Drive dry run is not permitted before Phase 9. The substitute:
drive the *unmigrated* code (`from .drive import _get_clients,
_load_manifest_from_drive, _with_retry`, both local imports inside the
function bodies) from a `FakeDriveDoorway.from_fixtures()` through thin
`gc.open_by_key` / `_download_file_json` shims, guarding every unshimmed route
to real Drive so it raises rather than quietly working -- confirmed by
deliberately unpatching the guard and checking it actually raises before
trusting any scenario. Ten scenarios were run through both the unmigrated and
migrated code against identically seeded fakes: `--sheets` over all languages,
`--sheets --lang` for one language, a language whose manifest `spreadsheet_id`
does not exist in the fake (exercising the `except Exception` around
`open_spreadsheet`), a class whose live tab is missing, a class whose live
header has drifted from the manifest's `construction_params` (the
`sync-params --apply` warning path), a stale `_split_` column (the specific
remediation-text path), the plain run with no `--sheets` at all, and
`--check-stale-sheets` with a stale entry, with none, and with Drive unreachable.
stdout, exit codes, and the mutation logs (empty throughout) came back
byte-identical in all ten -- except one deliberate, documented case: line
~439's `ss = _with_retry(lambda: gc.open_by_key(...))` becomes
`doorway.open_spreadsheet(...)` with the outer retry wrapper *removed*, not
preserved, because the doorway retried the open itself (at the time via the
same `_with_retry` `coding/drive.py`'s `_open_spreadsheet` used; since Phase
10 unit 5b the Drive door retries every call and `_with_retry` is gone). Confirmed
behaviourally equivalent (not just documented as such): the fake raises
`SpreadsheetNotFound` for an unknown ID either way, and both the unmigrated and
migrated `bad_spreadsheet_id` scenario report the identical "could not open
spreadsheet" line. The shim script is a scratch throwaway per the plan's
convention, not committed.

Regenerate: PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_integrity_check_snapshot.py
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import drive_ids
from coding import integrity_check as ic
from command_runner import run_command
from fake_drive import FakeDriveDoorway, use_frozen_coded_data

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "integrity_check"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]

# main()'s header line stamps date.today() into stdout -- frozen so the full
# transcript snapshots (which include that header) don't drift with the
# calendar. The Drive section under test never reads the date itself.
_FROZEN_TODAY = date(2026, 8, 3)


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return _FROZEN_TODAY

# The command reads local TSVs from coded_data/, a separate repo that a bare
# worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive seeded from the three fixture languages, with the
    frozen copy of their local folders (never the live coded_data/, which
    changes whenever an annotator works -- see fake_drive.FROZEN_CODED_DATA).
    """
    doorway = FakeDriveDoorway.from_fixtures()
    use_frozen_coded_data(monkeypatch, tmp_path)
    monkeypatch.setattr(ic, "date", _FrozenDate)
    # The ID file the command reads; a test changes it through run_main.config.
    config = FakeDriveDoorway.drive_config()
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    drive_doorway.set_doorway(doorway)

    def run_main(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                run_command(ic, "integrity-check")
        except SystemExit as exc:
            exit_code = exc.code
        return buf.getvalue(), exit_code

    run_main.config = config
    try:
        yield doorway, run_main
    finally:
        drive_doorway.reset_doorway()


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}")
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff.")


def sheet_id(doorway, lang: str, class_name: str) -> str:
    return drive_ids.class_sheet_id(FakeDriveDoorway.drive_config(), lang, class_name)


def first_criterion_col(header: List[str]) -> int:
    for i, col in enumerate(header):
        if col not in ("Element", "Position_Name", "Position_Number", "Source", "Comments"):
            return i
    raise AssertionError("no criterion column found")


# ---------------------------------------------------------------------------
# Coordinator-facing transcripts
# ---------------------------------------------------------------------------

def test_sheets_arao1248_transcript(env):
    """Every tab matches today, on the real fixtures -- the all-clear path."""
    _, run_main = env
    out, _ = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    check_snapshot("sheets_arao1248.txt", out)


def test_check_stale_sheets_clean_transcript(env):
    _, run_main = env
    out, _ = run_main(["integrity-check", "--check-stale-sheets"])
    check_snapshot("check_stale_sheets_clean.txt", out)


# ---------------------------------------------------------------------------
# --sheets: mismatched header -> sync-params warning naming both column lists
# ---------------------------------------------------------------------------

def test_mismatched_header_names_expected_and_actual(env):
    doorway, run_main = env
    sid = sheet_id(doorway, "arao1248", "ciscategorial")
    ws = doorway.spreadsheet(sid).worksheet("general")
    header = ws.row_values(1)
    idx = first_criterion_col(header)
    ws._cell(0, idx).value = "renamed_criterion_col"

    out, exit_code = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    assert "expected criteria columns:" in out
    assert "actual criteria columns:" in out
    assert "renamed_criterion_col" in out
    assert "→ run: python -m coding sync-params --apply" in out
    # A header mismatch is a warning, not a blocking error, so the run passes.
    # (Until the 2026-10-19 refreeze it failed anyway: arao1248's diagnostics
    # file lacked required classes, Finding 19; it now has a proform stub.)
    assert exit_code is None
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# --sheets: a missing tab is an error, not fatal to the rest of the language
# ---------------------------------------------------------------------------

def test_missing_tab_is_an_error_and_does_not_stop_the_run(env):
    doorway, run_main = env
    sid = sheet_id(doorway, "arao1248", "subspanrepetition")
    ss = doorway.spreadsheet(sid)
    ss.del_worksheet(ss.worksheet("tso_clause_linkage"))
    doorway.clear_mutations()  # deleting the tab is test setup, not the command's own write

    out, exit_code = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    assert "subspanrepetition · tso_clause_linkage  —  tab missing from spreadsheet" in out
    # The sibling construction on the same spreadsheet is still checked.
    assert "✓  Araona [arao1248] · subspanrepetition · auxiliary_construction" in out
    assert exit_code == 1
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# --sheets: a stale _split_/_merged_ column gets its own remediation text
# ---------------------------------------------------------------------------

def test_stale_split_column_names_itself_and_the_remediation(env):
    doorway, run_main = env
    sid = sheet_id(doorway, "arao1248", "ciscategorial")
    ws = doorway.spreadsheet(sid).worksheet("general")
    header = ws.row_values(1)
    idx = first_criterion_col(header)
    ws._cell(0, idx).value = "_split_" + header[idx]

    out, exit_code = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    assert "stale split column '_split_" in out
    assert "Remap any cell values from the stale column(s)" in out
    assert "delete the stale" in out
    # This is a different remediation from the ordinary header-mismatch path.
    assert "→ run: python -m coding sync-params --apply" not in out
    # This scenario is a warning, not blocking, so the run passes (see
    # test_mismatched_header_names_expected_and_actual above).
    assert exit_code is None
    assert doorway.mutations == []


def test_stale_merged_column_uses_the_merge_wording(env):
    doorway, run_main = env
    sid = sheet_id(doorway, "arao1248", "ciscategorial")
    ws = doorway.spreadsheet(sid).worksheet("general")
    header = ws.row_values(1)
    idx = first_criterion_col(header)
    ws._cell(0, idx).value = "_merged_" + header[idx]

    out, _ = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    assert "stale merge column '_merged_" in out
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# --sheets: an unreachable spreadsheet is reported per-class, not fatal
# ---------------------------------------------------------------------------

def test_unreachable_spreadsheet_reported_per_class_not_fatal(env):
    doorway, run_main = env
    run_main.config["arao1248"]["class_sheets"]["ciscategorial"]["id"] = "does_not_exist_xyz"

    out, exit_code = run_main(["integrity-check", "--sheets", "--lang", "arao1248"])
    assert "ciscategorial  —  could not open spreadsheet:" in out
    # The other classes for this language are still checked.
    assert "✓  Araona [arao1248] · noninterruption · general" in out
    assert "✓  Araona [arao1248] · subspanrepetition · auxiliary_construction" in out
    assert exit_code == 1
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# Plain run (no --sheets) skips the Drive section and touches no Drive calls
# ---------------------------------------------------------------------------

def test_no_sheets_flag_skips_the_section_and_touches_no_drive_calls(env):
    doorway, run_main = env
    out, _ = run_main(["integrity-check", "--lang", "arao1248"])
    assert "(skipped — pass --sheets to check live sheet structure)" in out
    assert "ANNOTATION SHEETS" in out  # the section header still prints
    assert doorway.mutations == []
    # Confirm the skip is real, not partial: none of the per-class Drive-check
    # lines that --sheets would print show up anywhere in the transcript.
    assert "could not open spreadsheet" not in out
    assert "tab missing from spreadsheet" not in out
    assert "ciscategorial · general" not in out


# ---------------------------------------------------------------------------
# --check-stale-sheets: stale entries, none, and an unreadable ID file
# ---------------------------------------------------------------------------

def test_check_stale_sheets_reports_stale_entries_and_exits_1(env):
    doorway, run_main = env
    run_main.config["arao1248"]["class_sheets"]["ghost_class"] = {
        "id": "does_not_matter", "version": 1}

    out, exit_code = run_main(["integrity-check", "--check-stale-sheets"])
    assert "CLASS SHEETS NOT IN DIAGNOSTICS (1)" in out
    assert "ghost_class" in out
    assert "python -m coding retire-classes --apply" in out
    assert exit_code == 1
    assert doorway.mutations == []


def test_check_stale_sheets_clean_does_not_exit_nonzero(env):
    _, run_main = env
    out, exit_code = run_main(["integrity-check", "--check-stale-sheets"])
    assert "No class sheets recorded for classes absent from diagnostics." in out
    assert exit_code is None


def test_check_stale_sheets_fails_when_the_id_file_is_unreadable(env, monkeypatch):
    """The ID file is a local file (unit 11c), so one that can't be read is a
    real error: the check fails, and the refresh's issue shows why, rather
    than skipping as it did when it read the manifest from Drive."""
    doorway, run_main = env

    def _boom(*args, **kwargs):
        raise ValueError("drive_config.json: Expecting value: line 1 column 1")

    monkeypatch.setattr(drive_module, "_load_drive_config", _boom)
    with pytest.raises(ValueError, match="drive_config.json"):
        run_main(["integrity-check", "--check-stale-sheets"])
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# No scenario ever produces a mutation -- this file only ever reads
# ---------------------------------------------------------------------------

def test_full_sheets_run_across_all_languages_never_mutates(env):
    doorway, run_main = env
    run_main(["integrity-check", "--sheets"])
    assert doorway.mutations == []
