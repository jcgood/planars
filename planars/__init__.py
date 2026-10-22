"""planars: span derivation for morphosyntactic and phonological domains.

Each analysis module (one per class in ``schemas/diagnostic_classes.yaml``)
exposes:

- ``derive_*()`` -- takes a filled TSV ``Path`` (or ``_data=`` already
  loaded, as Colab passes it) and returns a result dict. Result dicts use
  ``complete_positions`` / ``partial_positions`` and ``*_span`` keys.
- ``derive`` -- an alias for that function, which the snapshots, the
  generated notebooks and check-codebook call.
- ``format_result(result)`` -- the result as text.

``tests/test_smoke_modules.py`` fails on a module missing any of them. Path
resolution happens at the call site, never inside the library. Where a
module departs from this shape (``nonpermutability``, ``coreference``,
``biuniqueness_deviations``: pair rows or two tabs, and their own result
keys), its own docstring says how.

Shared pieces: ``io`` (loading a filled tab), ``spans`` (span arithmetic),
``elements`` (reading a planar's Elements cell), ``position_cells`` (answers
that name positions, by number or name, and their renumbering), ``schema_values`` (values the
schemas own), ``contracts`` (DataFrame checks), ``reports`` (collecting spans
and completeness for every language), ``charts`` and ``html_report``
(rendering).
"""
