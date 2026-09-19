"""Integration test for the kill-matrix runner (subprocess based)."""
from testforge.mutation import evaluate_mutants, generate_mutants
from testforge.types import Outcome

SRC = '''\
def inc(x: int) -> int:
    """Return x plus one."""
    return x + 1
'''

STRONG_TEST = "from inc_mod import inc\n\ndef test_inc():\n    assert inc(1) == 2\n"
WEAK_TEST = "from inc_mod import inc\n\ndef test_inc():\n    inc(1)\n"


def _mutants():
    return generate_mutants(SRC, "inc", max_mutants=50, seed=7)


def test_strong_test_kills_aor_mutant():
    mutants = _mutants()
    assert mutants
    res = evaluate_mutants(mutants, "inc_mod", {"test_a.py": STRONG_TEST}, timeout=15.0, workers=2)
    # every mutant of `inc` changes observable behavior on inc(1) except
    # possibly equivalent ones; at least the AOR x+1 -> x-1 must die
    killed = [mid for mid, o in res.items() if o.killed_mutant]
    assert killed, res


def test_weak_test_kills_nothing():
    mutants = _mutants()
    res = evaluate_mutants(mutants, "inc_mod", {"test_a.py": WEAK_TEST}, timeout=15.0, workers=2)
    assert all(o is Outcome.PASS for o in res.values())
