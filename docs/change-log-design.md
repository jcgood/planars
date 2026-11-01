# Unit 17: logging hand edits to the sources, and versions read from the log

**Status: built 2026-10-31 (§ 10, as built); Jeff answered § 8 the same
day (each took its recommendation; don't re-ask).** Phase 10 unit 17
(issue #271; implementation plan, Phase 10 table). Where it stands:
`docs/data-layer-progress.md`, Phase 10 row.

## 1. The problem

Every change the tooling makes to a language's files gets a line in that
language's change log (`coded_data/{lang}/changes.tsv`, unit 15). That covers
the files people type in (annotation) and the source files when a command edits
them (accept-proposal, rename-construction, sync-params). It does not cover the
edits that shape the framework most:

- **the schemas** (`schemas/*.yaml`): classes, criteria, span rules, terms,
  the planar conventions. These are edited by hand, by Jeff's or Adam's Claude,
  and Adam's span-rule pull requests edit them on a branch (#321);
- **a language's sources** (`planar_{lang}.tsv`, `diagnostics_{lang}.yaml`)
  edited by hand in planars-data, which the coordinator guide still tells
  coordinators to do.

For these, git history is the only record. It says which lines changed. It
doesn't say what kind of change it was, whether existing answers still hold,
or whether the spans moved. Nothing marks a version either, so a chart or a
chapter can't say which state of the framework it was drawn from (unit 18
needs that).

Jeff's note on the unit (2026-10-19) also makes the log research data: a
record of how a typological framework's schema changes, language by language,
in the terms the schema-evolution literature uses (add, remove, rename, split,
merge; e.g. PRISM's operators).

## 2. What the unit adds

1. **Two kinds of log line gain a change class and their effects**: the
   project's log (new, `schemas/changes.tsv`) and each language's existing
   log, for lines about its sources (§ 3).
2. **A command for hand edits,** `log-change`, which writes those lines; the
   commands that already edit sources write the same lines through the door
   (§ 4).
3. **A check that every source is logged**: before a commit, in CI, and in
   the daily refresh (§ 5).
4. **Versions read from the log,** never typed (§ 6), and the rule they
   enforce for releases (§ 7).

## 3. The log line

### 3.1 Which files are logged

One list, in the code the check runs from (`SOURCES`, extended), every file
named and each exemption given its reason (explicit, not implicit):

| File | Logged | Why |
|---|---|---|
| `schemas/diagnostic_classes.yaml` | yes | classes, constructions, row shapes, span rules |
| `schemas/diagnostic_criteria.yaml` | yes | criteria and their values |
| `schemas/planar.yaml` | yes | the planar's columns and conventions, sheet columns |
| `schemas/terms.yaml` | yes | the analytical terms |
| `schemas/languages.yaml` | yes | e.g. `examples` changes the sheets' columns and the chapters |
| `coded_data/{lang}/lang_setup/planar_{lang}.tsv` | yes | the language's positions and elements |
| `coded_data/{lang}/lang_setup/diagnostics_{lang}.yaml` | yes | the classes, constructions and criteria it uses |
| `schemas/diagnostic_classes_status.yaml` | no | process state; a promotion is a decision (`record-decision`), the hash a review stamp (§ 8 Q2) |
| `schemas/issue_labels.yaml` | no | tooling, not the framework |
| `schemas/decisions.tsv` | no | its own log |

A file added to `schemas/` that is in neither column fails the check until it
is placed (the same rule as the label registry).

### 3.2 The columns

The language logs keep their seven columns (`CHANGE_LOG_COLUMNS`) and gain
five. `schemas/changes.tsv` has the same twelve, so one reader handles both.
Lines about annotation files leave the new five empty (except, since unit
18, the fingerprint: docs/result-stamp-design.md § 9).

| Column | Who fills it | What it holds |
|---|---|---|
| `change` | the person (or their Claude), from a fixed list | `add`, `remove`, `rename`, `split`, `merge`, `change` (an existing thing's values or rule altered), `reword` (text only: a definition, a note), `baseline` (§ 6.2) |
| `layer` | the person, from a fixed list | `shape` (what columns and values exist), `taxonomy` (what categories the theory has: classes, criteria, positions, span rules), `convention` (how coders write things); the three kinds `data-layer-design.md` names |
| `answers broken` | computed | how many answered cells, in every language, the change makes invalid or leaves with no column; `0` if none |
| `spans moved` | computed | the languages and classes whose span snapshots differ after the change, or empty |
| `fingerprint` | computed | a short hash of the file as it stands after the line |

Several changes in one edit (a rename and an added value) are several lines,
one per change class; the effects are measured once for the edit and written
on each of its lines, and the last line carries the fingerprint.

`why` stays as it is, but a line whose change is breaking (§ 6.1) must name
an issue (`#N`), usually the decision issue. A breaking line also fills
`what changed` with what happens to the existing answers: the command that
carries them over, or the issue telling the annotator which cells to redo.
`log-change` refuses a breaking line without both.

## 4. Writing the lines

### 4.1 Hand edits: `log-change`

```
log-change [--lang LANG_ID] --change CLASS --layer LAYER --why "#N: …" [--answers TEXT] [--apply]
```

It finds each logged file whose fingerprint differs from its last line, works
out what changed (the door already does this for the sources), measures the
effects (§ 4.3), and prints the lines. With `--apply` it writes them, archives
the previous version (a language's sources, as the door does; the schemas'
previous versions are in git and in each Zenodo release) and commits the log
with the edit. `--change` and `--layer` repeat, pairwise, for several changes
in one edit. A class or layer outside the lists is refused.

Claude drafts the classes from the diff and the person confirms, the same
hand-off as `record-decision`: a rename and a remove-plus-add look alike in a
diff, so a person names it.

### 4.2 Commands that edit sources

accept-proposal, rename-construction and sync-params (`edits_sources` in
`operations.yaml`), and `lookup-lang` for `languages.yaml`, know what they do,
so they pass the class and layer to the door (`write(..., change=, layer=)`);
the door refuses a source write without them. rename-construction is a
`rename`; accept-proposal passes each accepted change's own class.

### 4.3 Measuring the effects

- **Answers broken:** every language's annotation is checked against the
  file before and after the edit (`validate-coding`'s own checks, not a new
  checker); the line holds the answered cells that are invalid after but not
  before.
- **Spans moved:** the span snapshots are regenerated (`generate_snapshots.py`)
  and compared with the committed ones; the line names each language and
  class that differs. The snapshot diff stays the commit's record of *how*
  the spans moved; the line records *that* they did.

Both are computed, never declared, so neither can be forgotten or misjudged.

## 5. The check

The rule: **each logged file's fingerprint equals the fingerprint on its last
log line.** It reads the files and the logs, not git history (versioning must
not depend on git; decided 2026-10-12).

- **Before a commit** (pre-commit hook, in planars and in planars-data): a
  staged logged file whose fingerprint has no line is refused, with the
  `log-change` command to run.
- **In CI** (ci.yml, every push and pull request): the same check, which
  catches a commit made with `--no-verify` and Adam's span-rule pull requests
  (his Claude reads the failure and runs `log-change` on the branch).
- **In the daily refresh** (a step, through `integrity-check`'s new
  `CHANGES` section): it checks every language's sources, since planars-data
  has no CI. A miss files a `source-unlogged` issue naming each file and the
  command; it closes when the files are logged. It does not stop the import
  (§ 8 Q3).

## 6. Versions

### 6.1 The level of a change

Read from the line, never chosen:

- **breaking:** `answers broken` > 0, or `spans moved` is not empty. A change
  that moves results without touching any answer counts as breaking (Jeff,
  2026-10-31): a chart or chapter drawn before it no longer matches.
- **addition:** otherwise, a line whose change is `add`;
- **revision:** otherwise (rename, change, reword, and a remove, split or
  merge that broke nothing).

The plan's example put a new value under revision; here every `add` is an
addition. That keeps the level a reading of the change class with no second
judgement.

### 6.2 The version

One stream for `schemas/`, one per language: the count of each level since
the stream's `baseline` line, written breaking.addition.revision, e.g.
`schemas 3.12.40`, `stan1293 1.4.17`. A function reads it from the log
(`versions.py`); nothing stores it. Unit 18 stamps both on every result, with
the package version.

The first run writes one `baseline` line per logged file (fingerprint, no
effects), so every stream starts at 0.0.0 on the day the unit goes live
(§ 8 Q1).

## 7. Releases

A release (archived on Zenodo; `CITATION.cff`) is refused while a breaking
line still has annotation waiting on it: its `why` issue is open and labelled
for an annotator. The check is `integrity-check --check-release`, run as
the first step of the release procedure (coordinator guide § "Making a
release", added with this unit).

## 8. Questions for Jeff

**Answered 2026-10-31 (don't re-ask):** a change that moves results only
counts as breaking (§ 6.1); Q1 start at a baseline today; Q2 the status
file is not logged; Q3 the refresh files an issue and carries on.

**Q1. History before today.** Recommended: start every stream at a baseline
today. The schemas' history since March stays in git and can be logged later
as a one-time backfill (Claude reads each commit's diff and drafts its lines,
like the decision backfill) if you want it for the schema-evolution paper.
Alternative: do that reconstruction now, so the log starts in March. It is a
few hundred commits to classify, and the paper is the only reader.

**Q2. The status file.** Recommended: not logged. A promotion to `stable` is
a decision (`record-decision` on the class's issue), and the span-rule hash
records a review, not a change to the framework. Alternative: log it, so
promotions appear in the version stream as revisions.

**Q3. An unlogged hand edit in planars-data.** Recommended: the refresh
files a `source-unlogged` issue and carries on. Alternative: commands refuse
to run until the edit is logged. That gets it logged faster, but it would also
stop the daily import of everyone's annotation over one missing line.

## 9. Order of work

1. The columns, the file list and the fingerprint; a migration adds the five
   columns to each language's log; `schemas/changes.tsv` created; the
   baseline lines.
2. `log-change`, the door's `change=`/`layer=` for the commands that edit
   sources, and the effects (§ 4.3).
3. The check: pre-commit hooks, CI, the refresh step and `source-unlogged`
   label.
4. `versions.py`; `integrity-check --check-release`; the release procedure
   in the coordinator guide.

Docs in the same commits: `file_door.py`'s and the new modules' docstrings,
`schemas/__init__.py`, the coordinator guide (editing a source by hand: edit,
`log-change`, commit), `data_dependency_schema/` (`change_record`), and
CLAUDE.md's "Edit sources" convention.

## 10. As built (2026-10-31)

All four steps of § 9 in one pass. Where the build differs from §§ 2-7, and
why:

- **Modules.** `coding/source_log.py` owns the file list (`SCHEMA_SOURCES`,
  `NOT_LOGGED`, each with its reason; a language's are `file_door.SOURCES`),
  the logs, the rule (`unlogged`) and `previous_text`.
  `coding/change_effects.py` measures; `coding/log_change.py` is the
  command; `coding/versions.py` counts versions and checks a release. The
  log's columns, change classes and layers are `file_door`'s
  (`SOURCE_COLUMNS`, `CHANGE_CLASSES`, `LAYERS`), since the door writes them.
- **Effects are measured between two copies of the project, not against
  the committed snapshots** (§ 4.3). The committed snapshots also differ
  whenever annotation was imported since they were made, so comparing with
  them would charge the edit with everyone's new answers. Each copy holds
  the code, `schemas/` and every language's folder; *before* has the edited
  files put back as they were. *Answers broken* counts, per language, the
  valid answered cells lost per class and column, so a construction renamed
  with its answers breaks nothing, and a diagnostics file that no longer
  reads leaves no answer valid. *Spans moved* compares hashes of each
  class's span output with the titles left out (a renamed construction with
  the same spans has not moved). About ten seconds per measurement.
- **A command's source change is measured when the command ends**
  (`file_door.finish`), comparing every language file as the command found
  it with how it left it, so rename-construction's YAML edit and the TSV it
  moves are judged together. The lines are written at once with the effects
  empty and filled in then; a measurement that fails is written `unknown`,
  which counts as breaking.
- **A span rule is a schema edit plus a module change.** For a schema edit,
  `log-change` gives the *before* copy the analysis code as last committed
  (`git archive HEAD planars`), so logging the rule with its module change,
  before committing, records the spans they move together. Without this a
  span rule would never count as breaking, against Jeff's decision in § 6.1.
  On an expert's span-rule pull request the expert's side does not log; the
  other coordinator logs at the review's step 7 (CI fails the branch until
  then, like the hash).
- **The level is counted per edit, not per line** (§ 6.1 says "read from the
  line"): an edit is a stream's lines with the same time and command. One
  edit described as a rename and an added value moves the version once.
- **The checks are standalone modes of integrity-check, as its others are**:
  `--check-changes` (the refresh), `--check-changes --staged` (the
  pre-commit hooks: only staged sources, read with their logs as staged),
  `--check-changes --schemas` (CI), and `--check-release` (§ 7's `--section
  release`). The full run's CHANGES section reports warnings only: the
  refresh's own `changes` step files `source-unlogged`, as DECISIONS does.
- **For a schema edit, `log-change --apply` stages rather than commits**:
  the edit usually goes with code (a span rule's module), and the person
  commits them together; the hook then checks the staged log. A language's
  is committed and pushed by the local-file door, with the previous version
  archived (`file_door.log_hand_edit`). lookup-lang logs and stages its
  `languages.yaml` change the same way (`source_log.log_tool_edit`).
- **A new language's sources** are logged as an `add` with no previous
  version (no baseline line): its version counts from its first edit.
- **"Labelled for an annotator"** (§ 7) is `for_annotator: true` in
  `schemas/issue_labels.yaml`: `needs-fixing` and `needs-input`.
- **planars-data's hook** is its own `.pre-commit-config.yaml`, running the
  planars tooling from `../.venv`; each clone installs it once (coordinator
  guide, setup). A source is never removed by a command (the door refuses).
