# CCDB batch: all structures through planarsviz

Written by `scripts/planarsviz_ccdb_batch.py`; each structure's full output is in the `.log` beside this file.

| Structure | Positions | Tests | Families | Export | Charts | Minutes |
|---|---|---|---|---|---|---|
| arao1248_verbal | 18 | 19 | 2 | ok | 54 files for 54 of 54 charts | 0.7 |
| ayau1235_verbal | 31 | 30 | 8 | ok | 75 files for 75 of 75 charts | 1.3 |
| cent2127_verbal | 21 | 19 | 3 | ok | 58 files for 58 of 58 charts | 0.8 |
| chac1251_nominal | 12 | 26 | 4 | ok | 61 files for 61 of 61 charts | 0.8 |
| chac1251_verbal | 28 | 38 | 29 | ok | 91 files for 91 of 91 charts | 3.8 |
| cher1273_verbal | 24 | 21 | 8 | ok | 71 files for 71 of 71 charts | 1.1 |
| dura0000_nominal | 13 | 19 | 5 | ok | 65 files for 65 of 65 charts | 0.8 |
| dura0000_verbal | 29 | 27 | 40 | ok | 90 files for 90 of 90 charts | 2.4 |
| hupd1244_nominal | 15 | 12 | 2 | ok | 53 files for 53 of 53 charts | 0.6 |
| hupd1244_verbal | 32 | 15 | 3 | ok | 55 files for 55 of 55 charts | 0.7 |
| iyoj1235_verbal | 46 | 28 | 22 | ok | 70 files for 70 of 70 charts | 2.6 |
| kaya1330_verbal | 32 | 15 | 7 | ok | 72 files for 72 of 72 charts | 0.9 |
| kiow1266_verbal | 39 | 17 | 5 | ok | 65 files for 65 of 65 charts | 0.9 |
| mart1259_verbal | 27 | 12 | 4 | ok | 61 files for 61 of 61 charts | 0.8 |
| moco1246_verbal | 20 | 22 | 7 | ok | 74 files for 74 of 74 charts | 1.0 |
| siks1238_verbal | 14 | 32 | 31 | ok | 83 files for 83 of 83 charts | 1.7 |
| sout2991_verbal | 42 | 20 | 3 | ok | 57 files for 57 of 57 charts | 1.2 |
| teot1238_nominal | 20 | 18 | 9 | ok | 67 files for 67 of 67 charts | 0.8 |
| teot1238_verbal | 28 | 21 | 12 | ok | 71 files for 71 of 71 charts | 0.9 |
| yucu1253_verbal | 21 | 24 | 7 | ok | 71 files for 71 of 71 charts | 1.0 |
| zenz1235_verbal | 21 | 28 | 5 | ok | 64 files for 64 of 64 charts | 0.8 |

## What failed

Nothing.

## Charts a structure has none of (the bundle had nothing for them)

None.

## Worth a look

- **arao1248_verbal**: only 2 families: exemplary and conflict-group charts have little to show
- **ayau1235_verbal**: text the standard PDF fonts can't draw (ɛ): the renderer draws the charts that show it with Quartz (cairo off a Mac); check their fonts look right
- **hupd1244_nominal**: only 2 families: exemplary and conflict-group charts have little to show
- **iyoj1235_verbal**: 46 positions: check label crowding
- **moco1246_verbal**: text the standard PDF fonts can't draw (ʔ): the renderer draws the charts that show it with Quartz (cairo off a Mac); check their fonts look right
- **sout2991_verbal**: 42 positions: check label crowding
