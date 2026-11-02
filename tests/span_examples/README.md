# Worked examples of the span rules

Each example is a small made-up language, a few filled cells, and the spans
the agreed span rule should give for them. `tests/test_span_examples.py` runs
every class's code on every example and fails if the spans differ. They are
written while a span rule is reviewed with the domain expert (coordinator
guide § "Reviewing a span rule with the domain expert", step 5), so they
record what the rule means, worked out by hand from the rule, never copied
from what the code gives. Later they are the test any rewrite of the span
code must pass (Phase 11, `docs/data-layer-implementation-plan.md`).

## Layout

One folder per example, laid out like a language in `coded_data/`:

```
tests/span_examples/{class}/{example}/
    lang_setup/planar_{example}.tsv     the planar structure (Language_ID = {example})
    {class}/{construction}.tsv          one or more filled tabs, as imported
    expected_spans.tsv                  the spans the rule should give
```

- `{example}` starts with `synth` (reserved for made-up languages) and says
  what it shows, e.g. `synth_na_blocks`.
- The tabs have the same columns as the class's imported TSVs. Keep them
  small: just the positions and elements the point needs. A class whose tabs
  read another tab (a feeder such as `element_prescreening`) needs that tab too.
- `expected_spans.tsv` has the columns `Construction`, `Test_Labels`,
  `Span_Key`, `Left_Edge`, `Right_Edge`, `Why`, and lists **every** span the
  class reports for each span-producing tab, one row each. `Why` says in plain
  words why the rule gives that span; it is not compared.

When an example fails, the test prints the spans the code gives, in the same
columns, so the two can be set side by side.

## What to cover

For each class, at least one example per thing the rule decides: each value
a criterion can take (`y`, `n`, `both`, `na`, `?`, blank), complete against
partial positions and strict against loose spans where the class has them,
and each case the review settled.
