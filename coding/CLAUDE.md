# coding/ package

The coordinator tooling, run as `python -m coding <command>`.

- **What each command does:** `python -m coding registry` (one line each;
  `--command NAME` for flags, side effects and preconditions). It is built
  from `__main__.py`'s `_COMMANDS` and `data_dependency_schema/operations.yaml`.
- **What each module does:** its own docstring. Read that rather than
  looking for a description here. When a module's behaviour changes, its
  docstring changes in the same commit.

## Rules for changing the code

- **A new command** gets an entry in `__main__.py`'s `_COMMANDS`, a module
  with `build_parser()` and `main(args=None)` (dispatch parses once and
  passes `args`), and a record in `operations.yaml`. That record is what the
  code runs from: `writes_to_drive`, `writes_locally`, `edits_sources`,
  `apply_gate`, `modes`, `always_on_writes` decide what the doors let it
  write, and `preconditions` are enforced before it starts
  (`preconditions.py`).
- **Every write goes through its door.** Drive: `get_doorway()`, which
  wraps the Drive door (`drive_door.py`, checked against `sheet_spec.py`);
  retrying is the door's job, so no command wraps its own calls in a retry.
  Files in planars-data, the tooling's state files included:
  `file_door.py` (`tests/test_file_door_coverage.py` checks). GitHub
  issues: `issues.py` (`tests/test_issues.py` checks). Sharing: the helpers
  in `drive.py`, as `sheet_spec.sharing_spec` says.
- **Which columns of a tab hold criteria comes from the tab's own header;
  what each allows comes from the diagnostics YAML** (via
  `refresh_dropdowns._resolve_criterion_columns`/`_fresh_param_values`),
  never from the manifest, which is bookkeeping and goes stale. Every
  dropdown request is built by `generate_sheets.dropdown_request`. No
  dropdown or criterion note goes on a trailing column
  (`tests/mutation_checks.py`).
- **Row shapes are read from the schema, never named in code.** A command
  that branches on row shape handles element rows, pair rows
  (`restructure_sheets._get_pair_row_constructions`) and keyed rows
  (`_get_keyed_row_constructions`) explicitly, and hard-fails on anything
  else.
- **Command tests** run through `tests/command_runner.run_command` against
  the offline fake (`tests/fake_drive.py`) and the frozen data in
  `coded_data/.test_fixtures/`, changed only by
  `python -m coding capture-drive-state --apply`. Tests that need the
  frozen data skip when `coded_data/` is behind, so pull it first.
