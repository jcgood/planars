"""The daily refresh as one command (`python -m coding daily-refresh`).

Two kinds of test. The first group replaces each command with a stand-in
that returns a chosen exit status and output, and checks what the refresh
does with it: which issue it files or closes, where it stops. The last test runs every real command, in order, against the offline
Drive (`fake_drive.FakeDriveDoorway`), the in-memory GitHub and a scratch git
repository, and checks the run finishes without breaking and leaves the real
repositories untouched.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from coding import daily_refresh as dr

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Stand-ins
# ---------------------------------------------------------------------------

class FakeGit:
    """A repository that remembers commits. `dirty` says whether the next
    commit finds anything staged; `fail_on` makes a commit whose message
    contains it fail, as a failed push would."""

    def __init__(self, dirty: bool = True, fail_on: Optional[str] = None):
        self.commits: List[Tuple[str, Tuple[str, ...]]] = []
        self.dirty, self.fail_on = dirty, fail_on

    def commit(self, message: str, paths=("-A",)) -> bool:
        if self.fail_on and self.fail_on in message:
            raise dr.GitError(f"push rejected ({message})")
        if not self.dirty:
            return False
        self.commits.append((message, tuple(paths)))
        return True


@pytest.fixture()
def refresh_env(monkeypatch, tmp_path):
    """Every command replaced by a stand-in; `results` chooses what a command
    returns (key: the command and its flags as one string)."""
    results: Dict[str, dr.Result] = {}
    calls: List[str] = []

    def fake_run(cmd: str, *argv: str) -> dr.Result:
        key = " ".join((cmd,) + argv)
        calls.append(key)
        return results.get(key, dr.Result(0, f"{key}: ok\n"))

    code = FakeGit()
    monkeypatch.setattr(dr, "run", fake_run)
    monkeypatch.setattr(dr, "regenerate_snapshots", lambda: results.get(
        "snapshots", dr.Result(0, "snapshots: ok\n")))
    monkeypatch.setattr(dr, "code_git", lambda: code)
    coded = tmp_path / "coded_data"
    (coded / "stan1293" / "lang_setup").mkdir(parents=True)
    monkeypatch.setattr(dr, "CODED_DATA", coded)
    import coding.sync_planar as sp
    monkeypatch.setattr(sp, "PLANAR_CHANGES_PATH", tmp_path / "planar_changes.json")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    return results, calls, code, tmp_path


def _open(github, label: str) -> List[dict]:
    return github.list_issues(label)


# ---------------------------------------------------------------------------
# What each outcome leads to
# ---------------------------------------------------------------------------

def test_a_clean_run_runs_every_command_in_order_and_closes_every_issue(refresh_env, github):
    results, calls, code, _ = refresh_env
    for label in ("import-error", "integrity-error", "sheet-drift", "data-overwrite"):
        github.seed_issue(f"old {label}", label)
    r = dr.refresh()
    assert r.halted is None and r.uncovered_failures == []
    assert calls == [
        "issue --sync-labels --apply",
        "sync-planar --apply",
        "import-sheets --apply --ignore-status",
        "check-notes --apply",
        "check-comments --apply",
        "sync-diagnostics-yaml --apply",
        "proposal-sheets --apply",
        "sync-params --apply",
        "generate-sheets --regen-dependents",
        "integrity-check --check-dependents",
        "check-codebook",
        "integrity-check --check-stale-sheets",
        "integrity-check",
        "build-chapters --check --apply",
        "sync-overleaf --apply",
        "update-sheets --apply",
        "refresh-dropdowns --apply",
        "generate-status-sheet --apply",
        "generate-notebooks --apply",
    ]
    for label in ("import-error", "integrity-error", "sheet-drift", "data-overwrite"):
        assert _open(github, label) == []
    assert code.commits[0][1] == ("tests/snapshots/",)


def test_an_import_crash_files_import_error_led_by_the_crash_and_the_run_goes_on(
        refresh_env, github):
    results, calls, *_ = refresh_env
    results["import-sheets --apply --ignore-status"] = dr.Result(1, (
        "WARNING: something printed earlier\n"
        "Traceback (most recent call last):\n"
        '  File "/x/coding/import_sheets.py", line 9, in main\n'
        "    boom()\n"
        "KeyError: 'Status'\n"))
    r = dr.refresh()
    [issue] = _open(github, "import-error")
    assert issue["title"].startswith("Import error in data refresh (")
    body = issue["body"]
    assert body.index("The import crashed: `KeyError: 'Status'`") < body.index("something printed earlier")
    assert 'File "/x/coding/import_sheets.py", line 9' in body
    assert "integrity-check" in calls and r.halted is None


def test_a_second_failing_day_replaces_the_open_issue_rather_than_filing_another(
        refresh_env, github):
    results, *_ = refresh_env
    results["integrity-check"] = dr.Result(1, "  ✗ planar_stan1293.tsv: bad row\n")
    dr.refresh()
    dr.refresh()
    [issue] = _open(github, "integrity-error")
    assert "- planar_stan1293.tsv: bad row" in issue["body"]


def test_a_step_that_breaks_stops_the_run_but_the_always_steps_still_run(
        refresh_env, github, monkeypatch):
    results, calls, code, _ = refresh_env

    def cannot_file(*a, **k):
        raise RuntimeError("GitHub refused")
    monkeypatch.setattr(dr.issues, "close_open", cannot_file)
    r = dr.refresh()
    assert r.halted and "planar" in r.halted                  # its issue could not be closed
    assert "check-notes --apply" not in calls                 # skipped
    assert code.commits                                       # snapshots still committed
    outcomes = dict(r.outcomes)
    assert outcomes["snapshots"] == "done" and outcomes["scope"] == "done"
    assert outcomes["sheet updates"] == "skipped"


def test_a_failing_step_with_no_issue_of_its_own_makes_the_run_fail(refresh_env, monkeypatch):
    results, *_ = refresh_env
    results["check-notes --apply"] = dr.Result(1, "Docs API refused\n")
    r = dr.refresh()
    assert r.halted is None and r.uncovered_failures == ["collaborator notes"]
    monkeypatch.setattr(dr, "refresh", lambda: r)
    with pytest.raises(SystemExit) as exited:
        dr.main(dr.build_parser().parse_args(["--apply"]))
    assert exited.value.code == 1


def test_planar_changes_file_planar_changed_with_the_command_to_run(refresh_env, github, monkeypatch):
    results, *_ = refresh_env
    import coding.sync_planar as sp

    def sync_planar_writes_changes(cmd, *argv):
        if cmd == "sync-planar":
            sp.PLANAR_CHANGES_PATH.write_text(json.dumps({"stan1293": {
                "diff": {"added": {"31": "v:new"}}, "recommendation":
                "python -m coding update-sheets --apply"}}), encoding="utf-8")
        return dr.Result(0, "")
    monkeypatch.setattr(dr, "run", sync_planar_writes_changes)
    dr.refresh()
    [issue] = _open(github, "planar-changed")
    assert "- `+` position 31 (`v:new`) — added" in issue["body"]
    assert "python -m coding update-sheets --apply" in issue["body"]


def test_yesterdays_planar_changes_are_not_reported_again(refresh_env, github):
    *_, tmp = refresh_env
    (tmp / "planar_changes.json").write_text(json.dumps(
        {"stan1293": {"diff": {}, "recommendation": "r"}}))
    dr.refresh()
    assert _open(github, "planar-changed") == []


def test_the_refresh_replacing_another_commands_change_files_data_overwrite(
        refresh_env, github, monkeypatch):
    """Read from the change log (file_door.overwrites, tested in
    test_file_door.py): a migration's change, then today's import."""
    from coding import file_door
    log = file_door.change_log("stan1293")
    log.parent.mkdir(parents=True)
    header = "\t".join(file_door.CHANGE_LOG_COLUMNS)
    log.write_text(f"{header}\n2026-10-01T00:00:00Z\tmetrical/stress_domain.tsv\t1 cell(s) "
                   f"changed\tsort-examples\tmoved examples\tarchive/metrical/a.tsv\n",
                   encoding="utf-8")
    real_run = dr.run

    def import_logs(cmd, *argv):
        if cmd == "import-sheets":
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"{dr.now()}\tmetrical/stress_domain.tsv\t1 cell(s) changed\t"
                        f"import-sheets (daily refresh)\timported\tarchive/metrical/b.tsv\n")
        return real_run(cmd, *argv)
    monkeypatch.setattr(dr, "run", import_logs)
    dr.refresh()
    [issue] = _open(github, "data-overwrite")
    assert "`stan1293/metrical/stress_domain.tsv`" in issue["body"]
    assert "`sort-examples` made on 2026-10-01" in issue["body"]
    assert "`stan1293/archive/metrical/b.tsv`" in issue["body"]


def test_codebook_failure_attaches_the_rule_update_prompts(refresh_env, github):
    results, calls, *_ = refresh_env
    results["check-codebook"] = dr.Result(1, "  ✗ hash mismatch for metrical\n")
    results["generate-rule-update-prompt"] = dr.Result(0, "PROMPT TEXT\n")
    dr.refresh()
    [issue] = _open(github, "codebook-error")
    assert "- hash mismatch for metrical" in issue["body"]
    assert issue["body"].rstrip().endswith("PROMPT TEXT")


def test_an_audit_is_filed_when_none_was_ever_closed(refresh_env, github):
    dr.refresh()
    [issue] = _open(github, "audit")
    assert issue["title"].startswith("Audit due (")
    assert "No audit issue has been closed before" in issue["body"]
    assert '§ "Audit procedure"' in issue["body"]


def test_an_audit_is_filed_when_the_last_closed_over_a_month_ago(refresh_env, github):
    github.seed_issue("Audit due (2026-01-01)", "audit", state="CLOSED",
                      closed_at="2026-01-05T00:00:00Z")
    dr.refresh()
    [issue] = _open(github, "audit")
    assert "closed on 2026-01-05" in issue["body"]
    assert "git log --since=2026-01-05" in issue["body"]


def test_no_audit_is_filed_when_one_is_open_or_closed_recently(refresh_env, github):
    from datetime import datetime, timedelta, timezone
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    github.seed_issue("Audit due (recent)", "audit", state="CLOSED", closed_at=recent)
    dr.refresh()
    assert _open(github, "audit") == []
    github.seed_issue("Audit due (in progress)", "audit")
    dr.refresh()
    assert [i["title"] for i in _open(github, "audit")] == ["Audit due (in progress)"]


def test_the_summary_page_gets_each_report_and_the_step_table(refresh_env):
    *_, tmp = refresh_env
    dr.refresh()
    summary = (tmp / "summary.md").read_text(encoding="utf-8")
    for title in ("Import", "Diagnostics YAML sync", "Sheet drift check",
                  "Annotation scope", "Daily refresh steps"):
        assert f"## {title} — " in summary


def test_run_keeps_a_crash_and_an_exit_status_and_still_shows_the_output(monkeypatch, capsys):
    import coding.__main__ as entry

    def crashes(cmd, argv):
        print("half way")
        raise KeyError("Status")

    monkeypatch.setattr(entry, "dispatch", crashes)
    result = dr.run("import-sheets", "--apply")
    assert result.exit_code == 1
    assert "half way" in result.output and "KeyError: 'Status'" in result.output
    assert "Traceback (most recent call last)" in result.output
    assert "half way" in capsys.readouterr().out          # shown as it ran

    monkeypatch.setattr(entry, "dispatch", lambda cmd, argv: (_ for _ in ()).throw(SystemExit(3)))
    assert dr.run("integrity-check").exit_code == 3


def test_without_apply_it_lists_the_steps_and_runs_nothing(refresh_env, capsys):
    _, calls, *_ = refresh_env
    dr.main(dr.build_parser().parse_args([]))
    assert calls == []
    out = capsys.readouterr().out
    assert "dry run" in out and "import-sheets --apply --ignore-status" in out


def test_the_workflow_only_sets_up_and_runs_the_command():
    text = (ROOT / ".github" / "workflows" / "data-refresh.yml").read_text(encoding="utf-8")
    runs = [l.strip() for l in text.splitlines() if l.strip().startswith("run:")]
    assert "run: python -m coding daily-refresh --apply" in runs
    assert not [r for r in runs if "python -m coding" in r and "daily-refresh" not in r]


# ---------------------------------------------------------------------------
# Every real command, against the offline Drive
# ---------------------------------------------------------------------------

def _status(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                          capture_output=True, text=True).stdout


def _scratch_repo(tmp_path: Path, source: Path) -> Path:
    """A git copy of `source` with a bare remote it can push to."""
    remote = tmp_path / "remote.git"
    # Branch named, not the machine's default (main here, master on CI).
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    repo = tmp_path / "coded_data"
    shutil.copytree(source, repo, ignore=shutil.ignore_patterns(".git"))
    for args in (["init", "-q", "-b", "main"],
                 ["config", "user.name", "test"], ["config", "user.email", "t@example.org"],
                 ["add", "-A"], ["commit", "-q", "-m", "start"],
                 ["remote", "add", "origin", str(remote)], ["push", "-q", "-u", "origin", "main"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    return repo


@pytest.mark.skipif(not (ROOT / "coded_data").exists(),
                    reason="coded_data/ (planars-data) is not checked out")
def test_the_whole_refresh_runs_against_the_offline_drive(monkeypatch, tmp_path, github):
    import coding
    import importlib
    import pkgutil
    from coding import drive as drive_module, drive_doorway
    from fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway, point_coded_data_at

    repo_before = _status(ROOT)
    real_data = ROOT / "coded_data"
    data_before = _status(real_data)

    coded = _scratch_repo(tmp_path, FROZEN_CODED_DATA)
    point_coded_data_at(monkeypatch, coded)
    monkeypatch.setattr(dr, "CODED_DATA", coded)
    monkeypatch.setattr(dr, "code_git", lambda: FakeGit())
    monkeypatch.setattr(dr, "regenerate_snapshots", lambda: dr.Result(0, "snapshots: stand-in\n"))

    # Every file a command writes outside coded_data/ goes to tmp_path.
    saved_configs: List[dict] = []
    for info in pkgutil.iter_modules(coding.__path__):
        if info.name.startswith("__"):
            continue
        module = importlib.import_module(f"coding.{info.name}")
        if hasattr(module, "_load_drive_config"):
            monkeypatch.setattr(module, "_load_drive_config", FakeDriveDoorway.drive_config)
        if hasattr(module, "_save_drive_config"):
            monkeypatch.setattr(module, "_save_drive_config", saved_configs.append)
        if hasattr(module, "MANIFEST_PATH"):
            monkeypatch.setattr(module, "MANIFEST_PATH", tmp_path / "sheets_manifest.json")
    from coding import generate_notebooks, glottolog, import_sheets, sync_planar
    from conftest import point_state_files_at
    monkeypatch.setattr(import_sheets, "ROOT", tmp_path)
    monkeypatch.setattr(import_sheets, "ERROR_DIR", tmp_path / "import_errors")
    monkeypatch.setattr(sync_planar, "PLANAR_CHANGES_PATH", tmp_path / "planar_changes.json")
    monkeypatch.setattr(glottolog, "CACHE_PATH", tmp_path / "glottolog_cache.json")
    # The state files live in the scratch planars-data, as they do live, so
    # the test sees whether they reach its remote.
    point_state_files_at(monkeypatch, coded)
    monkeypatch.setattr(generate_notebooks, "regenerate_notebooks", lambda *a, **k: None)
    monkeypatch.setattr("coding.drive_door.time.sleep", lambda *a, **kw: None)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    drive_doorway.set_doorway(FakeDriveDoorway.from_fixtures())
    try:
        r = dr.refresh()
    finally:
        drive_doorway.reset_doorway()

    report = "\n".join(f"{n}: {o}" for n, o in r.outcomes)
    assert r.halted is None, report
    assert all(o == "done" for _, o in r.outcomes), report
    # The tree is committed at the end, so nothing is left for a later
    # command's clean-tree check to trip on.
    assert _status(coded) == ""
    # The state files reached GitHub's copy (unit 12): what the refresh wrote
    # to Drive is logged there.
    remote = tmp_path / "remote.git"
    on_remote = subprocess.run(["git", "-C", str(remote), "ls-tree", "-r", "--name-only", "main"],
                               capture_output=True, text=True, check=True).stdout.split()
    assert ".state/provenance_log.jsonl" in on_remote, report
    # Nothing outside the scratch copies changed.
    assert _status(ROOT) == repo_before
    assert _status(real_data) == data_before
    # Every command finished; the ones that found problems in the saved data
    # (on 2026-10-17: import-error, dependent-stale, integrity-error, the same
    # three the live refresh had open) said so in an issue with a real body.
    assert r.uncovered_failures == [], report
    for issue in github.issues:
        assert issue["body"].strip(), f"empty body: {issue['title']}"
