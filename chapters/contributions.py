"""Who did what in the project, people and Claude, counted as named values.

``contribution_values(until)`` is item 8 of docs/zenodo-report-plan.md
("Human and Claude contributions"): the counts a report's contributions
section cites, read from records the project already keeps, never typed
from recollection. ``until`` is a UTC time (ISO 8601); the report passes the
time of its data position's change-log line, so every count stops where the
data does. None counts everything so far. Nothing here writes anything.

Every key starts with ``project.contributions.``. The groups:

- ``until``: the cut-off, as given (or the time the counts were made);
- ``commits.*``: this checkout's commits (``git log HEAD``, merges left out,
  by commit time): ``total``; ``claude`` (made in a Claude session: a
  ``Co-Authored-By:`` line naming Claude anywhere in the message, not only
  where git reads trailers); ``pipeline`` (made by the
  tooling's own runs, an author ending ``[bot]``); ``people`` (the rest);
  ``first_claude`` (the day of the first Claude commit);
  ``models`` (every model the lines name, "; " between them, oldest first)
  and ``model.<slug>`` (commits naming each; a line naming no model is
  counted as ``Claude``);
- ``comments.*``: comments on the GitHub issues and pull requests
  (``coding.issues.list_comments``): ``total``; ``pipeline`` (posted by a
  ``[bot]`` account: the daily refresh and the other workflows); ``claude``
  (posted from a person's account and signed by their Claude, ``SIGNATURE``)
  and ``claude.<person>`` for each; ``people`` (unsigned, from a person's
  account) and ``people.<person>``; ``unlisted`` (from an account in no
  one's ``github:`` in people.yaml). Whose Claude signed is read from the
  account it posted from, not the signature's spelling: the spellings
  changed over the year (see ``SIGNATURE``);
- ``decisions.*``: lines in the decision logs (``coding.decisions``: the
  framework's and each language's) dated on or before ``until``: ``total``
  and ``<person>`` for each name in ``decided by``.

``<person>`` is the person's name in people.yaml in lower case, words joined
by ``_`` (``jeff_good``). Annotation drafted with Claude is counted per
language by chapters.data (``<L>.annotation.claude_drafts``), at the
language's data position.

The counts come from the repository's history and its GitHub issues, which
the software record on Zenodo (an archive of the files at one tag) does not
carry; to rebuild them, read the GitHub repository at the same ``until``.
A commit line means "made in a Claude session", not a share of authorship.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "project.contributions."

# A Claude's signature on a GitHub comment, in the forms used so far: a line
# holding only the name, with any of "*", "—", "-", "(", ")" and "Drafted by"
# around it; a line starting "klᴐd:"; or a line ending "(klᴐd)" or
# "— klᴐd". The spellings: "klᴐd" (Jeff's Claude since 2026-07-30), "klod"
# (Adam's; Jeff's before then too), "klɑd" (an early mistranscription, July
# 2026). A name mentioned in a sentence ("klod's compromise") or in a quoted
# line ("> *klᴐd*") is not a signature.
SIGNATURE_NAMES = ("klᴐd", "klod", "klɑd")
_NAMES = "|".join(SIGNATURE_NAMES)
SIGNATURE = re.compile(
    rf"^[ \t*—\-()]*(?:drafted by\s+)?(?:{_NAMES})[ \t*—\-()]*$"
    rf"|^[ \t]*\**(?:{_NAMES}):"
    rf"|^(?![ \t]*>).*(?:\(|—[ \t]*)\**(?:{_NAMES})\**\)?[ \t*]*$",
    re.IGNORECASE | re.MULTILINE)

_CO_AUTHOR_LINE = re.compile(r"^\s*Co-Authored-By:(.*)$", re.IGNORECASE | re.MULTILINE)
_CO_AUTHOR = re.compile(r"^\s*Claude\b(.*?)\s*(<[^>]*>)?\s*$")
_FIELD, _RECORD = "\x1f", "\x1e"


class ContributionsError(Exception):
    """A record the counts need can't be read; the message says why."""


def person_key(name: str) -> str:
    """A name from people.yaml as it appears in a value name."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _cutoff(until: Optional[str]) -> datetime:
    if until is None:
        return datetime.now(timezone.utc)
    try:
        when = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError:
        raise ContributionsError(f"until {until!r} is not a time (write e.g. 2026-11-25T12:00:00Z).")
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


# ── Commits ─────────────────────────────────────────────────────────────────

def _commits(cutoff: datetime, repo: Path) -> list[dict]:
    """[{when, author, co_authors}] for HEAD's commits at or before `cutoff`."""
    # The whole message, not git's trailer parsing: a cloud session's commits
    # end with a Claude-Session: line that stops git reading the
    # Co-Authored-By line as a trailer (14 commits, 2026-09).
    fmt = _FIELD.join(["%cI", "%an", "%B"])
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "HEAD", "--no-merges",
         f"--until={cutoff.isoformat()}", f"--format={fmt}{_RECORD}"],
        capture_output=True, text=True)
    if result.returncode != 0:
        raise ContributionsError(f"git log failed in {repo}: {result.stderr.strip()}")
    out = []
    for record in result.stdout.split(_RECORD):
        record = record.strip("\n")
        if not record:
            continue
        when, author, message = record.split(_FIELD)
        out.append({"when": datetime.fromisoformat(when), "author": author,
                    "co_authors": [m.strip() for m in _CO_AUTHOR_LINE.findall(message)]})
    return out


def claude_model(co_author: str) -> Optional[str]:
    """The model a Co-Authored-By value names ("Claude Opus 5.5"), "Claude"
    when it names Claude and no model, None when it isn't Claude. A note in
    brackets after the model ("(1M context)", a setting of the same model)
    is dropped."""
    match = _CO_AUTHOR.match(co_author)
    if not match:
        return None
    model = re.sub(r"\s*\([^)]*\)", "", match.group(1)).strip()
    return f"Claude {model}".strip()


def commit_values(commits: Iterable[dict]) -> dict:
    total, claude, pipeline, first = 0, 0, 0, None
    models: Counter = Counter()
    first_seen: dict = {}
    for commit in sorted(commits, key=lambda c: c["when"]):
        total += 1
        named = [m for m in map(claude_model, commit["co_authors"]) if m]
        if named:
            claude += 1
            first = first or commit["when"]
            for model in dict.fromkeys(named):
                models[model] += 1
                first_seen.setdefault(model, commit["when"])
        elif commit["author"].endswith("[bot]"):
            pipeline += 1
    order = sorted(models, key=lambda m: first_seen[m])
    values = {"commits.total": total, "commits.claude": claude, "commits.pipeline": pipeline,
              "commits.people": total - claude - pipeline,
              "commits.first_claude": first.date().isoformat() if first else "",
              "commits.models": "; ".join(order)}
    values.update({f"commits.model.{person_key(m)}": models[m] for m in order})
    return values


# ── Comments ────────────────────────────────────────────────────────────────

def is_signed(body: str) -> bool:
    """Whether a comment carries a Claude's signature (``SIGNATURE``)."""
    return bool(SIGNATURE.search((body or "").replace("\r\n", "\n").replace("\r", "\n")))


def comment_values(comments: Iterable[dict], cutoff: datetime, people: dict) -> dict:
    """`people`: GitHub username -> name in people.yaml."""
    counts: Counter = Counter()
    for comment in comments:
        if _cutoff(comment["created_at"]) > cutoff:
            continue
        counts["total"] += 1
        login = comment.get("login") or ""
        if login.endswith("[bot]"):
            counts["pipeline"] += 1
        elif login not in people:
            counts["unlisted"] += 1
        elif is_signed(comment.get("body") or ""):
            counts["claude"] += 1
            counts[f"claude.{person_key(people[login])}"] += 1
        else:
            counts["people"] += 1
            counts[f"people.{person_key(people[login])}"] += 1
    values = {f"comments.{k}": 0 for k in ("total", "pipeline", "claude", "people", "unlisted")}
    for name in people.values():
        values[f"comments.claude.{person_key(name)}"] = 0
        values[f"comments.people.{person_key(name)}"] = 0
    values.update({f"comments.{k}": v for k, v in counts.items()})
    return values


def _github_people() -> dict:
    from coding.people import github_for, known_names
    return {login: name for name in known_names() if (login := github_for(name))}


# ── Decisions ───────────────────────────────────────────────────────────────

def decision_values(logs: Iterable[str], cutoff: datetime, names: Iterable[str]) -> dict:
    """`logs`: the decision logs' texts; `names`: everyone in people.yaml."""
    from coding.decisions import NAME_SEPARATOR, _rows
    values = {"decisions.total": 0, **{f"decisions.{person_key(n)}": 0 for n in names}}
    day = cutoff.date().isoformat()
    for text in logs:
        for row in _rows(text):
            if (row.get("date") or "") > day:
                continue
            values["decisions.total"] += 1
            for name in (row.get("decided by") or "").split(NAME_SEPARATOR.strip()):
                if name.strip():
                    key = f"decisions.{person_key(name.strip())}"
                    if key not in values:
                        raise ContributionsError(
                            f"A decision log names {name.strip()!r}, who is not in "
                            f"people.yaml; correct the line (record-decision checks names).")
                    values[key] += 1
    return values


def _decision_logs() -> list:
    from coding import decisions, file_door
    texts = [decisions._framework_text()]
    texts += [file_door.read(file_door.decisions(lang)) for lang in file_door.language_ids()]
    return [t for t in texts if t]


# ── The one entry point ─────────────────────────────────────────────────────

def contribution_values(until: Optional[str] = None, repo: Path = ROOT) -> dict:
    """Every contribution count up to `until` (module docstring)."""
    from coding import issues
    from coding.people import known_names
    cutoff = _cutoff(until)
    try:
        comments = issues.list_comments()
    except RuntimeError as e:
        raise ContributionsError(str(e))
    values = {"until": until or cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")}
    values.update(commit_values(_commits(cutoff, repo)))
    values.update(comment_values(comments, cutoff, _github_people()))
    values.update(decision_values(_decision_logs(), cutoff, known_names()))
    return {PREFIX + k: v for k, v in values.items()}


def main(argv: list[str] | None = None) -> None:
    """``python -m chapters contributions [--until TIME]``: print the counts."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(prog="python -m chapters contributions",
                                     description="Print the contribution counts a report cites "
                                                 "(chapters/contributions.py). Writes nothing.")
    parser.add_argument("--until", default=None, metavar="TIME",
                        help="Count up to this UTC time, e.g. 2026-11-25T12:00:00Z (default: now).")
    args = parser.parse_args(argv)
    try:
        values = contribution_values(args.until)
    except ContributionsError as e:
        sys.exit(str(e))
    for key in sorted(values):
        print(f"{key}\t{values[key]}")
