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

---

## Current state

**Phase:** 0b/1 — migrating callers, 4 of 17 done (started 2026-08-01)
**Live Drive writes performed:** none. Permitted from Phase 9 only.
**Adam's annotation data touched:** none.
**Last worked:** 2026-08-02

Bugs found and fixed while doing this work, all the same root cause — something
inferred which column held a value from the wrong source: **#272** (dropdowns,
fixed), **#274** (coreference analysis returned different answers on different
runs, fixed). Open and needing a decision: **#275** (stan1293's
`phrasal_accent/general` sheet shape vs. the schema), **#276** (collapse the
duplicated Drive helpers — blocked until every Drive-writing command has
snapshots), **#273** (verified false alarm, safe to close).

### Status by unit

| Unit | Status | Commit |
|---|---|---|
| Design record + plan written | done | `7b995b9`, `f20478e` |
| Phase 2 — hidden-fact inventory | **done** → `docs/hidden-facts-inventory.md` | `e27bbe3` |
| Phase 0a — protocol surface enumeration | **done** → `docs/drive-protocol-surface.md` | `b978101`..`46bf833` |
| Phase 0a — protocol proposal reviewed | **done** — accepted, see decisions log | — |
| Phase 0a — `capture-drive-state` command | **done** | `c87ae7d` |
| Phase 0a — fixture capture run (read-only, live) | **done** — 29 sheets, 80 tabs | `b40cd64` |
| Phase 0a — doorway module (`coding/drive_doorway.py`) | **done** | `05be9af`, renamed `2706965` |
| Phase 0a — fake doorway (`tests/fake_drive.py`) + smoke tests | **done** — 62 tests | `05be9af` |
| Phase 0b/1 — file 1 of 17: `refresh_dropdowns.py` | **done** — snapshots captured, mutation log reviewed and accepted | `5ca369d` |
| Phase 0b/1 — file 2 of 17: `generate_reports.py` | **done** — snapshots captured, pre/post diff clean | `62047c3` |
| Phase 0b/1 — file 3 of 17: `setup_root_folder.py` | **done** — snapshots captured, pre/post diff clean | `3d70069` |
| Phase 0b/1 — file 4 of 17: `apply_pending.py` | **done** — snapshots captured, pre/post diff clean | `f7bc5fa` |
| Phase 0b/1 — files 5–17 | not started — see § "Migration order" | — |
| Phases 3–9 | not started | — |

### In flight

*(nothing — both launched agents completed 2026-08-01; scope verified, only
their own doc files touched, `coded_data/` untouched, tree clean)*

---

## Next action

**Not blocked.**

1. **The remaining thirteen files**, one at a time, snapshots captured
   immediately after each. See § "Migration order" below.
   Delegable to agents now that the pattern exists (the four done are the
   worked examples: one Sheets-heavy, one Drive-files-only, one
   folders-and-sharing, one read-only).

   Watch for, in each: a `_save_drive_config` call (must be patched in tests —
   the real `drive_config.json` holds live IDs and a test that clobbers it
   breaks the coordinator's access to their own Drive) and any expensive or
   non-deterministic pure-computation step (PDF rendering, notebook JSON) that
   should be stubbed so the snapshot locks the *Drive interaction*, which is what
   the migration touches, rather than output already covered elsewhere.

2. Phases 3–9 per the plan.

### Migration order

Fifteen files remain, not the nine the plan implied — the plan's list of
eleven was hand-written and never checked against the code; a scan on
2026-08-02 found seventeen files reaching Drive directly. The list is now
derived by `tests/test_doorway_coverage.py`, so it cannot drift again.

Ordered by risk, lowest first, so that every shared helper and every part of
the doorway has been exercised before the destructive commands are touched.

| # | file | why here |
|---|---|---|
| ~~1~~ | ~~`setup_root_folder.py`~~ | done — `3d70069` |
| ~~2~~ | ~~`apply_pending.py`~~ | done — `f7bc5fa` |
| 3 | `prune_manifest.py` | First file-move, but only of already-retired sheets |
| 4 | `check_notes.py` | The only user of Google Docs — that part of the doorway is untested |
| 5 | `generate_biuniqueness_stage1_sheet.py` | Near-twin of `generate_status_sheet`; do the smaller one first |
| 6 | `sync_diagnostics_yaml.py` | First writer to a reference sheet |
| 7 | `import_planar.py` | Reads *and* writes the planar sheet — the #248 command. Do it while the pattern is fresh, not last |
| 8 | `generate_notebooks.py` | File uploads; closest sibling to `generate_reports`, already done |
| 9 | `update_sheets.py` | Appends to live annotation sheets. First real risk to Adam's data |
| 10 | `generate_status_sheet.py` | Generated dashboard; no annotation at stake |
| 11 | `validate_coding.py` | Writes highlighting across every sheet |
| 12 | `integrity_check.py` | 941 lines but a small read-only Drive section |
| 13 | `import_sheets.py` | Downloads everything; the daily refresh depends on it |
| 14 | `sync_params.py` | Column surgery — insert, rename, delete. Highest density of read-then-write on one handle |
| 15 | `generate_sheets.py` | 2644 lines, creates everything, and owns helpers four other files call. Late, so those callers are already migrated and proven |
| 16 | `restructure_sheets.py` | Archive-then-rebuild with no rollback. The #248 command. Last, deliberately |

Two departures from "smallest first" worth keeping: `import_planar.py` moves
up because it is the command whose silent revert caused #248 and it deserves
attention rather than fatigue; `generate_sheets.py` moves down because four
other files call its helpers, and migrating it last means those callers are
already locked down when it changes.

### The per-file procedure, as actually executed on file 1

Step 1 of the plan's procedure ("run the dry-run against real Drive and save
the output") is not permitted before Phase 9. The substitute, which worked
better than expected and should be reused for files 2–11:

- Drive the **unmigrated** code from a fake seeded by `from_fixtures()`, using
  thin shims for the `gc` and `drive` objects it expects (a `open_by_key` that
  returns a fake spreadsheet; a `files().update()` that records the call).
  Capture stdout and the fake's mutation log.
- Migrate. Run the same commands through the doorway against an identically
  seeded fake.
- Diff. On `refresh_dropdowns.py` both modes' stdout were byte-identical and
  the 36 mutations matched exactly, including the manifest payload's byte
  count.
- Only then capture snapshots.

This gives write paths a real before/after diff rather than review alone, which
is a stronger check than the plan assumed was available. It has held for every
file since: `generate_reports`, `setup_root_folder`, and `apply_pending` all
came back byte-identical on the first try. The shims live in the scratchpad,
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

## Findings awaiting triage

Per the plan's Phase 0b/1 non-goals, a snapshot that reveals odd behaviour records
it rather than fixing it. These are recorded, live, and not yet triaged.

**Both filed as issue #272 (2026-08-01) — do not run `refresh-dropdowns --apply`
until it is fixed.** Dry run is unaffected.

**1. `refresh-dropdowns` narrows dropdowns for every class that uses
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

**3. `apply-pending` cannot tell a wrong spreadsheet ID from a bad connection**
(found 2026-08-02, file 4, not filed). `_verify_construction_tabs` catches every
exception and returns "could not verify", so a stale or mistyped
`spreadsheet_id` — a sheet that was archived, or an entry written before the ID
was recorded — reads exactly like a network blip. Both then ask the coordinator
to confirm from memory, and a "y" closes the entry with nothing checked.

Low severity: the entry it closes is a reminder to add a tab, not data, and the
next `import-sheets` re-files it if the tab really is missing. But it is the
same shape as the two above — one answer standing in for two different
questions — and separating "Drive said no such file" from "Drive did not
answer" is a few lines. Recorded now because the snapshot that shows it
(`new_construction.txt`, fourth block) makes the two indistinguishable on the
page, which is the point.

---

## Decisions log

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
