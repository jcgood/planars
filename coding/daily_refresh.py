"""The daily refresh as one command: ``python -m coding daily-refresh --apply``.

.github/workflows/data-refresh.yml only sets up the machine (checks out both
repositories, installs Python, writes the Google credentials, gives
coded_data/ a git identity) and runs this. Everything the refresh does is in
STEPS below, in order: which command runs, which GitHub issue it files or
closes, and when coded_data/ is committed. ``daily-refresh`` without
``--apply`` prints that list and runs nothing.

Each command runs through the same dispatcher as on the command line
(``coding.__main__.dispatch``), so its preconditions are checked and the
Drive door knows which command is writing. A command that fails is not the
refresh failing: its step files (or updates) the step's issue, and the next
step runs. The refresh itself has failed only when something it must do
breaks — a git commit or push, or filing an issue. Then the remaining steps
are skipped, except the ones marked ``always`` (snapshots, the overwrite
check, the final commits), as the workflow's ``if: always()`` steps were.

Exit status: 1 if the refresh itself failed, or if a step with no issue of
its own failed (label sync, collaborator notes, criterion columns,
snapshots), so the workflow run shows red; 0 otherwise. On GitHub Actions
each command's output also goes to the run's summary page
(``GITHUB_STEP_SUMMARY``).

Moved here from the workflow file on 2026-10-17 (Phase 10 unit 8, issue
#271): the steps, their order, and every issue body are unchanged from it,
apart from three fixes noted where they apply (stale drift and
planar-change files from an earlier run are deleted first; a door
violation is no longer reported twice; the overwrite check's issue is
filed even when an earlier step broke).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from . import issues

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

# Files in planars-data that the refresh itself rewrites, so a refresh
# changing them is not an overwrite of a coordinator's work: the notes state
# (check-notes), diagnostics TSVs (generated from the YAML) and planar TSVs
# (imported from the planar Sheet, their source of truth).
_REFRESH_OWNED_EXACT = ("notes_state.json",)
_REFRESH_OWNED_PARTS = ("lang_setup/diagnostics_", "lang_setup/planar_")
_BOT = "github-actions[bot]"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Running one command
# ---------------------------------------------------------------------------

@dataclass
class Result:
    """What one command did: its exit status and everything it printed."""
    exit_code: int
    output: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class _Tee(io.TextIOBase):
    """Keeps what a command prints and passes it straight on to the job log,
    so a long command (update-sheets takes minutes) is visibly working."""

    def __init__(self, keep: io.StringIO, show):
        self.keep, self.show = keep, show

    def write(self, text: str) -> int:
        self.keep.write(text)
        self.show.write(text)
        return len(text)

    def flush(self) -> None:
        self.show.flush()


def run(cmd: str, *argv: str) -> Result:
    """Run one command through the dispatcher, keeping what it prints.

    A crash is caught and its traceback kept in the output (the import-error
    issue quotes it)."""
    from .__main__ import dispatch
    buf = io.StringIO()
    tee = _Tee(buf, sys.stdout)
    code = 0
    with redirect_stdout(tee), redirect_stderr(tee):
        try:
            dispatch(cmd, list(argv))
        except SystemExit as exc:
            if exc.code is None:
                code = 0
            elif isinstance(exc.code, int):
                code = exc.code
            else:
                print(exc.code)
                code = 1
        except Exception:  # noqa: BLE001 - a crash is reported, not raised
            traceback.print_exc()
            code = 1
    return Result(code, buf.getvalue())


def regenerate_snapshots() -> Result:
    """Run generate_snapshots.py (a root script, not a command)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_snapshots", ROOT / "generate_snapshots.py")
    module = importlib.util.module_from_spec(spec)
    buf = io.StringIO()
    tee = _Tee(buf, sys.stdout)
    code = 0
    with redirect_stdout(tee), redirect_stderr(tee):
        try:
            spec.loader.exec_module(module)
            module.main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            code = 1
    return Result(code, buf.getvalue())


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

class GitError(RuntimeError):
    """A git command the refresh depends on failed."""


class Git:
    """The few git operations the refresh needs, on one repository."""

    def __init__(self, repo: Path):
        self.repo = repo

    def _git(self, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(self.repo), *args],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise GitError(f"git {' '.join(args)} failed in {self.repo}: "
                           f"{done.stderr.strip()}")
        return done.stdout

    def head(self) -> str:
        return self._git("rev-parse", "HEAD").strip()

    def last_commit_by(self, author: str) -> Optional[str]:
        for line in self._git("log", "--format=%H %ae").splitlines():
            sha, _, email = line.partition(" ")
            if author in email:
                return sha
        return None

    def changed_between(self, old: str, new: str) -> List[str]:
        return [l for l in self._git("diff", "--name-only", old, new).splitlines() if l]

    def tracked_files(self) -> List[str]:
        return [l for l in self._git("ls-files").splitlines() if l]

    def commit(self, message: str, paths: Sequence[str] = ("-A",)) -> bool:
        """Stage `paths`, and if anything is staged, commit and push.
        True if a commit was made."""
        self._git("add", *paths)
        quiet = subprocess.run(["git", "-C", str(self.repo), "diff", "--cached", "--quiet"])
        if quiet.returncode == 0:
            return False
        self._git("commit", "-m", message)
        self._git("push")
        return True


def data_git() -> Git:
    return Git(CODED_DATA)


def code_git() -> Git:
    return Git(ROOT)


def at_risk_files(git: Git) -> List[str]:
    """Files a person (not the refresh) committed to planars-data since the
    refresh last committed, excluding the files the refresh owns."""
    last = git.last_commit_by(_BOT)
    files = git.changed_between(last, "HEAD") if last else git.tracked_files()
    return [f for f in files
            if f not in _REFRESH_OWNED_EXACT
            and not any(part in f for part in _REFRESH_OWNED_PARTS)]


# ---------------------------------------------------------------------------
# Issue bodies (each moved unchanged from the workflow file)
# ---------------------------------------------------------------------------

def _details(summary: str, text: str) -> str:
    return f"<details><summary>{summary}</summary>\n\n```\n{text}\n```\n\n</details>\n"


def planar_changed_body(changes: dict) -> str:
    lines = [
        "## Planar structure changed\n\n",
        "One or more language planars were updated from Google Sheets. "
        "Annotation sheets need to be updated to match.\n",
    ]
    for lang_id, info in changes.items():
        lines.append(f"\n### {lang_id}\n\n")
        diff = info["diff"]
        for n, name in diff.get("added", {}).items():
            lines.append(f"- `+` position {n} (`{name}`) — added\n")
        for n, name in diff.get("deleted", {}).items():
            lines.append(f"- `-` position {n} (`{name}`) — removed\n")
        for n, pair in diff.get("renamed", {}).items():
            lines.append(f"- `~` position {n}: `{pair[0]}` → `{pair[1]}`\n")
        for col in diff.get("columns_added", []):
            lines.append(f"- `+` column `{col}` — added\n")
        if not any([diff.get("added"), diff.get("deleted"),
                    diff.get("renamed"), diff.get("columns_added")]):
            lines.append("- (content-only changes — elements, examples, or notes)\n")
        lines.append(f"\n**Command to run:**\n```\n{info['recommendation']}\n```\n")
    lines.append("\nClose this issue after running the recommended command "
                 "and verifying annotation sheets are up to date.\n")
    return "".join(lines)


def import_error_body(text: str) -> str:
    """What went wrong in import-sheets, crash first (#306), then its ERROR:
    lines (an unreadable sheet or tab), else the end of the output. Warnings
    are not listed: since #309 the import fails only when it broke, and an
    invalid value goes to the sheet-validation issue instead, so a warning
    printed beside a failure is never its cause."""
    lines = text.splitlines()
    errors = [l.strip() for l in lines if l.strip().startswith("ERROR:")]
    crash = []
    if "Traceback (most recent call last)" in text:
        start = max(i for i, l in enumerate(lines) if "Traceback (most recent call last)" in l)
        ours = [l.strip() for l in lines[start:] if l.strip().startswith("File ") and "/coding/" in l]
        exc = next((l.strip() for l in lines[start + 1:]
                    if l and not l[0].isspace() and ":" in l), None)
        if exc:
            crash.append(f"The import crashed: `{exc[:400]}`")
        if ours:
            crash.append(f"Last step in our code: `{ours[-1]}`")
    out = ["## What's wrong\n\n"]
    if crash:
        out.append("\n".join(f"- {c}" for c in crash) + "\n")
        if errors:
            out.append("\nAlso printed before the crash (not its cause):\n\n")
            out.append("\n".join(f"- {e}" for e in errors) + "\n")
    elif errors:
        out.append("\n".join(f"- {e}" for e in errors) + "\n")
    else:
        tail = lines[-25:] if len(lines) > 25 else lines
        out.append("_(No `ERROR:` lines found — showing end of output where the failure likely appears.)_\n\n")
        out.append("```\n" + "\n".join(tail) + "\n```\n")
    out.append("\n## What to do\n\n")
    out.append("Common causes:\n")
    out.append('- **OAuth token expired** — re-authorize credentials (see `docs/coordinator-guide.md § "OAuth setup"`)\n')
    out.append("- **A sheet can't be opened** — check it still exists and is shared with the tooling's account\n")
    out.append("- **A tab is missing from a sheet** — run `python -m coding update-sheets --apply`\n")
    out.append("- **Uncommitted `coded_data/` changes** — commit or discard them locally, then re-trigger this workflow\n")
    out.append("- **API quota exhausted** — transient; the issue will close automatically when the next run succeeds\n")
    out.append("\nInvalid values in the sheets are not reported here: they are listed in each "
               "sheet's Status tab and in the `sheet-validation` issue.\n")
    out.append("\nThe issue closes automatically when the next import run succeeds.\n")
    out.append("\n## Full log\n\n")
    out.append(_details("Show full import output", text))
    return "".join(out)


def diagnostics_yaml_error_body(tsv_output: Optional[str], sheet_output: Optional[str]) -> str:
    out = [
        f"## Diagnostics YAML validation errors — {today()}\n\n",
        "One or more languages' `diagnostics_{lang_id}.yaml` failed validation\n"
        "during the daily data refresh, so their TSV and/or diagnostics Google Sheet\n"
        "were not updated.\n\n",
        "## What to do\n\n",
        "Fix the errors named below in the language's `diagnostics_{lang_id}.yaml`,\n"
        "then run `python -m coding sync-diagnostics-yaml --apply` (and\n"
        "`--to-sheet --apply` if the Sheet also needs updating).\n\n",
        "The issue closes automatically once both directions run clean.\n",
    ]
    if tsv_output is not None:
        out.append("\n## YAML → TSV direction\n\n" + _details("Show full output", tsv_output))
    if sheet_output is not None:
        out.append("\n## YAML → Sheet direction\n\n" + _details("Show full output", sheet_output))
    return "".join(out)


def regen_dependents_body(output: str) -> str:
    return (
        f"## Dependent construction regeneration failed — {today()}\n\n"
        "`generate-sheets --regen-dependents` failed to regenerate one or more\n"
        "dependent (pair-row) tabs during the daily data refresh — see the failure\n"
        "lines in the full log below.\n\n"
        "## What to do\n\n"
        "Investigate the error below, then re-run for the affected language:\n\n"
        "```bash\n"
        "python -m coding generate-sheets --lang LANG_ID --regen-construction CLASS:CONSTRUCTION\n"
        "```\n\n"
        "The issue closes automatically once a run regenerates everything cleanly.\n\n"
        "## Full log\n\n" + _details("Show full output", output))


def dependent_stale_body(text: str) -> str:
    errors = [l.strip()[1:].strip() for l in text.splitlines() if l.strip().startswith("✗")]
    runs = [l.split("→ Run:", 1)[1].strip() for l in text.splitlines() if "→ Run:" in l]
    out = ["## What's wrong\n\n"]
    out.append("\n".join(f"- {e}" for e in errors) + "\n" if errors
               else "_(Details could not be extracted — see full log.)_\n")
    out.append("\n## What to do\n\n")
    out.append("A tab that is generated from an earlier tab (a pair list from its "
               "prescreening; for biuniqueness_deviations, morphemes from elements "
               "and morphs from morphemes) no longer matches the answers it was "
               "generated from, so it needs to be regenerated.\n\n")
    out.append("**This requires coordinator action** because the generated tab may "
               "already hold answers that need to be reviewed. Regeneration keeps every "
               "answer whose row still exists, and refuses to drop an answered row "
               "unless you re-run it with `--confirm-drop`.\n\n")
    out.append("Run:\n\n```bash\n")
    out.append("\n".join(dict.fromkeys(runs)) + "\n" if runs else
               "python -m coding integrity-check --check-dependents   # shows the command per tab\n")
    out.append("```\n\n")
    out.append("Then run `python -m coding import-sheets --apply` to import the "
               "updated sheet. Any removed rows will appear in `apply-pending` "
               "for review before the TSV is updated.\n\n")
    out.append("The issue closes automatically when the generated tabs are back in sync.\n")
    out.append("\n## Full log\n\n" + _details("Show full check output", text))
    return "".join(out)


def drift_body(drift: list) -> str:
    out = [
        f"## Diagnostics YAML drift detected — {today()}\n\n",
        "The daily data refresh found ambiguous differences between a diagnostics TSV\n"
        "(downloaded from Google Sheets) and the corresponding YAML source of truth.\n\n",
        "**Ambiguous changes require coordinator review** before they can be applied.\n\n",
        "To resolve:\n",
        "1. Pull latest `coded_data/` and run `python -m coding sync-diagnostics-yaml --from-tsv` (dry run)\n",
        "2. Review the output and edit the YAML directly for any ambiguous items\n",
        "3. Run `python -m coding sync-diagnostics-yaml --apply` to regenerate the TSV from the corrected YAML\n\n",
        "### Drift details\n\n",
        "| Language | Class | Change type | Suggestions |\n",
        "|---|---|---|---|\n",
    ]
    for entry in drift:
        for item in entry.get("ambiguous", []):
            suggestions = ", ".join(item.get("suggestions") or []) or "—"
            out.append(f"| {entry['lang_id']} | {item['class_name']} | {item['kind']} | {suggestions} |\n")
    return "".join(out)


def codebook_error_body(report: str, prompts: str) -> str:
    errors = [l.strip()[1:].strip() for l in report.splitlines() if l.strip().startswith("✗")]
    out = ["## What's wrong\n\n"]
    out.append("\n".join(f"- {e}" for e in errors) + "\n" if errors
               else "_(Inconsistency details could not be extracted — see full log.)_\n")
    out.append("\n## What to do\n\n")
    out.append("What to do depends on the specific error:\n")
    out.append("- **Qualification rule hash mismatch** — paste the Claude prompt below into a new conversation, review the proposed changes, then run `python -m coding sync-qualification-hashes --apply`\n")
    out.append("- **Criterion missing from `diagnostic_criteria.yaml`** — add an entry to `schemas/diagnostic_criteria.yaml`\n")
    out.append("- **TSV class/criteria mismatch** — update `diagnostics_{lang_id}.yaml` and run `python -m coding sync-diagnostics-yaml --apply`\n")
    out.append("\nThe issue closes automatically when `check-codebook` passes.\n")
    out.append("\n## Full log\n\n" + _details("Show full codebook check output", report))
    if prompts.strip():
        out.append("\n---\n\n## Ready-to-paste Claude prompts\n\n" + prompts)
    return "".join(out)


def integrity_error_body(text: str) -> str:
    errors = [l.strip()[1:].strip() for l in text.splitlines() if l.strip().startswith("✗")]
    out = ["## What's wrong\n\n"]
    out.append("\n".join(f"- {e}" for e in errors) + "\n" if errors
               else "_(Error details could not be extracted — see full log.)_\n")
    out.append("\n## What to do\n\n")
    out.append("Each bullet above corresponds to a `✗` line in the full log. "
               "The `→` lines below each one in the full log explain what to do. "
               "Run `python -m coding integrity-check` locally for the full report with guidance.\n\n"
               "The issue closes automatically when the integrity check passes.\n")
    out.append("\n## Full log\n\n" + _details("Show full integrity check output", text))
    return "".join(out)


def overwrite_body(files: List[str]) -> str:
    return (
        f"## Coordinator data may have been overwritten — {today()}\n\n"
        "The daily data refresh detected human commits to planars-data that were\n"
        "overwritten by today's import from Google Sheets.\n\n"
        "This may be a false alarm if the coordinator's local edit matched the Sheet.\n"
        "But if the Sheet was stale (e.g. after a column rename), annotation data may be lost.\n\n"
        "**Check git history in planars-data to verify. Use `git log` and `git show`** "
        "on the commit(s) listed below, then compare against the current TSV.\n\n"
        "### Files affected\n```\n" + "\n".join(files) + "\n```\n")


def status_sheet_error_body(output: str) -> str:
    return (
        f"## Annotation Status sheets not rebuilt — {today()}\n\n"
        "`generate-status-sheet --apply` failed during the daily refresh, so each\n"
        "language's status sheet still shows the previous run's percentages.\n\n"
        "## What to do\n\n"
        "Fix the cause shown in the log below, then run:\n\n"
        "```bash\npython -m coding generate-status-sheet --apply\n```\n\n"
        "The issue closes automatically once a daily run succeeds.\n\n"
        "## Full log\n\n" + _details("Show full output", output))


# ---------------------------------------------------------------------------
# One run of the refresh
# ---------------------------------------------------------------------------

@dataclass
class Refresh:
    """State carried from one step to the next."""
    halted: Optional[str] = None             # why the refresh itself failed
    outcomes: List[tuple] = field(default_factory=list)   # (step, outcome)
    uncovered_failures: List[str] = field(default_factory=list)
    before_sha: Optional[str] = None
    at_risk: List[str] = field(default_factory=list)
    diag_tsv: Optional[Result] = None

    def summary(self, title: str, text: str) -> None:
        """Add a section to the Actions run's summary page, when there is one."""
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not path:
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"## {title} — {today()}\n\n```\n{text.rstrip()}\n```\n\n")

    def report(self, label: str, failed: bool, title: str, body: Callable[[], str],
               close_message: str) -> None:
        """File (replacing the open one) or close the step's issue."""
        if failed:
            number, created = issues.file_issue(label, f"{title} ({today()})", body(), replace=True)
            print(f"{'Filed' if created else 'Updated'} issue #{number} ({label}).")
        else:
            closed = issues.close_open(label, f"{close_message} on {today()} — closing.")
            if closed:
                print(f"Closed {', '.join(f'#{n}' for n in closed)} ({label}).")

    def unreported(self, name: str, result: Result) -> None:
        """A step with no issue of its own failed: make the run show red."""
        if not result.ok:
            self.uncovered_failures.append(name)


# Each step takes the Refresh. Raising from a step means the refresh itself
# broke (a commit, a push, filing an issue).

def record_before(r: Refresh) -> None:
    git = data_git()
    r.before_sha = git.head()
    r.at_risk = at_risk_files(git)
    print("Human-committed files at risk of overwrite:")
    print("\n".join(r.at_risk) or "(none)")


def sync_labels(r: Refresh) -> None:
    r.unreported("labels", run("issue", "--sync-labels", "--apply"))


def import_planar(r: Refresh) -> None:
    from .import_planar import PLANAR_CHANGES_PATH
    PLANAR_CHANGES_PATH.unlink(missing_ok=True)   # only today's changes count
    result = run("import-planar", "--apply")
    changes = (json.loads(PLANAR_CHANGES_PATH.read_text(encoding="utf-8"))
               if PLANAR_CHANGES_PATH.exists() else {})
    if changes:
        r.report("planar-changed", True,
                 "Planar structure changed — annotation sheets need updating",
                 lambda: planar_changed_body(changes), "")
    elif result.ok:
        r.report("planar-changed", False, "", str, "No planar changes detected")


def import_sheets(r: Refresh) -> None:
    from .import_sheets import DRIFT_PATH
    DRIFT_PATH.unlink(missing_ok=True)            # only today's drift counts
    result = run("import-sheets", "--apply", "--ignore-status")
    r.summary("Import", result.output or "(import did not produce output)")
    r.report("import-error", not result.ok, "Import error in data refresh",
             lambda: import_error_body(result.output), "Import succeeded")


def remind_pending(r: Refresh) -> None:
    issues.remind_stale(
        "pending-changes", 7,
        f"Reminder: this pending-changes issue has been open for more than 7 days as of "
        f"{today()}. Run `python -m coding apply-pending` to review and apply each change.")


def check_notes(r: Refresh) -> None:
    r.unreported("collaborator notes", run("check-notes", "--apply"))


def commit_data(message: str) -> Callable[[Refresh], None]:
    """Commit coded_data/ before the next command checks it is clean (#245,
    #283/#289/#290: a command finding its own sibling's output uncommitted
    stopped, every time)."""
    def step(r: Refresh) -> None:
        if data_git().commit(f"{message} {today()}"):
            print(f"Committed planars-data: {message}.")
        else:
            print("No planars-data changes.")
    return step


def diagnostics_to_tsv(r: Refresh) -> None:
    r.diag_tsv = run("sync-diagnostics-yaml", "--apply")


def diagnostics_to_sheet(r: Refresh) -> None:
    sheet = run("sync-diagnostics-yaml", "--to-sheet", "--apply")
    tsv = r.diag_tsv
    r.summary("Diagnostics YAML sync", ((tsv.output if tsv else "") + sheet.output) or "(no output)")
    failed = (tsv is not None and not tsv.ok) or not sheet.ok
    r.report("diagnostics-yaml-error", failed, "Diagnostics YAML validation errors",
             lambda: diagnostics_yaml_error_body(tsv.output if tsv else None, sheet.output),
             "Diagnostics YAML validation passed")


def sync_params(r: Refresh) -> None:
    r.unreported("criterion columns", run("sync-params", "--apply"))


def regen_dependents(r: Refresh) -> None:
    result = run("generate-sheets", "--regen-dependents")
    r.report("regen-dependents-error", not result.ok, "Dependent construction regeneration failed",
             lambda: regen_dependents_body(result.output),
             "Dependent construction regeneration succeeded")


def check_dependents(r: Refresh) -> None:
    result = run("integrity-check", "--check-dependents")
    r.report("dependent-stale", not result.ok,
             "Dependent construction stale — regeneration needed",
             lambda: dependent_stale_body(result.output), "Dependent constructions in sync")


def diagnostics_drift(r: Refresh) -> None:
    from .import_sheets import DRIFT_PATH
    drift = json.loads(DRIFT_PATH.read_text(encoding="utf-8")) if DRIFT_PATH.exists() else []
    r.report("diagnostics-drift", bool(drift), "Diagnostics YAML drift detected",
             lambda: drift_body(drift), "Diagnostics YAML drift resolved")


def codebook(r: Refresh) -> None:
    result = run("check-codebook")
    prompts = run("generate-rule-update-prompt").output if not result.ok else ""
    r.report("codebook-error", not result.ok, "Codebook inconsistency detected",
             lambda: codebook_error_body(result.output, prompts), "Codebook check passed")


def stale_manifest(r: Refresh) -> None:
    result = run("integrity-check", "--check-manifest")
    r.report("stale-manifest", not result.ok, "Stale manifest entries detected",
             lambda: result.output, "Stale manifest entries resolved")


def integrity(r: Refresh) -> None:
    result = run("integrity-check")
    r.report("integrity-error", not result.ok, "Integrity check failed",
             lambda: integrity_error_body(result.output), "Integrity check passed")


def snapshots(r: Refresh) -> None:
    r.unreported("snapshots", regenerate_snapshots())


def overwrite_check(r: Refresh) -> None:
    """Did today's refresh change a file a person committed since the last
    refresh? (#121 gap 2.)"""
    git = data_git()
    after = git.head()
    if not r.before_sha or r.before_sha == after:
        print("No planars-data changes — skipping overwrite check.")
        overwritten: List[str] = []
    else:
        changed = set(git.changed_between(r.before_sha, after))
        overwritten = sorted(set(r.at_risk) & changed)
    r.report("data-overwrite", bool(overwritten),
             "Coordinator data may have been overwritten by data-refresh",
             lambda: overwrite_body(overwritten), "No coordinator data overwritten")


def commit_snapshots(r: Refresh) -> None:
    """Commit regenerated snapshots to planars, so a code push the next day
    isn't failed by data changes (#121 gap 4)."""
    if code_git().commit(f"snapshots: regenerate from daily data refresh {today()}",
                         paths=("tests/snapshots/",)):
        print("Committed snapshot changes.")
    else:
        print("No snapshot changes.")


def update_sheets(r: Refresh) -> None:
    """Additive sheet updates (#121 gap 3). Exit 1 means drift only
    restructure-sheets can fix; this output is the drift report (a second
    read pass exhausted the quota, #154)."""
    result = run("update-sheets", "--apply")
    r.summary("Sheet drift check", result.output or "(update-sheets did not run)")
    r.report("sheet-drift", not result.ok,
             "Sheet drift detected — update-sheets --apply needs review",
             lambda: result.output, "Sheet drift resolved")


def status_sheets(r: Refresh) -> None:
    """After update-sheets, so rows added today are counted. A language's
    first status sheet writes its ID to drive_config.json, committed here."""
    result = run("generate-status-sheet", "--apply")
    commit_data("data: status sheet IDs")(r)
    r.report("status-sheet-error", not result.ok, "Annotation Status sheets not rebuilt",
             lambda: status_sheet_error_body(result.output), "Annotation Status sheets rebuilt")


def scope_summary(r: Refresh) -> None:
    langs = [p for p in CODED_DATA.iterdir() if p.is_dir() and not p.name.startswith(".")]
    yamls = list(CODED_DATA.glob("*/lang_setup/diagnostics_*.yaml"))
    tsvs = [p for p in CODED_DATA.rglob("*.tsv")
            if "archive" not in p.parts and "lang_setup" not in p.parts
            and not any(part.startswith(".") for part in p.relative_to(CODED_DATA).parts)]
    line = (f"{len(langs)} language(s) · {len(yamls)} with diagnostics YAML · "
            f"{len(tsvs)} filled construction TSV(s)")
    print(line)
    r.summary("Annotation scope", line)


@dataclass(frozen=True)
class Step:
    name: str
    does: str
    run: Callable[[Refresh], None]
    always: bool = False


STEPS: List[Step] = [
    Step("before", "note planars-data's state and the files people committed", record_before),
    Step("labels", "issue --sync-labels --apply (labels exist before anything files)", sync_labels),
    Step("planar", "import-planar --apply → planar-changed", import_planar),
    Step("import", "import-sheets --apply --ignore-status → import-error", import_sheets),
    Step("pending reminder", "remind on a pending-changes issue open over 7 days", remind_pending),
    Step("notes", "check-notes --apply (files its own collaborator-notes issues)", check_notes),
    Step("commit import", "commit planars-data", commit_data("data: daily import refresh")),
    Step("diagnostics tsv", "sync-diagnostics-yaml --apply", diagnostics_to_tsv),
    Step("commit diagnostics", "commit planars-data",
         commit_data("data: daily diagnostics sync refresh")),
    Step("diagnostics sheet", "sync-diagnostics-yaml --to-sheet --apply → diagnostics-yaml-error",
         diagnostics_to_sheet),
    Step("criterion columns", "sync-params --apply", sync_params),
    Step("regen dependents", "generate-sheets --regen-dependents → regen-dependents-error",
         regen_dependents),
    Step("dependents", "integrity-check --check-dependents → dependent-stale", check_dependents),
    Step("drift", "diagnostics_drift.json from the import → diagnostics-drift", diagnostics_drift),
    Step("codebook", "check-codebook (+ generate-rule-update-prompt) → codebook-error", codebook),
    Step("manifest", "integrity-check --check-manifest → stale-manifest", stale_manifest),
    Step("integrity", "integrity-check → integrity-error", integrity),
    Step("snapshots", "generate_snapshots.py", snapshots, always=True),
    Step("commit data", "commit planars-data", commit_data("data: daily annotation refresh")),
    Step("overwrite", "compare with the files people committed → data-overwrite",
         overwrite_check, always=True),
    Step("commit snapshots", "commit tests/snapshots/ to planars", commit_snapshots, always=True),
    Step("sheet updates", "update-sheets --apply → sheet-drift", update_sheets),
    Step("status sheets", "generate-status-sheet --apply, commit planars-data → status-sheet-error",
         status_sheets),
    Step("scope", "count languages, diagnostics files and filled TSVs", scope_summary, always=True),
]


def refresh(steps: Sequence[Step] = STEPS) -> Refresh:
    """Run every step in order. Returns what happened."""
    r = Refresh()
    for n, step in enumerate(steps, 1):
        print(f"\n=== [{n}/{len(steps)}] {step.name}: {step.does} ===", flush=True)
        if r.halted and not step.always:
            print(f"Skipped: the refresh stopped at an earlier step ({r.halted}).")
            r.outcomes.append((step.name, "skipped"))
            continue
        try:
            step.run(r)
            r.outcomes.append((step.name, "done"))
        except Exception as exc:  # noqa: BLE001 - recorded, then the run stops
            traceback.print_exc(file=sys.stdout)
            r.outcomes.append((step.name, f"FAILED: {exc}"))
            r.halted = r.halted or f"{step.name}: {exc}"
    table = "\n".join(f"{name:<20} {outcome}" for name, outcome in r.outcomes)
    r.summary("Daily refresh steps", table)
    return r


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Run the daily refresh: import, check, file or close issues, commit. "
                    "Without --apply, list the steps.")
    ap.add_argument("--apply", action="store_true", help="run the refresh")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    if not args.apply:
        print("The daily refresh runs these steps, in order "
              "(dry run — pass --apply to run them):\n")
        for n, step in enumerate(STEPS, 1):
            print(f"  {n:>2}. {step.name:<20} {step.does}{'  [always]' if step.always else ''}")
        return
    r = refresh()
    if r.halted:
        print(f"\nThe refresh stopped at: {r.halted}")
    if r.uncovered_failures:
        print("\nThese steps failed and have no issue of their own; see their output above: "
              + ", ".join(r.uncovered_failures))
    if r.halted or r.uncovered_failures:
        sys.exit(1)
