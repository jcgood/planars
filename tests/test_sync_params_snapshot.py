"""Snapshot tests for `python -m coding sync-params`, run against the fake.

File 16 of 18 migrated to the Drive doorway (#271). `sync_params` is the file
the migration order flagged as the one to watch: it inserts and deletes
criterion columns, which is the densest form of the question behind #272 and
Finding 10 — whether a command derives a tab's criterion columns from the
tab's own header (correct) or from the manifest's `construction_params`
(wrong, because the manifest is bookkeeping and goes stale). Read closely for
this migration, `_get_current_params`, `_insert_param_columns`, and
`_build_dropdown_refresh_requests` all already derive columns from the tab's
own header — `ws.row_values(1)` — never from the manifest. The manifest is
only ever a *record* of what was last pushed, read back to decide whether a
dropdown refresh is stale. `assert_no_criterion_writes_onto_trailing_columns`
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
`--refresh-dropdowns` code paths (the "no structural change" branch and the
branch that runs right after new columns are inserted in the same run); a
class present in the manifest but absent from the diagnostics YAML; and a
plain apply/dry-run baseline confirming the manifest is only rewritten when
something actually changed. stdout, the mutation log, and the rewritten
`diagnostics_{lang_id}.tsv`/`.yaml` files in `coded_data/` all came back
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
from coding import drive_doorway
from coding import generate_notebooks as gn
from coding import generate_sheets as gs
from coding import sync_params as sp
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
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
                 clean_checks: List[dict], saved_configs: List[dict],
                 notebook_calls: List[bool], run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.clean_checks = clean_checks
        self.saved_configs = saved_configs
        self.notebook_calls = notebook_calls
        self.run = run

    # -- the manifest ---------------------------------------------------
    def manifest(self) -> Dict:
        return self.doorway.download_file_json(MANIFEST_FILE_ID)

    def sheet_id(self, lang: str, class_name: str) -> str:
        return self.manifest()[lang]["sheets"][class_name]["spreadsheet_id"]

    def tab(self, lang: str, class_name: str, construction: str):
        return self.doorway.spreadsheet(
            self.sheet_id(lang, class_name)).worksheet(construction)

    # -- the local diagnostics YAML/TSV ----------------------------------
    def yaml_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml"

    def tsv_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.tsv"

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

    def widen_construction_criterion(self, lang: str, class_name: str,
                                     construction: str, criterion: str,
                                     values: List[str]) -> None:
        """Change one construction's allowed values via construction_criteria."""
        def edit(d):
            d["classes"][class_name]["construction_criteria"][construction][criterion] = list(values)
        self.edit_yaml(lang, edit)

    # -- reading the stand-in Drive back ----------------------------------
    def all_tab_values(self) -> Dict:
        return {
            (ss_id, ws.title): ws.get_all_values()
            for ss_id, ss in self.doorway._spreadsheets.items()
            for ws in ss.worksheets()
        }


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(ROOT / "coded_data" / lang / "lang_setup",
                        coded / lang / "lang_setup")

    clean_checks: List[dict] = []
    saved_configs: List[dict] = []
    notebook_calls: List[bool] = []

    monkeypatch.setattr(sp, "CODED_DATA", coded)
    monkeypatch.setattr(gs, "CODED_DATA", coded)
    monkeypatch.setattr(sp, "_check_coded_data_clean",
                        lambda **kw: clean_checks.append(kw))
    monkeypatch.setattr(sp, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    monkeypatch.setattr(sp, "_save_drive_config",
                        lambda cfg: saved_configs.append(cfg))
    monkeypatch.setattr(gn, "regenerate_notebooks",
                        lambda: notebook_calls.append(True))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                sp.main()
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, clean_checks, saved_configs, notebook_calls, run)
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


def test_refresh_dropdowns_dry_run_no_change_transcript(env):
    check_snapshot(
        "refresh_dropdowns_dry_run.txt",
        env.run(["sync-params", "--refresh-dropdowns"]))


def test_refresh_dropdowns_apply_no_structural_change_transcript(env):
    """One of the two nearly-identical dropdown-refresh blocks in main().

    This one lives inside the "sheet columns already match diagnostics"
    branch — no new_params, no removed_params, just a widened value list on
    an existing column.
    """
    env.widen_construction_criterion(
        "stan1293", "phrasal_accent", "prescreening", "accented",
        ["y", "n", "both", "maybe"])
    check_snapshot(
        "refresh_dropdowns_apply_no_structural_change.txt",
        env.run(["sync-params", "--apply", "--refresh-dropdowns"]))


def test_refresh_dropdowns_apply_with_new_params_transcript(env):
    """The second dropdown-refresh block: fires right after new columns land.

    A new criterion (new_params non-empty) alongside a widened value on an
    existing criterion of the same construction, in the same run.
    """
    env.add_criterion("synth0001", "ciscategorial", "PLACE-combines")
    env.edit_yaml("synth0001", lambda d: d["classes"]["ciscategorial"]["criteria"]
                 .__setitem__("V-combines", ["y", "n", "maybe"]))
    check_snapshot(
        "refresh_dropdowns_apply_with_new_params.txt",
        env.run(["sync-params", "--apply", "--refresh-dropdowns"]))


def test_a_class_not_in_diagnostics_is_named(env):
    env.edit_yaml("stan1293", lambda d: d["classes"].pop("proform"))
    out = env.run(["sync-params"])
    assert "[proform] Not in diagnostics_stan1293.tsv — skipping" in out


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


def test_the_dry_run_does_not_ask_whether_coded_data_is_clean(env):
    env.run(["sync-params"])
    assert env.clean_checks == []


def test_apply_refuses_to_read_a_half_written_diagnostics_tsv(env):
    env.run(["sync-params", "--apply"])
    assert env.clean_checks == [{"extensions": (".tsv",)}]


def test_apply_with_a_real_change_saves_drive_config(env):
    env.run(["sync-params", "--apply", "--remove"])
    # drive_config.json is only ever saved when the manifest was uploaded.
    assert env.saved_configs, "expected the baseline drift's --remove to change the manifest"
    for cfg in env.saved_configs:
        assert cfg.get("_planars_config_file_id") == MANIFEST_FILE_ID


def test_a_dry_run_never_saves_drive_config(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params"])
    assert env.saved_configs == []


# ---------------------------------------------------------------------------
# --remove is exact: it only ever removes what is genuinely surplus
# ---------------------------------------------------------------------------

def test_remove_deletes_only_the_columns_absent_from_diagnostics(env):
    """The real synth0001 drift: each pair tab keeps its own criterion."""
    env.run(["sync-params", "--apply", "--remove"])

    header = env.tab("synth0001", "coreference", "reflexivization").row_values(1)
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


def test_a_second_identical_refresh_dropdowns_apply_is_a_no_op(env):
    env.widen_construction_criterion(
        "stan1293", "phrasal_accent", "prescreening", "accented",
        ["y", "n", "both", "maybe"])
    env.run(["sync-params", "--apply", "--refresh-dropdowns"])
    env.doorway.clear_mutations()

    out = env.run(["sync-params", "--apply", "--refresh-dropdowns"])

    assert env.doorway.mutations == []
    assert "up to date" in out


def test_a_second_identical_remove_is_a_no_op(env):
    env.run(["sync-params", "--apply", "--remove"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply", "--remove"])

    assert env.doorway.mutations == []


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def test_manifest_upload_fires_when_something_changed(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params", "--apply"])
    assert [m["file_id"] for m in env.doorway.mutations_of("update_file")] \
        == [MANIFEST_FILE_ID]


def test_manifest_upload_is_absent_on_a_true_no_op_apply(env):
    """A second apply with nothing left to do touches the manifest not at all."""
    env.run(["sync-params", "--apply"])
    env.doorway.clear_mutations()

    env.run(["sync-params", "--apply"])

    assert env.doorway.mutations_of("update_file") == []


def test_manifest_is_never_touched_by_a_dry_run(env):
    env.add_criterion("arao1248", "ciscategorial", "PLACE-combines")
    env.run(["sync-params"])
    assert env.doorway.mutations_of("update_file") == []


# ---------------------------------------------------------------------------
# diagnostics_{lang_id}.tsv / .yaml are rewritten by rename/split/merge
# ---------------------------------------------------------------------------

def test_rename_rewrites_the_diagnostics_tsv_and_yaml(env):
    env.run(["sync-params", "--apply", "--rename", "noninterruption:free:free_form"])

    tsv_text = env.tsv_path("stan1293").read_text(encoding="utf-8")
    assert "free_form" in tsv_text
    yaml_data = _yaml.safe_load(env.yaml_path("stan1293").read_text(encoding="utf-8"))
    assert "free_form" in yaml_data["classes"]["noninterruption"]["criteria"]
    assert "notes" in yaml_data["classes"]["metrical"], (
        "existing notes must be carried over into the regenerated YAML")


def test_a_dry_run_does_not_rewrite_the_diagnostics_tsv(env):
    before = env.tsv_path("stan1293").read_text(encoding="utf-8")
    env.run(["sync-params", "--rename", "noninterruption:free:free_form"])
    assert env.tsv_path("stan1293").read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# Findings check — the recurring "manifest is authoritative for a tab's
# columns" mistake (#272, Finding 10). sync_params inserts and deletes
# criterion columns, so this is the densest test of the question.
# ---------------------------------------------------------------------------

def test_nothing_criterion_shaped_is_written_onto_source_or_comments(env):
    env.add_criterion("synth0001", "ciscategorial", "PLACE-combines")
    env.edit_yaml("synth0001", lambda d: d["classes"]["ciscategorial"]["criteria"]
                 .__setitem__("V-combines", ["y", "n", "maybe"]))

    env.run(["sync-params", "--apply", "--refresh-dropdowns"])

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
    """The real synth0001 coreference drift counts as "something changed" —
    surplus columns are reported (`any_changes = True`) as soon as they are
    seen, even without --remove, because a WARNING is itself something the
    coordinator needs to know about. Notebooks regenerate accordingly.
    """
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
