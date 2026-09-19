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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testforge.utils import write_json

RQ_MAP = {
    "RQ1": ("B0", "B1", "Can single-shot LLM tests improve fault detection beyond the existing suite?"),
    "RQ2": ("B1", "B3", "Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?"),
    "RQ3": ("B1", "B2", "What does the quality gate contribute on its own (reliability vs raw generation)?"),
    "RQ4": ("B3", "B4", "Ablation: mutant-survivor feedback vs coverage-gap feedback."),
}


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def _median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


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


def analyze(rows: list[dict], out_dir: Path) -> None:
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
    lines.append("| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |")
    lines.append("|---|---|---|---|---|---|---|")
    agg = {}
    for v in variants:
        rs = [r for r in rows if r.get("variant") == v and "error" not in r]
        agg[v] = {
            "ms_all": [_mean([r["ms_all"] for r in rs])],
            "ms_covered": _mean([r["ms_covered"] for r in rs]),
            "ms_all_median": _median([r["ms_all"] for r in rs]),
            "cov": _mean([r["coverage_pct"] for r in rs]),
            "acc": _mean([r["n_accepted"] for r in rs]),
            "cost": sum(r.get("cost", {}).get("cost_usd", 0.0) for r in rs),
        }
        lines.append(
            f"| {v} | {fmt_pct(agg[v]['ms_all'][0])} | {fmt_pct(agg[v]['ms_all_median'])} "
            f"| {fmt_pct(agg[v]['ms_covered'])} | {agg[v]['cov']:.1f} | {agg[v]['acc']:.2f} "
            f"| {agg[v]['cost']:.4f} |"
        )
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
            costs = [r.get("cost", {}).get("cost_usd", 0.0) for r in rows if r.get("variant") == treat and "error" not in r]
            lines.append(f"Cost of {treat}: total ${sum(costs):.4f} over {n_targets} targets "
                         f"(mean ${_mean(costs) if costs else 0:.4f}/target; token counts are exact in the ledger, price is configurable).\n")

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

    (out_dir / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(out_dir / "analysis.json", analysis)
    print(f"analysis -> {out_dir / 'analysis.md'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, help="experiment directory containing results.json")
    args = ap.parse_args()
    exp_dir = Path(args.exp)
    rows = json.loads((exp_dir / "results.json").read_text(encoding="utf-8"))
    analyze(rows, exp_dir)


if __name__ == "__main__":
    main()
