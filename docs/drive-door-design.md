# The Drive door: design (Phase 10 unit 5)

**Status: draft for Jeff's review, 2026-10-13. Nothing here is built yet.**
Unit 5 of Phase 10 ([implementation plan](data-layer-implementation-plan.md),
Phase 10 table) is a design pause: this file is the design, and § 7 lists the
decisions that are Jeff's. Once it is accepted, decisions move to the
decisions log in [data-layer-progress.md](data-layer-progress.md) and this
file stays as the design record.

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
   the spec lists for that file, at the spec's role. No "anyone" grant
   except where the spec lists one (see question Q4).
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
| dry run | each command's own `if args.apply` | **read-only door**: if `operations.yaml` says this invocation doesn't write to Drive (the `gating.py` match provenance already uses), the door refuses every write. This catches a dry run that writes, e.g. `import-sheets` painting pink highlights without `--apply` (a known, accepted gap; Q5) |
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

## 5. Order of work

Each step leaves a complete, working system.

1. **5a** `sheet_spec.py` for class sheets, plus a test that every recorded
   class sheet in the frozen test data matches its spec. Whatever doesn't
   match is real drift: fix it or explain it.
2. **5b** `CheckedDoorway` with rules 1–5, the closed request list, the
   read-only door, and retry moved in. The fake runs in enforce mode. Call-site
   `_with_retry`s are deleted in the same commit.
3. **5c** Snapshots, per-write provenance and the concurrent-edit check move
   in. `_snapshot_before_regen`, `_find_annotated_drops` and per-invocation
   provenance are deleted.
4. **5d** Identity labels: doorway methods, the fake's model, and a
   migration that labels the live files (**a live write, named for your
   approval when it's ready**). Rule 6 (end-of-command shape check) lands
   here, because it needs identity to find the spec.
5. **5e** Live in watch mode for class sheets, at least a week. Meanwhile:
   the rest of unit 3, and unit 8.
6. **5f** Enforce for class sheets. Then the other kinds in the plan's
   order: sharing → planar → diagnostics → status sheets → notes Docs →
   files (`manifest.json`, notebooks, PDFs, folders). Each kind gets its
   spec section and its own watch → enforce. Before enforce for the last
   kind, a write to an unlabelled target is refused outright, so no kind is
   left unchecked.

## 6. What this does not cover

- Annotators' own edits in the Sheets never pass any door. They are handled
  after the fact by `import-sheets` and `validate-coding`, and later by the
  proposal sheets in unit 11.
- Local files (`coded_data/`, state files) are unit 6, designed at the next
  pause with units 15 and 11.
- Reads stay unchecked ("reads may stay promiscuous").

## 7. Decisions for Jeff

**Q1. Check each write, or only the result?** Recommended: both, as in
§ 2.4. Each write is checked against rules that hold at every moment
(annotations, locked tabs, dropdowns, protection, sharing), and whole-tab
shape is checked once at the end. Checking only the end result would let an
annotation be destroyed mid-run and then "match the spec". Checking only
each write would make in-between states fail.

**Q2. Wrap the live handles** (reversing the 2026-08-01 "raw gspread
objects" choice)? Recommended: yes, for the reason in § 2.2. The checking
code is shared with the fake and so is under test.

**Q3. How a command says "I mean to replace these annotations".**
Recommended: the `door.replacing(tab, reason)` block, which always takes
a snapshot and logs the reason, with no list of which commands may use it.
A list would be one more registry to keep true. The risk is that callers
reach for the block too easily. The per-write provenance makes each use
visible, and the end-of-command check can confirm every annotation read
earlier is still somewhere on the sheet or in the snapshot.

**Q4. Notebooks and PDF reports are shared "anyone with the link"** (every
regeneration re-grants it). Unit 14 removed link sharing from folders and
sheets but didn't decide these. Options: (a) keep link sharing for these
two as a listed exception in the sharing spec; (b) named people only.
Recommended: (b), for consistency with "sharing by name only", **if**
Colab opens a notebook shared by name for an annotator who is signed in.
I would test that with one notebook before choosing. Your call either way.

**Q5. A dry run that writes.** The read-only door would break
`import-sheets`' dry run, which today paints pink highlights on invalid
cells. Options: (a) only `--apply` paints; (b) declare highlighting a
write in its `operations.yaml` record, so a dry run is allowed to do it.
Recommended: (b). Highlighting is feedback to the annotator, and they
should get it whoever ran the command. (a) would silently leave pink stale
after a dry run.

**Q6. Extra Drive reads.** Rule 1 and the concurrent-edit check read a tab
before writing it: at most one extra read per tab per command, cached.
The daily `update-sheets` touches about 25 sheets, within the read quota.
Nothing to decide unless you object.

**Q7. The watch week.** The plan says at least a week of watch mode for
class sheets. For the later kinds (sharing, planar, …) I suggest a shorter
watch: one week for all of them together, run at once after class sheets
are enforced, rather than a week each.
