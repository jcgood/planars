"""Snapshot tests for `python -m coding generate-sheets`, run against the fake.

File 17 of 18 migrated to the Drive doorway (#271) — the largest file migrated
so far (2,654 lines pre-migration) and the first whose migration is not a
plain call-site substitution in `main()`/one leaf helper: `gc`/`drive` were
threaded as explicit parameters through a chain of this file's own functions
(`_create_or_update_tsv_sheet`, `_upload_lang_setup_as_sheets`,
`_create_analysis_sheet`, `_regen_construction`, `_regen_dependents_simple`),
so the migration replaces two parameters with one (`doorway`) at every level
of that chain, not just at the entry point.

Before migrating, the old code was driven from a stand-in Drive through thin
`gc`/`drive` shims patched into `coding.generate_sheets`'s own namespace (the
lesson from files 5/15/16 — patching `coding.drive`'s copy of a name is not
enough for a module that imported it by name), across twelve scenarios: a dry
run and a true no-op `--apply` over the real fixture data (all three languages
already have every class); a brand-new language (`arao1248` with its manifest
entry removed — real annotation data untouched, since the fixture is a private
copy) both dry-run and `--apply`, the full creation path — folder, notes doc,
planar/diagnostics sheets, one sheet per class, Status tabs; a new class added
to an existing language's diagnostics YAML; a new construction added to an
existing class; `--force` refused when annotation sheets already exist;
`--regen-construction` for a `nonpermutability` pair construction and a
`coreference` one with `--pos-remap`; `--regen-dependents` both skipping (the
real fixture data has no missing dependent TSVs) and regenerating (one deleted
to force it); and `--push-manifest`. stdout and the mutation log came back
byte-identical between the unmigrated and migrated code for all twelve —
diffed as full files, not sampled.

`_find_annotated_drops`/`_format_annotated_drop` (the --regen-construction
annotated-drop abort) and `_regen_dependents_simple`'s skip/regenerate logic
already had dedicated non-Drive tests in `test_generate_sheets.py` before this
migration and needed no changes beyond the `gc`-shaped mock in
`TestCreateAnalysisSheetDriveNameGuard` becoming a doorway stub (mirroring
`test_import_sheets.py`'s `_DoorwayStub` precedent) — everything else in that
file is pure logic, unaffected by which Drive interface the surrounding
functions take.

`CODED_DATA` and `ROOT` are both redirected into a private tmp tree per test
(this file writes `manifest_backup.json`/`sheets_manifest.json` relative to
`ROOT`, which must never land in the real repo) — `schemas/` is symlinked in
so `_sync_language_metadata`'s direct-by-path read of `languages.yaml` still
resolves the three real, already-onboarded fixture languages rather than
spuriously warning that they're unknown.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_generate_sheets_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import yaml as _yaml
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import generate_notebooks as gn
from coding import generate_sheets as gs
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID, ROOT_FOLDER_ID
from mutation_checks import assert_no_criterion_writes_onto_trailing_columns
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "generate_sheets"
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

    def __init__(self, doorway: FakeDriveDoorway, coded: Path, tmp_root: Path,
                 saved_configs: List[dict],
                 notebook_calls: List[bool], run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.tmp_root = tmp_root
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

    # -- the local diagnostics YAML ----------------------------------
    def yaml_path(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml"

    def edit_yaml(self, lang: str, fn) -> None:
        data = _yaml.safe_load(self.yaml_path(lang).read_text(encoding="utf-8"))
        fn(data)
        self.yaml_path(lang).write_text(
            _yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def remove_from_manifest(self, lang: str) -> None:
        """Simulate a brand-new language: strip its manifest entry.

        Its spreadsheets stay seeded in the fake -- only the manifest forgets
        about them, exactly like arao1248 in the pre-migration baseline.
        """
        manifest = self.manifest()
        manifest.pop(lang, None)
        f = self.doorway.file(MANIFEST_FILE_ID)
        f.content = json.dumps(manifest).encode("utf-8")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures(langs=LANGS)

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(ROOT / "coded_data" / lang, coded / lang)

    # _sync_language_metadata reads ROOT/schemas/languages.yaml directly by
    # path, and gs.ROOT is redirected below so manifest_backup.json and
    # sheets_manifest.json never touch the real repo -- symlink schemas/ in so
    # that read still resolves the three real, already-onboarded languages.
    (tmp_path / "schemas").symlink_to(ROOT / "schemas")

    saved_configs: List[dict] = []
    notebook_calls: List[bool] = []

    monkeypatch.setattr(gs, "CODED_DATA", coded)
    monkeypatch.setattr(gs, "ROOT", tmp_path)
    monkeypatch.setattr(gs, "MANIFEST_PATH", tmp_path / "sheets_manifest.json")
    monkeypatch.setattr(gs, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    monkeypatch.setattr(gs, "_save_drive_config",
                        lambda cfg: saved_configs.append(cfg))
    monkeypatch.setattr(gn, "regenerate_notebooks",
                        lambda: notebook_calls.append(True))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                gs.main()
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, tmp_path, saved_configs, notebook_calls, run)
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
    """Real fixture data as committed: stan1293 and synth0001 already have every
    class; arao1248 is still missing sheets for two required classes it gained
    after onboarding (nonpermutability, free_occurrence -- #271 Finding 19).
    """
    check_snapshot("dry_run_baseline.txt", env.run(["generate-sheets"]))


def test_apply_noop_baseline_transcript(env):
    """stan1293 and synth0001 are a true no-op; arao1248 creates sheets for its
    two still-missing required classes (see test_dry_run_baseline_transcript).
    The apply still re-uploads the merged manifest once at the end regardless
    (unlike sync-params, generate-sheets has no "anything changed" gate on that
    final upload) -- so one update_file mutation here is real, existing
    behaviour, not a sign anything else was recreated.
    """
    out = env.run(["generate-sheets", "--apply"])
    check_snapshot("apply_noop_baseline.txt", out)
    created = env.doorway.mutations_of("create_spreadsheet")
    assert sorted(m["title"] for m in created) == [
        "free_occurrence_arao1248", "nonpermutability_arao1248",
    ]
    moved = env.doorway.mutations_of("move_file")
    assert {m["file_id"] for m in moved} == {m["spreadsheet"] for m in created}


def test_brand_new_language_dry_run_transcript(env):
    env.remove_from_manifest("arao1248")
    check_snapshot("brand_new_dry_run.txt", env.run(["generate-sheets"]))
    assert env.doorway.mutations == [], "a dry run must perform no Drive mutations at all"


def test_brand_new_language_apply_transcript(env):
    env.remove_from_manifest("arao1248")
    check_snapshot("brand_new_apply.txt", env.run(["generate-sheets", "--apply"]))


def test_brand_new_language_apply_digest(env):
    """The rendered write log for the highest-stakes write path this file has:
    a whole new folder, notes doc, planar/diagnostics sheet, and one sheet per
    class created in a single run. Reviewed here, not as raw JSON — see
    update_sheets' precedent (docs/data-layer-progress.md Findings 9-11).
    """
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    check_snapshot("brand_new_apply_digest.txt", render(env.doorway.mutations))


def test_new_class_on_existing_language_transcript(env):
    """arao1248 gains a 'metrical' class it didn't have before; its three
    existing class sheets are untouched.
    """
    env.edit_yaml("arao1248", lambda d: d["classes"].__setitem__("metrical", {
        "constructions": ["stress_domain"],
        "criteria": {"accented": ["y", "n", "both"], "obligatory": ["y", "n"]},
    }))
    out = env.run(["generate-sheets", "--apply"])
    check_snapshot("new_class_apply.txt", out)
    assert "metrical_arao1248" in out


def test_new_construction_on_existing_class_transcript(env):
    """arao1248's subspanrepetition class gains a third construction tab via
    _add_constructions_to_existing_sheet, not _create_analysis_sheet.
    """
    env.edit_yaml("arao1248", lambda d: d["classes"]["subspanrepetition"]
                 .__setitem__("constructions",
                             d["classes"]["subspanrepetition"]["constructions"]
                             + ["extra_construction_test"]))
    out = env.run(["generate-sheets", "--apply"])
    check_snapshot("new_construction_apply.txt", out)
    assert "extra_construction_test" in out


def test_force_refused_when_sheets_exist_transcript(env):
    out = env.run(["generate-sheets", "--apply", "--force"])
    check_snapshot("force_refused.txt", out)
    assert "[SystemExit: 1]" in out


def test_regen_nonpermutability_transcript(env):
    out = env.run(["generate-sheets", "--lang", "synth0001",
                  "--regen-construction", "nonpermutability:general"])
    check_snapshot("regen_nonperm.txt", out)


def test_regen_coreference_with_pos_remap_transcript(env):
    out = env.run(["generate-sheets", "--lang", "synth0001",
                  "--regen-construction", "coreference:reflexivization",
                  "--pos-remap", "5:6", "--confirm-drop"])
    check_snapshot("regen_coref_remap.txt", out)


def test_regen_dependents_noop_transcript(env):
    """The real fixture data has no missing dependent TSV -- nothing to do."""
    out = env.run(["generate-sheets", "--regen-dependents"])
    check_snapshot("regen_dependents_noop.txt", out)
    assert env.doorway.mutations == []


def test_regen_dependents_fires_when_dependent_tsv_absent(env):
    dep_path = env.coded / "synth0001" / "nonpermutability" / "general.tsv"
    dep_path.unlink()
    out = env.run(["generate-sheets", "--regen-dependents"])
    check_snapshot("regen_dependents_fire.txt", out)


def test_push_manifest_transcript(env):
    manifest = env.manifest()
    gs.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    out = env.run(["generate-sheets", "--push-manifest"])
    check_snapshot("push_manifest.txt", out)


# ---------------------------------------------------------------------------
# A dry run writes nothing, ever
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    env.run(["generate-sheets"])
    assert env.doorway.mutations == []
    assert env.saved_configs == []


# coded_data_clean_tree (--regen-dependents only, not the base command) is
# enforced centrally at the python -m coding dispatch chokepoint now, not
# inside gs.main() itself -- see coding/preconditions.py and
# tests/test_preconditions.py, which cover this command's gating (including
# --regen-construction, which needs no precondition) directly against the
# real operations.yaml record.


# ---------------------------------------------------------------------------
# --force genuinely refuses
# ---------------------------------------------------------------------------

def test_force_refuses_before_destroying_any_annotation_sheet(env):
    """Finding 15, fixed: --force used to overwrite arao1248's
    planar/diagnostics *reference* sheets before the guard could abort on
    arao1248's existing *annotation* sheets -- a preflight pass now checks
    --force against every language before any of them is touched, so nothing
    is written at all, not even the reference sheets, when any language
    already has annotation sheets. All three fixture languages already have
    annotation sheets, so this fires on arao1248 (alphabetically first)
    during the preflight pass, before the per-language loop -- and therefore
    before the per-language loop -- ever starts.
    """
    ciscategorial_id = env.sheet_id("arao1248", "ciscategorial")
    before = env.tab("arao1248", "ciscategorial", "general").get_all_values()
    planar_id = env.manifest()["arao1248"]["planar_spreadsheet_id"]
    diagnostics_id = env.manifest()["arao1248"]["diagnostics_spreadsheet_id"]
    before_planar = env.doorway.spreadsheet(planar_id).sheet1.get_all_values()
    before_diagnostics = env.doorway.spreadsheet(diagnostics_id).sheet1.get_all_values()

    out = env.run(["generate-sheets", "--apply", "--force"])

    assert "[SystemExit: 1]" in out
    # Not one Drive mutation happened anywhere -- the guard fired before any
    # language, including arao1248 itself, was touched.
    assert env.doorway.mutations == []
    after_ss = env.doorway.spreadsheet(ciscategorial_id)
    assert after_ss.worksheet("general").get_all_values() == before
    assert env.doorway.spreadsheet(planar_id).sheet1.get_all_values() == before_planar
    assert env.doorway.spreadsheet(diagnostics_id).sheet1.get_all_values() == before_diagnostics


def test_force_refuses_for_a_later_language_before_an_earlier_one_is_touched(env):
    """Finding 15, fixed: the preflight pass checks *every* language before
    any of them is touched, not just the language order the old, per-language
    check happened to run in. arao1248 and stan1293 are made brand new (no
    force conflict at all -- a real --force run against them would freely
    create their sheets), while synth0001 -- last alphabetically, so last in
    the old per-language loop -- keeps its real existing annotation sheets
    and so fails the guard. The old code would have fully created arao1248's
    and stan1293's sheets before ever reaching synth0001's abort; the fixed
    code aborts during the preflight pass, before arao1248 or stan1293 is
    touched at all.
    """
    env.remove_from_manifest("arao1248")
    env.remove_from_manifest("stan1293")

    out = env.run(["generate-sheets", "--apply", "--force"])

    assert "[SystemExit: 1]" in out
    assert "synth0001" in out
    assert env.doorway.mutations == []


def test_force_succeeds_as_before_when_no_language_fails_the_guard(env):
    """No behaviour change on the passing path: with every language brand
    new (no existing annotation sheets anywhere), --force --apply still
    creates every language's sheets exactly as a plain --apply would.

    Not asserting "ERROR" not in out overall: arao1248's
    diagnostics_arao1248.yaml is genuinely missing three collection_required:
    "y" classes (Finding 19), which surfaces as an informational validation
    line on every generate-sheets run for this language without blocking
    sheet creation (unlike import-sheets/sync-diagnostics-yaml, which skip
    processing outright). The guard this test actually checks is the
    --force-vs-existing-sheets one.
    """
    for lang in LANGS:
        env.remove_from_manifest(lang)

    out = env.run(["generate-sheets", "--apply", "--force"])

    assert "ERROR: --force refused" not in out
    assert "[SystemExit" not in out
    for lang in LANGS:
        assert lang in env.manifest()
    create_titles = [m["title"] for m in env.doorway.mutations_of("create_spreadsheet")]
    for lang in LANGS:
        assert f"planar_{lang}" in create_titles


# ---------------------------------------------------------------------------
# The orphan-sheet Drive-name guard aborts before create_spreadsheet
# ---------------------------------------------------------------------------

def test_orphan_sheet_guard_aborts_before_create(env):
    """A same-named spreadsheet already sitting in the language's Drive folder
    but absent from the manifest must stop the run before a second one gets
    created alongside it.
    """
    env.remove_from_manifest("arao1248")
    # arao1248's folder was already seeded (from the manifest entry before it
    # was stripped above) -- get_or_create_folder finds it by name, the same
    # resolution main() itself performs when existing_lang_data has no
    # folder_id of its own.
    lang_folder = env.doorway.get_or_create_folder("arao1248", parent_id=ROOT_FOLDER_ID)
    env.doorway.seed_file(
        "ciscategorial_arao1248",
        "application/vnd.google-apps.spreadsheet",
        [lang_folder],
    )
    env.doorway.clear_mutations()

    out = env.run(["generate-sheets", "--apply"])

    assert "already exists in the Drive" in out
    assert "[SystemExit" in out
    create_titles = [m["title"] for m in env.doorway.mutations_of("create_spreadsheet")]
    assert "ciscategorial_arao1248" not in create_titles


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------

def test_a_second_identical_apply_after_creation_is_a_noop_for_that_language(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    env.doorway.clear_mutations()

    out = env.run(["generate-sheets", "--apply"])

    assert "All classes already have sheets. Skipping arao1248." in out
    assert env.doorway.mutations_of("create_spreadsheet") == []
    assert env.doorway.mutations_of("add_worksheet") == []


def test_regen_dependents_stops_firing_once_the_dependent_tsv_is_imported(env):
    """_regen_dependents_simple's guard is "does the dependent TSV exist
    locally", not "did we already regenerate it this run" -- this command
    never writes coded_data/ itself (import-sheets does), so a bare second
    call with nothing else changed regenerates again, live, every time. The
    actual no-repeat promise is: once import-sheets has brought the tab down
    (dep_path exists, even with no annotated values), a later run leaves it
    alone. Simulate that hand-off rather than re-calling with nothing changed.
    """
    dep_path = env.coded / "synth0001" / "nonpermutability" / "general.tsv"
    dep_path.unlink()
    env.run(["generate-sheets", "--regen-dependents"])
    env.doorway.clear_mutations()

    dep_path.write_text("Element_A\tElement_B\tscopal\tSource\tComments\n", encoding="utf-8")
    out = env.run(["generate-sheets", "--regen-dependents"])

    assert env.doorway.mutations == []
    assert "already exists — skipping auto-regeneration" in out


# ---------------------------------------------------------------------------
# Findings check — the recurring "manifest is authoritative for a tab's
# columns" mistake (#272, Finding 10). generate_sheets builds construction_params
# and per-column dropdowns directly from the diagnostics YAML in several
# places (_create_analysis_sheet, _add_constructions_to_existing_sheet,
# _regen_construction), so this is exactly the shape of command the note in
# docs/data-layer-progress.md's "Next action" flagged to check.
# ---------------------------------------------------------------------------

def test_nothing_criterion_shaped_is_written_onto_source_or_comments_on_creation(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_new_class(env):
    env.edit_yaml("arao1248", lambda d: d["classes"].__setitem__("metrical", {
        "constructions": ["stress_domain"],
        "criteria": {"accented": ["y", "n", "both"], "obligatory": ["y", "n"]},
    }))
    env.run(["generate-sheets", "--apply"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_new_construction(env):
    env.edit_yaml("arao1248", lambda d: d["classes"]["subspanrepetition"]
                 .__setitem__("constructions",
                             d["classes"]["subspanrepetition"]["constructions"]
                             + ["extra_construction_test"]))
    env.run(["generate-sheets", "--apply"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


def test_nothing_criterion_shaped_is_written_onto_trailing_columns_on_regen(env):
    env.run(["generate-sheets", "--lang", "synth0001",
            "--regen-construction", "nonpermutability:general"])
    env.run(["generate-sheets", "--lang", "synth0001",
            "--regen-construction", "coreference:reflexivization",
            "--confirm-drop"])
    assert_no_criterion_writes_onto_trailing_columns(env.doorway)


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def test_manifest_upload_fires_on_creation(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    updates = [m["file_id"] for m in env.doorway.mutations_of("update_file")]
    assert MANIFEST_FILE_ID in updates


def test_manifest_is_never_touched_by_a_dry_run(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets"])
    assert env.doorway.mutations_of("update_file") == []


def test_drive_config_is_saved_on_apply(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    assert env.saved_configs, "drive_config.json should be written after a real apply"


# ---------------------------------------------------------------------------
# Notebook regeneration
# ---------------------------------------------------------------------------

def test_notebooks_regenerate_after_a_real_apply(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets", "--apply"])
    assert env.notebook_calls == [True]


def test_notebooks_do_not_regenerate_on_a_dry_run(env):
    env.remove_from_manifest("arao1248")
    env.run(["generate-sheets"])
    assert env.notebook_calls == []


def test_notebooks_do_not_regenerate_on_regen_construction(env):
    """--regen-construction and --regen-dependents return early, before
    main()'s own regenerate_notebooks() call at the very end -- confirmed
    behaviour, not merely assumed from reading the early `return`.
    """
    env.run(["generate-sheets", "--lang", "synth0001",
            "--regen-construction", "nonpermutability:general"])
    assert env.notebook_calls == []
