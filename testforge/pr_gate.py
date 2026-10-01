"""PR quality gate: diff -> targets -> budgeted runs -> summary.

This is the engine behind the repo's GitHub Action (action.yml at the repo
root) and the ``testforge ci`` subcommand. Design decisions, deliberately:

- **Advisory by default.** The gate's output is a mutation-score annotation
  plus *suggested* tests; a human merges. The command exits non-zero only for
  infrastructure errors (a target could not be run at all) — a low mutation
  score is information, not a failure.
- **Budget is first-class.** One Budget (wall clock + tokens) spans the whole
  PR run and is passed to every ForgeAgent; exhausted targets keep their
  mutation score for what was accepted before the cap hit.
- **No endpoint, no problem.** mode=mock runs the whole flow offline; the
  action defaults to it and treats api mode as explicit opt-in.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from .agent import ForgeAgent
from .budget import Budget
from .config import ForgeConfig
from .diff_targets import ChangedFunction, changed_functions
from .llm import make_client
from .types import CostLedger, TargetSpec, VariantResult
from .utils import write_json
from .variants import get_variant


def auto_diff(root: Path, base_ref: str) -> str:
    """Diff of the working tree against ``base_ref`` (used inside CI where
    the checkout action already fetched the base branch)."""
    subprocess.run(
        ["git", "fetch", "--depth=1", "origin", base_ref],
        cwd=root, capture_output=True, check=False,
    )
    proc = subprocess.run(
        ["git", "diff", f"origin/{base_ref}...HEAD"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    return proc.stdout


def _find_existing_tests(module_path: Path, module_stem: str, root: Path) -> str | None:
    """Locate an existing pytest file for a module: next to it, in a sibling
    ``existing_tests``-style dir, or under <root>/tests. First hit wins."""
    candidates = [module_path.parent / f"test_{module_stem}.py"]
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        candidates += sorted(tests_dir.rglob(f"test_{module_stem}.py"))
    parent = module_path.parent.parent
    if parent.is_dir():
        candidates += sorted(parent.rglob(f"test_{module_stem}.py"))
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def changed_to_targets(changed: list[ChangedFunction], root: Path) -> list[TargetSpec]:
    specs: list[TargetSpec] = []
    seen: set[str] = set()
    for c in changed:
        module_path = root / c.file
        stem = module_path.stem
        if not stem.isidentifier():
            continue
        target_id = c.qualified
        if target_id in seen:
            continue
        seen.add(target_id)
        specs.append(
            TargetSpec(
                target_id=f"{c.file}::{c.function.name}",
                module_path=str(module_path),
                module_name=stem,
                function_name=c.function.name,
                existing_test_path=_find_existing_tests(module_path, stem, root),
            )
        )
    return specs


def render_ci_summary(rows: list[dict], budget: Budget) -> str:
    lines = ["# TestForge PR quality gate\n"]
    if budget.sec or budget.tokens:
        lines.append(
            f"Budget: {budget.sec or '∞'}s / {budget.tokens or '∞'} tokens — "
            f"elapsed {budget.elapsed():.0f}s.\n"
        )
    lines.append("| Target | Variant | MS (all) | Gen | Accepted | Budget stop |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        if "error" in r:
            lines.append(f"| `{r['target_id']}` | {r.get('variant', '-')} | run error | — | — | — |")
            continue
        lines.append(
            f"| `{r['target_id']}` | {r['variant']} | {r['ms_all']:.1%} "
            f"| {r['n_generated']} | {r['n_accepted']} | {'yes' if r.get('budget_exceeded') else 'no'} |"
        )
    lines.append("")
    suggested = [r for r in rows if "error" not in r and r.get("accepted_codes")]
    if suggested:
        lines.append("## Suggested tests (human review required — nothing is auto-merged)\n")
        for r in suggested:
            lines.append(f"### `{r['target_id']}` — kills evidence in the per-target JSON\n")
            for i, code in enumerate(r["accepted_codes"], 1):
                lines.append("```python")
                lines.append(code)
                lines.append("```\n")
    return "\n".join(lines)


def run_ci(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    diff_text = (
        Path(args.diff).read_text(encoding="utf-8")
        if args.diff
        else auto_diff(root, args.base_ref)
    )
    changed = changed_functions(diff_text, root, skip_tests=True)
    specs = changed_to_targets(changed, root)
    if args.max_functions and len(specs) > args.max_functions:
        specs = specs[: args.max_functions]

    print(f"changed functions matched: {len(specs)}")
    for s in specs:
        print(f"  - {s.target_id} (tests: {'yes' if s.existing_test_path else 'none'})")
    if not specs:
        (Path(args.out) if args.out else Path("results/ci_gate")).mkdir(parents=True, exist_ok=True)
        return 0

    cfg = ForgeConfig.from_env(mode=args.mode)
    if args.budget_sec:
        cfg.validate()
    variant = get_variant(args.variant)
    out_dir = Path(args.out or "results/ci_gate")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    budget = Budget(sec=args.budget_sec or 0.0, tokens=args.budget_tokens or 0)
    client = make_client(cfg, root)
    import json as _json

    rows: list[dict] = _json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else []
    done = {(r.get("target_id"), r.get("variant")) for r in rows if "error" not in r}

    errors = 0
    for spec in specs:
        if (spec.target_id, variant.name) in done:
            print(f"skip {spec.target_id} (cached)")
            continue
        ledger = CostLedger(model=cfg.model)
        t0 = time.perf_counter()
        try:
            agent = ForgeAgent(cfg, client, ledger, budget=budget)
            res: VariantResult = agent.run_target(spec, variant)
            payload = _payload_from(res, ledger)
            status = "ok"
        except Exception as exc:  # noqa: BLE001 - record, continue, exit non-zero at the end
            payload = {"target_id": spec.target_id, "variant": variant.name, "error": str(exc)[:400]}
            status = "ERROR"
            errors += 1
        payload["wall_sec"] = round(time.perf_counter() - t0, 1)
        rows.append(payload)
        write_json(results_path, rows)
        ms = payload.get("ms_all")
        print(f"{spec.target_id:44s} {status} MS={ms:.1%}" if ms is not None else f"{spec.target_id:44s} {status} {payload.get('error', '')[:60]}")

    (out_dir / "summary.md").write_text(render_ci_summary(rows, budget), encoding="utf-8")
    print(f"summary -> {out_dir / 'summary.md'}")
    return 1 if errors else 0


def _payload_from(res: VariantResult, ledger: CostLedger) -> dict:
    from .benchmarks import result_to_dict

    payload = result_to_dict(res)
    payload["cost"] = ledger.summary()
    return payload


def main(argv=None) -> int:  # pragma: no cover - thin wrapper
    ap = argparse.ArgumentParser(prog="testforge-ci")
    ap.add_argument("--diff", default=None, help="path to a unified diff; default: git diff vs --base-ref")
    ap.add_argument("--base-ref", default="main", help="base branch for auto diff")
    ap.add_argument("--root", default=".", help="repository root the diff applies to")
    ap.add_argument("--mode", default=None, choices=["mock", "api"])
    ap.add_argument("--variant", default="B3")
    ap.add_argument("--max-functions", type=int, default=5, help="cap on targets per run")
    ap.add_argument("--budget-sec", type=float, default=0.0)
    ap.add_argument("--budget-tokens", type=int, default=0)
    ap.add_argument("--out", default="results/ci_gate")
    args = ap.parse_args(argv)
    return run_ci(args)


if __name__ == "__main__":
    sys.exit(main())
