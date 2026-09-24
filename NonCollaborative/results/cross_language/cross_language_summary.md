# Cross-language summary

One row per structure. Positions in the last two columns are relative to the root (root = 0).
`p placement` / `p layers`: one-sided p-value that chance gives as few families as observed, on the
span-placement and arbitrary-layers nulls. `Confl. betw.`: conflicting span pairs that fall wholly
across the morphosyntax/phonology divide. * = not from CCDB (Chichewa).
Written by scripts/analysis/export_cross_language.py; do not edit by hand.

| Structure | Pos. | Tests | Spans | Fam. | Fam. syn. | Fam. phon. | p placement | p layers | Confl. betw. | Confl. | Strongest edge | Top span |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Araona (verbal) | 18 | 19 | 9 | 2 | 2 | 2 | 0.0034 | 0.0036 | 0 | 3 | left -2 | -2..9 |
| Ayautla Mazatec (verbal) | 31 | 30 | 14 | 8 | 3 | 6 | 0.0412 | 0.0446 | 4 | 15 | left -4 | -4..9 |
| Blackfoot (verbal) | 14 | 32 | 17 | 31 | 13 | 2 | 0.927 | 0.7042 | 8 | 35 | left -3 | -3..7 |
| Central Alaskan Yupik (verbal) | 21 | 19 | 8 | 3 | 3 | 1 | 0.1618 | 0.141 | 0 | 5 | left 0 | 0..14 |
| Chichewa (verbal) * | 22 | 95 | 26 | 69 | 16 | 6 | 0.335 | 0.2866 | 12 | 65 | left -5 | -4..7 |
| Chorote (verbal) | 46 | 28 | 21 | 22 | 4 | 5 | 0.0852 | 0.0174 | 27 | 41 | left -2 | -2..0 |
| Chácobo (nominal) | 12 | 26 | 11 | 4 | 3 | 2 | 0.0524 | 0.036 | 3 | 14 | right +8 | -1..0 |
| Chácobo (verbal) | 28 | 38 | 22 | 29 | 8 | 9 | 0.1272 | 0.0882 | 4 | 32 | left -1 | -1..2 |
| Hup (nominal) | 15 | 12 | 7 | 2 | 2 | 1 | 0.3884 | 0.1756 | 0 | 2 | left 0 | 0..10 |
| Hup (verbal) | 32 | 15 | 10 | 3 | 2 | 1 | 0.045 | 0.0484 | 2 | 5 | left -4 | 0..14 |
| Kiowa (verbal) | 39 | 17 | 12 | 5 | 2 | 4 | 0.132 | 0.0692 | 4 | 11 | right +7 | 0..4 |
| Martinican (verbal) | 27 | 12 | 8 | 4 | 4 | 1 | 0.7598 | 0.3526 | 0 | 4 | left -14 | -1..2 |
| Mebengokre (verbal) | 32 | 15 | 10 | 7 | 7 | 1 | 0.3852 | 0.4684 | 0 | 12 | right 0 | -2..0 |
| Mocoví (verbal) | 20 | 22 | 11 | 7 | 6 | 3 | 0.3272 | 0.275 | 3 | 11 | left -1 | -1..0 |
| Oklahoma Cherokee (verbal) | 24 | 21 | 15 | 8 | 4 | 2 | 0.0708 | 0.0384 | 22 | 36 | right +10 | -10..11 |
| San Martín Duraznos Mixtec (nominal) | 13 | 19 | 10 | 5 | 3 | 2 | 0.2704 | 0.3246 | 8 | 17 | left -7 | -1..0 |
| San Martín Duraznos Mixtec (verbal) | 29 | 27 | 21 | 40 | 17 | 4 | 0.617 | 0.4858 | 28 | 56 | left -16 | -1..0 |
| South Bolivian Quechua (verbal) | 42 | 20 | 15 | 3 | 2 | 2 | 0.0 | 0.0 | 4 | 11 | left 0 | 0..6 |
| Teotitlán del Valle Zapotec (nominal) | 20 | 18 | 11 | 9 | 2 | 3 | 0.756 | 0.7532 | 10 | 16 | left -2 | 0..1 |
| Teotitlán del Valle Zapotec (verbal) | 28 | 21 | 11 | 12 | 3 | 5 | 0.9582 | 0.9486 | 7 | 15 | left -2 | -2..0 |
| Yukuna (verbal) | 21 | 24 | 15 | 7 | 5 | 3 | 0.038 | 0.0174 | 12 | 43 | left 0 | 0..6 |
| Zenzontepec Chatino (verbal) | 21 | 28 | 11 | 5 | 2 | 3 | 0.1388 | 0.1714 | 8 | 16 | left -6 | -3..0 |

## Across all structures

Structures share test batteries, authors and in some cases language families, so neither
figure below is a test on independent cases.

| Null | Which tests | Below / above / at median | Sign test p | Fisher p |
|---|---|---|---|---|
| span placement | all | 17 / 5 / 0 | 0.00845 | 2.738e-05 |
| span placement | syntax side | 15 / 3 / 4 | 0.003769 | 2.262e-05 |
| span placement | phonology side | 8 / 6 / 8 | 0.395264 | 0.8869611 |
| arbitrary layers | all | 19 / 3 / 0 | 0.000428 | 7.6e-07 |
| arbitrary layers | syntax side | 19 / 2 / 1 | 0.000111 | 8.37e-06 |
| arbitrary layers | phonology side | 9 / 2 / 11 | 0.032715 | 0.81761923 |
