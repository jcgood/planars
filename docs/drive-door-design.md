# The Drive door: design (Phase 10 unit 5)

**Status: accepted by Jeff 2026-10-13 (§ 7 records his answers). 5a–5d
built; 5e done; 5f under way: class sheets enforced live since 2026-10-19,
and every other kind specified and in watch since the same day (§ 8);
what is left is moving each to enforce, then refusing unlabelled targets.** Unit 5 of Phase 10 ([implementation plan](data-layer-implementation-plan.md),
Phase 10 table) was a design pause; this file is the design record. Progress
is tracked in [data-layer-progress.md](data-layer-progress.md), and the
decisions are logged there too.

## 1. The problem in one paragraph

Every command reaches Drive through the doorway (`coding/drive_doorway.py`),
but the doorway checks nothing it writes. `open_spreadsheet` returns the raw
gspread object, so once a command holds a sheet it can write anything
anywhere. The things that keep annotations safe are each written into one
command: `--regen-construction`'s refusal to drop annotated rows, its
snapshot before it clears a tab, `restructure-sheets`' journal, the
trailing-column dropdown check (a test only), and about 140 `_with_retry`
wrappers placed by hand. A new command, or a new code path in an old one,
gets none of them unless someone remembers. The design doc asked for a
chokepoint *that knows the topology*: what each sheet should look like and
who owns each cell. This unit builds that.

## 2. The four pieces

### 2.1 `coding/sheet_spec.py` — what a sheet should look like, from the schemas only

A function, not a registry: `spec_for(target)` builds the expected shape on
demand from sources that already exist, so it cannot drift from them.

For a **class sheet** (the first kind, § 5):

| Part of the spec | Read from (already exists) |
|---|---|
| tab list and order (locked first, constructions, locked last, Status) | `locked_tabs.locked_tab_specs()`, diagnostics YAML, `reorder_tabs` |
| each construction tab's header | `row_type` in `diagnostic_classes.yaml` (structural columns), `schemas.criteria_for` (criteria), `planar.yaml` `trailing_columns` |
| **who owns each column** | structural columns → tooling; criteria, `Source`, `Comments` → annotator |
| row key (what identifies a row) | `row_type`: position + element, pair key, or the keyed columns `keyed_rows` declares |
| allowed values per criterion column | `criteria_for` (placeholders `<free_text>`, `<position_names>` mean no dropdown) |
| locked tabs' content and protection | `locked_tabs` builders |
| sharing | the language's annotator in `people.yaml`, by name, writer; nobody by link |

The only new fact is the column-ownership rule, and it is a rule over
fields that already exist (structural vs. criteria vs. trailing), not a list.

### 2.2 A checking layer that wraps both the live and the fake doorway

`CheckedDoorway(inner)` wraps any doorway. `get_doorway()` returns
`CheckedDoorway(GspreadDoorway())` live and tests install
`CheckedDoorway(FakeDriveDoorway(...))`. Its handles wrap the inner
handles: reads pass straight through, every write is checked first.

This reverses the 2026-08-01 choice to return raw gspread objects "so there
are no wrapper bugs on the live path". The reason that held then (a wrapper
nobody tests) no longer holds: the checking layer sits *above* both
implementations, so every command test runs exactly the checking code that
runs live. The live-only code stays as thin as it is today.

**How every write gets checked.** Three things together make the door the
only way to write:

1. **Commands only ever hold wrapped objects.** `open_spreadsheet` returns a
   wrapper, and so does every route from it to a tab (`worksheet()`,
   `worksheets()`, `sheet1`, `ws.spreadsheet`). No command holds the raw
   gspread object.
2. **The wrapper has only the methods it can check.** It defines exactly the
   protocol's write methods (`update`, `update_cell`, `insert_cols`,
   `append_rows`, `clear`, `resize`, `update_title`, `add_worksheet`,
   `del_worksheet`, `reorder_worksheets`, `batch_update`,
   `values_batch_update`, and the file and permission methods). It does not
   forward unknown names to gspread (no `__getattr__` passthrough), so a
   method nobody has checked fails at once. A new kind of write has to be
   added to the door, with its check, before any command can use it.
3. **Nothing reaches Drive another way.** `tests/test_doorway_coverage.py`
   already fails if a command builds its own clients. It is extended to fail
   on any reach past a wrapper to the object inside.

**How the door knows which command is running.** The dispatch chokepoint in
`__main__.py`, where `preconditions.enforce` already runs (and, until 5c,
`provenance.record` did), hands the door the command name and its parsed arguments before
`main()` starts. That tells the door whether this invocation may write at
all (the read-only door, § 3) and what to put on each logged write. Code that
runs outside the dispatcher (tests, migrations) has to set this context
explicitly. A door with no command context refuses writes rather than
guessing.

Every write method then runs the same four steps:

1. **Target:** read the identity labels (§ 2.3) on the sheet and tab, and
   build the spec with `spec_for`.
2. **Effect:** turn the call into the cells, columns or permissions it
   would change. For `update(values, "A1")`, that means reading the tab's
   current contents (once per command, then cached) and lining the new
   values up against the header, which shows which columns are written and
   who owns them.
3. **Rules:** run the rules in § 2.4 that apply to that effect.
4. **Act:** with no violation, delegate to the inner doorway and log the
   write (§ 3). With a violation, enforce mode raises and writes nothing,
   and watch mode writes, records the violation and reports it (§ 4).

The door checks what a write *sends*. When Sheets computes the shown value
itself (a formula written with `raw=False`), the end-of-command check (rule 6)
covers the result.

The `batch_update` requests the door has to understand are a closed list
(nine types are used today: `updateSheetProperties`, `repeatCell`,
`setDataValidation`, `insertDimension`, `deleteDimension`,
`updateDimensionProperties`, `updateCells`, `mergeCells`,
`addProtectedRange`). A request type not on the list is refused, not passed
through: a new kind of write gets a check before it gets used.

### 2.3 Sheets carry their own identity

*As built (5d), files are labelled with Drive public properties, not Sheets
developer metadata or `appProperties`; only tabs use developer metadata.
See § 8. The paragraphs below are the design as accepted.*

To check a write, the door has to know what it is writing to. Today the
only way to know is the manifest, which is bookkeeping and goes stale.
Each spreadsheet gets Sheets *developer metadata* (labels stored in
the file that annotators never see):
`planars.kind=class_sheet`, `planars.lang=stan1293`,
`planars.class=ciscategorial`. Each tab gets `planars.construction=general`
(or `planars.locked=Instructions`, `planars.status`), so a tab keeps its
identity if someone renames it by hand. Drive files that are not sheets
(Docs, `manifest.json`, notebooks, PDFs, folders) get the same labels as
Drive `appProperties`.

The door reads the labels when it opens a file. A write to a file or tab
with no labels, or with labels it can't place, is refused ("explicit, not
implicit"). The manifest becomes something the door can *check* against the
sheets, which is the first step toward unit 11's "manifest shrunk to IDs".

Labelling the existing files is a one-time live migration (about 25 class
sheets plus the planar, diagnostics and status sheets, Docs and files).
The doorway gains `get_metadata`/`set_metadata`, and the fake models them.

### 2.4 Rules the door applies to every write

Each rule is derived from the spec; none names a command.

1. **Annotations are never lost silently.** A write that would blank or
   change a non-empty annotator-owned cell, or `clear`/delete/shrink a
   construction tab holding annotations, is refused unless it happens
   inside `with door.replacing(tab, reason=...)`. That block always
   snapshots the tab first (§ 3) and logs the reason. This generalises
   `_find_annotated_drops` and `_snapshot_before_regen` to every command.
2. **Locked tabs hold exactly what their builder makes.** Any write to a
   locked tab must leave it equal to the builder's output.
3. **Dropdowns match the spec.** `setDataValidation` only on criterion
   columns, with exactly the spec's values; never on structural or trailing
   columns. This turns `assert_no_criterion_writes_onto_trailing_columns`
   (a test today) into a rule that also runs live. Two commands broke it
   separately (#272, Finding 10).
4. **Protection only on locked tabs.** `addProtectedRange` anywhere else is refused.
5. **Sharing matches the sharing spec.** A grant must be to a named person
   the spec lists for that file, at the spec's role. No "anyone" grant on
   anything, notebooks and PDF reports included (Q4).
6. **Shape is checked at the end of the command.** Individual writes pass
   through shapes in between (insert a column, then write its header), so
   whole-tab shape is checked once, after the command finishes: the door
   remembers which tabs it touched, and the dispatch chokepoint in
   `__main__.py` (where preconditions and provenance already hook in) has
   it re-read those tabs and compare header, row keys, tab order and
   protection with the spec.

## 3. Safeguards that move into the door

Each one is deleted from where it lives now in the same commit that moves
it ("no half-finished transitions").

| Safeguard | Today | In the door |
|---|---|---|
| retry on 429/500/503 | ~140 hand-placed `_with_retry` calls; any new call can miss it | every call. A create (file, permission) retries only after checking the first attempt didn't land, which removes the duplicate-grant edge case recorded for #284 |
| dry run | each command's own `if args.apply` | **read-only door**: if `operations.yaml` says this invocation doesn't write to Drive (the `gating.py` match provenance already uses), the door refuses every write. `import-sheets`' pink highlighting, which runs on a dry run too, gets its own always-on mode in `operations.yaml` so the door allows it and provenance logs it (Q5) |
| refuse to drop annotations | `--regen-construction` only | rule 1 |
| snapshot before destroying | `--regen-construction` only, `regen_snapshots/` | every `door.replacing` block; same folder until unit 12 moves durable state into planars-data |
| provenance | one line per command invocation | one line per tab (or Drive file) written per command: what, which identity labels, how many cells, under which `replacing` reason |
| concurrent edits | none | before a rule-1 write, the door re-reads the cells. If they differ from what the command read earlier in the same run, an annotator edited the tab mid-run, and the write is refused |

`restructure-sheets`' journal stays where it is. It records progress
through a multi-step sequence, which is the command's own logic and not a
property of any single write.

## 4. Watch mode and enforce mode

The door runs in one of two modes, set in one place:

- **enforce**: a violation raises, nothing is written.
- **watch**: the write goes ahead, the violation is logged, and at the end
  of the command the door files or updates one GitHub issue through
  `coding/issues.py`, with a new registered label `door-violation`.

Printing to the terminal reaches no one, so watch mode reports in an issue,
which works on whatever machine ran the command (laptop or daily
refresh) and doesn't need unit 12. The fake runs in enforce mode from the
first commit. Every violation the existing command tests hit is either a
real bug, fixed then, or a gap in the spec, fixed in the spec.

**When a kind moves from watch to enforce (Q7):** once the door has seen
at least one real write to that kind go through with no violation, and
every violation reported in watch has been resolved. A kind nothing has
written stays in watch, however long that takes; a quiet period proves
nothing. Class sheets also keep the plan's minimum of a week, because the
daily refresh writes them on day one and the less frequent commands that
write them need a chance to run.

## 5. Order of work

Each step leaves a complete, working system.

1. **5a** `sheet_spec.py` for class sheets, plus a test that every recorded
   class sheet in the frozen test data matches its spec. Whatever doesn't
   match is real drift: fix it or explain it. Building it first required the
   row shapes to have one source: pair-row shapes were declared in no
   schema (hidden-facts D3, D4), so `planar.yaml` gained `pair_row_shapes`,
   and each pair construction a `pair_shape`. The test compares tab order,
   headers and row keys. It does not compare locked-tab wording with the
   recording, because every change of wording would fail it until the next
   refreeze; rule 2 checks locked tabs at write time instead.
2. **5b** `CheckedDoorway` with rules 1–5, the closed request list, the
   read-only door, and retry moved in. The fake runs in enforce mode. Call-site
   `_with_retry`s are deleted in the same commit.
3. **5c** Snapshots, per-write provenance and the concurrent-edit check move
   in. `_snapshot_before_regen`, `_find_annotated_drops` and per-invocation
   provenance are deleted.
4. **5d** Identity labels: doorway methods, the fake's model, and a
   migration that labels the live files (**a live write, named for your
   approval when it's ready**). Rule 6 (end-of-command shape check) lands
   here, because it needs identity to find the spec. Rule 6 also needs the
   rows of pair and keyed tabs, which 5a's spec leaves to the tab they are
   generated from. They come from the generators' own row builders, the
   functions integrity-check's dependent-staleness section already calls,
   not from a second copy.
5. **5e** Live in watch mode for class sheets (on since 5b, § 8), until the
   § 4 rule is met (at least a week). Meanwhile: the rest of unit 3, and unit 8.
   **The week restarted 2026-10-18:** until then the end-of-command half of
   the door (rule 6, labels, provenance, the `door-violation` issue) never
   ran live, because `running()` found no door yet (fixed in Phase 10 unit
   20), so the quiet days before it proved nothing.
6. **5f** Enforce for class sheets. Then the other kinds, in the plan's
   order for building their spec sections: sharing → planar → diagnostics
   → status sheets → notes Docs → files (`manifest.json`, notebooks, PDFs,
   folders). They can be in watch together, and each moves to enforce on
   its own by the § 4 rule. The sharing step starts with Q4's test: share
   one notebook by name and confirm an annotator can open it in Colab
   before link sharing is removed from notebooks and reports. Before the
   last kind is enforced, a write to an unlabelled target is refused
   outright, so no kind is left unchecked.

## 6. What this does not cover

- Annotators' own edits in the Sheets never pass any door. They are handled
  after the fact by `import-sheets` and `validate-coding`, and later by the
  proposal sheets in unit 11.
- Local files (`coded_data/`, state files) are unit 6, designed at the next
  pause with units 15 and 11.
- Reads stay unchecked ("reads may stay promiscuous").

## 7. Decisions (Jeff, 2026-10-13)

**Q1. Check each write, the result, or both? Both.** Each write is checked
against the rules that hold at every moment (annotations, locked tabs,
dropdowns, protection, sharing), and whole-tab shape is checked once at the
end (§ 2.4). Checking only the end result would let an annotation be wiped
mid-run and still "match the spec". Checking only each write would refuse
the in-between shapes ordinary commands pass through.

**Q2. Wrap the live handles? Yes.** This reverses the 2026-08-01 choice to
return raw gspread objects. The checking layer sits above both the live and
the fake doorway, so the tests run the same checks that run live (§ 2.2).

**Q3. How a command declares an intended replacement of annotations: the
`door.replacing(tab, reason)` block,** which always snapshots and logs the
reason. There is no list of which commands may use it. Per-write provenance
makes every use visible, and the end-of-command check confirms every answer
read earlier is still on the sheet or in the snapshot.

**Q4. Notebooks and PDF reports: named people only,** after a test that a
notebook shared by name opens in Colab for a signed-in annotator (§ 5,
step 5f). Until that test passes they keep link sharing.

**Q5. `import-sheets`' dry run keeps painting highlights.** The painting is
declared as its own always-on write in `operations.yaml`, so the read-only
door allows it and provenance logs it (§ 3).

**Q6. Extra Drive reads: accepted.** At most one read per tab written,
reusing the command's own read of the tab where there is one. Heavy runs
(`restructure-sheets`, a wide `sync-params`) may slow down under Google's
roughly 60-reads-a-minute limit; the door's retry absorbs that.

**Q7. When the trial ends: once the door has seen a real write go through
cleanly,** not after a fixed number of weeks (§ 4). Claude kept the plan's
one-week minimum for class sheets, for the reason given in § 4; Jeff may
drop it.

## 8. As built

**5b (2026-10-13), `coding/drive_door.py`.** Built as § 2.2–2.4 and § 3
describe, with these choices where the design left a gap:

- **Which sheet is which, before 5d's labels.** The rules need a sheet's
  identity, but labels come in 5d (they need a live migration). Until then
  the door places a class sheet from the manifest (read once per command,
  quietly) or from the identity a command passes to
  `create_spreadsheet(title, identity=class_sheet(lang, class))` (the four
  places a class sheet is made). In 5d that argument becomes the labels
  written at creation, and the manifest lookup is deleted. A write to a
  spreadsheet the door can't place passes the class-sheet rules, as § 5
  allows until the last kind is enforced.
- **Live mode is watch for every check** (dry run, request list, rules 1–5):
  `LIVE_MODE` in `drive_door.py`, the one place. Watch began with 5b rather
  than 5e, so the § 4 clock for class sheets starts with the first daily
  refresh after 5b; 5e is now just the wait.
- **Rule 5 checks who and how, not the role**, until 5d: an archived class
  sheet is still in the manifest when it is lowered to reader, so the door
  can't yet tell an archived sheet from a live one. Labels will carry that.
- **Q5** is `always_on_writes` in `operations.yaml` (import-sheets:
  `highlighting`) plus `with drive_door.always_on("highlighting")` around the
  two highlighting writes in `validate_coding.py`.
- **Rule 1 in 5b** permits writes inside `replacing()` and records the
  reason; the snapshot moves in with 5c. Two commands use it:
  `--regen-construction` (`generate_sheets._rebuild_tab`, `_rebuilding` in
  5b) and `sync-params --remove`.
- **Tests** run commands through `tests/command_runner.run_command`, which
  tells the door the command; `tests/test_drive_door.py` holds each rule.

What the door found on its first run of the test suite: `generate-sheets
--push-manifest` writes the manifest but no `operations.yaml` record said so
(added as a mode; provenance had never logged it); the rename-class tests
renamed a class in the language's file but not in the schema, so the new
sheet had no spec (the tests now register the new name, as a real rename
does); and the hand-placed retries never retried Drive file or permission
calls at all, since those raise the Google client's own error, not gspread's
(the door retries both).

**5c (2026-10-13), the same file.** Snapshots, per-write provenance and the
concurrent-edit check moved into the door, as § 3 describes, with these
choices:

- **The refusal to drop answered rows is part of `replacing()`.** Rule 1
  lets anything through inside `replacing()`, so `_find_annotated_drops`
  could only move into the door if the block learns which rows survive.
  `replacing(tab, reason, kept=..., allow_drop=...)` takes the row keys
  (the schema's `row_key`, as the tab holds them now) whose answers the
  rebuild carries over. Before the block runs, any row holding an answer
  whose key is not in `kept` raises `AnswersWouldBeDropped`, **in every
  mode**: it replaces a refusal that was always live, and watch mode must
  not weaken it. `--confirm-drop` is `allow_drop`. "Holding an answer" is
  now any criterion, Source or Comments cell; the old check looked only at
  the first criterion column, so a row with only a comment could go
  silently. Rows with a blank key used to be skipped; now an answered one
  counts as dropped. One check now serves pair and keyed tabs alike:
  `biuniqueness_rows.carry_over` no longer returns drops, and its
  `describe_drop` is deleted. A coreference `--pos-remap` passes the old
  keys of the rows it carries over (`_coreference_key_map`).
- **The concurrent-edit check runs when `replacing()` starts**, the only
  place a rule-1 write is allowed: the door re-reads the tab and compares
  the annotator-owned cells (and the header) with what the command read
  earlier in the run. A difference is a violation by mode (new, so watch
  first). This re-read is also the snapshot, so it costs one read per
  replaced tab, as § 3 and Q6 allow.
- **The snapshot is the re-read**, saved to `regen_snapshots/` (one file per
  tab, overwritten, as before) with the command and reason. Since every
  answer read earlier is then on the sheet or in the snapshot, Q3's
  end-of-command confirmation adds nothing until rule 6 (5d) re-reads the
  tabs anyway; the check that carried-over answers actually landed comes
  with rule 6.
- **Provenance is written when the command ends** (in `running()`'s
  `finally`, so a failed run still logs what it wrote): one line per tab or
  Drive file, with the command's arguments, the actions, calls, cells,
  identity and any `replacing` reasons. `provenance.record` and its call in
  `__main__.py` are deleted; an `--apply` run that wrote nothing no longer
  leaves a line. Tests' log and snapshots go to each test's `tmp_path`
  (`tests/conftest.py`).

**5d, labels (2026-10-14), the same file.** Every Drive file the tooling
makes now says what it is, and the door reads that instead of guessing from
the manifest. Choices where § 2.3 left a gap or turned out wrong:

- **Files are labelled with Drive public `properties`**, for spreadsheets
  too, not Sheets developer metadata (§ 2.3) and not `appProperties`, which
  only the OAuth client that wrote them can read; a second coordinator has
  their own client. One mechanism identifies any file id, which the sharing
  rule needs as well. Keys: `planars_kind`, `planars_lang`, `planars_class`,
  `planars_name`, and `planars_state` (`archived`).
- **Tabs are labelled with Sheets developer metadata** (document
  visibility): `planars_tab_kind` (locked, construction or status, the names
  `sheet_spec` now imports from the door) and `planars_tab` (its name). The
  door goes by a tab's label where it has one, so a tab renamed by hand is
  still checked against the right part of the spec.
- **Kinds are one table, `KINDS`, and validated:** class_sheet (language,
  class); planar_sheet, diagnostics_sheet, status_sheet, notes_doc, report
  (language); manifest; notebook (domains, validation or report, each with a
  language, or all_languages); folder (root, language, archive or status;
  language and archive folders with a language). An identity that doesn't
  fit can't be made, and a label that doesn't fit places nothing.
- **Every create on the door requires `identity=`** and writes the label
  (a spreadsheet in a second call straight after, since Sheets can't take
  Drive properties when it makes one). `get_or_create_folder` checks that a
  folder it finds isn't labelled as something else. `set_identity` labelled
  an existing file and refused, in every mode, to relabel one (deleted
  2026-10-17, unit 19, with the public `label_tabs`: only the labelling
  migration below used them).
- **The door places a file** from what this command made, then its label
  (read once per command). Until the migration below, a class sheet not yet
  labelled was placed from the manifest; that step was deleted on
  2026-10-16, so an unlabelled file is one the door can't place.
- **Rule 5 checks the role:** a class sheet's annotator is a writer while it
  is live and a reader once it is labelled archived, on `create_permission`
  and `update_permission` alike. So `mark_archived` comes first where a
  sheet is archived (`restructure_sheets._lock_archived_sheet`,
  `prune_manifest._archive_drive_sheet`), and `_rollback_unit` marks it live
  before raising the annotator back to writer. `mark_archived` refuses a
  file with no label.
- **Tab labels are written when a command that was allowed to write
  succeeds,** for each class sheet it wrote: one `batch_update` per sheet,
  only for tabs with no label yet, only tabs the spec lists (another tab is
  left for rule 6 to report). A dry run that only painted highlights labels
  nothing. Renaming a tab through the door drops its labels, and the end of
  the command labels it afresh under its new name if the spec has it. The
  door's own label requests are not in `REQUEST_TYPES`: commands cannot
  send them.
- **Provenance** shows the labelling as its own line per sheet
  (`label_tabs`), and a file's label writes as `label`.

What changed in the saved test outputs: every create now shows its label,
and every command that writes a class sheet labelled its tabs once, because
the recorded sheets had none yet. That went away with the migration and
refreeze below.

**5d, labelling the existing files (2026-10-15/16).**
`migrations/label_drive_files.py` found every file from the records that
name it (`drive_config.json`, the manifest's class sheets, each language's
`_archived/` folder, the Annotation Status folder) and, run live on
2026-10-15 with Jeff's approval, labelled 127 files and the 108 tabs of the
24 live class sheets. Two things the plan didn't foresee: the older
`_archived/v{N}/` folders restructure-sheets used before it put `_v{N}` on
the sheet's name are archive folders too, and the sheets in them archived
class sheets (16 of the 51); and synth0001's retired allomorphy screening
sheet, in its `_archived/` folder, fits no kind and is left unlabelled.
`capture-drive-state` now records the labels (file properties, tab
developer metadata), the test data was refrozen, and the manifest step was
deleted from the door.

**5d, rule 6 (2026-10-14), the same file.** The end-of-command shape check,
as § 2.4 describes, with the 2026-10-14 decision that it reports only what
the command made wrong (`data-layer-progress.md` decisions log). Choices:

- **What counts as changing a sheet's shape:** writing values, adding or
  removing rows, columns or tabs, renaming or reordering tabs, and
  protecting. Formatting, dropdowns, highlights and frozen rows do not, so
  import-sheets' daily highlighting costs no extra read.
- **Before:** the first time a command makes such a write to a class sheet,
  the door reads the sheet's tab list (names, order, protection: one
  metadata read) and keeps the tab's content as it already holds it (the
  command's own read where there was one). A sheet or tab the command made
  has no "before": all of its shape is the command's.
- **After:** when a command that succeeded, and was allowed to write, ends,
  the door re-reads the tab list and each tab it wrote (one read each, Q6),
  and compares both states with the spec as sets of mismatches: tabs
  missing, extra, out of order, protected or not; per tab, columns missing,
  extra or out of order, rows missing, extra or present twice (by row key),
  and a locked tab's content. Only the mismatches that are new are
  reported, as the door's other violations are (raise in enforce, the
  `door-violation` issue in watch). Archived sheets are not checked.
- **Rows of pair and keyed tabs** come from the generators:
  `generate_sheets.pair_rows`, which creating, extending and regenerating a
  sheet now all call (it had three copies), and `biuniqueness_rows.keyed_rows`;
  a keyed tab's hand-added rows (`biuniqueness_rows.is_generated`) are left
  out. When the rows can't be worked out (a source tab not imported yet, an
  element whose prescreening value differs by position), rows are not
  compared, and nothing is filed: `pair_rows(file_issue=False)`.
- **A replacement sheet** (restructure-sheets archives a class sheet and
  makes a new one) is made with `create_spreadsheet(..., replaces=old_id)`:
  the old sheet's tab list is the "before", and the new sheet's pair and
  keyed tabs are not compared row by row, because restructure carries their
  rows over (renames applied) rather than generating them; their staleness
  against the generator stays the dependent-stale check's. Everything else
  on the new sheet is compared in full.
- **Holding columns.** `sync-params --split/--merge` parks an old criterion
  as `_split_<name>`/`_merged_<name>` until the coordinator deletes it by
  hand; the spec allows these (`sheet_spec.PARKED_COLUMN_PREFIXES`, now also
  what sync-params and integrity-check read, which each had their own copy).
- **Q3's confirmation** that carried-over answers landed is covered: a row
  the rebuild meant to keep but did not write shows as a missing row.

What rule 6 found on its first run of the test suite: `sync-params
--split`/`--merge` put new criterion columns after the existing ones rather
than where the language's diagnostics file lists them (now `_insert_at`);
`restructure-sheets --rename-class` made the new sheet with no Status tab;
restructure left a tab with no header at all when the old sheet lacked a
pair tab (now it writes the header); and most command tests pointed only
the command's own module at their copy of the language folders, so the
door, and its specs, had been reading the real `coded_data/` in those tests
since 5b (`fake_drive.point_coded_data_at` now points every module).

**Reads the door adds (2026-10-15, #306).** The door found the tab a
`batch_update` request names by re-reading the spreadsheet's tab list, once
per request. import-sheets paints one request per invalid cell, so the
daily refresh of 2026-10-15 made hundreds of reads, ran out of Google's
per-minute read quota, and crashed (the status-sheet build after it failed
on the same quota, #308). The door now keeps each spreadsheet's tab list for
the command and re-reads it only for a tab id it hasn't seen, and
`values_batch_update` looks each tab up once per call, not once per cell.
Q6's "at most one read per tab written" now holds for these paths too
(`test_many_requests_to_one_tab_read_its_tab_list_once`).

**Rule 7, comments (2026-10-17, #309).** The door now carries comments
(`list_comments`, `create_comment`), so an annotator without GitHub can be
told about values to fix: a comment that mentions their address makes
Google email them. A comment goes only on a class sheet, and may mention
only that language's annotator; a create is retried only after checking it
didn't land, as for files and grants. The Status tab also gained a third,
tooling-owned column (`planar.yaml` `status_tab.columns`, now each with a
role and an owner), which rule 1 treats like the Construction column.

**5f, sharing (2026-10-18).** Sharing is the first kind specified for every
file, not only class sheets: `sheet_spec.sharing_spec(identity, archived)`
says who a file is shared with and at what role, and whether a link share is
allowed, from one table per kind (folders by which folder). Every kind in
`KINDS` has an entry, and a kind without one raises. The rules: class,
planar and diagnostics sheets and the notes Doc, the language's annotator as
writer; the status sheet and the language folder, the annotator as reader;
the Annotation Status folder, every annotator as reader; the root and
archive folders and the manifest, nobody; notebooks and PDF reports, a
reader link share and nobody by name, until Q4's test. An archived file is
read-only for everyone on it, with no link share. Rule 5 now checks this on
every file the door can place, for all three grant writes: a grant made or
changed has to match the spec, and a grant the spec calls for can't be
removed (removing one it doesn't call for, like a link share added by hand,
is allowed). The full suite found no command breaking it.

A read-only comparison of the live grants with the spec (2026-10-18; a
file's own grants only, since inherited ones come from its folder) found two
differences, both made by hand: the root folder gives Adam writer, which
every file under it inherits, so he can edit the manifest and every
archived class sheet whatever their own grants say; and synth0001's archived
biuniqueness sheet keeps Adam as reader, though synth0001 names no annotator.
Jeff's answers (2026-10-18): coordinators are writers on the root, so a
second coordinator's own account can run the tooling (`coordinator: true`
in people.yaml, read by `people.coordinator_emails`; archived sheets stay
editable for coordinators only, through the root); and the synth0001 grant
goes (`migrations/remove_synth0001_archived_grant.py`, run 2026-10-19).

**Standing grants (2026-10-19).** The door sees only the grants the tooling
makes, so integrity-check gained a SHARING section, in the daily report:
it finds every file by its label and compares its own grants with the spec
(`sheet_spec.sharing_differences`), naming people from people.yaml, never by
address, since the report goes into a public issue. For the tests to start
from real sharing, `capture-drive-state` now records each sheet's own grants
by person name, and the fake gives the name its people.yaml address (the
placeholder, in tests); the test data was refrozen. Found on the way:
the live doorway's `list_files` read only Drive's first page of 100 results,
which a listing by label would soon have outgrown; it now reads every page.

**5f, class sheets enforced (2026-10-19).** Jeff dropped the one-week
minimum (§ 4, Q7): the first refresh that reported anything (2026-10-18)
made 80 writes with no violation, which met his rule. The mode is now chosen
per write by the kind of file written: every check is told its target (the
file id, or the identity of a file being made), and a kind in
`LIVE_ENFORCED_KINDS` raises live, while every other kind stays in watch.
The end-of-command shape check (rule 6) is enforced for class sheets too;
since the planar Sheet joined it (below), each sheet's own kind decides, and
watched sheets' problems are reported before an enforced one raises. A write
to a file the door can't place stays in watch. Tests that are about watch
mode's reporting turn the list off (`watch_all`).

**5f, the planar Sheet (2026-10-19).** The second kind with a spec of its
contents (`sheet_spec.planar_sheet_spec`; the door's `SPECIFIED_KINDS`):
one tab holding exactly `planar_{lang}.tsv`, its header and then its rows.
Until unit 11 locks it (`ownership-design.md` § 3.1), the annotator edits
the Sheet and the daily `import-planar --apply` carries the edits into the
file, so every cell counts as the annotator's: rule 1 covers them all, and
there are no tooling columns, no dropdowns (rule 3) and no protection (rule
4). Rule 6 checks the Sheet has one unprotected tab equal to the file, rows
read by column name and compared in order, as import-planar compares them.
All three recorded planar Sheets match.

The finding: every push of the file to the Sheet (`import-planar
--to-sheet`, which restructure-sheets calls, and `generate-sheets --force`)
clears and rewrites it, so an annotator's edit made since the last import
was lost with no trace. The door cannot tell that edit from the
coordinator's change being pushed without the base unit 11 brings (§ 3.4
there), so the push is not refused: it now runs inside `replacing()`, which
saves the Sheet to `regen_snapshots/` first, notices an edit made mid-run,
and puts the reason in provenance. Found on the way: the push read the file
with pandas' default missing values, so a cell holding `NA`, `null` or
`None` went to the Sheet blank (two reads in import-sheets had the same
fault; all now `keep_default_na=False`).

**5f, the diagnostics Sheet (2026-10-19).** The third kind with a spec of
its contents, built the same way: the planar and diagnostics Sheets are now
both "copy sheets" (`drive_door.COPY_SHEETS`, `sheet_spec.copy_sheet_spec`),
one tab holding exactly one file, every cell the annotator's until unit 11.
The diagnostics Sheet's file is what `diagnostics_{lang}.yaml`, the source,
renders to (`make_forms._yaml_to_tsv_df`, which writes the TSV copy and is
what the push sends). All three recorded diagnostics Sheets match. The push
(`sync-diagnostics-yaml --to-sheet`, daily) now runs inside `replacing()`,
as `generate-sheets --force` already did.

The finding, recorded against unit 11b (`ownership-design.md` § 6): the
daily refresh imports the diagnostics Sheet, then regenerates the TSV from
the YAML and pushes the YAML back over the Sheet, so an annotator's edit
there is undone the same day. A changed value list reaches no issue at all;
an ambiguous change's `diagnostics-drift` issue closes the next day, since
the Sheet no longer shows it. Nobody has edited a diagnostics Sheet yet, and
11b retires that intake, so no interim fix (Jeff, 2026-10-19: fix later).

**5f, the status sheets (2026-10-19).** `sheet_spec.status_sheet_spec`:
one tab, `Status`, every cell the tooling's (`STATUS_SHEET_COLUMNS`, now
the one statement of its header, which generate-status-sheet reads); a
banner, the header, then one row per class and construction of the
diagnostics file, in order, each with a status. Rule 1 has no annotator
cells to look after; rule 3 allows no dropdowns; rule 4 no protection (the
sheet is read-only to annotators by sharing, rule 5's job). Rule 6 checks
the tab's name and its rows, reading a construction cell's link label (a
live read returns the label; the offline Drive, the `=HYPERLINK` formula).
The sheet is rebuilt whole every run, so rule 6 reports everything wrong
with it afterwards, not only what is new. Status sheets are not in the
recorded test data (they are found by name in their own folder), so the
tests check sheets the command writes.

Found and fixed: the command resized the tab to its new length plus two,
so when a language lost constructions, up to two rows of the old ones (with
their status colour) stayed on the page. It now cuts the tab to the new
rows first.

**5f, the notes Docs and the files (2026-10-19).** The last two steps of
§ 5's order, done together: the notes Docs, then the files (the manifest,
notebooks, PDF reports, folders). Every kind is now either a spreadsheet,
whose tabs and cells rules 1–4 and 6 check (`drive_door.SHEET_KINDS`), or
a file that is not one (`FILE_KINDS`), and a test holds the two together to
`KINDS`. A file's spec, `sheet_spec.file_spec`, is what it is called, the
folder it sits in, its type, what may be written into it, and whether only
one live file may carry its identity:

| Kind | Name | Folder | Content |
|---|---|---|---|
| notes Doc | `{Name [glottocode]} — Annotation Notes` | the language folder | the annotator's; the tooling only appends acknowledgment lines |
| report | `report_{lang}.pdf` | the language folder | a PDF |
| notebook | `{domains, validation, report}_{lang}.ipynb`; `all_languages.ipynb` | the language folder; the root | a notebook |
| manifest | `manifest.json` | the root | JSON the manifest contract accepts |
| folders | `ConstituencyTypology`, `Annotation Status` (outside every project folder); `{lang}` (the root); `_archived` (the language folder) | | nothing |

Only one of each may exist, except archive folders: the `_archived/v{N}/`
folders restructure-sheets made before it put `_v{N}` on archived names
are labelled archive folders too (5d, above).

**Rule 8** checks each create, rename, move and upload against the spec:
the name, folder and type it sends must be the spec's, and so must the kind
of content (the manifest through `manifest_contract.check`, a notebook by
its cells list and nbformat number, a PDF by its first bytes); a notes
Doc's text is never replaced, and only one acknowledgment line at a time,
in the form check-notes strips before it looks for new notes
(`drive.acknowledgment_line`), is appended to it; and a create of a kind
only one of which may exist is refused when a live one is already labelled
with that identity, since the commands keep the first one's id and a second
would be found by no one (for a notes Doc, the annotator's notes would be
split between two). The checks run on what each write sends, so a file
that was already off its spec (an older name, say) is not blamed on a
command that did not touch that part of it, and no end-of-command re-read
is needed: unlike a sheet, no file passes through an in-between shape.

Choices where the design left a gap:

- **The spec is the one place each file is named.** The names were typed
  in the commands that make the files (generate-notebooks four times,
  generate-reports, the folder names in four commands, the manifest's in
  `upload_manifest`); they now read `file_spec` or its folder-name
  constants, and `create_or_update_shared_file` takes its name and type
  from the identity. The labelling migration keeps its own copy of the
  status folder's name, as a record of a run that is finished.
- **The manifest check moved into the door.** `upload_manifest` printed a
  warning for a manifest that broke its contract and wrote it anyway; the
  print reached no one. The door reports it in watch mode and refuses it
  once the manifest is enforced, which happens only after real writes have
  passed (§ 4), so the contract's caution about unmodelled live data is
  tested first.
- **The offline Drive models the labelled folders.** Its root folder,
  manifest and language folders now carry their labels and the grants their
  sharing rule gives, as the live ones have since the 5d migration
  (integrity-check's SHARING section confirms the grants daily).

Found and fixed, both by the new rule on the test suite's first run:

- With no root folder in `drive_config.json`, generate-notebooks fell back
  to a legacy key and then to the first language folder, putting the
  all-languages notebook among one language's files. Neither fallback was
  in use (the live config has the root folder); both are deleted, and the
  command stops with its existing "run setup-root-folder" message.
- With no manifest id in `drive_config.json`, or an update that failed,
  `upload_manifest` made a second `manifest.json` beside the first, which
  every other copy of the config still named. It now finds the manifest
  Drive holds by its label and updates that, and creates one only when
  Drive holds none.

Each kind's § 4 clock starts with its first real write: the notes Docs
when check-notes next acknowledges notes, the notebooks and reports at the
next generate-notebooks and generate-reports runs, the manifest and
folders at the next command that saves or makes one.
