"""Find new or changed Comments cells and file them for the coordinator.

An annotator's Comments cell is where they tell the coordinator something:
a question, a doubt about a value, something the schema can't express
(#318). Before this command nothing read them: import-sheets copied them
into the TSVs and they stopped there. Examples go in the Example column,
page references in Source; Comments is only for the coordinator, and the
tooling never writes there (``schemas/planar.yaml`` ``trailing_columns``).

Reads the imported TSVs only (it runs after import-sheets, and after
check-notes, in the daily refresh), so it touches no Drive file. Compares every Comments cell with
what the last run saw (``state_files.COMMENTS_STATE_PATH``: language →
"class/construction | row key" → text), and for each language with new or
changed comments files or comments on one ``collaborator-comments`` issue,
"Comments — {Name [glottocode]}". The issue lists each comment with its
tab, row, answers, Example and Source, and ends with a Claude prompt: a
Claude Code session run from the issue sorts the comments and drafts
replies and issues for the coordinator to approve. No call to Claude is
made here.

A row is named by the columns its construction's schema entry gives as its
key (``planars.schema_values.row_key``), so a comment follows its row when
other rows are added; a text already seen on that tab for that element is
not reported again, so renumbered positions don't re-report every comment
(``changed``). A cleared comment is dropped from the state without
a report. A TSV whose class or construction the schema doesn't list is an
error (the run finishes the other files, then exits non-zero).

Usage:
    python -m coding check-comments                  # dry run: what would be filed
    python -m coding check-comments --apply          # file issues, save state
    python -m coding check-comments --lang stan1293
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import file_door, issues, state_files
from planars.schema_values import TRAILING_COLUMNS, row_columns, row_key

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
LABEL = "collaborator-comments"
COMMENTS = "Comments"
# Folders in a language's directory that hold no class TSVs.
_NOT_CLASSES = frozenset({"lang_setup", "archive"})


def _load_state() -> Dict:
    path = state_files.COMMENTS_STATE_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_state(state: Dict) -> None:
    file_door.write_state(file_door.comments_state(), json.dumps(state, indent=2, sort_keys=True,
                                                                 ensure_ascii=False) + "\n")


def issue_title(lang_id: str) -> str:
    from planars.languages import get_display_name
    return f"Comments — {get_display_name(lang_id)}"


def _lang_ids(lang_filter: Optional[str]) -> List[str]:
    from planars.languages import load_languages
    known = sorted(load_languages())
    if lang_filter:
        return [lang_filter]
    return [lang for lang in known if (CODED_DATA / lang).is_dir()]


def read_comments(lang_id: str) -> Tuple[Dict[str, Dict], List[str]]:
    """Every filled Comments cell in a language's TSVs.

    Returns ({"class/construction | key": row facts}, errors). Row facts:
    class, construction, key (column → value), answers (criterion → value),
    and each trailing column's text.
    """
    found: Dict[str, Dict] = {}
    errors: List[str] = []
    lang_dir = CODED_DATA / lang_id
    for tsv in sorted(lang_dir.glob("*/*.tsv")):
        class_name, construction = tsv.parent.name, tsv.stem
        if class_name in _NOT_CLASSES:
            continue
        try:
            key_cols = row_key(class_name, construction)
            id_cols = row_columns(class_name, construction)
        except (KeyError, ValueError) as exc:
            errors.append(f"{lang_id} {class_name}/{construction}: the schema doesn't "
                          f"describe this tab, so its comments can't be read ({exc})")
            continue
        df = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False)
        if COMMENTS not in df.columns:
            continue
        missing = [c for c in key_cols if c not in df.columns]
        if missing:
            errors.append(f"{lang_id} {class_name}/{construction}: no {missing} column, "
                          f"so its rows can't be named")
            continue
        not_answers = set(id_cols) | set(TRAILING_COLUMNS)
        answer_cols = [c for c in df.columns if c not in not_answers]
        for _, row in df.iterrows():
            text = row[COMMENTS].strip()
            if not text:
                continue
            key = {c: row[c] for c in key_cols}
            ident = f"{class_name}/{construction} | " + " | ".join(key.values())
            found[ident] = {
                "class": class_name, "construction": construction, "key": key,
                "answers": {c: row[c] for c in answer_cols},
                **{c: row[c].strip() for c in TRAILING_COLUMNS if c in df.columns},
            }
    return found, errors


def _element_of(ident: str) -> Tuple[str, str]:
    """(tab, the row key's first value: the element) from an ident."""
    tab, rest = ident.split(" | ", 1)
    return tab, rest.split(" | ", 1)[0]


def changed(found: Dict[str, Dict], seen: Dict[str, str]) -> List[Tuple[str, Dict, Optional[str]]]:
    """(ident, facts, previous text or None) for each comment new or changed since `seen`.

    A comment whose text was already seen on the same tab for the same
    element is not new, even if its row's key changed: when the planar's
    positions are renumbered, every row's Position_Number changes with it,
    and its comments must not all be reported again.
    """
    seen_texts = {(*_element_of(i), text) for i, text in seen.items()}
    out = []
    for ident, facts in found.items():
        before = seen.get(ident)
        text = facts[COMMENTS]
        if before == text or (*_element_of(ident), text) in seen_texts:
            continue
        out.append((ident, facts, before))
    return out


def _row_line(facts: Dict) -> str:
    key = ", ".join(f"{c} {v}" for c, v in facts["key"].items())
    answers = ", ".join(f"{c}={v or '(blank)'}" for c, v in facts["answers"].items())
    return f"{key}; answers: {answers}" if answers else key


def build_body(lang_id: str, items: List[Tuple[str, Dict, Optional[str]]]) -> str:
    from planars.languages import get_display_name
    display = get_display_name(lang_id)
    lines = [f"{len(items)} new or changed comment(s) in the {display} sheets.", ""]
    by_tab: Dict[str, List] = {}
    for ident, facts, before in items:
        by_tab.setdefault(f"{facts['class']}/{facts['construction']}", []).append((facts, before))
    for tab, rows in by_tab.items():
        lines += [f"### {tab}", ""]
        for facts, before in rows:
            lines.append(f"- **{_row_line(facts)}**")
            lines.append(f"  - Comments: {facts[COMMENTS]}")
            if before:
                lines.append(f"  - (was: {before})")
            for col in TRAILING_COLUMNS:
                if col != COMMENTS and facts.get(col):
                    lines.append(f"  - {col}: {facts[col]}")
        lines.append("")
    lines += [
        "---",
        "",
        "## Prompt for Claude",
        "",
        "Paste this into a Claude Code session in the planars repo:",
        "",
        "```",
        f"Read issue <this issue's number> (collaborator-comments, {display}). For each",
        "comment, say which it is: a question for the coordinator; a doubt about the",
        "row's value; a workaround for something the schema can't express; an example",
        "that belongs in the Example column; or a plain note. Check the open issues",
        "first and point to one that already covers it. Then draft, for the",
        "coordinator to approve: one short reply to the annotator per question or",
        "doubt (a few lines, per CLAUDE.md), and any new issue that is warranted",
        "(title, label from schemas/issue_labels.yaml, two-line body). Post nothing",
        "until the coordinator approves.",
        "```",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding check-comments`."""
    ap = argparse.ArgumentParser(
        description="File new or changed Comments cells as one issue per language.")
    ap.add_argument("--apply", action="store_true",
                    help="file or comment on the issues and save what was seen (default: dry run)")
    ap.add_argument("--lang", metavar="LANG_ID", help="restrict to this language")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    if not args.apply:
        print("DRY RUN — pass --apply to file issues and save state.\n")

    state = _load_state()
    all_errors: List[str] = []
    for lang_id in _lang_ids(args.lang):
        found, errors = read_comments(lang_id)
        all_errors += errors
        seen = state.get(lang_id, {}).get("seen", {})
        items = changed(found, seen)
        if not items:
            print(f"[{lang_id}] no new comments ({len(found)} in all)")
        else:
            print(f"[{lang_id}] {len(items)} new or changed comment(s)")
            body = build_body(lang_id, items)
            if args.apply:
                number, created = issues.file_issue(LABEL, issue_title(lang_id), body,
                                                    match_title=True)
                print(f"  → {'filed' if created else 'commented on'} issue #{number}")
            else:
                print("  " + "\n  ".join(body.splitlines()[:12]) + "\n  ...")
        if args.apply:
            # Saved per language, right after its issue: a later failure must
            # not make the next run report these comments a second time.
            state[lang_id] = {"seen": {i: f[COMMENTS] for i, f in found.items()}}
            _save_state(state)

    if all_errors:
        print("\nERROR: some tabs could not be read:")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
