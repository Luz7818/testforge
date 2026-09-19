"""Unit tests for the quality gate logic (pure classification)."""
from testforge.gate.gate import GatePolicy, evaluate_candidate
from testforge.types import Candidate, Outcome


def make_cand():
    return Candidate(cid="R0C1", round=0, code="def test_x():\n    assert 1\n")


def test_gate_accepts_strong_candidate():
    cand = make_cand()
    v = evaluate_candidate(
        cand,
        correctness_outcomes=[Outcome.PASS] * 5,
        kills={"M001", "M002"},
        covered_lines={1, 2},
        baseline_covered=set(),
        policy=GatePolicy(gate_enabled=True, flaky_runs=5),
    )
    assert v.accepted


def test_gate_rejects_flaky():
    cand = make_cand()
    v = evaluate_candidate(
        cand,
        correctness_outcomes=[Outcome.PASS, Outcome.FAIL],
        kills={"M001"},
        covered_lines=set(),
        baseline_covered=set(),
        policy=GatePolicy(gate_enabled=True, flaky_runs=5),
    )
    assert not v.accepted
    assert "runs_on_original" in v.reject_reasons


def test_gate_rejects_non_falsifiable():
    cand = make_cand()
    v = evaluate_candidate(
        cand,
        correctness_outcomes=[Outcome.PASS] * 5,
        kills=set(),
        covered_lines=set(),
        baseline_covered=set(),
        policy=GatePolicy(gate_enabled=True, flaky_runs=5),
    )
    assert not v.accepted
    assert "falsifiable" in v.reject_reasons


def test_gate_off_accepts_single_pass():
    cand = make_cand()
    v = evaluate_candidate(
        cand,
        correctness_outcomes=[Outcome.PASS],
        kills=set(),
        covered_lines=set(),
        baseline_covered=set(),
        policy=GatePolicy(gate_enabled=False),
    )
    assert v.accepted


def test_coverage_delta_enforced_when_configured():
    cand = make_cand()
    v = evaluate_candidate(
        cand,
        correctness_outcomes=[Outcome.PASS] * 5,
        kills={"M001"},
        covered_lines={1},
        baseline_covered={1},
        policy=GatePolicy(gate_enabled=True, require_coverage_delta=True),
    )
    assert not v.accepted
    assert "coverage_delta" in v.reject_reasons
