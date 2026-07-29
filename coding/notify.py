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
  - The issue number lives in sheets_manifest.json as
    manifest[lang_id]["notification_issue"] -- NOT in schemas/languages.yaml.
    languages.yaml is hand-edited coordinator metadata (source, author,
    annotator -- things a human types); the notification issue number is
    system-managed (auto-created and referenced by automation), which is
    exactly the kind of thing sheets_manifest.json already holds per
    language (folder_url, spreadsheet_ids, etc.).
  - Triggered after `restructure-sheets --apply`, once per language that had
    actual changes: post a comment to that language's tracking issue
    summarizing what changed (same content as the "Affected sheets" /
    "Bookmark this instead" terminal output, as markdown).

Not wired into any GitHub Actions workflow yet -- only into the manually
triggered, already-reviewed `restructure-sheets --apply` path.

The "decide what to do" logic (issue lookup/fallback, comment formatting) is
kept separate from "actually do it" (gh subprocess calls), following the
same split used elsewhere in this package (see _compute_stats vs
_write_tab_with_carryover in restructure_sheets.py) so the former can be
unit-tested without live gh/API calls.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

REPO = "jcgood/planars"


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


def get_notification_issue(lang_id: str, manifest: dict) -> Optional[int]:
    """Return the stored notification issue number for a language, if any."""
    return manifest.get(lang_id, {}).get("notification_issue")


def build_first_issue_body(lang_id: str) -> str:
    """Body for the one-time creation of a language's notification issue.

    Explicitly asks the reader to click "Subscribe" (top-right on this
    issue), not "Watch" the whole repo -- this repo also has active
    theoretical-linguistics discussion threads with nothing to do with
    sheet mechanics, and watching the repo would flood an annotator with
    that traffic. Subscribing to this issue alone gets exactly this
    language's sheet-change notifications.
    """
    return (
        f"This issue tracks annotation sheet changes for **{lang_id}** — "
        "new sheets created, sheets restructured (positions renamed, "
        "elements added/removed/split), etc. It's created once and reused "
        "for every future change to this language's sheets; each change is "
        "posted here as a new comment.\n"
        "\n"
        "**Click \"Subscribe\" (top-right on this issue), not \"Watch\" the "
        "whole repo.** This repo also has active theoretical-linguistics "
        "discussion threads unrelated to sheet mechanics -- watching the "
        "repo would flood you with that traffic. Subscribing to this issue "
        f"alone gets you exactly the {lang_id} sheet-change notifications "
        "and nothing else. If you annotate more than one language, "
        "subscribe to each language's issue individually.\n"
        "\n"
        "This issue is managed by `restructure-sheets`; the issue number is "
        "stored in `sheets_manifest.json` (`notification_issue`)."
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

    status_sheet_url, if given (from manifest[lang_id]["status_sheet_url"],
    set by generate_status_sheet.py), is the locked read-only status_{lang_id}
    sheet with per-construction completeness and links -- included every time
    so it isn't a one-off mention that gets buried, the same reasoning that
    applies to the folder link below.
    """
    lines = [f"## Sheet updates — {lang_id}", ""]
    if status_sheet_url:
        lines += [
            f"**Status/links page (locked, read-only):** {status_sheet_url}",
            "",
        ]
    if folder_url:
        lines += [
            "Every sheet below just got a **new URL** (restructure-sheets "
            "always creates a fresh spreadsheet and archives the old one) "
            "-- any previously bookmarked sheet links are now stale. The "
            "Drive folder link below does NOT change across restructures, "
            "so it's the one worth bookmarking long-term:",
            "",
            f"**Bookmark this instead:** {folder_url}",
            "",
        ]
    if lang_sheet_links:
        lines.append("**Affected sheets (new URLs -- old bookmarks to these classes are stale):**")
        lines.append("")
        for class_name, url in lang_sheet_links:
            lines.append(f"- {class_name}: {url}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Live gh calls (not unit-tested directly -- see tests/test_notify.py for
# the pure-logic functions above, which this orchestrates)
# ---------------------------------------------------------------------------

def _issue_is_open(issue_number: int) -> Optional[bool]:
    """Return True/False if the issue's state could be determined, else None.

    Purely informational -- GitHub allows commenting on a closed issue, so
    callers don't need to gate on this or reopen anything.
    """
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--repo", REPO, "--json", "state"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout).get("state") == "OPEN"
    except (json.JSONDecodeError, AttributeError):
        return None


def _create_notification_issue(lang_id: str) -> int:
    """Create this language's notification issue and return its number."""
    body = build_first_issue_body(lang_id)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        body_path = f.name
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--repo", REPO,
             "--title", f"Sheet updates — {lang_id}",
             "--body-file", body_path],
            capture_output=True, text=True, check=True,
        )
    finally:
        Path(body_path).unlink(missing_ok=True)
    url = result.stdout.strip()
    return int(url.rstrip("/").rsplit("/", 1)[-1])


def ensure_notification_issue(lang_id: str, manifest: dict) -> Tuple[int, bool]:
    """Find or create this language's notification issue.

    Looks up manifest[lang_id]["notification_issue"] first; if present, uses
    it as-is (a closed issue can still be commented on -- no need to
    reopen). Otherwise creates a new issue via `gh issue create`, stores the
    number into manifest[lang_id]["notification_issue"] (mutates manifest in
    place -- caller is responsible for persisting/uploading it, the same way
    other manifest mutations in restructure_sheets.py are persisted by
    main()), and returns it.

    Returns (issue_number, created) where created is True only if a new
    issue was just made (so the caller knows whether the manifest needs to
    be re-uploaded to Drive).
    """
    existing = get_notification_issue(lang_id, manifest)
    if existing is not None:
        is_open = _issue_is_open(existing)
        if is_open is False:
            print(f"    (issue #{existing} is closed -- commenting anyway, no reopen needed)")
        return existing, False

    issue_number = _create_notification_issue(lang_id)
    manifest.setdefault(lang_id, {})["notification_issue"] = issue_number
    print(f"    Created notification issue #{issue_number} for {lang_id}")
    return issue_number, True


def post_notification_comment(issue_number: int, body: str) -> None:
    """Post a comment to the language's notification issue."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        body_path = f.name
    try:
        subprocess.run(
            ["gh", "issue", "comment", str(issue_number), "--repo", REPO,
             "--body-file", body_path],
            check=True,
        )
    finally:
        Path(body_path).unlink(missing_ok=True)
