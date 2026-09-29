"""Tests for the named grid presets that pin the published parameters.

The three published 90-cell grids were run at 16 mutants / 3 candidates /
2 rounds / gate reruns x3 — not the code defaults. Reproducing them must not
require remembering prose from AGENTS.md, so the numbers are pinned in code
and tested here.
"""

from __future__ import annotations

import pytest

from testforge.config import ForgeConfig
from testforge.presets import PRESETS, PRESET_FINGERPRINTS, apply_preset


def test_published_preset_pins_documented_parameters():
    assert PRESETS["published"] == {
        "max_mutants": 16,
        "candidates_per_round": 3,
        "max_rounds": 2,
        "flaky_runs": 3,
    }


def test_published_b5_preset_pins_b5_grid_parameters():
    assert PRESETS["published-b5"] == {
        "max_mutants": 24,
        "candidates_per_round": 4,
        "max_rounds": 4,
        "flaky_runs": 5,
    }


def test_fingerprints_match_preset_arithmetic():
    # max(n_generated) in an archived grid == candidates x rounds
    for name, fp in PRESET_FINGERPRINTS.items():
        p = PRESETS[name]
        assert fp["n_generated"] == p["candidates_per_round"] * p["max_rounds"]


def test_apply_preset_overwrites_config_fields():
    cfg = ForgeConfig()
    apply_preset(cfg, "published")
    assert cfg.max_mutants == 16
    assert cfg.candidates_per_round == 3
    assert cfg.max_rounds == 2
    assert cfg.flaky_runs == 3


def test_unknown_preset_exits_with_choices():
    with pytest.raises(SystemExit):
        apply_preset(ForgeConfig(), "nope")


def _runner_module():
    import importlib.util

    from testforge import config as cfg

    path = cfg.PROJECT_ROOT / "experiments" / "run_experiment.py"
    spec = importlib.util.spec_from_file_location("run_experiment", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _args(**kw):
    import argparse

    base = dict(mode=None, preset=None, max_mutants=None, candidates=None,
                rounds=None, flaky_runs=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_resolve_params_defaults_without_preset():
    mod = _runner_module()
    assert mod.resolve_params(_args()) == {
        "max_mutants": 24, "candidates": 4, "rounds": 3, "flaky_runs": 5,
    }


def test_resolve_params_published_preset_matches_archive():
    mod = _runner_module()
    assert mod.resolve_params(_args(preset="published")) == {
        "max_mutants": 16, "candidates": 3, "rounds": 2, "flaky_runs": 3,
    }


def test_resolve_params_flag_beats_preset_beats_default():
    mod = _runner_module()
    out = mod.resolve_params(_args(preset="published", candidates=8))
    assert out["candidates"] == 8
    assert out["max_mutants"] == 16
