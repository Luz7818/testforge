"""Run configuration, loaded from defaults + a local .env + environment variables."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def _load_dotenv(env_file: Path | None = None) -> int:
    """Seed ``os.environ`` from a local ``.env``, without overriding what is
    already set. Returns the number of variables actually applied.

    Zero dependencies, and deliberately the same format and precedence as the
    other projects in this workspace: ``KEY=VALUE`` per line, ``#`` for whole-line
    comments, surrounding whitespace and one layer of matching quotes stripped.
    Inline comments are *not* stripped because a value may legitimately contain
    ``#``; keep comments on their own line.

    Precedence is shell export > .env > dataclass default, so an exported key
    always wins and ``.env`` only fills gaps. A missing file is not an error:
    CI runs with no ``.env`` at all and the mock backend needs no key.
    """
    path = ENV_FILE if env_file is None else env_file
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    applied = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        applied += 1
    return applied


_load_dotenv()


def _default_workers() -> int:
    try:
        cpus = os.cpu_count() or 4
    except Exception:  # pragma: no cover
        return 4
    return max(2, min(8, cpus - 2))


def _load_price_table() -> dict:
    """Read pricing.json at the repo root -> {model: entry}. Missing, empty or
    malformed file means "no prices configured", never an error."""
    path = PROJECT_ROOT / "pricing.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    prices = data.get("prices")
    if not isinstance(prices, list):
        return {}
    return {p["model"]: p for p in prices if isinstance(p, dict) and "model" in p}


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
    # Fill the mutant budget with mutants on baseline-executed lines first
    # (PRIMG-style priority), falling back to uncovered lines only if the
    # budget allows. Off by default: published grids use the historical
    # stratified sampling, and priority changes WHICH mutants get sampled.
    mutant_priority: bool = False
    # Skip executing mutants whose mutated line the suite under test does not
    # execute: unreachable code cannot change observed behavior, so those
    # mutants are recorded as PASS without a subprocess (results identical,
    # kill-matrix cost drops to the covered fraction). Off by default for
    # reproducibility bookkeeping; the toggle changes cost, never outcomes.
    incremental_execution: bool = False

    # Test execution.
    test_timeout_sec: float = 8.0
    flaky_runs: int = 5  # reruns against the original code

    # Coverage / acceptance policy. Coverage delta is reported by default but
    # not enforced: an assertion-strengthening test may add no new lines while
    # still detecting new bugs. Set require_coverage_delta=True to mimic
    # TestGen-LLM style acceptance.
    require_coverage_delta: bool = False

    # Property-based generation (Mock backend only): emit deterministic
    # @given property tests (Hypothesis-style) instead of single-example
    # characterization tests. Requires the optional `hypothesis` dependency
    # (pip install -e .[property]); falls back to characterization mode with
    # a warning when it is not importable. The generation space upgrades,
    # the feedback signal and the gate stay unchanged.
    property_based: bool = False

    workers: int = field(default_factory=_default_workers)

    # Cost accounting. Token counts in the ledger are always exact; a USD
    # figure is produced ONLY when a price is explicitly provided, so a
    # missing price shows up as "no dollar figure" instead of a fake $0.
    # Sources, in precedence order:
    #   1. TESTFORGE_PRICE_INPUT_PER_M / TESTFORGE_PRICE_OUTPUT_PER_M env
    #      (price_source records "env override")
    #   2. a matching "model" entry in pricing.json at the repo root
    #      (price_source records that entry's "source" and "effective" date)
    # v0.1 hard-coded placeholder prices here, which multiplied exact token
    # counts into seemingly-exact dollar figures — archived results from that
    # era carry no price provenance and are reported as unpriced.
    price_input_per_m: float | None = None
    price_output_per_m: float | None = None
    price_source: str = ""

    # Cache for LLM responses so re-runs are free and reproducible.
    cache_dir: str = ""  # empty -> <project>/llm_cache when mode == "api"

    @classmethod
    def from_env(cls, mode: str | None = None) -> ForgeConfig:
        mode = mode or os.environ.get("TESTFORGE_MODE", "mock")
        cfg = cls(mode=mode)
        cfg.api_key = os.environ.get("DEEPSEEK_API_KEY")
        cfg.model = os.environ.get("TESTFORGE_MODEL", cfg.model)
        cfg.api_base = os.environ.get("TESTFORGE_API_BASE", cfg.api_base)
        cfg.extra_body = os.environ.get("TESTFORGE_EXTRA_BODY", "")
        mt = os.environ.get("TESTFORGE_MAX_TOKENS")
        if mt:
            cfg.max_tokens = int(mt)
        lr = os.environ.get("TESTFORGE_LLM_RETRIES")
        if lr:
            cfg.llm_retries = int(lr)
        if os.environ.get("TESTFORGE_MUTANT_PRIORITY", "").strip().lower() in ("1", "true", "yes"):
            cfg.mutant_priority = True
        if os.environ.get("TESTFORGE_INCREMENTAL", "").strip().lower() in ("1", "true", "yes"):
            cfg.incremental_execution = True
        if os.environ.get("TESTFORGE_PROPERTY", "").strip().lower() in ("1", "true", "yes"):
            cfg.property_based = True
        # Point at a different directory to force fresh LLM samples: an
        # unchanged cache replays responses bit-for-bit, which is exactly what
        # a replication run must avoid.
        cfg.cache_dir = os.environ.get("TESTFORGE_CACHE_DIR", "")
        pin = os.environ.get("TESTFORGE_PRICE_INPUT_PER_M")
        pout = os.environ.get("TESTFORGE_PRICE_OUTPUT_PER_M")
        if pin or pout:
            cfg.price_input_per_m = float(pin) if pin else None
            cfg.price_output_per_m = float(pout) if pout else None
            cfg.price_source = "TESTFORGE_PRICE_* env override"
        else:
            entry = _load_price_table().get(cfg.model)
            if entry:
                cfg.price_input_per_m = entry.get("input_per_m")
                cfg.price_output_per_m = entry.get("output_per_m")
                cfg.price_source = (
                    f"pricing.json: {entry.get('source', 'unspecified source')}, "
                    f"effective {entry.get('effective', 'unspecified date')}"
                )
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
