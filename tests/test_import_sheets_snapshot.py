"""Snapshot tests for `python -m coding import-sheets`, run against the fake.

File 15 of 18 migrated to the Drive doorway (#271) -- the command the daily
`data-refresh` GitHub Action runs to pull annotator work down from Sheets, and
the largest and most consequential file migrated so far (1,138 lines against
the last three files' combined total of well under that). Its Drive footprint:
`get_doorway()`/`load_manifest(doorway)` once, `doorway.open_spreadsheet(...)`
per class spreadsheet, `doorway.get_file(...)` in `_verify_manifest_sheet_ids`
(abort-before-download guard, `--apply` only), and `upload_manifest(doorway, ...)`
at the very end if the manifest's glottolog/meta/planar-structure fields drifted
from `schemas/languages.yaml` and the local planar. Cell highlighting
(`_highlight_invalid_cells`, delegating to `validate_coding.highlight_cells`)
and the final `revalidate_sheets()` call are handle-level operations that
needed no edits -- both already went through the doorway before this file did
(files 13 and 12 respectively).

**How the pre-migration baseline was taken.** As for every file after the
first, a real-Drive dry run is not permitted before Phase 9. The substitute:
drive the *unmigrated* code (`from .drive import _check_coded_data_clean,
_get_clients, _load_manifest_from_drive, _open_spreadsheet,
_upload_planars_config, _load_drive_config, _save_drive_config, _with_retry`,
all module-level) from a `FakeDriveDoorway.from_fixtures()` through thin
`gc`/`drive` shims -- `gc` is never really used once `_open_spreadsheet` is
shimmed to route straight to the doorway, and `drive` only needs a
`.files().get(fileId=..., fields=...).execute()` shape for
`_verify_manifest_sheet_ids`. Twenty-two scenarios were run through both the
unmigrated and migrated code against identically seeded fakes: dry run over
all languages and with `--lang`; `--apply` with no prior local TSVs
(first-time download); a baseline "already matches" run and a genuine content
change on top of it (archive-then-write); `--overwrite-existing` forcing a
rewrite despite unchanged content; a purely-additive in-order planar change
(queues `update-sheets --apply`, confirmed via a stubbed
`sys.modules["coding.update_sheets"]` recording the auto-applied call rather
than really running it) versus a deletion and a reorder (each its own pending
entry); an unrecognised criterion in the diagnostics sheet (ambiguous YAML
drift); a missing construction tab (`WorksheetNotFound`, warn and continue); a
class with no Status tab versus `--ignore-status` versus one construction set
to `ready-for-review` alongside others left `in-progress`; an injected invalid
cell (confirmed via the mutation log, not just stdout, since blank cells are
*also* pink-highlighted on real fixture data and so don't move the highlight
*count* -- the confirming check was a `updateCells` mutation at the exact
row/column touched, with the pink `{1.0, 0.8, 0.8}` background); a missing
local row on an in-progress tab (collaborator-check, not pending); a bad
manifest spreadsheet ID reached under `--apply` (clean abort, pre-download)
versus the same ID on a language excluded by `--lang` under a dry run
(silently never reached, confirmed by the *absence* of a crash); the manifest
metadata sync firing only when the computed planar structure actually
differs; and `--lang` leaving other languages' local trees untouched. stdout,
exit codes, the mutation logs, the local `coded_data/` tree contents,
`pending_changes.json`, and `diagnostics_drift.json` all came back
byte-identical in every scenario once `datetime.now()` was frozen (the
archive filename embeds a timestamp computed once at the top of `main()`, so
two real invocations a second apart otherwise disagreed on nothing but that).
The shim script and its scenario driver are scratch throwaways per the plan's
convention, not committed.

**A genuine finding, not introduced by this migration, fixed separately:** a
dry run had *no* protection at all against a manifest entry pointing at an
inaccessible spreadsheet. `_verify_manifest_sheet_ids` -- the clean "ERROR:
Manifest contains inaccessible spreadsheet IDs" abort -- only runs `if apply:`.
A dry run instead reached `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])`
inside the per-class loop with no `try`/`except` around it at all, so a bad ID
crashed the *entire* run -- every language, not just the one naming the bad
ID -- with an unhandled `SpreadsheetNotFound` traceback. Confirmed identical
between the unmigrated and migrated code (both raised the same exception at
the same point); recorded as Finding 13 in docs/data-layer-progress.md, and
fixed in a follow-up commit rather than in the migration itself, per the
migration's non-goal of no behaviour changes beyond the doorway swap. The
`open_spreadsheet` call is now wrapped in its own `try`/`except Exception`,
reported per class the same way a missing worksheet already is (`WARNING:
... skipping`, appended to `lang_warning_lines`, `total_warnings` incremented),
and the loop moves on to the next class rather than the next language --
so a bad ID only ever costs the preview of the one class that names it.

`_verify_manifest_sheet_ids`, `_read_sheet_as_df`, `_download_lang_setup_sheets`,
and `_read_status_tab` all took a `gc`/`drive`/`ss` parameter typed against
`gspread`; each now takes a `doorway`/handle instead, with the type annotation
dropped (the doorway has no `gspread.Client` equivalent to name). `gspread` is
no longer imported at all -- it was used only for those annotations and for
`except gspread.WorksheetNotFound`, now `except WorksheetNotFound` imported
from `drive_doorway` (the identical class, re-exported for exactly this).

`tests/test_import_sheets.py`'s `TestVerifyManifestSheetIds` mocked a raw
`drive` object shaped like `.files().get(fileId=..., fields=...).execute()`;
its six tests now pass a tiny local stub with a `get_file(self, file_id,
fields=None)` method instead, keeping the same behaviour under test (which IDs
abort, which don't) without depending on a shape `_verify_manifest_sheet_ids`
no longer receives.

`revalidate_sheets()` (called at the end of `main()` under `--apply`) reads
local TSVs from `coding.validate_coding.CODED_DATA`, a *separate* module-level
constant from this file's own `ROOT` -- both are redirected into the same
private tree in every test below, so the revalidation pass sees exactly what
`import-sheets` itself just wrote rather than the real repo's current
annotation state (which would make these snapshots drift for reasons having
nothing to do with this file).

Regenerate: PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_import_sheets_snapshot.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import import_sheets as is_
from coding import validate_coding as vc
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "import_sheets"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]
AUTO_APPLY_MODULES = ["coding.update_sheets", "coding.sync_params", "coding.generate_sheets"]

# The archive filename embeds datetime.now(), computed once at the top of
# main() -- frozen so two runs a second apart don't disagree on nothing else.
FROZEN = datetime(2026, 8, 4, 12, 0, 0)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN if tz is None else FROZEN.astimezone(tz)


# The command reads local TSVs and diagnostics YAMLs from coded_data/, a
# separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


class Env:
    """One stand-in Drive, one private copy of coded_data/, one command."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path,
                 auto_apply_calls: List[Tuple[str, List[str]]],
                 notified_pending: List[List[Dict]],
                 notified_collaborator: List[List[Dict]],
                 run: Callable[[List[str]], Tuple[str, Optional[int]]]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.auto_apply_calls = auto_apply_calls
        self.notified_pending = notified_pending
        self.notified_collaborator = notified_collaborator
        self.run = run

    # -- the manifest ---------------------------------------------------
    def manifest(self) -> Dict:
        return self.doorway.download_file_json(MANIFEST_FILE_ID)

    def mutate_manifest(self, fn: Callable[[Dict], None]) -> None:
        m = self.manifest()
        fn(m)
        self.doorway.file(MANIFEST_FILE_ID).content = json.dumps(m).encode("utf-8")

    def sheet_id(self, lang: str, cls: str) -> str:
        return self.manifest()[lang]["sheets"][cls]["spreadsheet_id"]

    def tab(self, lang: str, cls: str, construction: str):
        return self.doorway.spreadsheet(self.sheet_id(lang, cls)).worksheet(construction)

    def planar_sheet(self, lang: str):
        return self.doorway.spreadsheet(self.manifest()[lang]["planar_spreadsheet_id"]).sheet1

    def diagnostics_sheet(self, lang: str):
        return self.doorway.spreadsheet(self.manifest()[lang]["diagnostics_spreadsheet_id"]).sheet1

    def set_status(self, lang: str, cls: str, construction: str, status: str) -> None:
        ws = self.doorway.spreadsheet(self.sheet_id(lang, cls)).worksheet("Status")
        for r, row in enumerate(ws.get_all_values()):
            if row and row[0] == construction:
                ws._cell(r, 1).value = status
                return
        raise AssertionError(f"{construction!r} not found in Status tab")

    def remove_status_tab(self, lang: str, cls: str) -> None:
        ss = self.doorway.spreadsheet(self.sheet_id(lang, cls))
        ss.del_worksheet(ss.worksheet("Status"))

    def delete_tab(self, lang: str, cls: str, construction: str) -> None:
        ss = self.doorway.spreadsheet(self.sheet_id(lang, cls))
        ss.del_worksheet(ss.worksheet(construction))

    def edit_sheet_rows(self, ws, fn) -> None:
        rows = fn(ws.get_all_values())
        ws.clear()
        ws.update(rows, "A1")

    # -- the local tree ---------------------------------------------------
    def output_tsv(self, lang: str, cls: str, construction: str) -> Path:
        return self.coded / lang / cls / f"{construction}.tsv"

    def archives(self, lang: str, cls: str) -> List[Path]:
        return sorted((self.coded / lang / "archive" / cls).glob("*.tsv")) \
            if (self.coded / lang / "archive" / cls).exists() else []

    def planar_tsv(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"planar_{lang}.tsv"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(ROOT / "coded_data" / lang, coded / lang,
                        ignore=shutil.ignore_patterns(".git"))

    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "languages.yaml").write_text("{}\n", encoding="utf-8")

    auto_apply_calls: List[Tuple[str, List[str]]] = []

    def make_stub(name):
        def _main():
            auto_apply_calls.append((name, list(sys.argv)))
        return SimpleNamespace(main=_main)

    for name in AUTO_APPLY_MODULES:
        monkeypatch.setitem(sys.modules, name, make_stub(name))

    notified_pending: List[List[Dict]] = []
    notified_collaborator: List[List[Dict]] = []
    saved_config: List[Dict] = []

    monkeypatch.setattr(is_, "ROOT", tmp_path)
    monkeypatch.setattr(is_, "ERROR_DIR", tmp_path / "import_errors")
    monkeypatch.setattr(is_, "PENDING_PATH", tmp_path / "pending_changes.json")
    monkeypatch.setattr(is_, "DRIFT_PATH", tmp_path / "diagnostics_drift.json")
    monkeypatch.setattr(is_, "datetime", _FrozenDatetime)
    monkeypatch.setattr(is_, "_notify_pending_changes", notified_pending.append)
    monkeypatch.setattr(is_, "_notify_collaborator_check", notified_collaborator.append)
    monkeypatch.setattr(is_, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(is_, "_save_drive_config", saved_config.append)
    # load_manifest()/upload_manifest() are defined in coding/drive.py and call
    # THAT module's own _load_drive_config() -- patching import_sheets.py's
    # imported copy alone leaves them looking at the real drive_config.json.
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    # revalidate_sheets() reads local TSVs from validate_coding's own
    # CODED_DATA constant, not this file's ROOT.
    monkeypatch.setattr(vc, "CODED_DATA", coded)
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> Tuple[str, Optional[int]]:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(buf):
                is_.main()
        except SystemExit as exc:
            exit_code = exc.code
        return buf.getvalue(), exit_code

    try:
        yield Env(doorway, coded, auto_apply_calls, notified_pending,
                  notified_collaborator, run)
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


def add_planar_position(rows: List[List[str]]) -> List[List[str]]:
    """One more position, numbered after the current last -- in-order addition."""
    header = rows[0]
    pos_idx, name_idx = header.index("Position"), header.index("Position_Name")
    numbers = [int(r[pos_idx]) for r in rows[1:] if r[pos_idx].strip().isdigit()]
    new_row = list(rows[-1])
    new_row[pos_idx] = str(max(numbers) + 1)
    new_row[name_idx] = "x:newpos-test"
    return rows + [new_row[:len(header)]]


def drop_last_planar_position(rows: List[List[str]]) -> List[List[str]]:
    return rows[:-1]


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Nothing changed anywhere -- the ordinary daily "nothing to do" run."""
    out, exit_code = env.run(["import-sheets"])
    assert exit_code is None
    check_snapshot("dry_run.txt", out)


def test_verify_aborts_transcript(env):
    """A manifest entry pointing at a spreadsheet the fake has never seen."""
    env.mutate_manifest(lambda m: m["arao1248"]["sheets"]["ciscategorial"]
                        .__setitem__("spreadsheet_id", "does_not_exist_xyz"))
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert exit_code == 1
    check_snapshot("verify_aborts.txt", out)


def test_apply_multiple_kinds_of_change_transcript(env):
    """One safe planar addition, one destructive planar deletion, one content
    change -- each on a different language, in the same run."""
    env.edit_sheet_rows(env.planar_sheet("arao1248"), add_planar_position)
    env.edit_sheet_rows(env.planar_sheet("stan1293"), drop_last_planar_position)
    env.tab("synth0001", "ciscategorial", "general")._cell(1, 3).value = "y"
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert exit_code is None
    check_snapshot("apply_multiple_changes.txt", out)


# ---------------------------------------------------------------------------
# --apply: first download, no-op, forced overwrite
# ---------------------------------------------------------------------------

def test_first_time_download_writes_every_construction(env):
    for cls_dir in (env.coded / "arao1248").iterdir():
        if cls_dir.is_dir() and cls_dir.name not in ("lang_setup", "archive"):
            shutil.rmtree(cls_dir)
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert "Would create" not in out  # this is --apply, not a dry run
    assert env.output_tsv("arao1248", "ciscategorial", "general").exists()
    assert env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").exists()


def test_a_noop_apply_writes_no_new_tsvs_or_archives(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize
    before = env.output_tsv("arao1248", "ciscategorial", "general").read_text()
    n_archives_before = len(env.archives("arao1248", "ciscategorial"))

    out, exit_code = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert exit_code is None
    assert "No changes" in out
    assert env.output_tsv("arao1248", "ciscategorial", "general").read_text() == before
    assert len(env.archives("arao1248", "ciscategorial")) == n_archives_before


def test_overwrite_existing_forces_a_rewrite_despite_unchanged_content(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize
    n_archives_before = len(env.archives("arao1248", "ciscategorial"))

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply",
                      "--overwrite-existing"])

    assert "Archived existing" in out
    assert len(env.archives("arao1248", "ciscategorial")) == n_archives_before + 1


def test_content_change_archives_before_overwriting(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize
    before = env.output_tsv("arao1248", "ciscategorial", "general").read_text()
    # coded_data/ carries pre-existing archives from real history; count the
    # delta this run adds, not an absolute total.
    n_archives_before = len(env.archives("arao1248", "ciscategorial"))
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "y"

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert "Archived existing" in out
    archives = env.archives("arao1248", "ciscategorial")
    assert len(archives) == n_archives_before + 1
    newest = max(archives, key=lambda p: p.stat().st_mtime)
    assert newest.read_text() == before
    assert env.output_tsv("arao1248", "ciscategorial", "general").read_text() != before


# ---------------------------------------------------------------------------
# Planar structural changes: safe addition vs. destructive deletion/reorder
# ---------------------------------------------------------------------------

def test_planar_pure_addition_queues_update_sheets_and_auto_applies_it(env):
    env.edit_sheet_rows(env.planar_sheet("arao1248"), add_planar_position)
    out, _ = env.run(["import-sheets", "--apply"])
    assert "queuing update-sheets" in out
    assert ("coding.update_sheets", ["update-sheets", "--apply"]) in env.auto_apply_calls
    assert not is_.PENDING_PATH.exists()


def test_planar_deletion_produces_a_pending_entry_not_an_auto_apply(env):
    env.edit_sheet_rows(env.planar_sheet("stan1293"), drop_last_planar_position)
    out, _ = env.run(["import-sheets", "--apply"])
    assert is_.PENDING_PATH.exists()
    entries = json.loads(is_.PENDING_PATH.read_text())
    assert any(e["change_type"] == "planar_deletion_or_reorder"
              and e["lang_id"] == "stan1293" for e in entries)
    assert env.auto_apply_calls == []
    assert env.notified_pending  # _notify_pending_changes was called


def test_planar_reorder_is_also_destructive(env):
    def reorder(rows):
        # Swap which position occupies slots 1 and 2, keeping the Position
        # numbers themselves sequential (1, 2, 3, ...) -- swapping whole rows
        # instead would leave Position reading 2, 1, 3, ... and get caught
        # upstream by planar structural validation ("not sequential 1..N")
        # before change-detection is ever reached.
        header = rows[0]
        pos_idx = header.index("Position")
        out = [list(r) for r in rows]
        row1, row2 = list(out[1]), list(out[2])
        for i in range(len(header)):
            if i == pos_idx:
                continue
            row1[i], row2[i] = row2[i], row1[i]
        out[1], out[2] = row1, row2
        return out
    env.edit_sheet_rows(env.planar_sheet("synth0001"), reorder)
    out, _ = env.run(["import-sheets", "--apply"])
    entries = json.loads(is_.PENDING_PATH.read_text())
    assert any(e["change_type"] == "planar_deletion_or_reorder"
              and e["lang_id"] == "synth0001" for e in entries)
    assert "Position order changed" in entries[0]["diff_summary"]


# ---------------------------------------------------------------------------
# Diagnostics YAML drift
# ---------------------------------------------------------------------------

def test_an_unrecognised_criterion_is_ambiguous_drift_not_a_crash(env):
    # stan1293, not arao1248: arao1248's diagnostics_arao1248.yaml is missing
    # three collection_required: "y" classes (Finding 19), which now blocks
    # its diagnostics download entirely ("Validation errors — skipping
    # download") before drift detection ever runs. stan1293 declares every
    # required class, so this scenario actually reaches the drift path.
    def add_unknown(rows):
        header = rows[0]
        class_idx, crit_idx = header.index("Class"), header.index("Criteria")
        out = [list(r) for r in rows]
        for r in out[1:]:
            if len(r) > class_idx and r[class_idx] == "ciscategorial":
                r[crit_idx] += ", totally_made_up_zyx"
                break
        return out
    env.edit_sheet_rows(env.diagnostics_sheet("stan1293"), add_unknown)

    out, _ = env.run(["import-sheets", "--apply"])

    assert "ambiguous YAML drift" in out
    assert is_.DRIFT_PATH.exists()
    drift = json.loads(is_.DRIFT_PATH.read_text())
    entry = next(d for d in drift if d["lang_id"] == "stan1293")
    assert entry["ambiguous"][0]["criterion"] == "totally_made_up_zyx"


# ---------------------------------------------------------------------------
# A missing construction tab warns and continues
# ---------------------------------------------------------------------------

def test_a_missing_tab_warns_and_does_not_stop_the_rest_of_the_language(env):
    before = env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").read_text()
    env.delete_tab("arao1248", "subspanrepetition", "tso_clause_linkage")
    out, _ = env.run(["import-sheets", "--apply"])
    assert "[subspanrepetition/tso_clause_linkage] tab not found in sheet, skipping" in out
    # The sibling construction on the same spreadsheet is still imported.
    assert env.output_tsv("arao1248", "subspanrepetition", "auxiliary_construction").exists()
    # The missing tab's local TSV (pre-existing from real history) is left
    # alone entirely -- the run never reaches the point of writing it.
    assert env.output_tsv("arao1248", "subspanrepetition", "tso_clause_linkage").read_text() == before


# ---------------------------------------------------------------------------
# Status tab: absent, --ignore-status, and a mixed in-progress/ready tab
# ---------------------------------------------------------------------------

def test_no_status_tab_treats_every_construction_as_ready_for_review(env):
    env.remove_status_tab("arao1248", "ciscategorial")
    out, _ = env.run(["import-sheets", "--apply"])
    assert "(no Status tab found — importing all constructions)" in out
    # A ready-for-review construction is never labelled "[backup]".
    assert "[general] [backup]" not in out.split("noninterruption")[0]


def test_ignore_status_treats_every_tab_as_ready_for_review(env):
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply", "--ignore-status"])
    assert "in-progress" not in out
    assert "[backup]" not in out


def test_mixed_status_only_treats_the_flipped_construction_as_ready(env):
    env.set_status("arao1248", "ciscategorial", "general", "ready-for-review")
    out, _ = env.run(["import-sheets", "--apply"])
    ciscategorial_section = out.split("noninterruption")[0]
    noninterruption_section = out.split("noninterruption")[1].split("subspanrepetition")[0]
    assert "in-progress" not in ciscategorial_section
    assert "status: 'in-progress' — importing for backup" in noninterruption_section


# ---------------------------------------------------------------------------
# Invalid cells get pink-highlighted
# ---------------------------------------------------------------------------

def test_an_invalid_cell_is_pink_highlighted(env):
    sid = env.sheet_id("arao1248", "ciscategorial")
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "maybe123"

    env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    hits = [
        m for m in env.doorway.mutations
        if m.get("op") == "batch_request" and m.get("request_type") == "updateCells"
        and m.get("spreadsheet") == sid
        and m["payload"]["range"].get("startRowIndex") == 1
        and m["payload"]["range"].get("startColumnIndex") == 3
    ]
    assert hits, "expected a pink-highlight write for the invalid cell"
    assert hits[0]["payload"]["rows"][0]["values"][0]["userEnteredFormat"]["backgroundColor"] \
        == {"red": 1.0, "green": 0.8, "blue": 0.8}


# ---------------------------------------------------------------------------
# A missing local row on an in-progress tab: collaborator-check, not pending
# ---------------------------------------------------------------------------

def test_a_missing_row_on_an_in_progress_tab_is_a_collaborator_check_not_pending(env):
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])  # materialize

    def drop_first_data_row(rows):
        return [rows[0]] + rows[2:]
    env.edit_sheet_rows(env.tab("arao1248", "ciscategorial", "general"), drop_first_data_row)

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert "ANOMALY: Missing rows" in out
    assert not is_.PENDING_PATH.exists()
    assert env.notified_collaborator
    assert env.notified_collaborator[0][0]["class_name"] == "ciscategorial"


# ---------------------------------------------------------------------------
# _verify_manifest_sheet_ids only ever runs under --apply
# ---------------------------------------------------------------------------

def test_verify_aborts_before_any_download_under_apply(env):
    env.mutate_manifest(lambda m: m["arao1248"]["sheets"]["ciscategorial"]
                        .__setitem__("spreadsheet_id", "does_not_exist_xyz"))
    out, exit_code = env.run(["import-sheets", "--apply"])
    assert exit_code == 1
    assert "ERROR: Manifest contains inaccessible spreadsheet IDs" in out
    assert "Language:" not in out  # aborted before the per-language loop started
    assert env.doorway.mutations == []


def test_verify_is_skipped_on_a_dry_run_that_never_reaches_the_bad_id(env):
    """A bad ID on a language the --lang filter excludes never gets checked at
    all on a dry run -- confirmed by the run completing normally rather than
    raising, since a reached bad ID has no guard on a dry run (see the module
    docstring's Finding). Not asserting "ERROR" not in out overall: arao1248's
    diagnostics_arao1248.yaml is genuinely missing three collection_required:
    "y" classes (Finding 19), which surfaces its own unrelated ERROR lines on
    every run for this language -- the thing this test actually checks is
    that stan1293's bad ID is never reached."""
    env.mutate_manifest(lambda m: m["stan1293"]["sheets"]["ciscategorial"]
                        .__setitem__("spreadsheet_id", "does_not_exist_xyz"))
    out, exit_code = env.run(["import-sheets", "--lang", "arao1248"])
    assert exit_code is None
    assert "does_not_exist_xyz" not in out
    assert "inaccessible spreadsheet" not in out


def test_a_bad_id_reached_on_a_dry_run_warns_and_previews_every_other_language(env):
    """Finding 13, fixed: a dry run used to have no guard at all -- reaching a
    bad manifest spreadsheet ID crashed the entire run with an unhandled
    exception, stopping every language, not just the one naming it. Now the
    bad ID is reported as a per-class warning and the run continues,
    previewing every other class and every other language exactly as if the
    bad ID were never there."""
    env.mutate_manifest(lambda m: m["stan1293"]["sheets"]["ciscategorial"]
                        .__setitem__("spreadsheet_id", "does_not_exist_xyz"))
    out, exit_code = env.run(["import-sheets"])

    assert exit_code is None
    assert "WARNING" in out
    assert "ciscategorial" in out
    assert "stan1293" in out
    # Every language still gets previewed -- the run did not stop at stan1293.
    assert "Language: arao1248" in out
    assert "Language: stan1293" in out
    assert "Language: synth0001" in out
    # stan1293's other classes (not just ciscategorial) are still reached.
    other_classes = [c for c in env.manifest()["stan1293"]["sheets"] if c != "ciscategorial"]
    assert other_classes, "expected stan1293 to have more than one class in the manifest"
    for cls in other_classes:
        assert f"\n  {cls}" in out


# ---------------------------------------------------------------------------
# Manifest metadata sync: uploads only when the planar structure changed
# ---------------------------------------------------------------------------

def test_manifest_metadata_sync_uploads_when_the_planar_structure_changed(env):
    env.mutate_manifest(lambda m: m["arao1248"].__setitem__(
        "planar", {"keystone_pos": 999, "positions": []}))

    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    assert "manifest.json updated on Drive" in out
    updates = [m for m in env.doorway.mutations if m["op"] == "update_file"
              and m["file_id"] == MANIFEST_FILE_ID]
    assert len(updates) == 1
    assert env.manifest()["arao1248"]["planar"]["keystone_pos"] != 999


def test_manifest_metadata_sync_uploads_nothing_when_unchanged(env):
    out, _ = env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert "manifest.json updated on Drive" not in out
    assert not any(m["op"] == "update_file" and m["file_id"] == MANIFEST_FILE_ID
                  for m in env.doorway.mutations)


# ---------------------------------------------------------------------------
# --lang restricts the run to one language
# ---------------------------------------------------------------------------

def test_lang_filter_leaves_other_languages_local_trees_untouched(env):
    for lang in LANGS:
        env.tab(lang, "ciscategorial", "general")._cell(1, 3).value = "y"
    before = {
        lang: (env.coded / lang / "ciscategorial" / "general.tsv").read_text()
        if (env.coded / lang / "ciscategorial" / "general.tsv").exists() else None
        for lang in LANGS if lang != "arao1248"
    }

    env.run(["import-sheets", "--lang", "arao1248", "--apply"])

    for lang, content in before.items():
        current = env.coded / lang / "ciscategorial" / "general.tsv"
        assert (current.read_text() if current.exists() else None) == content


# ---------------------------------------------------------------------------
# Pair-row constructions (coreference, nonpermutability, phrasal_accent) go
# through the pair-row validator; standard constructions go through the
# element-row validator. Both live in stan1293's manifest entry.
# ---------------------------------------------------------------------------

def test_pair_row_and_standard_constructions_both_import_cleanly(env):
    out, exit_code = env.run(["import-sheets", "--lang", "stan1293", "--apply"])
    assert exit_code is None
    assert env.output_tsv("stan1293", "ciscategorial", "general").exists()       # element rows
    assert env.output_tsv("stan1293", "coreference", "reflexivization").exists()  # pair rows
    assert env.output_tsv("stan1293", "nonpermutability", "general").exists()     # pair rows


def test_pair_row_constructions_are_read_from_the_schema_not_hardcoded(env):
    """coreference's three constructions and nonpermutability/general are
    pair-row constructions (see the schema's row_type field); phrasal_accent's
    general construction is too, but its live tab is a documented exception --
    #275, still in the pre-pair-rows shape pending Adam's prescreening
    annotation, so it is not useful evidence here. This used to be a
    hardcoded class list in this file that missed phrasal_accent entirely
    (data_dependency_schema/facts.yaml's pair_row_construction_set); confirms
    a genuinely pair-shaped live tab round-trips through _validate_pair_tab
    with its Element_A/Position_A/Position_B columns intact."""
    env.run(["import-sheets", "--lang", "stan1293", "--apply"])
    header = pd.read_csv(
        env.output_tsv("stan1293", "coreference", "reflexivization"), sep="\t", nrows=0,
    ).columns.tolist()
    assert header[:3] == ["Element_A", "Position_A", "Position_B"]
    assert "Element" not in header  # the element-row path's own column


# ---------------------------------------------------------------------------
# Defensive check: import-sheets never writes a criterion-shaped thing onto
# Source/Comments. It reads construction_params for validation only (fed into
# _validate_tab/_validate_pair_tab) and never writes a dropdown or a note --
# its only sheet write is highlight_cells, which paints backgrounds. Expected
# to always pass; kept as a guard against this file gaining such a write later.
# ---------------------------------------------------------------------------

def test_never_writes_a_criterion_shaped_thing_onto_trailing_columns(env):
    env.tab("arao1248", "ciscategorial", "general")._cell(1, 3).value = "maybe123"
    env.run(["import-sheets", "--lang", "arao1248", "--apply"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)
