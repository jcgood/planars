"""`python -m coding laminar-analysis`, the weekly full analysis, against the
offline fake Drive.

The analysis and drawing are stubbed (they need R and take about an hour per
English dataset). What is checked here: which datasets the plan lists and
what it makes on Drive, where one dataset's PDF and bundle go, that a bundle
is the record of what was run, what the report files, and that nothing the
annotation could show up in reaches the output or an issue.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_door, drive_doorway, file_door, laminar_analysis, laminar_charts, state_files
from command_runner import run_command
from fake_drive import FakeDriveDoorway
from laminar import contributor_charts as cc
from laminar import planars_language

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["arao1248", "stan1293"]
SECRET = "v:secret-element"

pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


def test_drive_names_match_the_datasets():
    """drive_door lists the dataset names a PDF may carry; they are the
    groupings x selections planars_language makes."""
    made = {d.removeprefix("stan1293_") for d in planars_language.dataset_names("stan1293")}
    assert made == drive_door.ANALYSIS_DATASETS


@pytest.fixture()
def env(monkeypatch):
    """Fake doorway; two languages and a made-up one; spans, fingerprints
    and drawing stubbed."""
    doorway = FakeDriveDoorway.from_fixtures()
    ids = FakeDriveDoorway.drive_config()
    config = {lang: {"folder_id": ids[lang]["folder_id"]} for lang in LANGS}
    state_files.ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    state_files.ID_FILE.write_text(json.dumps(config), encoding="utf-8")
    prints: dict[str, str] = {}
    drawn: list[str] = []

    def draw_dataset(lang_id, dataset, work, date, table, permutations=0):
        assert permutations == laminar_analysis.PERMUTATIONS
        drawn.append(dataset)
        data = work / "chart_data" / dataset / "data"
        data.mkdir(parents=True)
        (data / "spans.tsv").write_text(f"spans of {dataset}\n", encoding="utf-8")
        (data / "fragmentation_test.tsv").write_text("p\t0.5\n", encoding="utf-8")
        return cc.Drawn(dataset.split("_")[1], dataset, f"%PDF-1.7 {dataset}".encode(), 7)

    monkeypatch.setattr(laminar_charts, "_languages",
                        lambda only: [only] if only else [*LANGS, "synth0001"])
    monkeypatch.setattr(planars_language, "span_table", lambda lang_id: lang_id)
    monkeypatch.setattr(laminar_analysis, "fingerprint",
                        lambda lang_id, dataset, table: prints.get(dataset, f"fp-{dataset}"))
    monkeypatch.setattr(cc, "draw_dataset", draw_dataset)
    monkeypatch.setattr("laminar.charts.preflight", lambda lang_id, apply: None)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, prints, drawn
    finally:
        drive_doorway.reset_doorway()


def run(argv, monkeypatch, fails: bool = False) -> str:
    monkeypatch.setattr("sys.argv", ["laminar-analysis", *argv])
    buf = io.StringIO()
    with redirect_stdout(buf):
        if fails:
            with pytest.raises(SystemExit):
                run_command(laminar_analysis, "laminar-analysis")
        else:
            run_command(laminar_analysis, "laminar-analysis")
    return buf.getvalue()


def one(dataset: str, monkeypatch, *extra, fails: bool = False) -> str:
    return run(["--lang", dataset.split("_")[0], "--dataset", dataset, "--apply", *extra],
               monkeypatch, fails=fails)


def _matrix(path: Path) -> dict:
    line = next(l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("matrix="))
    return json.loads(line.removeprefix("matrix="))


def test_dry_run_lists_every_dataset_without_a_bundle_and_writes_nothing(env, monkeypatch):
    doorway, _, drawn = env
    out = run([], monkeypatch)
    assert out.count("would run (no bundle yet)") == 16
    assert "synth0001" not in out, "made-up languages are left out of the weekly run"
    assert doorway.mutations == [] and drawn == []


def test_plan_makes_each_analysis_folder_once_and_writes_the_list(env, monkeypatch, tmp_path):
    doorway, _, _ = env
    output = tmp_path / "github_output"
    run(["--plan", "--apply", "--github-output", str(output)], monkeypatch)
    folders = [c for c in doorway.mutations_of("create_file") if c["name"] == "analysis"]
    ids = json.loads(state_files.ID_FILE.read_text(encoding="utf-8"))
    assert sorted(c["parents"][0] for c in folders) == sorted(ids[l]["folder_id"] for l in LANGS)
    assert all(ids[l]["analysis_folder_id"] for l in LANGS)
    matrix = _matrix(output)
    assert len(matrix["include"]) == 16
    assert matrix["include"][0] == {"lang": "arao1248", "dataset": "arao1248_types_all", "was": ""}
    assert "count=16" in output.read_text(encoding="utf-8")
    doorway.clear_mutations()
    run(["--plan", "--apply"], monkeypatch)
    assert doorway.mutations_of("create_file") == [], "the folders are made once"


def test_one_dataset_uploads_its_pdf_and_commits_its_bundle(env, monkeypatch):
    doorway, _, drawn = env
    run(["--plan", "--apply"], monkeypatch)
    doorway.clear_mutations()
    one("stan1293_types_all", monkeypatch)
    assert drawn == ["stan1293_types_all"]
    [create] = doorway.mutations_of("create_file")
    ids = json.loads(state_files.ID_FILE.read_text(encoding="utf-8"))
    assert create["name"] == "analysis_types_all_stan1293.pdf"
    assert create["parents"] == [ids["stan1293"]["analysis_folder_id"]]
    assert doorway.mutations_of("create_permission") == []
    assert file_door.bundle_files("stan1293", "stan1293_types_all") == [
        "data/fragmentation_test.tsv", "data/spans.tsv", "run.json"]
    record = laminar_analysis.committed_run(laminar_analysis.Pair("stan1293", "stan1293_types_all"))
    assert record["fingerprint"] == "fp-stan1293_types_all" and record["charts"] == 7


def test_a_dataset_up_to_date_is_not_run_again(env, monkeypatch):
    doorway, _, drawn = env
    one("stan1293_types_all", monkeypatch)
    drawn.clear()
    doorway.clear_mutations()
    out = one("stan1293_types_all", monkeypatch)
    assert "up to date" in out and drawn == [] and doorway.mutations == []
    out = run([], monkeypatch)
    assert "stan1293_types_all" not in out


def test_changed_spans_update_the_pdf_in_place_and_drop_old_bundle_files(env, monkeypatch):
    doorway, prints, _ = env
    one("stan1293_types_all", monkeypatch)
    first = doorway.mutations_of("create_file")[-1]
    old = laminar_analysis.Pair("stan1293", "stan1293_types_all")
    extra = file_door.BundleFile("stan1293", "stan1293_types_all", "data/gone.tsv").path
    extra.write_text("an output the exporter no longer makes\n", encoding="utf-8")
    doorway.clear_mutations()
    prints["stan1293_types_all"] = "fp-new"
    assert "spans, planar or code changed" in run([], monkeypatch)
    one("stan1293_types_all", monkeypatch)
    assert doorway.mutations_of("create_file") == []
    assert [u["name"] for u in doorway.mutations_of("update_file")] == [first["name"]]
    assert not extra.exists()
    assert laminar_analysis.committed_run(old)["fingerprint"] == "fp-new"


def _planned(tmp_path, monkeypatch) -> str:
    output = tmp_path / "github_output"
    run(["--plan", "--apply", "--lang", "stan1293", "--github-output", str(output)], monkeypatch)
    return json.dumps(_matrix(output))


def test_the_report_names_datasets_whose_job_failed_and_a_clean_run_closes_it(
        env, monkeypatch, github, tmp_path):
    planned = _planned(tmp_path, monkeypatch)
    for d in planars_language.dataset_names("stan1293")[1:]:
        one(d, monkeypatch)
    run(["--report", planned, "--apply", "--run-url", "https://example/run/1"], monkeypatch,
        fails=True)
    [issue] = [i for i in github.issues if laminar_analysis.ISSUE_LABEL in i["labels"]]
    assert "`stan1293_types_all`" in issue["body"] and "stan1293_types_complete" not in issue["body"]
    assert "python -m laminar charts stan1293_types_all --apply" in issue["body"]
    assert "https://example/run/1" in issue["body"]
    planned = _planned(tmp_path, monkeypatch)
    one("stan1293_types_all", monkeypatch)
    run(["--report", planned, "--apply"], monkeypatch)
    assert issue["number"] in [c[1] for c in github.calls_of("close")]


def test_a_refresh_during_the_run_is_not_a_failure(env, monkeypatch, github, tmp_path):
    """The job replaced the bundle; the data moved on afterwards."""
    _, prints, _ = env
    output = tmp_path / "github_output"
    run(["--plan", "--apply", "--lang", "stan1293", "--github-output", str(output)], monkeypatch)
    for d in planars_language.dataset_names("stan1293"):
        one(d, monkeypatch)
    prints["stan1293_types_all"] = "fp-after-the-refresh"
    run(["--report", json.dumps(_matrix(output)), "--apply"], monkeypatch)
    assert not [i for i in github.issues if laminar_analysis.ISSUE_LABEL in i["labels"]]


def test_a_failure_says_nothing_from_the_annotation(env, monkeypatch, github, tmp_path):
    def draw_dataset(*a, **kw):
        print(f"R says: {SECRET}")
        raise cc.DrawingFailed(f"Drawing failed:\n{SECRET}")

    planned = _planned(tmp_path, monkeypatch)
    monkeypatch.setattr(cc, "draw_dataset", draw_dataset)
    with pytest.raises(SystemExit, match="analysing and drawing failed") as exc:
        one("stan1293_types_all", monkeypatch)
    assert SECRET not in str(exc.value)
    assert file_door.bundle_files("stan1293", "stan1293_types_all") == []
    out = run(["--report", planned, "--apply"], monkeypatch, fails=True)
    assert SECRET not in out
    [issue] = [i for i in github.issues if laminar_analysis.ISSUE_LABEL in i["labels"]]
    assert SECRET not in issue["body"]


def test_unreadable_spans_are_reported(env, monkeypatch, github):
    def span_table(lang_id):
        print(f"warning about {SECRET}")
        if lang_id == "arao1248":
            raise planars_language.SpanTableError(f"cannot place {SECRET}")
        return lang_id

    monkeypatch.setattr(planars_language, "span_table", span_table)
    out = run([], monkeypatch)
    assert SECRET not in out and "reading its spans failed" in out
    run(["--report", '{"include": []}', "--apply"], monkeypatch, fails=True)
    [issue] = [i for i in github.issues if laminar_analysis.ISSUE_LABEL in i["labels"]]
    assert "its spans could not be read" in issue["body"] and SECRET not in issue["body"]


def test_the_move_issue_is_filed_once_at_three_languages(env, monkeypatch, github):
    run(["--plan", "--apply"], monkeypatch)
    assert not [i for i in github.issues if i["title"] == laminar_analysis.MOVE_TITLE]
    file_door.BundleFile("synth0002", "synth0002_types_all", "run.json").path.parent.mkdir(parents=True)
    file_door.BundleFile("synth0002", "synth0002_types_all", "run.json").path.write_text("{}")
    for _ in range(2):
        run(["--plan", "--apply"], monkeypatch)
    moves = [i for i in github.issues if i["title"] == laminar_analysis.MOVE_TITLE]
    assert len(moves) == 1 and "design" in moves[0]["labels"] and "#333" in moves[0]["body"]
