# The Drive door: design (Phase 10 unit 5)

**Status: accepted by Jeff 2026-10-13 (§ 7 records his answers). Nothing
built yet.** Unit 5 of Phase 10 ([implementation plan](data-layer-implementation-plan.md),
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
`__main__.py`, where `preconditions.enforce` and `provenance.record` already
run, hands the door the command name and its parsed arguments before
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
5. **5e** Live in watch mode for class sheets, until the § 4 rule is met
   (at least a week). Meanwhile: the rest of unit 3, and unit 8.
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
