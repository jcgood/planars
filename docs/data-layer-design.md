# Data layer: diagnosis and design rationale

**Status:** design record, not yet implemented. Written 2026-08-01.
**Implementation plan:** [data-layer-implementation-plan.md](data-layer-implementation-plan.md)

This document records *why* the data layer is being redesigned and what the
constraints are. It is the reference for design decisions in that work. Read it
before proposing changes to `coding/`, `schemas/`, or `data_dependency_schema/`.

It exists because the reasoning behind these decisions is not recoverable from
the code, and because the project has one maintainer and will eventually be
handed to someone else.

---

## The diagnosis

Every significant failure in recent project history is the same failure:
**a fact recorded in more than one place, with no single owner.**

| Incident | The two places that disagreed |
|---|---|
| #244/#245/#248 planar revert | planar Google Sheet vs. `planar_{lang}.tsv` |
| #256/#258/#259 synth0001 revert | `make_synthetic_lang.py`'s writes vs. the Sheet push mechanism |
| #266/#267 duplicate issues | ad-hoc `gh issue create` vs. `manage_issue.sh`'s find-or-edit convention |
| phrasal_accent pair-row errors | `diagnostic_classes.yaml`'s `row_type` vs. `validate_coding.py`'s hardcoded class list |
| coreference position drift | pair-row `Position_A`/`Position_B` values vs. the planar's position numbers |
| synth0001 scopal divergence | the generator's flip logic vs. `generate_sheets.py`'s consistency guard |

Not one of these is a typo or a logic error. Every one is a replicated fact
that drifted because nothing owned it. That consistency is more informative
than the count: it means the defect is structural, not incidental, and that
fixing instances one at a time will not converge.

**Corollary:** detection is not the same as prevention. Contracts, validators,
and drift checks *detect* divergence between two copies. Deriving both copies
from one source *prevents* it. Prefer derivation wherever it is available; use
detection only for facts that genuinely cannot be derived.

`coding/validate_coding.py`'s switch to `_get_pair_row_constructions()`
(2026-08-01) is the in-repo template for the derivation pattern.

---

## Why the conflation hurts: differential rates of change

`schemas/` currently mixes three kinds of information:

1. **Schema proper** — what columns exist, what values are legal
2. **Taxonomy** — what categories exist in the linguistic theory
3. **Coding conventions** — typographic and notational rules for human coders

These are not merely coexisting; they are conflated *within single fields*.
`Class_Type` is the clearest case: its name and semantics are ontological (is
this position an open class?), but its actual job in code is to select which
*typographic* rule the validator applies.

The three kinds move at very different rates:

- **Bedrock** (rarely changes): that there is a keystone; strict/loose and
  complete/partial span semantics; the structural columns.
- **Slow** (occasional): typographic conventions, bracket-wrapping, standard
  labels.
- **Fast** (constant — this is the research frontier): which diagnostic classes
  exist, what criteria they require, qualification rules, element granularity.

Conflating things that move at the *same* rate is merely inelegant. Conflating
things that move at *different* rates is a bug generator, because the fast
part's motion shears the slow part. That is exactly what produced the pronoun
bug (see below).

---

## Worked example: the pronoun bug (#270)

`v:npsubj1` and `v:obj-part` carried `Class_Type: open` while enumerating the
*complete, closed* English pronoun paradigm. This is a linguist's error — no
tooling could have decided it — and the system did surface it correctly, every
day, for four days.

But it surfaced in the **wrong register**: the warning said `element 'he' is not
ALL CAPS` when the actual finding was *a closed lexical set is coded as an open
class*. Both the coordinator and Claude read it as cosmetic and dismissed it.

The register was wrong *because* the ontological claim and the typographic rule
were welded into one field. A diagnostic's job is not only to fire; it is to
fire in terms the reader can act on. Separating (2) from (3) is what makes the
better message possible.

---

## Standing conditions

### The schema is unstable by design

The schema is itself a research output. Expect significant evolution across the
next 5–10 languages, tapering after roughly 20. Two real languages are
onboarded today (`arao1248`, `stan1293`); `nyan1308` is blocked on two modules
that do not exist yet.

**Implications:**

- There is no "stabilize the schema, then build" path. Anything built must be
  built to be edited constantly, mid-research, by the coordinator.
- The objective is not correctness at a point in time. It is **cost per schema
  change**. Today that cost is: edit a YAML, then discover over the following
  days — via production errors — which tools held private copies of the fact
  you changed.
- Design against the taper, not for it. Each new language is a discovery event.
- Amortization window is roughly 10–30 significant revisions. Enough to justify
  real mechanism; not enough to justify a heavyweight formal framework that
  would still be settling in as the schema stopped moving.

### The binding cost is comprehension, not construction

Build effort is comparatively cheap (Claude tokens plus coordinator prompt
time) and does *not* compete with language onboarding, which is linguistic
analysis work done by a different person on a different clock.

The expensive resource is **one human's ability to understand, maintain, and
eventually hand off the tooling**. Rank design options by cost-to-comprehend,
not cost-to-build. This inverts several conventional trade-offs:

- A generated, always-accurate inventory of operations is valuable primarily as
  a *succession artifact*, and only secondarily as validation.
- A hand-authored registry is *worse than none*, because a human will trust a
  stale map. A wrong map beats no map only when you know it's wrong.
- Data contracts are valuable primarily as *local documentation that cannot go
  stale*, and only secondarily as runtime checks.

### The complexity is in the topology, not the internals

Black-boxing reduces load when complexity lives *inside* components and
interfaces are simple. That is not this project. Here the complexity is almost
entirely *between* the tools: ordering, preconditions, authority, cascade.

Evidence: `CLAUDE.md` and `coding/CLAUDE.md` are very large, and their content
is overwhelmingly relational — X must run before Y, Z aborts under this
precondition, pair this command with that one, this flag bypasses that safety
gate. **Those files are already a hand-maintained topology map.** Their size
measures how much relational knowledge the system demands; the recurring
"fix docs left stale" commits measure how well hand-maintenance holds.

So the goal is not opacity. It is a **map**: relationships made explicit,
inspectable, and *generated* rather than narrated.

---

## Is this a database?

It has the requirements of a database and the implementation of a filesystem.

**Stores in play:** Google Sheets in five roles (annotation tabs, planar sheet,
diagnostics sheet, generated status sheets, embedded reference tabs); local
TSVs in three roles (annotation mirror, planar mirror, derived diagnostics);
YAML schema across two repos; six JSON state files (`manifest.json` on Drive,
`drive_config.json`, `glottolog_cache.json`, `notes_state.json`,
`pending_changes.json`, `diagnostics_drift.json`); two independent git
histories that must be reasoned about jointly; GitHub Issues, which hold real
workflow state; Google Docs for collaborator notes; plus derived artifacts
(snapshots, notebooks, PDFs).

**Scored against what a database provides:**

| Property | Status |
|---|---|
| Single logical model | **No** — distributed across YAML, tool internals, implicit convention |
| Controlled access | **No, and unfixably** — primary data entry is a human typing in a spreadsheet cell, by design |
| Constraint enforcement | **Partial, post-hoc** — dropdowns at entry, `validate-coding` after, `validate_planar` on read |
| Transactions | **No** — `restructure-sheets --apply` performs 7 sequential side effects with no rollback |
| Provenance | **Partial, uncorrelated** — git for TSVs, Drive history for Sheets, nothing joins them |
| Query | **No** — paths and globs |

### Why the answer is not "install a DBMS"

- The authoritative store for annotation **must** remain Google Sheets. That is
  the collaborator interface, and non-technical collaborators are a hard
  project requirement.
- A schema that is a research output has poor ergonomics under DBMS migrations.
- Git is doing real provenance work that would be lost or duplicated.
- The data is tiny; there is no meaningful concurrency.
- It would add a ninth store rather than removing eight.

### The correct reframe: this is a replication problem, not a storage problem

Sheets and TSVs are two replicas of the same facts, with different owners,
different write paths, and no conflict-resolution protocol. The existing
machinery is already a hand-rolled replication system:

- the daily refresh is a **sync job**
- `pending_changes.json` + `apply-pending` is a **conflict resolution step**
- the `data-overwrite` detector is a **divergence alarm**
- `notes_state.json` content hashes are **change detection**
- `data_dependency_schema/facts.yaml` is a **partial replication protocol**,
  written in prose

This reframe matters because it selects the right prior art. "Database" points
toward normalization, migrations, and query — of which only the constraint part
is needed. "Replicated stores requiring reconciliation" points toward
**authority, ordering, idempotency, and recoverability**, which is where every
serious incident has actually occurred.

The project has already independently reinvented several database properties
under pressure (`data_dependency_schema/`, `preconditions.yaml`, the
archive-before-overwrite convention, `_autocommit_data`). A single maintainer
converging on those concepts without setting out to is evidence the pressure is
real and the concepts are right. They are currently expressed as documentation
and convention rather than as anything that can fail loudly.

---

## What the API layer is (and is not)

The tools should be reconceived as a registered API onto the data layer. With
one critical correction:

**The API cannot be the only writer.** Adam's writes into Google Sheets will
never route through it, and should not. What the API can be is:

> the only **programmatic** writer, and the owner of **reconciliation** for the
> human writes it does not control.

That means its core responsibility is not "wrap the existing operations." It is:
for each fact, know which replica is authoritative, how the cascade runs, and
what happens when a multi-step operation dies halfway through.

Reads may stay promiscuous. Writes need the chokepoint, and the chokepoint needs
to know the topology.

### Derive the mechanical half; declare the semantic half

A registry is right, but only if the two halves are handled differently:

**Derive** (never hand-author — it would become the newest duplicated fact):
- function names, parameters, options, types, defaults
- generated from signatures, annotations, and docstrings

**Declare** (genuinely new information that code cannot express):
- what side effects the call has (writes Drive? files an issue? commits data?)
- whether it is idempotent
- what it assumes is already true (preconditions)
- which store it treats as authoritative when replicas disagree
- what cascade it triggers

The declared half is the higher-value half, because it is the only part that
addresses where comprehension load actually lives.

---

## Hard constraints on any implementation

1. **Adam's annotations must not change.** Annotation data is irreplaceable and
   annotation is in progress *now*. This outranks every other consideration.
2. **Build in parallel; deploy only when proven stable.** Note that "parallel"
   is straightforward for pure logic and hard for anything touching Drive —
   two systems cannot both write to live sheets. The write cutover is a
   discrete event, not a fade, and must be designed for from the start.
3. **Maximum work before touching real data**, including replicating real data
   locally as test fixtures.
4. **Deep stress testing and full test coverage before going live.**
5. **Integrity, provenance, and consistency outrank performance** in all
   trade-offs. This is a scholarly project; there is no performance pressure
   worth trading correctness for.

---

## Known gaps not yet addressed

- **Provenance is a stated top-tier value with no current mechanism.** There is
  no record of *which tool run* produced a given change. An API layer is the
  natural place to capture this nearly free.
- **No inventory of hidden facts.** Facts have been migrated from code into
  YAML reactively, one per bug. Nobody knows how many remain.
- **No atomicity for multi-step operations.** This is the source of the
  #248-class incidents.
