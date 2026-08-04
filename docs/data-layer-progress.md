# Data layer: progress and resumption state

**This file is the single authoritative record of where the data layer work
stands.** It exists so the work survives an interrupted session: anyone picking
this up cold — a new Claude session, an agent, or Jeff after a gap — should be
able to read *this file alone* and know what is done, what is in flight, and
what to do next.

Deliberately not duplicated into issue #271; that issue points here. Two copies
of this state would be exactly the defect this project is trying to remove.

- **Rationale:** [`data-layer-design.md`](data-layer-design.md) — read before design work
- **Work queue:** [`data-layer-implementation-plan.md`](data-layer-implementation-plan.md) — phase specs
- **Tracker:** issue #271

## Update rules

- Update this file **at every unit boundary**, in the same commit as the work.
- Never let it describe intent — only what is actually true in the repo now.
- Record decisions that aren't in the plan doc under *Decisions log*, with the
  reasoning. A decision recoverable only from a chat transcript is lost.
- **Don't write commit hashes here.** A commit cannot contain its own hash, so
  every one of them cost a second commit to fill in afterwards — and a hash is
  the one fact git already keeps perfectly. To see the work behind any line
  below, in order:

      git log --oneline --grep '#271'

---

## Current state

**Phase:** 0b/1 — migrating callers, 15 of 18 done (started 2026-08-01)
**Live Drive writes performed:** none. Permitted from Phase 9 only.
**Adam's annotation data touched:** none.
**Last worked:** 2026-08-04

Bugs found and fixed while doing this work, all the same root cause — something
inferred which column held a value from the wrong source: **#272** (dropdowns,
fixed), **#274** (coreference analysis returned different answers on different
runs, fixed). **#273** closed 2026-08-02 — verified false alarm, no data lost.
**#277** (`prune-manifest` warned that a sheet was edited recently only after
you had already agreed to prune it, fixed) is a different shape: not a
wrong-source bug but a right-fact-at-the-wrong-time one.

Still open, none of them blocking: **#275** — decided 2026-08-02, the sheet is
stale and `stan1293`'s `phrasal_accent/general` gets rebuilt with pair rows.
Both its tabs are entirely unannotated, so nothing is at stake, and the rebuild
waits on Adam annotating `phrasal_accent/prescreening` rather than on this work
— `general`'s pair rows are derived from which elements he marks accented, so
rebuilding it before then produces a correctly-shaped empty tab. Daily
validation refiles this as a `sheet-validation` issue until the rebuild happens
(**#278** on 2026-08-03) — expected, and not a sign anything new is wrong; a
*different* problem would supersede that issue rather than pile up under it.
**#276** — collapse the duplicated Drive helpers, blocked until every
Drive-writing command has snapshots.

Also fixed, no issue filed: `apply-pending` gave one answer to four different
questions when it could not check a Sheet. Found by file 4's snapshot, fixed
the same day — see the decisions log.

### Status by unit

| Unit | Status |
|---|---|
| Design record + plan written | done |
| Phase 2 — hidden-fact inventory | **done** → `docs/hidden-facts-inventory.md` |
| Phase 0a — protocol surface enumeration | **done** → `docs/drive-protocol-surface.md` |
| Phase 0a — protocol proposal reviewed | **done** — accepted, see decisions log |
| Phase 0a — `capture-drive-state` command | **done** |
| Phase 0a — fixture capture run (read-only, live) | **done** — 29 sheets, 80 tabs |
| Phase 0a — doorway module (`coding/drive_doorway.py`) | **done** |
| Phase 0a — fake doorway (`tests/fake_drive.py`) + smoke tests | **done** — 62 tests |
| Phase 0b/1 — file 1: `refresh_dropdowns.py` | **done** — snapshots captured, mutation log reviewed and accepted |
| Phase 0b/1 — file 2: `generate_reports.py` | **done** — snapshots captured, pre/post diff clean |
| Phase 0b/1 — file 3: `setup_root_folder.py` | **done** — snapshots captured, pre/post diff clean |
| Phase 0b/1 — file 4: `apply_pending.py` | **done** — snapshots captured, pre/post diff clean |
| Phase 0b/1 — file 5: `prune_manifest.py` | **done** — snapshots captured, pre/post diff clean |
| Phase 0b/1 — file 6: `check_notes.py` | **done** — snapshots captured, pre/post diff clean; Docs part of the doorway now covered |
| Phase 0b/1 — file 7: `generate_biuniqueness_allomorphy_sheet.py` | **done** — snapshots captured, pre/post diff clean; first to create a spreadsheet and share it with a named person |
| Phase 0b/1 — file 8: `sync_diagnostics_yaml.py` | **done** — snapshots captured, pre/post diff clean; first writer to a reference sheet |
| Phase 0b/1 — file 9: `import_planar.py` | **done** — snapshots captured, pre/post diff clean across 30 scenarios; first to read *and* write the planar sheet |
| Phase 0b/1 — file 10: `generate_notebooks.py` | **done** — snapshots captured, pre/post diff clean across 7 scenarios |
| Phase 0b/1 — file 11: `update_sheets.py` | **done** — snapshots captured, pre/post diff clean across 12 scenarios; first to append to the annotation tabs themselves |
| Phase 0b/1 — file 12: `generate_status_sheet.py` | **done** — snapshots captured, pre/post diff clean across 8 scenarios; first to create a root-level folder (`parent_id=None`) and first to read *other* languages' already-existing annotation spreadsheets |
| Phase 0b/1 — file 13: `validate_coding.py` | **done** — pre/post diff clean across twelve scenarios; smallest Drive footprint of any file migrated so far (three call sites: `get_doorway()`, `load_manifest()`, `doorway.open_spreadsheet()`), no folder/sharing/manifest-upload logic at all |
| Phase 0b/1 — file 14: `integrity_check.py` | **done** — pre/post diff clean across ten scenarios; two independent read-only entry points (`--sheets`, `--check-manifest`), no writes anywhere in the file; first migration to deliberately drop a retry wrapper (`_with_retry(lambda: gc.open_by_key(...))` → `doorway.open_spreadsheet(...)`, per the doorway's own named exception) |
| Phase 0b/1 — file 15: `import_sheets.py` | **done** — pre/post diff clean across twenty-two scenarios; the command the daily `data-refresh` workflow depends on to pull annotator work down, and the largest file migrated so far (1,138 lines); found Finding 13 (a dry run has no guard at all against a bad manifest spreadsheet ID — it crashes the whole run rather than aborting cleanly the way `--apply` does) |
| Phase 0b/1 — remaining files | not started — see § "Migration order" |
| Phases 3–9 | not started |

### In flight

*(nothing — both launched agents completed 2026-08-01; scope verified, only
their own doc files touched, `coded_data/` untouched, tree clean)*

---

## Next action

**Not blocked.**

1. **The remaining files**, one at a time, snapshots captured
   immediately after each. See § "Migration order" below.
   Delegable to agents now that the pattern exists (the fourteen done are the
   worked examples: Sheets-heavy, Drive-files-only, folders-and-sharing,
   read-only, Docs, sheet creation, reference-sheet overwrite, a command
   with two directions that must round-trip, file uploads, appending to
   annotation tabs, a root-level folder that reads other languages'
   sheets, and a read-only structural comparison against a live Sheet header
   with two independent entry points in one file).

   Watch for, in each: a `_save_drive_config` call (must be patched in tests —
   the real `drive_config.json` holds live IDs and a test that clobbers it
   breaks the coordinator's access to their own Drive) and any expensive or
   non-deterministic pure-computation step (PDF rendering, notebook JSON) that
   should be stubbed so the snapshot locks the *Drive interaction*, which is what
   the migration touches, rather than output already covered elsewhere.

   **If the file reads `construction_params` from the manifest, call
   `tests/mutation_checks.assert_no_criterion_writes_onto_trailing_columns` in
   its snapshot test.** All three of the remaining files do: `sync_params`,
   `generate_sheets`, `restructure_sheets`.
   (`generate_status_sheet` and `validate_coding` were each checked against
   this same list before being migrated and turned out not to belong on it —
   see the 2026-08-03 decisions-log entries. `validate_coding` writes only pink
   highlighting, built from its own local param map, never a dropdown or a
   criterion note. `integrity_check` and `import_sheets` both read
   `construction_params` too, and genuinely stay on the "reads it" list —
   `integrity_check`'s `_section_sheets` compares it against the live header,
   `import_sheets` feeds it into `_validate_tab`/`_validate_pair_tab` as the
   allowed-value set for each criterion — but neither needed the assertion,
   for the same reason: neither ever writes a dropdown or a note back to
   Drive. `import_sheets`'s only sheet write is `highlight_cells`, which
   paints backgrounds, not `setDataValidation` or a note. A dropdown or note
   landing on `Source`/`Comments` is a write-side mistake; these two files'
   only way to get the same fact wrong would be to print an incorrect
   warning, which is what `integrity_check`'s own newest Finding turned out
   to be.) Two commands have now written criterion-shaped things onto
   `Source`/`Comments` independently (#272 and Finding 10), both from
   trusting the manifest about a tab's columns, so treat it as the expected
   mistake rather than a surprise. `sync_params` is the one to watch: it
   inserts and deletes criterion columns, which is the densest form of the
   same question.

2. Phases 3–9 per the plan.

### Held until Phase 9

Live Drive writes are not permitted before then, so these are queued rather than
forgotten. Each is small; the list exists because none of them is anybody's
current job and every one would otherwise be remembered by nobody.

- **Bin `biuniqueness_stage1_synth0001`.** The 2026-08-02 rename means the next
  `generate-biuniqueness-allomorphy-sheet --apply` creates
  `biuniqueness_allomorphy_synth0001` and leaves the old sheet orphaned in the
  `synth0001` Drive folder. Synthetic test data, nothing to preserve. Coordinator
  decision, 2026-08-02: delete it once the new one exists.
- **Rebuild `stan1293`'s `phrasal_accent/general` with pair rows** (#275,
  decided). Also waits on Adam annotating that class's `prescreening` tab —
  which is the binding constraint, not Phase 9, since the pair rows are derived
  from what he marks accented.
- **Give `synth0001`'s three `coreference` pair tabs one criterion column
  each.** `reflexivization`, `pronominalization` and `np_reference` each carry
  all three of `reflexive_allowed`, `pronoun_allowed` and `np_allowed`, where
  `diagnostic_classes.yaml` gives each construction a single `criterion:` and
  `stan1293`'s equivalent tabs have exactly that one column. So the sheets are
  stale against the schema, not disagreeing with it. Listed because it has
  produced an advisory warning on every daily validation run with no issue of
  its own, most recently #278.

  Synthetic data, but **not empty**: each tab holds 67 machine-generated values
  in its own criterion column, and the two surplus columns are blank. So decide
  the mechanism at the time rather than reaching for
  `generate-sheets --regen-construction coreference:reflexivization`, which
  rebuilds the whole tab — `sync-params --apply --remove` drops surplus
  criterion columns while leaving the rest of the tab alone, which is the
  smaller change and the one that matches what is actually wrong. Note that
  `--regen-construction` writes live regardless of `--apply`.
- **Re-run `capture-drive-state`** if the live sheets have changed structurally
  since 2026-08-01. The fixtures are a recording with no staleness alarm; see
  `data_dependency_schema/facts.yaml` § `drive_state_test_fixtures`.

### Migration order

Three files remain of eighteen that touch Drive. The plan's list of eleven
was hand-written and never checked against the code; a scan on 2026-08-02
replaced it with a derived one in `tests/test_doorway_coverage.py`.

That scan was reported as "seventeen", and this file repeated it for two days
before the arithmetic gave it away: seven migrated plus eleven remaining is
eighteen, not seventeen. A hand-copied count of a derived number, going stale
exactly as the derived list would have — the same defect one level up. The
counts above are now checked against the code by
`test_stated_counts_match_the_code`, and the per-file rows no longer carry a
total at all.

Ordered by risk, lowest first, so that every shared helper and every part of
the doorway has been exercised before the destructive commands are touched.

**"15 of 18" still flatters it, and planning should use the volume rather than
the count.** Because the order is smallest-and-safest first, the fifteen done
are 6,984 lines between them; the three remaining are 4,884 lines and **26
direct Drive calls**. That is still 41% of the phase by weight, even at 15 of
18 files by count. Recompute rather than trusting these numbers — the command
is in `tests/test_doorway_coverage.py` (`_DIRECT_ACCESS` over `coding/*.py`,
minus `_EXEMPT`).

| file | why here |
|---|---|
| ~~`setup_root_folder.py`~~ | done |
| ~~`apply_pending.py`~~ | done |
| ~~`prune_manifest.py`~~ | done |
| ~~`check_notes.py`~~ | done |
| ~~`generate_biuniqueness_allomorphy_sheet.py`~~ | done |
| ~~`sync_diagnostics_yaml.py`~~ | done |
| ~~`import_planar.py`~~ | done |
| ~~`generate_notebooks.py`~~ | done |
| ~~`update_sheets.py`~~ | done |
| ~~`generate_status_sheet.py`~~ | done |
| ~~`validate_coding.py`~~ | done |
| ~~`integrity_check.py`~~ | done |
| ~~`import_sheets.py`~~ | done |
| `sync_params.py` | Column surgery — insert, rename, delete. Highest density of read-then-write on one handle |
| `generate_sheets.py` | 2,651 lines, creates everything, and owns helpers four other files call. Late, so those callers are already migrated and proven |
| `restructure_sheets.py` | Archive-then-rebuild with no rollback. The #248 command. Last, deliberately |

Two departures from "smallest first" worth keeping: `import_planar.py` moves
up because it is the command whose silent revert caused #248 and it deserves
attention rather than fatigue; `generate_sheets.py` moves down because four
other files call its helpers, and migrating it last means those callers are
already locked down when it changes.

### The per-file procedure, as actually executed on file 1

Step 1 of the plan's procedure ("run the dry-run against real Drive and save
the output") is not permitted before Phase 9. The substitute, which worked
better than expected and should be reused for every file after the first:

- Drive the **unmigrated** code from a fake seeded by `from_fixtures()`, using
  thin shims for the `gc` and `drive` objects it expects (a `open_by_key` that
  returns a fake spreadsheet; a `files().update()` that records the call).
  Capture stdout and the fake's mutation log.
- **Make every unshimmed route to Google raise**, before running anything. See
  the 2026-08-02 decisions-log entry: patching `coding.drive._get_clients` is
  not enough for a command that did `from .drive import _get_clients`, because
  that binding lives in the command's own module, and the harness reached live
  Drive on its first run. A shim that is merely absent must fail loudly, not
  fall through to the real client.
- Migrate. Run the same commands through the doorway against an identically
  seeded fake.
- Diff. On `refresh_dropdowns.py` both modes' stdout were byte-identical and
  the 36 mutations matched exactly, including the manifest payload's byte
  count.
- Only then capture snapshots.

This gives write paths a real before/after diff rather than review alone, which
is a stronger check than the plan assumed was available. It has held for every
file since: `generate_reports`, `setup_root_folder`, `apply_pending` and
`sync_diagnostics_yaml` all came back byte-identical on the first try. The shims live in the scratchpad,
not the repo — they are per-file throwaways, and committing them would create a
second, decaying description of each command's client usage.

**Weight the automated evidence, not the human review.** The plan made human
review of the `--apply` mutation log the primary barrier for write paths. File
1 showed that is the wrong place to put the load: reviewing file 1's log meant
resolving opaque `sheetId`s and 0-based column indices against the fixtures
before it said anything at all, and the coordinator's honest response on
accepting it was that it was hard to judge. That is a fair reading of the
artifact, not a gap in diligence — and a review step that cannot be performed
confidently is not a safety mechanism, it is a formality that looks like one.

So for every file after the first, the order of evidence is:

1. the pre/post mutation-log diff (mechanical, exact, and the thing that
   actually proves the migration changed nothing);
2. property assertions that survive regeneration — for file 1: the dry run
   mutates nothing, `--apply` writes no cell value, every captured tab reads
   back byte-identical afterwards, a second `--apply` is a no-op. These are
   worth more than the snapshot text, because they state the command's promise
   rather than its current output;
3. human review last, on a *rendered* digest (tab titles and column headers
   resolved, not raw IDs), and framed as "does this match what the command is
   supposed to do", not "verify these 36 entries".

Both bugs behind #272 were found by (3) done on a rendered digest — raw JSON
had hidden the second one entirely. Render before asking anyone to read.

---

## Findings

Per the plan's Phase 0b/1 non-goals, a snapshot that reveals odd behaviour records
it rather than fixing it *in the same change*. **All twelve findings so far have
since been fixed** — the deferral only ever lasts until the migration each one
is riding on has been committed and its before/after comparison taken. Nothing
here is outstanding; the entries are kept because the sequence is the point.

**Do not delete this section when the migration ends without first checking that
every finding has an issue number or a decisions-log entry.** Findings 4 and 5
lived here alone for a day each, and a section that gets deleted is not tracking.

**1 and 2 — issue #272, fixed and closed 2026-08-02** (`b399e32`,
"refresh-dropdowns: read the sheet, not the manifest, for criterion columns").
The old warning here said not to run `refresh-dropdowns --apply` until it was
fixed; that stopped being true the moment it was, and the warning outlived it by
a day. Both are described below as they stood when found.

**1. `refresh-dropdowns` narrowed dropdowns for every class that uses
`construction_criteria`.** `refresh_dropdowns.py:110-113`
builds `class_criteria_map` by taking the **first construction's** criterion
values for each class, under the comment "criteria are shared across
constructions". That is false for classes declaring per-construction criteria.
`_read_diagnostics_for_language` returns the right values per construction; this
loop discards all but the first.

Live consequence, visible in `tests/snapshots/coordinator/refresh_dropdowns/apply.txt`: an
`--apply` run today would push
- `stan1293`/`synth0001` `segmental.flapping`: `[y, n, both, na]` → `[y, n]`
- `stan1293`/`synth0001` `phrasal_accent.general` `joint_accent`:
  `[always, sometimes, never]` → `[y, n]`

and write those wrong sets back into the manifest. Annotation data is not at
risk — validation is non-strict (`showCustomUi=True, strict=False`) and
`validate-coding` reads allowed values from the schemas, not the manifest — so
the damage is that Adam would be offered the wrong options in the dropdown.
Not fixed here: the snapshot's job on file 1 was to capture behaviour, and fixing
it in the same change would have meant the before/after diff could no longer
prove the migration was behaviour-preserving. Fix it as its own change, with
the snapshot diff as the evidence.

(The `coreference.prescreening` line in the same snapshot, three criteria → just
`referential`, is *correct* — `_fresh_param_values` special-cases it.)

**2. Dropdown columns are counted from the manifest, so they can land on
`Source`/`Comments`.** `_detect_col_start` falls back to a hardcoded column 3
when no manifest `param_names` entry matches the live header, and the number of
dropdowns written is `len(param_names)` — from the manifest — not the number of
criterion columns the tab actually has. On `synth0001`/`coreference`/`prescreening`
(header `[..., referential, Source, Comments]`, manifest still listing the three
pair criteria) that writes y/n dropdowns onto `Source` and `Comments`. Fires only
on `synth0001` today because `stan1293`'s entry happens to be correct.

Both are the same underlying mistake: **the manifest is treated as authoritative
for a tab's criterion columns when the sheet header is.** That is this project's
recurring defect shape, so #272 suggests deriving the column set rather than
patching the two symptoms.

**3. `apply-pending` could not tell a wrong spreadsheet ID from a bad
connection** (found 2026-08-02, file 4). **Fixed the same day** — see the
decisions log entry below. Kept here because the sequence is the point: the
snapshot showed it, and the snapshot now proves the fix
(`tests/snapshots/coordinator/apply_pending/cannot_check.txt`).

**4. `prune-manifest` printed its "edited N days ago" warning after the prompt
it should precede** (found 2026-08-02, file 5). **Issue #277, fixed
2026-08-02.** The warning exists
so a coordinator does not archive a sheet somebody was still annotating — but
`_archive_drive_sheet` only read the sheet's modified time in `--apply` mode,
by which point the per-class "Prune 'X'? [y/N]" had already been answered. So
the one piece of information that should change the answer arrived after it.

Nothing was lost when it bit: the sheet is moved to `_archived/`, not deleted,
and the local TSVs are archived too. The modified time is now read during the
dry run, where every other "would do this" line already lives, and cached so
the apply pass does not ask twice.

This one is the clearest illustration of what the deferral rule actually means.
Moving the read changes what the command asks Drive for and when, which is
exactly what a migration's before/after comparison is there to hold still — so
it waited. It waited *for file 5's migration to be committed*, not for the
whole migration to end. Once that comparison had been taken the reason expired,
and holding the fix any longer would have been habit rather than method.

**5. `sync-diagnostics-yaml --to-sheet` wrote the right thing but did not
always say what it changed** (found 2026-08-02, file 8). **Fixed the same day**
— see the decisions log. The "removed / added / changed" list it prints before
uploading was keyed on the `Class` column alone, and several classes have one
row per construction, because their constructions declare different criteria:
`stan1293` and `synth0001` each have two `segmental` rows
(`aspiration_prominence`, `flapping`) and two `phrasal_accent` rows
(`prescreening`, `general`). When the only difference sat in the *second* row
of such a class, the class name appeared on both sides and the changed-row
comparison looked at `.iloc[0]`, the first row, which was identical. So the
coordinator was told "Would update → diagnostics Sheet" with nothing named at
all. Deleting one row of a two-row class printed nothing either, for the same
reason.

Nothing was ever written wrongly: the whole-table comparison that decides
*whether* to upload sees every row, and the upload replaces the sheet with the
YAML's content either way. What was lost was the one look at the change before
approving it — which is the entire purpose of the dry run.

**6. `import-planar` could not see a column added to or removed from the planar
Sheet** (found 2026-08-02, file 9). **Fixed the same day**, in its own commit
after the migration, with the snapshot diff as the evidence. The download
direction read the Sheet and then reshaped it to the columns the *local TSV*
already had (`_read_sheet_df`'s `reindex`). Two consequences, checked rather
than reasoned:

- A column added in the Sheet was dropped on the way down. `import-planar` said
  "up to date" and would have gone on saying it forever. This is how
  `Biuniqueness_Scope` would arrive if anyone added it in the Sheet rather than
  locally, which is the ordinary way a planar gets edited.
- A column removed from the Sheet was not reported as a structural change at
  all. It came back filled with blanks, so an `--apply` wrote a TSV with every
  value in that column erased, described only as "(content-only changes)".

The Sheet is the source of truth in this direction, so the local file's column
list should not have been deciding what the Sheet was allowed to say. Same
shape as findings 1 and 2 and as #248 itself: **the copy was being trusted
about the original.**

The two halves are fixed asymmetrically, and the asymmetry is the point. A
column the Sheet has and the TSV lacks is carried down — growth is safe. A
column the TSV has and the Sheet lacks skips that language entirely, with both
ways out named, because **an absent column is far more likely to be a mistake
in the Sheet than an instruction to erase data.** That is the same reasoning
the empty-sheet skip already used, applied one level down. Refusing also avoids
the question a "just apply it" fix would have raised — how to line up the
values of a kept column against rows that may have been added, deleted or
renumbered — where a wrong answer smears data onto the wrong positions
silently. Registered in `data_dependency_schema/facts.yaml` under
`planar_sheet_structure`, which already owned this fact at row level.

**7. The download direction said nothing at all about a language whose planar
sheet is not recorded** (found 2026-08-02, file 9). **Fixed the same day.**
`import_planar` `continue`d past a language with no `planar_spreadsheet_id`
without printing its name, so it was indistinguishable from a language that was
never configured. The push direction, in the same file, already said "No
planar_spreadsheet_id in drive_config.json — skipping". It was visible in
`tests/snapshots/coordinator/import_planar/skips.txt`, where three languages
went in and only two were mentioned; the whole footprint of the fix is one
added line in that snapshot.

**8. `generate-notebooks`' dry run promised notebooks it would not deliver**
(found 2026-08-03, file 10). **Fixed the same day.** A language gets no
notebooks at all if `drive_config.json` has no Drive folder recorded for it —
there is nowhere to put them. The dry run did not know that: it listed three
notebooks for every language it found a planar for, and the omission first
appeared as three separate skip lines part-way through an `--apply` run, once
the coordinator had already been told what to expect.

The two now name the same set of languages, up front and once per language
rather than once per notebook kind, and say which command creates the missing
folder (`python -m coding generate-sheets --apply`). Same shape as finding 7 —
a command silently passing over something it had just been asked about.

Worth noting for the files still to come: this fix has no diff in the ordinary
snapshots, because all three fixture languages have folders, so the case never
arose. It is covered by a snapshot of its own
(`dry_run_no_folder.txt`). A snapshot suite that can only exercise the happy
path will report a fix like this as no change at all.

**9. Adding one row to a tab narrows that whole tab's dropdowns to `y`/`n`**
(found 2026-08-03, file 11). **Fixed the same day**, with 10 and 11, in one
commit after the migration. `update_sheets._apply_missing_rows` appends the
row and then re-applies validation to *every* data row, existing ones included,
using `per_col_values = [["y", "n"]] * len(param_names)` — a hardcoded pair,
with a comment saying per-criterion values "are not tracked in update_sheets".
They are: the manifest records them, `refresh-dropdowns` reads them, and the
sheet's own header names the columns.

What an annotator would lose on `stan1293`, from one appended row: `segmental`'s
four criteria drop `both` and `na`; `metrical`'s `accented` drops `both` and
`independence` drops `na`; `free_occurrence` loses `na` and `<position_number>`
on four criteria. Nothing already annotated is erased — validation is non-strict
— but the options offered are wrong on rows nobody touched.

Same shape as findings 1 and 2 and as #272: **a value set was invented where one
already existed.**

A third symptom of the same cause turned up while fixing it, and is folded into
the same change: the *width* of an added row was `len(manifest param_names)`
too, so on a tab whose manifest entry had gone stale a keystone row carried `NA`
past the last criterion into `Source` and `Comments`.

The fix imports `refresh_dropdowns._resolve_criterion_columns` and
`_fresh_param_values` rather than restating them. Those two were rewritten for
#272 to answer exactly this question — the sheet's header says which columns
hold criteria, the diagnostics YAML says what each one allows — and two commands
answering it separately is how they came to disagree. Where the header cannot be
reconciled with the YAML, the tab is now skipped with a reason rather than
written to: a row of the wrong width puts values under the wrong headings, which
is worse than not adding it.

**10. Header notes are positioned from the manifest, so they can land on
`Source` and `Comments`** (found 2026-08-03, file 11). **Fixed the same day.**
`_write_header_notes`
writes one hover note per criterion starting at a hardcoded column 3, and takes
the criterion list from the manifest rather than from the tab's header. On
`synth0001`/`coreference`/`prescreening` — one criterion column, `referential`,
against a manifest still listing the three pair criteria — the second and third
notes land on `Source` and `Comments`, describing criteria that tab does not
have. Exactly #272's second bug, in a different command; that one wrote
dropdowns, this one writes notes.

**11. The dry run cannot say the manifest would change** (found 2026-08-03,
file 11). **Fixed the same day.** The line is written — "Would update manifest
on Drive (new tabs detected)." — but `manifest_modified` is only ever set inside
the `if apply:` branch, so the `else` that prints it is unreachable. The dry run
does name each tab it would add, so nothing is hidden; what is missing is that
adding a tab also rewrites the manifest. Unlike 9 and 10 this only changes what
the command says, so by the rule below it did not need deferring at all — it is
grouped here because it was found in the same reading.

Worth carrying forward, and the second time this has come up (see finding 8):
**finding 9's fix has no diff in the ordinary snapshots at all.** The scenario
those record edits `arao1248`, whose criteria are all `y`/`n` already, so the
narrowed and the correct dropdown are the same three characters. What proves
that fix is a property assertion on `stan1293`'s `segmental` tab, not snapshot
text — which is the evidence order the migration settled on, arrived at again
from the other direction.

**12. `integrity-check --sheets` has been crashing before reaching any Drive
call at all, for essentially every real run, since 2026-08-02** (found
2026-08-03, file 14, while taking the pre-migration baseline — the unmigrated
code raised the identical `TypeError` the first time it was driven against
the fake, before either of the two Drive call sites this migration touches
was ever reached). **Fixed the same day**, as its own commit right after the
migration landed. This one sits slightly outside the deferral rule below
(fix now if it only changes what the command *says*; defer if it changes what
it *writes* or asks Drive for) — the function touches no Drive call at all,
so nothing it does falls on either side of that line — but it blocked the
baseline outright, so a harness workaround was not enough to trust the
migration on; it needed the real fix, and the fix could not itself move the
Drive-touching diff since it never touches Drive.
`_stale_manifest_param_values` (`coding/integrity_check.py` ~line 274) called
`refresh_dropdowns._fresh_param_values` with six positional arguments:

```python
fresh = _fresh_param_values(
    lang_id, class_name, construction,
    param_names, class_criteria, coref_pair_map,
)
```

`_fresh_param_values` has taken four positional arguments — `class_name,
construction, construction_criteria, coref_pair_map` — since `b399e32`
(2026-08-02, #272's fix), which dropped `lang_id` and `param_names` as part of
moving the function to derive columns from the sheet header rather than the
manifest. That commit updated every call site inside `refresh_dropdowns.py`
itself but not this one in `integrity_check.py`, so the call has raised
`TypeError: _fresh_param_values() takes 4 positional arguments but 6 were
given` for any construction carrying `param_names` — which, on the real
manifest, is effectively all of them — ever since. No test exercised
`_section_sheets` before this migration (`--sheets` requires either live
Drive or, as of now, the fake), so nothing caught it.

There is a second defect riding along with the crash, not just the wrong call
shape: `class_criteria_map` (built a few lines above the call) keeps only the
**first** construction's criteria per class —

```python
class_criteria_map: dict = {}
for cls, _con, _crit_names, crit_values in diag_rows:
    if cls not in class_criteria_map:
        class_criteria_map[cls] = crit_values
```

— which was exactly Bug 1 from #272, independently reintroduced here rather
than shared from the fix. `refresh_dropdowns.py` keys criteria by `(class,
construction)` for precisely this reason; this function keyed by class alone,
so even a corrected call would have resolved every construction of a
per-construction class (`segmental`, `phrasal_accent`) against the first
one's allowed values.

Not fixed in the migration commit itself — the function touches no Drive
call, so it was orthogonal to the doorway substitution, and the non-goal is
no behaviour changes beyond it. Worked around in the test harness only while
taking the pre/post baseline (both drivers patched
`_stale_manifest_param_values` to a no-op so the Drive-touching lines under
test could be reached and compared at all) — the source file itself was left
exactly as broken as it already was for that comparison. Fixed properly in
the very next commit: `criteria_by_construction` now keys by `(class,
construction)`, mirroring `refresh_dropdowns.py`'s working pattern exactly
rather than restating a second, independently-drifting copy of the same
logic, and the call to `_fresh_param_values` now passes the four arguments it
actually takes. Verified against the real fixture manifest before writing a
regression test: the fixed function now reports four genuine, already-known
mismatches on `synth0001`'s `coreference` pair tabs — the same drift named in
`coding/CLAUDE.md`'s "Held until Phase 9" list (each manifest entry still
lists all three pair criteria; the diagnostics YAML gives each construction
just the one it uses) — rather than crashing or inventing a false one.
`tests/test_integrity_check_snapshot.py::test_stale_param_values_reports_a_real_mismatch_without_crashing`
pins it.

**13. A dry run of `import-sheets` has no protection at all against a
manifest entry pointing at an inaccessible spreadsheet** (found 2026-08-04,
file 15). Not fixed here. `--apply` calls `_verify_manifest_sheet_ids` first
and aborts cleanly — "ERROR: Manifest contains inaccessible spreadsheet
IDs" — before downloading anything, but that call is gated `if apply:`. A
dry run instead reaches `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])`
inside the per-class loop (`coding/import_sheets.py` ~line 879) with no
`try`/`except` around it at all, so a bad ID raises an unhandled
`SpreadsheetNotFound` (or the live equivalent) straight out of `main()` —
stopping the *entire* run, every language, not just the one naming the bad
ID. Confirmed identical between the unmigrated and migrated code as part of
the pre/post comparison (both raise the same exception at the same point);
`tests/test_import_sheets_snapshot.py::test_a_bad_id_reached_on_a_dry_run_crashes_the_whole_run`
pins the crash as current behaviour rather than papering over it.

Nothing is lost when it happens — a dry run performs no writes either way —
and the daily `data-refresh` workflow itself runs `import-sheets --apply
--ignore-status` directly, so it always gets the clean abort. The risk is the
ordinary coordinator workflow this file's own module docstring recommends:
`python -m coding import-sheets` (dry run) before `--apply`, to preview what
would be written. A single stale manifest entry crashes that preview step
outright, with a raw traceback, rather than reporting per-language the way
every other failure mode in this file does. Same shape as #248 and findings 6
and 7: a guard that exists on one path and not its twin.

---

## Decisions log

**2026-08-04 — file 15 (`import_sheets.py`) needed no doorway addition.**
Every primitive it uses already existed: `get_doorway()`, `load_manifest()`,
`upload_manifest()`, `doorway.open_spreadsheet()`, `doorway.get_file()`. Five
functions touched Drive directly, each a plain call-site substitution —
`_read_sheet_as_df(gc, ...)` → `_read_sheet_as_df(doorway, ...)`,
`_read_status_tab` dropped its `gspread.Spreadsheet` type annotation and
`except gspread.WorksheetNotFound` became `except WorksheetNotFound` (the
identical class, imported from `drive_doorway` instead), `_download_lang_setup_sheets`
renamed its `gc` parameter to `doorway` and threaded it into two
`_read_sheet_as_df` calls, `_verify_manifest_sheet_ids` swapped
`drive.files().get(fileId=..., fields=...).execute()` for
`doorway.get_file(spreadsheet_id, fields="id,trashed")`, and `main()` replaced
`gc, drive = _get_clients()` / `_load_manifest_from_drive(drive)` with
`doorway = get_doorway()` / `load_manifest(doorway)`, threaded `doorway`
everywhere `gc`/`drive` had been, and closed with
`upload_manifest(doorway, manifest, root_id, file_id)` in place of
`_upload_planars_config(drive, manifest, root_id, file_id)`. `gspread` is no
longer imported at all — it was needed only for the two dropped type
annotations and the one `except` clause.

By far the largest and most consequential file migrated so far (1,137 lines
post-migration; the daily `data-refresh` workflow's `import-sheets --apply
--ignore-status` step is what pulls annotator work down from Sheets every
day), so the scenario count follows suit: twenty-two, run through both the
unmigrated and migrated code against identically seeded fakes — dry run over
all languages and with `--lang`; `--apply` with no prior local TSVs
(first-time download); an "already matches" baseline and a genuine content
change on top of it; `--overwrite-existing`; a purely-additive in-order
planar change (queues `update-sheets --apply`, confirmed via a stubbed
`sys.modules["coding.update_sheets"]` recording rather than really running
the auto-applied command) versus a deletion and a reorder (each its own
pending entry); an unrecognised diagnostics criterion (ambiguous YAML drift);
a missing construction tab (`WorksheetNotFound`, warn and continue); a class
with no Status tab versus `--ignore-status` versus one construction flipped to
`ready-for-review` alongside others left `in-progress`; an injected invalid
cell (confirmed via a `updateCells` mutation at the exact row/column, not just
by reading stdout — real fixture data already has blank cells pink-highlighted
too, so the highlight *count* alone does not move when a blank becomes
invalid); a missing local row on an in-progress tab (collaborator-check, not
pending); a bad manifest spreadsheet ID reached under `--apply` (clean abort)
versus the same ID excluded by `--lang` under a dry run (silently never
reached) versus reached on a dry run over all languages (crashes — Finding
13); the manifest metadata sync firing only when the computed planar
structure actually differs from what the manifest already has; and `--lang`
leaving other languages' local trees untouched. stdout, exit codes, the
mutation logs, the local `coded_data/` tree contents, `pending_changes.json`,
and `diagnostics_drift.json` all came back byte-identical once
`datetime.now()` was frozen — the archive filename embeds a timestamp
computed once at the top of `main()`, so two real invocations a second apart
otherwise disagreed on nothing else.

Two harness-only findings, neither about the migration itself, both worth
naming for whoever migrates `sync_params.py`, `restructure_sheets.py`, or
`generate_sheets.py` next: first, `load_manifest()`/`_load_manifest_from_drive()`
are defined in `coding/drive.py` and call *that module's own* `_load_drive_config()`
when falling back to the pre-#30 per-language manifest format — patching
`import_sheets.py`'s imported copy of `_load_drive_config` is not enough, the
same "patch where it's actually bound and looked up" lesson as file 5's
finding, one level further down the call chain. Caught before it mattered:
the very first harness run, with only the target module's copy patched,
reached a *real* OAuth token refresh against `oauth2.googleapis.com` — three
established HTTPS connections to Google IP ranges, found via `lsof` after the
process sat idle past a two-minute timeout with zero CPU use. No data was
read or written; `_get_clients` guards on `PLANARS_OAUTH_CREDENTIALS`, which
happened to already be satisfied on the machine doing this migration, so the
usual "no credentials file, raises immediately" guard did not fire. The
harness now also wraps every scenario in a socket-level guard that raises
immediately on any connection not to localhost, rather than trusting each
shim to be complete. Second: `revalidate_sheets()` (called at the end of
`main()` under `--apply`) reads local TSVs from `coding.validate_coding`'s
own `CODED_DATA` constant, a different module-level path than this file's
`ROOT` — both need redirecting into the test's private tree, or the
revalidation pass silently reads the real repo's current annotation state
instead of the scenario under test.

`tests/test_import_sheets.py`'s `TestVerifyManifestSheetIds` mocked a raw
`drive` object shaped like `.files().get(fileId=..., fields=...).execute()`;
its six tests now pass a `_DoorwayStub` with a `get_file(self, file_id,
fields=None)` method instead, keeping the same behaviour under test (which
IDs abort, which don't) without depending on a shape `_verify_manifest_sheet_ids`
no longer receives. The rest of that file is unchanged, per its own docstring
being otherwise pure logic.

Twenty-six tests in a new `tests/test_import_sheets_snapshot.py` (plus the six
updated in `test_import_sheets.py`). They pin: a no-op apply writes no new
TSVs or archives; `--overwrite-existing` forces a rewrite despite unchanged
content; a content change archives the old file before overwriting; a
purely-additive planar change auto-applies `update-sheets --apply` while a
deletion or reorder writes a `pending_changes.json` entry instead; an
unrecognised diagnostics criterion lands in `diagnostics_drift.json`, not a
crash; a missing tab warns and leaves the rest of the language alone; the
Status-tab-absent, `--ignore-status`, and mixed-status paths each produce the
right ready-for-review/in-progress split; an invalid cell gets pink-highlighted
at its exact cell address; a missing local row on an in-progress tab goes to
`_notify_collaborator_check`, never `pending_changes.json`;
`_verify_manifest_sheet_ids` aborts cleanly before any language is printed
under `--apply`, is silently never called when `--lang` excludes the bad ID
under a dry run, and crashes when a dry run does reach it (Finding 13,
confirmed rather than avoided); the manifest metadata sync uploads only when
the computed planar structure changed; `--lang` leaves other languages
untouched; both a pair-row construction (`coreference/reflexivization`, whose
output TSV keeps its `Element_A`/`Position_A`/`Position_B` columns) and a
standard construction import cleanly in the same run; and a defensive call to
`assert_no_criterion_writes_onto_trailing_columns`, expected to always pass
here since this file's only sheet write is `highlight_cells` painting
backgrounds, never a dropdown or a criterion note.

`tests/test_doorway_coverage.py`'s `_REMAINING` drops `import_sheets.py`
(three files now remain, all still reading `construction_params` from the
manifest for different reasons — see the "Next action" update in the same
commit); `coding/CLAUDE.md`'s migrated list gains it and its
"`construction_params`" sentence is rewritten to name `import_sheets` and
`integrity_check` together as readers that never write it back;
`docs/data-layer-progress.md` moves to 15 of 18 and recomputes the
remaining-files weight (4,884 lines, 26 direct Drive calls across
`sync_params`, `restructure_sheets`, `generate_sheets`).

**2026-08-03 — file 14 (`integrity_check.py`) needed no doorway addition.**
Every primitive it uses already existed (`get_doorway`, `load_manifest`,
`doorway.open_spreadsheet`); `_with_retry` stays imported and used for the
three call sites that were never wrapped by `_open_spreadsheet`
(`ss.worksheets()`, `ss.worksheet(construction)`, `ws.row_values(1)`), which
keep exactly the retry behaviour they had before, per the migration's
non-goal. Two independent entry points, both function-scoped imports rather
than module-level: `_section_sheets` (the `--sheets` flag) and `main()`'s
`--check-manifest` fast path, which makes no Sheet API calls at all and exists
for the daily `data-refresh` workflow to check the manifest cheaply.

One substitution departs from a plain call-site swap on purpose:
`ss = _with_retry(lambda: gc.open_by_key(sheet_info["spreadsheet_id"]))`
becomes `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])` with the
outer `_with_retry` **removed**, not preserved. `drive_doorway.py`'s own
docstring names this exact idiom — bare `gc.open_by_key` wrapped by the
caller — as one of three inconsistently-retried open idioms the doorway
deliberately unifies onto `open_spreadsheet`'s always-retried path, safe
because opening is an idempotent read. Confirmed equivalent, not just
documented as such: `coding/drive.py`'s `_open_spreadsheet(gc, spreadsheet_id)`
is itself `_with_retry(lambda: gc.open_by_key(spreadsheet_id))` with the same
default `retries=5`, i.e. the identical wrapping this file was doing by hand —
so the migration changes *which line* does the retrying, not the retry count
or backoff. The three other `_with_retry` call sites in this file
(`ss.worksheets()`, `ss.worksheet(...)`, `ws.row_values(1)`) are not
`open_spreadsheet` and stay wrapped exactly as they were.

Pre/post comparison across ten scenarios — `--sheets` over all languages, one
`--lang`, a language whose manifest `spreadsheet_id` does not exist in the
fake (the `except Exception` around opening), a class whose live tab is
missing, a class whose live header has drifted from the manifest's
`construction_params`, a stale `_split_` column, the plain run with no
`--sheets` at all, and `--check-manifest` with a stale entry, with none, and
with the connection itself failing — came back byte-identical between the
unmigrated and migrated code: stdout, exit codes, and the (empty throughout)
mutation logs. The pre-migration baseline needed the guard-intercepts-or-fails
check run explicitly before trusting any scenario, per the established
per-file procedure, and it passed on the first attempt this time — unlike file
5, where the equivalent check was the thing that first surfaced that a
module-level import needs a different patch target than a function-local one.
This file's two entry points both do the `from .drive import ...` locally
inside their own function bodies, so patching `coding.drive._get_clients`
directly (rather than the importing module's own namespace) was the right
target here, confirmed by making the patch briefly absent and checking it
raised before running any scenario.

A pre-existing bug unrelated to the migration was found while taking the
baseline — recorded as Finding 12, and fixed as its own commit right after
this one landed rather than folded into it, since the fix touches no Drive
call and so could not itself move the migration's before/after diff. It
blocked the baseline outright (the unmigrated code crashed on the very first
scenario), so it was neutralized in the test harness only, identically on
both sides of the comparison, for the migration commit itself; see Finding 12
for the fix.

Thirteen tests in a new `tests/test_integrity_check_snapshot.py` (twelve from
the migration commit, plus one more —
`test_stale_param_values_reports_a_real_mismatch_without_crashing` — added
with the Finding 12 follow-up). They pin: a header mismatch names both the
expected and actual column lists and points at `sync-params --apply`; a
missing tab is an error that does not stop the rest of that language's run; a
stale `_split_`/`_merged_` column gets its own remediation text instead of
the header-mismatch message; an unreachable spreadsheet is reported per
class, not fatal to the language; a plain run with no `--sheets` prints the
section header and the skip line and touches no Drive calls at all;
`--check-manifest` reports stale entries and exits 1, a clean manifest exits
cleanly, and a failed connection warns and returns rather than crashing or
filing a misleading issue; a real, already-known `param_values` mismatch on
`synth0001`'s `coreference` tabs is reported without crashing (Finding 12's
regression test); and every scenario that touches Drive leaves
`doorway.mutations` empty, since this file never writes. `main()`'s header
line stamps `date.today()` into the two full-transcript snapshots, so the
fixture freezes it rather than letting the snapshots drift with the calendar.

`tests/test_doorway_coverage.py`'s `_REMAINING` drops `integrity_check.py`
(four files now remain, all reading `construction_params` from the manifest
except that this file reads it only to compare, never to write — see the
"Next action" update in the same commit); `coding/CLAUDE.md`'s migrated list
gains it and its "construction_params" sentence count drops from five to
four; `docs/data-layer-progress.md` moves to 14 of 18 and recomputes the
remaining-files weight (6,022 lines, 32 direct Drive calls across
`sync_params`, `import_sheets`, `restructure_sheets`, `generate_sheets`).

**2026-08-03 — file 13 (`validate_coding.py`) needed no doorway addition and
no `assert_no_criterion_writes_onto_trailing_columns`.** Every primitive it
needs already existed (`load_manifest`, `get_doorway`,
`doorway.open_spreadsheet`), and its only sheet writes are pink highlighting
via `batch_update` — `highlight_cells`/`clear_highlights` call
`ws.spreadsheet.batch_update(...)` directly, needing no edits at all, since
handle methods mirror gspread by design. It never calls `setDataValidation`
or writes a criterion hover note, so — like `generate_status_sheet` before it
— it was checked against the "reads `construction_params` from the manifest"
list and does not belong there either: its own `_load_param_map` and
`_COREFERENCE_CONSTRUCTION_PARAMS` read the diagnostics YAML and schema
files, never the manifest.

Pre/post comparison across twelve scenarios — all languages, one `--lang`,
`--verbose`, a `--lang` matching nothing in the manifest, a spreadsheet ID the
fake has never seen (the `except Exception` around `open_spreadsheet`), an
invalid local-TSV cell value (`highlight_cells` actually firing a
`batch_update`), each fixture language alone, and `main()` across the
equivalent argv combinations for exit-code behaviour — came back byte-identical
between the unmigrated and migrated code.

Thirteen tests. They pin: pink highlighting is written for an invalid cell and
cleared once the value is fixed; `Status`/`Instructions`/`Planar Structure`
tabs are skipped entirely (never reported, never looked up as a construction);
a spreadsheet that cannot be opened is reported per-class and does not stop
the rest of that language's run; `--lang` restricts output to one language;
blank-cell issues never count toward the blocking total or `sys.exit(1)`, and
are reported on a separate line from real issues; and a pair-row construction
(`coreference/reflexivization`) is validated through `revalidate_pair_sheet`
while a standard construction (`ciscategorial/general`) goes through
`revalidate_sheet` — visibly different in the transcript, since only the pair
path labels a row `Element_A → pos Position_B`.

**2026-08-03 — file 12 turned out not to need
`assert_no_criterion_writes_onto_trailing_columns`, correcting a line written
during file 11's migration.** The § "Next action" list said six of the seven
remaining files read `construction_params` from the manifest, naming
`generate_status_sheet` among them. Reading the file before migrating it
showed that was never true: its `_construction_params` (singular, local) reads
the diagnostics YAML and `_COREFERENCE_CONSTRUCTION_PARAMS`, never the
manifest, and the command's only sheet writes are the three-column status
table and its background-color formatting — no `setDataValidation`, no
criterion note, nothing that could land on `Source`/`Comments`. So the
assertion has nothing to check here; the file was miscounted, not exempted.
Both `docs/data-layer-progress.md` and `coding/CLAUDE.md` said "six" (now
"five" and "five", respectively) as part of this file's migration commit,
per the rule that a stale statement gets fixed the moment it's noticed rather
than deferred to an audit.

**2026-08-03 — file 12 (`generate_status_sheet.py`) needed no doorway
addition; the one gap was filled inline instead.** Every other primitive it
uses already existed (`get_or_create_folder` with `parent_id=None`,
`list_files`, `create_permission`, `list_permissions`, `delete_permission`,
`move_file`, `create_spreadsheet`, `open_spreadsheet`). The one thing that
had no doorway-level counterpart was `drive._remove_anyone_permission` — every
still-unmigrated caller uses that helper directly, so it was left alone rather
than added to the `DriveDoorway` protocol for a single caller; `_lock_read_only`
inlines the same two-call sequence (`list_permissions` then
`delete_permission` on any `type == "anyone"` entry) from primitives that
already exist. Also worth naming: the command shares read-only (`role="reader"`)
with Adam, unlike file 7's writer share — the two migrations use the same
`create_permission` call with different arguments, not different mechanisms.

**2026-08-02 — file 9 was checked by a round trip, not only by each direction
on its own.** `import-planar` is the only migrated command with two directions
that write to different places, and #248 was neither direction being wrong: it
was a local edit going up and not coming back down. So the snapshot tests
assert the pair — push a planar up, import it back, and the file is unchanged;
import down, push up, and the Sheet is unchanged. Each direction also carries
the promise that it does not write to the other side at all, which is the
narrower version of the same thing.

Two other properties are worth naming because they are the ones that would have
made #248 visible: an empty sheet never wipes the local planar (it is skipped),
and a sheet that cannot be read leaves that language's TSV alone without
stopping the other languages.

**2026-08-02 — file 9 dropped a parameter, the same boundary as file 8.**
`push_planar_to_sheet(lang_id, gc, cfg, apply)` took a `gc` client and passed
it to one call. Through the doorway there is nothing to pass, so the parameter
went. Its only caller is `push_planars_to_sheets`, in the same file; the two
callers outside `coding/import_planar.py` (`restructure_sheets.py`,
`tests/make_synthetic_lang.py`) both call `push_planars_to_sheets`, whose
signature is unchanged.

`/tmp/planar_changes.json` also became a named constant,
`import_planar.PLANAR_CHANGES_PATH` — added *before* the pre-migration run, so
both sides of the before/after comparison exercised the same code. The path is
what the daily workflow reads to build the `planar-changed` issue, and a test
suite writing to the real one would hand the workflow a diff nobody made.

**2026-08-02 — the migration-order table no longer numbers its rows.** The
numbers had drifted from the status table's "file N of 18" — one counted
files done, the other files remaining — so two different numbers were both
called the file's number. The order is the rows' order; that is all it ever
meant.

**2026-08-02 — finding 5 was fixed straight after being found, and the rule
that decides which findings get that treatment is now stated once here.** Three
findings have been deferred and two fixed on the spot, and the line between
them has been redrawn in prose each time. It is this: **fix it now if it only
changes what a command *says*; defer it if it changes what a command *writes*
or what it asks Drive for.** The reason is the migration's evidence, not
caution in general — the pre/post mutation diff is what proves a migration
changed nothing, so anything that would move that diff has to wait until the
migration it is riding on is already committed and proven.

**The deferral is only ever until *that file's* migration is committed, not
until the migration ends.** Stating this because getting it wrong is what
happened: #272's two dropdown bugs were correctly fixed once file 1 was done,
but the `prune-manifest` ordering sat on for a further day after file 5 landed
purely because nothing said the wait was over, and the warning here telling
people not to run `refresh-dropdowns --apply` outlived its own fix by a day.
A deferral with no expiry written next to it is indistinguishable from being
forgotten. Every one of the five findings has now been fixed.

`apply-pending`'s four-way failure message and finding 5 were
fixed the day they were found. Both fixes landed as their own commit *after*
the migration commit, with the snapshot diff as the evidence — which is what
made the change legible: finding 5's entire footprint is one new line,
`+ added: phrasal_accent / general`, appearing in two snapshots where nothing
had been printed before.

Worth noting what the fix is not. The obvious repair was to key the report on
(Class, Constructions) instead of Class, and that would have been a regression
for the common case: most classes hold a single row whose `Constructions` cell
is a *list*, so adding one construction to `subspanrepetition` would have
changed the key and reported a removal plus an addition where "changed" is the
truth. A class with one row on each side is therefore still reported by class
name alone, and only a class holding several rows is reported per
construction. `_describe_changes` is now a named function with that reasoning
in its docstring, rather than a loop inline in the middle of an upload.

**2026-08-02 — file 8 dropped a parameter rather than keeping the migration
purely a call-site substitution.** `_sync_to_sheet` took a `gc` client and
passed it to one call, `_open_spreadsheet(gc, diag_id)`. Through the doorway
there is nothing to pass, so the parameter went. It is a private function with
one caller inside the same file, so this is not the cross-file rewrite the
phase forbids — but it is worth naming as the boundary: a *signature* may
change when the thing it threaded through no longer exists, a *call site in
another file* may not.

Also worth noting for the files still to come: the upload direction used to
build both clients eagerly, before it knew whether it had anything to do.
`get_doorway()` builds them on first use, which here is the manifest download a
line later. No output moved, and the fifteen-scenario pre/post diff was
byte-identical — but on a command that can exit before touching Drive at all,
this is the difference between prompting for OAuth and not.

**2026-08-02 — the fake was writing acknowledgment lines in the wrong place,
and it would have hidden a daily duplicate-issue loop.** Found on file 6, by a
test rather than by the pre/post diff — the diff could not see it, because both
sides used the same fake.

`check-notes` decides whether a collaborator has written anything new by
hashing their doc. It also *writes into that doc*, appending "notes transferred
to coordinator", so the hash deliberately ignores acknowledgment lines. The
live helper inserts at `endIndex - 1` — **before** the document's final
newline, which a Google Doc always has. The fake appended after everything,
leaving a blank line behind. A blank line survives acknowledgment-stripping, so
the hash changed anyway, so the next run would see new content, file again, and
append again — one duplicate report per day, growing forever.

The command is correct; the fake was not. Fixed to insert where the live helper
inserts. Recorded because of what it says about the method rather than the bug:
**a pre/post diff cannot catch a fake that is wrong in the same way on both
sides.** It proves a migration changed nothing; it says nothing about whether
the thing being preserved was right. Tests that state the command's promise —
here, "an acknowledgment does not look like new notes tomorrow" — are what
catch this class, which is why the evidence order above puts property
assertions above snapshot text.

Two smaller fake corrections in the same file: `create_doc` was double-logging
the way `get_or_create_folder` was (same fix), and a file created with the Docs
mimetype now registers as a readable empty document, because that is what one
Drive call actually produces — there is no second step that turns a file into a
Doc. Without it, a Doc created through `create_file` existed in Drive but 404'd
on the next read.

`drive.py` gained `create_notes_doc(doorway, ...)`, sharing the doc's naming
rule with `_create_notes_doc` and keeping the "anyone with the link can edit"
grant beside the creation. That grant is the loosest sharing in the project and
deliberately so — collaborators must reach their notes doc without an invite —
so it should not be left to each caller to remember.

**2026-08-02 — the pre-migration harness reached live Drive once, on file 5.
Read-only, nothing changed, and the harness now cannot do it again.**
`prune_manifest.py` does `from .drive import _get_clients`, which binds that
name into *its own* module; the harness patched `coding.drive._get_clients`,
which does not touch that binding. So the command built a real authenticated
Drive client from the cached token and ran one `files().get` for a spreadsheet
ID that exists only in the stand-in Drive. It 404'd. No write reached Google:
the run went on to attempt the manifest upload, and both attempts raised
`TypeError` inside googleapiclient's *request builder* — before any HTTP —
because the media object was the harness's stand-in rather than a real
`MediaUpload`. That crash is what surfaced the whole thing.

Two changes came out of it. The harness replaces the binding in the command's
own namespace, and `coding.drive._get_clients` is replaced by a function that
**raises**, so any route not shimmed fails loudly instead of quietly working.
The first four files happened not to need this because their Drive access all
went through names the harness had covered — which is exactly why the guard has
to be unconditional rather than added when it seems necessary.

Worth stating plainly, because it is an argument for the work rather than
against it: **this failure is not available to a migrated command.** Once a
command calls `get_doorway()` there is one binding, and `set_doorway()` replaces
it. The four files migrated before this one cannot make the mistake, and neither
can `prune_manifest.py` now.

**2026-08-02 — two small additions to the doorway and one correction to the
fake, all made for file 5.** The doorway's `get_file` gained
`supports_all_drives`, carried through rather than dropped: `prune_manifest` is
the only caller that sets it, and dropping a flag on the live path is not a
migration's business. Recorded rather than resolved: `move_file`, which
`prune_manifest` calls on the same file moments later, has never sent it, so a
sheet on a shared drive can be read but not moved.

`drive.py` gained `upload_manifest(doorway, ...)`, sharing one body with
`_upload_planars_config` the way `load_manifest` already shares with
`_load_manifest_from_drive` — key ordering and the update-then-create fallback
now exist once. This does not close #276; three other manifest writers remain.

The fake was recording **two** mutations for one folder creation —
`get_or_create_folder` logged `create_folder` on top of the `create_file` its
own call had already logged. Nothing had exercised it before (`setup_root_folder`
keeps its own find-then-create). Caught by the pre/post diff, which is the
first thing that diff has actually caught. Removed: creating a folder *is*
creating a file with the folder mimetype, and a log whose job is to say what
changed must not turn one call into two. The fake also models `modifiedTime`
now, so `prune_manifest`'s "edited N days ago" warning can be exercised at
all — it is the only guard against pruning a sheet somebody was still working
in.

**2026-08-02 — commit hashes are no longer written into this file.** Every one
of them cost a second commit, because a commit cannot contain its own hash, and
git already keeps the fact perfectly. `git log --oneline --grep '#271'` lists
the work behind every line above, in order, and cannot go stale. The hashes
that were here are in that log.

**2026-08-02 — `apply-pending`'s Sheet check was fixed straight after being
found, unlike the other two findings.** The other two are deferred because
fixing them would change what a command writes, and the before/after diff is
what proves a migration changed nothing. This one only changes what the command
*says* when it cannot check, so the diff was never at risk.

The old code caught every failure alike and printed "could not verify (Drive
unavailable or spreadsheet ID not recorded)", then asked "Mark as resolved?".
Four different situations, one sentence, one question — and answering yes
closed the entry with nothing checked. They are now told apart, because each
one needs something different: an entry with no spreadsheet ID recorded is told
which Sheet to look in by name; an ID pointing at a sheet that no longer exists
is told the entry is aimed at the wrong place and pointed at
`python -m coding integrity-check --sheets`, the same command `import-sheets`
already gives for a stale manifest; a sheet the signed-in account is not shared
on is told to ask for access; and a dropped connection is told that nothing is
wrong and to run the command again later.

The question changes with the situation too. "Have the tabs been added" is
answerable when Drive merely could not be reached, and is not answerable at all
when the sheet the entry names is gone, so those ask "Close this entry anyway?"
instead. All four still let the coordinator clear the entry themselves —
otherwise an entry naming an unreachable spreadsheet would be stuck open
forever.

`SpreadsheetNotFound` and `NoAccess` are now named in `drive_doorway.py`
alongside `WorksheetNotFound` and `APIError`, for the same stated reason: a
caller telling failures apart needs the fake to raise what the real thing
raises. gspread turns a 404 into `SpreadsheetNotFound` and a 403 into Python's
own `PermissionError` when *opening*, but reading the tab names afterwards is a
second call that reports both as plain status codes, so the code checks for
those too.

**2026-08-01 — the manifest is now a captured fixture, and `capture-drive-state`
records it going forward.** The fake needs the manifest: it is what every
command reads to learn which spreadsheet holds which class, so without it no
command can be driven offline at all. The 2026-08-01 capture downloaded the
manifest but did not persist it — a gap in the command, now fixed (it writes
`tests/fixtures/drive_state/manifest.json` alongside the spreadsheets). The
committed fixture is a byte-identical copy of the local `manifest_backup.json`
written by `generate-sheets` at 2026-07-31 22:55, which is a *raw downloaded
manifest before any mutation*, so it is a recording of the same kind, not a
reconstruction. It agrees with the capture exactly: same 29 spreadsheets, same
IDs, no additions or removals on either side. Registered in
`data_dependency_schema/facts.yaml` as `drive_state_test_fixtures`, with the
new `test_fixture` entity — a committed snapshot of live state is a replicated
fact, and its whole failure mode is going quietly stale.

**2026-08-01 — handle method names mirror gspread, deviating from the accepted
proposal's renames.** The reviewed proposal named the two batch endpoints
`apply_sheet_requests` and `write_value_ranges`. `coding/drive_doorway.py`
instead keeps gspread's own `batch_update` / `values_batch_update`, and mirrors
gspread's names for every handle method. Reason: the migration proceeds one file
at a time, and helpers are shared *across* migrated and unmigrated files —
`generate_sheets._format_and_validate` is called by four of the eleven callers
and calls `worksheet.spreadsheet.batch_update(...)` itself. Under the renamed
protocol that helper would have to speak two vocabularies at once for the length
of the migration, or every one of its callers would have to migrate together,
which is precisely the cross-file rewrite Phase 0b/1's non-goals forbid.
Mirroring also lets `GspreadDoorway` return raw gspread objects as handles,
adding no wrapper code on the path that touches live data.

The disambiguation the rename was protecting is preserved another way: the fake
**rejects a wrong-shaped body** on either method (`batch_update` given `data`,
or `values_batch_update` given `requests`), so conflating the two endpoints
fails loudly instead of silently. Reversible if Jeff prefers the renames — it is
a mechanical rename of two methods plus the shared helper.

**2026-08-01 — the fake raises on anything it does not model.** Unknown
`batch_update` request types, unparseable Drive `q` clauses, and wrong-shaped
batch bodies all raise rather than no-op. A fake that silently ignores an
unmodelled request produces a *passing* snapshot for a command that would have
done something different live — which would make the snapshot actively harmful
rather than merely incomplete. Eight request types are modelled, matching what
the eleven caller files actually send.

**2026-08-01 — one live oddity found while modelling, recorded not fixed.**
`restructure_sheets._cascade_rename_pair_tab` builds `values_batch_update`
ranges with no sheet prefix (`"D5"`, from `rowcol_to_a1(...)[:-1]`). The Sheets
values API resolves an unprefixed range against the **first sheet** of the
spreadsheet, not against the tab the caller is holding — so that cascade writes
to sheet1 whenever the pair tab is not first. The fake reproduces this
faithfully (`test_unprefixed_values_range_resolves_against_the_first_sheet`).
Not fixed: Phase 0b/1's non-goal is explicit that current behaviour is recorded
as-is, including behaviour that looks wrong. Belongs to triage on #271 once
`restructure_sheets.py` has snapshots.

**2026-08-01 — Phases 0 and 1 interleaved rather than sequenced.** As first
written they were circular: snapshots need the doorway, and safely migrating to the
doorway needs snapshots. Resolved by building infrastructure first (0a, no caller
changes) then migrating one file at a time with snapshots captured immediately
after each. See `f20478e`.

**2026-08-01 — the fake is built from recorded real responses.** Not from the
gspread documentation. Its subtleties (1-indexing, `get_all_values` padding,
`update` range semantics) are what gets guessed wrong, and a wrong fake would
silently invalidate every test built on it.

**2026-08-01 — human review of `--apply` mutation logs before they become
snapshots.** Write paths have no pre-migration baseline to diff against, so this
review is the only barrier between a migration bug and its enshrinement as
correct behavior.

**2026-08-01 — supervision is front-loaded deliberately.** Phase 0a and the
first file migration are done rather than delegated, because their correctness
is only visible by reading. That investment is what makes phases 2, 5, 6, and 8
cheaply delegable later.

**2026-08-01 — the ragged-row hypothesis is empirically false; the fake is
simpler than predicted.** The protocol enumeration predicted that
partially-filled annotation tabs return *ragged* rows and that a fake would need
to reproduce raggedness selectively. The live capture falsifies this: all 80
tabs are internally rectangular. The real hazard is that `get_all_values()` pads
to the **used range**, which can be **narrower than the declared `col_count`** —
true of 10 of 80 tabs.

Consequences: the fake pads to used-range width, must allow that width to be
less than `col_count`, and need not synthesise ragged fixtures.
`generate_sheets.py`'s `len(row) >= N` guards are not dead code — they defend
against short responses, which are real, not ragged ones, which are not.

This is the clearest vindication so far of the rule that the fake be built from
recorded responses rather than inference: the inference was careful, plausible,
and wrong, and only the recording settled it. The correction is annotated inline
at `docs/drive-protocol-surface.md` § "Subtleties most likely to be guessed
wrong" so the falsified claim isn't left standing in a reference doc.

**2026-08-01 — protocol proposal accepted as the basis for the doorway.** Its six
design stances were reviewed and none rejected. The consequential ones:
handles are modelled as objects rather than a flat function list (long
read-mutate-reread chains in `sync_params.py` and `restructure_sheets.py` would
otherwise have to re-thread IDs they already hold); mutations must be visible to
the next read on the same handle; `batch_update` and `values_batch_update` stay
*two distinct methods* (they are different Sheets endpoints behind
similar-sounding gspread names, and merging them is the single most likely way a
fake silently diverges); structural requests stay generic
(`apply_sheet_requests`) rather than one method per request type, while
gspread's convenience methods stay individually named because callers reason
about their differing indexing conventions.

**Deferred:** collapsing the duplicated Drive helpers — now **issue #276**,
which owns this and lists all four groups and the axes they disagree on. Do
not restate it here or in code comments; point at the number. Precondition:
every Drive-writing command has snapshots first.

**2026-08-01 — the `untestable` trap was fixed immediately rather than deferred
to Phase 3.** A deliberate exception to Phase 2's inventory-only rule, taken
because the fix can only *widen* an allowed-value set (it cannot newly reject
anything already annotated) and because the failure it prevents is
collaborator-facing: the dropdown offered a value that validation then flagged
pink. Criterion values now come from `schemas.criterion_values()` rather than
being restated in `validate_coding.py`.

One hardcode deliberately left in place: coreference `prescreening` is
`row_type: element` and declares no `criterion` in `diagnostic_classes.yaml`,
so its criterion *name* (`referential`) still has to be named in code. Removing
it means adding `criterion: referential` to the schema, which changes sheet
generation — that wants snapshots first, so it belongs to Phase 3. Catalogued in
`docs/hidden-facts-inventory.md`.

**2026-08-01 — agent briefs must require incremental *commits*, not just
incremental writes.** The protocol-enumeration agent stalled roughly three
files into an eleven-file pass with all of its analysis uncommitted in the
working tree. It was resumed rather than relaunched (context intact, far
cheaper) and instructed to commit per file. Telling an agent to "write
incrementally" is not enough — unstaged work is not recoverable work. Folded
into the plan's *Working with agents* section for all future briefs.

---

## Open questions for Jeff

*(none currently — Phases 3 and 4 will raise the research/administrative
classification and the authority assignments)*
