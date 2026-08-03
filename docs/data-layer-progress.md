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

**Phase:** 0b/1 — migrating callers, 9 of 18 done (started 2026-08-01)
**Live Drive writes performed:** none. Permitted from Phase 9 only.
**Adam's annotation data touched:** none.
**Last worked:** 2026-08-02

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
rebuilding it before then produces a correctly-shaped empty tab. **#276** —
collapse the duplicated Drive helpers, blocked until every Drive-writing
command has snapshots.

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
   Delegable to agents now that the pattern exists (the nine done are the
   worked examples: Sheets-heavy, Drive-files-only, folders-and-sharing,
   read-only, Docs, sheet creation, reference-sheet overwrite, and a command
   with two directions that must round-trip).

   Watch for, in each: a `_save_drive_config` call (must be patched in tests —
   the real `drive_config.json` holds live IDs and a test that clobbers it
   breaks the coordinator's access to their own Drive) and any expensive or
   non-deterministic pure-computation step (PDF rendering, notebook JSON) that
   should be stubbed so the snapshot locks the *Drive interaction*, which is what
   the migration touches, rather than output already covered elsewhere.

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

Nine files remain of eighteen that touch Drive. The plan's list of eleven
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

**"9 of 18" flatters it, and planning should use the volume rather than the
count.** Because the order is smallest-and-safest first, the nine done are
2,557 lines between them; the nine remaining are 9,173 lines and **57 direct
Drive calls**. That is under a quarter of the phase by weight. Recompute rather
than trusting these numbers — the command is in `tests/test_doorway_coverage.py`
(`_DIRECT_ACCESS` over `coding/*.py`, minus `_EXEMPT`).

| file | why here |
|---|---|
| ~~`setup_root_folder.py`~~ | done |
| ~~`apply_pending.py`~~ | done |
| ~~`prune_manifest.py`~~ | done |
| ~~`check_notes.py`~~ | done |
| ~~`generate_biuniqueness_allomorphy_sheet.py`~~ | done |
| ~~`sync_diagnostics_yaml.py`~~ | done |
| ~~`import_planar.py`~~ | done |
| `generate_notebooks.py` | File uploads; closest sibling to `generate_reports`, already done |
| `update_sheets.py` | Appends to live annotation sheets. First real risk to Adam's data |
| `generate_status_sheet.py` | Generated dashboard; no annotation at stake |
| `validate_coding.py` | Writes highlighting across every sheet |
| `integrity_check.py` | 945 lines but a small read-only Drive section |
| `import_sheets.py` | Downloads everything; the daily refresh depends on it |
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
better than expected and should be reused for files 2–11:

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
it rather than fixing it *in the same change*. **All seven findings so far have
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

---

## Decisions log

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
