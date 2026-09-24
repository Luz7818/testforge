"""Experimental conditions shared by the CLI and the experiment runner.

- B0: existing test suite only (baseline, no generation).
- B1: "vibe testing" — single-shot generation, no gate, no feedback.
- B2: single-shot generation + quality gate (no feedback loop).
- B3: full TestForge — gate + mutation-survivor feedback loop (ours).
- B4: ablation — gate + *coverage-gap* feedback instead of mutant feedback.
- B5: B3 without early exit — feedback keeps being re-injected until the round
  budget is spent even when a round accepts nothing.
"""

from __future__ import annotations

from .types import VariantSpec

VARIANTS: dict[str, VariantSpec] = {
    "B0": VariantSpec(name="B0", rounds=0, gate_enabled=False, feedback_mode="none"),
    "B1": VariantSpec(name="B1", rounds=1, gate_enabled=False, feedback_mode="none"),
    "B2": VariantSpec(name="B2", rounds=1, gate_enabled=True, feedback_mode="none"),
    "B3": VariantSpec(name="B3", rounds=3, gate_enabled=True, feedback_mode="mutants"),
    "B4": VariantSpec(name="B4", rounds=3, gate_enabled=True, feedback_mode="coverage"),
    "B5": VariantSpec(
        name="B5",
        rounds=4,
        gate_enabled=True,
        feedback_mode="mutants",
        continue_on_zero_accept=True,
    ),
}


def get_variant(name: str) -> VariantSpec:
    try:
        return VARIANTS[name]
    except KeyError:
        raise SystemExit(f"unknown variant {name!r}; choose from {sorted(VARIANTS)}") from None
