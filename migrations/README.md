# migrations/

One-time data migration scripts. These are not part of the ongoing workflow — each script was run once to transform existing data and is kept here for historical reference.

## Conventions for new migration scripts

Every migration script should have a module-level docstring that documents:

- **What it does**: the transformation performed (old → new)
- **Why it was needed**: the motivating change (e.g., renamed field, restructured sheet)
- **When it was run**: approximate date or commit reference
- **How to run it**: the exact command(s), including dry-run and apply modes
- **What to check afterward**: any validation steps to confirm the migration worked

Example structure:

```python
"""One-time migration: <short description of transformation>.

Motivation: <what changed that made this necessary>.
Run: <approximate date or commit, e.g., "March 2026, after commit abc1234">

Usage:
    python migrations/<script>.py           # dry run
    python migrations/<script>.py --apply   # apply changes

Post-run checks:
    python -m coding integrity-check
"""
```

Dry-run mode (default) should always be supported and should print what would change without modifying anything.
