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

**Phase:** 6 — **started 2026-08-17, three of four boundaries done.** The
filled-TSV/sheet loader (`planars/io.py`'s `_parse_filled_df`), the
planar loader (`coding/make_forms.py`'s `build_element_index`), and the
coreference pair-row loader (`planars/coreference.py`) now have pandera
contracts (`planars/contracts.py`, `coding/contracts.py`); only manifest
read/write is not started. See Next action below for the full
account. 5 — done, all five units. Unit A (argparse standardization, all 9 batches) done 2026-08-16. Units B (dispatch integration) and C (derived `registry` command) done the same day, right after A: every command module now exposes `build_parser()` separately from `main(args=None)`, `__main__.py` parses once and calls `mod.main(args)` directly (the chokepoint units D/E hook into), and `python -m coding registry` derives the full command inventory fresh from that plus `operations.yaml` on every call. Units D (precondition enforcement) and E (provenance capture) done 2026-08-17, both same day, after Jeff decided both units' open questions (see the Decisions log): D replaces the scattered manual `_check_coded_data_clean()` calls, file-by-file, with `coding/preconditions.py` driven by each command's `operations.yaml` record; E logs only Drive-writing invocations (not every command, and per actual invocation not per command) to `provenance_log.jsonl`, append-forever, via `coding/provenance.py`. 4 — done. Every record traced against code, all three "done when" items complete, and all five review items closed out with Jeff (started 2026-08-10, review session 2026-08-11, line-by-line trace + fixes 2026-08-11, Findings 27/28 resolved with Jeff 2026-08-16). 3 — done (started and finished 2026-08-10). 0b/1 — done, 18 of 18 (2026-08-01–2026-08-04).
**Live Drive writes performed:** none. Permitted from Phase 9 only.
**Adam's annotation data touched:** none.
**Last worked:** 2026-08-17

Phase 3 split `schemas/diagnostic_classes.yaml` into that file (linguistic
content only) and a new `schemas/diagnostic_classes_status.yaml` (process/
tracking state: `status`, `criterion_set_status`, `collection_required`,
`qualification_rule_hash`, `sheet_instructions`, `include_planar_reference_tab`),
joined by class `name`. Scope turned out narrower than "split all of
`schemas/`": `diagnostic_criteria.yaml`, `terms.yaml`, and `languages.yaml`
were already single-purpose and needed no split; `planar.yaml`'s only
conflated field, `Class_Type`, was catalogued rather than split (splitting
its actual semantics would be a behaviour change, out of scope for this
phase's own non-goals — see Findings 18/19 below and the decisions log).
`coding/schemas.py`'s `load_diagnostic_classes()` merges both files by name
at read time, so the ~30 existing callers across `coding/` and `planars/`
needed no changes; `coding/sync_qualification_hashes.py` (the only writer of
`qualification_rule_hash`) and `coding/generate_rule_update_prompt.py` (which
read the old file directly, bypassing the merged loader, and would have
silently treated every class as stale) were the two that did.

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
**#276** — closed 2026-08-04; the four duplicated Drive helper groups
collapsed into three shared functions in `coding/drive.py`. See the decisions
log for what changed and the bonus discovery (a real, silent duplicate-grant
bug in `generate_notebooks.py`, not just `setup_root_folder.py`).
**#279** — filed 2026-08-10, open; asks Adam what construction (if any) fills
`arao1248`'s still-missing `proform` class (Finding 19/20).
**#280** — filed 2026-08-11, fixed the same day; the shared
batched-write-at-end-of-loop pattern, in the end across six commands
(Finding 22): the originally-filed four (`import_sheets.py`,
`apply_pending.py`, `prune_manifest.py`, `check_notes.py`) plus
`generate_notebooks.py`/`generate_reports.py`, found sharing the same shape
against `drive_config.json` during the same-day line-by-line review pass
(Finding 25) and folded into the same fix rather than filed separately. Each
now persists its record incrementally, once per item, instead of once after
the whole loop.

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
| Phase 0b/1 — file 15: `import_sheets.py` | **done** — pre/post diff clean across twenty-two scenarios; the command the daily `data-refresh` workflow depends on to pull annotator work down, and the largest file migrated so far (1,138 lines); found and later fixed Finding 13 (a dry run had no guard at all against a bad manifest spreadsheet ID — it crashed the whole run rather than reporting per class the way every other failure mode in this file does) |
| Phase 0b/1 — file 16: `sync_params.py` | **done** — pre/post diff clean across fifteen scenarios; the file the migration order flagged to watch (column insert/delete is the densest form of the #272 question) and it passed clean — every column position already comes from the tab's own header; found and fixed Finding 14 (adding or removing a column re-stamped the manifest's `param_values` for the *whole* construction, masking a genuinely stale dropdown on an untouched sibling criterion) |
| Phase 0b/1 — file 17: `generate_sheets.py` | **done** — pre/post diff clean across twelve scenarios; the largest file migrated so far (2,654 lines) and the first whose migration threaded `doorway` through this file's own call chain rather than substituting at a single entry point; passed `assert_no_criterion_writes_onto_trailing_columns` clean; found and later fixed Finding 15 (`--force` overwrote a language's planar/diagnostics reference sheets before the guard could abort on its existing annotation sheets) |
| Phase 0b/1 — file 18: `restructure_sheets.py` | **done** — pre/post diff clean across thirteen scenarios; the last file, deliberately: the archive-then-rebuild command with no rollback behind #248's original incidents. `assert_no_criterion_writes_onto_trailing_columns` caught a real, pre-existing bug (Finding 16, fixed the same day); also surfaced a pre-existing gap, the missing `_check_coded_data_clean()` guard (Finding 17, fixed in a later follow-up commit) |
| **Phase 0b/1 (the whole doorway migration)** | **done** — all eighteen files that reach Drive now go through it |
| Phase 3 — schema reorganization | **done** — `diagnostic_classes.yaml` split from `diagnostic_classes_status.yaml`; `Class_Type` catalogued as a resistant field on issue #271, not split (behaviour-neutral phase) |
| Phase 4 — topology declaration | **done** — `data_dependency_schema/operations.yaml` + `operation_record.schema.json`, one record per `coding/__main__.py` command (24, mechanically checked), `modes` added for the 4 commands whose behavior genuinely diverges by flag; every `idempotent` claim traced against actual code across all 24 records (not just the ones flagged 2026-08-10), corrections applied; 2 new facts added; 5 real code gaps found and fixed on the spot (Findings 23/24/26/28); 1 cross-cutting bug pattern found, filed, and fixed (#280, Finding 22, across 6 commands after Finding 25 found 2 more sharing the shape); `CLAUDE.md`'s narrative prose replaced by a pointer to the registry; all five review items closed out with Jeff 2026-08-16 (Findings 27/28). |
| Phase 5, unit A — argparse standardization | **done** — all 17 `coding/` commands that hand-scanned `sys.argv` now use `argparse` (9 batches, smallest-and-safest first, `generate_sheets.py` deliberately last — same ordering logic as the Phase 0b/1 file migration). Documented flags unchanged; the actual difference is that an unknown flag now hard-errors (exit 2) instead of being silently ignored, the specific failure mode the plan calls out for `generate-sheets`. `restructure_sheets.py`/`sync_params.py` layer argparse in front of their existing hand-rolled colon/comma parsers (`_parse_flag_map`, `_parse_renames`, etc.) rather than replacing them, since those have their own passing unit tests. One real test update: `test_no_lang_flag_is_refused` (biuniqueness/allomorphy) now checks `SystemExit` code 2 instead of stdout text, since argparse's `required=True` error goes to stderr, which that test's capture helper doesn't see — same intent (refuse to run without `--lang`), exit code changes from 1 to 2. Full pytest suite (1281 tests) green after every one of the 9 batches. |
| Phase 5, unit B — dispatch integration | **done** — every command module (all 24, including the 2 with no flags at all and the 2 with hand-rolled colon/comma parsers underneath argparse) exposes `build_parser()` separately from `main(args: argparse.Namespace \| None = None)`; `main()` parses `sys.argv` itself only when called with no `args`, so all 18 existing snapshot tests that monkeypatch `sys.argv` and call `mod.main()` kept working unchanged (one exception: `setup_root_folder`'s test never controlled `sys.argv` at all, safe before only because `main()` never parsed it — fixed to monkeypatch like every other test). `__main__.py`'s dispatch now parses once and calls `mod.main(args)` directly instead of letting each command re-parse internally — the chokepoint units D and E will hook into, keyed by command name and already-parsed `args`. |
| Phase 5, unit C — derived `registry` command | **done** — `python -m coding registry` joins `__main__.py`'s `_COMMANDS` table + every command's `build_parser()` (unit A/B) with `operations.yaml` (Phase 4), recomputed fresh on every call, nothing cached. Plain listing by default; `--command CLI_COMMAND` for one command's full detail. Replaced `__main__.py`'s own hand-maintained "Commands:" docstring table — exactly the kind of duplicated inventory this command exists to remove (ground rule 4). `operations.yaml` gained a record for `registry` itself; `tests/test_registry.py` checks flag lists against a *fresh* call to each module's own `build_parser()`, not a copy pinned in the test, so a hand-copied list couldn't pass silently. |
| Phase 5, unit D — precondition enforcement | **done** — `coding/preconditions.py`, wired into `__main__.py`'s dispatch; replaced the scattered manual `_check_coded_data_clean()` calls in all 7 files that had one, migrated one command at a time |
| Phase 5, unit E — provenance capture | **done** — `coding/provenance.py`, wired into the same dispatch chokepoint; logs Drive-writing invocations only, per actual invocation, to `provenance_log.jsonl` (append-forever); new `operations.yaml` `writes_to_drive` field populated across all 25 records (Finding 29) |
| **Phase 5 (the whole unit)** | **done** — units A/B/C/D/E all complete |
| Phase 6, boundary 1 — filled-TSV/sheet loader | **done** — `planars/contracts.py` (pandera), wired into `planars/io.py`'s `_parse_filled_df`; `tests/test_contracts.py` new, `tests/test_io.py`'s 14 error-path tests pass unchanged |
| Phase 6, boundary 2 — planar load | **done** — `coding/contracts.py` (pandera), wired into `coding/make_forms.py`'s `build_element_index`; `tests/test_coding_contracts.py` new, `tests/test_make_forms.py`'s 3 pre-existing error-path tests pass unchanged plus 6 new ones closing a pre-existing test-coverage gap |
| Phase 6, boundary 3 — pair-row load | **done** — `planars/contracts.py` section 2 (pandera), wired into `planars/coreference.py`'s `_load_planar_for_coreference`/`derive_coreference_domains`; `tests/test_coreference.py` new (no unit-test file existed for this module before), `tests/test_contracts.py` extended, all 6 pre-existing coreference snapshot tests pass unchanged |
| Phase 6, boundary 4 — manifest read/write | not started |
| Phases 7–9 | not started |

### In flight

*(nothing — both launched agents completed 2026-08-01; scope verified, only
their own doc files touched, `coded_data/` untouched, tree clean)*

---

## Next action

**Phase 0b/1 — the doorway migration itself — is complete.** All eighteen
files in `coding/` that reach Google now go through `drive_doorway`; none
reaches `gspread`/`googleapiclient` directly (`tests/test_doorway_coverage.py`
verifies this, with an empty `_REMAINING`). No file remains to migrate — there
is no next *file*.

**Phase 3 ("Schema reorganization") is done — see Current state above.**
Jeff made the calls the plan marked "(coordinator decides)": the split
mechanism (two parallel files, joined by class `name`, over the alternatives
of one file with two top-level keys or a field-rate registry with no
physical split) and the bucket for three borderline fields
(`criterion_set_status`, `qualification_rule_hash`, `sheet_instructions` — all
administrative). Every Phase 1 snapshot passed byte-identical, confirmed by
`generate_snapshots.py` producing a zero-diff run against the pre-split
baseline (the split touches no field any analysis module reads); the one
snapshot that *did* change (`tests/snapshots/coordinator/integrity_check/sheets_arao1248.txt`)
reflects an intentional file-name wording fix, not a behaviour change.

**Phase 4 ("Topology declaration") is drafted, traced against code end to
end, and has had a real, substantial interactive review pass with Jeff —
still awaiting his final read-through of the diff, not a re-review from
scratch (see the two entries below this one for what happened after the
interactive session).** Jeff's instruction was "I draft, you review": Claude
drafts, he checks the two things the plan calls out specifically.
`data_dependency_schema/
operations.yaml` (+ `operation_record.schema.json`) has one record per
`coding/__main__.py` command (24 total, mechanically checked against
`_COMMANDS` by `test_every_coding_command_has_an_operation_record`), each
covering side effects, an `idempotent` claim with a required
`idempotency_note`, which `preconditions.yaml`/`facts.yaml` entries it
touches and how, what it triggers downstream, and plain-language ordering
constraints relative to other commands — the CLAUDE.md-narrative knowledge
(`--regen-construction` bypassing `--apply`; `--split-element` before
`--regen-construction`; `prune-manifest` for retirement but never rename) is
now in `ordering_constraints` rather than only in prose.

**What the 2026-08-11 review session actually did, working through it
question by question rather than a single "approved" pass:**
- **Mode scoping.** Jeff picked a `modes` field (self-contained overrides,
  not merged with the parent record) over flattening or splitting into
  separate records, after being talked out of Claude's first ("keep it
  flat") recommendation — that recommendation would have made
  `coded_data_clean_tree`-only-applies-to-`--regen-dependents` unenforceable
  by Phase 5, since a caveat in prose isn't structured data. Applied to the
  4 commands whose behavior genuinely diverges by flag: `generate-sheets`,
  `import-planar`, `sync-diagnostics-yaml`, `sync-params`.
- **Idempotency, redefined and re-checked.** Adopted retry-safety ("safe to
  re-run after a failure, given nothing else changed") as the operational
  definition, replacing an inconsistently-applied notion of pure output
  determinism. Re-passed all four flagged records against actual code
  (not just the descriptions): `sync-params` flipped `false` → `true`
  (its Sheet edits are diff-driven from the tab's real header, so a retry
  is safe); `import-sheets`/`prune-manifest`/`apply-pending` stayed `false`
  but with concrete, code-traced mechanisms replacing the earlier hedged
  notes. This tracing is what surfaced Findings 22–24 below.
- **A factual correction.** `import_sheets.py` does **not** auto-commit
  `coded_data/` — only `import_planar.py` and `restructure_sheets.py` call
  `drive._autocommit_data()`. An earlier version of the `operations.yaml`
  record claimed otherwise; corrected once traced.
- **Two new facts added to `facts.yaml`**, both grounded in real evidence
  (an existing Finding or an existing parallel fact), not speculative:
  `construction_criterion_columns` (found reviewing `sync-params` — its base
  behavior didn't match any registered fact, since `manifest_dropdown_values`
  is about criterion *values* not column *existence*) and
  `collaborator_notes_surfaced_state` (parallel in shape to the
  already-registered `sheet_change_notification_state`).
- **Findings 22–24** (batched-write pattern → #280, now fixed; `prune-manifest`
  and `sync-diagnostics-yaml` both missing `coded_data_clean_tree` — both
  fixed on the spot, see their own entries).

**2026-08-11, same day: the line-by-line pass over all 24 records, and what
it turned up.** Three general-purpose agents each traced a batch of the
records not yet given a deep code-trace on 2026-08-11's interactive session
(`sync_params`, `import_sheets`, `prune_manifest`, `apply_pending`,
`check_notes`, `sync_diagnostics_yaml`, and `generate_sheets` already had
one) against the actual `coding/*.py` source, reporting per-record either
"confirmed clean" or a specific field/claim mismatch with file:line evidence.
11 of 17 came back clean; the rest are Finding 25 (below) — mostly stale
`operations.yaml`/`facts.yaml` claims, plus a real data-loss bug (Finding 26)
and a duplicated-vs-deliberate pair-row-detection question resolved with
Jeff on 2026-08-16 (Finding 27). Jeff decided, mid-pass, to fix issue #280
(Finding 22) and the Finding 26 bug immediately rather than leave them
documented-only. See Findings 25–28 below for the full account of what was
found and fixed.

**`CLAUDE.md`'s narrative topology prose replaced by a pointer** — the
plan's third "done when" item. The "Retiring a class"/"Renaming a class"
paragraphs under Work phases, which duplicated `prune_manifest`'s and
`restructure_sheets`'s `ordering_constraints` verbatim, are now one sentence
pointing at `operations.yaml`; the `sync-params` ordering line under the
diagnostics YAML section got a pointer added rather than a full replacement,
since it was one clause, not a restated sequence. Architecture/behavior
descriptions (what a command does, side effects) were deliberately left
alone — not the "topology" the plan means, and CLAUDE.md's own
documentation-maintenance rule wants that context kept.

All three of the plan's "done when" items are complete: every command has a
record (already true), the coverage test still passes, and the narrative
pointer replacement above. The plan is explicit that authority assignments
and idempotency claims are the coordinator's call, not Claude's to assert
unilaterally — reviewed directly with Jeff 2026-08-16 rather than via a
separate line-by-line diff read, on the basis that the underlying
trace-through was already covered by the test suite (see Findings 27/28,
the two items that turned into real follow-up work rather than a plain
confirmation). **Phase 4 is done. Nothing is blocked or waiting on it.**

**Phase 5, unit A ("Standardize on argparse everywhere") is done, all 17
files.** Batches, in order: A1 `capture_drive_state.py`/`generate_reports.py`/
`glottolog.py`; A2 `validation_report.py`/`update_sheets.py`/
`validate_coding.py`; A3 `sync_diagnostics_yaml.py`/`generate_notebooks.py`/
`check_notes.py`; A4 `apply_pending.py`/`prune_manifest.py`; A5
`generate_biuniqueness_allomorphy_sheet.py`/`generate_status_sheet.py`; A6
`refresh_dropdowns.py`/`import_sheets.py`; A7 `restructure_sheets.py`; A8
`sync_params.py`; A9 `generate_sheets.py`. Each batch committed and pushed
separately with the full pytest suite green; see `git log --oneline --grep
'Phase 5 batch'` for the individual commits (this progress-doc update lands
as its own commit after all nine, not one per batch — a deviation from the
usual same-commit rule, noted here rather than silently).

Two files kept their existing hand-rolled parsers underneath a thin argparse
gate instead of a full rewrite: `restructure_sheets.py` (`_parse_flag_map`/
`_parse_split_flag_map`, covering `--rename-map`/`--rename-element`/
`--rename-class`/`--split-element`) and `sync_params.py` (`_parse_renames`/
`_parse_splits`/`_parse_merges`, covering `--rename`/`--split`/`--merge`) —
both have their own dedicated unit tests
(`tests/test_restructure.py`/`tests/test_sync_params.py`) for colon/comma
syntax and error messages that a reimplementation would have had to prove
equivalent for no behavioral gain. argparse declares the same flags so
`--help` and unknown-flag detection work; the proven parsers still do the
real parsing from `sys.argv`.

`generate_sheets.py`'s `--pos-remap old:new` integer-pair parsing (previously
the one hand-rolled loop with no separate unit test) was converted directly
to argparse's `action="append"`, verified against
`test_regen_coreference_with_pos_remap_transcript`. Its bottom-of-file `if
__name__ == "__main__":` guard (direct-script invocation, not the documented
`python -m coding` path) was left untouched — it never reaches `main()`'s
argparse instance, out of scope for this unit.

**Phase 5, units B and C are done, same day as unit A.** B: every command
module (all 24 — including the 2 with no flags at all, `check_codebook.py`/
`setup_root_folder.py`, and the 2 with hand-rolled colon/comma parsers,
`restructure_sheets.py`/`sync_params.py`) now exposes `build_parser()`
separately from `main(args: argparse.Namespace | None = None)`; `main()`
parses `sys.argv` itself only when called with no `args`, preserving every
existing test's `monkeypatch.setattr("sys.argv", ...); mod.main()` pattern
unchanged (one real fix needed: `setup_root_folder`'s test never controlled
`sys.argv` at all — safe before only because `main()` never parsed it, since
the command took no flags — now fixed to monkeypatch like every other
snapshot test). `__main__.py`'s dispatch no longer calls `mod.main()` and
lets it re-parse internally; it builds the parser, parses once, and calls
`mod.main(args)` directly — the chokepoint units D and E hook into, keyed by
command name and already-parsed `args`. `restructure_sheets.py`/
`sync_params.py` keep their proven `sys.argv`-reading helpers underneath
`build_parser()` unchanged, same division of labor unit A established.

C: `python -m coding registry` joins `_COMMANDS` + every command's
`build_parser()` with its `operations.yaml` record, recomputed fresh on
every call — nothing cached, so it cannot go stale the way the plan warns a
hand-authored registry would. Plain listing by default; `--command
CLI_COMMAND` for one command's full detail (flags, side effects,
idempotency, preconditions, ordering, modes). `__main__.py`'s own
hand-maintained "Commands:" docstring table — the exact kind of duplicated
inventory this command exists to remove — is replaced by a pointer to it.
`operations.yaml` gained a `registry` record for itself (read-only,
idempotent, no preconditions); the two `test_data_dependency_schema.py`
tests that enumerate commands were updated to include it.
`tests/test_registry.py` checks a handful of known commands' flag lists
against a *fresh, independent* call to that module's own `build_parser()`
(not a copy pinned in the test), so a hand-copied flag list couldn't pass
silently. Full pytest suite (1291 tests, +10 new) green.

**Phase 5, unit D ("Precondition enforcement") is done, 2026-08-17.** Jeff's
decision on the unit D open question: replace, file-by-file, with the same
pre/post-diff discipline Phase 0b/1 used — not add a second layer, and not
one sweep. `coding/preconditions.py` (`active_preconditions(op_id, args)`/
`enforce(op_id, args)`) derives which preconditions apply to a real
invocation straight from that command's `operations.yaml` record (base
`apply_gate` plus any active `modes`), so a declared-but-unchecked
precondition — the exact shape Findings 23/24 already found twice — is no
longer possible; the declaration IS what runs. Wired into `__main__.py`'s
dispatch right after parsing, before `mod.main(args)`. Only
`coded_data_clean_tree` is centrally enforced (the one precondition that was
actually a scattered manual `_check_coded_data_clean()` call per file);
`coded_data_git_identity_configured` and `check_notes_documents_scope_authorized`
stay enforced where they already were — neither was that shape, so
centralizing them would be a different, un-scoped change (see
`preconditions.py`'s module docstring). Migrated one command at a time —
`sync_diagnostics_yaml.py` first (the one extensions exception, a good early
check), then `update_sheets.py`, `prune_manifest.py`, `sync_params.py`,
`import_sheets.py`, `generate_sheets.py`, `restructure_sheets.py` last
(deliberately — the archive-then-rebuild command with no rollback, same
ordering logic Phase 0b/1 used) — each its own commit, full pytest suite run
after every one. Each command's own snapshot tests lost the guard-specific
assertions they used to carry (a monkeypatched `_check_coded_data_clean` and
one or two dry-run-vs-apply tests per file) since the guard no longer lives
in that file at all; that coverage now lives once, in
`tests/test_preconditions.py`, checked against the real, live
`operations.yaml` rather than duplicated per command. `coding/gating.py`
factors the `apply_gate`-matching logic out for reuse by unit E. Full pytest
suite green after every commit (1306 by the end of unit D).

**Phase 5, unit E ("Provenance capture") is done, 2026-08-17, same day as
unit D.** Jeff's decisions on the unit E open questions: log only commands
with real Drive side effects (not every command), and log per actual
invocation rather than per command — scoping unit E turned up that
Drive-write status genuinely diverges by mode for `sync-diagnostics-yaml`
and `import-planar` (their default directions touch only the local
YAML/TSV; only `--to-sheet` reaches the live Sheet), so "does *this* run's
flags actually hit Drive" is the only version that doesn't either under- or
over-log those two. Retention: append-forever. `coding/provenance.py`
(`writes_to_drive(op_id, args)`/`record(cli_command, op_id, args)`) is wired
into `__main__.py`'s dispatch right before `mod.main(args)` runs (not after
— a run that fails partway through can still have written something), and
appends one JSON line (`{timestamp, command, args}`) to
`provenance_log.jsonl` at the repo root (gitignored) whenever the actual
invocation reaches a Drive/Sheets/Docs write. Required a new
`operations.yaml` field, `writes_to_drive` (base + per-mode, schema change
in `operation_record.schema.json`, documented in `SCHEMA.md`), populated
across all 25 records by tracing each command's real Drive footprint rather
than assuming `apply_gate` always means "writes to Drive" — see Finding 29
below for what that tracing turned up. Full pytest suite green (1322 tests).

**Both units needed a decision from Jeff before they could start; neither
does anymore. Phase 5 is done in full** — units A/B/C/D/E all complete.

**Phase 6 ("Data contracts at boundaries") started 2026-08-17, first
boundary done.** The plan names four candidate boundaries and already
assigns tooling by data shape — pandera for the three DataFrame boundaries
(planar load, filled-TSV/sheet load, pair-row load), pydantic for the one
dict/JSON boundary (manifest read/write) — but says not to attempt full
coverage in one pass, so which boundary to start with was an open scoping
question. Jeff picked the filled-TSV/sheet loader
(`planars/io.py`'s `_parse_filled_df`, shared by `load_filled_tsv` and
`load_filled_sheet`): highest reuse (all fifteen `planars/*.py` analysis
modules that read a filled sheet go through it), and it already did the
checking by hand — a pandera schema formalizes what was there rather than
adding new checking. Known and accepted going in: this loader is imported
directly by Colab notebooks, so `pandera` becomes a Colab runtime
dependency, not just a local one — added to `pyproject.toml`'s
`dependencies` (governs the Colab install) as well as `requirements.in`.

New `planars/contracts.py`: `raw_shape_schema(required_criteria)` (Position_Name
<-> Position_Number 1-to-1, exactly one keystone row — applied post-
normalization, pre-keystone-split) and `strict_criteria_schema(required_criteria)`
(every required criterion non-blank in every non-keystone row — applied to
`data_df` post-split, only when the caller asked for `strict=True`). Column
*presence* and blank-`Position_Number` detection stayed as plain checks in
`_parse_filled_df` itself, ahead of both schemas — the normalization step
that produces the columns the schemas check has to run first, so validating
presence via a schema built from columns that might not exist yet would be
circular. Both schemas raise `pandera.errors.SchemaError`/`SchemaErrors`;
`_parse_filled_df` catches that and re-raises `ValueError` with the same
level of diagnostic detail the old hand-written messages had (which specific
`Position_Name`s/`Position_Number`s collided, which row indices had a blank
required criterion), so every one of the fifteen callers keeps seeing the
exception type — and the same message content — it always has. All fourteen
pre-existing `tests/test_io.py` error-path tests pass unchanged against the
new implementation; `tests/test_contracts.py` (new) tests the two schemas
directly, including a regression test for a late-binding closure bug caught
before commit (a naive dict comprehension building one `Check` lambda per
required criterion would have every lambda close over the same loop
variable, so every column's blank-check would report the *last* criterion's
name regardless of which one was actually blank — fixed with a factory
function per column instead). Full pytest suite green (1322 tests) after a
real bug this rewrite introduced and the same run caught: `keystone_pos`
briefly leaked a numpy `int64` instead of a plain `int` (Finding 30) — fixed
same session, before commit.

**Phase 6, boundary 2 ("planar load") done, same session.**
`coding/make_forms.py`'s `build_element_index` — the function every sheet-
generation and structural-maintenance command (`generate_sheets.py`,
`update_sheets.py`, `restructure_sheets.py`) depends on to know what
elements exist at what positions — gets its own `coding/contracts.py`
(deliberately not `planars/contracts.py`: `build_element_index` is
coordinator tooling only, nothing the Colab-installed `planars` package
imports, so this boundary doesn't add a Colab runtime dependency the way
boundary 1 did). No open scoping question here — the plan already named
this the second candidate boundary and pandera as the right tool for a
DataFrame boundary, so this one proceeded straight to implementation.

`position_integer_schema()` and `class_type_schema()` cover the same two
checks the original hand-written loop raised on (`Position` castable to
`int`; `Class_Type` one of `open`/`list`/`mixed`), applied to the same
two narrowed row subsets the original loop's `continue` statements
produced (matching-language + non-blank-`Position` for the first check,
further narrowed to non-blank-`Elements` for the second) — refactored so
both the schema check and the indexing loop that follows read off one
shared, normalized DataFrame instead of each re-deriving the same
strip/lower logic separately and risking drift between them. The
duplicate-`element@position`-key check stays procedural in
`make_forms.py`, not moved into the schema, since it depends on per-row
multi-element splitting (`_split_elements`) that doesn't fit a per-column
check. Same wrapping pattern as boundary 1: `SchemaError` caught, `ValueError`
re-raised with the original message wording, so all three callers see the
exception type and message shape they always have.

Found while adding tests, not a code bug: `build_element_index` had exactly
three tests before this (the `open`/`list`/`mixed` indexing parity check,
a single-item list check, and the unexpected-`Class_Type` error path) —
missing-column, non-integer-`Position`, and duplicate-key were all
real, working `ValueError` paths with no test ever exercising them. Six
new tests close that gap (including one confirming a different-language
row's garbage `Class_Type` is correctly ignored, not raised on). All
pre-existing `tests/test_make_forms.py` tests pass unchanged;
`tests/test_coding_contracts.py` (new) tests the two schemas directly.

**Phase 6, boundary 3 ("pair-row load") done, same session — Jeff's call to
do it despite a flagged thin payoff.** `planars/coreference.py`'s pair-row
loader is a genuinely weaker fit than boundaries 1–2: the module
deliberately treats most bad *values* (an unrecognized element, an
unparseable `Position_B`) as warnings collected into `missing_data`, only
raised at all when the caller passes `strict=True` — so there wasn't much
existing hand-written validation to formalize the way boundaries 1–2 had.
Real value turned out to be different in kind, not absent: both
`_load_planar_for_coreference` and `derive_coreference_domains` read
required columns via `row.get(col, "")` with a silent `""` fallback, so a
genuinely missing column doesn't crash — it quietly makes every row look
"unknown" and, unless `strict=True`, produces a wrong-but-plausible-looking
*empty* result instead of an error. Exactly the class of failure Phase 6's
own "done when" language calls out ("would have turned the phrasal_accent
failure into a clear error"), just found on a smaller boundary than
expected.

Column presence for both the planar TSV and the pair TSV is now checked
explicitly (plain checks, not pandera — same reasoning as boundaries 1–2:
the checks that follow need the columns to exist first). One real pandera
schema added, `coreference_planar_rows_schema()` in `planars/contracts.py`
(section 2, appended to the same file as boundary 1's section 1 rather
than a new file, since both are `planars/`-package DataFrame boundaries):
`Position` castable to `int` (previously an unguarded `int(...)` call
raising a raw, unclear `ValueError`) and a keystone row exists (already had
a clear message; now schema-backed). All 6 existing coreference snapshot
tests pass unchanged. No dedicated unit-test file existed for this module
at all before today — `tests/test_coreference.py` (new) covers the error
paths now added plus the pre-existing "no keystone" and "other-language
rows ignored" behaviour, none of which had a test before.

Boundary 4 (manifest read/write) is not started — the one boundary the
plan assigns to pydantic rather than pandera (dict/JSON, not a DataFrame).
No scoping question open there either, the plan already made that call.
Phases 7–9 remain entirely unscoped; see
`docs/data-layer-implementation-plan.md`.

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

All eighteen files that touch Drive are migrated; none remain. The plan's
list of eleven was hand-written and never checked against the code; a scan on
2026-08-02 replaced it with a derived one in `tests/test_doorway_coverage.py`,
which now asserts `_REMAINING` is empty.

That scan was reported as "seventeen", and this file repeated it for two days
before the arithmetic gave it away: seven migrated plus eleven remaining is
eighteen, not seventeen. A hand-copied count of a derived number, going stale
exactly as the derived list would have — the same defect one level up. The
counts above are checked against the code by `test_stated_counts_match_the_code`,
and the per-file rows below no longer carry a total at all.

The files were migrated in order of risk, lowest first, so that every shared
helper and every part of the doorway had been exercised before the destructive
commands were touched. The last one, `restructure_sheets.py` (1,425 lines, 10
direct Drive calls), was deliberately saved for last: the archive-then-rebuild
command with no rollback, behind #248's original incidents. By the time it was
migrated the eighteen files together totalled roughly 11,900 lines —
`generate_sheets.py` alone was 2,651 post-migration, larger than the combined
remaining weight this doc quoted for any prior file. Recompute rather than
trusting these numbers if picking this back up later — the command is in
`tests/test_doorway_coverage.py` (`_DIRECT_ACCESS` over `coding/*.py`, minus
`_EXEMPT`).

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
| ~~`sync_params.py`~~ | done |
| ~~`generate_sheets.py`~~ | done |
| ~~`restructure_sheets.py`~~ | done |

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
it rather than fixing it *in the same change*. **Findings 1–12, 14, and 16 have
all since been fixed** — the deferral only ever lasts until the migration each
one is riding on has been committed and its before/after comparison taken.
Findings 13, 15, and 17 are the exceptions still outstanding: each is recorded
as current behaviour, accepted rather than deferred-then-fixed, pending a
coordinator decision named in its own entry on whether it warrants a fix at
all (17 is mechanical rather than a judgment call, but adding a new abort path
is a behaviour change outside a call-site migration's scope, so it is left for
a deliberate change of its own rather than folded into this one). Nothing else
here is outstanding; the entries are kept because the sequence is the point.

**Do not delete this section when the migration ends without first checking that
every finding has an issue number or a decisions-log entry.** Findings 4 and 5
lived here alone for a day each, and a section that gets deleted is not tracking.

**18–24 — found 2026-08-10/11. 18 and 19 while splitting
`diagnostic_classes.yaml` for Phase 3; 20–21 while acting on what 19
surfaced; 22–24 while drafting and interactively reviewing the Phase 4
operation registry with Jeff (`data_dependency_schema/operations.yaml`). All
pre-existing, not introduced by any of this work. 22 is still open (filed as
#280); the rest were each fixed the same day, in their own commit.**

**18 — fixed, `40ba95a`.** `nonpermutability` carried `keystone_active_default:
true` twice in `schemas/diagnostic_classes.yaml` (now
`diagnostic_classes_status.yaml`'s sibling record, but the duplicate itself
predates the split). Both occurrences agreed (`true`), so PyYAML's
last-value-wins behaviour made this harmless, but a future edit to only one
copy would have silently done nothing. Caught by the split script's own
field-inventory check (it counts occurrences per class), not by any existing
test. Deleted the earlier occurrence.

**19 — fixed.** `validate_diagnostics.py`'s required-class check had never
matched anything. `_required_classes()` (`coding/validate_diagnostics.py:128`)
read `collection_required` and tested `is True` — a Python bool identity
check — but the field's actual values are the strings
`"y"`/`"n"`/`"[NEEDS COORDINATOR INPUT]"` throughout
`diagnostic_classes_status.yaml`, never the YAML booleans `true`/`false`.
`"y" is True` is always `False`, so this function had always returned an
empty set and the required-class check it feeds had never flagged a missing
required class. Fixed by comparing against `"y"` instead.

Fixing it surfaced a real, previously-invisible gap: **`arao1248` is
genuinely missing three `collection_required: "y"` classes** —
`nonpermutability`, `free_occurrence`, `proform` — consistent with its
in-progress onboarding status (only `ciscategorial`, `noninterruption`,
`subspanrepetition` are annotated so far, per `CLAUDE.md`'s "In-progress
annotation work"). This now shows up live: `integrity-check`'s error count
went from 3 (pre-existing synth0001 coreference staleness) to 6;
`import-sheets` and `sync-diagnostics-yaml --to-sheet` both skip processing
arao1248's diagnostics entirely until it's resolved (their own validation
gate, unrelated to this fix — they were always going to skip on any
error, they just had nothing to skip on before); `generate-sheets` reports
it but doesn't block sheet creation. The next `data-refresh.yml` run will
likely fold this into already-open issue #247 (`integrity-error`) rather
than file a new one.

23 test fixtures needed updating to match: five broke because the shared
`_valid_data()` helper in `tests/test_validate_diagnostics_yaml.py` declared
only `ciscategorial` and needed all six required classes to stay genuinely
valid; eleven coordinator-facing snapshots gained the arao1248 error lines
for real (regenerated via `PLANARS_UPDATE_SNAPSHOTS=1`, each diff reviewed —
see `git log --oneline --grep 'Finding 19'`); the rest were assertions like
`"ERROR" not in out` written when the check was dormant, now updated to
check for the *specific* error each test is about rather than the absence of
any error at all (arao1248 always has one now, for an unrelated reason).
Nothing here required touching `tests/fixtures/drive_state/` — the arao1248
diagnostics content driving these tests comes from the real, checked-out
`coded_data/arao1248/lang_setup/diagnostics_arao1248.yaml`, not a recorded
Drive fixture.

**Follow-up, same day: two of arao1248's three missing classes are now
onboarded** (`nonpermutability`, `free_occurrence` — both universal with
fixed, language-independent criteria, so drafting their YAML entries needed
no linguistic judgment call). `proform` is still open — it's
construction-specific and nothing in the repo says what construction fills
it for Araona — filed as issue #279, addressed to Adam. Doing this onboarding
surfaced two more findings, 20 and 21 below.

**20 — fixed.** Jeff wanted the two ready classes applied without waiting on
`proform` (#279), with `proform`'s absence still surfacing on its own rather
than being silently dropped. But `sync-diagnostics-yaml`'s required-class
check (the one Finding 19 fixed) treated *any* validation error, including
"required class missing," as fully blocking — `_sync_to_tsv` refused to
regenerate `diagnostics_arao1248.tsv` at all while `proform` was absent, even
though `nonpermutability` and `free_occurrence` were already valid. Fixed by
adding a `blocking: bool = True` field to `ValidationIssue`
(`coding/validate.py`) and setting it `False` on the required-class-missing
issue in `validate_diagnostics_yaml` (`coding/validate_diagnostics.py`) —
still printed as `[ERROR]`, still counted by `integrity-check` (unaffected;
it calls the separate `validate_diagnostics_df` path, whose own required-class
check was intentionally left fully blocking), still blocks
`sync-diagnostics-yaml --to-sheet` and `import-sheets` (also untouched, since
pushing a still-incomplete language to the live Sheet or importing over it is
a different call than regenerating a local file) — only `_sync_to_tsv`'s gate
changed. `integrity-check` continues to report `proform` missing and the
daily `data-refresh.yml` run will fold it into the usual `integrity-error`
issue, which is the "come up in the daily check" Jeff asked for; issue #279
is the more specific, Adam-addressed version of the same fact.

**21 — fixed.** Applying arao1248's two new classes exposed a real,
pre-existing bug in `generate_sheets.py --apply`, unrelated to the required-
class check: the scan for constructions added to an *already-existing*
class's diagnostics YAML entry only ran inside the `if not new_class_names`
branch — so on any run where the language also had a class with no sheet at
all (exactly arao1248's situation once `nonpermutability`/`free_occurrence`
needed creating), an unrelated new construction on an existing class
(`subspanrepetition` gaining a construction, in the test that caught this)
was silently skipped instead of getting its tab added. The dry-run path
(`_plan_language_creation`) already computed `new_classes` and
`new_constructions` independently and was never affected — only the `--apply`
execution path shared the two under one conditional. Fixed by running the
existing-class scan unconditionally over every already-existing class, before
deciding whether there's also brand-new-class work to do. See
`coding/CLAUDE.md`'s `generate_sheets.py` entry for the mechanics.

**22 — fixed, filed and closed as #280.** Reviewing each command's
`idempotent` claim for `operations.yaml` surfaced a shared bug pattern across
four commands: `import_sheets.py`, `apply_pending.py`, `prune_manifest.py`,
and `check_notes.py` each accumulate "what's been done" in memory across a
loop over multiple items, then write the persistent record of it
(respectively: `pending_changes.json`, `pending_changes.json` again, the
Drive manifest, `notes_state.json`) exactly once, *after* the loop finishes —
while the real, external side effects inside that loop (writing a TSV,
running a pending entry's command, archiving a TSV and moving a Drive sheet,
filing/commenting on a GitHub issue and appending a doc acknowledgment)
happen incrementally, per item. A crash between "the real side effect
already happened" and "the loop finishes and the record gets saved" meant a
retry either silently lost that item's record (`import-sheets`) or repeated
the real side effect a second time (`apply-pending`'s command re-run;
`prune-manifest`'s Drive-sheet re-move, probably harmless but unverified;
`check-notes`' duplicate issue comment and doc acknowledgment). Fixed
2026-08-11, same day as filing: each command now persists its record right
after each item instead of once at the end. `generate_notebooks.py`/
`generate_reports.py` turned out to share the same shape against
`drive_config.json` (found by Finding 25's line-by-line pass) and were fixed
the same way, folded into this issue rather than filed separately. Each
command's own `idempotency_note` in `operations.yaml` records the exact
mechanism and now reads `idempotent: true`.

**23 — fixed.** `prune_manifest.py --apply` writes to `coded_data/` (archives
local TSVs out of it) but never called `drive._check_coded_data_clean()`
first — the same gap Finding 17 named for `restructure_sheets.py`, found the
same way (filling in `operations.yaml`'s `preconditions` field) but *not*
deferred the way Finding 17 was: that deferral was specific to the doorway
migration's call-site-substitution-only commit discipline, which doesn't
apply here, so this one was fixed on sight instead. Registered in
`preconditions.yaml`'s `coded_data_clean_tree` `required_by`; two new tests
(`test_apply_checks_coded_data_is_clean_before_archiving` and its dry-run
counterpart) confirm the guard fires.

**24 — fixed.** `sync_diagnostics_yaml.py --apply` reads
`coded_data/*.yaml` as ground truth for all three of its directions (default,
`--to-sheet`, `--from-tsv`) and writes `coded_data/` TSV/YAML for two of
them, with the same gap as 23 — found the same day, immediately after. Risk
shape differs from 23: this isn't about acting on a stale *target* file, it's
about propagating a stale/reverted *source* (the YAML) forward — `--to-sheet`
would push it live, the default direction would regenerate the TSV from it.
Fixed the same way, `extensions=(".yaml", ".tsv")` since this command reads
and writes both file types (every other guarded command is TSV-only).
Registered in `preconditions.yaml` and all three of the command's
`operations.yaml` records (base + two mode overrides); two new tests added,
scoped to `--to-sheet` only since this test file's fixture reads the real
`coded_data/` directly rather than a redirected copy.

**25 — fixed (documentation).** A line-by-line pass over all 24
`operations.yaml` records, 2026-08-11, same day as the interactive review
session above: three agents each traced a batch of the records not yet
given a deep code-trace, reporting per-record either "confirmed clean" or a
specific field/claim mismatch with file:line evidence. 11 of 17 came back
clean; the rest were stale claims, none a live-data risk on their own, all
fixed the same day: `restructure_sheets`'s `ordering_constraints` still
called the missing `coded_data_clean_tree` guard "still open" — Finding 17
was fixed 2026-08-04, six days before `operations.yaml` was even drafted,
and the record even contradicted its own `preconditions` field, which
already listed `coded_data_clean_tree`; `facts.yaml`'s `planar_sheet_structure`
cascade mechanism made the same overstatement, that `restructure-sheets`
"edits `planar_tsv` directly" — grepped every `to_csv` call in the file,
none targets a planar path, it only reads `planar_tsv` and pushes it,
corrected in both places. Also fixed: `restructure_sheets`'s missing
`revalidate_sheets()` cascade entry; `capture_drive_state`'s
"byte-identical" claim (ignored `index.json`'s timestamp); `lookup_lang`'s
idempotency note overstating what a cache hit does (zero writes, not a
re-fetch); `setup_root_folder`'s "zero Drive calls" (should read "zero
*write* calls" — reads still fire); `update_sheets`'s `facts_touched`
claiming it reads `pair_row_construction_set` (it derives pair-row status
from the tab's own header instead — see Finding 27) and claiming it writes
`manifest_class_registration` (it only ever extends an already-registered
class, never registers a new one); `integrity_check` missing a
`pair_row_construction_set` note (see Finding 27); `generate_notebooks`/
`generate_reports` missing a `languages_metadata` fact-touch (both read
`schemas/languages.yaml` for display names).

**26 — fixed.** `generate_biuniqueness_allomorphy_sheet.py --apply` wiped
`has_allomorphs`/`Members`/`Notes` unconditionally on every re-run
(`ws.clear()` before rewrite) while `operations.yaml` described this as a
benign "recomputes fresh, same content" idempotent operation — found by
Finding 25's pass. Low current risk (`synth0001`-only per its own
docstring), but the sheet is shared as *writer* with Adam and issue #254
plans to expand it beyond `synth0001`. Fixed by reading the tab's existing
`has_allomorphs`/`Members`/`Notes` before clearing (`_existing_annotations()`)
and carrying them back in by `(Position_Name, Element)`
(`_rows_to_sheet_values()`'s new `existing` parameter) — only elements no
longer in scope lose their annotation now, the same carry-over principle
`restructure_sheets.py` already uses elsewhere. New regression test:
`test_a_rerun_preserves_existing_annotations` in
`tests/test_biuniqueness_allomorphy_snapshot.py`.

**27 — resolved, one fixed one left as-is.** Finding 25 turned up two
readers deriving pair-row status independently instead of calling the
shared `restructure_sheets._get_pair_row_constructions()` helper. Reviewed
with Jeff 2026-08-16, and the two turned out to be different in kind, not
the same finding twice: `integrity_check.py`'s `_section_sheets` duplicated
the *same* source (`diagnostic_classes.yaml`'s `row_type`) via its own local
loop — pure DRY risk, no live-data stakes either way (read-only report), so
it now calls the shared helper directly. `update_sheets.py` reads a
*different* source on purpose: the tab's own live header
(`"Element_A" in header`), not the schema. That's deliberate, not a bug —
this command is about to WRITE to a tab, and the header says what's
actually there right now, while the schema says what a construction is
eventually supposed to look like; the two can disagree (`phrasal_accent`/
`general` on `stan1293` is a live example, still element-row-shaped though
its schema says `pair_rows`), and trusting the header is the safer choice
for a command whose job is not corrupting an already-existing tab. Left the
code as-is, added an explanatory comment at `coding/update_sheets.py:428`
so a future reader doesn't mistake it for the #275 bug pattern and "fix" it
into an actual regression.

**28 — fixed.** `collaborator_notes_surfaced_state`'s second drift risk
(facts.yaml), independent of #280 and left unfixed when #280 was: `check_notes.py`'s
`_get_open_notes_issue` found an annotator's already-open issue by a title
substring match only, so a manually-renamed issue silently stopped being
found even while still open, and the next run opened a duplicate thread
rather than continuing the existing one. Fixed 2026-08-16, same session as
Finding 27: the issue number is now stored in `notes_state.json`'s new
`_annotator_issues[annotator]` map (mirroring `notify.py`'s
`ensure_notification_issue` pattern for `sheets_manifest.json`'s
`notification_issue`, though not identical — see below) and preferred over
the title search, which remains only as a one-time fallback for an issue
filed before this tracking existed, backfilling the ID once found so the
fallback is never needed twice for the same annotator. Saved incrementally,
same as the rest of #280's fix, so a crash right after creating/finding the
issue doesn't lose the ID.

Deliberately NOT a straight copy of `notify.py`'s pattern: that helper
reuses a stored issue regardless of open/closed state, because a
notification thread is meant to live forever. A collaborator-notes issue is
different — closing it is how a coordinator marks a batch of notes as
triaged (see `CLAUDE.md`'s `collaborator-notes` label), so new content
after that closing should start a fresh issue, not reopen an
already-handled one. The fix checks the stored ID's open/closed state
before reusing it and drops it if closed, rather than reusing
unconditionally. New tests in `tests/test_check_notes_snapshot.py`:
`test_a_renamed_but_still_open_issue_is_still_found`,
`test_a_closed_issue_is_not_reused`,
`test_an_open_issue_predating_id_tracking_is_found_by_title_and_backfilled`.
The test fixture's `gh` stand-in had to be corrected alongside this — its
`view` subcommand wasn't stubbed at all before, so every existing test was
accidentally passing via the title-search fallback without ever exercising
the stored-ID path.

**Phase 4 is now fully closed.** All five items Jeff was asked to check
(idempotency flips, the `restructure-sheets`/`planar_tsv` correction, the
pair-row-detection question, the `CLAUDE.md` cut, and this issue-lookup gap)
are resolved — the last four discussed directly with Jeff 2026-08-16, on the
understanding that the underlying trace-through was already verified by
tests and doesn't need a separate line-by-line re-read. Nothing remains open
from Phase 4.

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
file 15). **Fixed 2026-08-04.** `--apply` calls `_verify_manifest_sheet_ids`
first and aborts cleanly — "ERROR: Manifest contains inaccessible spreadsheet
IDs" — before downloading anything, but that call is gated `if apply:`. A
dry run instead reached `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])`
inside the per-class loop (`coding/import_sheets.py` ~line 879) with no
`try`/`except` around it at all, so a bad ID raised an unhandled
`SpreadsheetNotFound` (or the live equivalent) straight out of `main()` —
stopping the *entire* run, every language, not just the one naming the bad
ID. Confirmed identical between the unmigrated and migrated code as part of
the pre/post comparison (both raised the same exception at the same point).

Nothing was lost when it happened — a dry run performs no writes either way —
and the daily `data-refresh` workflow itself runs `import-sheets --apply
--ignore-status` directly, so it always got the clean abort. The risk was the
ordinary coordinator workflow this file's own module docstring recommends:
`python -m coding import-sheets` (dry run) before `--apply`, to preview what
would be written. A single stale manifest entry crashed that preview step
outright, with a raw traceback, rather than reporting per-language the way
every other failure mode in this file does. Same shape as #248 and findings 6
and 7: a guard that exists on one path and not its twin.

Fixed by wrapping the `open_spreadsheet` call in its own `try`/`except
Exception` and reporting the failure per class — matching the reporting
style already used a few lines later in the same loop for `WorksheetNotFound`
(`WARNING: ...`, appended to `lang_warning_lines`, `total_warnings`
incremented, `continue`) — rather than extending `_verify_manifest_sheet_ids`'s
hard-abort to dry runs, which would still have crashed the whole run on the
first bad ID instead of previewing everything else. The `continue` lands back
in the per-class loop, so only the classes on the bad spreadsheet are skipped
for that language — sibling classes on other spreadsheets, and every other
language, are still previewed normally.
`tests/test_import_sheets_snapshot.py::test_a_bad_id_reached_on_a_dry_run_warns_and_previews_every_other_language`
replaces the test that pinned the crash as expected behaviour; it fails
against the pre-fix code (confirmed) and passes now, asserting every language
is still previewed and the bad class is reported as a warning rather than
raised. `--apply`'s clean-abort behaviour via `_verify_manifest_sheet_ids` is
unaffected — still gated `if apply:`, still runs before any language is
touched.

**14. Adding or removing a criterion column re-stamps the manifest's
`param_values` for the whole construction, so a widened value on an untouched
sibling criterion could go stale forever without `--refresh-dropdowns` ever
reporting it** (found 2026-08-04, file 16, `sync_params.py`, while taking the
pre-migration baseline). **Fixed the same day**, as its own commit right after
the migration landed, with the snapshot diff as the evidence — same pattern as
Finding 12.

`main()`'s `if new_params:` branch (`coding/sync_params.py` ~line 720, before
the fix) wrote `cp[construction]["param_values"] = exp_values` unconditionally
whenever a construction gained even one new column — not `{new column: its
values}`, but the *entire* fresh diagnostics dict for every criterion of that
construction, including ones whose dropdown `_insert_param_columns` never
touched (it only builds `setDataValidation` requests for the columns it just
inserted). The `if removed_params:` branch (~line 746) made the identical
mistake on delete. Both were reachable by real fixture data with no test
scenario needed to invent them: `synth0001`'s three `coreference` pair tabs
each still carry all three pair criteria while the diagnostics YAML narrows
each construction to its own one (documented in `coding/CLAUDE.md`'s "Held
until Phase 9" list), so `--apply --remove` against that real drift exercised
the `removed_params` copy of the bug directly.

The second, later `if refresh_dropdowns:` block (~line 758) exists
specifically to catch a criterion whose allowed values changed but whose
column count didn't — it compares `exp_values` against
`sheet_info["construction_params"][construction]["param_values"]`. Because the
branches above had already overwritten that same dict with `exp_values`
moments earlier in the same run, the comparison was always vacuous:
`exp_values.get(p) != exp_values.get(p)` is never true. So any run that both
added or removed a column *and* separately widened a different, untouched
criterion in the same construction — a coordinator adding one criterion and
correcting another's typo'd value list in the same YAML edit, the ordinary way
`diagnostics_{lang_id}.yaml` gets edited — silently dropped the second change.
The sheet's dropdown stayed exactly as stale as before, but the manifest now
falsely recorded it as current, so every subsequent `--refresh-dropdowns` run,
forever, would report "OK — dropdowns up to date" for a column that was never
actually pushed. Same shape as #272 and Findings 9–10: **the manifest was made
to say something true of a column it never actually wrote to.**

Confirmed live, not just reasoned about: reproduced by adding a new criterion
to `synth0001`'s `ciscategorial` class alongside widening `V-combines`'
allowed values in the same YAML edit — the pre-fix code printed nothing about
`V-combines` at all and pushed no `setDataValidation` for its column, while
silently recording `V-combines: ["y", "n", "maybe"]` in the manifest as if it
had. Fixed by snapshotting each construction's prior `param_values` once,
before either branch runs, and having each branch update only the keys it
actually touched (the newly inserted columns, or the surviving columns minus
whatever was just deleted) rather than replacing the whole dict with
`exp_values`. `tests/test_sync_params_snapshot.py`'s
`test_a_new_column_does_not_mask_a_sibling_criterions_stale_dropdown` and
`test_removing_a_column_does_not_mask_a_sibling_criterions_stale_dropdown`
pin both branches: the widened criterion is now reported, and its
`setDataValidation` request is confirmed landing on the correct column with
the correct values — not merely that the manifest's text changed.

**15. `--force` does not cleanly refuse before writing anything — it
overwrites a language's planar/diagnostics reference sheets first, then
aborts** (found 2026-08-04, file 17, while taking the pre-migration baseline).
**Fixed 2026-08-04, per Jeff's sign-off.** `main()`'s per-language loop called
`_upload_lang_setup_as_sheets(..., force=force)` — which overwrites the planar
and diagnostics Sheets whenever `force=True`, regardless of whether that
language has annotation sheets — *before* `_check_force_against_existing_sheets`
ran and aborted the whole multi-language run with `SystemExit(1)`. The
module's own docstring line, `--apply --force  # blocked with a hard error if
annotation sheets already exist`, reads as a clean refusal; what actually
happened for a multi-language run was: the first language with existing
annotation sheets got its planar/diagnostics *reference* sheets (not its
annotation sheets, which the guard genuinely does protect) silently
overwritten, then the whole run stopped there — no later language in the same
invocation was ever reached, `--force` or not.

Nothing analytically irreplaceable was at risk — the overwritten sheets are
the structural planar/diagnostics tables, sourced from the local TSV, not
annotation judgments — but it was still a live write the coordinator's own
mental model of this flag says cannot happen. Same shape as #248 and Finding
13: a guard that exists but does not cover the whole path leading up to it.

Jeff's decision: move the guard so it runs for every language before any
upload happens for any of them — a preflight pass, not just a reorder within
one language's own iteration. Fixed by adding a preflight loop, right after
`merged_config` is fetched and before the per-language loop starts, that
resolves `existing_lang_data` for every language (the same manifest lookup
plus old-format fallback the per-language loop used to do inline) into
`existing_lang_data_by_lang`, and calls `_check_force_against_existing_sheets`
on each one immediately. Any language failing the guard raises
`SystemExit(1)` during this preflight pass, before the per-language loop —
and therefore before any language's sheets — is ever reached. The
per-language loop now looks `existing_lang_data` up from
`existing_lang_data_by_lang` instead of recomputing it (avoiding a duplicate
Drive read for the old-format fallback), and its own now-redundant call to
`_check_force_against_existing_sheets` was removed.
`tests/test_generate_sheets_snapshot.py::test_force_refuses_before_destroying_any_annotation_sheet`
was strengthened from pinning only the annotation sheet's tab content
byte-identical to asserting `env.doorway.mutations == []` — no mutation
happens anywhere, not even to the reference sheets. A new test,
`test_force_refuses_for_a_later_language_before_an_earlier_one_is_touched`,
makes the earlier-vs-later distinction explicit: with `arao1248` and
`stan1293` made brand new (no force conflict) and only `synth0001` — last
alphabetically — keeping its real existing annotation sheets, the run still
aborts with zero mutations, proving the guard checks every language up front
rather than happening to catch the first one in iteration order. A third
test, `test_force_succeeds_as_before_when_no_language_fails_the_guard`,
confirms the passing path is unchanged: with every language brand new,
`--force --apply` still creates every language's sheets exactly as before.
All three fail against the pre-fix code and pass against the fix.
`tests/snapshots/coordinator/generate_sheets/force_refused.txt` was
regenerated: the transcript no longer shows `Language: arao1248` or
`Updated planar/diagnostics sheet` lines before the abort — the whole run now
prints nothing but the connection line, the manifest backup line, and the
error, confirming no per-language work happens before the preflight check.

**16. `_copy_pair_tab_with_rename` wrote a pair tab's dropdown onto the wrong
column for two of the project's three pair-row shapes** (found 2026-08-04,
file 18, `restructure_sheets.py`, via `assert_no_criterion_writes_onto_trailing_columns`
during the migration's own snapshot suite). **Fixed the same day**, as its own
commit right after the migration landed, with the snapshot diff as the
evidence — the same pattern as Findings 12 and 14. The function called
`_format_and_validate(ws, ..., col_start=4)` unconditionally
(`coding/restructure_sheets.py`, inside `_copy_pair_tab_with_rename`).
`col_start=4` is correct for coreference's pair shape — `Element_A,
Position_A, Position_B, Direction`, four structural columns before the one
criterion — but `nonpermutability`'s and `phrasal_accent`'s `general`
construction uses a different, two-column pair shape: `Element_A, Element_B`,
with the criterion at column 2. Confirmed live against the real fixture data:
a restructure of `stan1293`'s `nonpermutability` class wrote a `y`/`n`/`both`
dropdown onto `Comments` (header `[Element_A, Element_B, scopal, Source,
Comments]`) and left `scopal` itself with no dropdown at all.

Same shape as #272, Finding 10, and Finding 14: **a column position assumed
rather than read from the header it is actually writing to.** The other three
pair-row-writing functions in this file (`_write_tab_with_carryover`,
`_cascade_rename_pair_tab`, and `_apply_split_to_pair_rows`) all locate their
columns by `header.index(...)`, which is exactly why they passed the same
check clean; this one function had reverted to a hardcoded offset. Confirmed
identical between the unmigrated and migrated code as part of this
migration's own before/after comparison — both wrote the dropdown to the same
wrong column — so it was pre-existing, not introduced by the doorway
substitution. Not fixed in the migration commit itself, per the deferral rule
(fixing would have changed what the command writes, which is exactly the diff
that migration's comparison needed to hold still). Fixed properly in the very
next commit: `col_start` is now `header.index(criterion_col)` when
`criterion_col` is present in the header (the function already receives
`criterion_col`), falling back to `header.index(param_names[0])` and then to
a derived (not guessed) position if neither is found. `tests/test_restructure_sheets_snapshot.py::test_finding_16_pair_tab_dropdown_lands_on_the_criterion_column_not_comments`
pins the fix: the dropdown now lands on `scopal` with its real allowed values
(`['y', 'n', 'both']`), not merely that some column changed. Verified
independently of the pytest suite too, by re-running the exact scenario that
first surfaced it against `stan1293`'s real `nonpermutability` fixture data
and confirming `assert_no_criterion_writes_onto_trailing_columns` now passes
where it previously failed.

**17. `restructure_sheets.py` never calls `drive._check_coded_data_clean()`**
(found 2026-08-04, file 18, confirmed by grep — the string does not appear in
the file at all). **Fixed 2026-08-04, per Jeff's sign-off.** Every other
command that reads `coded_data/` as its source of truth before writing live
Sheets calls this guard first (`import_sheets.py`, `update_sheets.py`,
`sync_params.py`, `generate_sheets.py --regen-dependents` — see
`coding/CLAUDE.md`'s `drive.py` bullet) precisely because #248's stray-row
incident was `update-sheets` acting on a `planar_{lang_id}.tsv` left stale by
an earlier step's failed auto-commit, with nothing to catch it.
`restructure_sheets.py` reads exactly the same two files
(`planar_{lang_id}.tsv`, `diagnostics_{lang_id}.tsv`) as its source of truth
for what the *new* sheet structure should be, and is the single most
destructive command in the project — archive-then-recreate, no rollback — so
it was a plausible candidate for the same class of incident, not a peripheral
one.

Not fixed in the migration itself: adding the guard is a new abort path,
which changes what the command does before any of its Drive calls, not a
call-site substitution — squarely the kind of change that migration's
non-goals ruled out. Fixed in a follow-up commit by importing
`_check_coded_data_clean` from `.drive` and calling
`_check_coded_data_clean(extensions=(".tsv",))` right after CLI flags are
parsed and before connecting to Drive — the same position and phrasing as
`sync_params.py`'s precedent, gated `if apply:` like every sibling command.
`tests/test_restructure_sheets_snapshot.py::test_apply_asks_whether_coded_data_is_clean`
pins it (fails before the fix with an `AttributeError`, since the module had
no such attribute to patch at all — direct confirmation of the grep finding —
and passes after); `test_the_dry_run_does_not_ask_whether_coded_data_is_clean`
confirms the guard stays off the dry-run path, matching every sibling
command. The precondition record was added in the same commit as the fix,
per this project's "write the record as part of the fix" rule for
`data_dependency_schema/`: `restructure_sheets.py (restructure-sheets --apply)`
is now listed in `data_dependency_schema/preconditions.yaml`'s
`coded_data_clean_tree` entry's `required_by`.

**29. Populating `operations.yaml`'s new `writes_to_drive` field (unit E)
found `apply_pending`'s own direct Drive footprint is read-only** (found
2026-08-17, scoping unit E's provenance logging). Its side effect text says
it "applies coordinator-approved destructive changes to coded_data/ and/or
the manifest", which reads as a Drive write — but tracing `apply_pending.py`
directly shows its only Drive call is `doorway.open_spreadsheet()` inside
`_check_construction_tab_exists`, a read used to verify a new-construction
entry before offering to apply it. The actual destructive action runs via
`_run_command`, a `subprocess.run` shelling out to another
`python -m coding <cmd> --apply` — which, invoked that way, goes through the
dispatch chokepoint itself and logs its own provenance entry independently.
Setting `apply_pending`'s `writes_to_drive: true` would have double-logged
every entry it applies: once (correctly) from the delegated command's own
run, and once (redundantly) from `apply_pending` itself, for a write it
never actually performed. Set to `false` instead — not a code fix, since
nothing was wrong before this field existed; recorded here because it's the
same kind of "declared claim doesn't match what the code does" gap
Findings 22–28 exist to catch, just caught before anything was ever wired to
the wrong value rather than after.

Also found, not fixed (deliberately, see `coding/provenance.py`'s module
docstring and its "Known gap" note): `import-sheets` paints pink highlighting
on invalid cells (a real Sheet write) on *every* run, including a dry run —
that write is not gated by `--apply` at all, only its other side effects
(the local TSV write, `pending_changes.json`) are. Its `operations.yaml`
`apply_gate` ("--apply") correctly describes those other effects, so gating
provenance logging on that same field means a dry run of `import-sheets`
that paints cells goes unlogged. The schema's `writes_to_drive`/`apply_gate`
pairing has no way to express "this command has two side effects with two
different gates" without a second field on the one record that needs it —
judged not worth adding for a single case; flagged here rather than
silently accepted.

**30. `keystone_pos` briefly leaked a numpy `int64` instead of a plain `int`**
(introduced and caught the same session, 2026-08-17, Phase 6 unit 1). While
rewiring `_parse_filled_df` onto `raw_shape_schema`, `keystone_pos` was read
straight off the DataFrame with `.iloc[0]`; the original code got a plain
`int` for free because it passed through `.unique().tolist()` first, which
converts numpy scalars to native Python ones. `tests/test_reports.py`'s
`assert isinstance(entry["keystone_pos"], int)` and two snapshot tests
(`stan1293_free_occurrence_general`, `synth0001_free_occurrence_general`,
which format a position list into text) caught it immediately — the numpy
repr (`np.int64(30)`) showed up inline in the rendered span text. Fixed by
wrapping in `int(...)` at the same call site. No coordinator-facing output
was ever produced with the bug in place; caught by the full suite before
commit.

---

## Decisions log

**2026-08-17 — Phase 5 units D and E, both decided in the same session
after being blocked on Jeff's input since 2026-08-16.** D: replace the
scattered manual `_check_coded_data_clean()` calls with dispatch-level
enforcement, file-by-file with the Phase 0b/1 pre/post-diff discipline —
not add a second layer, and not one sweep. E, two decisions: log only
commands with real Drive side effects (not every command), and — a
refinement surfaced only once implementation started, since
`sync-diagnostics-yaml`'s and `import-planar`'s Drive-write status turned
out to genuinely diverge by mode (their default directions touch only the
local YAML/TSV) — log per actual invocation, not per command, so a run
whose real flags never reach Drive is never logged even when the command
*can* write to Drive under a different flag. Retention: append-forever.
Both units done the same day; see the *Next action* section above for what
each actually built, and Finding 29 above for what populating the new
`writes_to_drive` field turned up.

**2026-08-04 — file 18 (`restructure_sheets.py`), the last file, completes
Phase 0b/1.** Every primitive it needed already existed: `get_doorway()`,
`load_manifest()`, `upload_manifest()`, `doorway.open_spreadsheet()`,
`doorway.create_spreadsheet()`, `doorway.move_file()`,
`doorway.update_file()`, `doorway.get_or_create_folder()`,
`doorway.create_permission()`, `doorway.list_permissions()`,
`doorway.delete_permission()`. The call-site mapping was a plain substitution
throughout `_rename_class_for_language` and `main()`'s per-class loop, `gc,
drive = _get_clients()` / `_load_manifest_from_drive(drive)` becoming
`doorway = get_doorway()` / `load_manifest(doorway)`, `_open_spreadsheet(gc,
id)` becoming `doorway.open_spreadsheet(id)`, and six occurrences of `except
gspread.WorksheetNotFound` becoming `except WorksheetNotFound` (imported from
`drive_doorway` instead).

**`_get_or_create_subfolder` was consolidated into `doorway.get_or_create_folder`
rather than migrated as its own function**, after checking the two really are
equivalent rather than assuming it: both build the identical Drive query
(name + parent + folder mimetype + not trashed) and the identical
create-if-absent body; the only difference is the `fields` mask on the list
call (`"files(id)"` vs. the doorway's `"files(id, name)"`), and every caller
of either only ever reads `.id`, so the extra field is inert. This is the
same substitution the brief for file 12 (`generate_status_sheet.py`) declined
to make for `_remove_anyone_permission`, for the opposite reason: that helper
had no doorway equivalent at all, so it was inlined from primitives instead
(and `_lock_archived_sheet` here does exactly the same inlining, following
that precedent, rather than restating a third copy of the same two-call
sequence).

**`import gspread` stays**, unlike most migrated files, for
`gspread.utils.rowcol_to_a1` in `_cascade_rename_pair_tab` (~line 607) — pure
coordinate arithmetic, not a client call, the identical reasoning
`sync_params.py`'s migration (file 16) used to keep the same import. Grepping
the whole file afterward for `gspread\.` turned up only that one call plus
one docstring mention; every other prior use was a type hint
(`gspread.Worksheet`/`gspread.Spreadsheet` → `WorksheetHandle`/
`SpreadsheetHandle`) or an `except` clause, confirmed rather than assumed.

Thirteen scenarios, run through both the unmigrated code (a throwaway copy
placed temporarily inside `coding/` so its own relative imports resolved,
never committed) and the migrated code against identically-seeded fakes,
using thin `gc`/`drive` shims backed by the same `FakeDriveDoorway` instance
and a socket-level guard raising on any connection not to localhost: a plain
dry run and a true no-op `--apply` over the real fixture data (nothing in the
repository today needs restructuring, confirmed rather than assumed — every
class hit "no changes — skipping"); `--rename-map` carrying over a renamed
position, dry run and apply, across every class of one language including its
pair-row constructions; `--rename-element`; `--split-element` fanning one
element into two and cascading into `nonpermutability/general` (the pair-row
tab referencing it); the same split with a synthetic self-pair row injected
directly into the fake beforehand (left untouched, flagged for manual
review); `--rename-class`'s pre-flight abort (old class still active in
diagnostics) and a real apply after the diagnostics files were updated first;
a missing construction tab, hit on both the download step and
`_copy_pair_tab_with_rename` in the same run (deleting a coreference pair tab
from the fixture before a rename-map apply that restructures every class in
that language); `--lang` restricting to one language while two others stay
seeded; and a class absent from the manifest. `_autocommit_data`,
`generate_notebooks.regenerate_notebooks`, `validate_coding.revalidate_sheets`,
and `import_planar.push_planars_to_sheets` were stubbed identically on both
sides rather than driven for real (file 15's precedent — the harness diffs
this file's own Drive interaction, not theirs). stdout, the mutation log,
`sheets_manifest.json`, and every `coded_data/` TSV written came back
byte-identical across all thirteen.

Two harness lessons, both already named in this log for earlier files and
reconfirmed here: `load_manifest`/`upload_manifest` (`coding/drive.py`) call
*that module's own* `_load_drive_config()` internally, so patching only the
importing module's copy of the name reaches real `drive_config.json` and a
real (unreachable, fake-seeded) file ID — caught immediately by an early
`SystemExit`, not a silent pass, but worth restating since it is the same
"patch where it's actually bound" lesson files 5 and 15 already recorded, one
level further down the call chain than either of those. `_autocommit_data`
similarly reads *that module's own* `CODED_DATA` constant rather than any
path threaded through a caller, so both harness runs stub it rather than
letting it shell out to `git` against a temp directory it doesn't know about.

**`assert_no_criterion_writes_onto_trailing_columns` did not pass clean in the
migration commit** — see Finding 16 above, fixed the same day in the very next
commit. This is the first file where that check caught a real, live bug
rather than confirming cleanliness: `_copy_pair_tab_with_rename`'s hardcoded
`col_start=4` was right for coreference's four-structural-column pair shape
and wrong for `nonpermutability`'s/`phrasal_accent`'s two-column one.
Pre-existing, confirmed identical on both sides of the before/after
comparison, and not fixed in the migration commit itself per the deferral
rule — the migration's own test suite reflected this honestly rather than
papering over it: two of the "nothing criterion-shaped is written" checks were
scoped to `arao1248` (which has no pair-row classes at all, so genuinely
demonstrates clean behaviour for `_write_tab_with_carryover`), and a separate
test explicitly pinned the wrong placement on `nonpermutability/general` as
known, current, deferred behaviour rather than folding it into a passing
"clean" assertion. Once the migration's own before/after comparison was taken
and committed, the deferral expired the same way it did for Findings 12 and
14: `col_start` now derives from `header.index(criterion_col)`, and the
pinning test was rewritten to assert the fixed placement instead of the bug.

**The pre-existing, undocumented gap this file's brief asked to confirm —
whether `_check_coded_data_clean()` is called anywhere in
`restructure_sheets.py` — is confirmed real.** It is not, despite the file
reading `planar_{lang_id}.tsv`/`diagnostics_{lang_id}.tsv` from `coded_data/`
as its source of truth for the very structure it recreates sheets from, and
despite being the most destructive command in the project. Recorded as
Finding 17. Not fixed in this session, per the task's own explicit
instruction — adding a new abort path is a behaviour change, not a call-site
migration, and belongs to a deliberate change of its own.

`tests/test_doorway_coverage.py`'s `_REMAINING` is now the empty set — the
migration's main test flips, exactly as its own docstring said it would, from
"the list is exactly this" to "the list is empty"; `test_stated_counts_match_the_code`'s
regex was widened to recognise the finished phrasing ("done, N of N") as well
as the in-progress one ("migrating callers, N of M done"), since the progress
doc's own wording changed once there was no longer an "of M" to be behind.
`coding/CLAUDE.md`'s migrated list gains `restructure_sheets.py` (now all
eighteen), the "one other command still reaches Drive directly" sentence
becomes "all commands that touch Drive now go through the doorway," and its
own bullet plus the `drive_doorway.py` paragraph both name Finding 16.
`docs/data-layer-progress.md` moves to "done, 18 of 18" and the migration
order table's last row is struck through like the rest. This is the Phase
0b/1 completion commit; `docs/data-layer-implementation-plan.md`'s Phase 3
is next, gated on a decision from Jeff per the plan's own "(coordinator
decides)" marking on that phase — see § "Next action" above.

**2026-08-04 — file 17 (`generate_sheets.py`) needed no doorway addition, but
was the first migration shaped differently from every one before it.** Every
prior file only reached Drive inside `main()` or one or two leaf helpers, so
the migration was a call-site substitution at the entry point.
`generate_sheets.py` instead passes `gc`/`drive` as explicit parameters
through a chain of its own functions — `_create_or_update_tsv_sheet` (called
by `_upload_lang_setup_as_sheets`), `_create_analysis_sheet`,
`_regen_construction` (called by `_regen_dependents_simple`) — so the
migration replaced two parameters with one (`doorway`) at every level of that
chain, not just at `main()`. `_add_constructions_to_existing_sheet` needed no
signature change at all: it already took an open spreadsheet handle rather
than a client, added when `update_sheets.py` (file 11, which also calls it)
was migrated — that caller was already reaching Drive through the doorway
with no client to hand over, and this migration confirms the same function
serves both callers unchanged.

Every primitive this file uses already existed: `get_doorway()`,
`load_manifest()`, `upload_manifest()`, `create_notes_doc()`,
`doorway.open_spreadsheet()`, `doorway.create_spreadsheet()`,
`doorway.move_file()`, `doorway.create_permission()`,
`doorway.get_or_create_folder()`, `doorway.list_files()`,
`doorway.download_file_json()`. `main()`'s own manifest download
(`merged_config = doorway.download_file_json(existing_config_file_id)`,
inside the try/except that also writes `manifest_backup.json` and resets to
`{}` on the pre-#30 per-language format) deliberately did **not** get
consolidated into `load_manifest(doorway)` — that helper has different
fallback semantics for the old format and does not write the recovery
backup, both of which this call site depends on. Same for the two other
in-file manifest downloads (inside `--regen-construction`/`--regen-dependents`
and the old-format fallback) — all became `doorway.download_file_json(...)`,
none became `load_manifest(...)`. The dead `docs = _get_docs_client(gc)` line
in `main()` was confirmed genuinely unused (no other reference to the bare
name `docs` anywhere in the file) and deleted as part of the migration rather
than preserved — it existed only to build a client this migration removes the
need for, and the doorway has no equivalent "raw Docs client" primitive to
hand back (`create_doc`/`get_doc_text`/`append_doc_text` cover every real use).

One departure from a plain call-site substitution, on purpose: `_regen_construction`
opened its spreadsheet with a bare, unwrapped client call — the only spot in
this file with no retry at all, unlike every other spreadsheet open here
(which already went through the file's own retry helper). `doorway.open_spreadsheet`
always retries, so this call site now gets the same 429/500/503 backoff as the
rest of the file. `drive_doorway.py`'s own docstring names exactly this
inconsistency as one of three it deliberately unifies; opening is an
idempotent read, so the added retry changes nothing about what gets written —
confirmed by the pre/post diff below, not just reasoned about.

`import gspread` is dropped entirely (unlike file 16, which kept it for one
coordinate-arithmetic utility `restructure_sheets.py` also needs) — every
remaining use in this file was a type hint (`gspread.Spreadsheet` →
`SpreadsheetHandle`, `gspread.Worksheet` → `WorksheetHandle`) or an
`except gspread.WorksheetNotFound` (five occurrences, all → `WorksheetNotFound`
imported from `drive_doorway`), confirmed by grepping the whole file for
`gspread.` after the edits, per the migration brief's own instruction to
verify rather than assume.

Twelve scenarios, run through both the unmigrated and migrated code against
identically-seeded fakes, using thin `gc`/`drive` shims patched into
`coding.generate_sheets`'s own namespace (the file 5/15/16 lesson — this file
does `from .drive import ..., _get_clients, ...` at module level, so the name
is bound in its own namespace) with a socket-level guard raising on any
connection not to localhost: a dry run and a true no-op `--apply` over the
real fixture data (all three languages already have every class — the manifest
and each language's `diagnostics_{lang_id}.yaml` agree exactly, confirmed
before writing the harness rather than assumed); a brand-new language —
`arao1248` with its manifest entry stripped from a private copy of the
fixture, its real spreadsheets left seeded in the fake so only the manifest
"forgets" — both dry-run and `--apply` (the full creation path: folder, notes
doc, planar/diagnostics sheets, one sheet per class, Status tabs); a new class
added to an existing language's diagnostics YAML; a new construction added to
an existing class (`_add_constructions_to_existing_sheet`, not
`_create_analysis_sheet`); `--force` refused when annotation sheets already
exist; `--regen-construction` for a `nonpermutability` pair construction and a
`coreference` one with `--pos-remap` and `--confirm-drop` (real fixture data:
38 pairs both added and removed by the remap, not a constructed edge case);
`--regen-dependents` both skipping (the real fixture data has no missing
dependent TSV) and regenerating (one deleted to force it); and `--push-manifest`.
stdout and the mutation log came back byte-identical between the unmigrated
and migrated code for all twelve, diffed as complete files rather than
sampled.

A pre-existing quirk, not introduced by this migration, confirmed identical on
both sides of the comparison rather than fixed: **`--force` overwrites a
language's planar/diagnostics reference sheets before
`_check_force_against_existing_sheets` aborts the run** — recorded as
Finding 15 above, per the deferral rule (it changes what the command writes,
so fixing it would have obscured the before/after comparison this migration
needed).

A second, minor gap found while building the mutation digest, not a migration
bug: `tests/render_mutations.py` resolves a mutation's tab title and header
by looking the spreadsheet ID up in the recorded fixtures, so it cannot name
columns for a spreadsheet created within the test itself — `brand_new_apply_digest.txt`
shows `BEYOND HEADER` for every column of every newly created tab. This is the
first migration to create enough new sheets in one digest for the gap to be
visible; every earlier creation-heavy file (`generate_biuniqueness_allomorphy_sheet.py`)
either didn't produce a digest snapshot or created only one sheet. The
mutation-log diff (not the digest) is what actually proved this migration
correct, per the established evidence order — the digest remains useful for
counts and structure, just not column names, for a spreadsheet born mid-test.
Not fixed here; noted in `coding/CLAUDE.md`'s `render_mutations.py` mention for
whoever migrates `restructure_sheets.py` next, since that file also creates
sheets in its own snapshot tests.

Thirty tests in a new `tests/test_generate_sheets_snapshot.py`: the twelve
transcript/digest scenarios above, plus a dry run performs no Drive mutations
and never asks whether `coded_data/` is clean (only `--regen-dependents`
does); `--force` refuses before destroying any annotation sheet's own content
(the quirk above, pinned rather than papered over); the orphan-sheet Drive-name
guard aborts before `create_spreadsheet` is ever called, confirmed by asserting
on the mutation log rather than only on stdout; a second identical `--apply`
after creation is a no-op for that language; `--regen-dependents` stops firing
for a class once its dependent TSV has been imported locally (the actual
no-repeat promise — a bare second call with nothing else changed is not
idempotent by itself, since this command never writes `coded_data/`, only
the live Sheet); `assert_no_criterion_writes_onto_trailing_columns` passes
clean across creation, a new class, a new construction, and both
`--regen-construction` paths; the manifest uploads on a real creation and
never on a dry run; `drive_config.json` is saved after a real apply; and
notebooks regenerate after a real apply but not on a dry run or on
`--regen-construction` (which returns before `main()`'s own
`regenerate_notebooks()` call, confirmed rather than assumed from the early
`return`).

`tests/test_generate_sheets.py`'s `TestCreateAnalysisSheetDriveNameGuard`
replaced its raw `MagicMock()` stand-ins for `gc`/`drive` with a `_DoorwayStub`
exposing `list_files`/`create_spreadsheet`/`move_file`/`create_permission` —
the same precedent `test_import_sheets.py`'s `_DoorwayStub` set for file 15.
Every other test in that file (the pure-logic tests: `_build_nonperm_pairs`,
`_filter_nonperm_pairs_by_prescreening`, `_prefill_free_occurrence_rows`,
`_regen_dependents_simple`'s skip/regen logic even though its own `gc`
parameter is now `doorway`, `_plan_language_creation`,
`_check_force_against_existing_sheets`, the phrasal-accent adjacency
algorithm, `_parse_pos_cell`/`_remap_coreference_prefill`) needed no changes
at all, confirming the brief's own read that this file is "long but not deep".

`tests/test_doorway_coverage.py`'s `_REMAINING` drops `generate_sheets.py`
(one file now remains: `restructure_sheets.py`); `coding/CLAUDE.md`'s migrated
list gains it, its own `generate_sheets.py` bullet notes the migration and the
retry-behaviour departure, and the `drive_doorway.py` bullet's
`assert_no_criterion_writes_onto_trailing_columns` paragraph is rewritten to
name `generate_sheets` as checked-and-clean alongside `sync_params`, and to
record the `render_mutations.py` header-resolution gap for newly created
sheets; `docs/data-layer-progress.md` moves to 17 of 18 and recomputes the
remaining weight (`restructure_sheets.py` alone: 1,425 lines, 10 direct Drive
calls).

**2026-08-04 — file 16 (`sync_params.py`) needed no doorway addition.** Every
primitive it uses already existed: `get_doorway()`, `load_manifest()`,
`upload_manifest()`, `doorway.open_spreadsheet()`. The call-site mapping was a
plain substitution throughout: `gc, drive = _get_clients()` /
`_load_manifest_from_drive(drive)` became `doorway = get_doorway()` /
`load_manifest(doorway)`; `ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])`
became `ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])`;
`except gspread.WorksheetNotFound` became `except WorksheetNotFound` (imported
from `drive_doorway` instead); the manifest-upload call at the end of `main()`
became `upload_manifest(doorway, manifest, root_folder_id, existing_file_id)`;
and six `ws: gspread.Worksheet` type hints (`_get_current_params`,
`_rename_column`, `_insert_param_columns`, `_apply_split_to_sheet`,
`_apply_merge_to_sheet`, `_build_dropdown_refresh_requests`) became `ws:
WorksheetHandle`. One departure from dropping `gspread` entirely, unlike file
15: `gspread.utils.rowcol_to_a1(1, insert_at + 1)` (`_insert_param_columns`,
computing where to anchor a batch write) is pure coordinate arithmetic, not a
client call, and `restructure_sheets.py` — not yet migrated — uses the
identical call, so `import gspread` stays for that one utility rather than
being removed and re-added on the next file.

Every `_with_retry`-wrapped call site keeps exactly the retry behaviour it had
— `_get_current_params`'s and the two split/merge helpers' `ws.row_values(1)`
stay wrapped, matching the three unwrapped `ws.row_values(1)` calls inline in
`main()`'s rename/split/merge blocks staying unwrapped, per the migration's
non-goal of no behaviour changes beyond the call-site substitution.

This was the file the migration order named as the one to watch —
`docs/data-layer-progress.md`'s own "Next action" section had flagged it as
the most likely to reproduce #272/Finding 10's bug class, since it inserts and
deletes criterion columns, the densest form of that question. It checked out
clean: `_get_current_params`, `_insert_param_columns`, and
`_build_dropdown_refresh_requests` all already derived column positions from
the tab's own header (`ws.row_values(1)`, read fresh at each call), never from
the manifest's `param_names`/`construction_params`. `assert_no_criterion_writes_onto_trailing_columns`
passed clean across every scenario that touches columns (add, remove, rename,
split, merge, both refresh-dropdowns code paths). What the manifest *did* get
wrong here was a different shape — see Finding 14 — a `param_values`
bookkeeping error, not a wrong-column write, so it did not trip this
assertion at all.

Fifteen scenarios, run through both the unmigrated and migrated code against
identically-seeded fakes: a plain dry run and apply over the real fixture data
(which already contains one genuine drift — `synth0001`'s three `coreference`
pair tabs each carry all three pair criteria while the diagnostics YAML
narrows each construction to its own one, so this is a real WARNING, not a
constructed scenario); a new criterion added to the diagnostics YAML, dry run
and apply; `--apply --remove` against that real coreference drift; `--rename`
unscoped and scoped to one class; `--split`; `--merge`; both
`--refresh-dropdowns` code paths (the "no structural change" branch, and the
branch right after new columns are inserted in the same run); a class present
in the manifest but absent from the diagnostics YAML; and a missing
construction tab (`WorksheetNotFound`). stdout, the mutation log, and the
rewritten `diagnostics_{lang_id}.tsv`/`.yaml` files in `coded_data/` all came
back byte-identical between the unmigrated and migrated code, confirmed with
`assert_no_criterion_writes_onto_trailing_columns` run against every scenario
in the harness rather than assumed clean from the code reading alone.

A pre-existing bug unrelated to the migration was found while taking the
baseline, reproducible on both the unmigrated and migrated code identically —
recorded as Finding 14 above. Not fixed in the migration commit itself, per
the deferral rule (it changes what the command *writes* to the manifest, so
it waited for this migration's own before/after comparison to be taken
first, mirroring how Finding 12 was handled) — fixed properly in the very
next commit, with the snapshot diff as the evidence: `main()` now
snapshots each construction's prior `param_values` once, before either the
`new_params` or `removed_params` branch runs, and each branch updates only
the keys it actually touched rather than replacing the whole dict with
`exp_values`. Forty tests in `tests/test_sync_params_snapshot.py`: the
fifteen transcript/digest scenarios above, plus property assertions — a dry
run performs no mutations and never touches `coded_data/`'s diagnostics
files; `--remove` only ever deletes columns genuinely absent from the
diagnostics YAML, never one still expected; `_split_`/`_merged_`-prefixed
stale columns survive a later `--apply --remove` untouched; a second
identical `--apply`, `--remove`, or `--refresh-dropdowns` run is confirmed a
true no-op (verified empirically rather than assumed — `sync_params` has
more moving parts than `update_sheets`, and all three held); the manifest
upload and `generate_notebooks.regenerate_notebooks()` both fire only when
something genuinely changed, including the non-obvious case where a
`--remove`-eligible warning alone (with no `--remove` passed) already counts
as "something changed" because the coordinator needs to see the warning; and
the two Finding 14 regression tests
(`test_a_new_column_does_not_mask_a_sibling_criterions_stale_dropdown`,
`test_removing_a_column_does_not_mask_a_sibling_criterions_stale_dropdown`),
which check the actual `setDataValidation` mutation and its values landed on
the right column — not just that the manifest's text changed, which is
exactly what the bug would have passed.

`tests/test_doorway_coverage.py`'s `_REMAINING` drops `sync_params.py` (two
files now remain, both still reading `construction_params` from the manifest
— see the "Next action" update in the same commit); `coding/CLAUDE.md`'s
migrated list gains it, its own `sync_params.py` bullet notes the migration
and the Finding 14 fix, and the `drive_doorway.py` bullet's paragraph about
the remaining files reading `construction_params` is rewritten to name
`sync_params` as checked-and-clean rather than still-to-check;
`docs/data-layer-progress.md` moves to 16 of 18 and recomputes the
remaining-files weight (4,080 lines, 22 direct Drive calls across
`generate_sheets` and `restructure_sheets`).

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

**2026-08-04 — issue #276 resolved: the four duplicated Drive helper groups
collapsed into three shared functions in `coding/drive.py`.** Jeff made the
two behavioural calls the issue flagged as needing his judgment: reports now
reassert their PDF's "anyone" share on every run instead of only on create
(matching notebooks), and root-folder setup now checks before granting
instead of re-granting unconditionally (matching `generate_status_sheet.py`'s
existing `_already_shared` precedent). Rather than three separate patches,
one mechanism does both: `ensure_anyone_permission(doorway, file_id,
role="reader")` lists existing permissions first and only creates a grant
if none of type `anyone` exists — self-healing after a manual revoke and
duplicate-proof against a normal repeat run, from the same check. Building it
as one function first, then wiring in all three call sites, avoided giving
reports the exact bug root-folder setup was being fixed for: an unconditional
reassert with no existence check is itself the bug, regardless of which file
carries it.

`create_or_update_shared_file` (create-or-update, rename-on-update, calling
`ensure_anyone_permission` internally) replaces `generate_notebooks.py`'s
`_upload_file`/`_set_viewer_permissions` and `generate_reports.py`'s
`_upload_pdf` — confirmed identical once sharing timing was unified, per the
issue's own suggestion. `get_or_create_spreadsheet` replaces
`generate_status_sheet.py`'s `_get_or_create_status_spreadsheet` and
`generate_biuniqueness_allomorphy_sheet.py`'s
`_get_or_create_allomorphy_spreadsheet` — identical bodies, as catalogued.
`refresh_dropdowns.py`'s inline manifest-write copy was replaced with a call
to the already-shared `upload_manifest`, gaining key-reordering and a
create-if-missing fallback it previously lacked. Folder find-or-create (the
issue's item 3) needed no work — already consolidated into
`doorway.get_or_create_folder` during `restructure_sheets.py`'s own #271
migration (commit `6bc9abc`).

**The suspicion that `generate_notebooks.py` already had the duplicate-grant
bug, not just `setup_root_folder.py`, panned out.** Its `_set_viewer_permissions`
was called unconditionally on every run with no existence check — the same
shape of bug as `setup_root_folder.py`'s, just never named as a Finding
because nothing had compared the two files side by side. Since notebooks
regenerate after nearly every `--apply` across several commands
(`generate_sheets`, `sync_params`, `restructure_sheets`), this had likely been
silently piling up duplicate "anyone" grants on every language's notebooks in
production. Fixed by the same `ensure_anyone_permission` check as everything
else, not by a separate patch.

**Dead code removed as part of the same change:** `drive.py`'s
`_share_anyone_with_link`, `_share_with_person`, and `_remove_anyone_permission`
had no remaining callers once the doorway migration finished — every caller
that used to reach them directly had already moved to the doorway's
`list_permissions`/`create_permission`/`delete_permission`. `_share_anyone_with_link`'s
only caller was the raw (non-doorway) `_create_notes_doc`, itself dead —
`create_notes_doc` (the doorway-based wrapper `generate_sheets.py` and
`check_notes.py` actually call) has always been the live path. Deleted rather
than left as unreferenced code, per this project's "delete unused code, don't
deprecate it" convention.

---

**2026-08-10 — Phase 3 (schema reorganization) done.** Jeff decided the split
mechanism (two parallel files, `diagnostic_classes.yaml` +
`diagnostic_classes_status.yaml`, joined by class `name`) over a one-file/
two-key-block alternative and a no-physical-split field-rate-registry
alternative — the two-file option won on "clean ownership" (a person editing
linguistic content never scrolls past process bookkeeping and vice versa),
accepting that every reader needs a merge step. That step already existed as
a single chokepoint (`coding/schemas.py`'s `load_diagnostic_classes()`), which
is what made the two-file option's downside (every reader needs both files)
cost nothing in practice — the ~30 existing callers across `coding/` and
`planars/` needed no changes.

Jeff also bucketed the three fields that don't obviously belong to either
side by their own logic, not a rule stated in advance: `criterion_set_status`
(a workflow/maturity flag like `status`, not a claim about the language),
`qualification_rule_hash` (a derived integrity checksum, never hand-edited,
belongs with other process fields even though it's meaningless without the
rule it checks), and `sheet_instructions` (operational guidance for running
annotation, not a claim about the language's grammar) — all landed
administrative. One real coupling cost from that: a class's two-stage sheet
workflow is now split across both files (`constructions` in the research
file states the dependency structure; `sheet_instructions` in the status file
says what to tell the annotator), so editing a multi-stage class like
`nonpermutability`, `coreference`, or `phrasal_accent` means opening both.

The text-level split (not a `yaml.dump` round-trip) was necessary to preserve
every inline comment exactly — this file has 30+ rationale/issue-reference
comments per class on average. The split script found and fixed its own bug
mid-build: a first pass forward-attached every standalone same-indent comment
to the field that followed it, which is right most of the time but wrong for
seven comments that continue a field's own inline trailing comment wrapped at
the wrong indent (e.g. `status`'s rationale, continued at indent 4 instead of
the deeper indent used elsewhere) — misattributing those would have silently
moved a class's review rationale into the wrong file. Each of the seven was
resolved by reading it in context, not by a smarter general heuristic; a
`yaml.safe_load` merge-back equality check against the original file (every
class, every field) caught a real corruption from the first version of the
bug (a comment fragment that leaked into a folded scalar's literal text) and
would have caught the misattribution too had the manual read-through missed
one. `Class_Type` (`schemas/planar.yaml`) — the field the plan named as the
known example of a field that resists classification — was catalogued here
and on issue #271, not resolved: splitting its ontological claim (open/closed
word class) from its typographic-rule-selector job would be a behaviour
change to the validator, out of scope for a phase whose own non-goal is "no
intended behaviour changes whatsoever."

## Open questions for Jeff

None open right now. Phase 4's five review items were closed out with Jeff
on 2026-08-16 (see Findings 25–28); Phase 5 units D and E's two open
questions were decided 2026-08-17 (see the Decisions log) and both units are
done. Phases 6–9 aren't scoped in enough detail yet to have surfaced their
own questions.
