# Drive/Sheets protocol surface inventory

**Status:** Phase 0a deliverable — protocol-surface enumeration only. No code
written. See [data-layer-implementation-plan.md](data-layer-implementation-plan.md)
§ "Phase 0a" for scope, and [data-layer-design.md](data-layer-design.md) for
rationale.

**Method.** Every gspread / googleapiclient call site was located by reading
`coding/drive.py` and the eleven caller files directly (grep to locate
candidates, then read surrounding code for real usage). This is an inventory
of what is *actually called*, not a speculative design — per the plan's
instruction to derive the surface from the files.

This document has two parts:

1. **Per-file call-site inventory** — every distinct external API operation,
   every call site, arguments passed, return value usage, retry-wrapping, and
   read/write classification.
2. **Proposed minimal protocol** — a candidate set of method signatures that
   would cover every call site found in part 1, for human review. Not a
   commitment; Phase 0a's job is enumeration, and the actual protocol design
   happens separately.

---

## Shared helpers (`coding/drive.py`)

These are not themselves Drive API calls but wrap them; every caller file
goes through these rather than touching `gspread`/`googleapiclient` cold in
most cases (though several call gspread/Drive methods directly on objects
these helpers return — see per-file sections).

| Helper | What it does | Wraps calls | Retry |
|---|---|---|---|
| `_with_retry(fn, retries=5)` (`drive.py:38`) | Exponential backoff (15s × attempt) on `gspread.exceptions.APIError` with status 429/500/503. Re-raises other errors and the final attempt's error. | generic — callers pass a lambda | N/A (this *is* the retry wrapper) |
| `_get_clients()` (`drive.py:57`) | OAuth2 login via `gspread.oauth(...)`; builds a `googleapiclient` Drive v3 service reusing gspread's refreshed credentials (`gc.http_client.auth`). Returns `(gc, drive)`. | `gspread.oauth()`, `google_build("drive", "v3", credentials=...)` | No — auth call, not data call |
| `_get_docs_client(gc)` (`drive.py:81`) | `google_build("docs", "v1", credentials=gc.http_client.auth)` | — | No |
| `_download_file_json(drive, file_id)` (`drive.py:106`) | `drive.files().get_media(fileId=...)` + `MediaIoBaseDownload` chunked read, `json.loads()` | Read | **No** — not wrapped in `_with_retry` |
| `_upload_planars_config(drive, full_config, root_folder_id, existing_file_id=None)` (`drive.py:118`) | `drive.files().update(fileId=..., media_body=...)` (update path) or `drive.files().create(body=..., media_body=..., fields="id")` (create path). Returns file ID (str), used by caller. | Write | **No** — not wrapped in `_with_retry`; has its own inline `try/except Exception` fallback from update→create instead |
| `_load_manifest_from_drive(drive)` (`drive.py:171`) | Reads `drive_config.json` locally, then calls `_download_file_json` (new merged format) or, per-language, `_download_file_json` again (old-format fallback). | Read | Inherits from `_download_file_json` (no retry) |
| `_open_spreadsheet(gc, spreadsheet_id)` (`drive.py:224`) | `gc.open_by_key(spreadsheet_id)`, **wrapped in `_with_retry`** | Read (opens; itself has no side effect) | **Yes** |
| `_get_or_create_folder(drive, name, parent_id=None)` (`drive.py:233`) | `drive.files().list(q=..., fields="files(id, name)")`, and conditionally `drive.files().create(body=..., fields="id")` | Read then maybe Write | **No** |
| `_share_anyone_with_link(drive, file_id)` (`drive.py:259`) | `drive.permissions().create(fileId=..., body={"type":"anyone","role":"writer"}, fields="id")` | Write | **No** |
| `_share_with_person(drive, file_id, email, role="writer")` (`drive.py:273`) | `drive.permissions().create(fileId=..., body={"type":"user","role":role,"emailAddress":email}, fields="id", sendNotificationEmail=False)` | Write | **No** |
| `_remove_anyone_permission(drive, file_id)` (`drive.py:291`) | `drive.permissions().list(fileId=..., fields="permissions(id,type)")` then `drive.permissions().delete(fileId=..., permissionId=...)` for each `type=="anyone"` | Read then Write | **No** |
| `_move_to_folder(drive, file_id, folder_id)` (`drive.py:302`) | `drive.files().get(fileId=..., fields="parents")` then `drive.files().update(fileId=..., addParents=..., removeParents=..., fields="id, parents")` | Read then Write | **No** |
| `_create_notes_doc(drive, lang_id, folder_id, display_name="")` (`drive.py:321`) | `drive.files().create(body={"name":..., "mimeType":"application/vnd.google-apps.document", "parents":[folder_id]}, fields="id")`, then calls `_share_anyone_with_link` | Write | **No** |
| `_read_notes_doc_text(docs, doc_id)` (`drive.py:344`) | `docs.documents().get(documentId=doc_id)`, walks `body.content[].paragraph.elements[].textRun.content` | Read | **No** |
| `_append_to_notes_doc(docs, doc_id, text)` (`drive.py:375`) | `docs.documents().get(...)` (to find `endIndex`) then `docs.documents().batchUpdate(documentId=..., body={"requests":[{"insertText":{"location":{"index":end_index},"text":"\n"+text}}]})` | Read then Write | **No** |

**Non-Drive helpers in `drive.py`** (git subprocess, not API calls, out of
protocol scope but load-bearing preconditions): `_check_coded_data_clean()`,
`_autocommit_data()`, `_load_drive_config()`/`_save_drive_config()` (local
JSON file I/O).

**Subtlety flag on `_with_retry` coverage:** of the 13 Drive-touching helpers
in `drive.py` itself, only `_open_spreadsheet` is wrapped. Everything that
goes through `drive.files()...execute()` or `drive.permissions()...execute()`
or `docs.documents()...execute()` directly is unretried at the shared-helper
layer — callers get no backoff on manifest download, manifest upload, folder
creation, permission grants, or notes-doc reads/writes, only on the initial
`gc.open_by_key`. This is a candidate finding for the protocol design (every
one of these is a good candidate to be a protocol method with `_with_retry`
built in, rather than left to each caller to remember).

---

## File-by-file call-site inventory

### `coding/generate_sheets.py` (2644 lines)

The largest and most Drive-call-dense file: creates spreadsheets, tabs,
formatting/validation, folders, notes docs, and the manifest.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `gc.create(name)` — new spreadsheet | `:148` (`_create_or_update_tsv_sheet`), `:1480` (`_create_analysis_sheet`) | Returns `gspread.Spreadsheet`; caller reads `.id`, `.url`, `.sheet1` off it. **Not wrapped in `_with_retry`.** | No | Write |
| `gc.open_by_key(id)` | `:1800` (`_regen_construction`, bare, unwrapped) vs. `:1916` (`_add_constructions_to_existing_sheet`, wrapped: `_with_retry(lambda: gc.open_by_key(...))`) | Returns `Spreadsheet`, held live across many subsequent ops | Inconsistent — one site wrapped, one not | Read (open) |
| `spreadsheet.sheet1` | `:145,153` (via `_with_retry(lambda: ss.sheet1)`), `:1486` (bare `spreadsheet.sheet1`) | Returns default `Worksheet`; `.title` read at `:1619` | Inconsistent | Read |
| `ws.clear()` | `:146` (wrapped), `:1045`, `:1110`, `:1249` (`_reset_worksheet` — clears then immediately re-formats via `batch_update`) | Return value ignored | Only `:146` wrapped | Write |
| `ws.update(values, "A1")` | `:155` (wrapped), `:935`, `:979`, `:1046`, `:1051`, `:1116`, `:1201`, `:1430` | Always list-of-lists (header + data rows), always anchored at `"A1"`. Rows padded to equal width by callers before calling (e.g. `_populate_tab` pads trailing cols) — **caller's responsibility, not gspread's**; return value ignored throughout | Only `:155` wrapped | Write |
| `spreadsheet.batch_update({"requests": [...]})` | `:158` (bare), `:1076` (bare), `:1118` (wrapped), `:1205` (bare), `:1251` (via `ws.spreadsheet.batch_update`, bare), `:1387` (via `worksheet.spreadsheet.batch_update`, bare) | Request-shape batch (freeze/bold/dataValidation/note/repeatCell/updateDimensionProperties). Return value always ignored. Six call sites building near-identical freeze+bold requests — duplicated shape, not shared. | Only `:1118` wrapped | Write |
| `spreadsheet.worksheet(name)` (lookup by title, raises `gspread.WorksheetNotFound`) | `:921, :964, :1109, :1419, :1805` (all wrapped in `_with_retry`) | try/except is the control-flow idiom used everywhere: exists → reset/clear path; `WorksheetNotFound` → create path | All wrapped | Read |
| `spreadsheet.add_worksheet(title=, rows=, cols=)` | `:924, :967, :1048, :1112, :1198, :1422` | Returns new `Worksheet`; `.id`/`.title` read subsequently. **None wrapped.** | No | Write |
| `spreadsheet.worksheets()` | `:1042` (`_with_retry(spreadsheet.worksheets)` — note: passes the *bound method* to `_with_retry`, not a lambda, unlike most other call sites — same effect but an inconsistent idiom), `:1150, :1165, :1186, :2014` (mix of `_with_retry(spreadsheet.worksheets)` and `_with_retry(lambda: spreadsheet.worksheets())`) | Returns `List[Worksheet]` in **current tab order** (this is the ordering the fake must replicate — used to detect and fix drift via `reorder_worksheets`) | All wrapped, but via two different call idioms (`fn` vs `lambda: fn()`) | Read |
| `spreadsheet.reorder_worksheets(list)` | `:1156` (wrapped), `:1172` (bare, in `_move_status_tab_to_end`) | Takes the full ordered `List[Worksheet]`; no return value used | Inconsistent | Write |
| `spreadsheet.del_worksheet(ws)` | `:1620` | Deletes the leftover default `Sheet1` tab if unused; no return used | No | Write |
| `ws.get_all_values()` | `:1190` (`_with_retry(ws.get_all_values)`), `:1806` (`_with_retry(ws.get_all_values)`) | **Subtlety:** returns `List[List[str]]`; gspread pads/truncates ragged rows to the sheet's used-range width (not necessarily the header width) — code at `:1191` and `:1807` assumes `row[0]`/`row[1]` exist and does `len(row) >= N` guards before indexing, i.e. the callers already assume ragged rows are possible. Any fake must reproduce this padding behavior exactly, not just return exact-width rows. | Both wrapped | Read |
| `ws.append_rows(values, value_input_option="RAW")` | `:1194` | Appends missing Status-tab construction rows; return ignored | No | Write |
| `ws.id` / `ws.title` / `ws.url` / `spreadsheet.id` / `spreadsheet.url` | throughout (e.g. `:162, :1053, :1151, :1322, :1637-1638`) | Read-only property access on already-fetched objects — not separate API calls in gspread (cached on the object at creation/fetch time), but worth flagging: a fake object must expose these as static attributes consistent with what created/fetched it | N/A | N/A |
| `drive.files().list(q=..., fields=..., pageSize=...)` | `:1459` (`_create_analysis_sheet`'s duplicate-name guard) | Custom Drive query string built with f-string interpolation of `folder_id`/`sheet_title` (**injection-shaped if a name ever contains a `'`** — not currently a runtime risk since class/lang names are internally generated, but worth flagging for the fake's query parser). Reads only `files(id, name)`; only `.get("files", [])` consumed. **Not wrapped.** | No | Read |
| `_move_to_folder(drive, id, folder_id)` (drive.py helper) | `:149, :1481` | See drive.py table — internally does `files().get` then `files().update` | No (inherited) | Write |
| `_share_with_person(drive, id, email, role=)` | `:152, :1484, :2378` | See drive.py table. `:2378` is wrapped in a local `try/except Exception` (folder share failure is logged as WARNING, not fatal) | No (inherited); caller adds its own try/except at `:2377-2380` | Write |
| `_get_or_create_folder(drive, name, parent_id=)` | `:2372` | Only call site of this helper in this file — one Drive `files().list` + maybe `files().create` per language, on every run (re-resolves even when `folder_id` is cached in the manifest, because of the `or` short-circuit only when `existing_lang_data.get("folder_id")` is falsy) | No (inherited) | Read then maybe Write |
| `_create_notes_doc(drive, lang_id, folder_id, display_name)` | `:2390` | Wrapped in local `try/except Exception` (non-fatal, logs WARNING) | No (inherited) | Write |
| `_download_file_json(drive, file_id)` | `:2224, :2252, :2275, :2336` | Manifest and per-language legacy-manifest downloads. `:2336` wrapped in local `try/except Exception: pass` (migration-path fallback) | No (inherited) | Read |
| `_upload_planars_config(drive, config, root_folder_id, existing_file_id)` | `:2560, :2584, :2633` | Full-manifest write, called once **per language processed** (`:2560`, inside the loop — so partial progress survives a mid-run crash, per the docstring) plus once more at the end (`:2584`) and once in a separate manifest-only code path (`:2633`) | No (inherited) | Write |

**Live-object-held-across-many-ops sites (the awkward cases for a protocol
seam):** `_create_analysis_sheet` and `_add_constructions_to_existing_sheet`
each hold a `Spreadsheet` object across a whole sequence of tab
creates/writes/formats/reorders before returning — this is the shape the
protocol needs to support directly (an opaque spreadsheet handle used for many
subsequent calls), not just single request/response pairs. `_regen_construction`
similarly holds both a `Spreadsheet` and a `Worksheet` across a read (existing
annotations) → compute (diff) → write (repopulate) sequence, with a
`raise SystemExit` possible *between* the read and the write — i.e. the read
must not be assumed to always be followed by a write.

**Subtlety flags specific to this file:**
- `ws.update(rows, "A1")` is always called with the **full data as list-of-lists
  anchored at A1**, never a computed range — every "range" in this codebase is
  actually "whole sheet, starting at top-left." A fake only needs A1-anchored
  full-body writes for the operations actually used here, not general A1-notation
  range parsing.
- `_reset_worksheet` (`:1241`) clears + reformats specifically *because*
  `ws.clear()` alone does not reset background color or grid size — this is a
  real gspread/Sheets API behavior (cell values vs. cell formatting vs. grid
  dimensions are three separate concerns in the underlying API) that a naive
  fake could easily get wrong by treating `clear()` as "reset everything."
- Two different idioms wrap `spreadsheet.worksheets()` in `_with_retry`:
  `_with_retry(spreadsheet.worksheets)` (passing the bound method) vs.
  `_with_retry(lambda: spreadsheet.worksheets())`. Functionally identical, but
  a protocol method needs to accommodate call-site variety like this
  disappearing entirely (the seam should not care which idiom the old code used).
- `existing.get("folder_id")` short-circuiting `_get_or_create_folder` means the
  "list folders" Drive read is *not* always made — the fake needs a
  find-or-create path that is genuinely idempotent on repeated calls, since
  production code relies on that idempotency implicitly (no test currently
  proves it).

### `coding/import_sheets.py` (1124 lines)

Almost entirely **read-only** against Sheets/Drive — this file downloads, it
does not write annotation content. The only Drive *write* is the manifest
metadata sync at the very end (`_upload_planars_config`, gated by `--apply`).

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `_open_spreadsheet(gc, id)` (drive.py) | `:187` (`_read_sheet_as_df`), `:872` (main loop) | Returns `Spreadsheet` held live for the rest of that language's/tab's iteration | Yes (inherited — `_open_spreadsheet` itself wraps `gc.open_by_key`) | Read |
| `ss.sheet1.get_all_values()` | `:188` | Read planar/diagnostics reference sheet (sheet1, not a named tab) as `List[List[str]]`; converted directly to a DataFrame with `rows[0]` as columns — **assumes rectangular, non-ragged rows**, unlike the ragged-row-aware code in `generate_sheets.py`. This is a spot where the fake's padding behavior could silently produce a DataFrame with misaligned columns if a row is short. | Wrapped (`_with_retry(ss.sheet1.get_all_values)`) | Read |
| `ss.worksheet(name)` (Status tab, construction tab lookups) | `:411` (`_read_status_tab`, wrapped, catches `WorksheetNotFound` → returns `{}`), `:880` (main loop, wrapped, catches `WorksheetNotFound` → skip with warning) | Same try/except idiom as `generate_sheets.py` | Both wrapped | Read |
| `ws.get_all_values()` | `:414` (Status tab rows), `:897` (construction tab rows) | `:897`'s `rows[0]` becomes `header`; downstream validation (`_validate_pair_tab` / element-tab path) assumes `header` reflects the real column set — if the live Sheet's header row diverges from the manifest's `construction_params`, that's a silent mismatch, not caught here | Both wrapped | Read |
| `drive.files().get(fileId=, fields="id,trashed")` | `:807` (`_verify_manifest_sheet_ids`) | Cheap existence/trash check per manifest-listed spreadsheet ID, run once per sheet before any download in `--apply` mode; exceptions collected and reported together, not per-call — this is a fail-fast guard against a stale manifest, not tolerant of individual failures | **No** — no retry, and errors are caught by a broad `except Exception` per-ID rather than distinguishing transient (429/500) from permanent (404/403) failures. A protocol-level retry here would change behavior from "collect all bad IDs" to "retry each one" — worth flagging for design. | Read |
| `_load_manifest_from_drive(drive)` | `:845` | Full manifest read at the top of `main()`, before the per-language loop | No (inherited) | Read |
| `_upload_planars_config(drive, manifest, root_id, file_id)` | `:1054` | Only fires if `manifest_changed and apply` — writes back glottolog/meta/planar sync from `languages.yaml` into the Drive manifest. Return value (`new_id`) compared against the old `file_id`; if different, `_save_drive_config` persists the new file ID locally. | No (inherited) | Write |
| `_check_coded_data_clean()` | `:841` | Precondition guard, not a Drive call — gates the whole run before any Drive access when `--apply` | — | — |

**Subtlety flags:**
- `_read_sheet_as_df` (`:185-191`) builds a DataFrame straight from
  `get_all_values()` with **no ragged-row guard** — contrast with
  `generate_sheets.py`'s explicit `len(row) >= N` checks. If the fake's
  `get_all_values` doesn't pad every row to the same width as the header, this
  function breaks in a way production code has apparently never hit (real
  Sheets apparently always return rectangular data for a fully-written sheet1
  reference tab) — a case where the fake being *too* faithful to gspread's raw
  ragged-row behavior could make this passing code start failing, which is
  itself informative about what the real API returns in practice.
- `_verify_manifest_sheet_ids` treats **any** exception from `drive.files().get`
  (not just 404) as "bad ID" and reports it as such — a 429 rate-limit here
  would currently be *misreported* as a stale/deleted spreadsheet. This is a
  case where adding `_with_retry` at the protocol layer would be a genuine
  behavior fix, not just a refactor, but Phase 0a's job is to flag it, not fix it.
- This file never calls `spreadsheet.worksheets()` (list all tabs) — it always
  looks up specific tab names via `ss.worksheet(name)`, one at a time, relying
  on the manifest's `sheet_info["constructions"]` list to know what to look
  for. A protocol surface needs `open` + `get_worksheet_by_title` (with a
  not-found signal) as separate from `list_worksheets`.

