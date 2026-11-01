"""One-time migration: pin each language chapter to a change-log position
instead of a planars-data commit.

Motivation: Phase 10 unit 18 (docs/result-stamp-design.md, Jeff's Q4):
every result records what it was drawn from without git, and a chapter's
``data.lock`` now names the language's change-log position
(``chapters/build.py`` ``LOCK_FIELDS``) and is rebuilt from the files and
their archive (``coding.source_log.files_at``). A lock written before then
names a commit, which build-chapters now refuses.

A commit before the change logs' baselines (2026-11-01) has no position
that can be rebuilt, so each chapter is pinned to its language's position
now. That moves the data under the chapter, so it is done only for a
chapter the daily check finds not behind its data (no open
``chapter-behind`` issue): then nothing the chapter shows differs between
its old pin and today. A chapter that is behind is left for the coordinator,
who moves it with ``build-chapters --lang L --update`` once the lock is
deleted by hand. Run 2026-11-01.

Usage:
    python migrations/pin_chapters_to_positions.py           # dry run
    python migrations/pin_chapters_to_positions.py --apply   # write the locks

Post-run: rebuild each chapter so its front matter names the new version,
    python -m coding build-chapters --lang LANG_ID --apply
and check the next refresh's `chapters` step files no chapter-behind issue.
"""
from __future__ import annotations

import sys

import yaml

from chapters import build
from chapters.data import chapter_data
from coding import file_door, issues


def main(apply: bool) -> None:
    volume, stub = build.read_volume()
    if stub is not None:
        print("No .papers/volume.yaml: no chapters to migrate.")
        return
    behind = {i["title"] for i in issues.list_open(build.CHECK_LABEL)}
    for lang in [p for p in volume["parts"] if p != build.INTRO]:
        target = file_door.paper_built(f"{lang}/{build.LOCK}")
        text = file_door.read_paper(target)
        old = yaml.safe_load(text) if text else None
        if not old or "planars_data" not in old:
            print(f"{lang}: {'not built' if not old else 'already pinned to a position'}; nothing to do.")
            continue
        if build.check_title(lang) in behind:
            print(f"{lang}: its chapter-behind issue is open, so moving the pin would change what "
                  f"the chapter shows. Left as it is: delete .papers/{lang}/{build.LOCK} and run "
                  f"`python -m coding build-chapters --lang {lang} --update` to move it, reading "
                  f"the report.")
            continue
        new = build.lock_text(chapter_data(lang))
        print(f"{lang}: planars-data {old['planars_data'][:12]} ({old['date']}) -> "
              f"{yaml.safe_load(new)}")
        if apply:
            file_door.write_paper(target, new)
    if not apply:
        print("Dry run: add --apply to write.")


if __name__ == "__main__":
    from coding import drive_door
    apply = "--apply" in sys.argv
    with drive_door.running("migration pin_chapters_to_positions", may_write=apply):
        main(apply)
