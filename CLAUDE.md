# CLAUDE.md

Guidance for every Claude working in this repository (Jeff's and Adam's).
This file holds **rules and pointers**. How a piece of code behaves is in that
code's module docstring; what is done and next is in the progress docs and
issues; why a decision was made is in a decisions log. If you are about to add
a paragraph describing behaviour or history here, put it in its owner instead.
`planars/CLAUDE.md` and `coding/CLAUDE.md` cover the two packages.

## What this project is

Linguistic typology: deriving morphosyntactic and phonological domains from
per-language annotation, to test three hypotheses about constituency (Good,
"Domains of linearization, constituency, and wordhood in Chichewa", draft):

1. **Tree** — the domains of constituency diagnostics nest within each other.
2. **Morphosyntax/phonology divide** — deviations from nesting are allowed
   between morphosyntactic and phonological diagnostics, not within either.
3. **Word** — some diagnostics converge on a small span, a word, and the larger
   domain is completely partitioned into such spans.

The spans the analysis modules compute are the instrument for testing them.
Terms (keystone, partial/complete positions, strict/loose spans) are defined
in `schemas/terms.yaml`; each class's rule is in `schemas/diagnostic_classes.yaml`,
summarised in `docs/analyses.md`.

**It is a research project.** The schemas, span rules and models are
outputs of the research, not fixed inputs: annotation informs theory, which
changes `schemas/`, which changes what gets annotated. Expect everything to be
revised as more languages come in.

**Reference works.** The framework extends Tallman, Auderset & Uchihara (eds.)
2024, *Constituency and convergence in the Americas* (Language Science Press,
doi:10.5281/zenodo.10559861; source https://github.com/langsci/291), whose
companion database (CCDB, https://github.com/Constituency-and-Convergence/Constituency-Database,
CC-BY-SA 4.0) covers the same diagnostics. Use the book's definitions in docs
and the codebook, but mark toolkit extensions (strict/loose spans,
partial/complete positions, named `*-combines` criteria): this is research that
goes beyond the book. For how the schemas change over time, draw on the
schema- and ontology-evolution literature (versioning; add/remove/rename/split/merge
change classes; migration tooling; compatibility policy).

**Languages.** English (stan1293) is the active focus. Araona (arao1248) is a
trial, not a priority (Jeff, 2026-09-24): don't propose expanding or
unblocking it (e.g. #279's missing `proform`) unless Jeff raises it. Chichewa
(nyan1308) is planned and waits on the `tonosegmental` and `intonational`
modules (#72). Per-language metadata is `schemas/languages.yaml`; progress per
tab is each language's status sheet.

## Where things live

| What | Where |
|---|---|
| Resuming work | `NextPrompt.md` ("Read NextPrompt.md and carry on.") |
| Library (span derivation) | `planars/` — see `planars/CLAUDE.md` |
| Coordinator tooling (`python -m coding …`) | `coding/` — see `coding/CLAUDE.md`; full command list `python -m coding registry` |
| Annotation data | private repo `planars-data`, cloned into `coded_data/` (ignored by this repo; setup in `docs/coordinator-guide.md`) |
| Schemas (the definition files) | `schemas/` — what each file owns: `schemas/__init__.py` |
| Per-language sources | `coded_data/{lang_id}/lang_setup/`: `planar_{lang_id}.tsv`, `diagnostics_{lang_id}.yaml` (the one diagnostics file; every command reads it) |
| Facts kept in two places, shared preconditions, what each command does | `data_dependency_schema/` — see its `SCHEMA.md` |
| Commands, workflows, setup | `docs/coordinator-guide.md` |
| Annotators' guide | `docs/collaborator-guide.md` |
| Design principles (late aggregation, definition vs data files) | `docs/data-management.md` |
| Coordinator UX checklist | `docs/tooling-design.md` |
| Data layer redesign (#271): rationale, plan, **current state** | `docs/data-layer-design.md`, `docs/data-layer-implementation-plan.md`, `docs/data-layer-progress.md` |
| Tests and saved outputs | `docs/testing.md`; span snapshots in `tests/snapshots/` |
| One-time migrations | `migrations/` — convention in `migrations/README.md` |
| Laminar-family analysis and charts | `laminar/` (run `python -m laminar charts <dataset>`) and `planarsviz/` (R chart package); plan `docs/laminar-analysis-plan.md`, state `docs/laminar-analysis-progress.md` |
| Chapters written from the annotation (values, fragments, outline, prose slots) | `chapters/` (`python -m chapters values`; built with `python -m coding build-chapters` into `coded_data/.papers/`); plan and state `docs/chapter-generation-plan.md` |
| Personal working area, not the pipeline | `NonCollaborative/` |

## Working rules for every Claude on this project

Jeff's and Adam's Claude instances both work here, so project rules live in
this file, not in either instance's private memory (moved here 2026-10-12;
see `docs/data-layer-implementation-plan.md` Phase 10).

- **Light maintenance beats speed and elegance.** Before adding any registry,
  declaration, document or check, ask who updates it when the code changes
  and what happens if they don't. If someone has to remember, choose a design
  with nothing to remember: regenerate (compare, write what differs), read the
  value from its one source, or delete the copy. A registry is right only if
  it is the one source the code *runs from*; never one that only *describes*
  the code. A list moved inside a function body is a hidden fact, not a fix.
- **Belt and suspenders, not duct tape.** Fix small problems and robustness
  gaps the moment you find them, completely, rather than tracking them or
  writing "documented limitation" — a deferred item has nobody to remember
  it. Defer only *features* with no current use. When a gap is structural,
  recommend the structural fix, not the smallest piece that attaches to it.
- **A bug you find is never a question.** Fix it, or add it to the plan,
  and report what you did. Ask only what only the person can decide: a live
  write to Drive or GitHub, a linguistic call, something that can't be
  undone. A report that ends "Shall I…?" about a bug is the warning sign:
  if "no" would be a strange answer, the question shouldn't have been asked.
  The same goes for code that breaks a rule already written here (e.g.
  sync-params editing the diagnostics TSV, against "edit sources, never
  their copies", #315): the rule is the decision, so bring the code into line.
- **Before saying "that's everything", enumerate the kinds of place** a fact
  can live or a write can happen (code, schemas, docs, tests, workflows,
  Drive, GitHub, local state, memory, hand edits) and check each, rather than
  listing what has come up.
- **Trace a recommendation forward before labelling it "Recommended":** who
  reads the result and what they do with it. Don't let "keep it simple" pick
  the smaller option by default.
- **Explicit, not implicit.** A classifier or typing rule never lets an
  unrecognised input fall into a default category: register every case
  explicitly, keep exceptions as an explicit list, and hard-fail (or return
  "unknown") on anything it cannot place.
- **Critical data paths go through the daily pipeline,** never a separate
  command someone must remember to run (it would get no backup, no
  `import-error` issue, no validation, no status percentage).
- **Don't dismiss a recurring warning as old noise.** Check it against the
  documented rule it enforces; persistence is not evidence the rule is met
  (#270 hid that way for days).
- **Verify an issue is still open** (`gh issue view`) before recommending it.
- **validate-coding's blank counts come from the local TSVs.** If someone says
  cells are filled, run `import-sheets` and look, rather than defending the
  count.
- **Criteria are opt-in per language.** A criterion missing from a language's
  diagnostics file means "doesn't apply"; present but blank means "not yet
  coded". Add a newly found criterion to the schema and to that language only.
- **A stale docstring or comment is a bug,** fixed in the same change the
  moment you notice it (see "Documentation" below).

## Who the tooling is for

The coordinator is a scientist first, not a software engineer — one person
doing the work a well-funded project would spread across several roles. The
tooling design is as much a social problem as a software one: where
information lives, what triggers reminders, and how much to automate versus
hand to Claude all follow from this.

**Planned scale: 30–40 languages and more than one coordinator.** Workflow
code must loop over every language, and docs must be followable by a
coordinator other than Jeff. A single-language assumption is a bug, not a
simplification.

**Low cognitive load is a first-class requirement.** Prefer self-documenting
systems (errors say what to do next), issue-driven workflows (the GitHub issue
IS the instruction for that situation) and pre-assembled context (Claude
prompts generated by scripts, not composed from memory). A workflow that needs
the coordinator to remember a sequence of steps is a design flaw. Complexity
accumulates faster than one person can hold it: automate the deterministic
parts, hand the judgement to Claude with the context pre-assembled, and
document the hand-off points.

**Design for "John"**, the typical future collaborator: a language expert who
can open a browser, fill in a Google Sheet and follow a short written guide,
and cannot use a terminal, install software or run code. The annotation
Sheets must work for John; anything needing a terminal must at least work for
a collaborator whose Claude runs it for them.

**Terminal output reaches no collaborator.** It is seen only by whichever
Claude ran the command, and then it is gone. Anything meant for a person goes
into a channel both sides check: a GitHub issue or comment, a Sheet's
`Comments` cell or `Instructions` tab, the language's notes Doc, the docs.
CLI output aimed at Claude (dry-run counts, diagnostics for the next command)
is the right design; output that assumes a human will notice a line and relay
it is not.

### Write in plain language

Software jargon is a barrier here, not shorthand. The coordinator and the
collaborators are linguists. Anything a person reads — summaries, issue
bodies, error messages, dry-run output, commit messages, docs, code comments —
should make sense to someone who has never written a test.

- **Before introducing a term, ask whether the project already has a word for
  the thing.** If it does, use it: `tests/snapshots/` already existed, so
  "golden" was dropped for *snapshot*. If it genuinely doesn't, pick the
  plainest name and define it once, in a few words (the single place every
  Drive call passes through is the *doorway*, not a "seam" or "backend").
- **Otherwise prefer an ordinary phrase.** "Fixture", "mock", "idempotent",
  "regression", "assertion", "CI" rarely earn their place. The test is not
  *is this jargon* but *does this name something the project needed to name*.
- **Lead with what is broken and what it would do,** in the project's terms —
  sheets, columns, annotators, positions, elements — not with how it was found.
- **Say what you need.** End with a specific question (with a recommendation)
  or an explicit "nothing needed".
- **Keep anything an annotator reads short** (Adam, #318, 2026-10-22):
  replies, issue bodies and comments, sheet text, notes. Answer in a few
  lines, give the one next step, and don't recap their points; the time
  spent reading comes out of annotation time. This includes text the
  tooling writes for them.
- **Name who must answer.** Claude's comments post under Jeff's account, so
  a question with no name reads as Jeff thinking aloud. Open with the person
  ("Adam — …"), and separate what needs their answer from what is only
  for their information (Adam, #318, 2026-10-28).
- **Cut narration of your own process.** Report findings and decisions, not
  method. This is about register, not depth: the coordinator engages closely
  with substance stated plainly.

## Design rules

- **Read `docs/data-layer-design.md` before proposing anything that touches
  `coding/`, `schemas/` or `data_dependency_schema/` at a design level.** Every
  significant failure in the project's history has been a fact recorded in
  more than one place with no single owner; options are ranked by
  cost-to-comprehend, not cost-to-build. Current state of that work is
  `docs/data-layer-progress.md`.
- **Apply the checklist in `docs/tooling-design.md`** before proposing or
  making any fix to coordinator-facing output (error messages, issue bodies,
  `accept-proposal` prompts, `integrity-check` output, generated Claude prompts,
  dry-run output, documented steps).
- **Checkers don't proliferate; commands do.** New validation goes into
  `integrity-check` (summary) or `check-codebook` (detail), with `--section`
  flags if one grows too long — never a new standalone checker. New scripts are
  commands (they transform or generate data) and may validate on the side.
- **Never aggregate during data collection; never store derived values**
  (spans, domain types) in annotation TSVs (`docs/data-management.md`).
- **Drive goes through the doorway.** Code that touches Drive calls
  `get_doorway()` (`coding/drive_doorway.py`), which wraps it in the Drive
  door (`coding/drive_door.py`) that checks every write; never `_get_clients()`.
  `tests/test_doorway_coverage.py` checks. Command tests run against the
  offline fake and a frozen copy of the data in planars-data
  (`coded_data/.test_fixtures/`), changed only by
  `python -m coding capture-drive-state --apply`.
- **GitHub issues go through `coding/issues.py`,** which refuses a label not
  in `schemas/issue_labels.yaml`.
- **When a bug traces to an undocumented authority/cascade relationship or
  shared precondition,** write the `data_dependency_schema/` record as part of
  the fix, not as follow-up.
- **Schema work is the most consequential work** (mistakes cascade across
  languages): go slow, run `integrity-check` and `check-codebook` after. A
  span rule change also updates the module's docstring and comments —
  coordinator guide § "Updating a span rule". A snapshot diff in a
  commit is the expected record of how a change altered spans; a snapshot
  failure on a PR means output changed without going through the hook.
- **Retiring a class is `prune-manifest`; renaming is
  `restructure-sheets --rename-class`,** which carries annotations over.
- **Releases** are archived on Zenodo, with the DOI in `CITATION.cff`.

## Conventions

- **Language IDs are Glottocodes.** In anything a person reads, show
  `Name [glottocode]` (e.g. `Araona [arao1248]`) via
  `planars.languages.get_display_name`. Onboarding a language starts with
  `python -m coding lookup-lang <glottocode>`. IDs starting with `synth` are
  reserved for synthetic test languages (`synth0001`, built by
  `tests/make_synthetic_lang.py`) and skip Glottocode checks.
- **Edit sources, never their copies:** `schemas/languages.yaml`, not the
  manifest; `diagnostics_{lang_id}.yaml`, not the diagnostics Sheet (the
  daily refresh copies it there). Rules for the YAML: `schemas/__init__.py`.
- **Imported TSVs** are `coded_data/{lang_id}/{class_name}/{construction}.tsv`;
  archives go under `coded_data/{lang_id}/archive/{class_name}/`.
- **The keystone** is the row with `Position_Name == 'v:verbstem'`; it anchors
  every span and is never in the positions a span expands over (`planars/io.py`).
- **Analysis status** (`status` in `schemas/diagnostic_classes_status.yaml`;
  its values are listed in that file's header). **Only a coordinator (Adam
  Tallman or an equivalent domain expert) promotes a class out of
  `[AUTO-DERIVED]` or `[NEEDS REVIEW]`.** Claude may add "likely stable" notes or evidence
  summaries in the status comment, change `[AUTO-DERIVED]` to `[NEEDS REVIEW]`
  for a specific concern, or downgrade `stable` to `[NEEDS REVIEW]` on a bug
  or data problem — never promote.

## Running and testing

Commands: `python -m coding registry` (one line each; `--command NAME` for
detail) and `docs/coordinator-guide.md`; `make help` for short aliases.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # includes `-e .`
pytest                                  # full suite; run it before pushing
python generate_snapshots.py            # regenerate span snapshots; review with git diff tests/snapshots/
```

- **`requirements.txt` is a pinned lockfile; never edit it.** Edit
  `requirements.in`, then
  `pip-compile requirements.in --output-file requirements.txt --strip-extras`,
  and commit both (`--upgrade` to upgrade everything; `pip-tools` is installed
  separately).
- Notebooks run in Colab, not locally; Colab installs the package from GitHub,
  so a library change needs a version bump (the pre-commit hook does it for
  `planars/` changes; bump by hand for a `schemas/` change Colab reads).
- **Audits** happen in an `audit` issue: the daily refresh files one when
  none has closed in 30 days; open one by hand after a cross-cutting change.
  Steps: coordinator guide § "Audit procedure". The refresh already runs the
  checks; an audit reads warnings, confirms the checks ran, and reads what
  changed — comment findings on the issue, then close it.

## Commits

- **Commit after each logical unit of work** (a command working, a bug fixed,
  docs brought up to date, a refactor done), **and push after every commit**
  unless it is explicitly a work-in-progress checkpoint.
- **Keep `coded_data/` commits separate from code commits** — they are two
  repositories (commit inside `coded_data/` for data), with different authors
  and review needs.
- When a commit resolves an issue, put `Closes #N` in its message (one line
  per issue); for a partial fix, comment and close by hand.

## Documentation

**A docstring or comment that no longer matches the code is a bug, not
untidiness.** Fix it the moment you notice it, in the same change. The team is
one person, so nothing else will catch it; and Claude reads docstrings as a
shortcut to a file, so a stale one produces confidently wrong work. This covers
anything a reader could act on: commands and flags, paths, function and column
names, described behaviour, cross-references. Commands in coordinator-facing
output must also be fully runnable (`docs/tooling-design.md` item 5).

Check these at the end of any session where they could be affected:

| File | Update when |
|------|-------------|
| A module's docstring | Its behaviour changes — this is where behaviour is described |
| `CLAUDE.md` (this file, `planars/`, `coding/`) | A rule, convention or pointer changes |
| `NextPrompt.md` | The current thread or next action changes (it holds no state) |
| `docs/data-layer-progress.md` | **At every unit boundary of data layer work, in the same commit** |
| `docs/data-layer-implementation-plan.md` / `docs/data-layer-design.md` | A phase's scope or sequencing / a design decision changes |
| `docs/*.md` | A workflow, setup step or command changes |
| `README.md` | The annotated table of contents changes |
| `schemas/*.yaml` | Classes, criteria, terms, labels, conventions or language metadata change (what each owns: `schemas/__init__.py`) |
| `coded_data/{lang_id}/lang_setup/diagnostics_{lang_id}.yaml` | A language's classes, constructions or criteria change — then `sync-diagnostics-yaml --apply` |
| `notebooks/templates/*.ipynb` | Notebook boilerplate changes — then `generate-notebooks --apply` |
| `data_dependency_schema/*.yaml` | A bug traces to an undocumented dependency (see Design rules) |

When in doubt, update.

## Issue tracking

Issues: https://github.com/jcgood/planars/issues. Give every new issue at
least one label from the table below (`gh issue create --label …`).

- Labels are defined only in `schemas/issue_labels.yaml`: to add one, add an
  entry and commit — the daily refresh creates it on GitHub and the pre-commit
  hook regenerates the table below. Never create a label on GitHub by hand.
- **Sign every issue comment Claude posts** with `---` then `*klᴐd*` for
  Jeff's Claude (not "klɑd", a mistranscription) or `*klod*` for Adam's, so
  nobody mistakes it for the person's own.

### Labels

<!-- label-table:start — generated from schemas/issue_labels.yaml by `python -m coding issue --write-label-table`; edit that file, not this table -->
| Label | Filed by | Meaning |
|-------|----------|---------|
| `diagnostics` | by hand; generate-sheets | Requires linguistic validation from Adam before implementation. Also filed by `generate-sheets` when an element's prescreening value differs by position. Filter: `gh issue list --label diagnostics` |
| `linguistics` | by hand | Linguistically driven; needs domain expertise to settle. |
| `needs-input` | by hand | Waiting on input from Adam or another domain expert. |
| `Jeff` | by hand | Waiting on a decision from Jeff. |
| `design` | by hand | Architectural or forward-looking design decisions. |
| `infrastructure` | by hand | Tooling, scripts and workflows. |
| `codebook` | by hand | Criterion definitions and the rendered codebook (`schemas/diagnostic_criteria.yaml`, `render_codebook.py`). |
| `notebooks` | by hand | Colab notebooks and their templates. |
| `bug` | by hand | Something isn't working. |
| `enhancement` | by hand | New feature or request. |
| `documentation` | by hand | Improvements or additions to documentation. |
| `sheet-validation` | validation-report --apply (sheet-validation.yml) | Filed when `validate-coding` finds **errors** (or crashes). Advisory warnings never file or hold open an issue — they appear as context only. One open issue per *problem*, not per label: a later run reporting the same problem rewrites its body in place, notifying nobody, and a run reporting a different one closes it as superseded and files a new one. Auto-closed when no errors remain. |
| `needs-fixing` | validate-coding --notify (sheet-validation.yml) | One issue per language, for its annotator (issue #309; "To do in the {Name [glottocode]} sheets"): how many cells need fixing in which sheet (on tabs marked ready-for-review, listed in each sheet's Status tab), and which in-progress tabs the check marked ready-for-review because every cell was answered with no errors. Mentions the annotator when people.yaml has their GitHub username; otherwise a comment on the spreadsheet emails them. When the check marks a tab, a comment also mentions the other coordinators and the owner (people.yaml). A new notice is posted only when the list changes, not daily. Auto-closed when nothing is left. |
| `sheet-drift` | data-refresh.yml | Sheets are out of sync with the data model. Resolve: `update-sheets --apply`. Auto-closed when clean. |
| `diagnostics-yaml-error` | data-refresh.yml | `sync-diagnostics-yaml` found a blocking `diagnostics_{lang_id}.yaml` validation error — a malformed YAML, not schema inconsistency (`codebook-error`) — so the diagnostics Sheet was not updated. A non-blocking error (e.g. a required class not yet drafted) does not trigger this. Resolve: fix the YAML, run `sync-diagnostics-yaml --apply`. Auto-closed when clean. |
| `import-error` | data-refresh.yml | `import-sheets --apply` exited non-zero. The issue body contains the failure output. Auto-closed when import succeeds. |
| `codebook-error` | data-refresh.yml | `check-codebook` found schema inconsistencies in the daily refresh (CI also runs the check on every push, but files nothing). Auto-closed when the check passes. |
| `data-overwrite` | daily-refresh --apply (data-refresh.yml) | Today's refresh replaced a file whose last change, in the language's change log (`changes.tsv`), was made by a different command someone ran (a migration, restructure-sheets). The issue names each file and the archive copy holding the replaced version; compare it with the current file. Auto-closed when clean. |
| `planar-changed` | sync-planar (data-refresh.yml) | A language's planar file changed since its planar Sheet was last updated (`sync-planar`, which also renumbers position numbers typed in answers). Resolve: run the command in the issue body (`update-sheets --apply` for additions, `restructure-sheets ... --apply` for moved, renamed or removed positions). Auto-closed when a later run finds no planar changes. |
| `stale-manifest` | data-refresh.yml | Manifest entries have no matching class in `diagnostics_{lang}.yaml`. Resolve: `prune-manifest --apply`. Auto-closed when clean. |
| `integrity-error` | data-refresh.yml | `integrity-check` detected errors. Run `integrity-check` locally for details. Auto-closed when clean. |
| `dependent-stale` | data-refresh.yml | A dependent construction (e.g. nonpermutability `general`) is out of sync with its source (e.g. `element_prescreening`). Resolve: `generate-sheets --lang LANG --regen-construction CLASS:CONSTRUCTION`. Auto-closed when in sync. |
| `regen-dependents-error` | data-refresh.yml | `generate-sheets --regen-dependents` failed to regenerate a dependent tab (a real error, not `dependent-stale`, which needs a coordinator decision because annotation data already exists). Resolve: investigate the error, then re-run `generate-sheets --lang LANG_ID --regen-construction CLASS:CONSTRUCTION`. Auto-closed when clean. |
| `status-sheet-error` | data-refresh.yml | `generate-status-sheet --apply` failed during the daily refresh, so each language's status sheet still shows the previous run's percentages. The issue body has the failure output. Resolve: fix the cause, then run `python -m coding generate-status-sheet --apply`. Auto-closed when a later run succeeds. |
| `laminar-charts-error` | laminar-charts --apply (laminar-charts.yml) | `laminar-charts --apply`, run after each daily refresh, could not draw or upload some languages' contributor charts, so their Drive folders still hold the previous ones. The issue names each language and the stage; the reason is left out (it can quote the annotation, and the repository is public), and the issue gives the command that shows it. Resolve: fix the cause, then run `python -m coding laminar-charts --apply`. Auto-closed when a run draws every language that needs it. Also filed by the workflow itself when a setup step (R, system libraries) fails before the command runs. |
| `chapter-behind` | build-chapters --check --apply (data-refresh.yml) | One issue per language chapter ("Chapter behind its data — {Name [glottocode]}"): the daily refresh built the chapter in planars-data's `.papers/` against today's annotation and code without moving its pinned data version, and something the chapter shows changed (spans, the planar structure, the diagnostics, the analysis, a generated file, or a `\claim` in its prose). The issue gives counts and the prose to reread, never the annotation (the repository is public). Resolve: run the command in the issue; or, to keep the chapter on its version for now, leave the issue open (it is rewritten in place, notifying nobody). Auto-closed when the chapter matches its data again. |
| `overleaf-sync` | sync-overleaf --apply (data-refresh.yml) | One issue ("Overleaf sync — chapters"): `sync-overleaf --apply` found a file in planars-data's `.papers/` changed both in Overleaf and in planars-data since the last sync, or a file the chapter build makes edited in Overleaf, and kept the other version as a copy under `conflicts/` (on both sides); or the sync failed. The issue names the files, never their text (the repository is public). Resolve: merge each copy into its file (in Overleaf or locally), delete the copy; for a failure, fix its cause. Rewritten in place while open; auto-closed when `conflicts/` is empty and the sync succeeds. |
| `collaborator-notes` | check-notes --apply (data-refresh.yml) | A collaborator's notes Doc has new content (one issue per annotator). Resolve: paste the Claude prompt from the issue body, review proposed issues, file warranted ones, then close this issue. |
| `collaborator-comments` | check-comments --apply (data-refresh.yml) | An annotator wrote or changed a Comments cell in a class sheet (one issue per language, "Comments — {Name [glottocode]}"; a later run comments on it while it is open). Each comment is listed with its tab, row and answers. Resolve: paste the Claude prompt from the issue into a Claude Code session, which sorts the comments and drafts replies and issues for the coordinator to approve; then close this issue. |
| `collaborator-check` | import-sheets | An in-progress sheet has structural anomalies (missing rows, missing columns, >10% annotated-cell decrease). Not a blocking error — verify the change was intentional with the collaborator. |
| `label-drift` | issue --sync-labels --apply (data-refresh.yml) | A label someone created on GitHub by hand is on issues but not in `schemas/issue_labels.yaml`, so the tooling can't keep it in line. Resolve: add it to the registry (or take it off those issues). Auto-closed when every label in use is registered. |
| `audit` | daily-refresh --apply (data-refresh.yml) | Filed when no audit issue has been closed for 30 days. The issue is the instruction: Claude runs the steps in `docs/coordinator-guide.md` § "Audit procedure", comments the findings and what was done about each, and closes it; the closing date is the date of the last audit. |
| `door-violation` | the Drive door, at the end of any watched command | While the Drive door (`coding/drive_door.py`) is in watch mode for a kind of file, a write that breaks one of its rules still goes ahead, and the command files or updates this issue listing what broke. Each line is a bug in the command or a gap in the door's rules or spec. Resolve: fix whichever it is, then close. (The local-file door filed here too until it began refusing such writes, 2026-10-22.) |
| `sheet-updates` | restructure-sheets --apply | One long-lived issue per language ("Sheet updates — {lang_id}"); `restructure-sheets --apply` comments on it whenever that language's sheets get new URLs. Annotators subscribe to it. Never closed. |
| `planars-and-diagnostics` | proposal-sheets --apply (data-refresh.yml) | One issue per language ("Changes suggested — {Name [glottocode]} planars and diagnostics"): the annotator's planars and diagnostics sheet differs from what it was filled with, and the issue lists each change in plain words, and any row both they and the coordinator changed (a conflict). Kept current by `proposal-sheets --apply` in the daily refresh. Resolve: `accept-proposal --lang LANG_ID --apply`, which closes it with the decisions; it also closes by itself when the sheet holds no suggested change. (Called `proposal` until 2026-10-24.) |
<!-- label-table:end -->
