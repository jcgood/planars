"""schemas — YAML schema files for the planars project.

This directory is a Python package so that its YAML files are included
when planars is installed (e.g. via ``pip install`` in Colab).  The package
itself contains no executable code; it exists solely to make the schema
files accessible via ``importlib.resources``.

Each file's own header comments say what each of its keys means; this list
says which file owns what. After editing any of them, run
``python -m coding integrity-check`` and ``python -m coding check-codebook``.

Files
-----
diagnostic_classes.yaml
    Normative schema for the linguistic content of analysis classes: domain
    type (morphosyntactic / phonological / indeterminate), whether a class is
    universal or conditional, its constructions and their row shape
    (``row_type``: element rows, ``pair_rows`` or ``keyed_rows``; feeder tabs
    say ``produces_spans: false``), required criteria, keystone settings
    (``keystone_active_default``, ``keystone_na_criteria``) and the
    ``span_rule``. A rule change must also reach the module's
    docstring and comments (coordinator guide, "Updating a span rule").

diagnostic_classes_status.yaml
    Process/tracking state for the same classes: status, criterion_set_status,
    collection_required, span_rule_hash, sheet_instructions,
    module_pending and include_planar_reference_tab. Split out from diagnostic_classes.yaml in
    Phase 3 of the data layer redesign (issue #271) because the two move at
    different rates. coding/schemas.py's load_diagnostic_classes() merges
    both files by class name at read time. ``status`` values are listed in
    the file's header; only a coordinator promotes a class to ``stable``
    (CLAUDE.md § Conventions, "Analysis status").

diagnostic_criteria.yaml
    Source of truth for diagnostic criterion definitions, valid values, and
    linguistic descriptions (``[PLACEHOLDER]`` marks a missing description,
    ``[NEEDS REVIEW]`` a provisional rule).  Key machine-readable entries:
      always_allowed_values: values every criterion accepts on top of its
        own list (currently [na, ?]). There is no default list for a
        criterion with no values. ``untestable`` is accepted only where a
        language's diagnostics file lists it.
      value_placeholders: allowed values that stand for an entry rather than
        a choice (``<free_text>``, ``<position_names>`` free entry: may be
        blank, kept as typed; ``<position_number>``). A criterion with one
        gets no dropdown (``coding/schemas.py``, ``dropdown_values``).

issue_labels.yaml
    The one definition of the project's GitHub issue labels (name, colour,
    short description, meaning, who files it). Read by ``coding/issues.py``,
    which refuses any label not listed; GitHub's labels and CLAUDE.md's
    Labels table are both rebuilt from it (see the file's header). Not used
    in Colab.

languages.yaml
    Source of truth for per-language metadata.  Glottolog fields
    (name, iso639_3, family, coordinates) are written and refreshed by
    ``python -m coding lookup-lang <glottocode>``.  Project metadata
    (source, author, annotator, annotation_status, examples, notes) is
    hand-edited by coordinators.  Valid annotation_status values: planned |
    in-progress | complete.  ``examples`` is how the language's examples are
    written, one of planar.yaml's ``example_styles`` (glossed, or unglossed
    for a language that is its own metalanguage, i.e. English); it decides
    which example columns its annotation tabs carry and how the chapters
    print its examples.  Always edit this file, never the copy in the manifest
    (generate-sheets and import-sheets write that copy).  No email addresses
    here (this repo is public): the annotator's address lives in private
    planars-data, ``coded_data/people.yaml``, keyed by the ``annotator``
    name, and is read only through ``coding/people.py``.
    Key machine-readable entries:
      required_meta_fields: meta fields integrity-check warns about when blank
        (currently [source, author]).

    Note: running ``lookup-lang`` uses PyYAML to rewrite this file, which
    strips YAML comments.  Keep essential documentation here rather than
    in the file header.

planar.yaml
    Source of truth for structural column definitions and element conventions:
    the planar file's columns, the keystone's name, each row shape's columns
    and key, the Status tab, the trailing columns appended to annotation
    tabs (``trailing_columns``, and per example style the ones a language's
    tabs leave out, ``example_styles``; to add one, edit it and run
    ``update-sheets --apply``), the locked tabs (``locked_tabs``) and the
    fixed sentences on Instructions tabs (``sheet_text``). Read in one
    place, ``planars/schema_values.py`` (locked tabs:
    ``coding/locked_tabs.py``; sheet text: ``coding.schemas.sheet_text``).

terms.yaml
    Source of truth for analytical terms (keystone, partial, complete,
    strict, loose), the chart label glossary and the retired terms (words
    the project no longer uses; ``tests/test_no_hidden_facts.py`` fails if
    one reappears). ``span_label_map`` is read by planars/reports.py.

diagnostics_{lang_id}.yaml  (per-language, lives in coded_data/{lang_id}/lang_setup/)
    Per-language source of truth for which analysis classes, constructions, and
    diagnostic criteria apply to a language: its one diagnostics file, read
    by every command (a TSV copy beside it was deleted 2026-10-27).  Format::

        language: stan1293
        classes:
          ciscategorial:
            constructions: [general]
            criteria:
              V-combines: [y, n]
              N-combines: [y, n]
            notes: "optional free-text notes"   # omit if not needed

    Rules:
      - ``constructions`` is a non-empty list of construction names.
      - ``general`` must be the only construction when used.
      - ``criteria`` is an ordered dict of criterion_name → allowed_values list.
        Every criterion lists its values; one without is an error.
      - ``construction_criteria`` (a dict of construction → criteria) replaces
        ``criteria`` when a class's constructions have different criteria;
        each tab then shows only its own.
      - Allowed values always include ``na`` and ``?`` implicitly; only list the
        domain-meaningful values (e.g. ``[y, n]`` or ``[y, n, both]``).
      - A criterion missing from the file means it doesn't apply to the
        language; present but blank on a sheet means not yet coded.
      - ``notes`` is an optional string (class-level).
    Workflow:
      - Coordinators edit this YAML directly, then commit and push it in
        planars-data.
      - When the criterion columns change, ``sync-params --apply`` carries
        the change to existing sheets.
      - The diagnostics Sheet is a read-only copy of this file (the daily
        refresh rebuilds it); an annotator proposes a change on the
        language's proposal sheet, and ``accept-proposal`` writes it here.
    Validated by ``coding/validate_diagnostics.py:validate_diagnostics_yaml()``.
"""
