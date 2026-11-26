"""One-time migration: planars-data's ``.papers/``, one volume → one folder per volume.

What it does, in planars-data (``coded_data/``), in one commit, then pushes:

- moves everything at the top of ``.papers/`` (``volume.yaml``, ``main.tex``,
  the ``.sty`` files, ``<part>.tex``, each part's folder, ``conflicts/`` if
  any, and the untracked files compiling left there) into
  ``.papers/<name>/``, so the book becomes one volume among several
  (``chapters/build.py``: a volume is a folder holding ``volume.yaml``);
- records the Overleaf project's last sync under that volume in
  ``.state/overleaf_state.json`` (``{"project", "commit"}`` →
  ``{<name>: {"project", "commit"}}``, coding/sync_overleaf.py), so the
  next sync sees nothing changed: the Overleaf project's own layout is
  unchanged, its top level now being the volume's folder;
- changes planars-data's ``.gitignore`` line ``.papers/*.pdf`` (the PDFs
  compiling leaves next to main.tex) to ``.papers/*/*.pdf``, and the
  comment above it (``IGNORE_LINES``).

Each chapter's pin (``data.lock``) moves with its folder unchanged. No issue
needs renaming: none labelled ``chapter-behind`` or ``overleaf-sync`` had
been filed when this was written.

Motivation: the Zenodo annual report (docs/zenodo-report-plan.md, "What has
to be built" item 1) is a second volume beside the De Gruyter book, and
won't be the last.
Run: 2026-11-25, with the commit that taught build-chapters and
sync-overleaf about volume folders. planars-data is shared through git, so
one run moves it for every machine.

Usage:
    python migrations/papers_into_volume_folders.py                 # dry run
    python migrations/papers_into_volume_folders.py --apply         # move, commit, push
    python migrations/papers_into_volume_folders.py --name NAME     # the volume's name (default: book)

Post-run checks:
    python -m coding build-chapters                 # dry run: only main.tex's comment line changes
    python -m coding sync-overleaf                  # dry run: nothing changed in Overleaf
    git -C coded_data log -1 --stat                 # the moved files
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chapters import build  # noqa: E402
from coding import state_files  # noqa: E402

OLD_IGNORE = ".papers/*.pdf"
NEW_IGNORE = ".papers/*/*.pdf"
# .gitignore's lines that change, the rule and the comment above it.
IGNORE_LINES = {
    OLD_IGNORE: NEW_IGNORE,
    "# stan1293.tex, in .papers/) leaves behind: never committed, so compiling":
        "# stan1293.tex, in a volume's folder in .papers/) leaves behind: never committed, so compiling",
    "# never makes coded_data/ unclean. Only the top level's PDFs: figure":
        "# never makes coded_data/ unclean. Only each volume folder's PDFs: figure",
}


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(state_files.CODED_DATA), *args],
                          capture_output=True, text=True)


def plan(name: str) -> tuple[list, dict | None, bool]:
    """(top-level entries of .papers/ to move, the new Overleaf state or
    None, whether .gitignore needs its line changed). Refuses when there is
    nothing in the old layout, or the target folder exists."""
    papers = state_files.PAPERS_DIR
    build.check_volume_name(name)
    if not (papers / build.VOLUME).is_file():
        raise SystemExit(f"{papers}/{build.VOLUME} does not exist: .papers/ is not in its "
                         f"one-volume layout (already migrated?). Nothing to do.")
    if (papers / name).exists():
        raise SystemExit(f"{papers / name} already exists; choose another --name.")
    entries = sorted(papers.iterdir())
    state_path = state_files.OVERLEAF_STATE_PATH
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    new_state = {name: state} if "project" in state else None
    ignore = (state_files.CODED_DATA / ".gitignore").read_text(encoding="utf-8")
    return entries, new_state, OLD_IGNORE in ignore.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", default="book", help="The volume's name (default: book).")
    parser.add_argument("--apply", action="store_true", help="Move, commit and push.")
    args = parser.parse_args()
    papers = state_files.PAPERS_DIR
    unclean = _git("status", "--porcelain", "--", ".papers", ".state/overleaf_state.json",
                   ".gitignore").stdout.strip()
    if unclean:
        raise SystemExit(f"planars-data has uncommitted changes there; commit or settle them "
                         f"first:\n{unclean}")
    entries, new_state, ignore = plan(args.name)
    target = papers / args.name
    for entry in entries:
        print(f"{'moved' if args.apply else 'would move'} .papers/{entry.name}"
              f"{'/' if entry.is_dir() else ''} -> .papers/{args.name}/{entry.name}")
    if new_state is not None:
        print(f"{'recorded' if args.apply else 'would record'} the Overleaf sync state under "
              f"volume {args.name}: {json.dumps(new_state)}")
    if ignore:
        print(f"{'changed' if args.apply else 'would change'} .gitignore: {OLD_IGNORE} -> "
              f"{NEW_IGNORE}")
    if not args.apply:
        print("Dry run: add --apply to move, commit and push.")
        return
    target.mkdir()
    for entry in entries:
        entry.rename(target / entry.name)
    if new_state is not None:
        state_files.OVERLEAF_STATE_PATH.write_text(json.dumps(new_state, indent=2) + "\n",
                                                   encoding="utf-8")
    if ignore:
        path = state_files.CODED_DATA / ".gitignore"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        path.write_text("".join(IGNORE_LINES[line.rstrip("\n")] + "\n"
                                if line.rstrip("\n") in IGNORE_LINES else line
                                for line in lines), encoding="utf-8")
    for step in (("add", "-A", "--", ".papers", ".state/overleaf_state.json", ".gitignore"),
                 ("commit", "--quiet", "-m",
                  f"Move .papers/ into the volume folder .papers/{args.name}/ "
                  f"(migrations/papers_into_volume_folders.py)")):
        done = _git(*step)
        if done.returncode != 0:
            raise SystemExit(f"git {step[0]} failed in planars-data: {done.stderr.strip()}")
    if _git("push").returncode != 0:
        print("WARNING: committed but could not push. Run: git -C coded_data push")
        return
    print("Committed and pushed in planars-data.")


if __name__ == "__main__":
    main()
