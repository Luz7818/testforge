"""Tests for the offline mock LLM: determinism + generated tests must pass."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from testforge.llm.client import MockLLMClient, split_candidates

MODULE = '''\
def add(a: int, b: int) -> int:
    """Add two ints."""
    return a + b


def div(a: int, b: int) -> float:
    """Divide; b == 0 raises ZeroDivisionError."""
    if b == 0:
        raise ZeroDivisionError("b is zero")
    return a / b
'''

PROMPT = (
    "=== MODULE_NAME ===\nfake_mod\n\n"
    "=== FUNCTION_NAME ===\ndiv\n\n"
    "=== SIGNATURE ===\ndef div(a: int, b: int) -> float:\n\n"
    "=== CANDIDATE_COUNT ===\n3\n\n"
    "=== ROUND ===\n1\n\n"
    "=== SURVIVING_MUTANTS ===\n[M001] line 9 (ROR): `b == 0` -> `b != 0`\n\n"
    "=== MODULE_SOURCE ===\n" + MODULE + "\n\n"
    "=== FUNCTION ===\ndef div(a: int, b: int) -> float:\n    if b == 0:\n        raise ZeroDivisionError('b is zero')\n    return a / b\n"
)


def test_mock_generates_requested_candidates():
    resp = MockLLMClient().generate("sys", PROMPT)
    cands = resp.split_candidates()
    assert len(cands) == 3
    for c in cands:
        assert "import pytest" in c
        assert "from fake_mod import div" in c


def test_mock_is_deterministic():
    a = MockLLMClient().generate("sys", PROMPT).text
    b = MockLLMClient().generate("sys", PROMPT).text
    assert a == b


def test_mock_generated_tests_pass_on_original():
    """The characterization tests must pass against the code they captured."""
    resp = MockLLMClient().generate("sys", PROMPT)
    cands = split_candidates(resp.text)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "fake_mod.py").write_text(MODULE, encoding="utf-8")
        for i, code in enumerate(cands):
            (td / f"test_gen_{i}.py").write_text(code, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "."],
            cwd=td, capture_output=True, text=True, env=env,
        )
        assert r.returncode == 0, r.stdout + r.stderr
