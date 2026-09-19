"""Generate the experiment figures (matplotlib, English labels).

    python experiments/plots.py --exp results/exp_mock_20260919_120000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

VARIANT_ORDER = ["B0", "B1", "B2", "B3", "B4"]
COLORS = {"B0": "#9aa0a6", "B1": "#d9776b", "B2": "#e2b93b", "B3": "#4c8f5c", "B4": "#5b8db8"}


def load(exp_dir: Path) -> list[dict]:
    return json.loads((exp_dir / "results.json").read_text(encoding="utf-8"))


def ms_by_variant(rows: list[dict], out: Path) -> None:
    variants = [v for v in VARIANT_ORDER if any(r.get("variant") == v for r in rows)]
    by = {(r["target_id"], r["variant"]): r for r in rows if "error" not in r}
    targets = sorted({r["target_id"] for r in rows if "error" not in r})

    means = []
    for v in variants:
        vals = [by[(t, v)]["ms_all"] for t in targets if (t, v) in by]
        means.append(sum(vals) / len(vals) if vals else 0.0)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bars = ax.bar(variants, means, color=[COLORS.get(v, "#888") for v in variants], alpha=0.85)
    # per-target dots
    rng_jitter = 0.12
    for i, v in enumerate(variants):
        for j, t in enumerate(targets):
            if (t, v) in by:
                x = i + ((j % 7) - 3) * rng_jitter / 3
                ax.plot(x, by[(t, v)]["ms_all"], "o", ms=3, color="#333", alpha=0.45, zorder=3)
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, m + 0.02, f"{m:.0%}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Mutation score (all mutants)")
    ax.set_title("Fault detection by variant (mean over targets; dots = per-target)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def uplift_vs_cost(rows: list[dict], out: Path) -> None:
    by = {(r["target_id"], r["variant"]): r for r in rows if "error" not in r}
    targets = sorted({r["target_id"] for r in rows if "error" not in r})
    xs, ys = [], []
    for t in targets:
        b0, b3 = by.get((t, "B0")), by.get((t, "B3"))
        if b0 and b3:
            ys.append(b3["ms_all"] - b0["ms_all"])
            xs.append(b3.get("cost", {}).get("cost_usd", 0.0) or 1e-6)
    if not xs:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.axhline(0, color="#999", lw=0.8)
    ax.plot(xs, ys, "o", color="#4c8f5c", alpha=0.85)
    ax.set_xscale("log")
    ax.set_xlabel("LLM cost per target (USD, log scale; 0 -> 1e-6)")
    ax.set_ylabel("MS uplift of B3 over B0")
    ax.set_title("Fault-detection uplift vs LLM cost (B3)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def gate_rejections(rows: list[dict], out: Path) -> None:
    reasons = ["flaky", "falsifiable", "failing_on_original", "timeout", "duplicate", "syntax_error"]
    variants = [v for v in VARIANT_ORDER if v not in ("B0",)]
    data = {v: [] for v in variants}
    for v in variants:
        rs = [r for r in rows if r.get("variant") == v and "error" not in r]
        for key in reasons:
            data[v].append(sum(r.get("rejection_reasons", {}).get(key, 0) for r in rs))
    if not any(sum(data[v]) for v in variants):
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bottom = [0] * len(variants)
    palette = ["#d9776b", "#e2b93b", "#5b8db8", "#8e6bb8", "#4c8f5c", "#9aa0a6"]
    for i, key in enumerate(reasons):
        vals = [data[v][i] for v in variants]
        if sum(vals) == 0:
            continue
        ax.bar(variants, vals, bottom=bottom, label=key, color=palette[i % len(palette)], alpha=0.9)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("rejected candidates (total)")
    ax.set_title("What the gate filters out, by variant")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def ms_heatmap(rows: list[dict], out: Path, label: str = "mock grid") -> None:
    """Per-target x variant mutation-score matrix: the whole grid at a glance."""
    by = {(r["target_id"], r["variant"]): r["ms_all"] for r in rows if "error" not in r}
    variants = [v for v in VARIANT_ORDER if any((t, v) in by for t in {k[0] for k in by})]
    targets = sorted({k[0] for k in by})
    data = [[by.get((t, v), float("nan")) for v in variants] for t in targets]

    fig, ax = plt.subplots(figsize=(7.0, 7.6))
    im = ax.imshow(data, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(variants)), variants)
    ax.set_yticks(range(len(targets)), targets)
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)
    for i in range(len(targets)):
        for j in range(len(variants)):
            v = data[i][j]
            if v == v:  # skip NaN
                ax.text(
                    j, i, f"{v:.0%}",
                    ha="center", va="center", fontsize=8,
                    color="black" if 0.25 < v < 0.85 else "white",
                )
    ax.set_title(f"Mutation score per target x variant ({label})")
    ax.set_xlabel("Variant")
    fig.colorbar(im, ax=ax, shrink=0.7, label="MS (all mutants)")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--label", default=None, help="grid label for plot titles (default: derived from dir name)")
    args = ap.parse_args()
    exp_dir = Path(args.exp)
    if args.label:
        label = args.label
    elif "api" in exp_dir.name:
        label = "real LLM: Qwen3-VL-8B"
    else:
        label = "mock backend"
    rows = load(exp_dir)
    plot_dir = exp_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    ms_by_variant(rows, plot_dir / "ms_by_variant.png")
    ms_heatmap(rows, plot_dir / "ms_heatmap.png", label=label)
    uplift_vs_cost(rows, plot_dir / "uplift_vs_cost.png")
    gate_rejections(rows, plot_dir / "gate_rejections.png")
    print(f"plots -> {plot_dir}")


if __name__ == "__main__":
    main()
