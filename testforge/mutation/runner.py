"""Mutant execution: the kill-matrix workhorse.

One subprocess per (mutant, test-suite) pair: the mutated module plus the
test files are written into a throwaway directory and pytest runs with
``-x`` (first failure ends the run — a kill). Pairs are executed in a
process pool; TIMEOUT counts as a kill (behavior change) per the standard
convention.
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..types import Mutant, Outcome
from ..utils import workspace

_PYTEST_ARGS = ["-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"]


def classify_rc(rc: int) -> Outcome:
    """Map a pytest exit code to an Outcome. 5 (no tests collected) maps to
    PASS: nothing failed, and the falsifiability gate rejects such files."""
    if rc == 0 or rc == 5:
        return Outcome.PASS
    if rc == 1:
        return Outcome.FAIL
    if rc == -9:
        return Outcome.TIMEOUT
    return Outcome.ERROR


def _mutant_job(job: dict) -> tuple[str, str, float]:
    t0 = time.perf_counter()
    with workspace(
        job["module_source"], job["module_name"], job["test_files"]
    ) as wd:
        rc, _out = run_cmd_pytest(wd, list(job["test_files"].keys()), job["timeout"])
    outcome = classify_rc(rc)
    return job["mid"], outcome.value, time.perf_counter() - t0


def run_cmd_pytest(wd: Path, test_files: list[str], timeout: float):
    from ..utils import run_cmd

    return run_cmd([*_PYTEST_ARGS, *test_files], wd, timeout)


def evaluate_mutants(
    mutants: list[Mutant],
    module_name: str,
    test_files: dict[str, str],
    timeout: float,
    workers: int,
) -> dict[str, Outcome]:
    """Run ``test_files`` against every mutant. Returns mid -> Outcome."""
    if not mutants:
        return {}
    jobs = [
        {
            "mid": m.mid,
            "module_name": module_name,
            "module_source": m.mutated_source,
            "test_files": test_files,
            "timeout": timeout,
        }
        for m in mutants
    ]
    results: dict[str, Outcome] = {}
    n_workers = max(1, min(workers, len(jobs)))
    if n_workers == 1:
        for job in jobs:
            mid, outcome, _ = _mutant_job(job)
            results[mid] = Outcome(outcome)
        return results
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        for mid, outcome, _ in ex.map(_mutant_job, jobs, chunksize=1):
            results[mid] = Outcome(outcome)
    return results
