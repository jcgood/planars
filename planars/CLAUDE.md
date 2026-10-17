# planars/ package

The core library: span derivation, one analysis module per class in
`schemas/diagnostic_classes.yaml`.

- **The module contract** (`derive_*()`, the `derive` alias, `format_result()`,
  result-dict keys) and the list of shared modules are in
  `planars/__init__.py`'s docstring.
- **Each module's own docstring** says what it does and, for an analysis
  module, its qualification rule (mirroring `diagnostic_classes.yaml`). Read
  that rather than looking for a description here.
- **Values the schemas own** (keystone name, row shapes, trailing columns, a
  class's required criteria) come from `planars/schema_values.py`, never typed;
  `tests/test_no_hidden_facts.py` fails on a copy.
- **Adding an analysis module:** register it in `planars/reports.py`'s
  `_CLASS_HANDLERS` (the one list of analyses; span collection, charts and
  snapshots read it); `tests/test_smoke_modules.py` checks the contract.
