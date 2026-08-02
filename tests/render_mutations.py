"""Render a fake-backend mutation log as something a person can actually read.

    python tests/render_mutations.py tests/snapshots/coordinator/refresh_dropdowns/apply_mutations.json

The raw log is faithful but opaque: spreadsheets appear as Drive IDs, tabs as
numeric `sheetId`s, and columns as 0-based indices. Reviewing it in that form
means resolving every one of those against the fixtures by hand before the log
says anything at all — which is how the second bug behind #272 (dropdowns
written onto `Source` and `Comments`) stayed hidden in a log that had already
been read once.

So this resolves each ID back to `lang/role`, each `sheetId` to its tab title,
and each column index to that tab's actual header, using the same recorded
fixtures the fake was seeded from. Reviewing writes is a step that recurs once
per migrated file (eleven times), and the plan's per-file procedure asks a human
to sign off on each one; this is what should be put in front of them.

Used by the snapshot tests to produce a `*_digest.txt` alongside each raw log, so
the readable form is the committed artifact and the diff a reviewer sees is a
diff of headers and values, not of sheet IDs.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "drive_state"

# Sheets API request types that carry no per-cell detail worth rendering.
_SUMMARY_ONLY = {"updateSheetProperties", "repeatCell", "mergeCells",
                 "updateDimensionProperties"}


def _load_fixture_names(fixture_dir: Path = FIXTURE_DIR):
    """Return (spreadsheet_id -> label, (ss_id, sheet_id) -> (title, header))."""
    labels: Dict[str, str] = {}
    tabs: Dict[Tuple[str, int], Tuple[str, List[str]]] = {}
    index_path = fixture_dir / "index.json"
    if not index_path.exists():
        return labels, tabs
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for entry in index["spreadsheets"]:
        path = ROOT / entry["path"]
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        labels[data["spreadsheet_id"]] = f"{entry['lang_id']}/{entry['role']}"
        for tab in data["worksheets"]:
            header = tab["values"][0] if tab["values"] else []
            tabs[(data["spreadsheet_id"], tab["sheet_id"])] = (tab["title"], header)
    return labels, tabs


def _column(header: List[str], index: Optional[int]) -> str:
    """Name a 0-based column index using the tab's own header."""
    if index is None:
        return "?"
    if 0 <= index < len(header) and header[index]:
        return f"col {index} ({header[index]})"
    return f"col {index} (BEYOND HEADER)"


def _grid_range(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("range", "properties"):
        value = payload.get(key)
        if isinstance(value, dict) and "sheetId" in value:
            return value
    return None


def render(mutations: List[Dict[str, Any]], fixture_dir: Path = FIXTURE_DIR) -> str:
    """Return a human-readable digest of a mutation log."""
    labels, tabs = _load_fixture_names(fixture_dir)
    lines: List[str] = []

    counts = Counter(m["op"] for m in mutations)
    lines.append("SUMMARY")
    for op, n in sorted(counts.items()):
        lines.append(f"  {n:>4}  {op}")
    request_types = Counter(m["request_type"] for m in mutations
                            if m["op"] == "batch_request")
    for kind, n in sorted(request_types.items()):
        lines.append(f"  {n:>4}    └─ {kind}")

    # Non-spreadsheet operations (Drive files, permissions, docs) read fine flat.
    other = [m for m in mutations if "spreadsheet" not in m]
    if other:
        lines.append("")
        lines.append("DRIVE OPERATIONS")
        for m in other:
            detail = ", ".join(f"{k}={v!r}" for k, v in m.items()
                               if k != "op" and v is not None)
            lines.append(f"  {m['op']}: {detail}")

    grouped: "OrderedDict[Tuple[str, str], List[Dict[str, Any]]]" = OrderedDict()
    for m in mutations:
        if "spreadsheet" not in m:
            continue
        ss_id = m["spreadsheet"]
        label = labels.get(ss_id, ss_id)
        title, _ = _resolve_tab(m, ss_id, tabs)
        grouped.setdefault((label, title), []).append(m)

    if grouped:
        lines.append("")
        lines.append("SHEET OPERATIONS")
    for (label, title), entries in grouped.items():
        lines.append("")
        lines.append(f"  {label}  tab={title}")
        for m in entries:
            for line in _render_entry(m, tabs):
                lines.append(f"    {line}")

    return "\n".join(lines) + "\n"


def _resolve_tab(m: Dict[str, Any], ss_id: str, tabs) -> Tuple[str, List[str]]:
    """Best-effort (title, header) for one mutation entry."""
    if m.get("worksheet"):
        for (sid, _), (title, header) in tabs.items():
            if sid == ss_id and title == m["worksheet"]:
                return title, header
        return m["worksheet"], []
    grid = _grid_range(m.get("payload", {}))
    if grid is not None:
        return tabs.get((ss_id, grid["sheetId"]), (f"sheetId={grid['sheetId']}", []))
    return "-", []


def _render_entry(m: Dict[str, Any], tabs) -> List[str]:
    op = m["op"]
    _, header = _resolve_tab(m, m["spreadsheet"], tabs)

    if op == "batch_request":
        kind = m["request_type"]
        payload = m["payload"]
        if kind == "setDataValidation":
            rng = payload["range"]
            values = [v["userEnteredValue"]
                      for v in payload["rule"]["condition"]["values"]]
            return [f"{kind}: {_column(header, rng.get('startColumnIndex'))} "
                    f"rows {rng.get('startRowIndex')}-{rng.get('endRowIndex')} "
                    f"-> {values} (strict={payload['rule'].get('strict')})"]
        if kind in _SUMMARY_ONLY:
            rng = _grid_range(payload) or {}
            span = ""
            if "startColumnIndex" in rng:
                span = f" {_column(header, rng.get('startColumnIndex'))}"
            if "startRowIndex" in rng:
                span += f" rows {rng.get('startRowIndex')}-{rng.get('endRowIndex')}"
            return [f"{kind}:{span or ' (whole sheet)'}"]
        return [f"{kind}: {json.dumps(payload)[:160]}"]

    if op == "update":
        return [f"update: anchor {m['range']} raw={m['raw']} "
                f"{m['rows']}x{m['cols']}"] + [
            f"  | {row}" for row in m["values"][:3]] + (
            ["  | ..."] if len(m["values"]) > 3 else [])

    if op in {"append_rows", "insert_cols"}:
        return [f"{op}: {json.dumps({k: v for k, v in m.items() if k not in {'op', 'spreadsheet', 'worksheet', 'values'}})}"] + [
            f"  | {row}" for row in m.get("values", [])[:3]]

    return [f"{op}: " + ", ".join(f"{k}={v!r}" for k, v in m.items()
                                  if k not in {"op", "spreadsheet", "worksheet"})]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: python {sys.argv[0]} <mutation_log.json>")
    mutations = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(render(mutations))


if __name__ == "__main__":
    main()
