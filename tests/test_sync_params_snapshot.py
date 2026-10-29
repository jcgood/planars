"""Snapshot tests for `python -m coding sync-params`, run against the fake.

File 16 of 18 migrated to the Drive doorway (#271). `sync_params` is the file
the migration order flagged as the one to watch: it inserts and deletes
criterion columns, which is the densest form of the question behind #272 and
Finding 10 — whether a command derives a tab's criterion columns from the
tab's own header (correct) or from the manifest's `construction_params`
(wrong, because the manifest is bookkeeping and goes stale). Read closely for
this migration, `_get_current_params` and `_insert_param_columns` both
already derive columns from the tab's own header row — never from the
manifest. `assert_no_criterion_writes_onto_trailing_columns`
below passes cleanly for every scenario, confirming this rather than assuming
it.

Before migrating, the old code was driven from this same stand-in Drive
through `gc`/`drive` shims patched into `coding.sync_params`'s own namespace
(not `coding.drive`'s — the lesson from files 5 and 15), with a socket-level
guard raising on any connection not to localhost, across fifteen scenarios:
a plain dry run and apply over the real fixture data (which already contains
one genuine drift — `synth0001`'s three `coreference` pair tabs each still
carry all three pair criteria, while the diagnostics YAML narrows each
construction to its own one); a new criterion added to the diagnostics YAML,
dry run and apply; `--apply --remove` against that real coreference drift;
`--rename` unscoped and scoped to one class; `--split`; `--merge`; both
code paths of `--refresh-dropdowns` (removed 2026-10-23 with the manifest's
copy of each criterion's values it relied on); a class present in the manifest but absent from the diagnostics YAML; and a
plain apply/dry-run baseline confirming the manifest is only rewritten when
something actually changed. stdout, the mutation log, and the rewritten
`diagnostics_{lang_id}.yaml` files in `coded_data/` (and the TSV copies,
deleted 2026-10-27) all came back
byte-identical between the unmigrated and migrated code.

`CODED_DATA` is redirected into a temp tree in every test, for both this
module and `generate_sheets` (`sync_params` imports `CODED_DATA` from it).

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_sync_params_snapshot.py`
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import yaml as _yaml
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List

import pytest

from coding import drive as drive_module
from coding import drive_doorway, drive_ids
from coding import generate_notebooks as gn
from coding import sync_params as sp
from command_runner import run_command
from fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway, MANIFEST_FILE_ID, point_coded_data_at
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "sync_params"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]

# The command reads each language's planar/diagnostics files from coded_data/,
# a separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


class Env:
    """One stand-in Drive, one private copy of the language setup files."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path,
                 notebook_calls: List[bool], run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.notebook_calls = notebook_calls
        self.run = run

    # -- the ID file ----------------------------------------------------
    def sheet_id(self, lang: str, class_name: str) -> str:
        return drive_ids.class_sheet_id(FakeDriveDoorway.drive_config(), lang, class_name)

    def tab(self, lang: str, class_name: str, construction: str):
        return self.doorway.spreadsheet(
            self.sheet_id(lang, class_name)).worksheet(construction)

    # -- the local diagnostics YAML ---------------------------------------
    def yaml_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml"

    def edit_yaml(self, lang: str, fn) -> None:
        data = _yaml.safe_load(self.yaml_path(lang).read_text(encoding="utf-8"))
        fn(data)
        self.yaml_path(lang).write_text(
            _yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def add_criterion(self, lang: str, class_name: str, name: str,
                      values: List[str] = ("y", "n")) -> None:
        """The ordinary case: a new criterion added to a class in the YAML."""
        self.edit_yaml(lang, lambda d: d["classes"][class_name]["criteria"]
                       .__setitem__(name, list(values)))

    # -- reading the stand-in Drive back ----------------------------------
    def all_tab_values(self) -> Dict:
        return {
            (ss_id, ws.title): ws.get_all_values()
            for ss_id, ss in self.doorway._spreadsheets.items()
            for ws in ss.worksheets()
        }


# Criteria a --split/--merge creates must be defined in the schema with values
# (no [y, n] default since 2026-10-12). These tests invent names, so they
# declare those names' values here instead of in diagnostic_criteria.yaml.
_TEST_CRITERIA = {"free_left": ["y", "n"], "free_right": ["y", "n"],
                  "widescope_either": ["y", "n"]}


@pytest.fixture(autouse=True)
def _test_criteria(monkeypatch):
    real = sp.criterion_values
    monkeypatch.setattr(sp, "criterion_values", lambda n: _TEST_CRITERIA.get(n) or real(n))


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(FROZEN_CODED_DATA / lang / "lang_setup",
                        coded / lang / "lang_setup")

    notebook_calls: List[bool] = []

    point_coded_data_at(monkeypatch, coded)
    monkeypatch.setattr(sp, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    monkeypatch.setattr(gn, "regenerate_notebooks",
                        lambda: notebook_calls.append(True))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                run_command(sp, "sync-params")
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, notebook_calls, run)
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


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_baseline_transcript(env):
    """Real fixture data as committed — including the one genuine drift.

    synth0001's coreference pair tabs each carry all three pair criteria while
    the diagnostics YAML narrows each construction to its own one, so this
    dry run already shows real WARNING lines, not a constructed scenario.
    """
    check_snapshot("dry_run_baseline.txt", env.run(["sync-params"]))


def test_apply_baseline_transcript(env):
    check_snapshot("apply_baseline.txt", env.run(["sync-params", "--apply"]))


def test_dry_run_new_param_transcript(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    check_snapshot("dry_run_new_param.txt", env.run(["sync-params"]))


def test_apply_new_param_transcript(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    check_snapshot("apply_new_param.txt", env.run(["sync-params", "--apply"]))


def test_apply_new_param_digest(env):
    """The rendered write log — tab titles and column headers resolved.

    The artifact to review, not the raw JSON — see update_sheets' precedent
    (docs/data-layer-progress.md § Findings 9-11): raw sheetIds and 0-based
    column indices hid a bug through a first reading twice already.
    """
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params", "--apply"])
    check_snapshot("apply_new_param_digest.txt", render(env.doorway.mutations))


def test_apply_remove_transcript(env):
    """--remove against the real synth0001 coreference drift."""
    check_snapshot("apply_remove.txt", env.run(["sync-params", "--apply", "--remove"]))


def test_apply_rename_all_classes_transcript(env):
    check_snapshot(
        "apply_rename_all.txt",
        env.run(["sync-params", "--apply", "--rename", "free:free_form"]))


def test_apply_rename_scoped_to_class_transcript(env):
    check_snapshot(
        "apply_rename_scoped.txt",
        env.run(["sync-params", "--apply", "--rename",
                "noninterruption:free:free_form"]))


def test_apply_split_transcript(env):
    check_snapshot(
        "apply_split.txt",
        env.run(["sync-params", "--apply", "--split", "free:free_left:free_right"]))


def test_apply_merge_transcript(env):
    check_snapshot(
        "apply_merge.txt",
        env.run(["sync-params", "--apply", "--merge",
                "widescope_right:widescope_left:widescope_either"]))


def test_a_class_not_in_diagnostics_is_named(env):
    env.edit_yaml("stan1293", lambda d: d["classes"].pop("proform"))
    out = env.run(["sync-params"])
    assert "[proform] Not in diagnostics_stan1293.yaml — skipping" in out


def test_a_missing_tab_is_named_and_skipped(env):
    ss = env.doorway.spreadsheet(env.sheet_id("stan1293", "subspanrepetition"))
    ss.del_worksheet(ss.worksheet("control"))
    out = env.run(["sync-params", "--apply"])
    assert "[subspanrepetition/control] Tab not found — skipping" in out


# ---------------------------------------------------------------------------
# The dry run writes nothing
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    before = env.all_tab_values()

    env.run(["sync-params"])

    assert env.doorway.mutations == []
    assert env.all_tab_values() == before


# coded_data_clean_tree is enforced centrally at the python -m coding
# dispatch chokepoint now, not inside sp.main() itself -- see
# coding/preconditions.py and tests/test_preconditions.py, which cover this
# command's gating directly
# against the real operations.yaml record.


def _drop_from_yaml(env, lang, class_name, criterion):
    """Make a sheet column surplus by dropping its criterion from the YAML.
    (Tests used to lean on drift that happened to be in the frozen data;
    the live sheets have since been fixed, so they set up their own.)"""
    env.edit_yaml(lang, lambda d: d["classes"][class_name]["criteria"].pop(criterion))


def test_apply_with_a_real_change_removes_the_column_and_writes_no_manifest(env):
    _drop_from_yaml(env, "synth0001", "noninterruption", "multiple")
    env.run(["sync-params", "--apply", "--remove"])
    assert env.doorway.mutations_of("update_file") == []


# ---------------------------------------------------------------------------
# --remove is exact: it only ever removes what is genuinely surplus
# ---------------------------------------------------------------------------

def test_remove_deletes_only_the_columns_absent_from_diagnostics(env):
    """The real synth0001 drift: each pair tab keeps its own criterion."""
    env.run(["sync-params", "--apply", "--remove"])

    header = env.tab("synth0001", "coreference", "reflexive_coreference").row_values(1)
    assert "reflexive_allowed" in header
    assert "pronoun_allowed" not in header
    assert "np_allowed" not in header


def test_remove_never_touches_a_column_still_expected(env):
    env.run(["sync-params", "--apply", "--remove"])

    header = env.tab("arao1248", "ciscategorial", "general").row_values(1)
    assert {"V-combines", "N-combines", "A-combines", "PRED-combines"} <= set(header)


def test_split_stale_column_survives_a_later_remove(env):
    """_split_-prefixed columns are preserved on purpose until remapped by hand."""
    env.run(["sync-params", "--apply", "--split", "free:free_left:free_right"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply", "--remove"])

    header = env.tab("arao1248", "noninterruption", "general").row_values(1)
    assert "_split_free" in header


def test_merge_stale_columns_survive_a_later_remove(env):
    """_merged_-prefixed columns are preserved the same way as _split_ ones."""
    env.run(["sync-params", "--apply", "--merge",
            "widescope_right:widescope_left:widescope_either"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply", "--remove"])

    header = env.tab("arao1248", "subspanrepetition", "auxiliary_construction").row_values(1)
    assert "_merged_widescope_right" in header
    assert "_merged_widescope_left" in header


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------

def test_a_second_identical_apply_is_a_no_op(env):
    env.run(["sync-params", "--apply"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply"])

    assert env.doorway.mutations == []


def test_an_unchanged_apply_reads_each_spreadsheet_three_times(env, monkeypatch):
    """The daily run: one open, one tab list and one batch of header rows per
    spreadsheet, however many tabs it has. Reading tab by tab (a lookup and a
    header each) brought the 2026-10-20 refresh within one retry of Google's
    per-minute read limit."""
    import fake_drive as fd
    reads: Dict[str, int] = {}

    def counted(cls, name):
        real = getattr(cls, name)

        def wrapper(self, *a, **kw):
            reads[name] = reads.get(name, 0) + 1
            return real(self, *a, **kw)
        monkeypatch.setattr(cls, name, wrapper)

    counted(fd.FakeDriveDoorway, "open_spreadsheet")
    for name in ("worksheets", "worksheet", "values_batch_get"):
        counted(fd.FakeSpreadsheet, name)
    for name in ("row_values", "get_all_values"):
        counted(fd.FakeWorksheet, name)

    env.run(["sync-params", "--apply"])

    sheets = reads["open_spreadsheet"]
    assert sheets > 0
    assert reads == {"open_spreadsheet": sheets, "worksheets": sheets,
                     "values_batch_get": sheets}


def test_a_second_identical_remove_is_a_no_op(env):
    env.run(["sync-params", "--apply", "--remove"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply", "--remove"])

    assert env.doorway.mutations == []


# ---------------------------------------------------------------------------
# The manifest is not this command's
# ---------------------------------------------------------------------------

def test_manifest_is_never_written_even_when_something_changed(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params", "--apply"])
    assert env.doorway.mutations_of("update_file") == []


def test_manifest_is_never_touched_by_a_dry_run(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params"])
    assert env.doorway.mutations_of("update_file") == []


# ---------------------------------------------------------------------------
# rename/split/merge edit diagnostics_{lang_id}.yaml (#315)
# ---------------------------------------------------------------------------

def _changed_lines(before: str, after: str) -> List[str]:
    import difflib
    return [line for line in difflib.unified_diff(
        before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def test_rename_changes_only_the_renamed_criterion_in_the_yaml(env):
    before = env.yaml_path("stan1293").read_text(encoding="utf-8")
    env.run(["sync-params", "--apply", "--rename", "noninterruption:free:free_form"])
    after = env.yaml_path("stan1293").read_text(encoding="utf-8")

    assert _changed_lines(before, after) == [
        "-      free: [y, n]", "+      free_form: [y, n]"]


def test_split_and_merge_change_only_their_criteria_in_the_yaml(env):
    before = env.yaml_path("stan1293").read_text(encoding="utf-8")
    env.run(["sync-params", "--apply", "--split", "free:free_left:free_right"])
    env.run(["sync-params", "--apply", "--merge",
            "widescope_right:widescope_left:widescope_either"])
    after = env.yaml_path("stan1293").read_text(encoding="utf-8")

    changed = _changed_lines(before, after)
    assert sorted(changed) == sorted(
        ["-      free: [y, n]", "+      free_left: [y, n]", "+      free_right: [y, n]"] * 2
        + ["-      widescope_right: [y, n]", "-      widescope_left: [y, n]",
           "+      widescope_either: [y, n]"])
    assert "# Positions treated as always present" in after


def test_a_dry_run_does_not_rewrite_the_diagnostics_yaml(env):
    before = env.yaml_path("stan1293").read_text(encoding="utf-8")
    env.run(["sync-params", "--rename", "noninterruption:free:free_form"])
    assert env.yaml_path("stan1293").read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# Findings check — the recurring "manifest is authoritative for a tab's
# columns" mistake (#272, Finding 10). sync_params inserts and deletes
# criterion columns, so this is the densest test of the question.
# ---------------------------------------------------------------------------

def test_nothing_criterion_shaped_is_written_onto_source_or_comments(env):
    env.add_criterion("synth0001", "ciscategorial", "PLACE-combines")
    env.edit_yaml("synth0001", lambda d: d["classes"]["ciscategorial"]["criteria"]
                 .__setitem__("V-combines", ["y", "n", "maybe"]))

    env.run(["sync-params", "--apply"])

    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_remove(env):
    env.run(["sync-params", "--apply", "--remove"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_split_and_merge(env):
    env.run(["sync-params", "--apply", "--split", "free:free_left:free_right"])
    env.run(["sync-params", "--apply", "--merge",
            "widescope_right:widescope_left:widescope_either"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


# ---------------------------------------------------------------------------
# Notebook regeneration
# ---------------------------------------------------------------------------

def test_notebooks_regenerate_when_something_changed(env):
    """A surplus column counts as "something changed" — it is reported
    (`any_changes = True`) as soon as it is seen, even without --remove,
    because a WARNING is itself something the coordinator needs to know
    about. Notebooks regenerate accordingly.
    """
    _drop_from_yaml(env, "synth0001", "noninterruption", "multiple")
    env.run(["sync-params", "--apply"])
    assert env.notebook_calls == [True]


def test_notebooks_do_not_regenerate_on_a_true_no_op_apply(env):
    """Once the drift is actually cleared, a second apply changes nothing."""
    env.run(["sync-params", "--apply", "--remove"])
    env.notebook_calls.clear()

    env.run(["sync-params", "--apply", "--remove"])

    assert env.notebook_calls == []


def test_notebooks_do_not_regenerate_on_a_dry_run(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params"])
    assert env.notebook_calls == []
