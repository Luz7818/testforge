"""Serial test execution helpers used by the quality gate: running candidate
tests against the *original* code (correctness + flakiness) and measuring
line coverage of the module under test."""

from __future__ import annotations

import json

from ..mutation.runner import classify_rc
from ..types import Outcome
from ..utils import run_cmd, workspace

_COVERAGE_TIMEOUT = 60.0


def run_tests_once(
    module_source: str,
    module_name: str,
    test_files: dict[str, str],
    timeout: float,
) -> Outcome:
    with workspace(module_source, module_name, test_files) as wd:
        from ..mutation.runner import run_cmd_pytest

        rc, _ = run_cmd_pytest(wd, list(test_files.keys()), timeout)
    return classify_rc(rc)


def measure_coverage(
    module_source: str,
    module_name: str,
    test_files: dict[str, str],
    timeout: float,
) -> tuple[Outcome, set[int], set[int]]:
    """Run the tests under coverage.

    Returns (outcome, executed module lines, executable module lines).
    The executable set (executed ∪ missing) excludes docstrings, blank and
    comment lines, so downstream percentages are computed over a meaningful
    denominator.
    """
    with workspace(module_source, module_name, test_files) as wd:
        rc, _out = run_cmd(
            [
                "-m",
                "coverage",
                "run",
                f"--include={module_name}.py",
                "-m",
                "pytest",
                "-x",
                "-q",
                "-p",
                "no:cacheprovider",
                *test_files.keys(),
            ],
            wd,
            timeout,
        )
        if rc == -9:
            return Outcome.TIMEOUT, set(), set()
        rc2, payload = run_cmd(["-m", "coverage", "json", "-o", "-"], wd, _COVERAGE_TIMEOUT)
    if rc2 != 0:
        return classify_rc(rc), set(), set()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return classify_rc(rc), set(), set()
    executed: set[int] = set()
    executable: set[int] = set()
    for path, info in data.get("files", {}).items():
        if path.replace("\\", "/").endswith(f"/{module_name}.py") or path == f"{module_name}.py":
            executed.update(info.get("executed_lines", []))
            executable.update(info.get("executed_lines", []))
            executable.update(info.get("missing_lines", []))
            break
    return classify_rc(rc), executed, executable
