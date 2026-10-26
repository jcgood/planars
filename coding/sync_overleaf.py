"""``python -m coding sync-overleaf``: keep the chapters' Overleaf project and
planars-data's ``.papers/`` the same, both ways.

    python -m coding sync-overleaf            # dry run: what would move which way
    python -m coding sync-overleaf --apply

The Overleaf project is named in ``.papers/volume.yaml`` (``overleaf:`` and
the project's ID, the last part of its address); with none, there is
nothing to sync. Each Overleaf project is a git repository
(``https://git.overleaf.com/<ID>``), which this command clones into a
temporary folder each run. On the machine of whoever runs it, git's own
stored login is used; elsewhere (the daily refresh) an Overleaf git token in
``OVERLEAF_TOKEN``, passed to git through its environment, never its
command line.

**How each file is settled.** The command compares three versions of every
file: what Overleaf has, what ``.papers/`` has (files compiling leaves are
left out, as planars-data's .gitignore says), and what both had at the last
sync (the Overleaf version recorded in ``.state/overleaf_state.json``):

- changed on one side only: that side's version goes to the other (a file
  added or deleted counts as a change);
- changed on both sides, differently: ``.papers/``'s version is kept, and
  Overleaf's goes in as a copy at ``conflicts/<date>/<path>`` on both sides;
- a file the chapter build makes (``chapters.build.is_built``) changed in
  Overleaf: the built version is kept (the next build would replace the
  edit anyway), and Overleaf's goes in as a copy the same way. Generated
  text is changed in the templates or the data, never in Overleaf.

So nothing anyone wrote is lost; a copy is a question for a person. Files
taken from Overleaf are written through the local-file door, which writes
over a person's file only when told exactly what it replaces (the version
here, which the sync has just seen unchanged since the last sync), and
commits and pushes them when the command ends. Then ``.papers/`` as it now
stands is pushed to Overleaf, and the Overleaf version recorded.

**The first sync** with a project (none recorded, or a different one)
treats Overleaf's content as unchanged since a sync, so ``.papers/`` replaces
it: start from a new, empty project.

**Its issue** (``overleaf-sync``, one, rewritten in place): with
``--apply``, filed while ``conflicts/`` holds any copy or when the sync
failed (Overleaf unreachable, a push refused because someone edited in the
meantime: the next run picks that up). It names files, never their text
(the repository is public). Closed when ``conflicts/`` is empty and the
sync succeeded.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from . import file_door, issues, state_files

# Where Overleaf's git repositories are; a project's is this plus its ID.
OVERLEAF_GIT = "https://git.overleaf.com/"
TOKEN_ENV = "OVERLEAF_TOKEN"
VOLUME_KEY = "overleaf"
CONFLICTS = "conflicts"
LABEL = "overleaf-sync"
TITLE = "Overleaf sync — chapters"
_PROJECT_ID = re.compile(r"^[0-9a-z]+$")


class SyncError(Exception):
    """A sync that could not finish; its message says why."""


# ── Overleaf's side ────────────────────────────────────────────────────────

def _env() -> Dict[str, str]:
    """git's environment: the token, when there is one, as an HTTP header
    set through git's environment-config variables (not on the command line,
    where other processes could read it)."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    token = os.environ.get(TOKEN_ENV)
    if token:
        login = base64.b64encode(f"git:{token}".encode()).decode()
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.extraHeader",
                   GIT_CONFIG_VALUE_0=f"Authorization: Basic {login}")
    return env


def _git(repo: Optional[Path], *args: str) -> bytes:
    cmd = ["git"] + (["-C", str(repo)] if repo else []) + list(args)
    run = subprocess.run(cmd, capture_output=True, env=_env())
    if run.returncode != 0:
        said = run.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(f"`git {args[0]}` failed: {said}")
    return run.stdout


def _tree(repo: Path, commit: str) -> Dict[str, bytes]:
    """Every file at ``commit``: {path: content}."""
    names = _git(repo, "ls-tree", "-r", "-z", "--name-only", commit).decode().split("\0")
    return {n: _git(repo, "cat-file", "blob", f"{commit}:{n}") for n in names if n}


def _has_commit(repo: Path, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True).returncode == 0


# ── planars-data's side ────────────────────────────────────────────────────

def project_id() -> Optional[str]:
    """The Overleaf project volume.yaml names, or None."""
    text = file_door.read_paper(file_door.paper_stub("volume.yaml"))
    found = (yaml.safe_load(text) or {}).get(VOLUME_KEY) if text else None
    if found is None:
        return None
    found = str(found).strip().rstrip("/").rsplit("/", 1)[-1]
    if not _PROJECT_ID.match(found):
        raise SyncError(f".papers/volume.yaml: `{VOLUME_KEY}` should be the Overleaf project's "
                        f"ID (the end of its address), not {found!r}.")
    return found


def local_files() -> Dict[str, bytes]:
    """Every file in .papers/ but what planars-data's .gitignore leaves out
    (what compiling leaves behind)."""
    papers = state_files.PAPERS_DIR
    if not papers.is_dir():
        return {}
    names = [str(p.relative_to(papers)) for p in sorted(papers.rglob("*")) if p.is_file()]
    repo = papers.parent
    if names and (repo / ".git").exists():
        ask = subprocess.run(["git", "-C", str(repo), "check-ignore", "--stdin", "-z"],
                             input="\0".join(f"{papers.name}/{n}" for n in names).encode(),
                             capture_output=True)
        ignored = {n.split("/", 1)[1] for n in ask.stdout.decode().split("\0") if n}
        names = [n for n in names if n not in ignored]
    return {n: (papers / n).read_bytes() for n in names}


def read_state() -> dict:
    path = file_door.overleaf_state().path
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# ── Settling each file ─────────────────────────────────────────────────────

def _conflict_path(rel: str, taken: set, today: str) -> str:
    n = 1
    while True:
        folder = f"{CONFLICTS}/{today}" + ("" if n == 1 else f"-{n}")
        path = f"{folder}/{rel}"
        if path not in taken:
            return path
        n += 1


def settle(base: Dict[str, bytes], theirs: Dict[str, bytes], ours: Dict[str, bytes],
           today: str) -> Tuple[Dict[str, Optional[bytes]], List[str], List[str]]:
    """What to write in .papers/ ({path: content, None to delete}), with the
    content each replaces checked by the door; lines saying what happens;
    and the conflict copies made."""
    from chapters.build import is_built
    writes: Dict[str, Optional[bytes]] = {}
    said, copies = [], []
    taken = set(theirs) | set(ours)

    def copy(rel: str, why: str) -> None:
        path = _conflict_path(rel, taken, today)
        taken.add(path)
        writes[path] = theirs[rel]
        copies.append(path)
        said.append(f"{rel}: {why}; Overleaf's version kept as {path}")

    for rel in sorted(set(base) | set(theirs) | set(ours)):
        b, o, l = base.get(rel), theirs.get(rel), ours.get(rel)
        if o == l or o == b:
            continue  # the same, or only .papers/ changed it: pushed below
        built = is_built(rel)
        if l == b:
            if built and o is not None:
                copy(rel, "the build makes this file, and it was edited in Overleaf")
            elif built:
                said.append(f"{rel}: deleted in Overleaf, but the build makes it; put back")
            else:
                writes[rel] = o
                said.append(f"{rel}: {'deleted' if o is None else 'changed'} in Overleaf; "
                            f"taken")
        elif o is None:
            said.append(f"{rel}: deleted in Overleaf but changed here; this version kept")
        elif l is None and not built:
            writes[rel] = o
            said.append(f"{rel}: deleted here but changed in Overleaf; Overleaf's version kept")
        else:
            copy(rel, "changed both here and in Overleaf" if not built else
                 "the build makes this file, and it was edited in Overleaf")
    return writes, said, copies


def _write_local(writes: Dict[str, Optional[bytes]], ours: Dict[str, bytes]) -> None:
    from chapters.build import is_built
    for rel, content in writes.items():
        kind = file_door.paper_built if is_built(rel) else file_door.paper_stub
        if content is None:
            file_door.remove_paper(kind(rel), replaces=ours.get(rel))
        else:
            file_door.write_paper(kind(rel), content, replaces=ours.get(rel))


def _push(clone: Path, files: Dict[str, bytes]) -> Optional[str]:
    """Make the clone hold exactly ``files``, commit and push. The new
    commit, or None when Overleaf already held them."""
    for name in _git(clone, "ls-files", "-z").decode().split("\0"):
        if name:
            (clone / name).unlink(missing_ok=True)
    for rel, content in files.items():
        path = clone / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    _git(clone, "add", "-A")
    if not _git(clone, "status", "--porcelain"):
        return None
    _git(clone, "-c", "user.name=planars", "-c", "user.email=planars@users.noreply.github.com",
         "commit", "--quiet", "-m", "From planars-data's .papers/ (python -m coding sync-overleaf)")
    _git(clone, "push", "--quiet", "origin", "HEAD")
    return _git(clone, "rev-parse", "HEAD").decode().strip()


# ── The issue ──────────────────────────────────────────────────────────────

def issue_body(copies: List[str], failure: Optional[str], today: str) -> str:
    lines = [f"## The chapters' Overleaf project needs a person — {today}", ""]
    if failure:
        lines += ["The sync between planars-data's `.papers/` and the Overleaf project failed:", "",
                  f"```\n{failure}\n```", "",
                  "The next daily refresh tries again; fix the cause if it says one (an expired "
                  f"Overleaf token: make a new one and store it as the `{TOKEN_ENV}` secret).", ""]
    if copies:
        lines += ["A file changed both in Overleaf and in planars-data since the last sync, or a "
                  "file the chapter build makes was edited in Overleaf. The planars-data version "
                  "was kept, and Overleaf's saved as a copy (in both places):", ""]
        lines += [f"- `{c}`" for c in copies]
        lines += ["", "## What to do", "",
                  "For each copy: merge what it adds into the file it copies (the path after "
                  f"`{CONFLICTS}/<date>/`), in Overleaf or locally, then delete the copy. A "
                  "generated file's edit belongs in the prose, the templates or the data instead. "
                  "This issue closes by itself once no copy is left."]
    return "\n".join(lines) + "\n"


def _report(copies: List[str], failure: Optional[str], today: str) -> None:
    if copies or failure:
        number, created = issues.file_issue(LABEL, TITLE, issue_body(copies, failure, today),
                                            replace=True, match_title=True)
        print(f"{'Filed' if created else 'Rewrote'} issue #{number} ({LABEL}).")
        return
    for number in issues.close_open(LABEL, f"Synced with nothing left to settle on {today} — "
                                           f"closing."):
        print(f"Closed issue #{number} ({LABEL}).")


# ── The command ────────────────────────────────────────────────────────────

def sync(apply: bool, today: str) -> List[str]:
    """Sync once; the conflict copies standing afterwards. Raises SyncError."""
    project = project_id()
    if project is None:
        print(f"No Overleaf project named in .papers/volume.yaml (`{VOLUME_KEY}: <project ID>`); "
              f"nothing to sync.")
        return []
    state = read_state()
    with tempfile.TemporaryDirectory() as folder:
        clone = Path(folder) / "overleaf"
        try:
            _git(None, "clone", "--quiet", OVERLEAF_GIT + project, str(clone))
        except SyncError as e:
            hint = "" if os.environ.get(TOKEN_ENV) or not os.environ.get("GITHUB_ACTIONS") else (
                f" No Overleaf login here: store an Overleaf git token as the repository's "
                f"`{TOKEN_ENV}` secret.")
            raise SyncError(f"Could not reach Overleaf project {project}: {e}{hint}") from None
        head = _git(clone, "rev-parse", "HEAD").decode().strip()
        theirs = _tree(clone, head)
        last = state.get("commit") if state.get("project") == project else None
        if last and not _has_commit(clone, last):
            raise SyncError(f"Overleaf's history no longer has the version last synced "
                            f"({last[:12]}); the project's history was rewritten.")
        base = _tree(clone, last) if last else theirs
        if not last:
            print("First sync with this project: .papers/ replaces what it holds.")
        ours = local_files()
        writes, said, copies = settle(base, theirs, ours, today)
        print("\n".join(said) if said else "Nothing changed in Overleaf since the last sync.")
        after = {**ours, **{k: v for k, v in writes.items() if v is not None}}
        for rel in [k for k, v in writes.items() if v is None]:
            after.pop(rel, None)
        sent = sorted(rel for rel in after if theirs.get(rel) != after[rel])
        gone = sorted(rel for rel in theirs if rel not in after)
        print(f"To Overleaf: {len(sent)} file(s) new or changed, {len(gone)} deleted.")
        if not apply:
            if writes or sent or gone:
                print("Dry run: add --apply to sync.")
            return sorted(r for r in after if r.startswith(f"{CONFLICTS}/"))
        _write_local(writes, ours)
        pushed = _push(clone, after)
        file_door.write_state(file_door.overleaf_state(), json.dumps(
            {"project": project, "commit": pushed or head}, indent=2) + "\n")
        print(f"Overleaf is at {(pushed or head)[:12]}" + ("" if pushed else " (unchanged)") + ".")
    return sorted(r for r in after if r.startswith(f"{CONFLICTS}/"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m coding sync-overleaf",
        description="Sync planars-data's .papers/ with the Overleaf project volume.yaml names, "
                    "both ways; an edit made on both sides keeps each as a copy.")
    parser.add_argument("--apply", action="store_true",
                        help="Sync, and file or close the overleaf-sync issue (default: dry run).")
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    args = args if args is not None else build_parser().parse_args()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    failure, copies = None, []
    try:
        copies = sync(args.apply, today)
    except SyncError as e:
        failure = str(e)
        print(failure)
    if copies:
        print(f"{len(copies)} conflict cop{'y' if len(copies) == 1 else 'ies'} under "
              f"{CONFLICTS}/ to merge by hand.")
    if args.apply:
        _report(copies, failure, today)
    if failure:
        sys.exit(1)


if __name__ == "__main__":
    main()
