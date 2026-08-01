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

Current structure: a full-copy mirror of `stan1293` (38 positions, keystone at 30, no structural drop — chosen to avoid structural-drop noise while validating the biuniqueness/allomorphy mechanism, see issue #254) with ~25% of criterion values flipped. Default (non-full-copy) mode drops ~25% of non-keystone positions instead, giving a genuinely different planar structure; that mode remains available for other multi-language test cases.

```bash
python tests/make_synthetic_lang.py                        # dry run — show what would be written
python tests/make_synthetic_lang.py --apply                # regenerate synth0001 (random position drop)
python tests/make_synthetic_lang.py --full-copy --apply    # regenerate with no position drop (current mode)
python tests/make_synthetic_lang.py --clean --apply        # remove synth0001
```

`--apply` (not `--clean`) also pushes the regenerated planar structure to the live Drive planar spreadsheet — without this, the next scheduled `import-planar --apply` would silently revert the regeneration back to the old structure (issue #256's 2026-07-31 incident: this push was missing, and the live Sheet stayed stale long enough for a downstream cascade to overwrite local changes before it was caught).

`synth0001` is committed to `coded_data/` (in the `planars-data` repo). Regenerate it only if the `stan1293` planar structure changes substantially and the multi-language tests need to be re-baselined.
