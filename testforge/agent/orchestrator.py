"""The TestForge agent loop.

Per (target, variant):

1. Sanity-run the existing suite (B0) against the original code.
2. Generate mutants of the target function and find which ones B0 already
   kills -> the *surviving* set (the bugs nobody detects yet).
3. Loop up to ``variant.rounds`` rounds:
     - prompt the LLM (round 0: initial; later: feedback about surviving
       mutants, or coverage gaps in the coverage-feedback ablation);
     - gate each candidate: repeated passing runs on the original (flaky
       detection), falsifiability (kills >= 1 surviving mutant), optional
       coverage-delta;
     - accept greedily and update the killed set;
     - stop when a round produces no accepted test or all mutants die.
4. Final joint evaluation, shared by every variant for fairness: all tests
   together must pass on the original; every mutant is re-run against the
   full suite to compute the definitive mutation score.

Cost and wall time are accounted per run; an LLM ledger records exact tokens.
"""

from __future__ import annotations

import ast
import time
import zlib
from collections import Counter
from pathlib import Path

from ..analysis import inspect_target
from ..config import ForgeConfig
from ..gate import GatePolicy, coverage_pct, evaluate_candidate, measure_coverage, run_tests_once
from ..mutation import evaluate_mutants, generate_mutants
from ..types import Candidate, CostLedger, Outcome, TargetSpec, VariantResult, VariantSpec
from . import prompts


def _stable_hash(text: str) -> int:
    return zlib.crc32(text.encode("utf-8"))


def _norm_hash(code: str) -> int:
    collapsed = "\n".join(
        line.rstrip() for line in code.splitlines() if line.strip() and not line.strip().startswith("#")
    )
    return _stable_hash(collapsed)


def _read_or_placeholder(path: str | None) -> str:
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return "# no existing tests\n"


class ForgeAgent:
    def __init__(self, config: ForgeConfig, client, ledger: CostLedger | None = None):
        self.cfg = config
        self.client = client
        self.ledger = ledger or CostLedger(model=config.model)

    # ------------------------------------------------------------------ run
    def run_target(self, spec: TargetSpec, variant: VariantSpec) -> VariantResult:
        t0 = time.perf_counter()
        cfg = self.cfg
        info = inspect_target(spec)
        module_name = spec.module_name
        res = VariantResult(target_id=spec.target_id, variant=variant.name)

        # -- 1. baseline suite sanity -------------------------------------
        b0_code = _read_or_placeholder(spec.existing_test_path)
        outcome = run_tests_once(
            info.module_source, module_name, {"test_b0.py": b0_code}, cfg.test_timeout_sec
        )
        if outcome is not Outcome.PASS:
            raise RuntimeError(
                f"[{spec.target_id}] existing tests fail on the original code ({outcome})"
            )

        # -- 2. mutants and what B0 already kills -------------------------
        mutants = generate_mutants(
            info.module_source,
            spec.function_name,
            max_mutants=cfg.max_mutants,
            seed=cfg.mutation_seed + _stable_hash(spec.target_id) % 10000,
        )
        if not mutants:
            raise RuntimeError(f"[{spec.target_id}] no mutants could be generated")
        res.mutants_total = len(mutants)

        b0_kills = evaluate_mutants(
            mutants, module_name, {"test_b0.py": b0_code}, cfg.test_timeout_sec, cfg.workers
        )
        killed_by_b0: set[str] = {mid for mid, o in b0_kills.items() if o.killed_mutant}
        res.b0_killed_final = len(killed_by_b0)

        _, b0_cov, b0_exec = measure_coverage(
            info.module_source, module_name, {"test_b0.py": b0_code}, cfg.test_timeout_sec
        )
        target_exec = {l for l in b0_exec if info.start_line <= l <= info.end_line}
        res.b0_coverage_pct = round(coverage_pct(b0_cov, b0_exec, range(info.start_line, info.end_line + 1)), 1)
        baseline_covered = b0_cov

        # -- 3. generation / gate / feedback loop --------------------------
        killed: set[str] = set(killed_by_b0)
        accepted: list[Candidate] = []
        seen_hashes: set[int] = {_norm_hash(b0_code)}
        reasons: Counter[str] = Counter()
        flaky_rejects = 0
        generated = 0
        repaired = 0
        rounds_used = 0
        policy = GatePolicy(
            gate_enabled=variant.gate_enabled,
            flaky_runs=cfg.flaky_runs,
            require_coverage_delta=cfg.require_coverage_delta,
        )

        for rnd in range(variant.rounds):
            survivors = [m for m in mutants if m.mid not in killed]
            if not survivors:
                break
            rounds_used = rnd + 1
            if rnd == 0:
                prompt = prompts.build_initial_prompt(info, module_name, cfg.candidates_per_round)
            elif variant.feedback_mode == "coverage":
                uncovered = sorted(target_exec - baseline_covered)
                prompt = prompts.build_feedback_prompt(
                    info, module_name, cfg.candidates_per_round, rnd, [], "coverage", uncovered
                )
            else:
                prompt = prompts.build_feedback_prompt(
                    info,
                    module_name,
                    cfg.candidates_per_round,
                    rnd,
                    survivors,
                    variant.feedback_mode,
                    [],
                    cfg.max_feedback_mutants,
                )

            resp = self.client.generate(
                _system_prompt(), prompt, purpose=f"{spec.target_id}:{variant.name}:r{rnd}"
            )
            self.ledger.add(
                purpose=f"{spec.target_id}:{variant.name}:r{rnd}",
                tokens_in=resp.tokens_in,
                tokens_out=resp.tokens_out,
                cost_usd=resp.cost_usd,
                cached=resp.cached,
            )
            res.llm_calls += 1
            res.tokens_in += resp.tokens_in
            res.tokens_out += resp.tokens_out
            res.cost_usd += resp.cost_usd

            codes = resp.split_candidates()[: cfg.candidates_per_round]
            accepted_this_round = 0

            for i, raw in enumerate(codes):
                generated += 1
                code = raw.strip()
                if not code:
                    reasons["empty"] += 1
                    continue
                if not _parses(code):
                    fixed, did_repair = self._maybe_repair(code)
                    repaired += int(did_repair)
                    if fixed is None:
                        reasons["syntax_error"] += 1
                        continue
                    code = fixed
                h = _norm_hash(code)
                if h in seen_hashes:
                    reasons["duplicate"] += 1
                    continue

                cand = Candidate(cid=f"R{rnd}C{i + 1}", round=rnd, code=code)
                fname = f"test_gen_{spec.function_name}_r{rnd}c{i + 1}.py"

                # correctness / flakiness on the original code
                needed = cfg.flaky_runs if variant.gate_enabled else 1
                outcomes: list[Outcome] = []
                for _ in range(needed):
                    o = run_tests_once(info.module_source, module_name, {fname: code}, cfg.test_timeout_sec)
                    outcomes.append(o)
                    if o is not Outcome.PASS:
                        break
                correct_ok = (
                    all(o is Outcome.PASS for o in outcomes) and bool(outcomes)
                    if variant.gate_enabled
                    else outcomes[0] is Outcome.PASS
                )
                if not correct_ok:
                    if Outcome.TIMEOUT in outcomes:
                        reasons["timeout"] += 1
                    elif len(outcomes) > 1 and outcomes[0] is Outcome.PASS:
                        reasons["flaky"] += 1
                        flaky_rejects += 1
                    else:
                        reasons["failing_on_original"] += 1
                    res.gate_log.append(
                        {"cid": cand.cid, "accepted": False, "reason": "correctness", "runs": [o.value for o in outcomes]}
                    )
                    continue

                # coverage of the candidate (diagnostic + coverage feedback)
                _, cov_lines, _cand_exec = measure_coverage(
                    info.module_source, module_name, {fname: code}, cfg.test_timeout_sec
                )
                cand.covered_lines = cov_lines

                # falsifiability: run against surviving mutants only
                if variant.gate_enabled:
                    current_survivors = [m for m in mutants if m.mid not in killed]
                    kill_map = evaluate_mutants(
                        current_survivors, module_name, {fname: code}, cfg.test_timeout_sec, cfg.workers
                    )
                    cand.kills = {mid for mid, o in kill_map.items() if o.killed_mutant}
                    cand.new_kills = set(cand.kills)  # survivors are, by definition, un-killed

                verdict = evaluate_candidate(
                    cand,
                    correctness_outcomes=outcomes,
                    kills=cand.kills,
                    covered_lines=cand.covered_lines,
                    baseline_covered=baseline_covered,
                    policy=policy,
                )
                cand.verdict = verdict
                if verdict.accepted:
                    accepted.append(cand)
                    seen_hashes.add(h)
                    killed |= cand.kills
                    accepted_this_round += 1
                    res.gate_log.append({"cid": cand.cid, "accepted": True, "new_kills": len(cand.kills)})
                else:
                    reasons.update(verdict.reject_reasons)
                    res.gate_log.append(
                        {"cid": cand.cid, "accepted": False, "reasons": verdict.reject_reasons}
                    )

            if accepted_this_round == 0 and not variant.continue_on_zero_accept:
                break

        # -- 4. final joint evaluation (shared across variants) ------------
        final_gen = [{"name": f"test_gen_{j:02d}.py", "code": c.code} for j, c in enumerate(accepted)]
        files = {"test_b0.py": b0_code, **{f["name"]: f["code"] for f in final_gen}}
        o = run_tests_once(info.module_source, module_name, files, cfg.test_timeout_sec)
        if o is not Outcome.PASS:
            # Drop interaction failures: each generated file is re-verified
            # together with B0; culprits are removed (rare, but possible).
            for _ in range(3):
                culprits = [
                    f
                    for f in final_gen
                    if run_tests_once(
                        info.module_source,
                        module_name,
                        {"test_b0.py": b0_code, f["name"]: f["code"]},
                        cfg.test_timeout_sec,
                    )
                    is not Outcome.PASS
                ]
                if not culprits:
                    break
                for f in culprits:
                    files.pop(f["name"], None)
                    final_gen = [g for g in final_gen if g["name"] != f["name"]]
                o = run_tests_once(info.module_source, module_name, files, cfg.test_timeout_sec)
                if o is Outcome.PASS:
                    break
        res.final_suite_passes = o is Outcome.PASS
        res.n_final_tests = len(final_gen)
        res.accepted_codes = [f["code"] for f in final_gen]

        final_kills = evaluate_mutants(mutants, module_name, files, cfg.test_timeout_sec, cfg.workers)
        res.killed_final = sum(1 for o in final_kills.values() if o.killed_mutant)

        _, final_cov, final_exec = measure_coverage(
            info.module_source, module_name, files, cfg.test_timeout_sec
        )
        res.coverage_pct = round(
            coverage_pct(final_cov, final_exec, range(info.start_line, info.end_line + 1)), 1
        )
        covered_mutants = [m for m in mutants if m.line in final_cov]
        res.mutants_covered = len(covered_mutants)
        res.killed_covered = sum(1 for m in covered_mutants if final_kills[m.mid].killed_mutant)

        res.mutant_summary = [
            {
                "mid": m.mid,
                "operator": m.operator,
                "line": m.line,
                "description": m.description,
                "killed_by_b0": m.mid in killed_by_b0,
                "killed_by_final": final_kills[m.mid].killed_mutant
                if m.mid in final_kills
                else None,
                "covered": m.line in final_cov,
            }
            for m in mutants
        ]

        res.n_generated = generated
        res.n_accepted = len(final_gen)
        res.n_repaired = repaired
        res.rejection_reasons = dict(reasons)
        res.flaky_rejects = flaky_rejects
        res.rounds_used = rounds_used
        res.wall_sec = round(time.perf_counter() - t0, 1)
        return res

    # ------------------------------------------------------------- repair
    def _maybe_repair(self, bad_code: str) -> tuple[str | None, bool]:
        """One repair attempt for a syntactically broken candidate (API mode
        only — the mock always emits parseable files)."""
        if self.cfg.mode != "api":
            return None, False
        try:
            compile(bad_code, "<candidate>", "exec")
            error = "unknown"
        except SyntaxError as exc:
            error = f"{type(exc).__name__}: {exc}"
        prompt = prompts.build_repair_prompt(bad_code, error)
        try:
            resp = self.client.generate(_system_prompt(), prompt, purpose="repair")
        except RuntimeError:
            return None, True
        text = resp.text.strip()
        # strip a possible markdown fence
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("python"):
                text = text[len("python") :]
        if _parses(text):
            return text, True
        return None, True


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _system_prompt() -> str:
    from ..llm.client import SYSTEM_PROMPT

    return SYSTEM_PROMPT
