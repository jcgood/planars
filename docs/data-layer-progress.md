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
| Phase 2 — hidden-fact inventory | in flight (agent) | — |
| Phase 0a — protocol surface enumeration | in flight (agent) | — |
| Phase 0a — `capture-drive-state` command | not started | — |
| Phase 0a — fixture capture run (read-only, live) | not started | — |
| Phase 0a — fake backend | not started | — |
| Phase 0b/1 — file 1 of 11 (pattern-setting migration) | not started | — |
| Phase 0b/1 — files 2–11 | not started | — |
| Phases 3–9 | not started | — |

### In flight

Two Sonnet agents launched 2026-08-01:

1. **Phase 2 inventory** → produces `docs/hidden-facts-inventory.md`.
   Read-only analysis of `coding/` and `planars/`; forbidden from fixing
   anything. Commits, does not push.
2. **Protocol surface enumeration** → produces
   `docs/drive-protocol-surface.md`. Static reading of the eleven
   Drive-touching files plus `drive.py`; produces an inventory and a *proposed*
   protocol only, explicitly forbidden from writing the protocol module or
   modifying any source file. Commits, does not push.

If a session ends before these land, check for those two files and any
uncommitted work in the repo before relaunching — the agents were instructed to
write incrementally, so partial output may exist.

---

## Next action

**Blocked on:** the protocol-surface enumeration landing.

Once it does, in order:

1. Review the proposed protocol; make the design call on its shape (this is a
   design decision, not delegable — see *Working with agents* in the plan).
2. Write `python -m coding capture-drive-state` (read-only). It must record
   **raw API responses**, not just parsed content — the fake is to be built
   from recorded real responses rather than from the gspread docs.
3. Run it once against live Drive. Read-only; safe. Commit fixtures.
4. Build the fake from those recordings. Smoke-test every protocol operation.
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

**2026-08-01 — agent briefs must require incremental *commits*, not just
incremental writes.** The protocol-enumeration agent stalled roughly three
files into an eleven-file pass with all of its analysis uncommitted in the
working tree. It was resumed rather than relaunched (context intact, far
cheaper) and instructed to commit per file. Telling an agent to "write
incrementally" is not enough — unstaged work is not recoverable work. Folded
into the plan's *Working with agents* section for all future briefs.

---

## Open questions for Jeff

*(none currently — Phase 3 and 4 will raise the research/administrative
classification and the authority assignments)*
