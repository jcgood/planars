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

### `coding/update_sheets.py` (488 lines)

Additive-only: appends missing rows/columns and creates newly-declared
construction tabs on sheets that already exist. Never deletes or overwrites
existing annotated cells (only appends). Reuses `generate_sheets.py`'s
`_format_and_validate`, `_add_constructions_to_existing_sheet`,
`_build_criterion_notes`, `_create_status_tab`, `_move_status_tab_to_end` —
i.e. this file's write surface is largely *calls into* `generate_sheets.py`
rather than its own gspread calls, so those operations are not re-listed here
(see the `generate_sheets.py` table above for their call/args/retry details);
only genuinely new operations and this file's own direct call sites are
tabulated.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `ws.insert_cols([col_data], col=insert_col_1)` | `:190` (`_add_trailing_columns`) | **New operation, not seen elsewhere in the 11 files.** `col_data` is a single column's full value list (`[col_name] + [""] * (num_rows-1)`); `col=` is **1-based** (comment at `:185` calls this out explicitly: `"gspread uses 1-based column indices"`). Inserted at a computed position to keep `_TRAILING_COLS` order stable relative to whichever trailing columns already exist. Return value ignored. **Not wrapped in `_with_retry`.** | No | Write |
| `ws.spreadsheet.batch_update({"requests": [...]})` | `:231` (`_write_header_notes`, wrapped) | Writes header-cell notes only (`repeatCell`/`note` requests), reusing the same shape as `generate_sheets.py`'s note-writing code but as an independent request list, not a shared call | Wrapped (`_with_retry(lambda: ...)`) | Write |
| `_open_spreadsheet(gc, id)` | `:353` | Held live across the whole per-language, per-class, per-construction nested loop | Yes (inherited) | Read |
| `ss.worksheet(name)` | `:360` (wrapped, catches `WorksheetNotFound` → skip with print, no error) | Same idiom as other files | Wrapped | Read |
| `ws.get_all_values()` | `:247` (`_compute_missing_rows`), `:366` (initial read), `:393` (**re-read after `_add_trailing_columns` mutates the sheet**, specifically to see the updated header before `_compute_missing_rows` runs) | The `:393` re-read is notable: it is a *read that exists only because a prior write in the same request sequence isn't reflected in an object already held in memory* — i.e. the code cannot assume `ws`'s in-memory state tracks the live sheet after a mutation, it must re-fetch. A protocol/fake pair needs to get this right: a mutation via one call must be visible to the *next* read call on the same handle, not just to a fresh `open`. | Wrapped (all 3) | Read |
| `ws.append_rows(rows, value_input_option="RAW")` | `:289` (`_apply_missing_rows`) | Same call shape as `generate_sheets.py:1194`; appends element rows for planar positions/elements missing from an existing tab | No | Write |
| `_add_constructions_to_existing_sheet(gc, spreadsheet_id, ...)` (generate_sheets.py) | `:450` | Called with a raw `spreadsheet_id` string (not a held `Spreadsheet` object) — internally re-opens via `_with_retry(lambda: gc.open_by_key(...))` (see `generate_sheets.py:1916`), so this is a fresh open, not a reuse of the `ss` object already open at `:353` in the same iteration. Minor inefficiency (double-open of the same spreadsheet within one loop body) worth flagging for the protocol design — a caching/handle-reuse layer could remove it. | Inherited (yes, via `generate_sheets.py:1916`) | Write |
| `_create_status_tab(ss, ...)` / `_move_status_tab_to_end(ss)` (generate_sheets.py) | `:461-462` | Reuses the already-open `ss` correctly here (unlike the `_add_constructions_to_existing_sheet` call just above it) | Inherited (mixed — see `generate_sheets.py` table) | Write |
| `_load_drive_config()` / `_upload_planars_config(...)` | `:465-469` | Manifest write, gated on `manifest_modified and apply`; mirrors `import_sheets.py`'s end-of-run manifest sync pattern | No (inherited) | Write |

**Live-object-held-across-many-ops:** `ss` (`Spreadsheet`, from `:353`) is held
across the entire nested `class → construction` loop body for one language —
tab lookup, drift check, trailing-column insert, header-note write, missing-row
append, and (for new constructions) the Status-tab refresh at the end. This is
one of the longest-lived single Spreadsheet handles across the eleven files.

**Subtlety flags:**
- `_add_trailing_columns`'s 1-based `col=` argument to `insert_cols` is the
  clearest 1-indexing trap in the whole codebase — every other write operation
  found so far (`update`, `append_rows`, `batch_update` requests) either uses
  A1 notation or 0-based `startColumnIndex`/`endColumnIndex` in the Sheets API
  request objects. `insert_cols`'s `col` parameter is gspread's own
  convenience wrapper and is 1-based, breaking that pattern. A fake that
  applies a single indexing convention uniformly across all write operations
  will get this one wrong.
- The `:366` → `:391` (write) → `:393` (re-read) sequence is this file's
  clearest instance of "operations that must be read-after-write consistent
  through the same handle," which matters for how a fake models mutation
  visibility (must not require a fresh `open()` to see your own write).
- `_check_structural_drift` (called at `:370`, pure local comparison against
  already-fetched `rows`) is not a Drive call itself, but gates whether this
  file will *ever* reach its write paths for a given tab — worth noting
  because it means most of this file's write operations are conditionally
  reached only on tabs *without* drift, and a fake exercising this file's
  write paths must construct fixtures where structural drift is absent.

### `coding/sync_params.py` (805 lines)

Column-level structural editing: insert/rename/delete criterion columns,
split/merge criteria, refresh dropdown validation. The most write-operation-
diverse of the eleven files — introduces several request shapes and gspread
convenience methods not seen elsewhere.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `ws.row_values(1)` — **new operation** | `:81, :99, :308, :330, :359, :726` (all wrapped, `_with_retry(lambda: ws.row_values(1))`); `:592, :613, :633` (**bare, unwrapped**, inline in `main()`) | Returns the header row only, as `List[str]` — 1-based row argument (gspread convention: row 1 is the first row). Used purely to check column presence (`in` tests) or build `header.index(name)` lookups. **Same call, inconsistent retry coverage** depending on whether it's inside a helper function (wrapped) or inline in `main()`'s loop body (bare) — six of nine call sites are unwrapped. | Inconsistent (6/9 sites bare) | Read |
| `ws.update_cell(1, col_1based, new_name)` — **new operation** | `:104` (`_rename_column`) | Single-cell write, explicitly `(row, col)` **1-based** for both axes (`col_1based = header.index(old_name) + 1`, comment makes the 1-indexing explicit) — a second, independent 1-indexing convention alongside `update_sheets.py`'s `insert_cols(col=)`. Return value ignored. **Not wrapped.** | No | Write |
| `spreadsheet.batch_update({"requests": [{"insertDimension": {...}}]})` — **new request shape** | `:225` (`_insert_param_columns`) | `insertDimension` (not `insertRange`/`repeatCell`/`setDataValidation` seen elsewhere) with `"inheritFromBefore": False` — inserts blank columns at a computed 0-based `startIndex`/`endIndex` *before* the Comments column. Distinct Sheets API request type from anything in `generate_sheets.py`/`update_sheets.py`. **Not wrapped.** | No | Write |
| `ws.get_all_values()` | `:238` | Bare (unwrapped), used only to compute `num_rows` and locate the keystone row (`v:verbstem`) by scanning `row[1]`; **assumes column 1 (0-based) is `Position_Name`,** i.e. hardcodes the standard element-row layout rather than reading it from the header — will misbehave silently if called on a pair-row tab (not currently done, but nothing in this function guards against it) | **No** | Read |
| `gspread.utils.rowcol_to_a1(1, insert_at + 1)` | `:257` | **Not an API call** — pure client-side coordinate-to-A1-notation conversion utility. Included here because it feeds directly into the next operation and because a protocol/fake needs equivalent coordinate math if it accepts non-A1 range args anywhere. `insert_at + 1` is again a 0-based→1-based conversion at the call site. | N/A | N/A |
| `ws.update(grid, start_cell)` — **different range semantics than every other `update()` call site in the 11 files** | `:258` | Unlike every `ws.update(rows, "A1")` call in `generate_sheets.py`/`update_sheets.py` (always anchored at the top-left), this is anchored at a **computed non-A1 start cell** (e.g. `"D1"`) — because it's writing only the newly-inserted columns' values, not the whole sheet body. This is the one call site that actually exercises `update()`'s general range-anchoring semantics rather than always writing the full sheet from A1. A fake that only implements "replace the whole body from A1" (which would cover every other call site in this inventory) will not cover this one. | No | Write |
| `spreadsheet.batch_update({"requests": [...]})` — `setDataValidation` | `:285` (new-column dropdowns, bare), `:699` (`ws.spreadsheet.batch_update`, refresh-dropdowns path, bare), `:772` (same, second `refresh_dropdowns` call site further down, bare) | Same `setDataValidation` shape as `generate_sheets.py`, but issued as a follow-up batch after `_insert_param_columns`'s structural batch — i.e. **two separate `batch_update` calls in sequence for what is conceptually one logical column-insert operation** (insert dimension, then write values via `update()`, then validate) — three round trips for one user-facing action. Worth flagging for the protocol design as a candidate for a single composite operation. | No (any site) | Write |
| `ws.row_count` | `:360` (`_build_dropdown_refresh_requests`) | Property access (gspread caches this from the worksheet's `gridProperties.rowCount` at fetch time — **not guaranteed to reflect rows added by an intervening write on the same handle**, unlike a fresh `get_all_values()` call; potential staleness a fake must decide how to model) | N/A | Read (cached) |
| `spreadsheet.batch_update({"requests": [{"deleteDimension": {...}}]})` — **new request shape** | `:730` (`ws.spreadsheet.batch_update`, inside the `--remove` column-deletion loop) | `deleteDimension` on `COLUMNS`, one request per removed column, called **once per column inside a loop, right-to-left by index** (`sorted(removed_params, key=lambda p: header.index(p), reverse=True)`) specifically so earlier deletions don't shift the indices used by later ones within the same loop — this ordering dependency is load-bearing and easy to get wrong in a fake that doesn't shift subsequent column indices after a delete. **Not batched into one request with multiple ranges even though that's expressible** — N separate API calls for N column removals. | No | Write |
| `_open_spreadsheet(gc, id)` | `:578` | Held live across the per-class, per-construction loop (same shape as `update_sheets.py`) | Yes (inherited) | Read |
| `ss.worksheet(name)` | `:582` (wrapped, catches `WorksheetNotFound`) | Same idiom | Wrapped | Read |
| `_get_current_params(ws)` / `_apply_split_to_sheet` / `_apply_merge_to_sheet` / `_insert_param_columns` (local helpers) | `:311-312, :336, :616, :639, :714` | Each of these composes 2-4 of the primitive calls above (row_values read → insert columns → update grid → validate → rename) as one logical "apply this structural edit" step | Mixed (see primitives) | Read+Write |
| `_load_drive_config()` / `_upload_planars_config(...)` / `_save_drive_config(...)` | `:780-788` | End-of-run manifest sync, same pattern as `import_sheets.py`/`update_sheets.py`, gated on `apply and manifest_changed` | No (inherited) | Write |

**Live-object-held-across-many-ops:** `ws` is held and mutated repeatedly
within a single construction's processing block — rename, then split, then
merge, then insert-new-params, then maybe remove-params, then maybe
refresh-dropdowns, all against the same `Worksheet` object, with **re-reads
of `ws.row_values(1)` interleaved between mutations** (e.g. `:726` re-reads
after `_insert_param_columns` may have already run at `:714`, precisely so
`header.index(param)` reflects post-insert column positions before deleting).
This file has the highest read-after-write-through-the-same-handle density of
the eleven files — a fake's mutation model must make every write immediately
visible to the next read on that same worksheet handle, or this file's own
internal index bookkeeping (which assumes that) will silently corrupt column
positions.

**Subtlety flags specific to this file:**
- Two *different* 1-based-indexing conventions exist side by side:
  `ws.update_cell(row, col)` (both axes 1-based) here, vs.
  `update_sheets.py`'s `ws.insert_cols(col=...)` (column only, 1-based) vs.
  everything else in the inventory using 0-based `startColumnIndex` in raw
  Sheets API request bodies. A fake needs to track, per gspread *method*
  (not per Sheets API request type), which indexing convention applies —
  there is no single global rule.
- `:258`'s `ws.update(grid, start_cell)` is the **only** call site among all
  eleven files that writes to a computed, non-`"A1"` anchor. Every other
  `update()` call in the inventory writes the full sheet body from the top-left.
  A protocol method modeled only on "replace whole body" will not cover this file.
- The three-round-trip insert (`insertDimension` → `update` values → `setDataValidation`)
  and the N-round-trip delete (one `deleteDimension` per column) are both
  candidates for a single composite "insert column(s) with values and
  validation" / "remove column(s)" protocol method — but Phase 0a's job is
  only to note that the current code makes them as separate calls, not to
  decide whether the protocol should collapse them.
- `_insert_param_columns` (`:209`) hardcodes column-1 (`row[1]`, 0-based) as
  `Position_Name` when scanning for the keystone row (`:245`) — this silently
  assumes the standard element-row layout. It is never called on a pair-row
  tab in current usage (pair-row tabs don't get param-column inserts through
  this path in the observed call graph), but nothing enforces that, so a fake
  used to test this function against a pair-row fixture would expose a latent
  bug rather than a modeling gap in the fake itself.

### `coding/validate_coding.py` (659 lines)

Reads annotation content from **local TSVs**, not from Sheets (deliberately —
see module docstring) — so this file's only Drive/Sheets I/O is opening
spreadsheets/tabs to discover structure, and writing pink/white cell
highlighting. It never reads cell *values* from a live Sheet for validation
purposes.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `ws.spreadsheet.batch_update({"requests": [{"updateCells": {...}}]})` — **new request shape** | `:80-96` (`highlight_cells`, wrapped) | `updateCells` (not `repeatCell`) — **one request per bad cell** (`bad_cells` is a list of `(row_idx, col_idx)` pairs, each becoming its own `updateCells` request in a single `requests` array), setting `userEnteredFormat.backgroundColor` to pink. Distinct from `repeatCell`, which applies one format to a *range*; `updateCells` here is used for a scattered, non-contiguous set of individual cells all in one batch call — still one API round trip even if hundreds of cells are bad, since they're all in the same `requests` list. | Wrapped | Write |
| `ws.spreadsheet.batch_update(body)` — `repeatCell` over the full used range | `:99-114` (`clear_highlights`, wrapped) | Resets `backgroundColor` to white across `startRowIndex=0..ws.row_count`, `startColumnIndex=0..ws.col_count` — **reads `ws.row_count`/`ws.col_count` as the range bounds**, i.e. trusts the cached worksheet dimensions rather than fetching current values first. Called **before** `highlight_cells` on every revalidation (`:356-357`, `:463-464`) — clear-then-repaint, not diffed against previous highlight state. | Wrapped | Write |
| `ws.row_values(1)` | `:319` (`_check_header_sync`, wrapped) | Compares live Sheet header against local TSV header; **explicitly documents gspread's padding behavior**: `"gspread may pad with trailing empty strings for empty cells; trim to TSV width"` (`:320-321`) — this is the clearest first-hand statement in the whole codebase of what `get_all_values`/`row_values` padding actually does, and exactly the subtlety the plan calls out by name. A fake must reproduce this padding (trailing empty-string fill to the sheet's used-range width) for this comparison to mean anything. | Wrapped | Read |
| `_open_spreadsheet(gc, id)` | `:556` (wrapped in a local `try/except Exception`, not raised — logs and `continue`s to the next class on any failure, including non-transient ones) | | Yes (inherited); **caller then swallows every exception type**, not just expected ones — a 429 that exhausts `_with_retry`'s retries would be silently downgraded to a "could not open spreadsheet" skip rather than surfaced as a real failure requiring re-run | Read |
| `ss.worksheets()` | `:561` (`_with_retry(lambda: ss.worksheets())`) | Iterates **every tab** in the spreadsheet (not just tabs listed in the manifest's `constructions`), explicitly to catch tabs the manifest doesn't know about; skips `_STATUS_TAB`/`_INSTRUCTIONS_TAB`/`_PLANAR_REF_TAB` by title. Order returned is whatever `worksheets()` returns — not otherwise relied on here. | Wrapped | Read |
| `_read_tsv_rows(...)` (local file, not Drive) | `:285-298` | Not a Drive call — included to make explicit that the *validated data* never comes from a live API call in this file, only from `coded_data/` TSVs already on disk | — | Local file read |

**Live-object-held-across-many-ops:** `ws` is passed into `revalidate_sheet`/
`revalidate_pair_sheet`, which each do a local-TSV read, a pure-Python
validation pass, then two Sheets writes on the same handle (`clear_highlights`
then `highlight_cells`) — always in that order, always both, never just one.
A fake needs "last write wins" semantics for overlapping format ranges applied
in sequence on the same worksheet (clear-white-everything, then paint specific
cells pink) to reproduce the visible end state correctly.

**Subtlety flags specific to this file:**
- `updateCells` (per-cell writes, one request per bad cell in a single batch)
  vs. `repeatCell` (one request, one contiguous range) are two different ways
  to write cell formatting that this codebase uses side by side within the
  same file for two different purposes (paint scattered bad cells vs. reset a
  whole rectangular range) — a fake needs to support both request shapes
  under the same `batch_update`/`spreadsheet.batch_update` umbrella (unlike
  `values_batch_update`, these two really are the same underlying gspread
  method with different request payloads, not a naming collision).
- `clear_highlights` bounds its reset range with `ws.row_count`/`ws.col_count`
  — cached grid-dimension properties, not a fresh read. If a fake's cached
  dimensions drift from its actual data range (e.g. after a resize elsewhere
  in the same test), this reset could clear less or more than intended; worth
  a fixture-consistency note for whoever builds the fake.
- This is the one file in the inventory whose docstring explicitly reasons
  about *why* it avoids one of the read operations entirely ("Reads cell
  values from local TSVs ... rather than re-fetching them from Google
  Sheets") — worth preserving that design rationale in the protocol design
  discussion, since it means not every command needs (or should default to)
  a live read path even where one exists.

### `coding/refresh_dropdowns.py` (200 lines)

Smallest of the eleven files — refreshes dropdown validation only, no data or
structural changes. Notable mainly for **not** reusing the shared manifest-
upload helper.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `gc.open_by_key(spreadsheet_id)` — **bare, not via `_open_spreadsheet`** | `:128` | Third distinct way of opening a spreadsheet seen in the inventory: `_open_spreadsheet(gc, id)` (wrapped, most files), bare `gc.open_by_key(...)` unwrapped (`generate_sheets.py:1800`), and here, bare `gc.open_by_key` wrapped only in a local `try/except Exception` that logs and `continue`s rather than retrying. **Not wrapped in `_with_retry` at all.** | No | Read |
| `ss.worksheet(name)` | `:161` (`_with_retry(lambda c=construction: ss.worksheet(c))`, wrapped, but catches bare `Exception` rather than `gspread.WorksheetNotFound` specifically — the only file in the inventory to do so) | Broader exception handling than every other call site's `except gspread.WorksheetNotFound` idiom — would also silently swallow, e.g., a network error as "tab not found" | Wrapped, but with the wrong exception granularity | Read |
| `ws.row_values(1)` | `:166` (wrapped) | Feeds `_detect_col_start`, a **new heuristic** not seen elsewhere: scans the header for the first column matching a name in `param_names`, falling back to a hardcoded `3` (standard element-row layout) if none match — i.e. this file derives `col_start` dynamically per-tab rather than assuming a fixed offset the way `generate_sheets.py`/`update_sheets.py` do. | Wrapped | Read |
| `ws.row_count` | `:169` | Cached property, same caveat as `sync_params.py`'s use — feeds `num_rows` for the validation range | N/A | Read (cached) |
| `_format_and_validate(ws, ...)` (generate_sheets.py) | `:170` | Reused directly; see that file's table for the underlying `batch_update`/`setDataValidation` shape | Inherited | Write |
| `drive.files().update(fileId=manifest_file_id, media_body=MediaIoBaseUpload(...))` — **independent, fourth manifest-write implementation** | `:192-195` | **Does not call `_upload_planars_config`.** Reimplements the same "upload JSON as manifest.json" operation inline, using `MediaIoBaseUpload` directly, duplicating `drive.py`'s `_upload_planars_config` logic (minus its key-reordering step and its create-if-missing fallback — this version has no create path at all; if `manifest_file_id` is unset it just prints a warning and gives up, `:197-198`). This is a clear "same fact, no single owner" instance per the design doc's diagnosis: the manifest-upload operation now has **two** independent implementations in the codebase (`drive.py`'s and this one), not counting the read side. **Not wrapped in `_with_retry`.** | No | Write |

**Live-object-held-across-many-ops:** `ss` (from bare `gc.open_by_key` at
`:128`) is held across the per-construction loop for one class, same shape as
other files, but opened without the shared retry helper.

**Subtlety flags specific to this file:**
- The manifest-upload duplication here is the clearest concrete instance in
  the whole inventory of the "replicated fact with no single owner" pattern
  `data-layer-design.md` opens with — worth flagging prominently for whoever
  reviews this document, since it's an actual latent bug risk (this path
  skips `_upload_planars_config`'s key-reordering and has no create-if-missing
  fallback) as well as a protocol-design argument.
- `except Exception` (not `gspread.WorksheetNotFound`) at `:161-164` means a
  transient API error here is currently indistinguishable from "tab genuinely
  doesn't exist" — a fake built to distinguish these cases correctly would
  expose that this file's error handling is looser than its siblings.

### `coding/generate_status_sheet.py` (527 lines)

Builds a read-only, locked status dashboard sheet per language, in a
freestanding Drive folder chosen specifically to route around an inherited-
permission limitation of the Sheets/Drive API (see module docstring,
`:11-21` — a genuine API constraint, not a design preference: "Google's API
refuses to remove an *inherited* permission at a child level"). Introduces
several operations not seen elsewhere: `update_title`, `resize`, `mergeCells`,
and the `raw=False` argument to `update()`.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `drive.files().list(q=..., fields="files(id)")` | `:284-291` (`_get_or_create_status_spreadsheet`) | **Third** independent "find by name in folder" Drive query in the inventory (alongside `drive.py`'s `_get_or_create_folder` and `restructure_sheets.py`'s `_get_or_create_subfolder`) — same shape, requesting only `id` this time (not even `name`). Read, then `_open_spreadsheet` if found. | No | Read |
| `gc.create(name)` / `_move_to_folder(...)` | `:294-295` | Create-if-not-found path of the same helper | No | Write |
| `drive.permissions().list(fileId=, fields="permissions(emailAddress)")` | `:304-306` (`_already_shared`) | **Second** distinct use of `permissions().list` in the inventory (first is `drive.py`'s `_remove_anyone_permission`, which requests `permissions(id,type)`); this one requests `permissions(emailAddress)` instead — same underlying call, different `fields` projection, called to avoid piling up duplicate share grants on repeated `--apply` runs | No | Read |
| `_remove_anyone_permission` / `_share_with_person` (drive.py, via local `_lock_read_only` wrapper) | `:310-314`, called at `:465, :501` | Standard reuse | No (inherited) | Write |
| `ws = ss.sheet1` | `:347` (`_with_retry(lambda: ss.sheet1)`) | | Wrapped | Read |
| `ws.update_title("Status")` — **new operation** | `:349` (`_with_retry(lambda: ws.update_title("Status"))`) | Renames the default `Sheet1` tab in place rather than creating/deleting a differently-named tab — the only file in the inventory that renames a tab instead of add/delete. Conditional on `ws.title != "Status"` so it's a no-op on re-runs. | Wrapped | Write |
| `ws.resize(rows=, cols=)` — **new operation** | `:368` (`_with_retry(lambda: ws.resize(rows=max(len(all_rows)+2, 10), cols=n_cols))`) | Explicit grid resize as its own call, called *before* `update()` writes values — contrast with `generate_sheets.py`'s `_reset_worksheet`, which folds the equivalent resize into the same `batch_update` that also clears formatting; here it's a separate gspread convenience method. | Wrapped | Write |
| `ws.update(all_rows, "A1", raw=False)` — **new argument, `raw=False`** | `:369` (`_with_retry(lambda: ws.update(all_rows, "A1", raw=False))`) | **Every other `update()` call site in the inventory omits `raw`** (gspread default `raw=True`, values written literally as strings). Here `raw=False` is required so that Sheets parses the embedded `=HYPERLINK(...)` formula strings in `data_rows`/`banner` as actual formulas rather than literal text — a real, load-bearing difference in write semantics that a fake must model (does the fake even distinguish formula-string cells from literal-string cells, or store both as opaque strings?). Silently getting this wrong wouldn't error, it would just make the sheet display broken raw formula text — the kind of divergence that's easy to miss without a byte-level golden. | Wrapped | Write |
| `spreadsheet.batch_update({"requests": [...]})` | `:434` (`_with_retry(lambda: ss.batch_update({"requests": requests}))`) | Largest single request list in the inventory: freeze, bold (x2), **`mergeCells`** (new request type, once per banner row), column-width `updateDimensionProperties` (x3), `wrapStrategy` `repeatCell`, plus one `repeatCell` background-color request **per data row** (`:423-432`, one request per construction row, similar in spirit to `validate_coding.py`'s per-cell `updateCells` but using `repeatCell` on a 1-row range instead) — potentially dozens of requests in one call for a language with many constructions, still one round trip. | Wrapped | Write |
| `_get_or_create_folder(drive, name)` (drive.py, no `parent_id`) | `:463` | **The only call site in the inventory that omits `parent_id`**, i.e. searches/creates at Drive-root level rather than inside a language folder — deliberately, per the module docstring's explanation of the inherited-permission problem | No (inherited) | Read then maybe Write |
| `ss.worksheet(construction)` | `:244` (`_gather_status_rows`, wrapped, catches `WorksheetNotFound`) | Standard idiom | Wrapped | Read |
| `ws.get_all_values()` | `:257` (`_with_retry(lambda w=ws: w.get_all_values())`) | Feeds `annotation_status()` (from `validate_coding.py`) for the completeness percentage — this is the one file that *does* read live cell values from Sheets for a completeness computation (contrast `validate_coding.py`, which deliberately reads local TSVs instead) | Wrapped | Read |
| `_open_spreadsheet(gc, id)` | `:233` | **Cached per class_name within one language's processing** (`open_spreadsheets` dict, `:218, :231-236`) so a class spreadsheet shared by multiple constructions is opened only once — the one file in the inventory that explicitly deduplicates opens within a single run, worth noting as a pattern other files could adopt | Yes (inherited) | Read |
| `_upload_planars_config(...)` | `:520` | End-of-run manifest sync (`status_sheet_url` field), gated on `manifest_dirty` | No (inherited) | Write |

**Live-object-held-across-many-ops:** `ss` per status spreadsheet is held from
find-or-create through the single `_write_status_sheet` call (resize → update
values → one big batch_update) → the lock-read-only permission calls — a
shorter chain than `restructure_sheets.py`'s but still a create-then-multi-
write-then-permission sequence with no rollback if it fails partway (lower
stakes here since there's no annotation data at risk, only a regenerable
dashboard).

**Subtlety flags specific to this file:**
- `raw=False` on `update()` is the single most easily-missed argument
  difference in the whole inventory — it changes what the write *means*
  (formula vs. literal string), not just its target range, and every other
  call site in the other ten files omits it. A protocol method signature that
  doesn't expose a raw/formula distinction will not be able to express this
  call correctly.
- `ws.resize()` as a standalone gspread method (vs. folding grid-size changes
  into a `batch_update` `updateSheetProperties` request, as `generate_sheets.py`
  does) is a second gspread-convenience-method-vs-raw-request-object split,
  alongside `update_sheets.py`'s `insert_cols`/`update_cell` and
  `sync_params.py`'s `row_values`. A protocol design should decide once
  whether to model these as convenience calls or normalize everything through
  raw batch requests — the current code does both, inconsistently, depending
  on which file/author touched it.
- Link construction (`f"{ss.url}#gid={ws.id}"`, `:250`) treats `ws.id` (the
  Sheets API's internal numeric sheet ID) as directly usable in a URL
  fragment — correct for real Google Sheets, but a detail a fake's worksheet
  IDs need to preserve if anything downstream ever parses these links (nothing
  currently does, but the manifest's `status_sheet_url` is written verbatim to
  Drive for Adam to click).

### `coding/generate_biuniqueness_stage1_sheet.py` (291 lines)

Structurally a near-duplicate of `generate_status_sheet.py`'s Drive-writing
code (same find-or-create-by-name pattern, same `update_title`/`resize`/
`update(..., raw=False)`/`mergeCells`/banner-row shape) — the module docstring
says as much (`"mirrors generate_status_sheet.py's precedent"`). Rather than
re-tabulate identical call shapes, this entry lists only the calls and the
**one behavioral delta** from that file.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `drive.files().list(...)` / `gc.create(...)` / `_move_to_folder(...)` | `:149-161` (`_get_or_create_stage1_spreadsheet`) | Identical shape to `generate_status_sheet.py:284-296`'s `_get_or_create_status_spreadsheet` — **fourth** independent "find-by-name-in-folder" implementation in the inventory | No | Read then maybe Write |
| `ws = ss.sheet1` / `ws.update_title("Stage1")` | `:171-173` | Same pattern as `generate_status_sheet.py:347-349` | Wrapped | Read/Write |
| `ws.clear()` — **behavioral delta from `generate_status_sheet.py`** | `:174` (bare, unwrapped) | `generate_status_sheet.py`'s `_write_status_sheet` does **not** call `ws.clear()` at all before its `resize`+`update` (relies on resize+full overwrite alone); this file explicitly clears first. Two sibling files, written to the same pattern, differ on whether an explicit `clear()` precedes the resize/rewrite — worth flagging alongside the other "same operation, different-file idiom" findings (`ws.clear()` bare vs. `_reset_worksheet` in `restructure_sheets.py`/`generate_sheets.py`). | No | Write |
| `ws.resize(rows=, cols=)` | `:182` (wrapped) | Same as `generate_status_sheet.py:368` | Wrapped | Write |
| `ws.update(values, "A1", raw=False)` | `:183` (wrapped) | Same `raw=False` formula-write concern as `generate_status_sheet.py:369` — though this sheet's data rows are plain strings (no `HYPERLINK` formulas built into `_rows_to_sheet_values`), so `raw=False` is currently a no-op in practice here; only the **banner** rows would matter if they ever gained a formula, which they don't today. Still worth the fake supporting `raw=False` correctly since the call is made regardless. | Wrapped | Write |
| `spreadsheet.batch_update({"requests": [...]})` | `:227` (wrapped) | Same request-shape family as `generate_status_sheet.py` (freeze, bold ×2, `mergeCells`, one `setDataValidation` for the `has_allomorphs` y/n dropdown, `wrapStrategy`) — no per-row background-color requests here (this sheet has no color-coding), so one flat batch of a fixed number of requests regardless of row count, unlike `generate_status_sheet.py`'s N-requests-per-row pattern | Wrapped | Write |
| `_share_with_person(drive, id, email, role="writer")` | `:273` | Hardcoded to Adam's email (`_ADAM_EMAIL`) rather than `_annotator_email(lang_id)` — deliberate, per the module docstring (`synth0001` has no `annotator_email` in `languages.yaml`) | No (inherited) | Write |
| `_load_manifest_from_drive` / `_upload_planars_config` | `:265, :284` | Same end-of-run manifest-sync pattern (`biuniqueness_stage1_spreadsheet_id`/`url` fields), gated on the value actually changing | No (inherited) | Read / Write |

**Subtlety flags specific to this file:** none beyond what's already flagged
under `generate_status_sheet.py` — its main value for the inventory is
confirming that `raw=False` and the `mergeCells`/banner-row pattern are a
**repeated idiom** (two independent call sites), not a one-off, which raises
the priority of getting both right in a fake/protocol rather than treating
them as edge cases.

### `coding/generate_notebooks.py` (456 lines)

**Never touches gspread at all.** This is the one file in the eleven whose
entire Drive footprint is the raw `googleapiclient` Drive v3 service
(`drive.files()`, `drive.permissions()`) — no `Spreadsheet`/`Worksheet`
objects anywhere, because it uploads `.ipynb` JSON blobs as opaque file
content, not spreadsheet cells. Worth flagging structurally: a protocol
surface built only around gspread-shaped operations (open/worksheet/update/
batch_update) would miss this file's needs entirely — it needs generic
"create/update a Drive file with arbitrary bytes and a mimetype" as a
first-class operation.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `drive.files().update(fileId=, body={"name": filename}, media_body=media)` — inside `_upload_file` | `:221-225` | **Third independent implementation of "create-or-update a Drive file with content"** (alongside `drive.py`'s `_upload_planars_config` and `refresh_dropdowns.py`'s inline duplicate) — this one is at least written as a reusable helper (`_upload_file`, parameterized by filename/mimetype/folder/existing-id) rather than hardcoded to manifest.json, but it is still a third, independent piece of code doing conceptually the same thing. Also updates the file's `name` on every update call (the other two don't rename on update). Return value discarded (existing ID reused). **Not wrapped in `_with_retry`.** | No | Write |
| `drive.files().create(body={"name":, "parents":[folder_id]}, media_body=media, fields="id")` — inside `_upload_file` | `:228-233` | Create path of the same helper; `result["id"]` is the only field consumed | No | Write |
| `drive.permissions().create(fileId=, body={"type":"anyone","role":"reader"}, fields="id")` — `_set_viewer_permissions` | `:238-242` | **Near-duplicate of `drive.py`'s `_share_anyone_with_link`**, which is the identical call with `"role":"writer"` instead of `"reader"` — a second independent (if trivially small) reimplementation of the same permission-grant shape rather than a call to the shared helper with a `role` parameter (which `_share_anyone_with_link` doesn't currently expose, unlike `_share_with_person`, which does take `role=`). | No | Write |
| `_get_clients()` | `:348` | Only `drive` (the Drive service) is used from the returned `(gc, drive)` pair — `gc` is discarded (`_, drive = _get_clients()`) since this file never touches gspread | — | — |

**Live-object-held-across-many-ops:** none in the gspread sense — no
`Spreadsheet`/`Worksheet` objects exist in this file at all. The closest
analogue is `drive_config` (a local dict, not a live handle), which is read
once, mutated in memory across the whole run (one notebook type at a time,
four passes: contributor/validation/report/coordinator), and saved once at
the end via `_save_drive_config` (`:432`) — a local file write, not a Drive
call, so failure mid-run leaves Drive-uploaded notebooks whose file IDs never
made it into `drive_config.json`, silently orphaning them from future
`--apply` runs' update-in-place logic (they'd just get re-created under a
new file ID next time, rather than erroring).

**Subtlety flags specific to this file:**
- This file is the strongest argument in the whole inventory for **not**
  designing the protocol surface exclusively around Sheets-shaped operations.
  "Upload arbitrary file content to a Drive folder, by mimetype, with
  create-or-update-by-existing-id semantics" is a distinct primitive from
  anything involving worksheets, and it's used by this file, `drive.py`'s
  manifest helpers, and `refresh_dropdowns.py`'s inline duplicate — three
  call sites, one real underlying operation, currently three implementations.
- `_upload_file`'s update path renames the file on every call
  (`body={"name": filename}`) while `_upload_planars_config`'s update path
  does not touch the name at all — a real behavioral difference between the
  two "upload or update a Drive file" implementations, not just duplicated
  code that happens to agree.

### `coding/generate_reports.py` (127 lines)

Smallest file in the inventory. Like `generate_notebooks.py`, **never touches
gspread** — pure Drive-file upload, this time for PDF bytes rather than
`.ipynb` JSON. Its own local `_upload_pdf` is a fourth independent
create-or-update-Drive-file implementation.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `drive.files().update(fileId=, body={"name": filename}, media_body=media)` | `:47-51` (`_upload_pdf`) | **Fourth** independent "create-or-update a Drive file" implementation (after `drive.py`'s `_upload_planars_config`, `refresh_dropdowns.py`'s inline duplicate, `generate_notebooks.py`'s `_upload_file`). Same rename-on-update behavior as `generate_notebooks.py`'s version. `media_body=MediaIoBaseUpload(..., resumable=False)` — the only call site in the inventory that explicitly sets `resumable=False`; every other `MediaIoBaseUpload` use in the codebase (`drive.py`'s manifest upload, `generate_notebooks.py`'s notebook upload) leaves it at the library default. Worth a note for a fake: if resumable-upload semantics are ever modeled, this is the one call that opts out. **Not wrapped in `_with_retry`.** | No | Write |
| `drive.files().create(body={"name":, "parents":[folder_id]}, media_body=media, fields="id")` | `:54-58` | Same shape as elsewhere | No | Write |
| `drive.permissions().create(fileId=, body={"type":"anyone","role":"reader"}, fields="id")` — **behavioral delta from `generate_notebooks.py`** | `:60-64` | **Only called on the create branch** (inside the `else:` at `:53-65`) — unlike `generate_notebooks.py`'s `_set_viewer_permissions`, which this file's sibling calls unconditionally after every upload (both create and update paths, `generate_notebooks.py:370` runs after every `_upload_file` regardless of whether it created or updated). This file's PDF permission is set once at creation and never reasserted on subsequent updates — if the "anyone with link, reader" grant is ever accidentally removed from a report PDF, `generate-reports --apply` will silently fail to restore it on the next run (it will just update the PDF content in place, permission untouched), whereas the equivalent notebook would self-heal. A behavioral inconsistency worth flagging for the protocol design (should "upload or update + ensure viewer permission" be one composite operation, applied uniformly?). | No | Write |
| `_get_clients()` | `:85` | Same discard-`gc` pattern as `generate_notebooks.py:348` | — | — |

**Live-object-held-across-many-ops:** none — same as `generate_notebooks.py`,
no gspread objects exist in this file. `drive_config` is mutated in memory
across the per-language loop and saved once at the end (`:117`); a failure
partway through leaves already-uploaded PDFs' `report_file_id`s unpersisted,
same orphaning risk as `generate_notebooks.py`.

**Subtlety flags specific to this file:**
- The create-only permission-set (vs. `generate_notebooks.py`'s
  every-time permission-set) is the clearest concrete "two implementations of
  the same conceptual operation, differing in behavior in a way that matters"
  finding among the four independent Drive-file-upload implementations found
  across the eleven files. Listed together, the four are: `drive.py`'s
  `_upload_planars_config` (update never renames; create sets no permission —
  manifest.json is never meant to be publicly viewable), `refresh_dropdowns.py`'s
  inline duplicate (same, minus the key-reordering and create-fallback),
  `generate_notebooks.py`'s `_upload_file`+`_set_viewer_permissions` (update
  renames; permission set unconditionally every run), and this file's
  `_upload_pdf` (update renames; permission set only on create). A single
  protocol method for "create-or-update a Drive file" would need an explicit,
  named parameter for each of these axes (rename-on-update: yes/no;
  reassert-permission: always/on-create-only/never) rather than letting each
  caller reinvent the combination it happens to want.

### `coding/restructure_sheets.py` (1423 lines)

The most consequential file in the inventory — archive/recreate cycles, the
only file that calls `values_batch_update` (a *different* gspread method from
`batch_update`), and the multi-step operation the design doc names by name as
the source of the #248-class incidents (`docs/data-layer-design.md`'s
`restructure-sheets --apply performs 7 sequential side effects with no
rollback`). Reuses `generate_sheets.py` helpers heavily (`_build_rows`,
`_create_status_tab`, `_format_and_validate`, `_maybe_create_planar_reference_tab`,
`_reorder_system_tabs`, `_build_criterion_notes` — not re-tabulated; see that
file's section) but also introduces its own direct gspread/Drive calls.

| Operation | Call sites | Args / return usage | Retry | R/W |
|---|---|---|---|---|
| `ws.get_all_values()` | `:129` (`_download_tab_annotations`, **bare**), `:610` (`_cascade_rename_pair_tab`, wrapped via `_with_retry(lambda: ws.get_all_values())`), `:655` (`_copy_pair_tab_with_rename`, wrapped) | `:129` builds a `{(element,pos_name): {col:val}}` dict from raw rows with an explicit `len(row) <= max(el_idx,pos_name_idx)` ragged-row guard before indexing — a third distinct ragged-row-handling idiom (compare `generate_sheets.py`'s `len(row) >= N` and `import_sheets.py`'s lack of any guard) | Inconsistent (1 of 3 bare) | Read |
| `spreadsheet.worksheet(name)` | `:331, :654, :682, :795, :1141, :1316` (all wrapped, all the same try/`WorksheetNotFound` idiom) | Consistent with the rest of the inventory | All wrapped | Read |
| `spreadsheet.add_worksheet(...)` | `:334, :660, :685` | Same shape as elsewhere | No | Write |
| `ws.clear()` | `:332, :683` | Bare `clear()`, **not** the full `_reset_worksheet` treatment used in `generate_sheets.py` (no explicit format/grid-size reset) — this file relies on the subsequent `ws.update(...)` overwriting old values but does **not** explicitly clear old cell formatting/grid size the way `generate_sheets.py` does. Worth flagging: two different "clear a tab before rewriting" idioms exist across the eleven files, one thorough (`_reset_worksheet`) and one not (bare `.clear()` here). | No | Write |
| `ws.update(rows, "A1")` | `:338` (`_write_tab_with_carryover`), `:689` (`_copy_pair_tab_with_rename`) | Same A1-anchored-full-body pattern as `generate_sheets.py` | No | Write |
| `spreadsheet.del_worksheet(ws)` | `:878, :1266` | Removes leftover default `Sheet1` after tab population, same pattern as `generate_sheets.py:1620` | No | Write |
| `gc.create(name)` | `:849, :1215` | New spreadsheet for the recreated class sheet (archive+recreate step) | No | Write |
| `new_ss.sheet1` | `:856, :1222` (both `_with_retry(lambda: new_ss.sheet1)`) | Read the default tab to know what to delete later | Wrapped | Read |
| `drive.files().update(fileId=ss.id, body={"name": ...})` — **rename, not move** | `:839-842, :1205-1208` | Renames the spreadsheet file to `{class}_{lang_id}_v{N}` as the archive step's first act, **before** `_move_to_folder` moves it into `_archived/` — two separate Drive writes (`files().update` for rename, then `_move_to_folder`'s own `files().get`+`files().update` for the parent-folder change) for one conceptual "archive" action. **Not wrapped in `_with_retry`.** | No | Write |
| `_move_to_folder(drive, id, folder_id)` (drive.py) | `:843, :851, :1209, :1217` | Archive-move and new-sheet-move, both directions | No (inherited) | Write |
| `_lock_archived_sheet(drive, id, lang_id)` (local helper, wraps `_remove_anyone_permission` + `_share_with_person`) | `:844, :1210` | See drive.py table for the two calls this makes | No (inherited) | Write |
| `_get_or_create_subfolder(drive, parent_id, name)` — **new helper, structurally identical to `drive.py`'s `_get_or_create_folder` but reimplemented locally rather than reused** | `:211-232`, called at `:838, :1204` | `drive.files().list(q=...)` then maybe `drive.files().create(body=..., fields="id")` — same shape as `_get_or_create_folder` in `drive.py`, but a **separate, parallel implementation** (only fields requested differ: `"files(id)"` here vs. `"files(id, name)"` in `drive.py`). This is exactly the kind of "same fact, no single owner" duplication the design doc's diagnosis section is about — flagged here because a protocol method for "get-or-create folder" should replace both, not just this file's copy. | No | Read then maybe Write |
| `drive.files().create(body={..., "mimeType": "...folder", "parents": [...]}, fields="id")` | `:224-231` (inside `_get_or_create_subfolder`) | Duplicate of `_get_or_create_folder`'s create path, see above | No | Write |
| `_share_with_person(drive, id, email, role=)` | `:854, :1220` | Same as elsewhere | No (inherited) | Write |
| `gspread.utils.rowcol_to_a1(1, col_idx + 1)[:-1]` | `:624` | **Pure utility**, used to extract just the column letter (strips the trailing row digit off `"D1"` → `"D"`) for building a `{col_letter}{row_idx}` range string for `values_batch_update`. Fragile in general (`[:-1]` assumes a single-digit row number, safe here only because row 1 is hardcoded) — not a bug at the current call site but a sharp edge if reused elsewhere. | N/A | N/A |
| `ws.spreadsheet.values_batch_update({"valueInputOption": "RAW", "data": [{"range": ..., "values": [[...]]}]})` — **new gspread method, distinct from `spreadsheet.batch_update`** | `:628-631` (`_cascade_rename_pair_tab`, wrapped: `_with_retry(lambda: ...)`) | **This is `spreadsheets.values.batchUpdate` (per-cell/per-range value writes), not `spreadsheets.batchUpdate` (structural/formatting requests) — two different Sheets API endpoints exposed as two different gspread methods with similar names but incompatible request shapes.** This is the only call site among all eleven files that uses `values_batch_update`; every other batch write in the inventory uses `batch_update`. A protocol/fake that conflates the two (e.g. one generic "batch write" method) will not correctly model this call — its `data` list of `{range, values}` dicts is a different contract from a `requests` list of typed request objects. | Wrapped | Write |
| `_open_spreadsheet(gc, id)` | `:791, :1135, :1314` | Held live across the whole archive-download-recreate sequence per class per language — the longest-lived handle in the inventory, spanning a read (download annotations) → compute (stats) → **destructive** write (archive+rename+move) → another write (create new sheet, populate tabs) sequence, entirely within one `main()` loop iteration, no journaling or resumability | Yes (inherited) | Read |
| `MANIFEST_PATH.write_text(...)` | `:1287, :1328, :1412` | Not a Drive call — local `sheets_manifest.json` write, done **immediately after each class's manifest update** (`:1287`, inside the per-class loop) specifically so partial progress survives a mid-run crash — same defensive pattern as `generate_sheets.py`'s per-language `_upload_planars_config` call | — | Local file write |
| `_upload_planars_config(...)` | `:1339, :1416` | End-of-run Drive manifest sync (plus a second one if new notification issues were created) | No (inherited) | Write |

**Live-object-held-across-many-ops:** this file has the inventory's clearest
example of a single object spanning a genuinely multi-step, partially
irreversible operation: `ss` (opened at `:791`/`:1135`) is read from (download
every tab's annotations), then — if `apply` — its underlying spreadsheet file
is **renamed and moved** (archived) via Drive calls that operate on `ss.id`,
while a *second*, unrelated `Spreadsheet` object `new_ss` (from `gc.create(...)`
at `:849`/`:1215`) is populated and becomes the new manifest entry. There is no
rollback if population of `new_ss` fails partway through after `ss` has
already been archived — this is precisely the "7 sequential side effects, no
rollback" scenario `data-layer-design.md` names, and it is the reason Phase 7
(recoverability) exists as a separate later phase. A protocol seam here needs
to support: open A, read A, mutate A (rename+move), create B, populate B
across N tab-writes, update a manifest — as one logical unit with a
well-defined partial-failure story, not just individual call wrappers.

**Subtlety flags specific to this file:**
- **`values_batch_update` vs. `batch_update`** is the single most likely
  naming collision to trip up a fake or a protocol design — they sound like
  the same operation and are not. Any protocol method name needs to
  disambiguate this explicitly (e.g. `write_cell_ranges` vs.
  `apply_sheet_requests`), not use "batch update" as a generic name.
- **Two independent "get-or-create folder" implementations** exist
  (`drive.py:_get_or_create_folder` and this file's `_get_or_create_subfolder`)
  doing the same Drive query/create shape with slightly different `fields`
  values. A fake needs both call shapes to work identically even though the
  production code never unified them — and the protocol design should
  probably collapse them into one method, per `data-layer-design.md`'s
  "derive, don't duplicate" principle.
- **Archive-then-create is not atomic and not journaled.** The rename
  (`drive.files().update`) happens, then the move (`_move_to_folder`), then
  the permission lock (`_lock_archived_sheet`), then a brand-new spreadsheet
  is created and populated tab-by-tab, then the manifest is updated — six-plus
  Drive round trips per class per language, any one of which can fail after
  the archive step has already destroyed the "current" status of the old
  sheet. This is the file the design doc's `#248 is exactly this story`
  sentence is about.
- `ws.clear()` here (bare) vs. `_reset_worksheet()` in `generate_sheets.py`
  (clear + explicit grid/format reset) is a second instance (after
  `update_sheets.py`'s `insert_cols` 1-indexing) of the same operation being
  done two different ways in two files — a fake needs to decide whether
  `clear()` alone resets formatting/grid size or not, and current production
  code depends on the answer being "no" in some places (this file, apparently
  tolerating leftover formatting on a *freshly created* worksheet, where it
  wouldn't matter) and needing it to be handled explicitly elsewhere
  (`generate_sheets.py`, where tabs are *reused*, not freshly created, so
  leftover pink highlighting from `validate-coding` would otherwise persist).

---

## Proposed minimal protocol

**This is a proposal for review, not a decision.** Phase 0a's job was
enumeration; the actual protocol module (`drive_backend.py` or similar) is a
separate, later piece of work. Everything below is derived directly from the
call-site tables above — every method listed exists because at least one call
site in part 1 needs it, and every call site in part 1 should be coverable by
at least one method below. Where the current code does something in an
inconsistent or duplicated way (four manifest-upload implementations, two
get-or-create-folder implementations, mixed 1-based/0-based indexing), the
proposal picks one shape and notes what it's collapsing — but that collapse
is itself a design decision for the reviewer to accept or reject, not
something Phase 0a is authorized to have already decided.

### Design stance the proposal takes (flag these first — they're judgment calls)

1. **Model live handles as objects, not a flat function list.** The
   "live-object-held-across-many-ops" notes under nearly every file (longest
   chains: `restructure_sheets.py`'s archive-then-recreate, `sync_params.py`'s
   read-mutate-reread-mutate sequences) mean the protocol needs `Spreadsheet`-
   and `Worksheet`-shaped handles that callers hold and pass around, not just
   stateless `(spreadsheet_id, ...) -> result` functions. A purely functional
   surface would force every call site to re-thread IDs it already has in hand.
2. **Mutations must be visible to the next read on the same handle.**
   `update_sheets.py:391→393` and `sync_params.py`'s interleaved
   read-mutate-reread all depend on this. The fake's model (and, if it proxies
   a cache, the real backend's) must not require a fresh `open()` to observe a
   write just made through the same handle.
3. **Keep `batch_update` (structural requests) and `values_batch_update`
   (range value writes) as two distinct methods**, not one generic "batch"
   call — see the naming-collision flag under `restructure_sheets.py`. Getting
   this merge wrong is the single most likely way a fake silently diverges
   from the real API.
4. **Expose raw Sheets API request objects for `batch_update`, rather than a
   method per request type.** The eleven files collectively use at least nine
   distinct request types (`updateSheetProperties`, `repeatCell`,
   `setDataValidation`, `insertDimension`, `deleteDimension`,
   `updateDimensionProperties`, `updateCells`, `mergeCells`, plus whatever
   `docs.documents().batchUpdate`'s `insertText` counts as in the Docs API).
   Wrapping each in its own protocol method would be nine-plus methods for
   what is, mechanically, one call shape (`{"requests": [...]}`) — the
   protocol proposal below keeps `apply_sheet_requests(spreadsheet, requests)`
   generic and lets callers build request dicts, matching current practice,
   rather than inventing a `freeze_header()`/`set_dropdown()`/`merge_cells()`
   proliferation that the real code doesn't have either. This is the opposite
   choice from (5) below for gspread's *convenience methods* — worth the
   reviewer's explicit attention, since it means the protocol is not uniform
   in how "close to the wire" it sits.
5. **Keep gspread's convenience methods (`row_values`, `update_cell`,
   `insert_cols`, `resize`, `update_title`, `append_rows`) as named protocol
   methods, not requests**, because callers already reason about them as
   distinct operations with distinct (and inconsistent!) indexing conventions
   — collapsing them into raw request objects would just relocate the
   indexing bugs rather than fix them. See the indexing table below.
6. **Collapse the four manifest/file-upload implementations and the two
   get-or-create-folder implementations into one method each**, per
   `data-layer-design.md`'s "derive, don't duplicate" principle — but expose
   the axes they currently disagree on (rename-on-update, reassert-permission,
   create-if-missing-fallback, key-reordering) as explicit parameters rather
   than silently picking one file's behavior as canonical. See the dedicated
   "Duplicate implementations to collapse" subsection below.

### Proposed method signatures

Grouped by the object they operate on. **[R]**/**[W]** marks read/write;
**[R/W]** marks a method that reads then conditionally writes.

**Session**

- `connect() -> (client, drive_service)` **[—]** — covers `_get_clients()`.
  No retry needed (auth, not data).

**Spreadsheet lifecycle**

- `create_spreadsheet(name: str) -> Spreadsheet` **[W]** — covers
  `gc.create(name)` (7 call sites across `generate_sheets.py`,
  `restructure_sheets.py`, `generate_status_sheet.py`,
  `generate_biuniqueness_stage1_sheet.py`).
- `open_spreadsheet(spreadsheet_id: str) -> Spreadsheet` **[R]** — covers
  `_open_spreadsheet`/`gc.open_by_key` (all variants: wrapped via
  `_open_spreadsheet`, bare `gc.open_by_key`, and the `refresh_dropdowns.py`
  bare-with-broad-except variant). **Always wrapped in retry** — this
  collapses the three inconsistently-retried call idioms found in part 1 into
  one, always-retried path. Raises a distinguishable not-found/no-access error
  (several callers currently catch bare `Exception` around this call and
  should be able to catch something narrower once the protocol exists).
- `spreadsheet.id -> str`, `spreadsheet.url -> str` **[R]** (cached
  attributes, not calls) — covers every `.id`/`.url` property read.
- `list_worksheets(spreadsheet) -> List[Worksheet]` **[R]** — covers
  `spreadsheet.worksheets()`. **Order matters and must be preserved**: current
  order is the tab order used for drift-detection/reordering logic in
  `generate_sheets.py`. See the "what `worksheets()` returns" subtlety below.
- `get_worksheet(spreadsheet, title: str) -> Worksheet` **[R]**, raising a
  distinguishable **not-found** condition — covers every
  `spreadsheet.worksheet(name)` / try-except-`WorksheetNotFound` call site
  (the single most common idiom in the inventory, ~15+ call sites). The
  protocol's not-found signal must be narrow enough that callers can keep
  distinguishing "tab genuinely absent" from "transient API error" —
  `refresh_dropdowns.py`'s bare `except Exception` around this call is a bug
  this protocol should make easy to avoid, not easy to keep making.
- `add_worksheet(spreadsheet, title: str, rows: int, cols: int) -> Worksheet`
  **[W]** — covers `spreadsheet.add_worksheet(...)` (6+ call sites).
- `delete_worksheet(spreadsheet, worksheet)` **[W]** — covers
  `spreadsheet.del_worksheet(ws)`.
- `reorder_worksheets(spreadsheet, ordered: List[Worksheet])` **[W]** —
  covers `spreadsheet.reorder_worksheets(...)`.

**Worksheet content**

- `get_all_values(worksheet) -> List[List[str]]` **[R]** — covers
  `ws.get_all_values()`. **Must reproduce gspread's ragged-row padding
  exactly** — see the dedicated subtlety subsection below; this is the
  single highest-risk operation for a naive fake per the plan's own callout.
- `row_values(worksheet, row: int) -> List[str]` **[R]** — covers
  `ws.row_values(1)` (9 call sites, all currently row 1 / the header). `row`
  is **1-based**, matching gspread; the protocol should keep this convention
  rather than silently 0-basing it, since every current caller already writes
  `row_values(1)` expecting "first row."
- `update(worksheet, values: List[List[str]], range_start: str = "A1", raw: bool = True)`
  **[W]** — covers every `ws.update(...)` call site. **`range_start` is an
  A1-notation anchor** (top-left cell of the write); every call site except
  `sync_params.py:258` uses `"A1"` (whole-body replace), and that one site
  uses a computed anchor (e.g. `"D1"`) to write only inserted columns. `raw`
  defaults `True` (values written literally); `generate_status_sheet.py`/
  `generate_biuniqueness_stage1_sheet.py` pass `raw=False` so embedded
  `=HYPERLINK(...)` strings are parsed as formulas — **this parameter is not
  optional to support**, it changes write semantics, not just presentation.
- `update_cell(worksheet, row: int, col: int, value: str)` **[W]** — covers
  `ws.update_cell(1, col_1based, new_name)`. **Both `row` and `col` are
  1-based** (gspread convention, made explicit in `sync_params.py`'s own
  comment). Note this is a *different* 1-basing convention from `insert_cols`
  below in the sense that it's easy to conflate "this method is 1-based" with
  "gspread is 1-based everywhere" — it is not; see the indexing table.
- `insert_cols(worksheet, columns: List[List[str]], col: int)` **[W]** —
  covers `ws.insert_cols([col_data], col=insert_col_1)`. **`col` is
  1-based.** `columns` is a list of full column value-lists (one column per
  list, `[header] + [value, value, ...]`), inserted starting at `col`.
- `append_rows(worksheet, rows: List[List[str]], value_input_option: str = "RAW")`
  **[W]** — covers `ws.append_rows(...)` (2 call sites).
- `clear(worksheet)` **[W]** — covers bare `ws.clear()`. **Only clears
  values**, not formatting or grid size — this is real Sheets API behavior
  (see `generate_sheets.py`'s `_reset_worksheet` docstring), and the protocol
  method should be documented as such rather than silently "fixed" to also
  reset formatting, since some call sites (`restructure_sheets.py`) rely on
  `clear()` *not* touching formatting on a tab that's about to be fully
  overwritten anyway.
- `resize(worksheet, rows: int, cols: int)` **[W]** — covers `ws.resize(...)`.
- `update_title(worksheet, title: str)` **[W]** — covers `ws.update_title(...)`.
- `worksheet.id`, `worksheet.title`, `worksheet.row_count`, `worksheet.col_count`
  **[R]** (cached attributes) — `row_count`/`col_count` are **not guaranteed
  fresh after an intervening write on the same handle** in current gspread
  usage (flagged under `sync_params.py` and `refresh_dropdowns.py`); the
  protocol should document whether its own handles refresh these eagerly or
  require an explicit re-fetch, since production code currently assumes the
  latter (stale-cached) behavior in at least two places.

**Structural/formatting requests (raw passthrough, per design stance #4)**

- `apply_sheet_requests(spreadsheet, requests: List[dict])` **[W]** — covers
  every `spreadsheet.batch_update({"requests": [...]})` / `ws.spreadsheet.batch_update(...)`
  call site (by far the most call sites of any single operation in the
  inventory — freeze/bold, `setDataValidation`, `repeatCell`, `updateCells`,
  `mergeCells`, `insertDimension`, `deleteDimension`,
  `updateDimensionProperties`, `updateSheetProperties`). Request dicts are
  passed through verbatim; the protocol does not need to understand their
  contents, only route them to the right spreadsheet. **This is the method
  every naive fake will get wrong first** — see the "batch_update request
  shapes" subtlety below.
- `write_value_ranges(spreadsheet, data: List[dict], value_input_option: str = "RAW")`
  **[W]** — covers the **one** `values_batch_update` call site
  (`restructure_sheets.py:628-631`). **Deliberately a separate method name
  from `apply_sheet_requests`**, per design stance #3 — `data` is a list of
  `{"range": "D5", "values": [[...]]}` dicts (A1-notation ranges + literal
  values), a completely different contract from `requests`.

**Drive files**

- `list_files(query: str, fields: str, page_size: Optional[int] = None) -> List[dict]`
  **[R]** — covers every `drive.files().list(...)` call site (5+ independent
  implementations of "find file(s) by name/parent/mimetype", see the
  duplication subsection below). `query` is passed through as a raw Drive
  query string; **the current code builds these with f-string interpolation
  of names/IDs with no escaping** (flagged under `generate_sheets.py`) — not
  a live bug today (names are internally generated) but worth the protocol
  layer at least documenting the risk rather than inheriting it silently.
- `get_file(file_id: str, fields: str) -> dict` **[R]** — covers
  `drive.files().get(fileId=..., fields=...)` (both `import_sheets.py`'s
  existence check and `_move_to_folder`'s parent lookup).
- `create_file(name: str, parents: List[str], content: Optional[bytes] = None, mimetype: Optional[str] = None) -> str`
  **[W]** — covers `drive.files().create(...)`, both the metadata-only form
  (folders, Docs) and the media-upload form (manifest.json, notebooks, PDFs).
- `update_file(file_id: str, name: Optional[str] = None, content: Optional[bytes] = None, mimetype: Optional[str] = None)`
  **[W]** — covers `drive.files().update(...)` for both rename-only
  (`restructure_sheets.py`'s archive rename) and content-replace
  (manifest/notebook/PDF updates) uses. **`name` must be optional and
  independent of content-replace** — see the duplication subsection: current
  implementations disagree on whether an update renames the file, and the
  protocol needs to let each caller choose rather than hardcoding one answer.
- `move_file(file_id: str, new_parent_id: str)` **[W]** — covers
  `_move_to_folder` (itself a `get` + `update` pair; the protocol can either
  keep that as two primitive calls or fold it into one method — folding is
  recommended since every current call site uses it as a single logical
  action and no caller needs the intermediate `parents` read).
- `download_file_json(file_id: str) -> dict` **[R]** — covers
  `_download_file_json` (chunked `MediaIoBaseDownload` + `json.loads`).
- `get_or_create_folder(name: str, parent_id: Optional[str] = None) -> str`
  **[R/W]** — covers `drive.py`'s `_get_or_create_folder` **and**
  `restructure_sheets.py`'s parallel `_get_or_create_subfolder` (see
  duplication subsection — these should become one method, not two).
  `parent_id=None` searches/creates at Drive-root level (used once, by
  `generate_status_sheet.py`, for the freestanding "Annotation Status" folder
  — a deliberate escape from an inherited-permission API limitation, not an
  oversight, and the protocol must preserve the ability to do this).

**Permissions**

- `list_permissions(file_id: str, fields: str) -> List[dict]` **[R]** —
  covers both `drive.permissions().list(...)` call sites (`fields` differs
  per caller: `permissions(id,type)` vs. `permissions(emailAddress)` — keep
  `fields` as a parameter rather than hardcoding one projection).
- `create_permission(file_id: str, type: str, role: str, email: Optional[str] = None, notify: bool = True)`
  **[W]** — covers all three `drive.permissions().create(...)` shapes found
  (`_share_anyone_with_link`, `_share_with_person`,
  `generate_notebooks.py`'s `_set_viewer_permissions`) as one parameterized
  method rather than three near-identical helpers differing only in
  `type`/`role`/`sendNotificationEmail`.
- `delete_permission(file_id: str, permission_id: str)` **[W]** — covers
  `drive.permissions().delete(...)` inside `_remove_anyone_permission`.

**Google Docs (collaborator notes)**

- `get_doc_text(doc_id: str) -> str` **[R]** — covers `_read_notes_doc_text`
  (fetch + walk `body.content[].paragraph.elements[].textRun.content`).
- `append_doc_text(doc_id: str, text: str)` **[W]** — covers
  `_append_to_notes_doc` (get, to find `endIndex`, then `batchUpdate` with an
  `insertText` request). Note this method internally does a **read then a
  write** — the protocol can either expose that as one composite call (as
  proposed here, matching current usage) or split it, but every current
  caller wants the composite behavior, so splitting would only add call sites
  without adding flexibility anyone uses today.

### Duplicate implementations to collapse (candidates, not decisions)

The inventory found the same conceptual operation implemented independently
multiple times. Collapsing these is exactly what `data-layer-design.md`
argues for ("derive, don't duplicate" / "a fact recorded in more than one
place, with no single owner"), but *which* behavior becomes canonical is a
design decision, not something this enumeration should pre-decide:

1. **"Create-or-update a Drive file with content"** — four independent
   implementations: `drive.py`'s `_upload_planars_config` (reorders manifest
   keys; update never renames; create sets no permission),
   `refresh_dropdowns.py`'s inline duplicate (no key-reordering, no
   create-fallback), `generate_notebooks.py`'s `_upload_file` +
   `_set_viewer_permissions` (update renames; permission reasserted every
   run), `generate_reports.py`'s `_upload_pdf` (update renames; permission
   set only on create). A single `update_file`/`create_file` pair (proposed
   above) needs explicit parameters for: rename-on-update (yes/no),
   reassert-permission (always/create-only/never), and whether a
   create-if-missing fallback exists when the "existing" ID doesn't resolve.
2. **"Find-or-create a folder by name inside a parent"** — two
   implementations: `drive.py`'s `_get_or_create_folder` (requests
   `files(id, name)`) and `restructure_sheets.py`'s `_get_or_create_subfolder`
   (requests `files(id)`, otherwise identical). Trivially collapsible.
3. **"Find a spreadsheet by name inside a folder"** — a related but distinct
   pattern (returns/creates a *spreadsheet*, not a folder) appearing
   independently in `generate_status_sheet.py`'s
   `_get_or_create_status_spreadsheet` and
   `generate_biuniqueness_stage1_sheet.py`'s `_get_or_create_stage1_spreadsheet`
   — identical bodies, different function names. Should become one method
   parameterized by name/folder, built from `list_files` + `create_spreadsheet`
   + `open_spreadsheet` primitives above.
4. **"Grant `anyone`-with-link access"** — `drive.py`'s
   `_share_anyone_with_link` (hardcoded `role="writer"`, used for the notes
   doc) vs. `generate_notebooks.py`'s `_set_viewer_permissions` (hardcoded
   `role="reader"`, used for notebooks/PDFs) — same call shape, should be one
   `create_permission(..., type="anyone", role=...)` call with `role` exposed,
   not two hardcoded wrappers.

### Subtleties most likely to be guessed wrong (per the plan's explicit callout)

These are elevated from the per-file tables above because the plan
specifically asked for them to be flagged prominently, not buried in file
sections — this is the section to read before writing a single line of the
fake.

**1. `get_all_values()` / `row_values()` padding and ragged rows.**
`validate_coding.py:320-321` is the only place in the codebase that states
this explicitly in a comment: *"gspread may pad with trailing empty strings
for empty cells; trim to TSV width."* Three different downstream idioms
depend on getting this right, and they are **inconsistent with each other**,
which is itself informative about what the real API actually does:
- `generate_sheets.py` (`:1191, :1807`) and `restructure_sheets.py` (`:145`)
  defensively check `len(row) >= N` / `len(row) <= max(...)` before indexing
  — written by someone who has seen ragged rows in practice.
- `import_sheets.py`'s `_read_sheet_as_df` (`:185-191`) has **no such guard**
  and feeds `get_all_values()` straight into a `pandas.DataFrame` constructor
  with the header row as columns — this would raise or silently misalign
  columns on a genuinely ragged response.
- The fact that `import_sheets.py`'s ungarded code is apparently never seen
  to fail in production suggests real Sheets responses for *that specific
  case* (a fully-written sheet1 reference tab) come back rectangular, while
  responses for partially-filled annotation tabs (the case the guarded code
  handles) do not. **A fake needs to reproduce this distinction** — i.e. pad
  ragged rows to the *used-range* width, not to a fixed header width, and the
  used range itself needs to be able to be genuinely ragged in fixtures that
  exercise the guarded code paths, and rectangular in fixtures that exercise
  `import_sheets.py`'s path — a uniformly-ragged or uniformly-rectangular
  fake would fail to exercise one code path or the other realistically.

**2. `update()` range/anchor semantics.**
Every `update()` call site in the inventory except exactly one
(`sync_params.py:258`) writes the **full sheet body starting at `"A1"`** —
i.e., in practice, "range" in this codebase almost always means "replace
everything from the top-left." The one exception writes only newly-inserted
columns at a computed anchor (e.g. `"D1"`). A fake built only against the
dominant pattern (which is what 95%+ of call sites would suggest) will not
cover `sync_params.py`'s column-insert path. Separately: `raw=True` (default,
implicit at every site except two) vs. `raw=False` (both
`generate_status_sheet.py` and `generate_biuniqueness_stage1_sheet.py`) is a
write-semantics fork, not a presentation detail — `raw=False` cells
containing `=HYPERLINK(...)` must be interpreted as formulas by anything that
later reads them back, which nothing in the current test suite exercises
(there are no goldens yet for either status-sheet generator).

**3. What `worksheets()` returns.**
Returns the live tab order, used by `generate_sheets.py`'s
`_reorder_system_tabs`/`_move_status_tab_to_end` to detect drift and
re-order. A fake that returns tabs in creation order, alphabetical order, or
any order other than "whatever order they'd currently appear in the Sheets
UI" will make every reorder-detection code path either falsely fire (thinks
reordering is needed when it isn't) or falsely stay silent (thinks tabs are
already in order when they aren't) — and either failure mode is silent, not
an exception, so it wouldn't be caught by anything except a golden that
specifically checks tab order after a mutating operation.

**4. `batch_update` request shapes.**
Nine-plus distinct request types are used across the eleven files
(enumerated under design stance #4 above). None of them are validated by the
calling code before being sent — they're just built as dicts and shipped.
This means **the fake's correctness on this operation is entirely about
faithfully modeling each request type's *effect***, not about validating
request shape (the real API does that; a fake that's lenient about malformed
requests where the real API would reject them will hide bugs). The two
request types most likely to be under-modeled because they're rare (one call
site each) are `mergeCells` (`generate_status_sheet.py`,
`generate_biuniqueness_stage1_sheet.py`) and `updateCells` (per-cell,
non-contiguous writes in `validate_coding.py`'s pink-highlight logic) —
both are easy to skip if a fake-builder samples "the common cases" rather
than reading every request type actually used.

**5. 1-indexing vs. 0-indexing has no single rule — it varies by gspread
*method*, not by axis or by file.** Consolidated from the per-file tables:

| Call | Row index | Column index |
|---|---|---|
| `ws.row_values(row)` | 1-based | — |
| `ws.update_cell(row, col)` | 1-based | 1-based |
| `ws.insert_cols(cols, col=)` | — | 1-based |
| `gspread.utils.rowcol_to_a1(row, col)` | 1-based | 1-based |
| Sheets API request `startRowIndex`/`startColumnIndex` (inside any `batch_update` request) | 0-based | 0-based |

The rule is: **gspread's own convenience methods are 1-based; raw Sheets API
request objects (everything inside a `batch_update` `requests` list) are
0-based.** This is a real, learnable rule, but it is never stated anywhere in
the current codebase — every call site just gets it right (or, in
`update_sheets.py:185`'s case, right with an explicit comment) locally. A
protocol/fake needs to enforce or at least document this split explicitly,
because it is the single most mechanical way to introduce an off-by-one that
would only surface as "wrote to the wrong column" with no error.

**6. Live handles spanning irreversible operations.**
Not a single-call subtlety but a design-level one, repeated from stance #1:
`restructure_sheets.py`'s archive-then-recreate (open `ss`, download every
tab, rename+move `ss` — destructive — then separately create and populate
`new_ss`, then write the manifest) is the clearest case, but similar chains
exist in `sync_params.py` (rename → split → merge → insert → maybe-delete,
all on one `ws`, with re-reads interleaved) and `update_sheets.py`
(mutate-then-immediately-reread-the-same-handle at `:391→393`). None of these
are journaled; none have partial-failure recovery today. A protocol that
only supports single request/response pairs, with no notion of a session or
handle spanning multiple calls with a defined partial-failure story, would
force every one of these call sites to be rewritten just to fit the seam —
which is explicitly out of scope for the *migration* phase (Phase 0b/1's
non-goal is "no refactoring of command logic beyond the call-site
substitution"). The handle-based object model in design stance #1 exists
specifically so migration can be a mechanical substitution, not a rewrite.

