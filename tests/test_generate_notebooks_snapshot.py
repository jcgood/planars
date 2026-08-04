"""Snapshot tests for `python -m coding generate-notebooks`, run against the fake.

File 10 of 18 migrated to the Drive doorway (plan Phase 0b/1). Like
`generate_reports.py`, this command never touches gspread — its whole Drive
footprint is "upload a file, create or update in place, then share it" — so
what these snapshots lock is the Drive interaction: how many files, into which
folders, under what names, with what permissions, and what ends up in
drive_config.json.

**The notebook templates are stubbed.** The real ones are large and are edited
independently of this command, so leaving them in would make every template
edit show up here as a changed byte count — noise in the one artifact that is
supposed to say what the command did to Drive. Token substitution and per-class
cell insertion are still exercised, against small stand-in templates, because
that is this command's own logic. `test_the_real_templates_load_and_carry_their
_markers` covers what stubbing gives up.

**drive_config.json is never written by these tests.** The real one holds live
Drive IDs; `_save_drive_config` is patched to capture into a dict instead.

Pre-migration baseline: the unmigrated code was driven from the same fake
through a Drive-service shim across seven scenarios (dry run, create, update,
a language with no folder, both missing-config stops, and `regenerate_notebooks`).
Stdout, mutation logs, and the saved config were byte-identical before and after.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_generate_notebooks_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway, generate_notebooks
from coding.make_forms import _read_diagnostics_for_language
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "generate_notebooks"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)

# Stand-in templates: one cell per token the real template bakes in, plus the
# marker cell the coordinator and contributor notebooks expand into per-class
# sections. Small enough that the uploaded byte counts stay readable.
_STUB_TEMPLATES = {
    "domains_boilerplate.ipynb": {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# {{LANG_DISPLAY}}"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["LANG_ID = '{{LANG_ID}}'\n", "CONFIG = '{{CONFIG_FILE_ID}}'"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["# __CLASS_CELLS_MARKER__\n"]},
        ],
    },
    "validation_boilerplate.ipynb": {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# validation {{LANG_DISPLAY}}"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["LANG_ID = '{{LANG_ID}}'\n", "CONFIG = '{{CONFIG_FILE_ID}}'"]},
        ],
    },
    "report_boilerplate.ipynb": {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# report {{LANG_DISPLAY}}"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["LANG_ID = '{{LANG_ID}}'\n", "CONFIG = '{{CONFIG_FILE_ID}}'\n",
                        "FOLDER = '{{FOLDER_ID}}'"]},
        ],
    },
    "all_languages_boilerplate.ipynb": {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# all languages"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["CONFIG = '{{CONFIG_FILE_ID}}'"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["# __CLASS_CELLS_MARKER__\n"]},
        ],
    },
}


@pytest.fixture()
def env(monkeypatch):
    """Fake doorway, stand-in templates, and a captured drive_config."""
    doorway = FakeDriveDoorway.from_fixtures()
    manifest = json.loads(doorway.file(MANIFEST_FILE_ID).content.decode())
    config = dict(FakeDriveDoorway.drive_config())
    for lang, entry in manifest.items():
        if isinstance(entry, dict) and entry.get("folder_id"):
            config[lang] = {"folder_id": entry["folder_id"]}
    saved: dict = {}

    monkeypatch.setattr(generate_notebooks, "_load_template",
                        lambda name: json.loads(json.dumps(_STUB_TEMPLATES[name])))
    monkeypatch.setattr(generate_notebooks, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(generate_notebooks, "_save_drive_config", saved.update)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, config, saved
    finally:
        drive_doorway.reset_doorway()


def run(argv, monkeypatch) -> str:
    monkeypatch.setattr("sys.argv", argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        generate_notebooks.main()
    return buf.getvalue()


def use_config(monkeypatch, config: dict) -> None:
    monkeypatch.setattr(generate_notebooks, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))


def declared_classes(lang_id: str) -> set:
    """The classes this language's diagnostics YAML declares."""
    specs = _read_diagnostics_for_language(
        lang_id, ROOT / "coded_data" / lang_id / "lang_setup")
    return {class_name for class_name, _, _, _ in specs}


def uploaded(doorway, name: str) -> dict:
    """The notebook JSON most recently written to Drive under ``name``."""
    for f in doorway._files.values():
        if f.name == name:
            return json.loads(f.content.decode())
    raise AssertionError(f"no Drive file named {name}")


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}"
    )
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff."
    )


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def test_dry_run_output(env, monkeypatch):
    check_snapshot("dry_run.txt", run(["generate-notebooks"], monkeypatch))


def test_dry_run_touches_neither_drive_nor_config(env, monkeypatch):
    doorway, _, saved = env
    run(["generate-notebooks"], monkeypatch)
    assert doorway.mutations == []
    assert saved == {}


def test_dry_run_never_authenticates(env, monkeypatch):
    """A dry run has nothing to ask Drive, so it must not reach for OAuth.

    Asserted with the fake removed, so any client construction fails loudly
    rather than popping a browser auth flow.
    """
    drive_doorway.reset_doorway()
    monkeypatch.setattr(drive_doorway, "_get_clients",
                        lambda: pytest.fail("dry run must not authenticate"))
    run(["generate-notebooks"], monkeypatch)


# ---------------------------------------------------------------------------
# Apply — create path
# ---------------------------------------------------------------------------

def test_apply_output(env, monkeypatch):
    check_snapshot("apply.txt", run(["generate-notebooks", "--apply"], monkeypatch))


def test_apply_mutation_digest(env, monkeypatch):
    doorway, _, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    check_snapshot("apply_digest.txt", render(doorway.mutations))


def test_apply_uploads_three_notebooks_per_language_and_one_coordinator_notebook(env, monkeypatch):
    doorway, config, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    langs = sorted(lang for lang in config if not lang.startswith("_"))

    creates = doorway.mutations_of("create_file")
    assert [c["name"] for c in creates] == (
        [f"domains_{lang}.ipynb" for lang in langs]
        + [f"validation_{lang}.ipynb" for lang in langs]
        + [f"report_{lang}.ipynb" for lang in langs]
        + ["all_languages.ipynb"]
    )
    for create in creates[:-1]:
        lang = create["name"].rsplit("_", 1)[1][: -len(".ipynb")]
        assert create["parents"] == [config[lang]["folder_id"]]
    # The coordinator notebook belongs to the project root, not to a language.
    assert creates[-1]["parents"] == [ROOT_FOLDER_ID]
    assert all(c["mimetype"] == "application/json" for c in creates)
    assert doorway.mutations_of("update_file") == []


def test_every_uploaded_notebook_is_shared_read_only_with_anyone(env, monkeypatch):
    """Collaborators open these from a link; a notebook nobody can read is dead."""
    doorway, _, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    uploads = [m["file_id"] for m in doorway.mutations_of("create_file")]
    perms = doorway.mutations_of("create_permission")
    assert [p["file_id"] for p in perms] == uploads
    assert all(p["type"] == "anyone" and p["role"] == "reader" for p in perms)


def test_apply_records_every_file_id_in_drive_config(env, monkeypatch):
    doorway, config, saved = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    created = {c["name"]: c["file_id"] for c in doorway.mutations_of("create_file")}
    for lang in (lang for lang in config if not lang.startswith("_")):
        assert saved[lang]["domains_notebook_file_id"] == created[f"domains_{lang}.ipynb"]
        assert saved[lang]["validation_notebook_file_id"] == created[f"validation_{lang}.ipynb"]
        assert saved[lang]["report_notebook_file_id"] == created[f"report_{lang}.ipynb"]
    assert saved["_all_languages_notebook_file_id"] == created["all_languages.ipynb"]


# ---------------------------------------------------------------------------
# What lands in the notebooks
# ---------------------------------------------------------------------------

def test_no_placeholder_survives_into_an_uploaded_notebook(env, monkeypatch):
    """An unsubstituted {{TOKEN}} is a notebook that fails on the first cell."""
    doorway, config, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    for f in doorway._files.values():
        if f.name.endswith(".ipynb"):
            assert "{{" not in f.content.decode(), f.name


def test_a_language_notebook_carries_that_language_s_classes_only(env, monkeypatch):
    doorway, config, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)

    for lang in (lang for lang in config if not lang.startswith("_")):
        nb = uploaded(doorway, f"domains_{lang}.ipynb")
        source = "".join("".join(cell["source"]) for cell in nb["cells"])
        assert f"LANG_ID = '{lang}'" in source

        imported = {line.split()[-1] for line in source.splitlines()
                    if line.startswith("from planars import ")}
        assert imported == declared_classes(lang)
        for class_name in imported:
            assert f"show_class_reports(gc, manifest, '{class_name}'" in source

    # The coordinator notebook carries the union, so it is a superset of each.
    coord = "".join("".join(c["source"]) for c in uploaded(doorway, "all_languages.ipynb")["cells"])
    for lang in (lang for lang in config if not lang.startswith("_")):
        nb = uploaded(doorway, f"domains_{lang}.ipynb")
        source = "".join("".join(cell["source"]) for cell in nb["cells"])
        for line in source.splitlines():
            if line.startswith("from planars import "):
                assert line in coord


def test_the_report_notebook_is_told_which_folder_to_write_its_html_into(env, monkeypatch):
    """FOLDER_ID is baked in only here — the report notebook uploads back to Drive."""
    doorway, config, _ = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    for lang in (lang for lang in config if not lang.startswith("_")):
        nb = uploaded(doorway, f"report_{lang}.ipynb")
        source = "".join("".join(cell["source"]) for cell in nb["cells"])
        assert f"FOLDER = '{config[lang]['folder_id']}'" in source


def test_the_real_templates_load_and_carry_their_markers(env):
    """What template-stubbing gives up: that the shipped templates are usable.

    A template that is not valid JSON, or a coordinator template that has lost
    its marker cell, would produce a notebook with no per-class sections at all
    — silently, since nothing else checks.
    """
    for name in _STUB_TEMPLATES:
        nb = generate_notebooks._load_template(name)
        assert nb["cells"], name
    for name in ("domains_boilerplate.ipynb", "all_languages_boilerplate.ipynb"):
        nb = generate_notebooks._load_template(name)
        sources = ["".join(c["source"]) if not isinstance(c["source"], str) else c["source"]
                   for c in nb["cells"]]
        assert any(s.strip() == generate_notebooks._CLASS_CELLS_MARKER.strip()
                   for s in sources), name


# ---------------------------------------------------------------------------
# Apply — update path
# ---------------------------------------------------------------------------

def test_a_second_run_updates_in_place_keeping_the_links_collaborators_hold(env, monkeypatch):
    doorway, config, saved = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    first = json.loads(json.dumps(saved))

    use_config(monkeypatch, first)
    doorway.clear_mutations()
    run(["generate-notebooks", "--apply"], monkeypatch)

    assert doorway.mutations_of("create_file") == []
    updated = {u["file_id"] for u in doorway.mutations_of("update_file")}
    expected = {first["_all_languages_notebook_file_id"]} | {
        first[lang][key]
        for lang in first if not lang.startswith("_")
        for key in ("domains_notebook_file_id", "validation_notebook_file_id",
                    "report_notebook_file_id")
    }
    assert updated == expected
    # The update path renames as well as replacing content.
    assert all(u["name"] for u in doorway.mutations_of("update_file"))


def test_a_second_run_does_not_duplicate_the_viewer_grant(env, monkeypatch):
    """Bonus discovery from issue #276: this was a real, silent bug.

    generate_notebooks.py reasserted its "anyone" grant on every run with no
    existence check, exactly the shape of bug setup_root_folder.py had for its
    root folder — just never named as a Finding because nothing had compared
    the two. Since notebooks regenerate after nearly every --apply across
    several commands, every one of those runs was quietly adding another
    duplicate grant. `ensure_anyone_permission` (coding/drive.py) fixes both
    files with the same check.
    """
    doorway, config, saved = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    use_config(monkeypatch, json.loads(json.dumps(saved)))
    doorway.clear_mutations()
    run(["generate-notebooks", "--apply"], monkeypatch)
    assert doorway.mutations_of("create_permission") == []


def test_a_manually_revoked_viewer_grant_is_restored_on_the_next_run(env, monkeypatch):
    """The property that must survive fixing the bug above: self-healing.

    A notebook whose sharing was removed by hand still gets it back on the
    next run — ensure_anyone_permission only skips the create when a grant
    already exists, so a genuinely missing one is still created.
    """
    doorway, config, saved = env
    run(["generate-notebooks", "--apply"], monkeypatch)
    file_id = saved["_all_languages_notebook_file_id"]
    perm = next(p for p in doorway.list_permissions(file_id) if p["type"] == "anyone")
    doorway.delete_permission(file_id, perm["id"])
    assert not any(p["type"] == "anyone" for p in doorway.list_permissions(file_id))

    use_config(monkeypatch, json.loads(json.dumps(saved)))
    doorway.clear_mutations()
    run(["generate-notebooks", "--apply"], monkeypatch)

    assert any(p["type"] == "anyone" and p["role"] == "reader"
               for p in doorway.list_permissions(file_id))
    created = [p for p in doorway.mutations_of("create_permission") if p["file_id"] == file_id]
    assert len(created) == 1


def test_regenerate_notebooks_always_applies(env, monkeypatch):
    """The entry point generate_sheets/sync_params/restructure_sheets call.

    It takes no apply flag — being called at all means the sheets have already
    changed, so the notebooks are already out of date.
    """
    doorway, _, saved = env
    monkeypatch.setattr("sys.argv", ["generate-sheets", "--apply"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        generate_notebooks.regenerate_notebooks()
    assert doorway.mutations_of("create_file")
    assert saved


# ---------------------------------------------------------------------------
# Missing configuration
# ---------------------------------------------------------------------------

def test_a_language_without_a_folder_id_is_named_and_skipped_not_fatal(env, monkeypatch):
    doorway, config, saved = env
    partial = json.loads(json.dumps(config))
    partial["arao1248"] = {}
    use_config(monkeypatch, partial)
    out = run(["generate-notebooks", "--apply"], monkeypatch)

    assert "No Drive folder recorded, so no notebooks: ['arao1248']" in out
    assert "python -m coding generate-sheets --apply" in out
    assert not any("arao1248" in c["name"] for c in doorway.mutations_of("create_file"))
    assert any("stan1293" in c["name"] for c in doorway.mutations_of("create_file"))


def test_dry_run_output_with_a_language_that_has_no_folder(env, monkeypatch):
    """Committed because every fixture language has a folder, so the ordinary
    dry-run snapshot cannot show what a skipped language looks like."""
    _, config, _ = env
    partial = json.loads(json.dumps(config))
    partial["arao1248"] = {}
    use_config(monkeypatch, partial)
    check_snapshot("dry_run_no_folder.txt", run(["generate-notebooks"], monkeypatch))


def test_the_dry_run_names_the_same_languages_the_apply_run_uploads_for(env, monkeypatch):
    """The dry run used to promise notebooks it would then not deliver.

    It listed three notebooks for every language, whether or not that language
    had a Drive folder to put them in; the omission only appeared once --apply
    had already run.
    """
    doorway, config, _ = env
    partial = json.loads(json.dumps(config))
    partial["arao1248"] = {}
    use_config(monkeypatch, partial)

    dry = run(["generate-notebooks"], monkeypatch)
    assert "domains_arao1248.ipynb" not in dry
    assert "domains_stan1293.ipynb" in dry

    run(["generate-notebooks", "--apply"], monkeypatch)
    assert set(re.findall(r"\w+\.ipynb", dry)) == {
        c["name"] for c in doorway.mutations_of("create_file")}


def test_no_manifest_file_id_recorded_stops_with_the_command_to_run(env, monkeypatch):
    doorway, config, _ = env
    without = json.loads(json.dumps(config))
    without.pop("_planars_config_file_id")
    use_config(monkeypatch, without)

    with pytest.raises(SystemExit) as excinfo:
        run(["generate-notebooks"], monkeypatch)
    assert "python -m coding generate-sheets --apply" in str(excinfo.value)
    assert doorway.mutations == []


def test_the_global_folder_falls_back_to_the_first_language_folder(env, monkeypatch):
    """Recorded, not endorsed: pre-`setup-root-folder` behaviour is still live.

    With no `_root_folder_id` and no `_global_folder_id`, the coordinator
    notebook lands in whichever language folder sorts first rather than at the
    project root.
    """
    doorway, config, _ = env
    without = json.loads(json.dumps(config))
    without.pop("_root_folder_id")
    use_config(monkeypatch, without)
    run(["generate-notebooks", "--apply"], monkeypatch)

    coord = [c for c in doorway.mutations_of("create_file")
             if c["name"] == "all_languages.ipynb"]
    assert coord[0]["parents"] == [config["arao1248"]["folder_id"]]
