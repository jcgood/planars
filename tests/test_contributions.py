"""chapters/contributions.py: the counts of what people and Claude did."""

import subprocess
from datetime import datetime, timezone

import pytest

from chapters import contributions as c

CUTOFF = datetime(2026, 11, 1, tzinfo=timezone.utc)
PEOPLE = {"jcgood": "Jeff Good", "ajrtallman": "Adam Tallman"}


@pytest.mark.parametrize("value, model", [
    ("Claude Opus 5.5 <noreply@anthropic.com>", "Claude Opus 5.5"),
    ("Claude Opus 5.5 (1M context) <noreply@anthropic.com>", "Claude Opus 5.5"),
    ("Claude <noreply@anthropic.com>", "Claude"),
    ("Adam Tallman <adam@example.org>", None),
])
def test_claude_model(value, model):
    assert c.claude_model(value) == model


@pytest.mark.parametrize("body", [
    "Done.\n\n---\n*klᴐd*",
    "Done.\n\n— klᴐd",
    "Done. (klᴐd)",
    "klᴐd: Duplicate of #267.",
    "*Drafted by klɑd*",
    "Reply.\r\n\r\n---\r\n*klod*\r\n",
])
def test_signed(body):
    assert c.is_signed(body)


@pytest.mark.parametrize("body", [
    'We used "klod\'s compromise" here.',
    "> *klᴐd*\n\nI disagree with the above.",
    "No signature at all.",
])
def test_not_signed(body):
    assert not c.is_signed(body)


def _commit(day, author="jcgood", co=()):
    return {"when": datetime(2026, 3, day, tzinfo=timezone.utc), "author": author,
            "co_authors": list(co)}


def test_commit_values():
    values = c.commit_values([
        _commit(1),
        _commit(2, co=["Claude Sonnet 4.6 <noreply@anthropic.com>"]),
        _commit(3, co=["Claude Opus 5.5 <noreply@anthropic.com>"]),
        _commit(4, co=["Claude Sonnet 4.6 <noreply@anthropic.com>"]),
        _commit(5, author="github-actions[bot]"),
    ])
    assert values == {
        "commits.total": 5, "commits.claude": 3, "commits.pipeline": 1, "commits.people": 1,
        "commits.first_claude": "2026-03-02",
        "commits.models": "Claude Sonnet 4.6; Claude Opus 5.5",
        "commits.model.claude_sonnet_4_6": 2, "commits.model.claude_opus_5_5": 1,
    }


def test_comment_values_by_account_and_cutoff():
    comments = [
        {"created_at": "2026-10-01T00:00:00Z", "login": "jcgood", "body": "x\n---\n*klᴐd*"},
        {"created_at": "2026-10-01T00:00:00Z", "login": "ajrtallman", "body": "x\n---\n*klod*"},
        {"created_at": "2026-10-01T00:00:00Z", "login": "ajrtallman", "body": "plain"},
        {"created_at": "2026-10-01T00:00:00Z", "login": "github-actions[bot]", "body": "*klᴐd*"},
        {"created_at": "2026-10-01T00:00:00Z", "login": "stranger", "body": "hi"},
        {"created_at": "2026-12-01T00:00:00Z", "login": "jcgood", "body": "after the cut-off"},
    ]
    values = c.comment_values(comments, CUTOFF, PEOPLE)
    assert values == {
        "comments.total": 5, "comments.pipeline": 1, "comments.unlisted": 1,
        "comments.claude": 2, "comments.claude.jeff_good": 1, "comments.claude.adam_tallman": 1,
        "comments.people": 1, "comments.people.jeff_good": 0, "comments.people.adam_tallman": 1,
    }


LOG = ("date\tissue\tdecided by\tdecision\tscope\n"
       "2026-10-01\t#1\tAdam Tallman\tA\t\n"
       "2026-10-02\t#2\tJeff Good; Adam Tallman\tB\t\n"
       "2026-12-01\t#3\tJeff Good\tafter the cut-off\t\n")


def test_decision_values():
    values = c.decision_values([LOG], CUTOFF, PEOPLE.values())
    assert values == {"decisions.total": 2, "decisions.jeff_good": 1, "decisions.adam_tallman": 2}


def test_decision_by_unknown_name_refused():
    with pytest.raises(c.ContributionsError, match="not in people.yaml"):
        c.decision_values(["date\tissue\tdecided by\tdecision\tscope\n2026-10-01\t#1\tKlod\tA\t\n"],
                          CUTOFF, PEOPLE.values())


def _git(repo, *args, date="2026-03-10T12:00:00Z"):
    env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "HOME": str(repo),
           "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def test_contribution_values_end_to_end(tmp_path, monkeypatch, github):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "jcgood")
    _git(repo, "config", "user.email", "jeff@example.org")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "by hand")
    # A cloud session's commit: the Claude-Session line keeps git from
    # reading Co-Authored-By as a trailer, and it must still count.
    _git(repo, "commit", "-q", "--allow-empty", "-m",
         "with Claude\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n"
         "Claude-Session: https://claude.ai/code/session_x")
    _git(repo, "commit", "-q", "--allow-empty", "-m",
         "later\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", date="2026-12-01T00:00:00Z")
    github.posted_comments = [
        {"created_at": "2026-10-01T00:00:00Z", "login": "jcgood", "body": "x\n---\n*klᴐd*"}]
    monkeypatch.setattr(c, "_github_people", lambda: PEOPLE)
    monkeypatch.setattr(c, "_decision_logs", lambda: [LOG])
    monkeypatch.setattr("coding.people.known_names", lambda: list(PEOPLE.values()))

    values = c.contribution_values("2026-11-01T00:00:00Z", repo=repo)

    p = c.PREFIX
    assert values[p + "until"] == "2026-11-01T00:00:00Z"
    assert values[p + "commits.total"] == 2
    assert values[p + "commits.claude"] == 1
    assert values[p + "commits.models"] == "Claude Opus 5"
    assert values[p + "comments.claude.jeff_good"] == 1
    assert values[p + "decisions.total"] == 2
    from chapters.tex import check_value_name
    for key in values:
        check_value_name(key)


def test_github_unreachable_refuses(github):
    github.signed_in = False
    with pytest.raises(c.ContributionsError, match="gh auth login"):
        c.contribution_values()
