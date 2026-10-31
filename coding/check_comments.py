"""Find new or changed comments, in Comments cells and on Drive, and file
them for the coordinator.

An annotator's Comments cell is where they tell the coordinator something:
a question, a doubt about a value, something the schema can't express
(#318). Before this command nothing read them: import-sheets copied them
into the TSVs and they stopped there. Examples go in the Example column,
page references in Source; Comments is only for the coordinator, and the
tooling never writes there (``schemas/planar.yaml`` ``trailing_columns``).

**Comments cells** are read from the imported TSVs (it runs after
import-sheets, and after check-notes, in the daily refresh). Every one is
compared with what the last run saw (``state_files.COMMENTS_STATE_PATH``:
language → "class/construction | row key" → text).

**Drive comment threads** (Phase 10 unit 16d, docs/plain-record-design.md
§ 3.4) are read from each language's class sheets, proposal sheet and
notes Doc (the IDs in the ID file): comments people leave on the files
themselves, and replies, such as an annotator's reply to the comment
``needs-fixing`` leaves to email them. Every comment and reply is kept in
``records/drive_comments.tsv`` (``file_door.drive_comments``; columns
``DRIVE_COLUMNS``, one row per comment or reply, the thread's first
comment being the row whose ``comment`` is its ``thread``), archived and
logged at each change. The record is also what the next run compares
with: a comment or reply not in it, or whose text changed, is new. Authors
are named as ``people.commenter`` says, never by address or the name
shown in Drive; an address in the text (a +mention) becomes the person's
name, or "[address removed]". The tooling's own comments, and the
owner's from the same account, are recorded but not reported. No *edited
by* is logged for the record: each row names its author.

For each language with something new it files or comments on one
``collaborator-comments`` issue, "Comments — {Name [glottocode]}". The
issue lists each Comments cell with its tab, row, answers, Example and
Source, then each Drive comment with its file, author and the comment it
replies to, and ends with a Claude prompt: a Claude Code session run from
the issue sorts the comments and drafts replies and issues for the
coordinator to approve. No call to Claude is made here. The state and the
record are saved right after the language's issue, so a later failure
cannot make the next run report them again.

A row is named by the columns its construction's schema entry gives as its
key (``planars.schema_values.row_key``), so a comment follows its row when
other rows are added; a text already seen on that tab for that element is
not reported again, so renumbered positions don't re-report every comment
(``changed``). A cleared comment is dropped from the state without
a report. A TSV whose class or construction the schema doesn't list, or a
Drive file that can't be read, is an error (the run finishes the other
files, then exits non-zero; a language with an unreadable Drive file keeps
its previous record).

Usage:
    python -m coding check-comments                  # dry run: what would be filed
    python -m coding check-comments --apply          # file issues, save state
    python -m coding check-comments --lang stan1293
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import file_door, issues, people, state_files
from planars.layout import class_folders
from planars.schema_values import TRAILING_COLUMNS, row_columns, row_key

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
LABEL = "collaborator-comments"
COMMENTS = "Comments"

# The Drive comments record: one row per comment or reply. ``file`` names
# the Drive file by what it is (``_drive_files``), ``thread`` is the
# thread's first comment's Drive ID, ``comment`` the row's own; ``resolved``
# (yes/no) is filled on a thread's first row only. A row is matched across
# runs by DRIVE_KEY.
DRIVE_COLUMNS = ("file", "thread", "comment", "author", "time", "resolved", "text")
DRIVE_KEY = ("file", "comment")
# How long a quoted earlier comment may run in the issue.
_QUOTE_CHARS = 200


def _load_state() -> Dict:
    path = state_files.COMMENTS_STATE_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_state(state: Dict) -> None:
    file_door.write_state(file_door.comments_state(), json.dumps(state, indent=2, sort_keys=True,
                                                                 ensure_ascii=False) + "\n")


def _tab_prefix(class_name: str, construction: str) -> str:
    """How a seen comment's key starts: the tab it is on."""
    return f"{class_name}/{construction} | "


def rename_tab_in_state(lang_id: str, class_name: str, old: str, new: str) -> int:
    """Carry what was seen on a tab over to its new name (rename-construction),
    so its comments are not reported again as new. How many keys moved."""
    state = _load_state()
    seen = state.get(lang_id, {}).get("seen", {})
    before, after = _tab_prefix(class_name, old), _tab_prefix(class_name, new)
    moved = {after + k[len(before):]: v for k, v in seen.items() if k.startswith(before)}
    if not moved:
        return 0
    state[lang_id]["seen"] = {**{k: v for k, v in seen.items() if not k.startswith(before)},
                              **moved}
    _save_state(state)
    return len(moved)


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
    for tsv in [t for d in class_folders(lang_dir) for t in sorted(d.glob("*.tsv"))]:
        class_name, construction = tsv.parent.name, tsv.stem
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
            ident = _tab_prefix(class_name, construction) + " | ".join(key.values())
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


# ---------------------------------------------------------------------------
# Drive comment threads (unit 16d)
# ---------------------------------------------------------------------------

def _drive_files(config: Dict, lang_id: str) -> List[Tuple[str, str, str]]:
    """(what the file is, its Drive ID, its address) for each Drive file a
    language's people can comment on: its class sheets, proposal sheet and
    notes Doc, as the ID file lists them."""
    from . import drive_ids
    from .check_notes import doc_url
    from .proposal_sheets import ID_KEY as PROPOSAL_ID_KEY
    if lang_id not in drive_ids.languages(config):
        return []
    files = [(f"class sheet: {c}", i, drive_ids.sheet_url(i))
             for c, i in sorted(drive_ids.class_sheets(config, lang_id).items())]
    entry = config[lang_id]
    if entry.get(PROPOSAL_ID_KEY):
        files.append(("proposal sheet", entry[PROPOSAL_ID_KEY],
                      drive_ids.sheet_url(entry[PROPOSAL_ID_KEY])))
    if entry.get("notes_doc_id"):
        files.append(("notes Doc", entry["notes_doc_id"], doc_url(entry["notes_doc_id"])))
    return files


def _named_addresses(text: str) -> str:
    """``text`` with each email address (a +mention) replaced by the
    person's name from people.yaml, or issues.ADDRESS_REMOVED: no address
    goes into a file (plain-record-design § 3.3)."""
    def named(m) -> str:
        # The pattern takes a +mention's "+" as part of the address.
        plus = "+" if m.group(0).startswith("+") else ""
        name = people.name_for_email(m.group(0)[len(plus):])
        return plus + name if name else issues.ADDRESS_REMOVED
    return issues.ADDRESS.sub(named, text or "")


def read_drive_comments(doorway, files: List[Tuple[str, str, str]]
                        ) -> Tuple[List[Dict[str, str]], List[str]]:
    """Every comment and reply on ``files`` (``_drive_files``), as record
    rows (``DRIVE_COLUMNS``), and the files that could not be read."""
    rows: List[Dict[str, str]] = []
    errors: List[str] = []
    for label, file_id, _ in files:
        try:
            threads = doorway.list_comments(file_id)
            others = any(not c["author"].get("me")
                         for t in threads for c in [t, *t.get("replies", [])])
            # The sharing list names comment authors (people.commenter); read
            # only when someone other than the tooling's account commented.
            shared = (doorway.list_permissions(file_id, fields=people.SHARED_WITH_FIELDS)
                      if others else [])
        except Exception as exc:
            errors.append(f"{label}: its comments could not be read ({exc})")
            continue
        for t in threads:
            for c in [t, *t.get("replies", [])]:
                rows.append({
                    "file": label, "thread": t["id"], "comment": c["id"],
                    "author": people.commenter(c.get("author") or {}, shared),
                    "time": c.get("createdTime", ""),
                    "resolved": ("yes" if t.get("resolved") else "no") if c is t else "",
                    "text": _named_addresses(c.get("content", "")).strip(),
                })
    return rows, errors


def drive_record_text(rows: List[Dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    w.writerow(DRIVE_COLUMNS)
    for r in rows:
        w.writerow([r[c] for c in DRIVE_COLUMNS])
    return buf.getvalue()


def read_drive_record(lang_id: str) -> Optional[List[Dict[str, str]]]:
    """The record's rows, or None if the language has none yet."""
    text = file_door.read(file_door.drive_comments(lang_id))
    if text is None:
        return None
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter="\t"))


def new_drive_comments(rows: List[Dict[str, str]], recorded: List[Dict[str, str]]
                       ) -> List[Tuple[Dict[str, str], Optional[str]]]:
    """(row, previous text or None) for each comment or reply not in the
    record or whose text changed, leaving out the tooling account's own and
    empty ones (Drive records resolving a thread as an empty reply)."""
    before = {tuple(r[k] for k in DRIVE_KEY): r["text"] for r in recorded}
    out = []
    for r in rows:
        if r["author"] == people.TOOLING_ACCOUNT or not r["text"]:
            continue
        old = before.get(tuple(r[k] for k in DRIVE_KEY))
        if old != r["text"]:
            out.append((r, old))
    return out


def _quote(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _QUOTE_CHARS else text[:_QUOTE_CHARS - 1] + "…"


def _drive_lines(items: List[Tuple[Dict[str, str], Optional[str]]],
                 rows: List[Dict[str, str]], urls: Dict[str, str]) -> List[str]:
    """The issue's Drive comments section: per file, each new comment or
    reply, with the thread's first comment when it is a reply."""
    first = {(r["file"], r["thread"]): r for r in rows if r["comment"] == r["thread"]}
    lines: List[str] = []
    by_file: Dict[str, List] = {}
    for r, old in items:
        by_file.setdefault(r["file"], []).append((r, old))
    for label, found in by_file.items():
        lines += [f"### {label} ([open]({urls.get(label, '')}))", ""]
        for r, old in found:
            what = "reply" if r["comment"] != r["thread"] else "comment"
            lines.append(f"- **{r['author']}**, {what}, {r['time'][:10]}: {_quote(r['text'])}")
            opener = first.get((r["file"], r["thread"]))
            if what == "reply" and opener:
                lines.append(f"  - in reply to {opener['author']}: {_quote(opener['text'])}")
            if old:
                lines.append(f"  - (was: {_quote(old)})")
        lines.append("")
    return lines


def _row_line(facts: Dict) -> str:
    key = ", ".join(f"{c} {v}" for c, v in facts["key"].items())
    answers = ", ".join(f"{c}={v or '(blank)'}" for c, v in facts["answers"].items())
    return f"{key}; answers: {answers}" if answers else key


def build_body(lang_id: str, items: List[Tuple[str, Dict, Optional[str]]],
               drive_items: List[Tuple[Dict[str, str], Optional[str]]] = (),
               drive_rows: List[Dict[str, str]] = (),
               urls: Optional[Dict[str, str]] = None) -> str:
    """The issue (or comment): the new Comments cells (``items``, from
    ``changed``), then the new Drive comments (``drive_items``, from
    ``new_drive_comments``; ``drive_rows`` all of them, for the threads they
    reply in; ``urls`` each file's address), then the prompt."""
    from planars.languages import get_display_name
    display = get_display_name(lang_id)
    lines: List[str] = []
    if items:
        lines += [f"{len(items)} new or changed Comments cell(s) in the {display} sheets.", ""]
    if drive_items:
        lines += [f"{len(drive_items)} new or changed comment(s) or replies on the {display} "
                  f"Drive files (below the cells).", ""]
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
    if drive_items:
        lines += ["## Comments on the Drive files", ""]
        lines += _drive_lines(list(drive_items), list(drive_rows), urls or {})
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
        "(title, label from schemas/issue_labels.yaml, two-line body). A reply to a",
        "comment on a Drive file goes in its thread on that file, posted by the",
        "coordinator. Post nothing until the coordinator approves.",
        "```",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding check-comments`."""
    ap = argparse.ArgumentParser(
        description="File new or changed Comments cells and Drive comments as one issue "
                    "per language, and keep a record of the Drive comments.")
    ap.add_argument("--apply", action="store_true",
                    help="file or comment on the issues, save what was seen and write each "
                         "language's Drive comments record (default: dry run)")
    ap.add_argument("--lang", metavar="LANG_ID", help="restrict to this language")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    if not args.apply:
        print("DRY RUN — pass --apply to file issues and save state.\n")

    from .drive import _load_drive_config
    config = _load_drive_config()
    doorway = None
    state = _load_state()
    all_errors: List[str] = []
    for lang_id in _lang_ids(args.lang):
        found, errors = read_comments(lang_id)
        all_errors += errors
        seen = state.get(lang_id, {}).get("seen", {})
        items = changed(found, seen)

        files = _drive_files(config, lang_id)
        drive_rows: List[Dict[str, str]] = []
        drive_ok = True
        if files:
            if doorway is None:
                from .drive_doorway import get_doorway
                doorway = get_doorway()
            drive_rows, drive_errors = read_drive_comments(doorway, files)
            all_errors += [f"{lang_id} {e}" for e in drive_errors]
            drive_ok = not drive_errors
        recorded = read_drive_record(lang_id)
        drive_items = new_drive_comments(drive_rows, recorded or []) if drive_ok else []

        print(f"[{lang_id}] {len(items)} new or changed Comments cell(s) ({len(found)} in all); "
              f"{len(drive_items)} new Drive comment(s) or replies ({len(drive_rows)} in all)")
        if items or drive_items:
            body = build_body(lang_id, items, drive_items, drive_rows,
                              {label: url for label, _, url in files})
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
            # Kept as it stood when every file was read; with one unreadable,
            # the previous record stays rather than lose that file's threads.
            if drive_ok and (drive_rows or recorded is not None):
                file_door.write(file_door.drive_comments(lang_id), drive_record_text(drive_rows),
                                why="read from the comment threads on the language's Drive files"
                                    + ("; the new ones reported on its collaborator-comments "
                                       "issue" if drive_items else ""))

    if all_errors:
        print("\nERROR: some tabs or Drive files could not be read:")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
