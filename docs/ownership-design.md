# One home per fact: design (Phase 10 units 6, 15 and 11)

**Status: Jeff answered its eight questions on 2026-10-18 (§ 7); nothing here
is built.**
This is the second design pause of Phase 10
([implementation plan](data-layer-implementation-plan.md), Phase 10 table and
"Order"). The plan has units 6, 15 and 11 designed together because each needs
the others: proposal sheets (11) need a checked way to write the sources (6)
and a record of what changed and why (15). Jeff moved this pause forward on
2026-10-18 so it happens during unit 5e's week of watching, instead of after
5f. Building starts after unit 12 (§ 6). § 7 records Jeff's answers to the
questions only he could settle.

## 1. The problem

**The planar structure has two editable copies, and the daily refresh decides
between them blindly.** The planar Google Sheet and `planar_{lang}.tsv` can
both be edited. Every morning `import-planar --apply` copies the Sheet over
the file, with nothing to say which one was edited. A hand edit of the file
that was never pushed is silently reverted (the coordinator guide's
"adding elements" step told coordinators to do exactly this, until
2026-10-18). Two commands copy the Sheet to the file, with different rules:
`import-planar` and `import-sheets`' set-up download.

**The diagnostics file is the source, but its Sheet is unlocked and is read
back as if it were.** `diagnostics_{lang}.yaml` is the source. The diagnostics
Sheet is meant to be a read-only view, but anyone can edit it. The daily
import reads it before the refresh pushes the YAML to it, so a difference in
either direction looks like a Sheet edit. On 2026-10-18 Araona's new `proform`
stub (in the YAML, not yet on the Sheet) would have been reported as "class
removed", with steps to delete it from the YAML and run `prune-manifest`.
#305 (2026-10-13) was the same mistake. A real edit to the Sheet fares no
better: it is reported once, then overwritten the same day.

**Other copies of the same facts drift quietly:**

| Copy | Of | Kept current by |
|---|---|---|
| `diagnostics_{lang}.tsv` | the YAML | the daily refresh; validate-coding and import read it |
| the manifest's `planar` entry | the planar | import-sheets; the reports in Colab read it |
| the manifest's `construction_params` | each tab's criteria | sync-params; Colab still reads it, though the commands stopped trusting it in August (#272) |
| IDs in both `drive_config.json` and the manifest | where each file is | several writers each; nothing compares the two |
| class lists inside each Colab notebook | the YAML | three commands regenerate notebooks; the daily refresh doesn't |

**Local writes pass no door.** About 35 places write files: annotation TSVs,
the set-up files, state files and the manifest copies. Some archive the old
version first (import-sheets, import-planar, prune-manifest), with two copies
of the same archive function. Others don't: `sync-diagnostics-yaml` rewrites
the diagnostics TSV, sync-params rewrites the YAML, and restructure-sheets
rewrites annotation TSVs, all with no copy kept. Nothing checks that a
written annotation TSV has the right columns or keeps every answered row.
Only two commands commit what they wrote, and prune-manifest leaves its work
uncommitted.

**The only full history is git.** Archived copies exist for some files, with
no record of why a file changed or who changed it. The `data-overwrite` alarm
works by comparing git commits by author. Phase 10's rule is "the record
outlives its tools": the history should be readable without git, GitHub or
Google.

## 2. The rule

Every fact has **one source**, edited in one place. Every other copy is
**built from the source**: locked against editing, rebuilt by the daily
refresh, written only where it differs. A person who wants to change a source
they don't own **proposes** the change. The person who owns it **accepts** it,
and the acceptance is what changes the source. Every write to a source or a
data file passes a **door** that checks it, keeps the previous version and
writes a line in the change log.

| Fact | Source | Who edits it |
|---|---|---|
| planar structure | `coded_data/{lang}/lang_setup/planar_{lang}.tsv` | coordinator; annotators propose |
| a language's classes, constructions, criteria | `diagnostics_{lang}.yaml` | coordinator; annotators propose |
| annotations | the class sheets (Google) | annotators; imported daily into TSVs, which are the record |
| notes | the notes Doc | annotators |
| where each Drive file is | one file in planars-data (§ 4.3); Colab finds files by their labels (Q7) | the tooling only |

Annotations are the one fact whose source stays in Google. Annotators can only
work there. The imported TSVs are the record that outlives Google: they are
copied with history (§ 5) but never edited.

## 3. Unit 11: proposal sheets

### 3.1 The copies become locked

The planar Sheet and the diagnostics Sheet become **locked copies**, rebuilt
from the source by the daily refresh the way the locked tabs already are
(`locked_tabs.py`: write only what differs, protect, the Drive door checks
the content). Nobody edits them, so there is nothing to read back. A new kind
in the Drive door's spec (`planar_sheet`, `diagnostics_sheet`, already
labelled since 5d) says what each should hold, built from the source.

### 3.2 One proposal sheet per language

Each language gets one **proposal sheet**, editable by name by that
language's annotator and by the project's coordinators (Q2). It has two tabs, each filled with the current source plus
one extra column, **What changed?**:

- **Planar**: the planar's own rows (Position, Position_Name, Elements, …).
- **Diagnostics**: one row per class, construction and criterion, with its
  values. The YAML's nested form is hard to edit in a grid; this flat form is
  what the diagnostics Sheet shows today.

An annotator edits rows, adds rows or deletes them, and says why in What
changed?. Nothing they do changes anything else: the source, the class
sheets, or the analyses.

**Daily:** the refresh compares each proposal sheet with what it was filled
from (§ 3.4) and, if anything differs, files or updates one `proposal` issue
per language. The issue lists each change in plain words ("position 12
`v:obj-part`: element `'em` added — *'em is a clitic form of them*") and
names the command that reviews it. When the sheet is back to its last
filled state, the issue closes.

### 3.3 Accepting a proposal

A new command, `accept-proposal` with `--lang LANG_ID` (not built yet; run
by the coordinator's Claude, from the issue):

1. Lists each change and asks accept or reject. A rejection needs a reason.
2. Applies the accepted ones to the source through the local-file door (§ 4),
   so the old version is kept and a change-log line records each one with
   its What-changed text and the issue number.
3. Runs the commands that already carry a source change into the class
   sheets, dry run first: `restructure-sheets` for renumbered or renamed
   positions and elements, `update-sheets` for added elements, `sync-params`
   and `generate-sheets` for criteria and classes. Nothing new here; this is
   what the coordinator does by hand today, and `apply-pending` names.
4. Rebuilds the locked copies and refills the proposal sheet from the new
   source.
5. Writes a **Last review** note at the top of the proposal sheet: date,
   what was accepted, what was rejected and why. It's where the annotator
   sees the outcome, since terminal output reaches nobody.
6. Comments on the issue and closes it.

Accepting part of a proposal is allowed. Rejected rows go back to the
source's value when the sheet is refilled; the Last review note says why.

### 3.4 When the coordinator changes the source meanwhile

The coordinator edits the source directly (that doesn't change), and may do it
while a proposal is open. Comparing the proposal sheet with today's source
would then show the coordinator's change as the annotator proposing to undo
it. So each refill also saves **what the sheet was filled from** (the base),
and a proposal is the difference between the sheet and its base, not the
sheet and the source:

- A row the annotator didn't touch is refreshed to the source's value on the
  next daily run.
- A row both changed is a **conflict**: the issue says so, and
  `accept-proposal` shows both versions.

This is the standard three-way comparison (sheet, base, source). Without it,
every source edit during an open proposal makes a false proposal. (Q3.)

### 3.5 What is retired

In the same units, nothing left half-moved:

- `import-planar`'s Sheet-to-file direction and `import-sheets`' set-up
  download (`_download_lang_setup_sheets`, `_detect_planar_changes`,
  `_detect_diagnostics_changes`, `_check_yaml_drift`).
- `sync-diagnostics-yaml --from-tsv` and `diagnostics_drift.json`.
- The `planar-changed` and `diagnostics-drift` labels, and pending-changes
  entries of the planar and diagnostics kinds. `proposal` replaces them.
- `diagnostics_{lang}.tsv` (Q5): its readers read the YAML through one
  function instead.

`import-planar --to-sheet` and `sync-diagnostics-yaml --to-sheet` become the
daily rebuild of the locked copies; restructure-sheets' push of the planar
becomes a call to the same rebuild.

### 3.6 The manifest, Colab and notebooks

- **The manifest goes (Q7).** Colab finds a language's files by their 5d
  labels, through **one package function** that opens the sheets, reads each
  tab's criteria from its header and the YAML (as the commands already do)
  and the planar from its locked copy. Colab then reads real Sheets, never a
  cached description of them.
- **Notebooks hold no class lists** that can go stale: the class cells are
  built when the notebook runs, from the language's sheets. They are then
  rebuilt by the daily refresh like the status sheets, so a template change
  reaches everyone the next morning.
- **Instructions:** the sentences typed into `locked_tabs.py`'s builder ("Leave
  a cell blank if unsure…") move into the schema beside `sheet_instructions`,
  so every word an annotator reads has one home a linguist can edit.

## 4. Unit 6: the local-file door

### 4.1 One door, built like the Drive door

`coding/file_door.py`. Every write to `coded_data/` and to the tooling's state
files goes through it, the way every Drive write goes through the Drive door:

- **Files are named by what they are, not by path.** `door.write(annotation(lang,
  class, construction), rows, reason=...)`. The door builds the path, from
  one function per kind of file. The `{lang}/{class}/{construction}.tsv`
  convention, now typed in about fifty places (hidden-facts R4), has its one
  home here.
- **Kinds** are one table, like the Drive door's `KINDS`: annotation TSV,
  planar, diagnostics YAML, proposal base, change log, archive copy, notes
  state, pending changes, people, the ID file, and the state files unit 12
  moves into planars-data (provenance log, regen snapshots, restructure
  journal). An unknown kind can't be written.
- **Checks, from the same specs:**
  - an annotation TSV has its tab's columns (`sheet_spec`), and loses no
    answered row except inside `replacing()`, the Drive door's rule 1;
  - a source (planar, diagnostics YAML) is written only by `accept-proposal`,
    a migration, or a command whose `operations.yaml` record says it edits
    that source (sync-params' rename, split and merge);
  - a dry run writes nothing: `operations.yaml` gains `writes_locally`
    beside `writes_to_drive`, read the same way (`gating.py`).
- **What it does for every write, so no command has to remember:** keep the
  previous version (§ 5.1), write the change-log line (§ 5.2), write only if
  the content differs, and add the file to the list the end of the command
  commits.
- **Watch first, then enforce,** by the Drive door's § 4 rule; tests enforce
  from the start. A test fails if anything outside the door writes under
  `coded_data/` (the local twin of `tests/test_doorway_coverage.py`).

### 4.2 Committing

`_autocommit_data` (two callers) and the daily refresh's commit steps
become one thing: when a command that wrote through the door ends, the door
commits and pushes exactly the files it wrote, with a message taken from
their change-log lines. That closes prune-manifest's "left uncommitted", and
restructure's renamed class folder, which no list of written files names. Git stays the
transport and the backup. Nothing reads its history (§ 5.3).

### 4.3 `drive_config.json` becomes the one list of IDs

Today IDs live in `drive_config.json`, in the manifest on Drive, and in
`sheets_manifest.json`, a local copy nobody reads. The design: one file in
planars-data lists every Drive file's ID (written only by the door, when a
command creates a file), and the commands read IDs from it. Colab finds files
by their 5d labels instead (Q7), so the manifest on Drive,
`sheets_manifest.json` and `manifest_backup.json` are all deleted.

### 4.4 What doesn't pass the door

- Hand edits to sources and schemas: unit 17 (a pre-commit hook that
  requires a change-log line). Until then, a hand edit is visible as a commit
  with no change-log line.
- Annotators' edits in Google: they reach the record through import-sheets,
  which writes through the door, so the change log says "imported from the
  annotator's sheet".
- Test data under `.test_fixtures/`: `capture-drive-state` stays its only
  writer.

## 5. Unit 15: the version history

### 5.1 Every previous version is kept

Whenever the door replaces a file in planars-data, the old version is copied
first to `coded_data/{lang}/archive/{folder}/{name}_{stamp}.{ext}`. That's
today's layout, which import-sheets already uses. It now applies to every
kind, including the YAML, the TSVs restructure rewrites and the proposal
base. One date format, `ARCHIVE_STAMP_FORMAT`, always UTC (hidden-facts
M-misc).

### 5.2 One change log per language

`coded_data/{lang}/changes.tsv`, one line per file changed, written by the
door:

| when (UTC) | file | what changed | by | why | previous version |
|---|---|---|---|---|---|
| 2026-10-19T13:30:12Z | `metrical/stress_domain.tsv` | 3 cells changed | import-sheets (annotator's sheet) | daily refresh | `archive/metrical/stress_domain_20261019_133012.tsv` |
| 2026-10-20T15:02:44Z | `lang_setup/planar_stan1293.tsv` | element added at 12 | accept-proposal | #320: "'em is a clitic form of them" | `archive/lang_setup/planar_stan1293_20261020_150244.tsv` |

It's a TSV so it opens in a spreadsheet, and anyone can read it without the
tooling. A project-wide log beside `schemas/` follows in unit 17.

### 5.3 What reads the log instead of git

- **The `data-overwrite` alarm.** Today it records files changed since the
  last bot commit and checks whether the refresh touched them. The log
  answers the real question directly: did an import replace a file whose
  last change was by a person? It needs no git history.
- **"What changed in this file, and why"**, which an audit or a collaborator
  asks: the log, not `git log`.
- `coded_data_clean_tree` keeps using `git status`. It checks the working
  copy, not history, and the door makes uncommitted writes rare.

### 5.4 Not in this unit

The provenance log of Drive writes stays the Drive door's. Unit 12 moves it
into planars-data, where it sits beside the change log (Q6). Results carrying
the change-log position is unit 18.

## 6. Order of work

Each step leaves a complete, working system, and removes what it replaces in
the same commit.

1. **(Before this: unit 12.** 6a doesn't need 5f's switches to enforce,
   only the watch-mode door, so it can be built while 5f's kinds are being
   watched.)
2. **6a — the door for annotation TSVs and set-up files,** in watch mode, with
   archive copies and the change log (unit 15's §§ 5.1–5.2 are built
   inside it). The two `_archive_tsv` copies and `_autocommit_data` are
   deleted.
3. **6b — the state files and the ID file** (§ 4.3).
4. **6c — enforce,** by the § 4 rule; `data-overwrite` moves to the log (§ 5.3).
5. **11a — proposal sheets:** the coordinators list (Q2), the
   `proposal_sheet` kind in both doors, creation (**a live write, named for
   Jeff's approval**), the daily comparison and issue, `accept-proposal`. The
   old intakes keep running alongside until 11b. Jeff tells Adam, and an
   issue mentioning him says what changes (Q8).
6. **11b — lock the planar and diagnostics Sheets, retire the intakes and
   delete the diagnostics TSV** (§ 3.5, Q5; **a live write**: protecting the
   Sheets), once Adam has used a proposal sheet. Until then the diagnostics
   Sheet's intake loses an annotator's edit (found 2026-10-19, drive-door
   design § 8, "5f, the diagnostics Sheet"): the same refresh that imports it
   regenerates the TSV from the YAML and pushes the YAML back over the Sheet,
   so a changed value list is undone without any issue, and an ambiguous
   change's `diagnostics-drift` issue closes the next day because the Sheet
   no longer shows it. The edit survives only in planars-data's history and
   `regen_snapshots/`. No annotator has edited a diagnostics Sheet so far
   (its history shows none), so 11b is the fix, not an interim one.
7. **11c — Colab by labels, the manifest deleted, notebooks rebuilt daily**
   (needs 5f's sharing test for notebooks, and Q7's label test).
8. **11d — the Instructions sentences into the schema.**

## 7. Decisions (Jeff, 2026-10-18)

**Q1. What a proposal sheet looks like: a full editable copy** of the
planar and diagnostics, with a What changed? column (§ 3.2), not a blank
request form. The proposal then already holds the edit, and the tooling can
list and apply it exactly.

**Q2. Who may edit a proposal sheet: Jeff, Adam, and the language's
annotator** (who also writes that language's chapter). Jeff and Adam can
edit every language's proposal sheet, so planars-data's `people.yaml` gains
a project-level list of coordinators beside each language's annotator, and
the sharing spec reads both. The coordinators still edit the sources
directly; the proposal sheet is open to them as well.

**Q3. Compare with the base: yes** (§ 3.4). The proposal is the difference
between the sheet and what it was filled from. Rows only the source changed
are refreshed, and rows both changed are a conflict shown in `accept-proposal`.

**Q4. A restructure stops after its dry run.** `accept-proposal` edits the
source, runs `restructure-sheets` as a dry run, and waits for the
coordinator's go-ahead before the live run. Changes that only add rows or
columns (new elements, new criteria) run without stopping.

**Q5. Delete `diagnostics_{lang}.tsv`.** Its readers (validate-coding,
integrity-check, check-codebook, the import) read the YAML through one
function. The locked diagnostics Sheet and the proposal sheet are the grid
views.

**Q6. One change log per language, a TSV** (§ 5.2). Drive writes stay in
their own log beside it.

**Q7. Colab finds files by their labels straight away;** no shrunk manifest
in between. The manifest on Drive is deleted in 11c, together with
`sheets_manifest.json` and `manifest_backup.json`. Before notebooks switch,
a test with an annotator's account has to show a notebook can find a
language's sheets by label. If it can't, the step waits until it can; it
doesn't fall back to a manifest.

**Q8. The switch for annotators: Jeff tells Adam himself, and an issue
mentioning him** says what changes and when (filed through `coding/issues.py`
when 11a is ready). The old Sheet intake keeps running until Adam has used a
proposal sheet once, then 11b locks the Sheets.
