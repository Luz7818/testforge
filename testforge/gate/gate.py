"""The multi-signal quality gate.

Acceptance policy (gate mode, the default):
1. ``runs_on_original`` — the test passes on the current code, repeated
   ``flaky_runs`` times (determinism check).
2. ``falsifiable`` — the test kills at least one mutant that neither the
   existing suite nor any previously accepted test kills. A test that cannot
   detect *any* seeded bug is not evidence of quality, no matter how it
   looks.

Line-coverage delta is *reported* but not enforced by default: an
assertion-strengthening test may cover no new lines yet still catch bugs the
covered lines were never really checked for. ``require_coverage_delta``
switches to the TestGen-LLM-style policy for ablation.

With ``gate_enabled=False`` (the B1 "vibe testing" baseline) a candidate is
accepted after a single passing run — what a typical developer does.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..types import Candidate, CheckResult, GateVerdict, Outcome


@dataclass
class GatePolicy:
    gate_enabled: bool = True
    flaky_runs: int = 5
    require_coverage_delta: bool = False


def evaluate_candidate(
    candidate: Candidate,
    *,
    correctness_outcomes: list[Outcome],
    kills: set[str],
    covered_lines: set[int],
    baseline_covered: set[int],
    policy: GatePolicy,
) -> GateVerdict:
    checks: list[CheckResult] = []

    if policy.gate_enabled:
        n_pass = sum(1 for o in correctness_outcomes if o is Outcome.PASS)
        stable = n_pass == len(correctness_outcomes) and bool(correctness_outcomes)
        checks.append(
            CheckResult(
                "runs_on_original",
                stable,
                f"{n_pass}/{len(correctness_outcomes)} runs passed (flaky detection)",
            )
        )
        checks.append(
            CheckResult(
                "falsifiable",
                bool(kills),
                f"kills {len(kills)} surviving mutant(s)",
            )
        )
        if policy.require_coverage_delta:
            new_lines = covered_lines - baseline_covered
            checks.append(
                CheckResult(
                    "coverage_delta",
                    bool(new_lines),
                    f"{len(new_lines)} newly covered line(s)",
                )
            )
    else:
        single = bool(correctness_outcomes) and correctness_outcomes[0] is Outcome.PASS
        checks.append(
            CheckResult("runs_on_original", single, "single run (gate disabled)")
        )

    return GateVerdict(accepted=all(c.passed for c in checks), checks=checks)
