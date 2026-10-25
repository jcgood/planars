# Plan: generating the data-driven parts of the chapters

Jeff, 2026-10-25. Phases 1 and 2 built 2026-10-25 (see "Phase 1 as
built" and "Phase 2 as built" at the end); the rest not started. Chapters are to be written
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
- **Structured examples** (form, gloss, translation, source) for every
  language whose examples need glossing (decision 4).

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
their built fragments live in the private planars-data repository, in
`coded_data/.papers/` (decision 2, which says why a dot-folder and what
follows from it).

## LaTeX and Word

- **LaTeX is the source for Jeff and Adam.** The venue is De Gruyter
  (decision 1), whose LaTeX package is `dgruyter` (CC BY 4.0; on Overleaf
  as "Manuscript Template for Walter de Gruyter Books and Journals"; built
  on the standard `book` class, with a `\contribution` block for a chapter
  in an edited volume). The current template comes from the editor after
  the contract, and the final PDF needs De Gruyter's house font. So the
  fragments are tied to no class: plain LaTeX that `dgruyter` and `book`
  both take (`booktabs` tables, `graphicx` figures, biblatex citations),
  and **every glossed example goes through one macro of our own**
  (`\planarsex{form}{gloss}{translation}{source}`), defined in one file per
  venue on top of whichever glossing package that venue wants (gb4e,
  expex, langsci-gb4e). When the series editor sends the real template,
  that file is the only thing that changes.
- **Word authors, before the second language's chapter** (annotators write
  their language's slots, decision 5), in two steps:
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
6. **Structured examples**: the per-language `examples` field, the example
   columns on the annotation sheets for glossed languages, the example
   macro and its venue file. Can run alongside 2–5; must be done before a
   glossed language's chapter.
7. **Word**: pandoc export for reading, then the placeholder path for
   writing; before the second language's chapter.

Prerequisites from other threads: construction descriptions (#318 (e));
the weekly full analysis (laminar plan 4d), whose results the results
sections cite; the span rules settled with Adam (#321), since a chapter
states them.

## Decisions (Jeff, 2026-10-25; don't re-ask)

1. **Venue: De Gruyter.** Fragments are class-neutral, with one macro for
   examples defined per venue (see "LaTeX and Word"). Ask the series editor
   for the current template and any glossing convention once there is a
   contract.
2. **Manuscripts live in planars-data, in `coded_data/.papers/`** (Jeff,
   2026-10-25, replacing "a new private GitHub repository"; a starting
   point he may revise later, so build nothing that makes moving them
   hard, but don't re-ask). A dot-folder
   because every command that loops over planars-data takes a plain
   top-level folder for a language and skips only dot-folders (as
   `.state/` and `.analysis/`). Consequences for Phase 3: anyone with
   access to planars-data can read the manuscripts; the build's writes
   there are tooling writes to planars-data, so they go through the
   local-file door (`coding/file_door.py`, a new kind) like every other;
   the daily refresh commits to the same repository, so pull before
   writing; Overleaf's GitHub sync takes a whole repository, so co-writing
   in Overleaf would need another route (decide if it is wanted).
3. **Generated text: one templated sentence per test stating its span,
   plus tables.** Anything interpretive is prose.
4. **Examples are structured** (form, gloss, translation, source) in the
   annotation, for every language whose examples need a gloss and a
   translation. **English is the exception**, because the metalanguage is
   English: its examples are plain sentences. This is recorded per
   language, not as a named exception in code: a field in
   `schemas/languages.yaml` (working name `examples: unglossed` for
   English, `glossed` for the rest), which the annotation sheets (which
   columns an example has) and the example macro both read. A schema
   change for the annotation sheets, so it goes through the usual schema
   steps (`integrity-check`, `check-codebook`, `update-sheets`); Adam to be
   told on an issue before the columns appear.
5. **Prose is mixed:** Jeff and Adam write the introduction and results;
   each annotator writes their language's background and analysis slots.
   So the slots carry short written instructions, and Word support (the
   placeholder path) is needed before the second language's chapter.

## Phase 1 as built (2026-10-25)

- **`chapters/data.py`, `chapter_data(lang_id, version=None)`**: a
  language's named values and tables at one planars-data version. What
  each value is called and where it comes from is the module docstring;
  `python -m chapters values --lang stan1293 [--version COMMIT]` prints
  them (English today: ~1,500 values, nearly all of them span edges and
  per-group analysis results).
- **A past version is read from a copy git writes into a temporary
  folder** (`git archive`), so the clone is never touched. The schemas and
  span rules are this checkout's, recorded as `planars_commit`.
- **An analysis bundle is used only if it was drawn from the same spans
  and planar file** as the version being read (the domains file rebuilt
  here must have the hash the bundle records), not merely the same
  commit: annotation that changes no span keeps its analysis. Otherwise
  its values are left out and `missing` says which commit it came from.
  Daily bundles carry no permutation tests, which `missing` also says.
- **Started before its prerequisites, without them:** no construction
  descriptions yet (#318 (e)); examples are the annotation's plain
  `Example` column (English needs no more, decision 4); the analysis is
  read from the working bundles in `.analysis/<lang>/chart_data/` until
  4d decides where the weekly ones live (only `bundle_root` changes).
- `completeness_summary` moved into `planars.reports`; the laminar
  bundles' source record and the chapters both read it.
- **Found, for Phase 4:** reading an old version with today's code is not
  the same as reading it as it was. At the 2026-09-23 commit, English's
  coreference gives no spans, because its constructions were renamed
  since (#318 (d)) and today's schema knows only the new names. So
  `data.lock` must record `planars_commit` as well, and `chapters update`
  should say whether a change came from the annotation or from the rules
  (move one pin at a time).

## Phase 2 as built (2026-10-25)

- **`python -m chapters build --lang LANG --out DIR [--version COMMIT]
  [--apply]`** and **`--intro --out DIR`** (`chapters/build.py`; what each
  writes is its docstring). Dry run by default; writes only what changed
  and deletes a fragment it no longer makes.
- **Wording lives in `chapters/templates/`** (Jinja2 with LaTeX-safe
  delimiters, `chapters/tex.py`). Everything a template prints is escaped
  unless it is already LaTeX, so a template can't forget to.
- **Generated sentences cite values, not numbers:** "Its *strict complete
  span* runs from position `\pv{…left}` (`\pv{…left_name}`) to …". A
  data change that moves a span changes `values.tex` only; a change in
  shape (a span becoming one position, a new construction) changes the
  fragment too.
- **One span table per class**, inside the class's fragment, and **a
  language-wide one** (`spans_table.tex`, Jeff, 2026-10-25): every span of
  the language, grouped by domain type in the schema's class order.
- **`coded_data/` must be its own clone** of planars-data, or the data
  version can't be named (git would answer for the planars repository
  around it); `chapter_data` refuses otherwise. CI now checks planars-data
  out as a clone into `coded_data/` (it used to copy it without `.git`,
  which failed the pinned-version test three times on 2026-10-25).
- **Refusals:** a language chapter's DIR may not be inside this public
  repository (it holds unpublished annotation; `coded_data/.papers/` is set
  up in Phase 3), and coded_data/ with uncommitted changes for the language is
  refused unless `--version` is given, so every chapter names a commit it
  can be rebuilt from.
- **Checked:** English and the introduction compile with pdflatex in the
  book class with no errors and no undefined values (also a test, skipped
  without pdflatex). Math symbols in schema prose (∈, →, ×) are escaped;
  a test fails if the schemas start using one that isn't. Long typewriter
  names may break after `_ : -`. A few sentences still run slightly into
  the margin where a position name sits in a sentence; leave until the
  venue's class is known.
- **Not in Phase 2:** examples (Phase 6 decides glossed or not per
  language) and construction descriptions (#318 (e)).
