"""Run the full experiment grid: (targets x variants), crash-safe.

Every (target, variant) cell is one ForgeAgent run; results are appended to
the output JSON after each cell so an interrupted run can be inspected.

    python experiments/run_experiment.py --mode mock
    python experiments/run_experiment.py --mode api --targets string_utils.slugify
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testforge.agent import ForgeAgent
from testforge.benchmarks import PROJECT_ROOT, load_targets, result_to_dict
from testforge.config import ForgeConfig
from testforge.llm import make_client
from testforge.presets import PRESETS
from testforge.report import render_summary
from testforge.types import CostLedger, VariantSpec
from testforge.utils import write_json
from testforge.variants import VARIANTS

# Code defaults, expressed with the same keys as PRESETS entries.
GRID_DEFAULTS = {"max_mutants": 24, "candidates_per_round": 4, "max_rounds": 3, "flaky_runs": 5}


def resolve_params(args) -> dict:
    """Effective grid parameters: explicit flag > preset value > code default."""
    preset_vals = PRESETS.get(args.preset, {}) if args.preset else {}

    def eff(flag, key):
        return flag if flag is not None else preset_vals.get(key, GRID_DEFAULTS[key])

    return {
        "max_mutants": eff(args.max_mutants, "max_mutants"),
        "candidates": eff(args.candidates, "candidates_per_round"),
        "rounds": eff(args.rounds, "max_rounds"),
        "flaky_runs": eff(args.flaky_runs, "flaky_runs"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="TestForge experiment grid")
    ap.add_argument("--mode", default=None, choices=["mock", "api"],
                    help="backend; default: TESTFORGE_MODE env, else mock")
    ap.add_argument("--preset", default=None, choices=sorted(PRESETS),
                    help="named parameter set; flags below override preset values. "
                         "'published' = the 90-cell grids (16 mutants / 3 candidates / "
                         "2 rounds / gate reruns x3)")
    ap.add_argument("--targets", default="all", help="'all' or comma-separated target ids")
    ap.add_argument("--variants", default="B0,B1,B2,B3,B4")
    ap.add_argument("--flaky-runs", type=int, default=None)
    ap.add_argument("--candidates", type=int, default=None)
    ap.add_argument("--rounds", type=int, default=None,
                    help="max feedback rounds for B3/B4/B5 (B0-B2 use their own definition)")
    ap.add_argument("--max-mutants", type=int, default=None)
    ap.add_argument("--mutant-priority", action="store_true",
                    help="sample baseline-covered-line mutants first (changes the mutant set)")
    ap.add_argument("--incremental", action="store_true",
                    help="skip executing uncovered mutants (same outcomes, cheaper matrix)")
    ap.add_argument("--property", action="store_true",
                    help="mock backend: deterministic @given property tests (needs hypothesis)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    mode = args.mode or os.environ.get("TESTFORGE_MODE", "mock")
    params = resolve_params(args)

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
    out_dir = PROJECT_ROOT / (args.out or f"results/exp_{mode}_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"

    probe = ForgeConfig.from_env(mode=mode)
    probe.mutant_priority = probe.mutant_priority or args.mutant_priority
    probe.incremental_execution = probe.incremental_execution or args.incremental
    probe.property_based = probe.property_based or args.property
    print(
        f"grid: mode={mode} preset={args.preset or 'none'} "
        f"mutants={params['max_mutants']} candidates={params['candidates']} "
        f"rounds={params['rounds']} flaky_runs={params['flaky_runs']} "
        f"priority={probe.mutant_priority} incremental={probe.incremental_execution} "
        f"property={probe.property_based} "
        f"targets={len(specs)} variants={','.join(vnames)} model={probe.model}"
    )
    print(f"out -> {out_dir}")

    rows: list[dict] = []
    if results_path.exists():
        import json

        rows = json.loads(results_path.read_text(encoding="utf-8"))
        failed = [r for r in rows if "error" in r]
        if failed:
            # An errored cell is not done. Archive its record outside
            # results.json, then let it be regenerated on this pass.
            err_path = out_dir / "errors.json"
            archived = json.loads(err_path.read_text(encoding="utf-8")) if err_path.exists() else []
            write_json(err_path, archived + failed)
            rows = [r for r in rows if "error" not in r]
            write_json(results_path, rows)
            print(f"retrying {len(failed)} errored cell(s); error rows archived in {err_path}")
    done = {(r["target_id"], r["variant"]) for r in rows}

    total_cells = len(specs) * len(vnames)
    cell = 0
    for spec in specs:
        for vname in vnames:
            cell += 1
            if (spec.target_id, vname) in done:
                print(f"[{cell}/{total_cells}] skip {spec.target_id} {vname} (cached)")
                continue
            cfg = ForgeConfig.from_env(mode=mode)
            cfg.flaky_runs = params["flaky_runs"]
            cfg.candidates_per_round = params["candidates"]
            cfg.max_mutants = params["max_mutants"]
            cfg.mutant_priority = cfg.mutant_priority or args.mutant_priority
            cfg.incremental_execution = cfg.incremental_execution or args.incremental
            cfg.property_based = cfg.property_based or args.property
            cfg.validate()

            base = VARIANTS[vname]
            variant = VariantSpec(
                name=base.name,
                rounds=params["rounds"] if vname in ("B3", "B4", "B5") else base.rounds,
                gate_enabled=base.gate_enabled,
                feedback_mode=base.feedback_mode,
                continue_on_zero_accept=base.continue_on_zero_accept,
            )

            t0 = time.perf_counter()
            ledger = CostLedger(model=cfg.model, price_source=cfg.price_source)
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
