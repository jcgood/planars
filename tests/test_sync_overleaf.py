"""sync-overleaf (coding/sync_overleaf.py): .papers/ and an Overleaf project
kept the same both ways. A local bare git repository stands in for
Overleaf; .papers/ is the temporary one tests/conftest.py points the door at."""

import json
import subprocess

import pytest

from coding import drive_door, file_door, state_files, sync_overleaf

PROJECT = "abc123"
VOLUME = f"title: A test volume\nvenue: book\nparts: [intro, stan1293]\noverleaf: {PROJECT}\n"
PROSE = "stan1293/prose/background.tex"
BUILT = "stan1293/fragments/front_matter.tex"


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def overleaf(tmp_path, monkeypatch):
    """The stand-in project, holding Overleaf's starter main.tex, and a
    clone to edit it through (as someone in Overleaf would)."""
    remote = tmp_path / "overleaf_server"
    bare = remote / PROJECT
    bare.mkdir(parents=True)
    _git(bare, "init", "--quiet", "--bare", "--initial-branch=master")
    work = tmp_path / "overleaf_web"
    subprocess.run(["git", "clone", "--quiet", str(bare), str(work)], check=True,
                   capture_output=True)
    (work / "main.tex").write_text("starter\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "--quiet", "-m", "starter")
    _git(work, "push", "--quiet", "origin", "HEAD")
    monkeypatch.setattr(sync_overleaf, "OVERLEAF_GIT", f"{remote}/")
    monkeypatch.delenv(sync_overleaf.TOKEN_ENV, raising=False)
    return work


def _edit_in_overleaf(work, files):
    _git(work, "pull", "--quiet")
    for rel, text in files.items():
        path = work / rel
        if text is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "--quiet", "-m", "edit")
    _git(work, "push", "--quiet", "origin", "HEAD")


def _in_overleaf(work):
    _git(work, "pull", "--quiet")
    return {p.relative_to(work).as_posix(): p.read_text(encoding="utf-8")
            for p in work.rglob("*") if p.is_file() and ".git" not in p.parts}


def _papers(files):
    for rel, text in files.items():
        path = state_files.PAPERS_DIR / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _run(*argv):
    args = sync_overleaf.build_parser().parse_args(list(argv))
    with drive_door.running("sync-overleaf", args):
        sync_overleaf.main(args)


def _start(overleaf):
    _papers({"volume.yaml": VOLUME, "main.tex": "the volume\n", PROSE: "prose\n",
             BUILT: "built\n"})
    _run("--apply")


def test_without_a_project_there_is_nothing_to_sync(capsys, github):
    _papers({"volume.yaml": "title: T\nvenue: book\nparts: [intro]\n"})
    _run("--apply")
    assert "nothing to sync" in capsys.readouterr().out and not github.issues


def test_the_first_sync_replaces_the_project_and_a_second_changes_nothing(overleaf, capsys, github):
    _start(overleaf)
    held = _in_overleaf(overleaf)
    assert held["main.tex"] == "the volume\n" and held[PROSE] == "prose\n" and len(held) == 4
    state = json.loads(state_files.OVERLEAF_STATE_PATH.read_text(encoding="utf-8"))
    assert state["project"] == PROJECT and state["commit"] == _git(overleaf, "rev-parse", "HEAD").strip()
    before = _git(overleaf, "rev-parse", "HEAD")
    capsys.readouterr()
    _run("--apply")
    assert "unchanged" in capsys.readouterr().out
    _git(overleaf, "pull", "--quiet")
    assert _git(overleaf, "rev-parse", "HEAD") == before and not github.issues


def test_a_dry_run_writes_and_pushes_nothing(overleaf, capsys):
    _papers({"volume.yaml": VOLUME, PROSE: "prose\n"})
    _run()
    assert "Dry run" in capsys.readouterr().out
    assert _in_overleaf(overleaf) == {"main.tex": "starter\n"}
    assert not state_files.OVERLEAF_STATE_PATH.exists()


def test_each_side_s_edits_reach_the_other(overleaf):
    _start(overleaf)
    _edit_in_overleaf(overleaf, {PROSE: "written in Overleaf\n", "figures/map.tex": "a figure\n"})
    _papers({"stan1293/prose/other.tex": "written here\n"})
    _run("--apply")
    assert (state_files.PAPERS_DIR / PROSE).read_text(encoding="utf-8") == "written in Overleaf\n"
    assert (state_files.PAPERS_DIR / "figures/map.tex").exists()
    assert _in_overleaf(overleaf)["stan1293/prose/other.tex"] == "written here\n"
    _edit_in_overleaf(overleaf, {"figures/map.tex": None})
    _run("--apply")
    assert not (state_files.PAPERS_DIR / "figures/map.tex").exists()


def test_edits_that_meet_keep_both_and_the_issue_follows_the_copies(overleaf, github):
    _start(overleaf)
    _edit_in_overleaf(overleaf, {PROSE: "zebra prose\n", BUILT: "hand-edited\n"})
    _papers({PROSE: "planars-data's\n"})
    _run("--apply")
    assert (state_files.PAPERS_DIR / PROSE).read_text(encoding="utf-8") == "planars-data's\n"
    assert (state_files.PAPERS_DIR / BUILT).read_text(encoding="utf-8") == "built\n"
    copies = sorted(p.relative_to(state_files.PAPERS_DIR).as_posix()
                    for p in (state_files.PAPERS_DIR / sync_overleaf.CONFLICTS).rglob("*.tex"))
    assert [c.split("/", 2)[2] for c in copies] == sorted([BUILT, PROSE])
    held = _in_overleaf(overleaf)
    assert held[PROSE] == "planars-data's\n" and all(held[c] for c in copies)
    [issue] = github.issues
    assert issue["labels"] == [sync_overleaf.LABEL] and all(c in issue["body"] for c in copies)
    assert "zebra" not in issue["body"], "a file's text in a public issue"
    _edit_in_overleaf(overleaf, {c: None for c in copies})
    _run("--apply")
    assert not list((state_files.PAPERS_DIR / sync_overleaf.CONFLICTS).rglob("*.tex"))
    assert github.issue(issue["number"])["state"] == "CLOSED"


def test_a_failed_sync_files_the_issue(overleaf, monkeypatch, github):
    _papers({"volume.yaml": VOLUME.replace(PROJECT, "nosuchproject")})
    with pytest.raises(SystemExit):
        _run("--apply")
    [issue] = github.issues
    assert "Could not reach" in issue["body"]


def test_the_door_writes_over_a_person_s_file_only_in_place_of_what_is_there():
    _papers({PROSE: "theirs\n"})
    args = sync_overleaf.build_parser().parse_args(["--apply"])
    with drive_door.running("sync-overleaf", args):
        with pytest.raises(file_door.DoorViolation):
            file_door.write_paper(file_door.paper_stub(PROSE), "new\n")
        with pytest.raises(file_door.DoorViolation):
            file_door.write_paper(file_door.paper_stub(PROSE), "new\n", replaces="stale\n")
        assert file_door.write_paper(file_door.paper_stub(PROSE), "new\n", replaces="theirs\n")
