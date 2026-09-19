"""Run configuration, loaded from defaults + environment variables."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _default_workers() -> int:
    try:
        cpus = os.cpu_count() or 4
    except Exception:  # pragma: no cover
        return 4
    return max(2, min(8, cpus - 2))


@dataclass
class ForgeConfig:
    """All knobs of the agent. Variants in the experiment section override
    ``max_rounds`` / ``gate_enabled`` / ``feedback_mode``."""

    # LLM backend: "mock" (deterministic, offline) or "api" (OpenAI-compatible).
    mode: str = "mock"
    model: str = "deepseek-chat"
    api_base: str = "https://api.deepseek.com"
    api_key: str | None = None
    temperature: float = 0.8
    max_tokens: int = 2048
    llm_timeout_sec: float = 120.0
    llm_retries: int = 3
    # Extra JSON merged into each chat-completions request body (openai SDK
    # ``extra_body``). Use for provider-specific knobs, e.g. Qwen3 thinking
    # mode: '{"enable_thinking": false}' (DashScope-style top level) or
    # '{"chat_template_kwargs": {"enable_thinking": false}}' (vLLM native).
    extra_body: str = ""

    # Agent loop.
    candidates_per_round: int = 4
    max_rounds: int = 3
    feedback_mode: str = "mutants"  # mutants | coverage | none
    gate_enabled: bool = True
    max_feedback_mutants: int = 8

    # Mutation engine.
    max_mutants: int = 24
    mutation_seed: int = 20260919

    # Test execution.
    test_timeout_sec: float = 8.0
    flaky_runs: int = 5  # reruns against the original code

    # Coverage / acceptance policy. Coverage delta is reported by default but
    # not enforced: an assertion-strengthening test may add no new lines while
    # still detecting new bugs. Set require_coverage_delta=True to mimic
    # TestGen-LLM style acceptance.
    require_coverage_delta: bool = False

    workers: int = field(default_factory=_default_workers)

    # Cost accounting (USD per 1M tokens). Placeholder estimates — update from
    # the provider pricing page before quoting absolute numbers; token counts
    # in the ledger are always exact.
    price_input_per_m: float = 0.27
    price_output_per_m: float = 1.10

    # Cache for LLM responses so re-runs are free and reproducible.
    cache_dir: str = ""  # empty -> <project>/llm_cache when mode == "api"

    @classmethod
    def from_env(cls, mode: str | None = None) -> "ForgeConfig":
        mode = mode or os.environ.get("TESTFORGE_MODE", "mock")
        cfg = cls(mode=mode)
        cfg.api_key = os.environ.get("DEEPSEEK_API_KEY")
        cfg.model = os.environ.get("TESTFORGE_MODEL", cfg.model)
        cfg.api_base = os.environ.get("TESTFORGE_API_BASE", cfg.api_base)
        cfg.extra_body = os.environ.get("TESTFORGE_EXTRA_BODY", "")
        if mode == "api" and not cfg.api_key:
            raise SystemExit(
                "mode=api requires DEEPSEEK_API_KEY (any non-empty string for "
                "unauthenticated internal endpoints, see .env.example). "
                "Or run with mode=mock for the offline pipeline."
            )
        return cfg

    def extra_body_dict(self) -> dict:
        if not self.extra_body.strip():
            return {}
        parsed = json.loads(self.extra_body)
        if not isinstance(parsed, dict):
            raise ValueError("TESTFORGE_EXTRA_BODY must be a JSON object")
        return parsed

    def validate(self) -> None:
        if self.mode not in ("mock", "api"):
            raise ValueError(f"unknown mode: {self.mode}")
        if self.feedback_mode not in ("mutants", "coverage", "none"):
            raise ValueError(f"unknown feedback_mode: {self.feedback_mode}")
