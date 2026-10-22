"""file_door.push: a push refused because someone else pushed meanwhile is
replayed on top of theirs (the daily refresh of 2026-10-22 lost its last four
steps when a person pushed while it ran)."""

import subprocess

from coding import file_door


def _git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c",
                           "user.email=t@example.org", *args],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _two_clones(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True,
                   capture_output=True)
    a, b = tmp_path / "a", tmp_path / "b"
    for clone in (a, b):
        subprocess.run(["git", "clone", str(remote), str(clone)], check=True,
                       capture_output=True)
        _git(clone, "config", "user.name", "t")
        _git(clone, "config", "user.email", "t@example.org")
    (a / "start.txt").write_text("start\n")
    _git(a, "add", "start.txt")
    _git(a, "commit", "-m", "start")
    _git(a, "push", "-u", "origin", "main")
    _git(b, "pull", "origin", "main")
    _git(b, "branch", "--set-upstream-to=origin/main", "main")
    return remote, a, b


def _commit(repo, name, text):
    (repo / name).write_text(text)
    _git(repo, "add", name)
    _git(repo, "commit", "-m", name)


def test_a_push_refused_by_someone_elses_push_is_replayed_and_lands(tmp_path):
    remote, a, b = _two_clones(tmp_path)
    _commit(a, "person.txt", "a person's edit\n")
    _git(a, "push")
    _commit(b, "refresh.txt", "the refresh's snapshots\n")

    assert file_door.push(b).returncode == 0
    files = _git(remote, "ls-tree", "--name-only", "main").split()
    assert {"person.txt", "refresh.txt"} <= set(files)


def test_a_replay_that_conflicts_is_undone_and_the_commit_kept(tmp_path):
    remote, a, b = _two_clones(tmp_path)
    _commit(a, "same.txt", "theirs\n")
    _git(a, "push")
    _commit(b, "same.txt", "ours\n")
    ours = _git(b, "rev-parse", "HEAD")

    assert file_door.push(b).returncode != 0
    assert _git(b, "rev-parse", "HEAD") == ours
    assert _git(b, "status", "--porcelain") == ""
