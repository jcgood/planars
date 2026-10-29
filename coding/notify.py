"""Per-language GitHub issue notifications for sheet structure changes.

Adam (and other annotators) work through their own separate Claude Code
instances and never watch the terminal where `restructure-sheets` runs.
Printing "Affected sheets" / "Bookmark this instead" to stdout at the end of
a run does not reach them -- that's the gap this module closes.

Design (settled by discussion, not re-litigated here):
  - One GitHub issue per language ("Sheet updates — {lang_id}"), not per
    contributor and not one shared issue. An annotator working on multiple
    languages subscribes to each language's issue individually, and it keeps
    one language's changes out of another's notification stream -- matching
    how everything else in this project is scoped (per-language folders,
    per-language diagnostics files, etc.).
  - Created once, reused indefinitely (find-or-create). Never recreated.
  - The issue number lives in the ID file (drive_config.json) as
    config[lang_id]["notification_issue"] (``drive_ids.notification_issue``)
    -- NOT in schemas/languages.yaml. languages.yaml is hand-edited
    coordinator metadata (source, author, annotator -- things a human
    types); the notification issue number is system-managed
    (auto-created and referenced by automation), which is exactly the kind
    of thing the ID file already holds per language (folder, sheets, ...).
    Before creating an issue, the open ones are searched by title, so a
    lost number can never make a duplicate (the manifest once lost
    arao1248's).
  - Triggered after `restructure-sheets --apply`, once per language that had
    actual changes: post a comment to that language's tracking issue
    giving the sheets' new links, the folder link and the status page, in a
    few lines (annotators asked for short text, #318).

Not wired into any GitHub Actions workflow yet -- only into the manually
triggered, already-reviewed `restructure-sheets --apply` path.

The "decide what to do" logic (issue lookup/fallback, comment formatting) is
kept separate from "actually do it" (the GitHub calls, which go through
coding/issues.py like every other issue the tooling files), following the
same split used elsewhere in this package (see _compute_stats vs
_write_tab_with_carryover in restructure_sheets.py).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from planars.languages import get_display_name

from . import drive_ids, issues

_FOLDER_URL = "https://drive.google.com/drive/folders/{}"


def folder_url(folder_id: str) -> str:
    """The address a person opens a language's Drive folder at."""
    return _FOLDER_URL.format(folder_id)


def notification_title(lang_id: str) -> str:
    """The title of a language's one long-lived ``sheet-updates`` issue."""
    return f"Sheet updates — {lang_id}"


# ---------------------------------------------------------------------------
# Pure logic (unit-testable, no gh/API calls)
# ---------------------------------------------------------------------------

def changed_lang_ids(sheet_links: List[Tuple[str, str, str]]) -> List[str]:
    """Return distinct lang_ids from sheet_links, in first-seen order.

    sheet_links is the (lang_id, class_name, url) list restructure_sheets.py
    already builds during its per-language/per-class loop -- any lang_id
    appearing in it had at least one class actually restructured. Used to
    recover a per-language change set from what is otherwise a single global
    any_changes flag.
    """
    seen: List[str] = []
    for lang_id, _class_name, _url in sheet_links:
        if lang_id not in seen:
            seen.append(lang_id)
    return seen


def get_notification_issue(lang_id: str, config: dict) -> Optional[int]:
    """Return the notification issue number the ID file holds for a language, if any."""
    return drive_ids.notification_issue(config, lang_id)


def build_first_issue_body(lang_id: str) -> str:
    """Body for the one-time creation of a language's notification issue.

    Explicitly asks the reader to click "Subscribe" (top-right on this
    issue), not "Watch" the whole repo -- this repo also has active
    theoretical-linguistics discussion threads with nothing to do with
    sheet mechanics, and watching the repo would flood an annotator with
    that traffic. Subscribing to this issue alone gets exactly this
    language's sheet-change notifications.
    """
    # Short: an annotator reads it (Adam, #318). The comment is for the
    # coordinator: restructure-sheets keeps this issue's number in the ID
    # file (drive_config.json, notification_issue).
    return (
        f"When the {get_display_name(lang_id)} sheets change, the new links are "
        "posted here. **Subscribe** to this issue (top right) rather than watching "
        "the repository, which has unrelated discussion.\n"
        "\n"
        "<!-- Managed by restructure-sheets; number in the ID file "
        "(drive_config.json, notification_issue). -->"
    )


def build_change_comment(
    lang_id: str,
    lang_sheet_links: List[Tuple[str, str]],  # [(class_name, url), ...]
    folder_url: Optional[str],
    status_sheet_url: Optional[str] = None,
) -> str:
    """Markdown comment body summarizing one language's sheet changes.

    Same content as the "Affected sheets" / "Bookmark this instead" terminal
    output restructure_sheets.py already prints at the end of a run -- this
    is a new sink for that same data (a GitHub comment reaches the
    annotator; stdout does not), not a rebuild of it.

    status_sheet_url, if given (``drive_ids.sheet_url`` of the language's
    ``drive_ids.status_sheet_id``, set by generate_status_sheet.py), is the locked read-only status_{lang_id}
    sheet with per-construction completeness and links -- included every time
    so it isn't a one-off mention that gets buried, the same reasoning that
    applies to the folder link below.
    """
    # Short: an annotator reads it (Adam, #318).
    lines = [f"The {get_display_name(lang_id)} sheets changed."
             + (" New links (the old sheets are archived):" if lang_sheet_links else ""), ""]
    if lang_sheet_links:
        lines += [f"- {class_name}: {url}" for class_name, url in lang_sheet_links]
        lines.append("")
    if folder_url:
        lines += [f"Bookmark the folder instead; its link never changes: {folder_url}", ""]
    if status_sheet_url:
        lines += [f"Progress and links: {status_sheet_url}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Live GitHub calls, through coding/issues.py
# ---------------------------------------------------------------------------

def ensure_notification_issue(lang_id: str, config: dict) -> Tuple[int, bool]:
    """Find or create this language's notification issue.

    Looks up the ID file's ``notification_issue`` for the language first; if
    present, uses it as-is (a closed issue can still be commented on -- no
    need to reopen). If the ID file has none, looks for an open
    ``sheet-updates`` issue with the language's title before making one, so
    a lost number never makes a duplicate; a found number is stored. Only
    when there is none does it create a new issue and store its number.
    Stores through ``drive_ids.set_notification_issue`` (mutates ``config``
    in place -- the caller saves the ID file).

    Returns (issue_number, created); ``created`` is True when the ID file
    changed (a new or a found number was stored), so the caller knows to
    save it.
    """
    existing = get_notification_issue(lang_id, config)
    if existing is not None:
        if issues.is_open(existing) is False:
            print(f"    (issue #{existing} is closed -- commenting anyway, no reopen needed)")
        return existing, False

    found = issues.find_open("sheet-updates", notification_title(lang_id))
    if found is not None:
        drive_ids.set_notification_issue(config, lang_id, found)
        print(f"    Found notification issue #{found} for {lang_id}")
        return found, True

    issue_number = issues.create("sheet-updates", notification_title(lang_id),
                                 build_first_issue_body(lang_id))
    drive_ids.set_notification_issue(config, lang_id, issue_number)
    print(f"    Created notification issue #{issue_number} for {lang_id}")
    return issue_number, True


def post_notification_comment(issue_number: int, body: str) -> None:
    """Post a comment to the language's notification issue."""
    issues.comment(issue_number, body)
