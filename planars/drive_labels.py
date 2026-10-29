"""The labels the tooling writes on Drive files and on class-sheet tabs,
and the values the Colab side looks for.

Owned here, in ``planars/``, because two sides read them: the Drive door
(``coding/drive_door.py``), which writes them on every file and tab it
makes, and ``planars/from_sheets.py``, which finds a language's sheets by
them in Colab (Phase 10 unit 11c). The door's rules about what each kind of
file must be stay in the door; only the names are here.
"""
from __future__ import annotations

# A Drive file's identity, as public Drive properties (not appProperties,
# which only the OAuth client that wrote them can read).
KIND = "planars_kind"
LANG = "planars_lang"
CLASS = "planars_class"
NAME = "planars_name"
# Set to ARCHIVED on a sheet retired or replaced (kept, read-only).
STATE = "planars_state"
ARCHIVED = "archived"

# Kinds of file the Colab side looks for.
CLASS_SHEET = "class_sheet"
PLANAR_SHEET = "planar_sheet"

# A class-sheet tab's labels, as Sheets developer metadata on the tab
# (document visibility, so any coordinator's client reads them): its kind
# and its name, which stays put if someone renames the tab by hand.
TAB_KIND = "planars_tab_kind"
TAB_NAME = "planars_tab"
CONSTRUCTION_TAB = "construction"
