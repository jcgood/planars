# Nothing only in Google or GitHub: design (Phase 10 unit 16)

**Status: drafted 2026-10-30; Jeff answered § 7's Q1–Q4 the same day (each
the recommended option), and Q5 took its recommendation unless he says
otherwise. Building follows § 6; 16a and 16b are built (2026-10-30). Where it
stands is the progress doc's Phase 10 row.** What is done and next is the Phase 10 row of
`docs/data-layer-progress.md`. The unit comes from the
[implementation plan](data-layer-implementation-plan.md), Phase 10 table:
"Status values, notes Doc text and last-edited-by imported into plain files;
a `diagnostics` issue closes only by recording its decision in a file."

## 1. The problem

Phase 10's rule is that **the record outlives its tools**: git, GitHub and
Google move, notify and edit, but the record is plain files in this repo and
planars-data. Units 6 and 15 did this for annotations and sources: every
import keeps the previous version and writes a change-log line. Some facts
still exist only in Google or only on GitHub. If either service went away, or
someone edited or deleted the text there, they would be lost.

Every kind of place a fact can live, checked on 2026-10-30:

| Fact | Lives in | A plain-file copy? |
|---|---|---|
| Answers, Comments, Example, Source | class sheet tabs | **yes**: the imported TSVs |
| Each tab's Status, and who marked it ready and when | the class sheet's Status tab | **no.** An import mentions it in the change log's *why*, but only for tabs it rewrote that day. No file says what state every tab is in |
| What an annotator wrote in their notes Doc | the notes Doc | **no.** `notes_state.json` keeps a hash for detecting changes. The text goes into a GitHub issue |
| Who edited a sheet or Doc, and when | Drive's revision history | **no.** The change log's *by* names the command (`import-sheets (daily refresh)`), not the person |
| Replies to the tooling's comments on a sheet, and annotators' own Drive comments | Drive comment threads | **no, and nobody reads them.** `needs-fixing` comments on a sheet to email an annotator with no GitHub username. A reply from the email lands in a thread the tooling never opens |
| Changes an annotator suggests on a proposal sheet that nobody has reviewed yet | the proposal sheet; listed in the `planars-and-diagnostics` issue | **no.** `proposal_base_{lang}.json` holds what the sheet was filled *from*, not what the annotator changed |
| Proposal changes rejected, and why | the proposal sheet's Last review tab; a comment on the issue | **no.** Accepted changes get change-log lines; rejected ones don't |
| Linguistic decisions (`diagnostics`, `linguistics` issues; Jeff's decision comments such as #318's) | GitHub threads | **only when a decision changed a file**, and then only as a schema comment that cites the issue, if someone wrote one. A decision to change nothing ("keep it as coded") is on GitHub only |
| Answers to annotators' questions (`collaborator-comments`, `collaborator-notes`) | GitHub replies | **no** (decisions in them are covered by the row above) |
| Status sheets, charts, notebooks, Instructions and Planar Structure tabs, cell highlights, dropdowns | Drive | not needed: each is built from files, and the daily refresh rebuilds it |
| Old answers that `restructure-sheets` quotes in a cell note | a cell note | **yes**: the archive copy of the TSV from before the split |
| Sharing, labels, chapter prose | Drive, GitHub, Overleaf | **yes**: `sheet_spec._SHARING`, `issue_labels.yaml`, `.papers/` (`sync-overleaf`) |
| Cell-by-cell edit history within a day | Drive's version history | **no, and none is planned.** The daily import keeps one version per day, and finer history stays with Google (§ 5) |

## 2. The rule

Anything a person writes in Google or GitHub that the research depends on
gets a **copy in plain files**, made by the daily refresh through the
local-file door. The door keeps the previous version and writes a change-log
line, as it does for annotations. The service stays the source, the place
where people type. The file is the record.

Copying does not move the source. The Status tab, notes Doc, Drive comments
and proposal sheet are still edited in Google, and the imported copies are
never edited, the same arrangement annotation TSVs already have
(ownership-design § 2). Decisions (§ 4) are the exception: their source
becomes a file, and the GitHub issue holds only the discussion leading to it.

## 3. The copies

The copies go in one folder per language, `coded_data/{lang}/records/`, apart
from the set-up files and the class folders. A language folder's layout is
stated once, in `planars/layout.py` (16a): before then, three places
(`check-comments`, `planars/reports.py`, the daily refresh's summary) each
listed the folders that are not classes, so a new folder would have been
read as a class. The refresh's count of construction TSVs also counted each
language's change log.

### 3.1 Tab status

`records/tab_status.tsv`: one row per class and construction, with columns
`Class`, `Construction`, `Status`, `Marked by`. It is the Status tab's
own cells as the annotator or tooling left them. `import-sheets` already reads
every Status tab on each run (`validate_coding.read_status_tab`), so it writes
this file once per language at the end, through a new file-door kind
`tab_status`. The change log then reads, for example, "`metrical/stress_domain`:
in-progress → ready-for-review (annotator, 2026-10-29)". (Marked by says
annotator, coordinator or the check, not a name; who edited the sheet is
§ 3.3.)

Nothing reads `tab_status.tsv` back. Status keeps coming from the Status tab
(the source), so no command can act on a stale copy.

### 3.2 Notes Docs

`records/notes.txt`: the notes Doc's text, written by `check-notes`
through a new file-door kind `notes_text` whenever the text changes.

With the text saved, the hash isn't needed: **what is new is the difference
between the Doc and `notes.txt`**. The hash in `notes_state.json` is deleted
(the state keeps only each annotator's issue number). The issue then quotes
just the new lines instead of the whole Doc each time. Today, Adam would
re-read every earlier note whenever he adds one.

### 3.3 Who edited

The doorway gets one read-only call, `list_revisions(file_id, since)`: Drive's
revisions of a file, each with its author and time. The change log gets a
seventh column, **edited by**: the people whose revisions fall between the
previous import and this one, by name. Names come from `people.yaml`
(`people.name_for_email`), never from the name someone gives themselves in
Drive, which anyone can set to "Adam Tallman". Someone not in `people.yaml`
is recorded as "someone not in people.yaml" (`people.UNLISTED_EDITOR`):
their own name doesn't belong in a public issue, and since the files are
shared only with people in `people.yaml`, such an edit means a file is open
wider than it should be. The import that finds one says so in the
`data-overwrite` check's issue, naming the file, so the coordinator can
check its sharing. Email addresses never go into a file, and
`coding/issues.py` removes any from issue text on its way to GitHub (a
notes Doc or a Drive comment's +mention can carry one).

It applies wherever a person's typing is imported: class sheets
(`import-sheets`), notes Docs (`check-notes`), proposal sheets
(`proposal-sheets`) and Drive comment threads (§ 3.4). Lines written before
this unit leave the column empty. `file_door.overwrites` (the
`data-overwrite` alarm) can then name the person whose work an import
replaced, not only the command.

Drive's revisions are whole-file, not per tab or cell. That is enough to say
who touched a sheet since the last import. Which rows are whose stays where
it already is: the Source column.

**Found 2026-10-30 (a read-only check on English's sheets):** revisions can
be listed on class sheets and notes Docs with the tooling's access. Every
write the tooling makes (highlights, Status cells, dropdowns) is a revision
by the account it runs as, Jeff's, so a sheet's recent revisions are almost
all "Jeff Good". Drive marks them `me`. The column therefore names everyone
**except that account**. Jeff's own hand edits, made from the same account,
can't be told apart from the tooling's and aren't named. Annotators and
coordinators with their own accounts are named. A sheet can have more than
200 revisions, so the call reads page by page and keeps only those after the
previous import.

### 3.4 Drive comment threads

`check-comments` already reads every class sheet's Comments cells daily and
files one `collaborator-comments` issue per language. It will also read each
language's Drive comment threads (class sheets, the proposal sheet, the notes
Doc): the annotators' own comments and their replies to the tooling's. New
ones go into the same issue under their own heading, and all of them are saved
to `records/drive_comments.tsv` (file, thread, author, time, text,
resolved). The author is named as in § 3.3, never by address or Drive name. The doorway's `list_comments` asks for authors, times and replies,
not only `id` and `content`. This fixes the unread-reply gap in § 1 whatever
§ 7 decides.

### 3.5 Proposal sheets

`proposal-sheets` already reads each proposal sheet daily and compares it
with its base. When the sheet differs from the base, it also writes the sheet
as the annotator left it to `records/proposal_sheet.json` (new kind
`proposal_sheet_copy`). When the sheet matches the base, it removes
that file. `accept-proposal` writes each rejected change and its reason to the
language's decisions log (§ 4), so a rejection is on record like an
acceptance.

## 4. Decisions

### 4.1 Where they go

Two decision logs, plain TSVs that open in a spreadsheet:

- **`schemas/decisions.tsv`**: decisions about the framework (a class, a
  criterion, a term, a span rule, a convention). It sits in this public repo,
  beside the schemas the decisions shape.
- **`coded_data/{lang}/decisions.tsv`**: decisions about one language (its
  planar, how a construction is coded, a proposal accepted or rejected). It
  sits in private planars-data, beside that language's change log.

Columns: `date`, `issue`, `decided by`, `decision` (a sentence or two, plainly
worded), `scope`, which is optional and names a class, criterion or position
when one applies. A log line does not list the files the decision changed.
Each of those changes carries the issue number in its own change-log line
(today for data files, from unit 17 for hand edits to sources), so searching
the change logs for `#N` lists them. That keeps one home for each fact: the
decision's wording in the decision log, the file changes in the change log.

A schema comment that explains a rule ("see #254") stays. It may now say
"decisions.tsv, #254" instead of leaning on the issue thread.

### 4.2 Recording one

A new command, `record-decision --issue N --decision "…" [--lang LANG_ID]
[--by NAME] [--scope …] [--apply]`. Without `--lang` the line goes to
`schemas/decisions.tsv`. It writes the line through the file door, comments
the decision on the issue (signed, as every Claude comment is) and closes it.
The coordinator's Claude drafts the wording from the thread and the
coordinator approves it, the same hand-off as `accept-proposal`.
`accept-proposal` calls the same function for its rejections (§ 3.5).

A decision that changes nothing is still a line ("Keep `vp_ellipsis` as one
construction; #319"). A closed issue that needed no linguistic decision (a
tooling bug filed under `diagnostics`) gets its label corrected rather than an
empty line.

### 4.3 Which issues need one, and how the rule is kept

`schemas/issue_labels.yaml` gets a field, `needs_decision: true`, on the
labels whose issues end in a linguistic decision (§ 7 Q2). The code runs from
it, so adding a label to the set is one line.

The daily refresh checks every issue closed under such a label after a start
date (§ 7 Q4). If its number is in neither decision log, the check **reopens
it**, with a comment giving the `record-decision` command (§ 7 Q3). The check
is a section of `integrity-check` (checkers don't multiply), and the reopening
is a refresh step through `coding/issues.py`.

## 5. Not in this unit

- **Cell-by-cell history within a day.** The daily import keeps one version
  per day. A cell changed twice between imports leaves only its last value in
  the record. Finer history would mean polling Google, and nothing in the
  research needs it.
- **GitHub discussion as such.** Threads stay on GitHub (unit 13: "issues for
  discussion only"). Only their outcome, the decision, must be in a file.
- **Hand edits to sources** without a change-log line: unit 17.
- **Results carrying a change-log position:** unit 18.

## 6. Order of work

Each step is one commit (or two) that leaves a working system and removes
what it replaces. Every new file kind goes into the file door's table, and
`tests/test_file_door_coverage.py` holds every writer to it.

1. **16a: tab status and proposal copies.** `tab_status.tsv` (§ 3.1) and
   `proposal_sheet.json` (§ 3.5). Built against the fake. Its first real
   write is the next refresh.
2. **16b: notes text.** `notes.txt`, the hash deleted, the issue quoting only
   the new lines (§ 3.2). The first run saves each Doc as it stands and files
   nothing new.
3. **16c: who edited.** `list_revisions` in the doorway, the Drive door
   (read-only, retried like every read) and the fake; the change log's
   *edited by* column; the alarm naming the person (§ 3.3).
4. **16d: Drive comment threads.** `check-comments` reads, saves and reports
   them (§ 3.4).
5. **16e: decisions.** The two logs, `record-decision`, `needs_decision` in
   the label registry, the refresh check, `accept-proposal`'s rejections
   (§ 4). Then the backfill if Jeff wants it (Q4): Claude drafts one line per
   closed issue, Jeff (and Adam, for the linguistic ones) approves the batch,
   and one run records them.

Docs in the same commits: the module docstrings,
`data_dependency_schema/` (new facts: `tab_status_record`, `notes_record`,
`decision_record`), the coordinator guide (how to close a decision issue),
and the collaborator guide (Drive comments are now read).

## 7. Questions for Jeff

**Answered 2026-10-30 (don't re-ask):** Q1 two logs; Q2 `diagnostics` and
`linguistics`; Q3 the refresh reopens the issue; Q4 backfill once, one
approved batch. Q5 was not put to Jeff: it takes its recommendation (everyone
with a revision since the last import) unless he says otherwise.

**Q1. Where decisions go.** Recommended: two TSV logs, framework decisions in
`schemas/decisions.tsv` (public) and a language's in its planars-data folder
(private), as § 4.1 says. Alternative: one log in planars-data for everything.
It's simpler, but framework decisions would then be invisible to anyone
reading the public schemas.

**Q2. Which issues must end in a recorded decision.** Recommended: those
labelled `diagnostics` or `linguistics`. Both mean "needs domain expertise to
settle". `needs-input` marks who the issue is waiting on, not what kind of
issue it is, so it's left out.

**Q3. An issue closed without a recorded decision.** Recommended: the
refresh **reopens it** with a comment naming the command, so the issue itself
is the reminder. Alternative: a line in the daily `integrity-error` issue.
That is quieter, but it ends up in an issue that mostly reports unrelated
problems.

**Q4. Backfill.** About 50 issues have closed under the two labels (37
`diagnostics`, 14 `linguistics`, some carrying both). Some are tooling bugs
with the wrong label (e.g. #269). Recommended: backfill them all once (Claude
drafts and you approve one batch), then start the check. Alternative: start
the check from today and leave older decisions on GitHub, which leaves the
older half of the record only in GitHub.

**Q5. "Edited by".** Recommended: everyone with a revision since the last
import (§ 3.3). Alternative: only the last person to edit the file, which is
one field Drive already returns but misses anyone who edited before them that
day.
