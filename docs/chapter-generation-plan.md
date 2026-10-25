# Plan: generating the data-driven parts of the chapters

Jeff, 2026-10-25 (scoping; nothing built yet). Chapters are to be written
from the annotation: an introduction chapter with shared conventions, one
chapter per language with its own sections, and results sections. Most of
the prose is written by people; what this plan covers is the part that can
be produced from the project's own sources (the schemas, each language's
diagnostics file and planar file, the annotation, the analysis), the
outline that holds it, and keeping those parts current while the
annotation keeps changing under a chapter being written. Jeff and Adam
write LaTeX; authors who write in Word must be possible later.

## What can be generated, and from where

Every generated piece comes from a source the project already keeps, read
from that source, never copied into the manuscript by hand.

| Piece | Source | Kind |
|---|---|---|
| The framework terms (keystone, strict/loose, partial/complete spans) | `schemas/terms.yaml` | definitions, intro chapter |
| Each diagnostic class: what it tests, its criteria and their values, its span rule | `schemas/diagnostic_classes.yaml`, `schemas/diagnostic_criteria.yaml` (what `render_codebook.py` already renders) | definitions, intro chapter |
| Which classes are morphosyntactic, indeterminate, phonological | `diagnostic_classes.yaml` (domain type, subtype) | grouping of sections |
| The language's metadata: name, Glottocode, family, annotator, source | `schemas/languages.yaml`, Glottolog | chapter front matter |
| The planar structure: positions, their names and elements | `planar_{lang}.tsv` | a table |
| Which diagnostics apply to the language, their constructions and criteria | `diagnostics_{lang}.yaml` | section skeleton, short descriptions |
| The coded values: per element and construction | the annotation TSVs | tables (summarised; full tables in an appendix or the archived data) |
| Examples the annotator gave | the annotation's `Example` column | example lists (see decision 4) |
| The span each test gives, strict and loose, complete and partial | `planars.reports.language_spans` | a span table, and one templated sentence per test |
| How complete the annotation is | `language_completeness` | a note on each chapter while annotation is in progress |
| The laminar analysis: families, forests, boundary strength, the three permutation tests | the weekly full analysis (laminar plan Phase 4d) | results figures and numbers |
| The three hypotheses' tests (tree, divide, word) | the same analysis | results sections, sentences with the numbers |

**Not generated:** the introduction's argument, a language's background and
analysis, why a construction was chosen as a test, discussion of what a
result means. Those are prose slots in the outline.

Missing today, needed before a chapter can be generated:
- **A description per construction** (what the construction is, with its
  frame), already asked for (#318 (e)): `diagnostics_{lang}.yaml` gets a
  `description` per construction, written by the annotator through the
  proposal sheet. The chapters make this more pressing.
- **Structured examples**, if generated example lists should be glossed
  (decision 4).

## How it fits together

**One command builds a chapter's generated parts** (working name
`python -m chapters build --lang stan1293`), from a pinned version of the
data (below), into a folder of fragments:

- `fragments/` — one file per generated piece (`planar_table.tex`,
  `diagnostic_ciscategorial.tex`, `spans_table.tex`, `results_forest.pdf`),
  always overwritten by the build, never edited by hand;
- `values.tex` — every number and short value a sentence might cite, as a
  named macro (`\pv{stan1293.spans.total}`, `\pv{stan1293.families.morsyn}`),
  so prose cites a value by name and never types it;
- `outline.tex` — the chapter skeleton: sections in a fixed order taken from
  the schema (class order, grouped by domain type), each generated fragment
  `\input` where it goes, and a prose slot (`\input{prose/<section>}`) per
  section;
- `prose/` — the hand-written parts. The build creates a stub for a slot
  that has none and **never overwrites one that exists**. A slot whose
  section has gone (a class retired) is reported, not deleted.

Prose files and generated fragments never share a file, so regenerating
can never touch what a person wrote. That one rule is what makes "rebuild
whenever the data changes" safe.

**The introduction chapter** is built the same way from the schemas alone
(terms, classes, criteria, span rules), with the same split into generated
fragments and prose slots. **The overall outline** of a volume or paper
(introduction, the language chapters in a chosen order, a comparative
results chapter) is one small file listing the parts; the build assembles
it.

**Templates, not code, hold the wording** of generated sentences ("The
ciscategorial test gives a strict span from position 9 (`v:…`) to 20 …"):
a Jinja2 template per piece, so changing a sentence means editing a
template, and the same template data can render LaTeX or Markdown.

## Keeping the chapter current as the annotation changes

The annotation will keep changing while a chapter is written. The design
makes every change visible and nothing silently stale:

1. **A chapter is built against a pinned data version**, not whatever is
   current: a planars-data commit (and, for publication, the Zenodo release
   the project already makes, `CITATION.cff`). The pin is recorded in the
   chapter (`data.lock`) and printed in its front matter, so a reader knows
   what the numbers come from.
2. **Moving the pin is a deliberate step with a report.** `chapters update
   --lang stan1293` builds against the new data alongside the old and
   reports, in plain words, what changed: spans that moved, numbers that
   changed, table rows added or removed, examples edited, sections added
   or gone. Fragments update in place; the report says which prose sections
   sit next to a change.
3. **Prose that states a data fact says so.** A sentence asserting
   something about the data cites it, either as a value
   (`\pv{stan1293.span.ciscategorial.strict}`, which simply updates) or,
   for a claim the prose argues from, as a checked claim
   (`\claim{stan1293.span.ciscategorial.strict}{9--20}`): the build compares
   the claim with the data and lists every claim that no longer holds, with
   its file and line, and the PDF marks it. A changed value never needs
   finding by eye; a broken argument is listed, not discovered by a reader.
4. **The daily pipeline does the noticing.** Once chapters exist, a step
   after the refresh builds each chapter against current data (without
   moving its pin) and files one issue per chapter when the pinned and
   current versions differ in a way that touches it ("English chapter: 3
   spans and 2 claims changed since its data version; run `chapters update
   --lang stan1293` to review"). Nobody has to remember to check.

## Where the chapters live

Unpublished manuscripts must not be in this public repository. The
generator lives here (`chapters/`, beside `laminar/`); the manuscripts and
their built fragments live in a **private repository** (a new
`planars-papers`, or one per volume), as the annotation lives in
planars-data. If Overleaf is wanted for co-writing, Overleaf's git link
points at that private repository.

## LaTeX and Word

- **LaTeX is the source for Jeff and Adam.** If the venue is Language
  Science Press, fragments use its conventions (`langscibook`, `booktabs`
  tables, `langsci-gb4e` examples, biblatex), so the volume builds with
  their template unchanged.
- **Word authors, later, in two steps:**
  - *reading and commenting:* `pandoc` turns a built chapter into .docx;
    prose, tables and figures come through well; glossed examples less so;
  - *writing:* a Word author writes their prose in a .docx with the same
    named values as placeholders (`{{stan1293.spans.total}}`) and slot
    headings; a small converter fills the values (for review) and, for the
    volume, pandoc turns the prose into LaTeX for the slots. Glossed
    examples in Word would need a fixed table layout the converter reads.
  Because generated sentences come from templates, the same fragments can
  also be rendered as Markdown, which pandoc turns into .docx more cleanly
  than it converts LaTeX.

## Phases

1. **The data layer for chapters**: one function that gathers everything a
   chapter cites for a language at a given data version (spans, counts,
   completeness, metadata, analysis results) into one named set of values,
   with the analysis results from the weekly run (laminar plan 4d), and its
   tests. No LaTeX yet.
2. **Fragments and values**: templates for the introduction's definitions,
   the planar table, each class's section, the span table; `values.tex`;
   `chapters build`. English first.
3. **Outline and prose slots**: the skeleton, stubs, the private
   repository, the volume outline file.
4. **The update report and checked claims**: `chapters update`, `\claim`.
5. **The daily check**: the step after the refresh and its issue (a new
   label).
6. **Word**: pandoc export for reading; later the placeholder path for
   writing, when there is a Word author.

Prerequisites from other threads: construction descriptions (#318 (e));
the weekly full analysis (laminar plan 4d), whose results the results
sections cite; the span rules settled with Adam (#321), since a chapter
states them.

## Decisions for Jeff

1. **Venue and template.** A Language Science Press volume like the CCDB
   book (then its template from the start), a journal paper, or both?
   This sets the fragment conventions.
2. **Where the manuscripts live**: a new private repository (recommended,
   with Overleaf linked to it if wanted), or Overleaf alone (then the
   fragments are pushed into it by the build).
3. **How much the generated sentences say.** Recommended: one templated
   sentence per test stating its span, plus tables; anything interpretive
   stays prose.
4. **Examples.** The `Example` column is free text. Generated example lists
   either quote it as is (cheap, unglossed), or the annotation gains
   structured examples (form, gloss, translation, source), which makes
   generated glossed examples possible and is a schema change for every
   language. Recommended: decide with Adam before English's chapter needs
   examples.
5. **Who writes the per-language prose**: the annotator (then the slots and
   their stubs are written for them, and Word support moves earlier), or
   Jeff and Adam.
