from .gate import GatePolicy, evaluate_candidate
from .runner import measure_coverage, run_tests_once

__all__ = ["GatePolicy", "evaluate_candidate", "measure_coverage", "run_tests_once"]


def coverage_pct(executed: set[int], executable: set[int], line_range: range) -> float:
    """Line coverage over *executable* lines within ``line_range`` (1-based,
    inclusive). Empty executable set -> 0.0."""
    target_exec = {l for l in executable if l in line_range}
    if not target_exec:
        return 0.0
    return 100.0 * len(target_exec & executed) / len(target_exec)
