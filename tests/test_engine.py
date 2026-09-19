"""Unit tests for mutant generation (splicing, validation, sampling)."""
import ast

from testforge.mutation.engine import generate_mutants, splice

SRC = '''\
def top(n: int) -> int:
    """Top-level doc."""
    total = 0
    for i in range(n):
        if i % 2 == 0:
            total += i
        else:
            total -= 1
    return total
'''


def test_generate_mutants_parses_and_differs():
    mutants = generate_mutants(SRC, "top", max_mutants=50, seed=1)
    assert mutants, "expected mutants"
    for m in mutants:
        ast.parse(m.mutated_source)  # must stay valid Python
        assert m.mutated_source != SRC
        assert m.diff.startswith("---")


def test_mutant_ids_sorted_and_unique():
    mutants = generate_mutants(SRC, "top", max_mutants=50, seed=1)
    ids = [m.mid for m in mutants]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_sampling_caps_mutant_count():
    mutants = generate_mutants(SRC, "top", max_mutants=5, seed=1)
    assert len(mutants) <= 5


def test_sampling_is_deterministic_per_seed():
    a = [m.mid for m in generate_mutants(SRC, "top", max_mutants=4, seed=1)]
    b = [m.mid for m in generate_mutants(SRC, "top", max_mutants=4, seed=1)]
    c = [m.mid for m in generate_mutants(SRC, "top", max_mutants=4, seed=2)]
    assert a == b  # same seed -> identical selection
    assert len(a) == 4


def test_splice_replaces_exact_segment():
    tree = ast.parse(SRC)
    ret = None
    for n in ast.walk(tree):
        if isinstance(n, ast.Return):
            ret = n
    out = splice(SRC, ret, "return -1")
    assert "return -1" in out
    ast.parse(out)


def test_unknown_function_raises():
    import pytest

    with pytest.raises(ValueError):
        generate_mutants(SRC, "nope", max_mutants=10, seed=1)
