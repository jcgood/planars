"""The one way the tooling files, finds, comments on and closes GitHub issues.

    python -m coding issue --file LABEL --title TITLE --body-file BODY.md [--replace]
    python -m coding issue --close LABEL --message TEXT
    python -m coding issue --remind LABEL --older-than-days 7 --message TEXT
    python -m coding issue --sync-labels [--apply]
    python -m coding issue --write-label-table

Phase 10 unit 10 (issue #271). Before this, seven Python functions and a
shell script each had their own copy of "is gh signed in, is an issue with
this label open, comment on it or create one", and two workflows had more
inline. (The daily refresh's issue steps, which then called this module from
the workflow file, are in coding/daily_refresh.py since unit 8.) They had drifted: some commented on the open issue, some replaced its
body; one asked gh for the repository, the rest assumed it; one created issues
with no label at all. And nothing checked a label against anything, so a
misspelt one would quietly create a new label on GitHub.

What lives here:

- **The label registry**, `schemas/issue_labels.yaml`, is read on every call.
  Every function that takes a label refuses one not listed there
  (`UnknownLabel`), and `create` makes a registered label GitHub doesn't
  have yet (`ensure_label`). `--sync-labels --apply` brings GitHub's own labels into
  line with it (the daily refresh's first step), and `--write-label-table`
  rewrites the Labels table in CLAUDE.md from it (run by the pre-commit hook
  whenever the registry is committed). So the registry is the one place a
  label is defined; GitHub's copy and CLAUDE.md's copy are rebuilt from it.

- **The GitHub door.** Every call to GitHub goes through one object
  (`get_github()`): `GhCli` runs the `gh` program; `tests/fake_github.py` is an
  in-memory stand-in for tests, installed with `set_github()` — the same
  arrangement the Drive doorway uses for Google.

- **The operations callers use**: `find_open`, `file_issue` (comment on the
  open issue, or replace its title and body, or create one), `create`,
  `comment`, `close_open`, `remind_stale`, `last_closed`, `is_open`, `body_of`.

Choosing *which* issue a caller means stays with the caller, because it is a
fact about that caller: `check-notes` keeps one issue per annotator by stored
number, `notify.py` one per language, `generate-sheets` one per exact title,
everything else one per label.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = ROOT / "schemas" / "issue_labels.yaml"
CLAUDE_MD_PATH = ROOT / "CLAUDE.md"
REPO = "jcgood/planars"

TABLE_START = "<!-- label-table:start — generated from schemas/issue_labels.yaml by `python -m coding issue --write-label-table`; edit that file, not this table -->"
TABLE_END = "<!-- label-table:end -->"


class UnknownLabel(ValueError):
    """A label that schemas/issue_labels.yaml does not list."""


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

def load_labels(path: Path = LABELS_PATH) -> List[Dict]:
    """The registry's entries, in file order. Read fresh every call."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    labels = data.get("labels") or []
    required = ("name", "color", "description", "meaning", "filed_by")
    seen = set()
    for entry in labels:
        missing = [f for f in required if not str(entry.get(f) or "").strip()]
        if missing:
            raise ValueError(f"{path.name}: label {entry.get('name')!r} is missing {missing}")
        if entry["name"] in seen:
            raise ValueError(f"{path.name}: label {entry['name']!r} is listed twice")
        if len(entry["description"]) > 100:
            raise ValueError(f"{path.name}: {entry['name']!r} description is over "
                             "GitHub's 100-character limit")
        seen.add(entry["name"])
    return labels


def check_label(label: str) -> str:
    """Return `label` if the registry lists it; otherwise raise UnknownLabel."""
    names = [entry["name"] for entry in load_labels()]
    if label not in names:
        raise UnknownLabel(
            f"GitHub label {label!r} is not in schemas/issue_labels.yaml. "
            f"Add it there (and commit) before filing issues under it. "
            f"Known labels: {', '.join(names)}")
    return label


def label_table(labels: Optional[List[Dict]] = None) -> str:
    """CLAUDE.md's Labels table, built from the registry."""
    labels = load_labels() if labels is None else labels
    rows = ["| Label | Filed by | Meaning |", "|-------|----------|---------|"]
    for entry in labels:
        meaning = " ".join(str(entry["meaning"]).split()).replace("|", "\\|")
        rows.append(f"| `{entry['name']}` | {entry['filed_by']} | {meaning} |")
    return "\n".join(rows)


def with_label_table(text: str, labels: Optional[List[Dict]] = None) -> str:
    """`text` (CLAUDE.md) with the generated table between its markers."""
    if TABLE_START not in text or TABLE_END not in text:
        raise ValueError("CLAUDE.md has lost its label-table markers; restore them "
                         f"around the Labels table:\n  {TABLE_START}\n  {TABLE_END}")
    before, rest = text.split(TABLE_START, 1)
    _, after = rest.split(TABLE_END, 1)
    return f"{before}{TABLE_START}\n{label_table(labels)}\n{TABLE_END}{after}"


# ---------------------------------------------------------------------------
# The GitHub door
# ---------------------------------------------------------------------------

class GitHub(Protocol):
    """Everything the tooling asks of GitHub. `GhCli` is the live one."""

    def available(self) -> bool: ...
    def list_issues(self, label: str, state: str = "open") -> List[Dict]: ...
    def get_issue(self, number: int) -> Optional[Dict]: ...
    def create_issue(self, title: str, label: str, body: str) -> int: ...
    def edit_issue(self, number: int, title: Optional[str], body: Optional[str]) -> None: ...
    def comment(self, number: int, body: str) -> None: ...
    def close_issue(self, number: int) -> None: ...
    def list_labels(self) -> List[Dict]: ...
    def create_label(self, name: str, color: str, description: str) -> None: ...
    def edit_label(self, name: str, color: str, description: str) -> None: ...
    def delete_label(self, name: str) -> None: ...


class GhCli:
    """GitHub through the `gh` program. Bodies always go via a file."""

    def _run(self, args: List[str], body: Optional[str] = None) -> str:
        cmd = ["gh", *args, "--repo", REPO]
        body_path = None
        if body is not None:
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                             encoding="utf-8") as f:
                f.write(body)
                body_path = f.name
            cmd += ["--body-file", body_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        finally:
            if body_path:
                Path(body_path).unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"`gh {' '.join(args[:2])}` failed: "
                               f"{(result.stderr or result.stdout).strip()}")
        return result.stdout

    def available(self) -> bool:
        try:
            return subprocess.run(["gh", "auth", "status"],
                                  capture_output=True).returncode == 0
        except OSError:
            return False

    def list_issues(self, label: str, state: str = "open") -> List[Dict]:
        out = self._run(["issue", "list", "--label", label, "--state", state,
                         "--limit", "1000", "--json", "number,title,state,createdAt,closedAt"])
        return json.loads(out or "[]")

    def get_issue(self, number: int) -> Optional[Dict]:
        try:
            out = self._run(["issue", "view", str(number),
                             "--json", "number,title,state,body"])
        except RuntimeError:
            return None
        return json.loads(out)

    def create_issue(self, title: str, label: str, body: str) -> int:
        out = self._run(["issue", "create", "--title", title, "--label", label], body=body)
        return int(out.strip().rstrip("/").rsplit("/", 1)[-1])

    def edit_issue(self, number: int, title: Optional[str], body: Optional[str]) -> None:
        args = ["issue", "edit", str(number)]
        if title is not None:
            args += ["--title", title]
        self._run(args, body=body)

    def comment(self, number: int, body: str) -> None:
        self._run(["issue", "comment", str(number)], body=body)

    def close_issue(self, number: int) -> None:
        self._run(["issue", "close", str(number)])

    def list_labels(self) -> List[Dict]:
        out = self._run(["label", "list", "--limit", "1000",
                         "--json", "name,color,description"])
        return json.loads(out or "[]")

    def create_label(self, name: str, color: str, description: str) -> None:
        self._run(["label", "create", name, "--color", color,
                   "--description", description])

    def edit_label(self, name: str, color: str, description: str) -> None:
        self._run(["label", "edit", name, "--color", color,
                   "--description", description])

    def delete_label(self, name: str) -> None:
        self._run(["label", "delete", name, "--yes"])


_github: Optional[GitHub] = None


def get_github() -> GitHub:
    global _github
    if _github is None:
        _github = GhCli()
    return _github


def set_github(github: Optional[GitHub]) -> None:
    global _github
    _github = github


def reset_github() -> None:
    set_github(None)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def available() -> bool:
    """Whether GitHub can be reached (gh installed and signed in)."""
    return get_github().available()


def find_open(label: str, title: Optional[str] = None,
              title_contains: Optional[str] = None) -> Optional[int]:
    """The lowest-numbered open issue under `label`, optionally matching a title."""
    check_label(label)
    for issue in sorted(get_github().list_issues(label), key=lambda i: i["number"]):
        if title is not None and issue["title"] != title:
            continue
        if title_contains is not None and title_contains not in issue["title"]:
            continue
        return issue["number"]
    return None


def is_open(number: int) -> Optional[bool]:
    """True/False if the issue's state is known, None if it could not be read."""
    issue = get_github().get_issue(number)
    return None if issue is None else issue.get("state") == "OPEN"


def body_of(number: int) -> str:
    issue = get_github().get_issue(number)
    return (issue or {}).get("body") or ""


def ensure_label(label: str) -> None:
    """Create `label` on GitHub from its registry entry if GitHub lacks it.

    A label newly added to the registry exists on GitHub only after the next
    daily `--sync-labels --apply`; until then GitHub refuses any issue filed
    under it (sheet-validation's first `needs-fixing` issue crashed that way,
    2026-10-17, #310). Creating it here means filing never waits on the sync.
    """
    gh = get_github()
    if any(l["name"] == label for l in gh.list_labels()):
        return
    entry = next(e for e in load_labels() if e["name"] == label)
    gh.create_label(label, str(entry["color"]), entry["description"])


def create(label: str, title: str, body: str) -> int:
    ensure_label(check_label(label))
    return get_github().create_issue(title, label, body)


def comment(number: int, body: str) -> None:
    get_github().comment(number, body)


def file_issue(label: str, title: str, body: str, *, replace: bool = False,
               match_title: bool = False) -> Tuple[int, bool]:
    """Put `body` in front of whoever watches `label`.

    If an issue under the label is open (with exactly this title, when
    `match_title`), comment on it — or, with `replace`, overwrite its title
    and body so the current state is what a reader sees first. Otherwise
    create one. Returns (issue number, whether it was created).
    """
    number = find_open(label, title=title if match_title else None)
    if number is None:
        return create(label, title, body), True
    if replace:
        get_github().edit_issue(number, title, body)
    else:
        comment(number, body)
    return number, False


def close_open(label: str, message: str) -> List[int]:
    """Comment `message` on every open issue under `label` and close it."""
    check_label(label)
    closed = []
    for issue in get_github().list_issues(label):
        comment(issue["number"], message)
        get_github().close_issue(issue["number"])
        closed.append(issue["number"])
    return closed


def close(number: int, message: Optional[str] = None) -> None:
    if message:
        comment(number, message)
    get_github().close_issue(number)


def last_closed(label: str) -> Optional[datetime]:
    """When the most recently closed issue under `label` was closed, or None."""
    check_label(label)
    times = [datetime.fromisoformat(i["closedAt"].replace("Z", "+00:00"))
             for i in get_github().list_issues(label, state="closed") if i.get("closedAt")]
    return max(times, default=None)


def remind_stale(label: str, older_than_days: int, message: str,
                 now: Optional[datetime] = None) -> List[int]:
    """Comment `message` on each open issue under `label` older than the limit."""
    check_label(label)
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=older_than_days)
    reminded = []
    for issue in get_github().list_issues(label):
        created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
        if created < cutoff:
            comment(issue["number"], message)
            reminded.append(issue["number"])
    return reminded


# ---------------------------------------------------------------------------
# Keeping GitHub's labels in line with the registry
# ---------------------------------------------------------------------------

def label_plan(registry: List[Dict], live: List[Dict],
               in_use: Dict[str, int]) -> List[Tuple[str, str, str]]:
    """What it takes to make GitHub's labels match the registry.

    Returns (action, name, reason) triples. Action is "create", "edit",
    "delete" (a label the registry doesn't list and no issue carries) or
    "refuse" (one the registry doesn't list that issues still carry — it
    needs adding to the registry, or removing from those issues, by a person).
    """
    live_by_name = {l["name"]: l for l in live}
    plan = []
    for entry in registry:
        current = live_by_name.get(entry["name"])
        color = str(entry["color"]).lower()
        if current is None:
            plan.append(("create", entry["name"], "listed in the registry, missing on GitHub"))
        elif (current.get("color", "").lower() != color
              or (current.get("description") or "") != entry["description"]):
            plan.append(("edit", entry["name"], "colour or description differs"))
    registered = {e["name"] for e in registry}
    for name in sorted(set(live_by_name) - registered):
        if in_use.get(name, 0):
            plan.append(("refuse", name, f"on GitHub and on {in_use[name]} issue(s), "
                                         "but not in schemas/issue_labels.yaml"))
        else:
            plan.append(("delete", name, "on GitHub, on no issue, not in the registry"))
    return plan


def sync_labels(apply: bool) -> List[str]:
    """Print (and with `apply`, carry out) the label plan.

    Returns the labels it could not fix (in use on GitHub, not registered).
    With `apply` those are reported in a `label-drift` issue, which is closed
    again once there are none — so the daily run needs no other step.
    """
    gh = get_github()
    registry = load_labels()
    live = gh.list_labels()
    registered = {e["name"] for e in registry}
    in_use = {l["name"]: len(gh.list_issues(l["name"], state="all"))
              for l in live if l["name"] not in registered}
    plan = label_plan(registry, live, in_use)
    by_name = {e["name"]: e for e in registry}
    for action, name, reason in plan:
        verb = {"create": "Create", "edit": "Update", "delete": "Delete",
                "refuse": "CANNOT FIX"}[action]
        print(f"  {verb if apply or action == 'refuse' else 'Would ' + verb.lower()} "
              f"label {name!r}: {reason}")
        if not apply:
            continue
        entry = by_name.get(name)
        if action == "create":
            gh.create_label(name, str(entry["color"]), entry["description"])
        elif action == "edit":
            gh.edit_label(name, str(entry["color"]), entry["description"])
        elif action == "delete":
            gh.delete_label(name)
    refused = [name for action, name, _ in plan if action == "refuse"]
    if not plan:
        print("GitHub labels match schemas/issue_labels.yaml.")
    elif not apply:
        print("Dry run — re-run with --apply to change GitHub.")
    if apply:
        if refused:
            body = ("These labels are on GitHub issues but not in "
                    "`schemas/issue_labels.yaml`, so the tooling cannot keep them "
                    "in line:\n\n"
                    + "\n".join(f"- `{name}` ({in_use[name]} issue(s))" for name in refused)
                    + "\n\nAdd each one to `schemas/issue_labels.yaml` and commit, "
                    "or take it off those issues. This issue closes by itself once "
                    "every label in use is registered.\n")
            file_issue("label-drift", "GitHub labels missing from schemas/issue_labels.yaml",
                       body, replace=True)
        else:
            close_open("label-drift", "Every label in use is registered — closing.")
    return refused


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding issue`."""
    ap = argparse.ArgumentParser(
        description="File, close or remind on labelled GitHub issues; keep labels in "
                    "line with schemas/issue_labels.yaml.")
    action = ap.add_mutually_exclusive_group(required=True)
    action.add_argument("--file", metavar="LABEL",
                        help="comment on the open issue under LABEL, or create one")
    action.add_argument("--close", metavar="LABEL",
                        help="comment --message on every open issue under LABEL and close it")
    action.add_argument("--remind", metavar="LABEL",
                        help="comment --message on open issues under LABEL older than "
                             "--older-than-days")
    action.add_argument("--sync-labels", action="store_true",
                        help="make GitHub's labels match the registry (dry run without --apply)")
    action.add_argument("--write-label-table", action="store_true",
                        help="rewrite the Labels table in CLAUDE.md from the registry")
    ap.add_argument("--title", help="issue title (--file)")
    ap.add_argument("--body-file", type=Path, metavar="BODY.md", help="issue body (--file)")
    ap.add_argument("--replace", action="store_true",
                    help="--file: overwrite the open issue's title and body instead of commenting")
    ap.add_argument("--message", help="comment text (--close, --remind)")
    ap.add_argument("--older-than-days", type=int, default=7, metavar="N",
                    help="--remind: only issues open longer than N days (default 7)")
    ap.add_argument("--apply", action="store_true", help="--sync-labels: change GitHub")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    ap = build_parser()
    if args is None:
        args = ap.parse_args()

    if args.write_label_table:
        text = CLAUDE_MD_PATH.read_text(encoding="utf-8")
        new = with_label_table(text)
        if new != text:
            CLAUDE_MD_PATH.write_text(new, encoding="utf-8")
            print("CLAUDE.md label table rewritten from schemas/issue_labels.yaml.")
        else:
            print("CLAUDE.md label table already matches schemas/issue_labels.yaml.")
        return

    if args.sync_labels:
        sync_labels(args.apply)
        return

    if args.file:
        if not args.title or not args.body_file:
            ap.error("--file needs --title and --body-file")
        number, created = file_issue(args.file, args.title,
                                     args.body_file.read_text(encoding="utf-8"),
                                     replace=args.replace)
        print(f"{'Created' if created else 'Updated'} issue #{number} ({args.file}).")
        return

    if not args.message:
        ap.error("--close and --remind need --message")
    if args.close:
        closed = close_open(args.close, args.message)
        print(f"Closed {', '.join(f'#{n}' for n in closed)}." if closed
              else f"No open {args.close} issue to close.")
    else:
        reminded = remind_stale(args.remind, args.older_than_days, args.message)
        print(f"Reminded on {', '.join(f'#{n}' for n in reminded)}." if reminded
              else f"No {args.remind} issue older than {args.older_than_days} days.")


if __name__ == "__main__":
    main()
