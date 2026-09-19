"""Run the full experiment grid: (targets x variants), crash-safe.

Every (target, variant) cell is one ForgeAgent run; results are appended to
the output JSON after each cell so an interrupted run can be inspected.

    python experiments/run_experiment.py --mode mock
    python experiments/run_experiment.py --mode api --targets string_utils.slugify
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testforge.agent import ForgeAgent
from testforge.benchmarks import PROJECT_ROOT, load_targets, result_to_dict
from testforge.config import ForgeConfig
from testforge.llm import make_client
from testforge.report import render_summary
from testforge.types import CostLedger, VariantSpec
from testforge.utils import write_json
from testforge.variants import VARIANTS


def main() -> None:
    ap = argparse.ArgumentParser(description="TestForge experiment grid")
    ap.add_argument("--mode", default="mock", choices=["mock", "api"])
    ap.add_argument("--targets", default="all", help="'all' or comma-separated target ids")
    ap.add_argument("--variants", default="B0,B1,B2,B3,B4")
    ap.add_argument("--flaky-runs", type=int, default=5)
    ap.add_argument("--candidates", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=3, help="max feedback rounds for B3/B4")
    ap.add_argument("--max-mutants", type=int, default=24)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    specs = load_targets()
    if args.targets != "all":
        wanted = {t.strip() for t in args.targets.split(",")}
        specs = [s for s in specs if s.target_id in wanted]
        missing = wanted - {s.target_id for s in specs}
        if missing:
            raise SystemExit(f"unknown targets: {sorted(missing)}")

    vnames = [v.strip() for v in args.variants.split(",")]
    for v in vnames:
        if v not in VARIANTS:
            raise SystemExit(f"unknown variant {v!r}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / (args.out or f"results/exp_{args.mode}_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"

    rows: list[dict] = []
    if results_path.exists():
        import json

        rows = json.loads(results_path.read_text(encoding="utf-8"))
    done = {(r["target_id"], r["variant"]) for r in rows}

    total_cells = len(specs) * len(vnames)
    cell = 0
    for spec in specs:
        for vname in vnames:
            cell += 1
            if (spec.target_id, vname) in done:
                print(f"[{cell}/{total_cells}] skip {spec.target_id} {vname} (cached)")
                continue
            cfg = ForgeConfig.from_env(mode=args.mode)
            cfg.flaky_runs = args.flaky_runs
            cfg.candidates_per_round = args.candidates
            cfg.max_mutants = args.max_mutants
            cfg.validate()

            base = VARIANTS[vname]
            variant = VariantSpec(
                name=base.name,
                rounds=args.rounds if vname in ("B3", "B4") else base.rounds,
                gate_enabled=base.gate_enabled,
                feedback_mode=base.feedback_mode,
            )

            t0 = time.perf_counter()
            ledger = CostLedger(model=cfg.model)
            client = make_client(cfg, PROJECT_ROOT)
            try:
                res = ForgeAgent(cfg, client, ledger).run_target(spec, variant)
                row = result_to_dict(res)
                row["cost"] = ledger.summary()
                status = "ok"
                err = ""
            except Exception as exc:  # noqa: BLE001 - record and continue
                row = {"target_id": spec.target_id, "variant": vname, "error": str(exc)}
                status = "ERROR"
                err = str(exc)
            row["wall_sec"] = round(time.perf_counter() - t0, 1)
            rows.append(row)
            write_json(results_path, rows)
            print(
                f"[{cell}/{total_cells}] {spec.target_id:40s} {vname}  {status}  "
                f"{row.get('wall_sec', 0):6.0f}s  {err[:80]}"
            )

    # human-readable summary for the completed grid
    from testforge.types import VariantResult

    ok_rows = [
        VariantResult(**{k: v for k, v in r.items() if k in VariantResult.__dataclass_fields__})
        for r in rows
        if "error" not in r
    ]
    (out_dir / "summary.md").write_text(render_summary(ok_rows), encoding="utf-8")
    print(f"done -> {out_dir}")


if __name__ == "__main__":
    main()
