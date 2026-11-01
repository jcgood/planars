# Unit 18: every result says what it was drawn from

**Status: built 2026-11-01 (§ 9, as built); Jeff answered § 7 the same day
(each took its recommendation; don't re-ask).** Phase 10
unit 18 (issue #271; implementation plan, Phase 10 table: "Every exported
result carries the package version and each language's change-log position";
done when "results reproducible from their record"). Where it stands:
`docs/data-layer-progress.md`, Phase 10 row.

## 1. The problem

A chart, a chapter or a report is drawn from three things: the code, the
schemas and a language's files. Today the results that record anything
record **git commits** (a bundle's `planars_data_commit`, a chapter's
`data.lock`). The rest record a date at most. Two consequences:

- the record depends on git, which the project decided it must not
  (2026-10-12: "versioning must not depend on git"; Phase 10 ground rule
  "the record outlives its tools");
- unit 17 now counts versions from the change logs (`schemas 0.0.0`,
  `stan1293 0.0.0`), and nothing reports them, so the versions describe
  the framework but no result says which one it used.

## 2. What counts as a result

Every kind of thing the tooling produces from the annotation, and whether
it is in this unit:

| Result | Where it goes | Records today | In this unit |
|---|---|---|---|
| laminar bundles and domains files (`laminar/planars_language.py`, `export_planarsviz_data.py`) | `coded_data/.analysis/{lang}/` (working files; the chapters read them) | planars-data commit, hashes of the spans and planar file | yes |
| contributor charts (`laminar-charts`) | each language's Drive folder | date and completeness above every page | yes |
| chapters (`build-chapters`) | `coded_data/.papers/`, Overleaf | `data.lock`: planars-data commit, planars commit, date | yes |
| language reports (`generate-reports`) | each language's Drive folder | nothing | yes |
| Colab notebooks | computed when opened, never saved | — | no: nothing is kept, so there is nothing to stamp |
| span snapshots (`tests/snapshots/`) | the repository | — | no: a test record; the commit's snapshot diff is its record |
| status sheets | Drive | — | no: progress, not a result |
| CCDB charts (`NonCollaborative/`, `--ccdb`) | `results/` | input file hashes | no: CCDB's data has no change log here; its own release is its version |

## 3. The stamp

One function, `versions.stamp(lang_ids)`, the only place a stamp is built.
It returns:

- **code**: the package version (`pyproject.toml`, e.g. `0.1.0a60`), plus
  whether the checkout has uncommitted changes to the code that produces
  results (as `planars_data_uncommitted_changes` does today for data);
- **schemas**: the version and the log position (§ 3.1);
- **each language**: the version and the log position.

Each kind of result writes it where a reader looks:

- bundles: in `metadata.json` and the domains `source_*.json`;
- contributor charts and reports: one line at the foot of every page
  (*"Drawn 2026-11-02 · code 0.1.0a61 · schemas 0.0.0 (line 6) · English
  [stan1293] 0.0.0 (line 59)"*);
- chapters: in `data.lock` and as values (`<L>.data.version`,
  `<L>.data.position`, `data.code`, `data.schemas`) a chapter can print.

### 3.1 The log position

A language's version counts only edits to its sources; it does not move
when annotation is imported. A result also depends on the annotation, so
the version alone cannot reproduce it. The **log position** does: the
number of lines in the log when the result was drawn. The logs are only
ever appended to, so line *n* names one state of every file the log covers.

## 4. Rebuilding from the stamp

"Reproducible from their record" means a function, not a promise:

`source_log.files_at(stream, position)` writes a copy of the stream's files
as they stood after line *n*. For each file it takes the current copy, then
walks the later lines back: each line touching the file names its *previous
version* in the archive (unit 15), which is the file before that line. A
file no later line touches is as it is now.

This works for a language today: every write since 2026-10-22 goes through
the local-file door, which archives before it writes, and unit 17 catches
hand edits. It does **not** work for the schemas: `log-change` does not
archive their previous versions (change-log design § 4.1: they "are in git
and in each Zenodo release"). § 7 Q2.

**The check, in the suite:** for a test language, `files_at` at every
position of its log gives exactly the files the archive says stood then,
and at the last position gives today's files. Chapters then rebuild from
`files_at` instead of `git archive` (`chapters/data.py` `data_at`).

## 5. The code

The package version goes up only when a commit changes `planars/*.py`
(`regenerate_snapshots_hook.py`). The analysis (`laminar/`), the chapter
builder (`chapters/`), the reports and the R chart package
(`planarsviz/`) also shape results, and changing them does not move it. So
two results stamped `0.1.0a60` can come from different code. § 7 Q3.

## 6. What it replaces

- the bundles' `planars_data_commit` and `planars_data_uncommitted_changes`,
  and the chapters' check that a bundle matches its data (it compares the
  stamps instead of rebuilding a domains file and hashing it);
- `data.lock`'s two commits, and `data_at`'s `git archive`;
- `laminar-charts`' own fingerprint stays (it decides *when* to redraw, not
  what a chart records).

## 7. Questions for Jeff

**Answered 2026-11-01 (don't re-ask):** Q1 the line number; Q2 archive the
schemas' previous versions; Q3 the version goes up for any code that
produces results; Q4 chapters move off git in this unit.

**Q1. The log position: a line number or a time?** Recommended: the line
number. It is exact and short. A time reads better ("as of 2026-11-02
11:43") but two lines can share a second. The stamp can print both: the
number is what rebuilding uses.

**Q2. Archiving the schemas' previous versions.** Recommended: `log-change`
archives each schema file before its line, as the door does for a
language's sources (`schemas/archive/{file}_{stamp}`), so `files_at`
rebuilds the schemas too and nothing needs git. Alternative: leave them to
git and Zenodo; then a result's schemas can only be rebuilt from a git
checkout or the nearest release.

**Q3. What the code version covers.** Recommended: the hook raises the
package version for a commit that changes any code that produces results
(`planars/`, `laminar/`, `chapters/`, `planarsviz/`, the report code), and
the stamp says so. The cost is more version numbers, which nobody reads by
hand. Alternative: stamp the package version plus a short hash of those
folders' files (exact, but meaningless to a reader).

**Q4. Chapters off git.** Recommended: yes, in this unit, since it is the
one reader that rebuilds today: `data.lock` pins a stamp, and
`build-chapters` rebuilds from `files_at`. The `chapter-behind` check then
compares stamps. Alternative: add the stamp to `data.lock` beside the
commits and move off git later; that leaves two pins that can disagree.

## 8. Order of work

1. `versions.stamp`, the log position, and `files_at` with its test (and,
   per Q2, the schemas' archive).
2. The hook's version rule (Q3).
3. Each result writes the stamp: bundles, contributor charts, reports.
4. Chapters: `data.lock`, values, rebuilding through `files_at`, the
   bundle-match check, `chapter-behind` (Q4).

Docs in the same commits: each module's docstring, `docs/chapter-generation-plan.md`
(the data version), `docs/laminar-analysis-plan.md` (bundle metadata),
`data_dependency_schema/` (the stamp as a record every result carries).

## 9. As built (2026-11-01)

All four steps of § 8 in one pass. Where the build differs from §§ 3–6, and
why:

- **Modules.** `coding/versions.py` builds the stamp (`stamp`,
  `stamp_problems`, `stamp_text`, `same_data`, `rebuild`, `RESULT_CODE`);
  `coding/source_log.py` holds the position, `files_at`, `drifted` and
  `archive_schema`. `data_dependency_schema/facts.yaml` `result_stamp`.
- **Every change-log line now records a fingerprint** (§ 4 named only the
  archive). Without one, a file edited outside the tooling and later
  overwritten by an import would rebuild as the hand-edited version,
  silently. With it, `files_at` checks every file it rebuilds, and
  `drifted` finds such a file at once. A file whose last line predates
  2026-11-01 has no fingerprint and can't be checked until it is next
  written.
- **A position before a file's `baseline` line can't be rebuilt**
  (`RebuildError`): hand edits before 2026-11-01 were not logged. No result
  is stamped before then, so nothing needs one.
- **The bundles keep their hash check** (§ 6 said compare stamps). Every
  import moves the log, so comparing positions would throw a bundle away
  whenever anyone annotated, even with no span changed. The hashes decide;
  the stamp says where a bundle that doesn't match came from.
- **`drawn=False`** leaves the time out of a bundle's source record, which
  is rewritten only when it differs.
- **The version bump is its own hook**, `bump_version_hook.py`, run on
  every commit and reading `versions.RESULT_CODE`, so the list is in one
  place (the snapshot hook still runs only for `planars/`).
  `check_snapshots.py`'s pre-push warning reads the same list.
- **Charts:** the full stamp is on the first page; each page's strip has
  the code version and the language's position, which fit the narrowest
  chart. **Reports:** one line under the date.
- **Chapters** read the language's files where the local-file door keeps
  them (`file_door.CODED_DATA`), so the files and the log they are checked
  against always come from the same place. `--version COMMIT` is
  `--position N` (build-chapters and `python -m chapters values`); values
  `<L>.data.commit*` and `planars_commit` are replaced by `data.position`,
  `data.version`, `data.code`, `data.schemas`, `data.schemas_position`.
  `migrations/pin_chapters_to_positions.py` moved English's pin from its
  commit to the position now, allowed because no `chapter-behind` issue
  had ever been filed (nothing the chapter shows differed).
- **Tests** read a private copy of English's folder (`english_files`,
  `reads_english` in `tests/conftest.py`), never the real clone, where the
  door would commit. The schemas' archive is its own setting
  (`source_log.SCHEMA_ARCHIVE`), which every test points at its temporary
  folder, as it does the log: the first build had a test archive into the
  real `schemas/archive/` and stage the copy.
