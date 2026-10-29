"""Data contract for the Drive manifest (Phase 6 boundary 4, issue #271).

Boundary 4 of the plan's four candidates, and the odd one out among them:
the manifest is a dict/JSON structure, not a DataFrame, so this uses
pydantic rather than the pandera used in `planars/contracts.py` and
`coding/contracts.py`.

Since unit 11c (2026-10-28) no command reads the manifest: it is a copy
rebuilt whole from the ID file and the sources by `coding/manifest_copy.py`
for the published Colab notebooks, and this contract, with the manifest,
goes in 11c-5. The rest of this docstring is the reasoning from when it was
written.

**Deliberately far more permissive than the other three boundaries.**
`load_manifest()` (`coding/drive.py`) was called near the
start of nearly every `coding/` command — the single highest-blast-radius
function in the project. A schema built from one static fixture
(`coded_data/.test_fixtures/drive_state/manifest.json`, three languages, captured
2026-08-01) and then allowed to raise would risk exactly the failure mode
this whole data layer effort exists to prevent: a *loud, self-inflicted*
outage on real data that was never actually wrong, just unmodeled — no live
Drive access is permitted before Phase 9 to check this model against what
the manifest actually looks like today. See the 2026-08-17 decisions-log
entry in `docs/data-layer-progress.md` for the full reasoning and the
options considered.

So: every field here is `Optional`, `extra="allow"` at every level (an
unrecognized key is never a violation), and nested structures the manifest
grows over time (`sheets`, `planar`, `meta`, `glottolog`) are typed as loose
`dict`s rather than fully modeled — the fields listed are current
documentation of what a language entry usually carries (from the same
fixture), not a claim about what it must carry. `check()`
returns problems as a list of strings rather than raising; callers decide
what to do with them:

- the Drive door (`coding/drive_door.py`, through
  `sheet_spec.content_problems`) — checks every manifest write before it is
  made (Phase 10 unit 5f, 2026-10-19; until then `upload_manifest()`
  printed a warning nobody saw). While the manifest is in watch mode a
  violation is written anyway and reported in the `door-violation` issue;
  it is refused only once the manifest moves to enforce, which happens only
  after real writes have passed the check (design § 4), so the risk above
  is tested on live data first. It is now the only caller: integrity-check's
  MANIFEST SHAPE section, which read the manifest back from Drive, was
  dropped in 11c (the door already checks the copy as it is written).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel, ValidationError


class GlottologInfo(BaseModel):
    """Documentation only -- see module docstring."""
    model_config = ConfigDict(extra="allow")
    name: Optional[str] = None
    iso639_3: Optional[str] = None
    family: Optional[str] = None
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None


class LanguageMeta(BaseModel):
    """Documentation only -- see module docstring."""
    model_config = ConfigDict(extra="allow")
    glottocode: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    annotator: Optional[str] = None
    annotator_email: Optional[str] = None
    annotation_status: Optional[str] = None
    notes: Optional[str] = None


class LanguageManifestEntry(BaseModel):
    """One language's entry in the merged manifest.

    Fields beyond these are accepted and passed through unvalidated
    (`extra="allow"`) -- the manifest schema evolves per language-onboarding
    and feature work (see CLAUDE.md's "What this project is": the schemas
    are outputs of the research, not fixed inputs), so a strict
    model would go stale within weeks. `sheets`/`planar` stay untyped dicts
    rather than fully modeled -- their shape is deep and construction-
    specific (`construction_params`, `param_names`, ...) in a way that
    would make this file the fourth place that shape is described, which is
    exactly the replication problem docs/data-layer-design.md diagnoses.
    """
    model_config = ConfigDict(extra="allow")
    folder_id: Optional[str] = None
    folder_url: Optional[str] = None
    meta: Optional[LanguageMeta] = None
    glottolog: Optional[GlottologInfo] = None
    notes_doc_id: Optional[str] = None
    planar_spreadsheet_id: Optional[str] = None
    planar_spreadsheet_url: Optional[str] = None
    diagnostics_spreadsheet_id: Optional[str] = None
    diagnostics_spreadsheet_url: Optional[str] = None
    sheets: Optional[Dict[str, Any]] = None
    planar: Optional[Dict[str, Any]] = None


class Manifest(RootModel[Dict[str, LanguageManifestEntry]]):
    """The merged manifest: {lang_id: LanguageManifestEntry}.

    Keys starting with "_" (e.g. drive_config.json's own
    "_planars_config_file_id", which sometimes ends up merged into the same
    dict by callers) are excluded before validation -- they're config
    bookkeeping, not a language entry, and were never meant to satisfy this
    shape.
    """


def check(full_config: Dict) -> List[str]:
    """Validate a manifest dict against the contract. Returns a list of
    problem descriptions (empty if none) -- never raises, regardless of
    what full_config actually is. See module docstring for why this never
    blocks a caller."""
    try:
        languages = {k: v for k, v in full_config.items() if not k.startswith("_")}
        Manifest.model_validate(languages)
    except ValidationError as e:
        return [str(err) for err in e.errors()]
    except Exception as e:
        return [f"manifest is not shaped like {{lang_id: {{...}}}} at all: {e}"]
    return []
