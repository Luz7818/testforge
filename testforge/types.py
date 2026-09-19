"""Shared data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Outcome(str, Enum):
    """Result of one pytest subprocess run."""

    PASS = "pass"
    FAIL = "fail"          # at least one test failed (assertion)
    ERROR = "error"        # collection/import error
    TIMEOUT = "timeout"    # exceeded the wall-clock budget

    @property
    def killed_mutant(self) -> bool:
        """A run that does not pass counts as killing the mutant.

        TIMEOUT counts as killed: the mutated program hung where the original
        terminated, i.e. the test suite observed a behavior change. This is
        the standard convention (e.g. PIT).
        """
        return self is not Outcome.PASS


@dataclass
class TargetSpec:
    """One benchmark unit: a single function inside a module."""

    target_id: str                 # "string_utils.slugify"
    module_path: str               # absolute path of the module under test
    module_name: str               # importable name (file stem)
    function_name: str
    existing_test_path: str | None = None


@dataclass
class TargetInfo:
    spec: TargetSpec
    module_source: str
    function_source: str
    signature: str
    docstring: str | None
    params: list[dict]             # [{name, annotation, default}]
    return_annotation: str | None
    start_line: int                # 1-based, inclusive
    end_line: int                  # inclusive


@dataclass
class Mutant:
    mid: str                       # "M001"
    operator: str                  # AOR / ROR / BCR / CRN / CRS / UOR / RTN
    description: str
    line: int                      # 1-based line of the mutated node
    original: str                  # original source segment
    replacement: str               # mutated segment
    mutated_source: str
    diff: str                      # unified diff (small context)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class GateVerdict:
    accepted: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def reject_reasons(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]


@dataclass
class Candidate:
    """One LLM-proposed test file, and what the gate did to it."""

    cid: str                       # "R0C1"
    round: int
    code: str
    accepted: bool = False
    verdict: GateVerdict | None = None
    kills: set[str] = field(default_factory=set)       # all mutants it kills
    new_kills: set[str] = field(default_factory=set)   # kills nobody had yet
    covered_lines: set[int] = field(default_factory=set)
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class VariantSpec:
    """Experimental condition (B1/B2/B3/...)."""

    name: str
    rounds: int
    gate_enabled: bool
    feedback_mode: str             # mutants | coverage | none


@dataclass
class VariantResult:
    """Outcome of one (target, variant) cell of the experiment grid."""

    target_id: str
    variant: str
    # Mutation score block (final joint evaluation, shared evaluator).
    mutants_total: int = 0
    killed_final: int = 0
    mutants_covered: int = 0
    killed_covered: int = 0
    b0_killed_final: int = 0       # for reference: kills attributable to B0
    # Agent loop stats.
    n_generated: int = 0
    n_accepted: int = 0
    n_repaired: int = 0
    rejection_reasons: dict = field(default_factory=dict)
    flaky_rejects: int = 0
    rounds_used: int = 0
    # Final suite quality.
    n_final_tests: int = 0         # accepted candidates in final suite
    final_suite_passes: bool = True
    coverage_pct: float = 0.0      # line coverage of target function, B0+suite
    b0_coverage_pct: float = 0.0
    # Cost.
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    wall_sec: float = 0.0
    # Artifacts (kept for the report; may be large).
    accepted_codes: list[str] = field(default_factory=list)
    mutant_summary: list[dict] = field(default_factory=list)
    gate_log: list[dict] = field(default_factory=list)

    @property
    def ms_all(self) -> float:
        return self.killed_final / self.mutants_total if self.mutants_total else 0.0

    @property
    def ms_covered(self) -> float:
        return (
            self.killed_covered / self.mutants_covered
            if self.mutants_covered
            else 0.0
        )


@dataclass
class CostLedger:
    """Every LLM call (or cache hit) with exact token counts."""

    model: str = "mock"
    entries: list[dict] = field(default_factory=list)

    def add(
        self,
        purpose: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        cached: bool = False,
    ) -> None:
        self.entries.append(
            {
                "purpose": purpose,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost_usd, 6),
                "cached": cached,
            }
        )

    @property
    def total_cost(self) -> float:
        return sum(e["cost_usd"] for e in self.entries)

    @property
    def tokens_in(self) -> int:
        return sum(e["tokens_in"] for e in self.entries)

    @property
    def tokens_out(self) -> int:
        return sum(e["tokens_out"] for e in self.entries)

    @property
    def n_calls(self) -> int:
        return len(self.entries)

    def summary(self) -> dict:
        return {
            "model": self.model,
            "calls": self.n_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.total_cost, 4),
        }
