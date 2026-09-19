"""Command line interface.

    python -m testforge.cli targets
    python -m testforge.cli run --target string_utils.slugify --variant B3 --mode mock
    python -m testforge.cli run --all --variant B3 --mode api
    python -m testforge.cli report --results results/runs/xxx.json --out report.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent import ForgeAgent
from .benchmarks import PROJECT_ROOT, get_target, load_targets, result_to_dict
from .config import ForgeConfig
from .llm import make_client
from .report import render_summary, render_target_report
from .types import CostLedger
from .utils import write_json
from .variants import get_variant


def _cmd_targets(_args) -> None:
    for spec in load_targets():
        print(f"{spec.target_id:40s} module={spec.module_name}")


def _cmd_run(args) -> None:
    cfg = ForgeConfig.from_env(mode=args.mode)
    if args.rounds is not None:
        cfg.max_rounds = args.rounds
    if args.candidates is not None:
        cfg.candidates_per_round = args.candidates
    if args.mutants is not None:
        cfg.max_mutants = args.mutants
    cfg.validate()
    variant = get_variant(args.variant)

    specs = load_targets() if args.all else [get_target(args.target)]
    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for spec in specs:
        ledger = CostLedger(model=cfg.model)
        client = make_client(cfg, PROJECT_ROOT)
        agent = ForgeAgent(cfg, client, ledger)
        res = agent.run_target(spec, variant)
        payload = result_to_dict(res)
        payload["cost"] = ledger.summary()
        path = out_dir / f"{spec.target_id}__{variant.name}.json"
        write_json(path, payload)
        rows.append(res)
        print(
            f"{spec.target_id:40s} {variant.name}  "
            f"MS(all)={res.ms_all:6.1%}  MS(cov)={res.ms_covered:6.1%}  "
            f"gen={res.n_generated:<3d} acc={res.n_accepted:<3d}  {res.wall_sec:6.0f}s"
        )

    (out_dir / f"summary__{variant.name}.md").write_text(
        render_summary(rows), encoding="utf-8"
    )


def _cmd_report(args) -> None:
    import json

    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    from .types import VariantResult

    res = VariantResult(**{k: v for k, v in data.items() if k in VariantResult.__dataclass_fields__})
    report = render_target_report(res, data.get("cost"))
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"report written to {args.out}")


def main(argv=None) -> None:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="testforge",
        description="Mutation-guided test quality agent: LLM generates tests, mutation testing proves they catch bugs",
    )
    parser.add_argument("--version", action="version", version=f"testforge {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("targets").set_defaults(func=_cmd_targets)

    p_run = sub.add_parser("run")
    p_run.add_argument("--target", help="benchmark target id, e.g. string_utils.slugify")
    p_run.add_argument("--all", action="store_true", help="run every benchmark target")
    p_run.add_argument("--variant", default="B3", help="B0 | B1 | B2 | B3 | B4")
    p_run.add_argument("--mode", default="mock", choices=["mock", "api"])
    p_run.add_argument("--rounds", type=int, default=None, help="override max feedback rounds")
    p_run.add_argument("--candidates", type=int, default=None, help="override candidates per round")
    p_run.add_argument("--mutants", type=int, default=None, help="override max mutants per target")
    p_run.add_argument("--out", default="results/runs")
    p_run.set_defaults(func=_cmd_run)

    p_rep = sub.add_parser("report")
    p_rep.add_argument("--results", required=True, help="path to a run JSON")
    p_rep.add_argument("--out", default="report.md")
    p_rep.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
