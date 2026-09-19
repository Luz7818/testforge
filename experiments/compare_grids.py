"""Cross-grid comparison: pool two independently sampled grids of the same
design (e.g. results/exp_api_full and results/exp_api_replicate) to report
replicate consistency and doubled-sample paired statistics.

    python experiments/compare_grids.py --a results/exp_api_full --b results/exp_api_replicate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyze import bootstrap_ci, wilcoxon_signed_rank, _mean, _median, _stdev  # noqa: E402


def load(exp_dir: Path) -> list[dict]:
    return json.loads((exp_dir / "results.json").read_text(encoding="utf-8"))


def paired(rows: list[dict], va: str, vb: str, metric: str = "ms_all") -> list[float]:
    by = {(r["target_id"], r["variant"]): r for r in rows if "error" not in r}
    targets = sorted({r["target_id"] for r in rows if "error" not in r})
    out = []
    for t in targets:
        a, b = by.get((t, va)), by.get((t, vb))
        if a and b and a.get(metric) is not None and b.get(metric) is not None:
            out.append(a[metric] - b[metric])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--treat", default="B1")
    ap.add_argument("--base", default="B0")
    args = ap.parse_args()

    ga, gb = Path(args.a), Path(args.b)
    ra, rb = load(ga), load(gb)
    da = paired(ra, args.treat, args.base)
    db = paired(rb, args.treat, args.base)
    pooled = da + db

    lines: list[str] = []
    lines.append(f"# Grid comparison: {args.treat} vs {args.base}\n")
    lines.append(f"- grid A `{ga.name}`: n={len(da)} pairs, mean uplift {_mean(da):+.1%} "
                 f"(median {_median(da):+.1%}, sd {_stdev(da):.1%})")
    lines.append(f"- grid B `{gb.name}`: n={len(db)} pairs, mean uplift {_mean(db):+.1%} "
                 f"(median {_median(db):+.1%}, sd {_stdev(db):.1%})")
    stats = wilcoxon_signed_rank(pooled)
    ci = bootstrap_ci(pooled)
    lines.append(f"- pooled: n={len(pooled)} pairs, mean uplift **{_mean(pooled):+.1%}** "
                 f"(median {_median(pooled):+.1%}, sd {_stdev(pooled):.1%})")
    lines.append(f"- pooled wins/ties/losses: {sum(d > 1e-9 for d in pooled)}/"
                 f"{sum(abs(d) <= 1e-9 for d in pooled)}/{sum(d < -1e-9 for d in pooled)}")
    if stats["n"]:
        lines.append(f"- pooled Wilcoxon signed-rank (normal approx): W+={stats['W_plus']:.1f}, "
                     f"z={stats['z']}, p={stats['p']}")
        lines.append(f"- pooled bootstrap 95% CI: [{ci['lo']:+.1%}, {ci['hi']:+.1%}]")
    else:
        lines.append("- no non-zero paired differences; significance test not applicable")
    lines.append("")

    # RQ2-style consistency check for a second pair (B3 vs B1) if present
    for treat, base in [("B3", "B1"), ("B2", "B1")]:
        pa, pb = paired(ra, treat, base), paired(rb, treat, base)
        if pa and pb:
            pp = pa + pb
            lines.append(f"- consistency check {treat} vs {base}: grid A mean {_mean(pa):+.1%}, "
                         f"grid B mean {_mean(pb):+.1%}, pooled n={len(pp)} "
                         f"({sum(abs(d) <= 1e-9 for d in pp)} ties / {len(pp)})")

    # compare.md lives next to grid A's results so git tracks it (results/
    # ignores everything outside experiment directories)
    (ga / "compare.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten -> {ga / 'compare.md'}")


if __name__ == "__main__":
    main()
