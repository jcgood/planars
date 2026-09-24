"""Export the `cross_language` data bundle for the `planarsviz` R package.

Sets every language structure's own bundle side by side: nyan1308 and the 21
CCDB structures, 22 in all. Plan: docs/PLAN_cross_language_charts.md; state:
docs/CROSS_LANGUAGE_PROGRESS.md (which also records Jeff's four answers,
2026-09-23, that the rules below carry out).

**It re-runs no analysis.** Every number it writes is read from, or worked
out by arithmetic on, the tables already in
results/chart_data/<dataset>/data/. The one exception is chart C's label
shuffle (below), which moves domain-type labels around a conflict list the
bundle already holds; no family is enumerated. Every per-language bundle
is left untouched.

Tables written to results/chart_data/cross_language/data/:

- `structures.tsv`: one row per structure -- names, planar type, counts,
  root position, and `source` (`ccdb`, or `nyan1308` for the one structure
  not from CCDB, which the charts mark).
- `family_count_tests.tsv` (charts A, B, C's companion panel): the
  span-placement and arbitrary-layers tests' rows for three roles -- `all`
  (every test pooled), `syntax_side` and `phonology_side` (see SIDES) --
  with the observed count and null percentiles also divided by the null
  median, so 1 means "what chance gives" whatever the structure's size.
- `pooled_tests.tsv`: across all structures, per null and role, how many
  fall below / above / on their null median, a one-sided sign test (ties
  left out), and Fisher's combination of the per-structure p-values (Jeff
  asked for both, 2026-09-23). Structures share test batteries, authors and
  sometimes language families, so neither is a clean independent test; the
  charts and docs say so wherever they are quoted.
- `conflict_divide.tsv` (chart C): where each structure's conflicting span
  pairs fall relative to the morphosyntax/phonology divide. See CHART C RULE.
- `boundary_profile.tsv` (chart D): each position's summed boundary
  strength, left and right, re-numbered relative to the root and scaled by
  that structure's largest value, with the jump test's p-value.
- `convergent_spans.tsv` (chart E): each structure's most convergent spans
  (up to three convergence ranks, ties kept), on the same root-relative axis.
- `summary.tsv` (table F): one row per structure, the numbers above in one
  place. `--apply` also writes it as Markdown and LaTeX to
  results/cross_language/.
- `metadata.json`: every input bundle's dataset and the SHA-256 of its
  metadata.json, so a cross-language bundle left behind by a re-export can
  be detected (tests/test_planarsviz_cross_language_bundle.py checks it).

SIDES. Which domain types count as the syntax side and which as the
phonology side, per the input bundle's `groupings`. CCDB: morphosyntactic
and indeterminate against phonological (Jeff: indeterminate goes with
syntax -- the `morsyn_indet` bundle). nyan1308: its own `syntaxlike`
(morphosyntactic, tonosegmental, length) against `phonologylike`
(phonological, intonational) -- Jeff, when asked again. Both are read from
planars_groupings.py so there is no second copy. A domain type on neither
side stops the export.

CHART C RULE. A span's sides are the sides of the domain types of the tests
that pick it out, so a span can be on one side or both. A conflicting pair is
*within* a side if both spans are on that side (tests of the same class
disagree about nesting -- what hypothesis (ii) says should not happen), and
*between* only if their sides are disjoint (one span purely syntax, the other
purely phonology -- what it allows). A pair with a span on both sides always
counts as within, since it shares a side with anything. The baseline is the
share of *all* span pairs that are between; that is also exactly the mean
share under shuffling the spans' side sets around a fixed conflict list,
which gives the p-value (share between >= observed; 5000 shuffles, seed 0,
by default). Synthetic spans (a full-structure span the exporter adds when a
structure has none) are left out; they never conflict.

Usage (from NonCollaborative/):
    python scripts/analysis/export_cross_language.py            # dry run
    python scripts/analysis/export_cross_language.py --apply
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import unicodedata
from itertools import combinations
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from planars_groupings import GROUPINGS  # noqa: E402

CONTRACT_VERSION = 1
DATASET = "cross_language"
# Bundles in results/chart_data/ that are not a language structure.
NOT_STRUCTURES = {"illustrations", "shifted_nyan", DATASET}
NULLS = ("span_placement", "arbitrary_layers")
ROLES = ("all", "syntax_side", "phonology_side")
# Chichewa's metadata.json predates the planar_type field (CCDB bundles carry
# it); its planar structure is the verb's.
PLANAR_TYPE_FALLBACK = {"nyan1308": "verbal"}


def _bundle_types(grouping, name):
    for bundle_name, types, _colour, _label in GROUPINGS[grouping]["bundles"]:
        if bundle_name == name:
            return bundle_name, list(types)
    raise KeyError(f"grouping {grouping!r} has no bundle {name!r}")


# role -> (group row to read in the test tables, the domain types on it)
SIDES = {
    "ccdb": {
        "syntax_side": _bundle_types("ccdb", "morsyn_indet"),
        "phonology_side": ("phonological", ["phonological"]),
    },
    "chichewa": {
        "syntax_side": _bundle_types("chichewa", "syntaxlike"),
        "phonology_side": _bundle_types("chichewa", "phonologylike"),
    },
}


def read_tsv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_tsv(rows, path):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(x, digits=4):
    return "" if x is None else round(float(x), digits)


def structure_dirs(chart_data):
    return sorted(
        d for d in chart_data.iterdir()
        if d.is_dir() and d.name not in NOT_STRUCTURES and (d / "data" / "metadata.json").exists()
    )


def load(bundle_dir):
    data = bundle_dir / "data"
    meta = json.loads((data / "metadata.json").read_text())
    for flag in ("span_placement_permutations", "arbitrary_layers_permutations",
                 "boundary_strength_test_permutations"):
        if not meta.get(flag):
            raise SystemExit(f"{bundle_dir.name}: bundle was exported without --{flag.replace('_', '-')}; "
                             "re-export it with all four permutation flags (see NextPrompt.md).")
    return {
        "dir": bundle_dir,
        "meta": meta,
        "meta_sha256": sha256(data / "metadata.json"),
        "spans": read_tsv(data / "spans.tsv"),
        "conflicts": read_tsv(data / "conflict_pairs.tsv"),
        "boundary": read_tsv(data / "boundary_strength.tsv"),
        "boundary_test": read_tsv(data / "boundary_strength_test.tsv"),
        "span_placement": read_tsv(data / "span_placement_test.tsv"),
        "arbitrary_layers": read_tsv(data / "arbitrary_layers_test.tsv"),
        "fragmentation": read_tsv(data / "fragmentation_test.tsv") if (data / "fragmentation_test.tsv").exists() else [],
    }


def structure_row(b):
    m = b["meta"]
    ds = m["dataset"]
    ccdb_json = REPO_DIR / "planar_tables" / f"ccdb_{ds}.json"
    if ccdb_json.exists():
        ccdb = json.loads(ccdb_json.read_text())
        # The CCDB import files hold names with accents as separate combining
        # characters (San Martín is "i" + U+0301), which PDF devices draw
        # beside the letter rather than over it; the per-language bundles
        # already hold the composed form, so compose here too.
        language = unicodedata.normalize("NFC", ccdb["language_name"])
        source, language_id = "ccdb", ccdb["language_id"]
    else:
        source, language, language_id = ds, m["language_name"], ds
    planar_type = m.get("planar_type") or PLANAR_TYPE_FALLBACK[ds]
    return {
        "dataset": ds,
        "source": source,
        "language": language,
        "language_id": language_id,
        "planar_type": planar_type,
        "label": f"{language} ({planar_type})",
        "groupings": m["groupings"],
        "n_positions": m["n_positions"],
        "root_position": m["root_position"],
        "n_active_tests": m["n_active_tests"],
        "n_unique_spans": m["n_unique_spans"],
        "n_maximal_families": m["n_maximal_families"],
        "n_conflict_pairs": m["n_conflict_pairs"],
    }


def family_count_rows(b):
    ds = b["meta"]["dataset"]
    sides = SIDES[b["meta"]["groupings"]]
    groups = {"all": "all", **{role: group for role, (group, _types) in sides.items()}}
    rows = []
    for null in NULLS:
        by_group = {r["group"]: r for r in b[null]}
        for role in ROLES:
            r = by_group[groups[role]]
            median = float(r["null_p50"])
            n_perm = int(r["n_permutations"])
            p = float(r["p_value_le_observed"])
            rows.append({
                "dataset": ds,
                "null": null,
                "role": role,
                "group": r["group"],
                "n_spans": r["n_spans"],
                "observed_families": r["observed_families"],
                "null_mean": r["null_mean"],
                "null_p05": r["null_p05"],
                "null_p50": r["null_p50"],
                "null_p95": r["null_p95"],
                "observed_ratio": fmt(float(r["observed_families"]) / median),
                "null_p05_ratio": fmt(float(r["null_p05"]) / median),
                "null_p95_ratio": fmt(float(r["null_p95"]) / median),
                "p_value_le_observed": r["p_value_le_observed"],
                # The stored p is k/N; Fisher needs it never to be 0, so it
                # uses (k + 1) / (N + 1), the usual permutation-test form.
                "p_value_corrected": fmt((round(p * n_perm) + 1) / (n_perm + 1), 6),
                "n_permutations": n_perm,
            })
    return rows


def binomial_upper(k, n):
    """P(X >= k) for X ~ Binomial(n, 1/2)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def chi2_sf_even_df(x, df):
    """Survival function of chi-squared with an even df (Fisher's method
    always has df = 2k), in closed form: exp(-x/2) * sum_{i<k} (x/2)^i / i!."""
    half = x / 2
    return math.exp(-half) * sum(half ** i / math.factorial(i) for i in range(df // 2))


def pooled_rows(fc_rows):
    rows = []
    for null in NULLS:
        for role in ROLES:
            sel = [r for r in fc_rows if r["null"] == null and r["role"] == role]
            below = sum(float(r["observed_families"]) < float(r["null_p50"]) for r in sel)
            above = sum(float(r["observed_families"]) > float(r["null_p50"]) for r in sel)
            ties = len(sel) - below - above
            chi2 = -2 * sum(math.log(float(r["p_value_corrected"])) for r in sel)
            df = 2 * len(sel)
            rows.append({
                "null": null,
                "role": role,
                "n_structures": len(sel),
                "n_below_median": below,
                "n_above_median": above,
                "n_at_median": ties,
                "sign_test_p": fmt(binomial_upper(below, below + above), 6),
                "n_p_below_05": sum(float(r["p_value_le_observed"]) < 0.05 for r in sel),
                "fisher_chi2": fmt(chi2, 3),
                "fisher_df": df,
                "fisher_p": fmt(chi2_sf_even_df(chi2, df), 8),
            })
    return rows


def span_sides(b):
    """span_id -> frozenset of sides, for every non-synthetic span."""
    side_of = {}
    for role, (_group, types) in SIDES[b["meta"]["groupings"]].items():
        for t in types:
            side_of[t] = role
    out = {}
    for s in b["spans"]:
        if s["synthetic"] == "True":
            continue
        sides = set()
        for t in s["domain_types"].split("|"):
            if t not in side_of:
                raise SystemExit(f"{b['meta']['dataset']}: domain type {t!r} is on neither side of the divide "
                                 "(SIDES in export_cross_language.py)")
            sides.add(side_of[t])
        out[s["span_id"]] = frozenset(sides)
    return out


def pair_kind(a, b):
    shared = a & b
    if not shared:
        return "between"
    if shared == {"syntax_side", "phonology_side"}:
        return "within_both"
    return "within_" + next(iter(shared)).replace("_side", "")


def conflict_divide_row(b, n_shuffles, seed):
    ds = b["meta"]["dataset"]
    sides = span_sides(b)
    for c in b["conflicts"]:
        for key in ("span_id_a", "span_id_b"):
            if c[key] not in sides:
                raise SystemExit(f"{ds}: conflict pair names span {c[key]} that is synthetic or missing")
    conflicts = [(c["span_id_a"], c["span_id_b"]) for c in b["conflicts"]]
    kinds = [pair_kind(sides[a], sides[bb]) for a, bb in conflicts]
    ids = sorted(sides)
    all_pairs = list(combinations(ids, 2))
    n_between_all = sum(pair_kind(sides[a], sides[bb]) == "between" for a, bb in all_pairs)
    observed = kinds.count("between")

    # Shuffle: the same side sets, dealt to the spans at random, conflict list
    # fixed. Seeded per structure from its name, so adding a structure does
    # not change any other structure's draws.
    rng = random.Random(f"{seed}:{ds}")
    labels = [sides[i] for i in ids]
    index = {span: k for k, span in enumerate(ids)}
    hits = 0
    for _ in range(n_shuffles):
        rng.shuffle(labels)
        n = sum(not (labels[index[a]] & labels[index[bb]]) for a, bb in conflicts)
        hits += n >= observed
    n_conf = len(conflicts)
    counts = {s: sum(v == frozenset({s}) for v in sides.values()) for s in ("syntax_side", "phonology_side")}
    return {
        "dataset": ds,
        "n_spans": len(ids),
        "n_spans_syntax_only": counts["syntax_side"],
        "n_spans_phonology_only": counts["phonology_side"],
        "n_spans_both": sum(len(v) == 2 for v in sides.values()),
        "n_conflict_pairs": n_conf,
        "n_between": observed,
        "n_within_syntax": kinds.count("within_syntax"),
        "n_within_phonology": kinds.count("within_phonology"),
        "n_within_both": kinds.count("within_both"),
        "share_between": fmt(observed / n_conf) if n_conf else "",
        "n_span_pairs": len(all_pairs),
        "expected_share_between": fmt(n_between_all / len(all_pairs)) if all_pairs else "",
        "p_value_ge_observed": fmt(hits / n_shuffles) if n_conf else "",
        "n_shuffles": n_shuffles,
        "seed": seed,
    }


def boundary_rows(b):
    ds = b["meta"]["dataset"]
    root = int(b["meta"]["root_position"])
    jump_p = {
        (r["side"], int(r["position"])): float(r["p_value_ge_observed"])
        for r in b["boundary_test"] if r["group"] == "all" and r["statistic"] == "jump"
    }
    values = [(int(r["position"]), side, float(r[f"{side}_summed"]))
              for r in b["boundary"] for side in ("left", "right")]
    top = max(v for _p, _s, v in values) or 1.0
    return [{
        "dataset": ds,
        "position": p,
        "relative_position": p - root,
        "side": side,
        "summed": int(v),
        "scaled": fmt(v / top),
        "jump_p_value_ge_observed": jump_p[(side, p)],
        "jump_significant": "y" if jump_p[(side, p)] < 0.05 else "n",
    } for p, side, v in values]


def convergent_rows(b, n_ranks):
    ds = b["meta"]["dataset"]
    root = int(b["meta"]["root_position"])
    n_pos = int(b["meta"]["n_positions"])
    n_tests = int(b["meta"]["n_active_tests"])
    spans = [s for s in b["spans"] if s["synthetic"] != "True"]
    levels = sorted({int(s["convergence"]) for s in spans}, reverse=True)[:n_ranks]
    rows = []
    for s in sorted(spans, key=lambda s: (-int(s["convergence"]), int(s["size"]), int(s["left"]))):
        conv = int(s["convergence"])
        if conv not in levels:
            continue
        left, right = int(s["left"]), int(s["right"])
        rows.append({
            "dataset": ds,
            "span_id": s["span_id"],
            "convergence_rank": levels.index(conv) + 1,
            "left": left,
            "right": right,
            "relative_left": left - root,
            "relative_right": right - root,
            "size": int(s["size"]),
            "relative_size": fmt(int(s["size"]) / n_pos),
            "contains_root": "y" if left <= root <= right else "n",
            "convergence": conv,
            "share_of_tests": fmt(conv / n_tests),
            "domain_types": s["domain_types"],
        })
    return rows


def summary_rows(structures, fc, divide, boundary, convergent, bundles):
    out = []
    for s in structures:
        ds = s["dataset"]
        f = {(r["null"], r["role"]): r for r in fc if r["dataset"] == ds}
        d = next(r for r in divide if r["dataset"] == ds)
        strongest = max((r for r in boundary if r["dataset"] == ds), key=lambda r: (r["summed"], r["side"] == "left"))
        top = next(r for r in convergent if r["dataset"] == ds)
        frag = {r["group"]: r for r in bundles[ds]["fragmentation"]}
        sides = SIDES[s["groupings"]]
        out.append({
            "dataset": ds,
            "label": s["label"],
            "source": s["source"],
            "planar_type": s["planar_type"],
            "n_positions": s["n_positions"],
            "n_active_tests": s["n_active_tests"],
            "n_unique_spans": s["n_unique_spans"],
            "families_all": f[("span_placement", "all")]["observed_families"],
            "families_syntax_side": f[("span_placement", "syntax_side")]["observed_families"],
            "families_phonology_side": f[("span_placement", "phonology_side")]["observed_families"],
            "span_placement_p": f[("span_placement", "all")]["p_value_le_observed"],
            "arbitrary_layers_p": f[("arbitrary_layers", "all")]["p_value_le_observed"],
            "fragmentation_p_syntax_side": frag.get(sides["syntax_side"][0], {}).get("p_value_le_observed", ""),
            "fragmentation_p_phonology_side": frag.get(sides["phonology_side"][0], {}).get("p_value_le_observed", ""),
            "conflicts_between": d["n_between"],
            "conflicts": d["n_conflict_pairs"],
            "strongest_edge_side": strongest["side"],
            "strongest_edge_relative_position": strongest["relative_position"],
            "most_convergent_span": f"{top['relative_left']}..{top['relative_right']}",
            "most_convergent_span_tests": top["convergence"],
        })
    return out


def tex_escape(text):
    return str(text).replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


SUMMARY_COLUMNS = [
    ("label", "Structure"), ("n_positions", "Pos."), ("n_active_tests", "Tests"),
    ("n_unique_spans", "Spans"), ("families_all", "Fam."), ("families_syntax_side", "Fam. syn."),
    ("families_phonology_side", "Fam. phon."), ("span_placement_p", "p placement"),
    ("arbitrary_layers_p", "p layers"), ("conflicts_between", "Confl. betw."), ("conflicts", "Confl."),
    ("strongest_edge_relative_position", "Strongest edge"), ("most_convergent_span", "Top span"),
]


def edge_text(r):
    position = int(r["strongest_edge_relative_position"])
    return f"{r['strongest_edge_side']} {position:+d}" if position else f"{r['strongest_edge_side']} 0"


def cell(r, key):
    if key == "strongest_edge_relative_position":
        return edge_text(r)
    if key == "label" and r["source"] != "ccdb":
        return f"{r['label']} *"
    return str(r[key])


def summary_markdown(rows, pooled):
    lines = [
        "# Cross-language summary",
        "",
        "One row per structure. Positions in the last two columns are relative to the root (root = 0).",
        "`p placement` / `p layers`: one-sided p-value that chance gives as few families as observed, on the",
        "span-placement and arbitrary-layers nulls. `Confl. betw.`: conflicting span pairs that fall wholly",
        "across the morphosyntax/phonology divide. * = not from CCDB (Chichewa).",
        "Written by scripts/analysis/export_cross_language.py; do not edit by hand.",
        "",
        "| " + " | ".join(h for _k, h in SUMMARY_COLUMNS) + " |",
        "|" + "|".join("---" for _ in SUMMARY_COLUMNS) + "|",
    ]
    lines += ["| " + " | ".join(cell(r, k) for k, _h in SUMMARY_COLUMNS) + " |" for r in rows]
    lines += ["", "## Across all structures", "",
              "Structures share test batteries, authors and in some cases language families, so neither",
              "figure below is a test on independent cases.", "",
              "| Null | Which tests | Below / above / at median | Sign test p | Fisher p |", "|---|---|---|---|---|"]
    for p in pooled:
        lines.append(f"| {p['null'].replace('_', ' ')} | {p['role'].replace('_', ' ')} | "
                     f"{p['n_below_median']} / {p['n_above_median']} / {p['n_at_median']} | "
                     f"{p['sign_test_p']} | {p['fisher_p']} |")
    return "\n".join(lines) + "\n"


def summary_latex(rows):
    head = " & ".join(tex_escape(h) for _k, h in SUMMARY_COLUMNS)
    body = [" & ".join(tex_escape(cell(r, k)) for k, _h in SUMMARY_COLUMNS) + r" \\" for r in rows]
    return "\n".join([
        "% Written by scripts/analysis/export_cross_language.py; do not edit by hand.",
        r"\begin{tabular}{l" + "r" * (len(SUMMARY_COLUMNS) - 1) + "}",
        r"\hline",
        head + r" \\",
        r"\hline",
        *body,
        r"\hline",
        r"\end{tabular}",
    ]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write the bundle (default: dry run).")
    parser.add_argument("--chart-data", type=Path, default=REPO_DIR / "results" / "chart_data")
    parser.add_argument("--tables-dir", type=Path, default=REPO_DIR / "results" / DATASET,
                        help="Where the Markdown and LaTeX summary tables go.")
    parser.add_argument("--shuffles", type=int, default=5000, help="Label shuffles for chart C (default 5000).")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--convergence-ranks", type=int, default=3)
    args = parser.parse_args()

    bundles = {d.name: load(d) for d in structure_dirs(args.chart_data)}
    for name, b in bundles.items():
        if b["meta"]["dataset"] != name:
            raise SystemExit(f"{name}: metadata.json names dataset {b['meta']['dataset']!r}")
    structures = sorted((structure_row(b) for b in bundles.values()), key=lambda r: r["dataset"])
    fc = [r for b in bundles.values() for r in family_count_rows(b)]
    pooled = pooled_rows(fc)
    divide = [conflict_divide_row(b, args.shuffles, args.seed) for b in bundles.values()]
    boundary = [r for b in bundles.values() for r in boundary_rows(b)]
    convergent = [r for b in bundles.values() for r in convergent_rows(b, args.convergence_ranks)]
    summary = summary_rows(structures, fc, divide, boundary, convergent, bundles)
    # The table reads by language name; every other table stays in dataset order.
    table_rows = sorted(summary, key=lambda r: r["label"])

    tables = {
        "structures.tsv": structures,
        "family_count_tests.tsv": fc,
        "pooled_tests.tsv": pooled,
        "conflict_divide.tsv": divide,
        "boundary_profile.tsv": boundary,
        "convergent_spans.tsv": convergent,
        "summary.tsv": summary,
    }
    metadata = {
        "contract_version": CONTRACT_VERSION,
        "dataset": DATASET,
        "producer": "scripts/analysis/export_cross_language.py",
        "n_structures": len(structures),
        "inputs": [{"dataset": ds, "metadata_sha256": bundles[ds]["meta_sha256"]} for ds in sorted(bundles)],
        "sides": {g: {role: {"group": grp, "domain_types": types} for role, (grp, types) in s.items()}
                  for g, s in SIDES.items()},
        "conflict_divide": {"n_shuffles": args.shuffles, "seed": args.seed},
        "convergence_ranks": args.convergence_ranks,
    }

    print(f"{len(structures)} structures: {', '.join(s['dataset'] for s in structures)}")
    for p in pooled:
        print(f"  {p['null']:17s} {p['role']:15s} below/above/at median {p['n_below_median']}/"
              f"{p['n_above_median']}/{p['n_at_median']}  sign p={p['sign_test_p']}  Fisher p={p['fisher_p']}")
    between = sum(d["n_between"] for d in divide)
    total = sum(d["n_conflict_pairs"] for d in divide)
    print(f"  conflicts across the divide: {between} of {total}")
    if not args.apply:
        for name, rows in tables.items():
            print(f"would write {name} ({len(rows)} rows)")
        print("Dry run; pass --apply to write.")
        return

    data_dir = args.chart_data / DATASET / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        write_tsv(rows, data_dir / name)
        print(f"wrote {data_dir / name} ({len(rows)} rows)")
    (data_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {data_dir / 'metadata.json'}")
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    (args.tables_dir / "cross_language_summary.md").write_text(summary_markdown(table_rows, pooled), encoding="utf-8")
    (args.tables_dir / "cross_language_summary.tex").write_text(summary_latex(table_rows), encoding="utf-8")
    print(f"wrote {args.tables_dir / 'cross_language_summary.md'} and .tex")


if __name__ == "__main__":
    main()
