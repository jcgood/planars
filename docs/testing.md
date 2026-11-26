# Testing

`pytest` runs the suite on every processor core at once (`addopts = "-n auto"` in `pyproject.toml`, through `pytest-xdist`): about 3.5 minutes rather than 11.5. That is safe because every test keeps its files in its own temporary folder (`tests/conftest.py`). Two things follow for a new test: it must not write into the repository or `coded_data/` itself, and a list of test cases built from a set must be sorted (each process collects the tests and they must agree; a `set` comes out in a different order each time). Run with `-n 0` to debug one test in a single process.

## Regression testing

Snapshot tests verify that analysis output does not change unexpectedly. Snapshots live in `tests/snapshots/` and cover every analysis with a filled TSV in `coded_data/`: `generate_snapshots.py` builds its list of analyses from `_CLASS_HANDLERS` in `planars/reports.py`, so a newly registered analysis is covered without editing this page.

```bash
python generate_snapshots.py   # regenerate baselines from current output
python check_snapshots.py      # verify current output matches baselines
```

Run `check_snapshots.py` after any change to analysis logic in `planars/` before committing. If the change is intentional, regenerate the baselines with `generate_snapshots.py` and commit the updated snapshots alongside the code change.

The snapshots exercise every analysis module registered in `_CLASS_HANDLERS` (`planars/reports.py`) and the shared code they call, `planars/spans.py` and `planars/io.py`. A change to any of these should be verified with `check_snapshots.py`.

Snapshots record what the code gives today; a snapshot diff only says that output moved. **Worked examples** record what a span rule *should* give: small made-up languages in `tests/span_examples/` with the spans worked out by hand when the rule was agreed with the domain expert, checked by `tests/test_span_examples.py`. A failing example means the code is wrong, not the example (layout: `tests/span_examples/README.md`).

---

## Synthetic test language

`coded_data/synth0001/` is a synthetic second-language dataset used for testing multi-language code paths. It is not real data.

Current structure: a full-copy mirror of `stan1293` (38 positions, keystone at 30, no structural drop — chosen to avoid structural-drop noise while validating the biuniqueness/allomorphy mechanism, see issue #254) with ~25% of criterion values flipped. Default (non-full-copy) mode drops ~25% of non-keystone positions instead, giving a genuinely different planar structure; that mode remains available for other multi-language test cases.

```bash
python tests/make_synthetic_lang.py                        # dry run — show what would be written
python tests/make_synthetic_lang.py --apply                # regenerate synth0001 (random position drop)
python tests/make_synthetic_lang.py --full-copy --apply    # regenerate with no position drop (current mode)
python tests/make_synthetic_lang.py --clean --apply        # remove synth0001
```

It writes only local files; commit them in planars-data, and the daily refresh brings the planar Sheet up to date (`python -m coding sync-planar --lang synth0001 --apply` to do it now).

`synth0001` is committed to `coded_data/` (in the `planars-data` repo). Regenerate it only if the `stan1293` planar structure changes substantially and the multi-language tests need to be re-baselined.
