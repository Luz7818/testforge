"""Whole-package offline batch enhancement (B5-shaped, engineering shell).

``testforge batch`` scans a package for public functions, orders them into a
priority queue, and runs the existing agent per target under one shared
Budget, writing crash-safe per-target results and a markdown summary.

Discovery rules (deliberately small):
- top-level public functions only (no leading underscore, no nested/classes);
- ``__init__.py``, ``test_*.py``, and files that fail to parse are skipped;
- existing tests are located next to the module, under ``<root>/tests``, or
  in a sibling ``existing_tests``-style directory (the benchmark layout);
- the module must be importable standalone — a package that relies on
  relative imports will record per-target errors instead of failing the run.

Priority queue: targets without any existing tests first, then targets with
fewer existing test functions, then name order — the least-covered surface
gets the budget first. No new science here, just plumbing.
"""

from __future__ import annotations

import argparse
import ast
import time
from pathlib import Path

from .agent import ForgeAgent
from .budget import Budget
from .config import ForgeConfig
from .llm import make_client
from .types import CostLedger, TargetSpec, VariantResult
from .utils import write_json
from .variants import get_variant


def _existing_test_functions(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return 0
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _find_existing_tests(module_path: Path, stem: str, root: Path) -> str | None:
    candidates = [module_path.parent / f"test_{stem}.py"]
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        candidates += sorted(tests_dir.rglob(f"test_{stem}.py"))
    parent = module_path.parent
    if parent.is_dir():
        candidates += sorted(p for p in parent.rglob(f"test_{stem}.py") if p != candidates[0])
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def discover_targets(package_dir: Path) -> list[TargetSpec]:
    """Public top-level functions of a package, priority-ordered."""
    specs: list[tuple[tuple, TargetSpec]] = []
    seen: set[str] = set()
    for py in sorted(package_dir.rglob("*.py")):
        if py.name == "__init__.py" or py.name.startswith("test_"):
            continue
        stem = py.stem
        if not stem.isidentifier():
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_"):
                continue
            target_id = f"{stem}.{node.name}"
            if target_id in seen:
                continue
            seen.add(target_id)
            tests_path = _find_existing_tests(py, stem, package_dir)
            n_tests = _existing_test_functions(Path(tests_path)) if tests_path else 0
            specs.append(
                (
                    (0 if not tests_path else 1, n_tests, target_id),
                    TargetSpec(
                        target_id=target_id,
                        module_path=str(py),
                        module_name=stem,
                        function_name=node.name,
                        existing_test_path=tests_path,
                    ),
                )
            )
    specs.sort(key=lambda pair: pair[0])
    return [spec for _, spec in specs]


def render_batch_summary(rows: list[dict], budget: Budget) -> str:
    lines = ["# TestForge batch report\n"]
    done = [r for r in rows if "error" not in r]
    skipped = [r for r in rows if "error" in r]
    if budget.sec or budget.tokens:
        lines.append(
            f"Budget: {budget.sec or '∞'}s / {budget.tokens or '∞'} tokens — elapsed {budget.elapsed():.0f}s\n"
        )
    lines.append("| Target | Variant | MS (all) | MS (covered) | Gen | Accepted | Final suite passes |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in done:
        lines.append(
            f"| `{r['target_id']}` | {r['variant']} | {r['ms_all']:.1%} | {r['ms_covered']:.1%} "
            f"| {r['n_generated']} | {r['n_accepted']} | {r['final_suite_passes']} |"
        )
    for r in skipped:
        lines.append(f"| `{r['target_id']}` | {r.get('variant', '-')} | skipped: {r['error'][:60]} | | | | |")
    if done:
        mean_ms = sum(r["ms_all"] for r in done) / len(done)
        lines.append("")
        lines.append(f"Mean MS(all) over completed targets: **{mean_ms:.1%}** ({len(done)} done, {len(skipped)} skipped)\n")
    suggested = [r for r in done if r.get("accepted_codes")]
    if suggested:
        lines.append("## Suggested tests (human review required)\n")
        for r in suggested:
            lines.append(f"### `{r['target_id']}`\n")
            for code in r["accepted_codes"]:
                lines.append("```python")
                lines.append(code)
                lines.append("```\n")
    return "\n".join(lines)


def run_batch(args: argparse.Namespace) -> int:
    package_dir = Path(args.package).resolve()
    if not package_dir.is_dir():
        raise SystemExit(f"package dir not found: {package_dir}")
    specs = discover_targets(package_dir)
    if args.max_functions and len(specs) > args.max_functions:
        specs = specs[: args.max_functions]
    if not specs:
        raise SystemExit(f"no public functions discovered under {package_dir}")
    print(f"discovered {len(specs)} target(s):")
    for s in specs:
        print(f"  - {s.target_id} (tests: {'yes' if s.existing_test_path else 'none'})")

    cfg = ForgeConfig.from_env(mode=args.mode)
    cfg.validate()
    variant = get_variant(args.variant)
    out_dir = Path(args.out or "results/batch")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    budget = Budget(sec=args.budget_sec or 0.0, tokens=args.budget_tokens or 0)
    client = make_client(cfg, package_dir)

    import json as _json

    rows: list[dict] = _json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else []
    done = {(r.get("target_id"), r.get("variant")) for r in rows if "error" not in r}

    for spec in specs:
        if (spec.target_id, variant.name) in done:
            print(f"skip {spec.target_id} (cached)")
            continue
        if budget.exhausted(
            sum(r.get("cost", {}).get("tokens_in", 0) + r.get("cost", {}).get("tokens_out", 0) for r in rows)
        ):
            rows.append({"target_id": spec.target_id, "variant": variant.name,
                         "error": "budget exhausted (target not started)"})
            write_json(results_path, rows)
            continue
        ledger = CostLedger(model=cfg.model, price_source=cfg.price_source)
        t0 = time.perf_counter()
        try:
            agent = ForgeAgent(cfg, client, ledger, budget=budget)
            res: VariantResult = agent.run_target(spec, variant)
            payload = _payload_from(res, ledger)
            status = "ok"
        except Exception as exc:  # noqa: BLE001 - per-target isolation
            payload = {"target_id": spec.target_id, "variant": variant.name, "error": str(exc)[:400]}
            status = "ERROR"
        payload["wall_sec"] = round(time.perf_counter() - t0, 1)
        rows.append(payload)
        write_json(results_path, rows)
        ms = payload.get("ms_all")
        print(
            f"{spec.target_id:44s} {status} MS={ms:.1%} {payload['wall_sec']:.0f}s"
            if ms is not None
            else f"{spec.target_id:44s} {status} {payload.get('error', '')[:70]}"
        )

    (out_dir / "batch-summary.md").write_text(render_batch_summary(rows, budget), encoding="utf-8")
    print(f"summary -> {out_dir / 'batch-summary.md'}")
    return 0


def _payload_from(res: VariantResult, ledger: CostLedger) -> dict:
    from .benchmarks import result_to_dict

    payload = result_to_dict(res)
    payload["cost"] = ledger.summary()
    return payload


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(prog="testforge-batch")
    ap.add_argument("--package", required=True, help="package dir to scan (recursive)")
    ap.add_argument("--mode", default=None, choices=["mock", "api"])
    ap.add_argument("--variant", default="B3")
    ap.add_argument("--max-functions", type=int, default=0, help="cap on targets (0 = all)")
    ap.add_argument("--budget-sec", type=float, default=0.0)
    ap.add_argument("--budget-tokens", type=int, default=0)
    ap.add_argument("--out", default="results/batch")
    args = ap.parse_args(argv)
    return run_batch(args)


if __name__ == "__main__":
    main()
