# Plan: the annual report as a citable Zenodo output (English)

Jeff, 2026-11-25. Being built (see "What has to be built"). A final annual report by Jeff and Adam,
published on Zenodo with a DOI: what the project's method is, what data it
has, and what the analysis shows. **English [stan1293] only.** The code
released with it includes the libraries first built on Chichewa (`laminar/`,
`planarsviz/`, the permutation and support tests), but no Chichewa data or
results.

## What gets published: three linked Zenodo records

| Record | Contents | Licence | Versions |
|---|---|---|---|
| **Report** (Zenodo type: Publication / Report) | the PDF, its LaTeX source and `values.tex` | CC BY 4.0 | one, final |
| **English dataset** (type: Dataset) | the annotation at one pinned change-log position: `planar_stan1293.tsv`, `diagnostics_stan1293.yaml`, every class's TSVs; the codebook (`render_codebook.py`); the spans and the analysis bundle, in a folder marked *derived*; a README and `CITATION.cff` | CC BY 4.0 or CC0 (open question 3) | one per data freeze |
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
| Annotation Claude drafted | Source cells marked "Claude draft"; the language's change log (which command wrote each change) | phrasal_accent only, to be replaced by Adam |
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
   (`migrations/papers_into_volume_folders.py`). The report's volume is
   started once items 2 and 3 give it a chapter kind and a venue. Details:
   `docs/chapter-generation-plan.md` § "More than one volume".
2. **A results chapter kind** in `chapters/templates/outline.yaml` (the
   chapter plan names it; only `language` and `intro` exist): the
   hypotheses' tests and the laminar figures, citing values.
3. **A report venue file** (`chapters/venues/report.sty`): an article-like
   layout, not the book's.
4. **The laminar modules in the bundle** (already the next step in
   `docs/laminar-analysis-progress.md`): domain support, the resolution
   test and the profile exported behind permutation flags and run weekly,
   so the report's numbers come from the pinned bundle, not from
   standalone runs.
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
6. **A rebuild check**: from an unpacked dataset folder and the software at
   its tag, rebuild `values.tex` and compare with the released one. A test,
   so the claim "rebuildable from the records" is checked, not hoped.
   Built for the spans 2026-11-25 (`tests/test_export_release.py`: the
   spans derived from the released folder are its `derived/spans.tsv`);
   `values.tex` waits for the report volume (item 1).
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
   `export-release`**: authors, ORCIDs and affiliations read from this
   repository's `CITATION.cff` at each export, never copied; the licence
   is `--licence` (CC-BY-4.0 or CC0-1.0), and a release that names none is
   refused, so open question 3 is settled by whoever runs it, not by a
   default. The authors are in the repository file's order (Jeff, then
   Adam) until open question 7 is answered.

Order of building (Jeff, 2026-11-25): 8, then 9, then 1 (dry run shown to
Jeff before planars-data's `.papers/` is moved), then 2 and 3.

## Before release: what has to be true

- **A freeze point for English** (a change-log position), chosen by Adam.
- **No Claude-drafted answers left**, or the release says how many and
  where (see the decisions).
- **Each span rule's status is printed** in the report beside its spans;
  none has been reviewed with Adam yet (#321, 0 of 7).
- **English's word chosen** (#335) if the report tests the word hypothesis.
- **Zenodo metadata**: funder and grant number, keywords, related
  identifiers (the 2024 volume's DOI, the CCDB). Authors' ORCIDs and
  affiliations are in `CITATION.cff` (2026-11-25), which the dataset's
  citation file should read rather than copy.
- **Zenodo's GitHub link is on for `jcgood/planars`** (2026-11-25; the
  repository's webhook sends release events to Zenodo), so the next GitHub
  release gets a DOI: make it only when the software record is meant to
  exist.
- **A trial run on Zenodo's sandbox** (sandbox.zenodo.org) for all three
  records before the real ones.

## Order of publishing

Software tag first, then the dataset, then the report, because the report
prints the other two DOIs. Zenodo can reserve a DOI before a record is
published, so the report's front matter can carry them during the final
build.

## Phases

1. Decisions below (Jeff, Adam).
2. Items 4 and 7 under "What has to be built" (needed whatever is decided).
3. Items 1–3, 5, 6.
4. Prose: Jeff and Adam write their slots; Adam sets the freeze point and
   settles the Claude drafts.
5. Sandbox run; rebuild check against the downloaded records.
6. Publish; DOIs into `CITATION.cff`, the README and the dataset's
   `CITATION.cff`.

## Open with Jeff and Adam

1. **Whose annual report, and by when?** (a funder's, the department's,
   the project's own): sets the funder field, the period covered and the
   schedule.
2. **Three records or one?** Recommended: three (above).
3. **Data licence.** CC BY 4.0 (the typology norm: WALS, Glottolog,
   Grambank) or CC0. Jeff leans to CC0 (2026-11-25); Adam to agree, as the
   annotator. Under CC0 the README and `CITATION.cff` ask for a citation
   rather than require one. The CCDB samples must stay CC BY-SA whatever
   is chosen; the report's own text stays CC BY.
4. **The Claude-drafted phrasal_accent answers:** wait for Adam to replace
   them (recommended), or release them marked.
5. **Unreviewed span rules:** review some with Adam before release, or
   release with every rule marked by its status (recommended: mark; the
   report is a progress report).
6. **Chichewa material in the software archive.** `NonCollaborative/`
   holds nyan1308 results and is already public on GitHub, but a DOI makes
   it a permanent citable copy. Leaving it out of the archive
   (`export-ignore` in `.gitattributes`, which Zenodo's GitHub link
   respects) also leaves out data some `laminar` tests read
   (`laminar.datasets.NC`), so those tests would skip in the archived copy.
   Recommended: leave it out and say so in the README.
7. **Authors and order** on each record (the data: Adam first?).

## Decided (don't re-ask)

- **The method covers the software design**, in the seven parts above
  (Jeff, 2026-11-25).
- **The report states human and Claude contributions**, from the records
  above (Jeff, 2026-11-25).
