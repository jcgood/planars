# Plan: the annual report as a citable Zenodo output (English)

Jeff, 2026-11-25. Not started. A final annual report by Jeff and Adam,
published on Zenodo with a DOI: what the project's method is, what data it
has, and what the analysis shows. **English [stan1293] only.** The code
released with it includes the libraries first built on Chichewa (`laminar/`,
`planarsviz/`, the permutation and support tests), but no Chichewa data or
results.

## What gets published: three linked Zenodo records

| Record | Contents | Licence | Versions |
|---|---|---|---|
| **Report** (Zenodo type: Publication / Report) | the PDF, its LaTeX source and `values.tex` | CC BY 4.0 | one, final |
| **English dataset** (type: Dataset) | the annotation at one pinned change-log position: `planar_stan1293.tsv`, `diagnostics_stan1293.yaml`, every class's TSVs; the codebook (`render_codebook.py`); the spans and the analysis bundle, in a folder marked *derived*; a README and `CITATION.cff` | CC BY 4.0 (recommended; Adam's own annotation) | one per data freeze |
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
| Framework and the three hypotheses (tree, divide, word) | `schemas/terms.yaml`, the introduction chapter's generated parts; prose |
| Method: diagnostics, criteria, span rules | the codebook; `schemas/diagnostic_classes.yaml` |
| Method: annotation workflow (Sheets, the daily pipeline, change logs, version stamps) | prose, drawing on `docs/data-management.md`, `docs/data-layer-design.md`, `docs/change-log-design.md` |
| Method: the laminar analysis (families and forests, the four permutation tests, domain support, the resolution profile) | `laminar/INDEX.md`, the modules' docstrings, `NonCollaborative/REFERENCES.md`; prose |
| The English data: planar structure (38 positions, 33 slots, 5 zones as of 2026-11-08), 11 classes, 23 constructions, how complete (77.9%) | `chapter_data` values; the English chapter's planar and diagnostics fragments |
| Sample datasets | English; `synth0001` as a small worked example of every class; the 21 CCDB structures run through the same analysis (CC BY-SA, cited) to show the method on other languages |
| Results: English spans, strict and loose, complete and partial | the English chapter's span tables |
| Results: the hypotheses tested on English | the weekly analysis bundle at the pin; the word hypothesis needs #335 |
| Status and limits | each class's analysis status (`diagnostic_classes_status.yaml`), span rules not yet reviewed (#321), open data questions (#314, #298) |
| Next year | prose |

The draft is an unpublished manuscript, so it lives in planars-data's
`.papers/`, not in this repository, until it is released.

## What has to be built

1. **More than one volume in `.papers/`.** Today there is one `volume.yaml`
   (the De Gruyter book). The report is a second volume and won't be the
   last, so each volume gets its own folder with its own `volume.yaml`,
   built by `build-chapters`, and the daily check covers each. A change to
   `state_files.PAPERS_DIR` and `chapters/build.py`, with a one-time
   migration of the existing book into its folder.
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
5. **A new `coding` command, `export-release`** (planned; taking a language
   and a change-log position), which writes
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
7. **`CITATION.cff` kept in step with the version.** Found while planning:
   it says `0.1.0a19`, `pyproject.toml` says `0.1.0a71`. The version hook
   (`bump_version_hook.py`) should write both, so nothing has to be
   remembered.

## Before release: what has to be true

- **A freeze point for English** (a change-log position), chosen by Adam.
- **No Claude-drafted answers left**, or the release says how many and
  where (see the decisions).
- **Each span rule's status is printed** in the report beside its spans;
  none has been reviewed with Adam yet (#321, 0 of 7).
- **English's word chosen** (#335) if the report tests the word hypothesis.
- **Zenodo metadata**: ORCIDs, affiliations, funder and grant number,
  keywords, related identifiers (the 2024 volume's DOI, the CCDB).
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
3. **Data licence.** Recommended: CC BY 4.0 for English; the CCDB samples
   must stay CC BY-SA.
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
