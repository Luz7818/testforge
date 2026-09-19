"""Prompt construction for the generator LLM.

The prompt is fully structured (``=== BLOCK ===`` sections) so that both a
real model and the offline mock can parse it reliably. Surviving-mutant
feedback is the core trick: the model sees the exact seeded bugs its tests
failed to catch, as minimal before/after diffs.
"""

from __future__ import annotations

from ..types import Mutant, TargetInfo

_TASK_RULES = """Requirements:
- Output exactly {k} independent candidate test files, separated by marker lines
  `# ==== CANDIDATE 0 ====` through `# ==== CANDIDATE {kmax} ====` (marker at column 0).
- Each candidate is a complete, self-contained pytest file that starts with
  `import pytest` and imports the function under test from module `{module_name}`.
- Use only the Python standard library and pytest. No I/O, no randomness, no time,
  no network. Tests must be deterministic and finish in well under one second.
- Write STRONG oracles: assert exact expected values, cover boundary inputs
  (empty, zero, negative, single element, large), and use `pytest.raises` for the
  documented error contract. A test without a meaningful assertion is worthless.
- Do not restate the implementation inside the test; assert externally observable
  behavior only.
- The current test file for this module is given for context: do not duplicate it,
  add value beyond it."""


def _header(info: TargetInfo, module_name: str) -> str:
    doc = info.docstring or "(no docstring)"
    params = "\n".join(
        f"  - {p['name']}: {p['annotation'] or 'unknown'}"
        + (f" = {p['default']}" if p["default"] else "")
        for p in info.params
    )
    ret = info.return_annotation or "unknown"
    return (
        f"=== MODULE_NAME ===\n{module_name}\n\n"
        f"=== FUNCTION_NAME ===\n{info.spec.function_name}\n\n"
        f"=== SIGNATURE ===\n{info.signature}\n\n"
        f"=== FUNCTION_DOC ===\n{doc}\n\n"
        f"=== PARAMETERS ===\n{params or '  - (none)'}\n\n"
        f"=== RETURNS ===\n{ret}\n\n"
        f"=== MODULE_SOURCE ===\n{info.module_source}\n"
    )


def build_initial_prompt(info: TargetInfo, module_name: str, k: int) -> str:
    existing = "(no existing tests)"
    if info.spec.existing_test_path:
        try:
            existing = open(info.spec.existing_test_path, encoding="utf-8").read()
        except OSError:
            existing = "(no existing tests)"
    return (
        "You are generating unit tests for one Python function.\n\n"
        + _header(info, module_name)
        + f"=== FUNCTION ===\n{info.function_source}\n\n"
        + f"=== EXISTING_TESTS ===\n{existing}\n\n"
        + f"=== CANDIDATE_COUNT ===\n{k}\n\n"
        + "=== ROUND ===\n0\n\n"
        + _TASK_RULES.format(k=k, kmax=k - 1, module_name=module_name)
    )


def build_feedback_prompt(
    info: TargetInfo,
    module_name: str,
    k: int,
    round_no: int,
    surviving_mutants: list[Mutant],
    mode: str,
    uncovered_lines: list[int],
    max_mutants: int = 8,
) -> str:
    if mode == "coverage":
        feedback = (
            "=== UNCOVERED_LINES ===\n"
            + (", ".join(map(str, uncovered_lines[:30])) or "(all lines covered)")
            + "\n\n"
            "The lines above are not yet exercised (or your assertions are too weak to "
            "show it). Generate tests that execute them and pin down their behavior.\n"
        )
    else:
        shown = surviving_mutants[:max_mutants]
        lines = [
            f"[{m.mid}] line {m.line} ({m.operator}): `{m.original}` -> `{m.replacement}`"
            for m in shown
        ]
        feedback = (
            f"=== SURVIVING_MUTANTS ===\n{chr(10).join(lines) or '(none)'}\n\n"
            "=== FEEDBACK_INSTRUCTIONS ===\n"
            f"Your previous tests FAILED to detect {len(surviving_mutants)} seeded bugs "
            "(mutants). Each mutant above is a small semantic change to the function; a "
            "mutant survives when no test notices the difference. Strengthen assertions "
            "or add cases whose expected output changes under these mutations. Focus on "
            "boundary values and error contracts.\n"
        )
    return (
        f"You are improving unit tests for one Python function (improvement round {round_no}).\n\n"
        + _header(info, module_name)
        + f"=== FUNCTION ===\n{info.function_source}\n\n"
        + feedback
        + f"=== CANDIDATE_COUNT ===\n{k}\n\n"
        + f"=== ROUND ===\n{round_no}\n\n"
        + _TASK_RULES.format(k=k, kmax=k - 1, module_name=module_name)
    )


def build_repair_prompt(bad_code: str, error: str) -> str:
    return (
        "The following pytest file has a defect (syntax or import error). "
        "Return the corrected complete file only, no commentary.\n\n"
        f"=== ERROR ===\n{error}\n\n"
        f"=== CODE ===\n{bad_code}\n"
    )
