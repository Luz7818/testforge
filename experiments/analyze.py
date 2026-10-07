"""Statistical analysis of an experiment grid -> analysis.md + analysis.json.

Implements the paired comparisons behind the four research questions, with a
manual Wilcoxon signed-rank test (normal approximation; noted in the report)
and bootstrap confidence intervals — no heavyweight dependencies.

    python experiments/analyze.py --exp results/exp_mock_20260919_120000
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testforge.utils import write_json

RQ_MAP = {
    "RQ1": ("B0", "B1", "Can single-shot LLM tests improve fault detection beyond the existing suite?"),
    "RQ2": ("B1", "B3", "Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?"),
    "RQ3": ("B1", "B2", "What does the quality gate contribute on its own (reliability vs raw generation)?"),
    "RQ4": ("B3", "B4", "Ablation: mutant-survivor feedback vs coverage-gap feedback."),
    "RQ5": ("B2", "B5", "Does spending the feedback-round budget after zero-acceptance rounds recover surviving mutants?"),
}


def _mean(xs):
    return statistics.fmean(xs) if xs else float("nan")


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


def _stdev(xs):
    return statistics.stdev(xs) if len(xs) >= 2 else 0.0


def _ranks(xs):
    """Average ranks (1-based) with tie handling."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon_signed_rank(diffs: list[float]) -> dict:
    """Two-sided Wilcoxon signed-rank test, normal approximation (with tie
    correction). Returns {n, W_plus, z, p}. Honest about small n in callers."""
    d = [x for x in diffs if abs(x) > 1e-12]
    n = len(d)
    if n == 0:
        return {"n": 0, "W_plus": 0.0, "z": 0.0, "p": 1.0}
    ranks = _ranks([abs(x) for x in d])
    # tie correction on |d|
    abs_vals = sorted(abs(x) for x in d)
    tie_term = 0.0
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs_vals[j + 1] == abs_vals[i]:
            j += 1
        t = j - i + 1
        if t > 1:
            tie_term += t**3 - t
        i = j + 1
    w_plus = sum(r for r, x in zip(ranks, d) if x > 0)
    mu = n * (n + 1) / 4
    sigma2 = n * (n + 1) * (2 * n + 1) / 24 - tie_term / 48
    sigma = math.sqrt(max(sigma2, 1e-12))
    z = (w_plus - mu) / sigma
    p = math.erfc(abs(z) / math.sqrt(2))  # two-sided
    return {"n": n, "W_plus": w_plus, "z": round(z, 3), "p": round(p, 4)}


def bootstrap_ci(diffs: list[float], n_boot: int = 10000, seed: int = 7, level: float = 0.95):
    rng = random.Random(seed)
    if not diffs:
        return {"lo": float("nan"), "hi": float("nan")}
    means = sorted(_mean([rng.choice(diffs) for _ in diffs]) for _ in range(n_boot))
    alpha = (1 - level) / 2
    return {
        "lo": round(means[int(alpha * n_boot)], 4),
        "hi": round(means[int((1 - alpha) * n_boot)], 4),
    }


def paired(rows: list[dict], va: str, vb: str, metric: str) -> list[dict]:
    """Per-target pairs for variant va (treatment) minus vb (baseline)."""
    by = {(r["target_id"], r["variant"]): r for r in rows if "error" not in r}
    targets = sorted({r["target_id"] for r in rows if "error" not in r})
    out = []
    for t in targets:
        a, b = by.get((t, va)), by.get((t, vb))
        if a and b and a.get(metric) is not None and b.get(metric) is not None:
            out.append({"target": t, "a": a[metric], "b": b[metric], "diff": a[metric] - b[metric]})
    return out


def fmt_pct(x):
    return f"{100 * x:.1f}%"


def priced(rows: list[dict]) -> list[dict]:
    """Rows whose cost carries explicit price provenance. Legacy v0.1 archives
    contain USD numbers computed from undocumented placeholder rates — they are
    treated as unpriced so a stale figure can never masquerade as sourced."""
    out = []
    for r in rows:
        cost = r.get("cost", {})
        if cost.get("cost_usd") is not None and cost.get("price_source"):
            out.append(r)
    return out


def grid_label(rows: list[dict]) -> str:
    models = sorted({r.get("cost", {}).get("model", "") for r in rows if "error" not in r})
    model = next((m for m in models if m and m != "mock"), models[0] if models else "")
    return model or "grid"


def cross_model_section(rows_a: list[dict], rows_b: list[dict], label_b: str | None = None):
    """Paired comparison of two grids (e.g. two model scales) on the shared
    (target, variant) cells. Returns (markdown lines, json block)."""
    la, lb = grid_label(rows_a), label_b or grid_label(rows_b)
    ok_a = [r for r in rows_a if "error" not in r]
    ok_b = [r for r in rows_b if "error" not in r]
    variants = sorted({r["variant"] for r in ok_a} & {r["variant"] for r in ok_b})

    lines: list[str] = [f"## Cross-model comparison: {la} vs {lb}\n"]
    lines.append(f"Grids paired on the (target, variant) cells present in both; grid A = {la} (this analysis), grid B = {lb}.\n")
    lines.append("| Variant | mean MS(all) A | mean MS(all) B | Δ (B − A) |")
    lines.append("|---|---|---|---|")
    variant_json: dict = {}
    for v in variants:
        ms_a = _mean([r["ms_all"] for r in ok_a if r["variant"] == v])
        ms_b = _mean([r["ms_all"] for r in ok_b if r["variant"] == v])
        lines.append(f"| {v} | {fmt_pct(ms_a)} | {fmt_pct(ms_b)} | {ms_b - ms_a:+.1%} |")
        variant_json[v] = {"ms_all_mean_a": ms_a, "ms_all_mean_b": ms_b, "delta_b_minus_a": ms_b - ms_a}
    lines.append("")

    cmp_json: dict = {"grid_a": la, "grid_b": lb, "variants": variant_json}

    def _rq_block(name: str, rows: list[dict], base: str, treat: str) -> dict | None:
        pairs = paired(rows, treat, base, "ms_all")
        diffs = [p["diff"] for p in pairs]
        if not diffs:
            return None
        stats = wilcoxon_signed_rank(diffs)
        ci = bootstrap_ci(diffs)
        wins = sum(d > 1e-9 for d in diffs)
        ties = sum(abs(d) <= 1e-9 for d in diffs)
        losses = sum(d < -1e-9 for d in diffs)
        lines.append(f"- **{name} — {treat} vs {base}**: mean uplift {_mean(diffs):+.1%} "
                     f"(median {_median(diffs):+.1%}); {wins}/{ties}/{losses} win/tie/loss; "
                     f"Wilcoxon p={stats['p']}, bootstrap 95% CI [{ci['lo']:+.1%}, {ci['hi']:+.1%}] (n={len(diffs)})")
        return {"mean_uplift": _mean(diffs), "wilcoxon_p": stats["p"], "ci": ci,
                "wins_ties_losses": [wins, ties, losses], "n": len(diffs)}

    lines.append("### Generation uplift per grid (RQ1, B1 − B0)\n")
    rq1 = {}
    for name, rows in ((la, rows_a), (lb, rows_b)):
        block = _rq_block(name, rows, "B0", "B1")
        if block:
            rq1[name] = block
    lines.append("")
    cmp_json["rq1_b1_minus_b0"] = rq1

    lines.append("### Gate contribution per grid (RQ3, accepted tests/target)\n")
    lines.append("| Grid | B1 accepted/target | B2 accepted/target | ratio B2/B1 |")
    lines.append("|---|---|---|---|")
    gate_json = {}
    for name, rows in ((la, rows_a), (lb, rows_b)):
        b1 = [r["n_accepted"] for r in rows if r.get("variant") == "B1" and "error" not in r]
        b2 = [r["n_accepted"] for r in rows if r.get("variant") == "B2" and "error" not in r]
        if b1 and b2:
            m1, m2 = _mean(b1), _mean(b2)
            ratio = m2 / m1 if m1 > 0 else float("nan")
            lines.append(f"| {name} | {m1:.2f} | {m2:.2f} | {ratio:.2f} |")
            gate_json[name] = {"b1_acc": m1, "b2_acc": m2, "ratio": ratio}
    lines.append("")
    cmp_json["gate_b1_vs_b2"] = gate_json

    tok = {}
    for name, rows in ((la, rows_a), (lb, rows_b)):
        t_in = sum(r.get("cost", {}).get("tokens_in", 0) for r in rows if "error" not in r)
        t_out = sum(r.get("cost", {}).get("tokens_out", 0) for r in rows if "error" not in r)
        if t_in or t_out:
            tok[name] = {"tokens_in": t_in, "tokens_out": t_out}
    if tok:
        lines.append("### LLM token totals per grid\n")
        lines.append("| Grid | tokens in | tokens out |")
        lines.append("|---|---|---|")
        for name, t in tok.items():
            lines.append(f"| {name} | {t['tokens_in']:,} | {t['tokens_out']:,} |")
        lines.append("")
        cmp_json["tokens"] = tok
    return lines, cmp_json


def analyze(rows: list[dict], out_dir: Path, compare_rows: list[dict] | None = None, compare_label: str | None = None) -> None:
    variants = sorted({r["variant"] for r in rows if "error" not in r})
    n_targets = len({r["target_id"] for r in rows if "error" not in r})
    errors = [r for r in rows if "error" in r]

    lines: list[str] = []
    lines.append("# TestForge experiment analysis\n")
    lines.append(
        f"Grid: {n_targets} targets x {len(variants)} variants ({', '.join(variants)}); "
        f"{len(errors)} cell(s) errored.\n"
    )
    if errors:
        lines.append("| target | variant | error |")
        lines.append("|---|---|---|")
        for r in errors:
            lines.append(f"| {r['target_id']} | {r['variant']} | {r['error'][:60]} |")
        lines.append("")

    # ---- aggregate table ------------------------------------------------
    lines.append("## Aggregate results\n")
    lines.append("| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | USD total (priced runs only) |")
    lines.append("|---|---|---|---|---|---|---|")
    agg = {}
    for v in variants:
        rs = [r for r in rows if r.get("variant") == v and "error" not in r]
        prs = priced(rs)
        agg[v] = {
            "ms_all": [_mean([r["ms_all"] for r in rs])],
            "ms_covered": _mean([r["ms_covered"] for r in rs]),
            "ms_all_median": _median([r["ms_all"] for r in rs]),
            "cov": _mean([r["coverage_pct"] for r in rs]),
            "acc": _mean([r["n_accepted"] for r in rs]),
            "cost": sum(r["cost"]["cost_usd"] for r in prs),
            "n_priced": len(prs),
        }
        cost_cell = f"{agg[v]['cost']:.4f}" if prs else "—"
        lines.append(
            f"| {v} | {fmt_pct(agg[v]['ms_all'][0])} | {fmt_pct(agg[v]['ms_all_median'])} "
            f"| {fmt_pct(agg[v]['ms_covered'])} | {agg[v]['cov']:.1f} | {agg[v]['acc']:.2f} "
            f"| {cost_cell} |"
        )
    lines.append("")
    lines.append(
        "The USD column only sums cells whose run carried an explicit price source "
        "(TESTFORGE_PRICE_* env or a pricing.json entry; see the price source in the "
        "per-cell ledger). Legacy archives priced with undocumented placeholder rates "
        "count as unpriced here — their exact token totals are in "
        "`LLM usage per variant` below.\n"
    )

    # ---- LLM usage per variant -------------------------------------------
    gen_variants = [v for v in variants if any(
        r.get("variant") == v and r.get("cost", {}).get("calls", 0) for r in rows
    )]
    if gen_variants:
        lines.append("## LLM usage per variant\n")
        lines.append("| Variant | LLM calls | tokens in | tokens out |")
        lines.append("|---|---|---|---|")
        for v in gen_variants:
            rs = [r for r in rows if r.get("variant") == v and "error" not in r]
            calls = sum(r.get("cost", {}).get("calls", 0) for r in rs)
            t_in = sum(r.get("cost", {}).get("tokens_in", 0) for r in rs)
            t_out = sum(r.get("cost", {}).get("tokens_out", 0) for r in rs)
            lines.append(f"| {v} | {calls} | {t_in:,} | {t_out:,} |")
        lines.append("")

    # ---- per-target table ----------------------------------------------
    lines.append("## Per-target mutation score (all mutants)\n")
    lines.append("| Target | " + " | ".join(variants) + " |")
    lines.append("|---|" + "---|" * len(variants))
    by = {(r["target_id"], r["variant"]): r for r in rows if "error" not in r}
    for t in sorted({r["target_id"] for r in rows if "error" not in r}):
        cells = []
        for v in variants:
            r = by.get((t, v))
            cells.append(fmt_pct(r["ms_all"]) if r else "-")
        lines.append(f"| {t} | " + " | ".join(cells) + " |")
    lines.append("")

    # ---- per-target uplift (generation vs baseline) -----------------------
    if "B0" in variants and "B1" in variants:
        pairs = paired(rows, "B1", "B0", "ms_all")
        pairs.sort(key=lambda p: -p["diff"])
        lines.append("## Per-target uplift (B1 minus B0), sorted\n")
        lines.append("| Target | B0 | B1 | uplift |")
        lines.append("|---|---|---|---|")
        for p in pairs:
            lines.append(f"| {p['target']} | {fmt_pct(p['b'])} | {fmt_pct(p['a'])} | {p['diff']:+.1%} |")
        lines.append("")

    # ---- research questions ----------------------------------------------
    lines.append("## Research questions\n")
    analysis = {"aggregate": {v: {k: (val[0] if isinstance(val, list) else val) for k, val in d.items()} for v, d in agg.items()}}
    for rq, (base, treat, question) in RQ_MAP.items():
        if base not in variants or treat not in variants:
            continue
        pairs = paired(rows, treat, base, "ms_all")
        diffs = [p["diff"] for p in pairs]
        stats = wilcoxon_signed_rank(diffs)
        ci = bootstrap_ci(diffs)
        lines.append(f"### {rq}: {question}\n")
        lines.append(f"Paired on {len(pairs)} targets, {treat} minus {base} on MS(all):")
        lines.append(f"- mean uplift: **{_mean(diffs):+.1%}** (median {_median(diffs):+.1%}, sd {_stdev(diffs):.1%})")
        lines.append(f"- wins/ties/losses: {sum(d > 1e-9 for d in diffs)}/{sum(abs(d) <= 1e-9 for d in diffs)}/{sum(d < -1e-9 for d in diffs)}")
        if stats["n"] == 0:
            lines.append("- no non-zero paired differences (treatment changed no target); significance test not applicable\n")
        else:
            lines.append(f"- Wilcoxon signed-rank (normal approx, n={stats['n']}): W+={stats['W_plus']:.1f}, z={stats['z']}, p={stats['p']}")
            lines.append(f"- bootstrap 95% CI of mean uplift: [{ci['lo']:+.1%}, {ci['hi']:+.1%}]\n")
        analysis[rq] = {
            "base": base,
            "treatment": treat,
            "pairs": pairs,
            "mean_uplift": _mean(diffs),
            "median_uplift": _median(diffs),
            "wilcoxon": stats,
            "bootstrap_ci": ci,
        }
        if rq == "RQ2":
            rs = [r for r in rows if r.get("variant") == treat and "error" not in r]
            prs = priced(rs)
            t_in = sum(r.get("cost", {}).get("tokens_in", 0) for r in rs)
            t_out = sum(r.get("cost", {}).get("tokens_out", 0) for r in rs)
            lines.append(
                f"LLM usage of {treat}: {sum(r.get('cost', {}).get('calls', 0) for r in rs)} calls, "
                f"{t_in:,} input / {t_out:,} output tokens over {n_targets} targets — token counts are exact."
            )
            if prs:
                src = prs[0].get("cost", {}).get("price_source", "unspecified source")
                lines.append(
                    f"Cost of {treat}: ${sum(r['cost']['cost_usd'] for r in prs):.4f} over "
                    f"{len(prs)} priced targets (price source: {src}).\n"
                )
            else:
                lines.append(
                    "No price was configured for this run, so no USD figure is derived; "
                    "the token counts above are the cost accounting.\n"
                )

    # ---- gate behaviour ----------------------------------------------------
    lines.append("## Gate behaviour (generation variants)\n")
    lines.append("| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |")
    lines.append("|---|---|---|---|---|---|---|")
    for v in variants:
        if v == "B0":
            continue
        rs = [r for r in rows if r.get("variant") == v and "error" not in r]
        gen = _mean([r["n_generated"] for r in rs]) if rs else 0
        acc = _mean([r["n_accepted"] for r in rs]) if rs else 0
        rr = [r.get("rejection_reasons", {}) for r in rs]

        def tot(key):
            return sum(d.get(key, 0) for d in rr)

        lines.append(
            f"| {v} | {gen:.2f} | {acc:.2f} | {tot('flaky')} | {tot('falsifiable')} "
            f"| {tot('failing_on_original')} | {tot('timeout')} |"
        )
    lines.append("")

    # ---- cross-model comparison (external validity) ------------------------
    if compare_rows is not None:
        section, cmp_json = cross_model_section(rows, compare_rows, compare_label)
        lines.extend(section)
        analysis["cross_model"] = cmp_json

    (out_dir / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(out_dir / "analysis.json", analysis)
    print(f"analysis -> {out_dir / 'analysis.md'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, help="experiment directory containing results.json")
    ap.add_argument("--compare-with", default=None,
                    help="second experiment directory; adds a cross-model comparison section")
    ap.add_argument("--compare-label", default=None,
                    help="label for the compared grid (default: its model id from the ledger)")
    args = ap.parse_args()
    exp_dir = Path(args.exp)
    rows = json.loads((exp_dir / "results.json").read_text(encoding="utf-8"))
    compare_rows = None
    if args.compare_with:
        cdir = Path(args.compare_with)
        compare_rows = json.loads((cdir / "results.json").read_text(encoding="utf-8"))
    analyze(rows, exp_dir, compare_rows=compare_rows, compare_label=args.compare_label)


if __name__ == "__main__":
    main()
