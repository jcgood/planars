"""stress.py — retired.

Stress is now handled by planars/metrical.py as the ``stress_domain``
construction within the metrical class. Use:

  - construction ``stress_domain`` with criteria
    stressed{y/n/both}, obligatory, independence, left-interaction,
    right-interaction in diagnostics_{lang_id}.tsv.

See schemas/diagnostic_classes.yaml (metrical class) and issue #100.
"""

raise ImportError(
    "planars.stress has been retired. "
    "Use planars.metrical with construction 'stress_domain' instead. "
    "See issue #100."
)
