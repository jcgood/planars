"""suprasegmental.py — retired.

Suprasegmental has been split into three focused modules as part of
issue #100 (phonological module restructuring):

  - planars/metrical.py    — metrical/prosodic domains (pitch-accent,
                             iambic foot, word-stress, tone-stress locus, etc.)
  - planars/tonosegmental.py — tonal melody overlay domains encoding
                             grammatical/semantic features (Chatino TAM
                             melodies, Cherokee superhigh-assignment)
  - planars/tonal.py       — general tonal phonological processes
                             (Cherokee H1-spreading, H3-assignment, etc.)

Update diagnostics_{lang_id}.tsv to use the appropriate new class.
"""

raise ImportError(
    "planars.suprasegmental has been retired. "
    "Use planars.metrical, planars.tonosegmental, or planars.tonal "
    "depending on the construction type. See issue #100."
)
