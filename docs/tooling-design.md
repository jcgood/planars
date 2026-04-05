# Tooling design principles

This document records the design philosophy behind the planars coordinator tooling and the checklist Claude should apply when proposing or implementing any change to a coordinator-facing workflow. It is the companion to the "Coordinator context and tooling philosophy" section in CLAUDE.md — that section states the goals; this document makes them operational.

## Who the coordinator is

The coordinator is a scientist doing work that a well-funded project would distribute across multiple dedicated roles: annotator, data manager, tool maintainer, and analyst. This is not a software engineering team. Every design decision should be evaluated against the question: **can one non-developer person follow this reliably, without assistance, after a gap of weeks?**

## The coordinator UX checklist

**Before proposing or implementing any fix to a coordinator-facing workflow, apply this checklist.** "Coordinator-facing" means: error messages, GitHub issue bodies, `apply-pending` prompts, `integrity-check` output, generated Claude prompts, script dry-run output, and documentation steps.

1. **What does the coordinator see at each step?** Trace the workflow from the outside — not what the code does, but what the coordinator reads in the terminal or GitHub. Is the sequence of visible outputs clear and complete?

2. **Is anything required from memory or assumed knowledge?** If the coordinator must remember a prerequisite, a prior step, or a command not shown in the current output, that is a design flaw. The output at each step should contain everything needed to take the next step.

3. **What happens if they skip a step or forget?** Does the system detect and surface the omission, or does it silently proceed in a broken state? Prefer designs where skipping a step produces a visible, actionable error over designs where it produces a plausible-looking but wrong outcome.

4. **Does the system verify completion, or trust the coordinator's recollection?** Whenever a pending action can be "resolved" by the coordinator saying "yes I did it," ask whether the system can verify this independently (e.g., by checking a Google Sheet, a file, or a git status). Prefer verification over trust.

5. **Are all commands in the output fully runnable as written?** Every command shown to the coordinator must be the full `python -m coding <command> [flags]` form (or a `make` alias). Never use abbreviated references like "run sync-params" or "use generate-sheets." The coordinator should be able to copy-paste without knowing the CLI structure from memory.

## Design patterns that follow from the checklist

**Errors are instructions.** Every error or warning in `integrity-check`, `check-codebook`, or any script should end with a `→ run:` line showing the exact command to fix the problem. Reporting a problem without a next step is incomplete.

**The GitHub issue IS the instruction.** When a workflow files an issue, the issue body should contain everything the coordinator needs to resolve it: what happened, why it matters, and the exact sequence of commands to run. The coordinator should not need to consult the guide for a routine issue.

**Pending entries stay open until verified.** A pending change in `apply-pending` should not be marked resolved until there is evidence of completion — not just coordinator confirmation. For changes that cannot be automated (e.g., manually adding a Sheet tab), check the actual artifact (Sheet, file, manifest) before closing.

**Dry-run by default; explicit opt-in for destructive actions.** Any command that archives, overwrites, or deletes should require an explicit flag (`--apply`, `--force`) and should describe the consequences in the dry-run output before the coordinator opts in.

**Full commands everywhere.** This applies to: error messages, issue bodies, `apply-pending` prompts, `integrity-check` next-step lines, generated Claude prompts, and all documentation steps. Use `python -m coding generate-sheets --force`, not "generate-sheets --force" or "run the generate-sheets command with force."

## What Claude's role is in this workflow

Claude is part of the operational workflow, not just a coding assistant. The qualification-rule update workflow, schema audit sessions, and complex restructuring steps are all designed to hand off to Claude with full context pre-assembled by scripts. When implementing a new workflow step, consider whether the judgment-requiring part belongs in a generated Claude prompt rather than in coordinator documentation. Documentation that says "then decide X based on Y" is a candidate for a Claude handoff.

When Claude makes a mistake in this domain — proposing a fix that looks correct at the code level but fails at the coordinator-experience level — it is usually because the analysis started from "what does this function do?" rather than "what does the coordinator see, and where can they be misled?" The checklist above is the corrective. Apply it before proposing, not after being corrected.
