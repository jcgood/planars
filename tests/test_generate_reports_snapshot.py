"""Snapshot tests for `python -m coding generate-reports`, run against the fake.

File 2 of 11 migrated to the Drive doorway (plan Phase 0b/1). This command never
touches gspread — its entire Drive footprint is "upload a PDF, create or update
in place" — so it locks the *other* half of the doorway: Drive file operations and
permission grants.

**PDF rendering is stubbed.** It is slow, needs system libraries, is not
byte-stable across weasyprint versions, and already has coverage in
tests/test_html_report.py. What these snapshots lock is the Drive interaction: how
many files, into which folders, under what names, with what permissions, and
what ends up in drive_config.json.

**drive_config.json is never written by these tests.** The real one lives in the
repo root and holds live Drive IDs; `_save_drive_config` is patched to capture
into a dict instead. A test that clobbered it would break the coordinator's
ability to reach their own Drive.

Pre-migration baseline: the unmigrated code was driven from the same fake
through a Drive-service shim; both `--apply` paths (create and update) produced
identical call sequences, payload sizes, names, parents, and permissions.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_generate_reports_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway, generate_reports
from fake_drive import MANIFEST_FILE_ID, FakeDriveDoorway
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "generate_reports"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


@pytest.fixture()
def env(monkeypatch):
    """Fake doorway, stubbed PDF rendering, and a captured drive_config."""
    doorway = FakeDriveDoorway.from_fixtures()
    manifest = json.loads(doorway.file(MANIFEST_FILE_ID).content.decode())
    config = {lang: {"folder_id": entry["folder_id"]}
              for lang, entry in manifest.items() if entry.get("folder_id")}
    saved: dict = {}

    monkeypatch.setattr(generate_reports, "language_report_data",
                        lambda lang_id, source, repo_root: {"lang_id": lang_id})
    monkeypatch.setattr(generate_reports, "render_language_report_pdf",
                        lambda data: f"%PDF-1.4 {data['lang_id']}".encode())
    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(generate_reports, "_save_drive_config", saved.update)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, config, saved
    finally:
        drive_doorway.reset_doorway()


def run(argv, monkeypatch) -> str:
    monkeypatch.setattr("sys.argv", argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        generate_reports.main()
    return buf.getvalue()


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
    check_snapshot("dry_run.txt", run(["generate-reports"], monkeypatch))


def test_dry_run_touches_neither_drive_nor_config(env, monkeypatch):
    doorway, _, saved = env
    run(["generate-reports"], monkeypatch)
    assert doorway.mutations == []
    assert saved == {}


def test_dry_run_never_authenticates(monkeypatch):
    """A dry run must not reach for OAuth — it has nothing to ask Drive.

    Asserted without a doorway installed at all, so any client construction
    would fail loudly rather than pop a browser auth flow.
    """
    monkeypatch.setattr(generate_reports, "language_report_data",
                        lambda *a, **k: {"lang_id": "x"})
    drive_doorway.reset_doorway()
    monkeypatch.setattr(drive_doorway, "_get_clients",
                        lambda: pytest.fail("dry run must not authenticate"))
    run(["generate-reports"], monkeypatch)


# ---------------------------------------------------------------------------
# Apply — create path
# ---------------------------------------------------------------------------

def test_apply_create_output(env, monkeypatch):
    check_snapshot("apply_create.txt", run(["generate-reports", "--apply"], monkeypatch))


def test_apply_create_mutation_digest(env, monkeypatch):
    doorway, _, _ = env
    run(["generate-reports", "--apply"], monkeypatch)
    check_snapshot("apply_create_digest.txt", render(doorway.mutations))


def test_apply_create_uploads_one_pdf_per_language_into_its_own_folder(env, monkeypatch):
    doorway, config, saved = env
    run(["generate-reports", "--apply"], monkeypatch)

    creates = doorway.mutations_of("create_file")
    assert [c["name"] for c in creates] == [
        f"report_{lang}.pdf" for lang in sorted(config)]
    for create in creates:
        lang = create["name"][len("report_"):-len(".pdf")]
        assert create["parents"] == [config[lang]["folder_id"]]
        assert create["mimetype"] == "application/pdf"
    assert doorway.mutations_of("update_file") == []


def test_apply_create_grants_anyone_reader_once_per_new_report(env, monkeypatch):
    """PDFs are meant to be link-shareable with non-technical collaborators."""
    doorway, config, _ = env
    run(["generate-reports", "--apply"], monkeypatch)
    perms = doorway.mutations_of("create_permission")
    assert len(perms) == len(config)
    assert all(p["type"] == "anyone" and p["role"] == "reader" for p in perms)


def test_apply_records_new_file_ids_in_drive_config(env, monkeypatch):
    doorway, config, saved = env
    run(["generate-reports", "--apply"], monkeypatch)
    created = {c["name"]: c["file_id"] for c in doorway.mutations_of("create_file")}
    for lang in config:
        assert saved[lang]["report_file_id"] == created[f"report_{lang}.pdf"]
        assert "report_html_file_id" not in saved[lang]


# ---------------------------------------------------------------------------
# Apply — update path
# ---------------------------------------------------------------------------

def test_apply_second_run_updates_in_place_keeping_the_url(env, monkeypatch):
    """The stable-URL promise: a re-run must not mint new file IDs."""
    doorway, config, saved = env
    run(["generate-reports", "--apply"], monkeypatch)
    first_ids = {lang: saved[lang]["report_file_id"] for lang in config}

    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(saved)))
    doorway.clear_mutations()
    out = run(["generate-reports", "--apply"], monkeypatch)

    assert doorway.mutations_of("create_file") == []
    updates = doorway.mutations_of("update_file")
    assert sorted(u["file_id"] for u in updates) == sorted(first_ids.values())
    # The update path renames on every run, unlike the manifest writer.
    assert all(u["name"] == f"report_{lang}.pdf"
               for lang, u in zip(sorted(config), sorted(updates, key=lambda u: u["name"])))
    assert "created." not in out and "updated." in out


def test_update_path_does_not_duplicate_the_permission(env, monkeypatch):
    """A normal repeat run finds the grant already there and adds nothing."""
    doorway, config, saved = env
    run(["generate-reports", "--apply"], monkeypatch)
    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(saved)))
    doorway.clear_mutations()
    run(["generate-reports", "--apply"], monkeypatch)
    assert doorway.mutations_of("create_permission") == []


def test_update_path_now_self_heals_after_a_manual_revoke(env, monkeypatch):
    """The behavioural change issue #276 asked for: reports now self-heal too.

    Before, this file granted the "anyone" share only on create — a report
    whose permission was removed by hand was never restored, unlike a
    notebook, which generate_notebooks.py already reasserted every run. Both
    now go through the same shared, idempotent check
    (drive.ensure_anyone_permission), so a manually-revoked report share comes
    back on the next --apply.
    """
    doorway, config, saved = env
    run(["generate-reports", "--apply"], monkeypatch)
    file_id = saved["stan1293"]["report_file_id"]
    perm = next(p for p in doorway.list_permissions(file_id) if p["type"] == "anyone")
    doorway.delete_permission(file_id, perm["id"])
    assert not any(p["type"] == "anyone" for p in doorway.list_permissions(file_id))

    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(saved)))
    doorway.clear_mutations()
    run(["generate-reports", "--apply"], monkeypatch)

    assert any(p["type"] == "anyone" and p["role"] == "reader"
               for p in doorway.list_permissions(file_id))
    created = [p for p in doorway.mutations_of("create_permission") if p["file_id"] == file_id]
    assert len(created) == 1


def test_legacy_report_html_file_id_is_migrated_in_place(env, monkeypatch):
    """The old key names an existing file — it must be updated, not re-created."""
    doorway, config, saved = env
    legacy = {lang: {"folder_id": cfg["folder_id"],
                     "report_html_file_id": f"legacy_{lang}"}
              for lang, cfg in config.items()}
    for lang in config:
        doorway.seed_file(f"report_{lang}.pdf", "application/pdf",
                          [config[lang]["folder_id"]], file_id=f"legacy_{lang}")
    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(legacy)))

    run(["generate-reports", "--apply"], monkeypatch)

    assert doorway.mutations_of("create_file") == []
    assert sorted(u["file_id"] for u in doorway.mutations_of("update_file")) == [
        f"legacy_{lang}" for lang in sorted(config)]
    for lang in config:
        assert saved[lang]["report_file_id"] == f"legacy_{lang}"
        assert "report_html_file_id" not in saved[lang]


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_a_language_without_a_folder_id_is_skipped_not_fatal(env, monkeypatch):
    doorway, config, saved = env
    partial = dict(config)
    partial["arao1248"] = {}
    monkeypatch.setattr(generate_reports, "_load_drive_config",
                        lambda: json.loads(json.dumps(partial)))
    out = run(["generate-reports", "--apply"], monkeypatch)
    assert "No folder_id in drive_config — skipping" in out
    assert [c["name"] for c in doorway.mutations_of("create_file")] == [
        "report_stan1293.pdf", "report_synth0001.pdf"]


def test_an_upload_failure_skips_that_language_and_continues(env, monkeypatch):
    doorway, config, saved = env
    real_create = doorway.create_file

    def flaky(name, *a, **kw):
        if "stan1293" in name:
            raise RuntimeError("boom")
        return real_create(name, *a, **kw)

    monkeypatch.setattr(doorway, "create_file", flaky)
    out = run(["generate-reports", "--apply"], monkeypatch)
    assert "upload ERROR: boom" in out
    # The failed language records no file ID (nothing was uploaded to point at),
    # and the run carries on to the next one rather than aborting.
    assert "report_file_id" not in saved["stan1293"]
    assert "report_file_id" in saved["synth0001"]
