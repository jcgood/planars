"""aspiration.py — retired.

Aspiration is now handled by planars/segmental.py as a construction type
within the segmental class. Use:

  - construction ``aspiration_prominence`` for the blocked-span
    prosodically-conditioned case (e.g. English).
  - construction ``aspiration_fusion`` for aspiration-related segmental
    process types (e.g. Yukuna ch. 11).

See schemas/diagnostic_classes.yaml (segmental class) and issue #100.
"""

raise ImportError(
    "planars.aspiration has been retired. "
    "Use planars.segmental with construction 'aspiration_prominence' or "
    "'aspiration_fusion' instead. See issue #100."
)
