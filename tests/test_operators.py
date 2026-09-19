"""Unit tests for the AST mutation operators."""
import ast

from testforge.mutation.operators import find_mutation_candidates


def ops_of(source, func=None):
    tree = ast.parse(source)
    root = tree
    if func:
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == func:
                root = n
                break
    return find_mutation_candidates(root, source)


def test_aor_on_binop():
    cands = ops_of("def f(a, b):\n    return a + b\n", "f")
    aor = [c for c in cands if c.operator == "AOR"]
    assert len(aor) == 1
    assert aor[0].replacement.startswith("a - b")


def test_ror_on_compare():
    cands = ops_of("def f(a):\n    return a > 0\n", "f")
    ror = [c for c in cands if c.operator == "ROR"]
    assert len(ror) == 1
    assert "not" not in ror[0].replacement  # > becomes <=, not 'not ...'


def test_bcr_flips_boolean():
    cands = ops_of("def f():\n    return True\n", "f")
    bcr = [c for c in cands if c.operator == "BCR"]
    assert len(bcr) == 1 and bcr[0].replacement == "False"


def test_crn_and_crs():
    cands = ops_of('def f():\n    return "ab" + str(3)\n', "f")
    kinds = {c.operator for c in cands}
    assert "CRS" in kinds and "CRN" in kinds


def test_uor_removes_not():
    cands = ops_of("def f(a):\n    return not a\n", "f")
    uor = [c for c in cands if c.operator == "UOR"]
    assert len(uor) == 1 and uor[0].replacement == "a"


def test_rtn_returns_none():
    cands = ops_of("def f(a):\n    return a * 2\n", "f")
    rtn = [c for c in cands if c.operator == "RTN"]
    assert len(rtn) == 1 and rtn[0].replacement == "return None"


def test_docstring_not_mutated():
    cands = ops_of('def f():\n    """Doc here."""\n    return 1\n', "f")
    assert all("Doc" not in c.replacement for c in cands)


def test_error_message_strings_not_mutated():
    src = 'def f(a):\n    if a < 0:\n        raise ValueError("negative input")\n    return a\n'
    cands = ops_of(src, "f")
    assert all("negative input" not in c.replacement for c in cands)


def test_annotations_not_mutated():
    src = "def f(a: int) -> int:\n    x: int = 5\n    return a + x\n"
    cands = ops_of(src, "f")
    crn = [c for c in cands if c.operator == "CRN"]
    # only the *value* 5 is executable; argument/return annotations must not
    # be mutated
    assert len(crn) == 1
    assert crn[0].node.lineno == 2 and crn[0].replacement == "6"
