# Testing

## Regression testing

Snapshot tests verify that analysis output does not change unexpectedly. Snapshots live in `tests/snapshots/` and cover the `ciscategorial`, `subspanrepetition`, and `noninterruption` analyses across all filled TSVs in `coded_data/`. Other analyses do not yet have snapshot coverage.

```bash
python generate_snapshots.py   # regenerate baselines from current output
python check_snapshots.py      # verify current output matches baselines
```

Run `check_snapshots.py` after any change to analysis logic in `planars/` before committing. If the change is intentional, regenerate the baselines with `generate_snapshots.py` and commit the updated snapshots alongside the code change.

The snapshot runner covers these modules (changes to any of them should be verified):
- `planars/ciscategorial.py`
- `planars/subspanrepetition.py`
- `planars/noninterruption.py`
- `planars/spans.py`
- `planars/io.py`

---

## Synthetic test language

`coded_data/synth0001/` is a synthetic second-language dataset used for testing multi-language code paths. It is not real data.

It was derived from `stan1293` by dropping 9 positions and flipping approximately 25% of criterion values, giving a genuinely different planar structure (28 positions vs. 37, keystone at position 23 vs. 30).

```bash
python tests/make_synthetic_lang.py                    # dry run — show what would be written
python tests/make_synthetic_lang.py --apply            # regenerate synth0001
python tests/make_synthetic_lang.py --clean --apply    # remove synth0001
```

`synth0001` is committed to `coded_data/` (in the `planars-data` repo). Regenerate it only if the `stan1293` planar structure changes substantially and the multi-language tests need to be re-baselined.
