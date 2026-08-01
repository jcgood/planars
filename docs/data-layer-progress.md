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

**Phase:** 0a / 2 (started 2026-08-01)
**Live Drive writes performed:** none. Permitted from Phase 9 only.
**Adam's annotation data touched:** none.

### Status by unit

| Unit | Status | Commit |
|---|---|---|
| Design record + plan written | done | `7b995b9`, `f20478e` |
| Phase 2 — hidden-fact inventory | **done** → `docs/hidden-facts-inventory.md` | `e27bbe3` |
| Phase 0a — protocol surface enumeration | **done** → `docs/drive-protocol-surface.md` | `b978101`..`46bf833` |
| Phase 0a — protocol proposal reviewed | **done** — accepted, see decisions log | — |
| Phase 0a — `capture-drive-state` command | **done** | `c87ae7d` |
| Phase 0a — fixture capture run (read-only, live) | **done** — 29 sheets, 80 tabs | `b40cd64` |
| Phase 0a — fake backend | not started | — |
| Phase 0b/1 — file 1 of 11 (pattern-setting migration) | not started | — |
| Phase 0b/1 — files 2–11 | not started | — |
| Phases 3–9 | not started | — |

### In flight

*(nothing — both launched agents completed 2026-08-01; scope verified, only
their own doc files touched, `coded_data/` untouched, tree clean)*

---

## Next action

**Not blocked.** In order:

1. Review the proposed protocol in `docs/drive-protocol-surface.md` (its
   "proposed minimal protocol" section) and make the design call on its shape.
   Not delegable — see *Working with agents* in the plan. Note it flags four
   independent reimplementations of "create-or-update a Drive file" and two of
   "get-or-create folder" as collapse candidates; decide whether collapsing
   them is in scope for the seam or a follow-on, since collapsing changes
   behavior and there are no goldens yet.
2. Write `python -m coding capture-drive-state` (read-only). It must record
   **raw API responses**, not just parsed content — the fake is to be built
   from recorded real responses rather than from the gspread docs.
3. Run it once against live Drive. Read-only; safe. Commit fixtures.
4. Build the fake from those recordings. Smoke-test every protocol operation.
   Pay particular attention to the subtleties the enumeration flagged:
   ragged-row padding, `update()` range and `raw=` semantics, `worksheets()`
   ordering, `batch_update` vs `values_batch_update` (two different endpoints
   behind similar names), and the 1-indexing-varies-by-method table.
5. Migrate **one** file end-to-end using the per-file procedure in the plan
   (pre-migration dry-run baseline → migrate → diff against fake → capture
   goldens → human review of the `--apply` mutation log). This establishes the
   pattern; the remaining ten then go to agents.

---

## Decisions log

**2026-08-01 — Phases 0 and 1 interleaved rather than sequenced.** As first
written they were circular: goldens need the seam, and safely migrating to the
seam needs goldens. Resolved by building infrastructure first (0a, no caller
changes) then migrating one file at a time with goldens captured immediately
after each. See `f20478e`.

**2026-08-01 — the fake is built from recorded real responses.** Not from the
gspread documentation. Its subtleties (1-indexing, `get_all_values` padding,
`update` range semantics) are what gets guessed wrong, and a wrong fake would
silently invalidate every test built on it.

**2026-08-01 — human review of `--apply` mutation logs before they become
goldens.** Write paths have no pre-migration baseline to diff against, so this
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

**2026-08-01 — protocol proposal accepted as the basis for the seam.** Its six
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

**Deferred:** collapsing the four duplicate "create-or-update a Drive file"
implementations and the two "get-or-create folder" implementations. They are
genuine duplication and belong in the inventory, but collapsing them changes
behaviour and there are no goldens yet, so they wait until after 0b/1 rather
than riding along with the seam migration.

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
generation — that wants goldens first, so it belongs to Phase 3. Catalogued in
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
