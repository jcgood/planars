"""Snapshot tests for `python -m coding integrity-check`'s Drive section, run
against the fake.

File 14 of 18 migrated to the Drive doorway (#271). Its Drive footprint is
confined to two independent, read-only entry points: `_section_sheets` (the
`--sheets` flag, opening each language's class spreadsheets and comparing live
tab titles/headers against the manifest) and `main()`'s `--check-manifest` fast
path (downloads the manifest only, no Sheet API calls at all -- used by the
daily `data-refresh` workflow). Neither ever writes: this file only opens
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
`--check-manifest` with a stale entry, with none, and with Drive unreachable.
stdout, exit codes, and the mutation logs (empty throughout) came back
byte-identical in all ten -- except one deliberate, documented case: line
~439's `ss = _with_retry(lambda: gc.open_by_key(...))` becomes
`doorway.open_spreadsheet(...)` with the outer retry wrapper *removed*, not
preserved, because `drive_doorway.DriveDoorway.open_spreadsheet` retries
internally via the exact same `_with_retry(lambda: gc.open_by_key(...))`
`coding/drive.py`'s `_open_spreadsheet` already used -- the doorway's own
docstring names this idiom as the one case it deliberately unifies. Confirmed
behaviourally equivalent (not just documented as such): the fake raises
`SpreadsheetNotFound` for an unknown ID either way, and both the unmigrated and
migrated `bad_spreadsheet_id` scenario report the identical "could not open
spreadsheet" line. The shim script is a scratch throwaway per the plan's
convention, not committed.

A pre-existing bug unrelated to this migration was found while taking the
baseline, worked around in the harness only (not fixed) to get the baseline
at all, and then fixed as its own follow-up commit right after the migration
landed -- see Finding 12 in docs/data-layer-progress.md. `_stale_manifest_param_values`
(~line 274) called `refresh_dropdowns._fresh_param_values` with 6 positional
arguments; that function has taken 4 since `b399e32` (#272's fix,
2026-08-02). Every `--sheets` run with any construction carrying
`param_names` -- effectively every real run -- had been raising `TypeError`
before reaching any Drive call at all since that commit, uncaught because
nothing exercised `_section_sheets` before now. Neither function touches
Drive, so the fix is orthogonal to this migration and lives in its own
commit; `test_stale_param_values_reports_a_real_mismatch_without_crashing`
below pins the fixed behaviour.

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
from coding import integrity_check as ic
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID

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
def env(monkeypatch):
    """A stand-in Drive seeded from the three fixture languages.

    No private copy of coded_data/ is needed here (unlike validate_coding's
    fixture) -- this command never writes to coded_data/, only reads it, and
    the checked-out copy already holds exactly the three fixture languages.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    monkeypatch.setattr(ic, "date", _FrozenDate)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)

    def run_main(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                ic.main()
        except SystemExit as exc:
            exit_code = exc.code
        return buf.getvalue(), exit_code

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


def mutate_manifest(doorway, fn) -> None:
    """Load manifest.json, apply fn(manifest) in place, write it back."""
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    fn(manifest)
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode("utf-8")


def sheet_id(doorway, lang: str, class_name: str) -> str:
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    return manifest[lang]["sheets"][class_name]["spreadsheet_id"]


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


def test_check_manifest_clean_transcript(env):
    _, run_main = env
    out, _ = run_main(["integrity-check", "--check-manifest"])
    check_snapshot("check_manifest_clean.txt", out)


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
    assert exit_code is None  # a header mismatch is a warning, not a blocking error
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
    assert exit_code is None  # warning, not blocking
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
# --sheets: stale param_values are reported without crashing (Finding 12's
# regression test -- _stale_manifest_param_values used to raise TypeError
# before any of the Drive-touching code below it ever ran)
# ---------------------------------------------------------------------------

def test_stale_param_values_reports_a_real_mismatch_without_crashing(env):
    """synth0001's coreference pair tabs are a real, already-known instance
    of stale param_values (see coding/CLAUDE.md's "Held until Phase 9" list,
    and CLAUDE.md's matching note): each manifest entry still lists all three
    pair criteria (reflexive_allowed, pronoun_allowed, np_allowed) while the
    diagnostics YAML gives each construction just the one it actually uses.
    No manifest mutation needed to exercise this -- the mismatch already
    exists in the fixtures."""
    _, run_main = env
    out, _ = run_main(["integrity-check", "--sheets", "--lang", "synth0001"])
    assert "param_values out of sync with YAML" in out
    assert "coreference · prescreening" in out
    assert "referential: stored=" in out
    assert "→ run: python -m coding refresh-dropdowns --apply" in out
    # Not asserting main()'s overall exit code here: synth0001's fixture data
    # also carries real, already-known DEPENDENT CONSTRUCTION STALENESS errors
    # (coreference/prescreening -> its three pair constructions -- see
    # coding/CLAUDE.md's "Held until Phase 9" list) that force exit_code == 1
    # regardless of this test's target. A param_values mismatch is a warning
    # on its own within this section -- confirmed directly instead.
    with redirect_stdout(io.StringIO()):
        e, w = ic._section_sheets(["synth0001"])
    assert e == 0
    assert w >= 4  # the four param_values warnings above, at minimum


# ---------------------------------------------------------------------------
# --sheets: an unreachable spreadsheet is reported per-class, not fatal
# ---------------------------------------------------------------------------

def test_unreachable_spreadsheet_reported_per_class_not_fatal(env):
    doorway, run_main = env
    mutate_manifest(doorway, lambda m: m["arao1248"]["sheets"]["ciscategorial"]
                     .__setitem__("spreadsheet_id", "does_not_exist_xyz"))

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
# --check-manifest: stale entries, a clean manifest, and Drive unavailable
# ---------------------------------------------------------------------------

def test_check_manifest_reports_stale_entries_and_exits_1(env):
    doorway, run_main = env
    mutate_manifest(doorway, lambda m: m["arao1248"]["sheets"].__setitem__(
        "ghost_class", {"spreadsheet_id": "does_not_matter",
                        "constructions": ["general"], "construction_params": {}}))

    out, exit_code = run_main(["integrity-check", "--check-manifest"])
    assert "STALE MANIFEST ENTRIES (1)" in out
    assert "ghost_class" in out
    assert "python -m coding prune-manifest --apply" in out
    assert exit_code == 1
    assert doorway.mutations == []


def test_check_manifest_clean_does_not_exit_nonzero(env):
    _, run_main = env
    out, exit_code = run_main(["integrity-check", "--check-manifest"])
    assert "No stale manifest entries." in out
    assert exit_code is None


def test_check_manifest_warns_and_continues_when_drive_is_unavailable(env, monkeypatch):
    """Designed to warn and move on, not crash -- see the comment at
    coding/integrity_check.py ~line 869: a daily workflow run should not file a
    misleading stale-manifest issue just because Drive was briefly unreachable."""
    doorway, run_main = env

    def _boom():
        raise ConnectionError("simulated Drive outage")

    monkeypatch.setattr(drive_doorway, "get_doorway", _boom)
    out, exit_code = run_main(["integrity-check", "--check-manifest"])
    assert "WARNING: Could not load manifest" in out
    assert "simulated Drive outage" in out
    assert "skipping stale manifest check" in out
    assert exit_code is None  # returns cleanly rather than sys.exit(1)
    assert doorway.mutations == []


# ---------------------------------------------------------------------------
# No scenario ever produces a mutation -- this file only ever reads
# ---------------------------------------------------------------------------

def test_full_sheets_run_across_all_languages_never_mutates(env):
    doorway, run_main = env
    run_main(["integrity-check", "--sheets"])
    assert doorway.mutations == []
