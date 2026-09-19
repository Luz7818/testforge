"""LLM backends.

Two interchangeable clients behind one interface:

- ``OpenAICompatClient`` — any OpenAI-compatible endpoint (DeepSeek by
  default), with prompt caching, retries and exact token/cost accounting.
- ``MockLLMClient`` — a deterministic, offline generator used to validate the
  whole pipeline with zero API cost. It produces *characterization tests*:
  it executes the target on sampled inputs and freezes the observed outputs
  (and error behavior) into assertions. This is a deliberate, documented
  baseline — it demonstrates the loop mechanics honestly and kills many
  value/operator mutants, but it cannot invent semantic oracles the way a
  real model can.

Both clients return *one response containing several candidate test files*
separated by the ``# ==== CANDIDATE k ====`` marker, which the orchestrator
splits.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
import zlib
from dataclasses import dataclass
from pathlib import Path

from ..config import ForgeConfig

CANDIDATE_MARKER = re.compile(r"^# ==== CANDIDATE \d+ ====\s*$", re.M)

SYSTEM_PROMPT = (
    "You are a meticulous Python test engineer. You write pytest unit tests "
    "with strong oracles: exact-value assertions, boundary cases, and "
    "pytest.raises for error contracts. You never write tests that assert "
    "nothing, and you never use randomness, network, filesystem or time in "
    "tests. Output must follow the requested format exactly."
)


@dataclass
class LLMResponse:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    model: str = "mock"

    def split_candidates(self) -> list[str]:
        """Split a raw completion into candidate test-file sources."""
        parts = CANDIDATE_MARKER.split(self.text)
        if len(parts) == 1:
            # No markers: treat the whole text as one candidate if it looks
            # like Python, else nothing.
            text = self.text.strip()
            return [text] if text.startswith(("#", "import", "from", '"', "'")) else []
        # parts[0] is anything before the first marker (usually preamble).
        return [p.strip() for p in parts[1:] if p.strip()]


def split_candidates(text: str) -> list[str]:
    return LLMResponse(text=text).split_candidates()


class OpenAICompatClient:
    """OpenAI-compatible chat client (DeepSeek etc.) with disk cache."""

    def __init__(self, config: ForgeConfig, cache_dir: Path):
        from openai import OpenAI  # imported lazily so mock mode needs no SDK

        self._cfg = config
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            timeout=config.llm_timeout_sec,
        )
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, system: str, prompt: str) -> Path:
        key = hashlib.sha256(
            f"{self._cfg.model}|{system}|{prompt}|{self._cfg.temperature}|{self._cfg.max_tokens}".encode()
        ).hexdigest()
        return self._cache_dir / f"{key}.json"

    def generate(self, system: str, prompt: str, purpose: str = "") -> LLMResponse:
        cpath = self._cache_path(system, prompt)
        if cpath.exists():
            data = json.loads(cpath.read_text(encoding="utf-8"))
            return LLMResponse(
                text=data["text"],
                tokens_in=data["tokens_in"],
                tokens_out=data["tokens_out"],
                cost_usd=data["cost_usd"],
                cached=True,
                model=self._cfg.model,
            )
        last_err: Exception | None = None
        for attempt in range(self._cfg.llm_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self._cfg.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self._cfg.temperature,
                    max_tokens=self._cfg.max_tokens,
                )
                text = resp.choices[0].message.content or ""
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0) or 0
                tokens_out = getattr(usage, "completion_tokens", 0) or 0
                cost = (
                    tokens_in / 1e6 * self._cfg.price_input_per_m
                    + tokens_out / 1e6 * self._cfg.price_output_per_m
                )
                out = LLMResponse(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost,
                    model=self._cfg.model,
                )
                cpath.write_text(
                    json.dumps(
                        {
                            "text": text,
                            "tokens_in": tokens_in,
                            "tokens_out": tokens_out,
                            "cost_usd": cost,
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return out
            except Exception as exc:  # noqa: BLE001 - retry any transport error
                last_err = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM call failed after retries: {last_err}")


class MockLLMClient:
    """Deterministic characterization-test generator (offline mode).

    Strategy per candidate file:
    1. Execute the module and probe the target with sampled inputs.
    2. Freeze observed return values into exact assertions (capture & replay).
    3. Freeze observed exceptions into ``pytest.raises`` contracts.
    Rounds > 0 re-sample with edge-heavy distributions and seeds derived from
    the surviving-mutant list, so the feedback loop changes behavior.
    """

    _VALUES = {
        "int": [3, 0, 1, -1, 7, 100, 2, 16, 65535, 12],
        "float": [1.0, 0.0, -2.5, 3.14, 100.0, 0.5],
        "str": [
            "",
            "a",
            "Hello World",
            "  x  y  ",
            "a,b@c",
            "ABC123",
            "-",
            "2024-01-15",
            "user@example.com",
            "#ff00AA",
        ],
        "list": [[], [1], [1, 2, 2, 3], [3, 1, 2], ["b", "a", "c"], [0, -1, 5]],
        "tuple": [(), (1,), (1, 2, 2), (3, 1, 2)],
        "dict": [{}, {"a": 1, "b": 2}],
        "bool": [True, False],
    }

    def __init__(self) -> None:
        self._last_usage = (0, 0)

    # -- prompt parsing ----------------------------------------------------
    @staticmethod
    def _block(prompt: str, name: str) -> str:
        m = re.search(rf"^=== {name} ===\s*\n(.*?)(?=^=== |\Z)", prompt, re.S | re.M)
        return m.group(1).rstrip("\n") if m else ""

    @staticmethod
    def _scalar(prompt: str, name: str, default: int) -> int:
        m = re.search(rf"^=== {name} ===\s*\n(\d+)", prompt, re.M)
        return int(m.group(1)) if m else default

    # -- input synthesis ---------------------------------------------------
    def _kind_of(self, param: dict) -> str:
        ann = (param.get("annotation") or "").lower()
        for kind in ("float", "int", "str", "list", "tuple", "dict", "bool"):
            if kind in ann:
                return kind
        name = param["name"].lower()
        if name in {"text", "s", "name", "line", "email", "color", "value", "sentence", "key"}:
            return "str"
        if name in {"n", "k", "width", "count", "x", "y", "a", "b", "t", "p", "year", "month", "day", "port", "size"}:
            return "int"
        if name in {"xs", "items", "values", "lst", "nested", "data", "rows"}:
            return "list"
        if name in {"flag", "enabled", "strict"}:
            return "bool"
        return "any"

    def _sample(self, kind: str, rng: random.Random, edge: bool) -> object:
        if kind == "any":
            pool = [0, "", [1], True, 1.5, {}, None]
        else:
            pool = self._VALUES[kind]
        if edge:
            pool = pool[: max(2, len(pool) // 3)]
        return rng.choice(pool)

    # -- main entry ----------------------------------------------------------
    def generate(self, system: str, prompt: str, purpose: str = "") -> LLMResponse:
        module_source = self._block(prompt, "MODULE_SOURCE")
        module_name = self._block(prompt, "MODULE_NAME").strip()
        function_name = self._block(prompt, "FUNCTION_NAME").strip()
        count = self._scalar(prompt, "CANDIDATE_COUNT", 1)
        round_no = self._scalar(prompt, "ROUND", 0)
        mutants_block = self._block(prompt, "SURVIVING_MUTANTS")
        mutant_ids = re.findall(r"\[(M\d+)\]", mutants_block)

        # Execute the module in a fresh namespace to probe behavior.
        namespace: dict = {}
        exec(compile(module_source, "<mock-module>", "exec"), namespace)  # noqa: S102
        func = namespace[function_name]

        # Parameter metadata from the FUNCTION block's signature line.
        sig_line = self._block(prompt, "SIGNATURE").strip()
        params = self._parse_params(sig_line)

        seeds_root = f"{function_name}|{round_no}|{'|'.join(mutant_ids)}|{len(module_source)}"
        candidates: list[str] = []
        for j in range(count):
            rng = random.Random(f"{seeds_root}|cand{j}")
            tests: list[str] = []
            combos_per_file = 3
            for i in range(combos_per_file):
                args = {
                    p["name"]: self._sample(self._kind_of(p), rng, edge=round_no > 0)
                    for p in params
                }
                test_code = self._probe(func, function_name, module_name, args)
                if test_code:
                    tests.append(test_code)
            body = "\n\n".join(tests) if tests else (
                f"def test_{function_name}_placeholder():\n"
                f"    assert callable({function_name})\n"
            )
            header = f"import pytest\nfrom {module_name} import {function_name}\n\n\n"
            candidates.append(header + body)

        self._last_usage = (0, 0)
        text = "\n\n".join(
            f"# ==== CANDIDATE {i} ====\n{code}" for i, code in enumerate(candidates)
        )
        return LLMResponse(text=text, model="mock")

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _parse_params(sig_line: str) -> list[dict]:
        m = re.search(r"def \w+\((.*?)\)", sig_line, re.S)
        if not m:
            return []
        raw = m.group(1).strip()
        if not raw:
            return []
        out = []
        for piece in raw.split(","):
            piece = piece.strip()
            if not piece or piece in {"*", "/"} or piece.startswith("*"):
                continue
            name, _, ann = piece.partition(":")
            name = name.split("=")[0].strip()
            ann = ann.split("=")[0].strip() if ann else ""
            out.append({"name": name, "annotation": ann})
        return out

    def _probe(self, func, fname: str, module: str, args: dict) -> str | None:
        call = f"{fname}({', '.join(self._fmt(v) for v in args.values())})"
        try:
            result = func(*args.values())
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, TypeError):
                return None  # wrong shape, not a contract
            if isinstance(exc, (ValueError, KeyError, IndexError, ZeroDivisionError, OverflowError)):
                tag = zlib.crc32(call.encode()) % 10000
                return (
                    f"def test_{fname}_raises_{tag}():\n"
                    f"    with pytest.raises({type(exc).__name__}):\n"
                    f"        {call}\n"
                )
            return None
        repr_result = repr(result) if result is not None else "None"
        if result is None:
            body = f"    assert {call} is None\n"
        elif isinstance(result, bool):
            body = f"    assert {call} is {result}\n"
        else:
            body = f"    assert {call} == {result!r}\n"
        tag = zlib.crc32(f"{call}{repr_result}".encode()) % 100000
        return f"def test_{fname}_{tag}():\n{body}"

    @staticmethod
    def _fmt(v) -> str:
        return repr(v)


def make_client(config: ForgeConfig, project_root: Path) -> OpenAICompatClient | MockLLMClient:
    if config.mode == "mock":
        return MockLLMClient()
    cache_dir = (
        Path(config.cache_dir)
        if config.cache_dir
        else project_root / "llm_cache"
    )
    return OpenAICompatClient(config, cache_dir)
