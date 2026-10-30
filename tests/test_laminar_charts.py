"""`python -m coding laminar-charts`, run against the offline fake Drive.

Drawing is stubbed (it needs R and takes minutes; laminar/contributor_charts.py
is checked by drawing English locally). What is checked here: which
languages are drawn and when, where the PDFs go and under what names, that
they get no sharing of their own, that links stay the same, and what is
recorded in drive_config.json and the state file.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway, laminar_charts, state_files
from command_runner import run_command
from fake_drive import FakeDriveDoorway
from laminar import contributor_charts as cc
from laminar import planars_language

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["arao1248", "stan1293"]

pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


linked: list[str] = []   # languages whose status sheet was rebuilt


@pytest.fixture()
def env(monkeypatch):
    """Fake doorway; two languages; spans and drawing stubbed; a fingerprint
    a test can change."""
    doorway = FakeDriveDoorway.from_fixtures()
    ids = FakeDriveDoorway.drive_config()
    config = {lang: {"folder_id": ids[lang]["folder_id"]} for lang in LANGS}
    state_files.ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    state_files.ID_FILE.write_text(json.dumps(config), encoding="utf-8")
    fingerprints = {lang: f"fp-{lang}" for lang in LANGS}
    drawn: list[str] = []

    def draw(lang_id, work, date, table=None):
        drawn.append(lang_id)
        return [cc.Drawn(g, f"{lang_id}_{g}_all", f"%PDF-1.7 {lang_id} {g}".encode(), 3)
                for g in cc.CONTRIBUTOR_DATASETS]

    monkeypatch.setattr(laminar_charts, "_languages", lambda only: [only] if only else LANGS)
    monkeypatch.setattr(planars_language, "span_table", lambda lang_id: lang_id)
    monkeypatch.setattr(cc, "fingerprint", lambda lang_id, table: fingerprints[lang_id])
    monkeypatch.setattr(cc, "draw", draw)
    monkeypatch.setattr("laminar.charts.preflight", lambda lang_id, apply: None)
    linked.clear()
    monkeypatch.setattr(laminar_charts, "_link_on_status_sheet",
                        lambda lang_id: linked.append(lang_id))
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, fingerprints, drawn
    finally:
        drive_doorway.reset_doorway()


def run(argv, monkeypatch, fails: bool = False) -> str:
    """The command's output; with `fails`, check it exits non-zero."""
    monkeypatch.setattr("sys.argv", ["laminar-charts", *argv])
    buf = io.StringIO()
    with redirect_stdout(buf):
        if fails:
            with pytest.raises(SystemExit):
                run_command(laminar_charts, "laminar-charts")
        else:
            run_command(laminar_charts, "laminar-charts")
    return buf.getvalue()


def _ids() -> dict:
    return json.loads(state_files.ID_FILE.read_text(encoding="utf-8"))


def test_dry_run_draws_and_uploads_nothing(env, monkeypatch):
    doorway, _, drawn = env
    out = run([], monkeypatch)
    assert "would draw (not on Drive yet)" in out
    assert drawn == [] and doorway.mutations == []
    assert not state_files.LAMINAR_CHARTS_STATE_PATH.exists()


def test_apply_puts_two_pdfs_in_each_language_folder_unshared(env, monkeypatch):
    doorway, _, drawn = env
    run(["--apply"], monkeypatch)
    assert drawn == LANGS
    creates = doorway.mutations_of("create_file")
    assert sorted(c["name"] for c in creates) == sorted(
        f"charts_by_{by}_{lang}.pdf" for lang in LANGS for by in ("class", "type"))
    ids = _ids()
    for c in creates:
        lang = c["name"].rsplit("_", 1)[1].removesuffix(".pdf")
        assert c["parents"] == [ids[lang]["folder_id"]]
        assert c["mimetype"] == "application/pdf"
    assert doorway.mutations_of("create_permission") == []
    assert linked == LANGS, "new PDFs: each status sheet rebuilt to link them"
    for lang in LANGS:
        assert ids[lang]["charts_classes_file_id"] and ids[lang]["charts_types_file_id"]
    state = json.loads(state_files.LAMINAR_CHARTS_STATE_PATH.read_text(encoding="utf-8"))
    assert state["stan1293"]["fingerprint"] == "fp-stan1293"


def test_nothing_changed_draws_nothing(env, monkeypatch):
    doorway, _, drawn = env
    run(["--apply"], monkeypatch)
    drawn.clear()
    doorway.clear_mutations()
    out = run(["--apply"], monkeypatch)
    assert drawn == [] and doorway.mutations == []
    assert "up to date" in out


def test_changed_spans_redraw_that_language_in_place(env, monkeypatch):
    doorway, fingerprints, drawn = env
    run(["--apply"], monkeypatch)
    first = _ids()["stan1293"]
    drawn.clear()
    doorway.clear_mutations()
    fingerprints["stan1293"] = "fp-new"
    out = run(["--apply"], monkeypatch)
    assert drawn == ["stan1293"]
    assert "spans, planar or chart code changed" in out
    assert doorway.mutations_of("create_file") == []
    assert linked == LANGS, "updated in place: same links, so the status sheet isn't rebuilt"
    assert sorted(u["file_id"] for u in doorway.mutations_of("update_file")) == sorted(
        [first["charts_classes_file_id"], first["charts_types_file_id"]])


def test_force_redraws(env, monkeypatch):
    _, _, drawn = env
    run(["--apply"], monkeypatch)
    drawn.clear()
    run(["--apply", "--force", "--lang", "stan1293"], monkeypatch)
    assert drawn == ["stan1293"]


def test_a_language_with_no_spans_is_skipped(env, monkeypatch):
    _, _, drawn = env

    def span_table(lang_id):
        if lang_id == "arao1248":
            raise planars_language.NoSpansYet("no spans")
        return lang_id

    monkeypatch.setattr(planars_language, "span_table", span_table)
    out = run(["--apply"], monkeypatch)
    assert "no spans yet" in out and drawn == ["stan1293"]


def test_a_failure_skips_that_language_records_nothing_and_fails_the_run(env, monkeypatch):
    doorway, _, drawn = env
    real_create = doorway.create_file

    def flaky(name, *a, **kw):
        if "arao1248" in name:
            raise RuntimeError("boom")
        return real_create(name, *a, **kw)

    monkeypatch.setattr(doorway, "create_file", flaky)
    with pytest.raises(SystemExit, match="Failed for arao1248"):
        run(["--apply"], monkeypatch)
    state = json.loads(state_files.LAMINAR_CHARTS_STATE_PATH.read_text(encoding="utf-8"))
    assert "arao1248" not in state and "stan1293" in state


# What the annotation could show up in never reaches the output or the issue:
# the workflow's log and the issue are public (the repository is).
SECRET = "v:secret-element"


def _failing_draw(env, monkeypatch, lang="arao1248"):
    _, _, drawn = env
    real = cc.draw

    def draw(lang_id, work, date, table=None):
        if lang_id == lang:
            print(f"R says: {SECRET}")
            raise cc.DrawingFailed(f"Drawing failed:\n{SECRET}")
        return real(lang_id, work, date, table=table)

    monkeypatch.setattr(cc, "draw", draw)


def test_a_drawing_failure_files_an_issue_without_the_reason(env, monkeypatch, github):
    _failing_draw(env, monkeypatch)
    out = run(["--apply"], monkeypatch, fails=True)
    assert SECRET not in out
    assert "python -m laminar.contributor_charts arao1248" in out
    [issue] = [i for i in github.issues if laminar_charts.ISSUE_LABEL in i["labels"]]
    assert SECRET not in issue["body"]
    assert "drawing failed" in issue["body"]
    assert "python -m laminar.contributor_charts arao1248" in issue["body"]
    assert "stan1293" not in issue["body"]


def test_a_second_failure_rewrites_the_issue_and_a_clean_run_closes_it(env, monkeypatch, github):
    working_draw = cc.draw
    _failing_draw(env, monkeypatch)
    for _ in range(2):
        with pytest.raises(SystemExit):
            run(["--apply"], monkeypatch)
    filed = [i for i in github.issues if laminar_charts.ISSUE_LABEL in i["labels"]]
    assert len(filed) == 1
    monkeypatch.setattr(cc, "draw", working_draw)
    run(["--apply"], monkeypatch)
    assert filed[0]["number"] in [c[1] for c in github.calls_of("close")]


def test_what_the_span_code_prints_is_held_back(env, monkeypatch, github):
    def span_table(lang_id):
        print(f"warning about {SECRET}")
        if lang_id == "arao1248":
            raise planars_language.SpanTableError(f"cannot place {SECRET}")
        return lang_id

    monkeypatch.setattr(planars_language, "span_table", span_table)
    out = run(["--apply"], monkeypatch, fails=True)
    assert SECRET not in out
    assert "reading its spans failed" in out
    [issue] = [i for i in github.issues if laminar_charts.ISSUE_LABEL in i["labels"]]
    assert SECRET not in issue["body"]


def test_missing_r_fails_every_language_to_be_drawn(env, monkeypatch, github):
    _, _, drawn = env

    def preflight(lang_id, apply):
        raise SystemExit("Can't draw yet:\n- R is not installed (no `Rscript` on the PATH).")

    monkeypatch.setattr("laminar.charts.preflight", preflight)
    with pytest.raises(SystemExit, match="Failed for arao1248, stan1293"):
        run(["--apply"], monkeypatch)
    assert drawn == []
    [issue] = [i for i in github.issues if laminar_charts.ISSUE_LABEL in i["labels"]]
    assert "setting up R failed: R is not installed" in issue["body"]


def test_a_lang_run_leaves_the_issue_alone(env, monkeypatch, github):
    _failing_draw(env, monkeypatch, lang="stan1293")
    with pytest.raises(SystemExit):
        run(["--apply", "--lang", "stan1293"], monkeypatch)
    assert not [i for i in github.issues if laminar_charts.ISSUE_LABEL in i["labels"]]


def test_a_dry_run_files_no_issue(env, monkeypatch, github):
    _failing_draw(env, monkeypatch)
    run([], monkeypatch)
    assert github.calls == []
