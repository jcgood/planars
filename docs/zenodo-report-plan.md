# Plan: a progress report as a citable Zenodo output (English)

Jeff, 2026-11-25. Being built (see "What has to be built"). The first
progress report by Jeff and Adam, covering all the project's work to date,
published on Zenodo with a DOI: what the project's method is, what data it
has, and what the analysis shows. **English [stan1293] only.** The code
released with it includes the libraries first built on Chichewa (`laminar/`,
`planarsviz/`, the permutation and support tests), but no Chichewa data or
results.

## What gets published: three linked Zenodo records

| Record | Contents | Licence | Versions |
|---|---|---|---|
| **Report** (Zenodo type: Publication / Report) | the PDF, its LaTeX source and `values.tex` | CC BY 4.0 | one per report: a later report is a record of its own, not a new version of this one |
| **English dataset** (type: Dataset) | the annotation at one pinned change-log position: `planar_stan1293.tsv`, `diagnostics_stan1293.yaml`, every class's TSVs; the codebook (`render_codebook.py`); the spans and the analysis bundle, in a folder marked *derived*; a README and `CITATION.cff` | CC0 (decided 2026-11-26) | one per data freeze |
| **Software** (type: Software) | `planars` at a tagged release, through Zenodo's GitHub link (one DOI for all versions, one per release); includes `planarsviz/` | MIT (as now) | one per release |

Three, not one, because they change at different rates, carry different
licences and have different authors (Adam is the annotator of the data).
The report cites both others by DOI and states the data position and code
version every number comes from; the dataset and software records point
back to the report ("is documented by").

Data is plain TSV plus the codebook for this release. CLDF (#84, #88) stays
open as its own piece of work; nothing in this plan needs it, and its open
questions (how to export `na`, what counts as finished) would hold up the
report.

## What the report contains, and where each part comes from

Every number in it is a named value (`\pv{...}`) read from the pinned data,
so the report can be rebuilt from the dataset and software records alone.

| Section | Source |
|---|---|
| Summary of the year | prose (Jeff, Adam) |
| Method (seven parts) | see "The method section" below |
| Who did what: people and Claude | see "Human and Claude contributions" below |
| The English data: planar structure (38 positions, 33 slots, 5 zones as of 2026-11-08), 11 classes, 23 constructions, how complete (77.9%) | `chapter_data` values; the English chapter's planar and diagnostics fragments |
| Sample datasets | English; `synth0001` as a small worked example of every class; the 21 CCDB structures run through the same analysis (CC BY-SA, cited) to show the method on other languages |
| Results: English spans, strict and loose, complete and partial | the English chapter's span tables |
| Results: the hypotheses tested on English | the weekly analysis bundle at the pin; the word hypothesis needs #335 |
| Status and limits | each class's analysis status (`diagnostic_classes_status.yaml`), span rules not yet reviewed (#321), open data questions (#314, #298) |
| Next year | prose |

## The method section

The method covers the software design as well as the linguistics (Jeff,
2026-11-25): the principles are part of why the data can be trusted, and
they are already written down, so the report draws on them rather than
restating them from memory.

| Part | What it says | Drawn from |
|---|---|---|
| 1. Framework and diagnostics | the hypotheses, the terms, each class's criteria and span rule; what extends Tallman, Auderset & Uchihara 2024 (strict/loose spans, partial/complete positions, the named `*-combines` criteria), marked as such | `schemas/terms.yaml`, `schemas/diagnostic_classes.yaml`, the codebook, `docs/analyses.md` |
| 2. Annotation for language experts who don't program | design for "John" (a browser and a Sheet, no terminal); the GitHub issue as the instruction; the daily pipeline, so nobody remembers a sequence of steps; annotators' proposals reviewed by issue | CLAUDE.md "Who the tooling is for", `docs/collaborator-guide.md`, `docs/tooling-design.md`, `docs/coordinator-guide.md` |
| 3. Principles of the research software | one owner for every fact (and the failures that taught it); aggregate late, never store derived values in the annotation; definition files apart from data files; explicit, not implicit (refuse what can't be placed); light maintenance (regenerate, never keep a copy by hand); checkers don't multiply | `docs/data-layer-design.md`, `docs/data-management.md`, `docs/hidden-facts-inventory.md`, CLAUDE.md "Working rules" and "Design rules" |
| 4. Provenance as the schemas change | the schemas are outputs of the research; change logs with typed change classes; version stamps on every result; chapters pinned to a data position; checked claims; links to the schema- and ontology-evolution literature | `docs/change-log-design.md`, `docs/result-stamp-design.md`, `docs/plain-record-design.md`, `schemas/changes.tsv`, `docs/references.md` |
| 5. Safeguards on the data | the Drive door and local-file door; unlogged-source, integrity and codebook checks; issues filed by the pipeline itself; the frozen test copy of Drive | `docs/drive-door-design.md`, `docs/ownership-design.md`, `data_dependency_schema/SCHEMA.md`, `docs/testing.md` |
| 6. Analysis methods | laminar families and forests; the four permutation tests; domain support and the resolution profile, with the phylogenetics methods they borrow | `laminar/INDEX.md`, the modules' docstrings, `NonCollaborative/REFERENCES.md`, `docs/laminar-analysis-plan.md` |
| 7. Reproducibility | rebuilding every number from the dataset and software records; the rebuild check | item 6 under "What has to be built" |

Each part is a prose slot with written instructions in the report's
outline, and cites values (the number of classes, change-log lines, tests)
rather than typing them.

## Human and Claude contributions

The report says what people did and what Claude did, and how Claude's
work was kept under control (Jeff, 2026-11-25). Everything it says comes
from records the project already keeps, counted by a script at the report's
data position, not from recollection:

| What | Record | Starting point (2026-11-25) |
|---|---|---|
| Code and docs written in Claude sessions | `Co-Authored-By: Claude` lines in this repository's commits | 1,117 of 1,324 commits (merges left out; 32 more by the pipeline), all since 2026-03-15; before that, everything is Jeff's (tag `pre-claude-noncollaborative`) |
| Comments Claude posted | issue comments signed `klᴐd` (Jeff's Claude) or `klod` (Adam's), whose Claude read from the account | 85 of 506 (Jeff's 80, Adam's 5); 254 by Jeff and Adam themselves, 167 by the pipeline |
| Annotation Claude drafted | Source cells marked "Claude draft"; the language's change log (which command wrote each change) | phrasal_accent only, released marked (Adam replaces each once checked) |
| Decisions | `schemas/decisions.tsv`, `coded_data/stan1293/decisions.tsv`; `diagnostics`/`linguistics` issues | every one made by Jeff or Adam |
| Limits on Claude | CLAUDE.md: only a coordinator promotes a class's status; ask before live writes and linguistic calls; sign every comment | CLAUDE.md |

The point to make plainly: the linguistic judgements (the diagnostics, the
annotation, every decision, every promotion of a span rule) are Jeff's and
Adam's; Claude wrote most of the tooling, under written rules, with Jeff
directing it and reviewing what it did. A commit line means "made in a
Claude session", not a share of authorship, and the report says so.
The counts are named values from `chapters/contributions.py` (item 8; its
docstring lists them and the rules for each).

The draft is an unpublished manuscript, so it lives in planars-data's
`.papers/`, not in this repository, until it is released.

## What has to be built

1. **Built 2026-11-25: more than one volume in `.papers/`.** Each volume
   is its own folder (`.papers/<volume>/`) with its own `volume.yaml`,
   pins and Overleaf project; `build-chapters`, its daily check and
   `sync-overleaf` cover each (`--volume NAME`; a new name starts a
   volume). The book moved to `.papers/book/`
   (`migrations/papers_into_volume_folders.py`). **The report's volume was
   started 2026-11-26** (`.papers/report/`: title "Report of the
   constituency typology project (November 2026)", the date set by hand at
   release; venue `report`; authors alphabetical with a note; parts intro,
   method, stan1293, results). Details:
   `docs/chapter-generation-plan.md` § "More than one volume".
2. **Built 2026-11-25: a results chapter kind**, the part `results`
   (`build-chapters --results`): the analysis summary and the three
   permutation tests' tables, citing values, a prose slot per hypothesis,
   and figures (the combined forest and the domain-coloured span bars,
   listed in `outline.yaml`). Chapters now read the weekly bundles in
   `.bundles/`. Details: `docs/chapter-generation-plan.md` § "The results
   chapter".
3. **Built 2026-11-25: a report venue file** (`chapters/venues/report.sty`):
   an 11pt article, letter paper, 1in margins, links (hyperref, for the
   DOIs). A venue file now also sets the document class and the heading a
   part starts at, so in the report each part (introduction, English,
   results) is a numbered section and every heading is one level below the
   book's (`chapters/tex.py`). Intro, English and results compile under it
   (a test, run for every venue). Added 2026-11-26: a volume's authors and
   a note on them (`volume.yaml`'s `authors`, `author_note`), no build
   date on the title page, and the part `method` (prose only: one slot per
   part of "The method section" below, each naming the documents to draw
   on). A language chapter now prints three examples per construction,
   the annotator's own first, and counts the rest (English's phrasal_accent
   examples had filled some 250 pages). **Built 2026-11-26: the report's
   other parts of its own** ("What the report contains"): `summary` and
   `next` (prose only); `contributions` (who did what: item 8's counts in
   its own `values.tex`, up to the end of the day of the volume's latest
   language pin, counted again only when that moves, refused in a shallow
   clone; a table and two prose slots); `status` (each class's span-rule
   and criteria status, in words, beside a prose slot on the open
   questions). A language chapter now prints each class's span-rule status
   above its spans (the decision under "Before release"). Details:
   chapters/build.py's docstring.
4. **Built 2026-11-25: the laminar modules in the bundle**: domain
   support, the resolution test and the profile exported behind permutation
   flags and run weekly, so the report's numbers come from the pinned
   bundle, not from standalone runs. English gets domain support and the
   profile; its resolution test waits on its word (#335). No chart and no
   chapter value reads them yet. Details: `docs/laminar-analysis-progress.md`
   ("Domain support and resolution").
5. **Built 2026-11-25: `export-release`** (`coding/export_release.py`, whose
   docstring says what the folder holds; English's dry run: 783 files,
   stopped only by the Claude drafts). As planned, it writes
   the dataset folder from one change-log position (reusing the past-version
   copy `chapter_data` already makes), through the local-file door, with a
   record in `operations.yaml`. It refuses, listing each case, when a source
   is unlogged, or when an answer's Source still says it is a Claude draft
   (English's phrasal_accent has them, 2026-10-27). It leaves out
   `people.yaml` and the Comments column (notes between annotator and
   coordinator). Tests on `synth0001`.
6. **Built 2026-11-26: a rebuild check**: from an unpacked dataset folder
   and the software at its tag, rebuild `values.tex` and compare with the
   released one: `python -m chapters rebuild-check --release DIR --values
   FILE` (`chapters/rebuild_check.py`; the dataset's README says how). It
   first checks every file's sha256 against `release.json` and that the
   software is the release's version (code version, schema files), then
   works every value out from the folder (`chapters.data.release_data`,
   the analysis from `derived/analysis/`) and lists each that differs.
   `tests/test_export_release.py` runs it on English: all 2,407 values,
   the analysis included, come back as built from planars-data at the same
   position; the spans likewise match `derived/spans.tsv`. The
   contribution counts (item 8) are outside it, as item 8 says.
   **Found and fixed 2026-11-26:** the software record is a `git archive`
   of the tag, with no git history, and three things read git. The chart
   code's fingerprint (`laminar.contributor_charts.code_version()`, which
   the results chapter's figures use) now works git's record out from the
   files when there is no git, the same value line for line
   (`tests/test_chart_code_files.py` checks against git);
   `test_no_retired_term_reappears` reads every file of such a copy; and
   the test of `log-change`'s "before" copy, a command run only in the
   repository, skips there. A trial archive (NonCollaborative/ left out,
   planars-data linked in) passes or skips every test.
7. **`CITATION.cff` kept in step with the version.** Found while planning:
   it said `0.1.0a19`, `pyproject.toml` `0.1.0a71`. Done 2026-11-25 by
   deleting the copy (and the stale `date-released`): Zenodo's GitHub link
   records both from the release tag (coordinator guide § "Making a
   release").

8. **Built 2026-11-25: the contribution counts as values**
   (`chapters/contributions.py`, `python -m chapters contributions
   [--until TIME]`): commits, signed comments, decisions and the models
   named in the commit lines, up to the time of the report's data
   position. Found while building: 14 commits from a cloud session end in
   a `Claude-Session:` line that stops git reading their co-author line, so
   the count reads every line of the message. These counts come from git
   history and GitHub, which the software record (files at one tag) does
   not hold, so the rebuild check (item 6) can't rebuild them from the
   Zenodo records alone; the report says where they are read from.
9. **Built 2026-11-25: the dataset's `CITATION.cff`, written by
   `export-release`**: the authors are the language's `dataset_authors`
   in `schemas/languages.yaml`, in that order (2026-11-26), with ORCIDs and
   affiliations read from this repository's `CITATION.cff` at each
   export, never copied; the licence is `--licence` (CC-BY-4.0 or
   CC0-1.0), and a release that names none is refused, so the licence is
   always a stated choice, not a default (English: CC0, below).

Order of building (Jeff, 2026-11-25): 8, then 9, then 1 (dry run shown to
Jeff before planars-data's `.papers/` is moved), then 2 and 3.

## Before release: what has to be true

- **A freeze point for English** (a change-log position): **line 59
  (2026-11-08)**, set 2026-11-26 ("now": no change has been logged since,
  so it is the pin the report was already built at). `export-release
  --lang stan1293 --position 59 --licence CC0-1.0` dry run: 784 files, no
  refusal.
- **Each span rule's status is printed** in the report beside its spans
  (decided; built 2026-11-26); none has been reviewed with Adam yet (#321,
  0 of 7).
- **English's word chosen** (#335) if the report tests the word hypothesis.
- **Zenodo metadata**: keywords (no funder: decided), related
  identifiers (the 2024 volume's DOI, the CCDB). Authors' ORCIDs and
  affiliations are in `CITATION.cff` (2026-11-25), which the dataset's
  citation file reads rather than copies.
- **Zenodo's GitHub link is on for `jcgood/planars`** (2026-11-25; the
  repository's webhook sends release events to Zenodo), so the next GitHub
  release gets a DOI: make it only when the software record is meant to
  exist.
- **No trial run on Zenodo's sandbox** (Jeff, 2026-11-26: skipped). The
  rebuild check ran instead on the export written locally at line 59: all
  2,407 values rebuilt as released (2026-11-26). Run it once more on the
  dataset downloaded from Zenodo after publishing.

## Order of publishing

Software tag first, then the dataset, then the report, because the report
prints the other two DOIs. Zenodo can reserve a DOI before a record is
published, so the report's front matter can carry them during the final
build.

## Phases

1. Decisions below (Jeff, Adam).
2. Items 4 and 7 under "What has to be built" (needed whatever is decided).
3. Items 1–3, 5, 6.
4. Prose: drafted by Claude for every slot (2026-11-26, Jeff: the point
   is getting to Zenodo, not work for the authors), each opening with
   `\claudedraft{date}`, which prints "Drafted by Claude" and which the
   authors delete once a slot is theirs; Adam sets the freeze point.
5. Skipped (no sandbox run, above); the rebuild check passed on the
   local export.
6. Publish; DOIs into `CITATION.cff`, the README and the dataset's
   `CITATION.cff`.

## Open with Jeff and Adam

1. Settled 2026-11-26: Jeff's and Adam's own progress report (see
   "Decided").
2. Settled 2026-11-26: three records (see "Decided").
3. Settled 2026-11-26: the data licence is CC0 (see "Decided").
4. Settled 2026-11-26: Claude-drafted answers are released marked (see
   "Decided").
5. Settled 2026-11-26: unreviewed span rules are released marked by status.
6. Settled 2026-11-26: `NonCollaborative/` is left out of the software
   archive.
7. Settled 2026-11-26: authors and order on each record.

Nothing is open: every question above is settled (see "Decided").

## Decided (don't re-ask)

- **The method covers the software design**, in the seven parts above
  (Jeff, 2026-11-25).
- **The report states human and Claude contributions**, from the records
  above (Jeff, 2026-11-25).
- **The report is Jeff's and Adam's own** (Jeff, 2026-11-26): each
  uses it in reporting to their own employer, so there is no funder
  field. This first one covers all the project's work to date; later ones
  may come more often than yearly, each its own Zenodo record citing its
  own data freeze. No deadline given.
- **Three Zenodo records**, as under "What gets published" (Jeff,
  2026-11-26).
- **Claude-drafted answers are released as they are, marked** (Jeff,
  2026-11-26: the data as it is, stated openly). `export-release` counts
  them per construction in the dataset's README and `release.json`, and
  the report says how many there are; the release doesn't wait for Adam
  to check them.
- **English's dataset is CC0** (Jeff and Adam, 2026-11-26): release it with
  `export-release --licence CC0-1.0`. The README and `CITATION.cff` ask for
  a citation rather than require one. The CCDB samples stay CC BY-SA and
  the report's own text stays CC BY.
- **Span rules are released marked by status** (Jeff, 2026-11-26): the
  report prints each rule's status beside its spans; release doesn't wait
  for #321's review.
- **`NonCollaborative/` is left out of the software archive** (Jeff,
  2026-11-26: its Chichewa results are coded under the old system).
  `.gitattributes` marks it `export-ignore`, which Zenodo's GitHub link
  follows; the tests that read it skip without it. The README says so.
- **Authors** (Jeff, 2026-11-26):
  - dataset: the language's `dataset_authors` (`schemas/languages.yaml`):
    English, Adam then Jeff; Araona, if it is ever released, Adam alone;
  - software: Jeff first, then Adam (the repository's `CITATION.cff`);
  - report: alphabetical (Good, Tallman), with a note on the title page
    saying the order is alphabetical. Written into the report volume's
    front matter when the volume is started.
