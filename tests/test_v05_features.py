"""Tests for the v0.5 engine/back-end upgrades.

Three independent, optional-by-default features:

1. mutant priority sampling — the budget fills with baseline-covered-line
   mutants first (PRIMG-style);
2. incremental mutant execution — mutants on lines the suite never runs are
   recorded PASS without a subprocess (outcomes identical, cost lower);
3. property-based mock generation — deterministic @given behavioral-envelope
   tests (needs the optional hypothesis dependency; tests skip without it).
"""

from __future__ import annotations

import textwrap

import pytest

from testforge.config import ForgeConfig
from testforge.mutation import evaluate_mutants, generate_mutants

_SRC = textwrap.dedent(
    """\
    def clamp(x, lo, hi):
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x
    """
)


def _covered_lines():
    # B0-ish suite: only exercises the lo-branch (lines 2-3).
    return {2, 3}


# -- 1. mutant priority sampling --------------------------------------------

def test_priority_fills_budget_with_covered_line_mutants():
    all_mutants = generate_mutants(_SRC, "clamp", max_mutants=10**6, seed=1)
    hot = {m.mid for m in all_mutants if m.line in _covered_lines()}
    assert hot, "fixture must produce hot mutants"

    prioritized = generate_mutants(
        _SRC, "clamp", max_mutants=2, seed=1, covered_lines=_covered_lines(), priority=True
    )
    assert len(prioritized) == 2
    assert {m.mid for m in prioritized} <= hot


def test_priority_falls_back_to_uncovered_lines():
    all_mutants = generate_mutants(_SRC, "clamp", max_mutants=10**6, seed=1)
    hot = [m for m in all_mutants if m.line in _covered_lines()]
    prioritized = generate_mutants(
        _SRC, "clamp", max_mutants=len(hot) + 2, seed=1,
        covered_lines=_covered_lines(), priority=True,
    )
    got_hot = [m for m in prioritized if m.line in _covered_lines()]
    got_cold = [m for m in prioritized if m.line not in _covered_lines()]
    assert len(got_hot) == len(hot)
    assert len(got_cold) == 2


def test_priority_off_keeps_historical_selection():
    # The default path must match the pre-0.5 call exactly.
    a = generate_mutants(_SRC, "clamp", max_mutants=3, seed=7)
    b = generate_mutants(_SRC, "clamp", max_mutants=3, seed=7, covered_lines=None, priority=False)
    assert [(m.mid, m.line, m.replacement) for m in a] == [
        (m.mid, m.line, m.replacement) for m in b
    ]


# -- 2. incremental mutant execution ----------------------------------------

def test_incremental_skips_uncovered_mutants_without_running_them():
    mutants = generate_mutants(_SRC, "clamp", max_mutants=10**6, seed=3)
    hot = [m for m in mutants if m.line in _covered_lines()]
    cold = [m for m in mutants if m.line not in _covered_lines()]
    assert hot and cold
    # Make an uncovered mutant's source syntactically broken: if the runner
    # executed it, pytest would error out -> ERROR, not PASS.
    for m in cold:
        m.mutated_source = "def clamp(:\n  this is not python"

    strong = {"test_x.py": (
        "from clamp import clamp\n\n"
        "def test_lo():\n    assert clamp(1, 2, 5) == 2\n"
    )}
    outcomes = evaluate_mutants(
        mutants, "clamp", strong, timeout=8.0, workers=1, covered_lines=_covered_lines()
    )
    for m in cold:
        assert outcomes[m.mid].value == "pass", (
            "uncovered mutant must be recorded PASS without execution"
        )
    for m in hot:
        assert m.mid in outcomes


def test_incremental_full_results_match_unrestricted_run():
    """The toggle changes cost, never outcomes: with the covered set of the
    same suite, every mutant's outcome equals the unrestricted run."""
    mutants = generate_mutants(_SRC, "clamp", max_mutants=10**6, seed=4)
    tests = {"test_x.py": (
        "from clamp import clamp\n\n"
        "def test_all():\n"
        "    assert clamp(1, 2, 5) == 2\n"
        "    assert clamp(9, 2, 5) == 5\n"
        "    assert clamp(3, 2, 5) == 3\n"
    )}
    covered = {2, 3, 4, 5, 6}  # this suite covers the whole function
    full = evaluate_mutants(mutants, "clamp", tests, timeout=8.0, workers=1)
    inc = evaluate_mutants(mutants, "clamp", tests, timeout=8.0, workers=1, covered_lines=covered)
    assert full == inc


# -- 3. property-based mock generation ---------------------------------------

hypothesis = pytest.importorskip("hypothesis")

from testforge.llm.client import MockLLMClient  # noqa: E402


def _prompt_for(src: str, fn: str, module: str, count: int = 2, rnd: int = 0) -> str:
    # Markers must sit at column 0: the block parser anchors them with ^=== .
    return (
        f"=== MODULE_SOURCE ===\n{src}"
        f"=== MODULE_NAME ===\n{module}\n"
        f"=== FUNCTION_NAME ===\n{fn}\n"
        f"=== SIGNATURE ===\ndef {fn}(x, lo, hi):\n"
        f"=== CANDIDATE_COUNT ===\n{count}\n"
        f"=== ROUND ===\n{rnd}\n"
        f"=== SURVIVING_MUTANTS ===\n"
    )


def test_property_mode_emits_given_tests_and_they_pass():
    cfg = ForgeConfig(property_based=True)
    client = MockLLMClient(cfg)
    resp = client.generate("sys", _prompt_for(_SRC, "clamp", "clamp"), purpose="t")
    codes = resp.split_candidates()
    assert len(codes) == 2
    for code in codes:
        assert "@given(" in code and "derandomize=True" in code
        assert "behavioral_envelope" in code


def test_property_mode_deterministic_across_clients():
    cfg = ForgeConfig(property_based=True)
    a = MockLLMClient(cfg).generate("sys", _prompt_for(_SRC, "clamp", "clamp"), purpose="t").text
    b = MockLLMClient(cfg).generate("sys", _prompt_for(_SRC, "clamp", "clamp"), purpose="t").text
    assert a == b


def test_property_tests_kill_mutants_characterization_misses():
    """The envelope property spans a frozen input domain, so value mutants on
    rarely-probed branches are killed where single-example tests miss them."""
    from testforge.mutation import generate_mutants as gm

    mutants = gm(_SRC, "clamp", max_mutants=10**6, seed=5)

    def kills(client):
        resp = client.generate("sys", _prompt_for(_SRC, "clamp", "clamp", count=4), purpose="t")
        codes = resp.split_candidates()
        killed = set()
        for i, code in enumerate(codes):
            km = evaluate_mutants(mutants, "clamp", {f"t{i}.py": code}, timeout=8.0, workers=1)
            killed |= {mid for mid, o in km.items() if o.killed_mutant}
        return killed

    pk = kills(MockLLMClient(ForgeConfig(property_based=True)))
    ck = kills(MockLLMClient(ForgeConfig(property_based=False)))
    assert pk >= ck, "property mode must kill a superset of characterization kills"
    assert len(pk) > len(ck), "the envelope should add kills beyond single examples"
