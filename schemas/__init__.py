"""schemas — YAML schema files for the planars project.

This directory is a Python package so that its YAML files are included
when planars is installed (e.g. via ``pip install`` in Colab).  The package
itself contains no executable code; it exists solely to make the schema
files accessible via ``importlib.resources``.

Files
-----
diagnostic_classes.yaml
    Normative schema for analysis classes: domain type, applicability,
    required diagnostic criteria, qualification rules, and collection_required.

diagnostic_criteria.yaml
    Source of truth for diagnostic criterion definitions, valid values,
    and linguistic descriptions.

languages.yaml
    Source of truth for per-language metadata.  Glottolog fields
    (name, iso639_3, family, coordinates) are written and refreshed by
    ``python -m coding lookup-lang <glottocode>``.  Project metadata
    (source, author, annotator, annotation_status, notes) is hand-edited
    by coordinators.  Valid annotation_status values: planned | in-progress
    | complete.

    Note: running ``lookup-lang`` uses PyYAML to rewrite this file, which
    strips YAML comments.  Keep essential documentation here rather than
    in the file header.

planar.yaml
    Source of truth for structural column definitions and element conventions.

terms.yaml
    Source of truth for analytical terms and chart label glossary.
"""
