"""Named grid parameter sets, so published numbers are reproducible without
remembering flags.

The published 90-cell grids (``results/exp_api27b_full`` /
``exp_api27b_replicate`` for the real model, ``exp_mock_full`` for the offline
mock) were run with 16 mutants per target, 3 candidates per round, 2 feedback
rounds and gate reruns x3 — NOT with the code defaults (24/4/3, reruns x5).
``--preset published`` pins those values; the archived fingerprints to check a
reproduction against are ``max(mutants_total) == 16``,
``max(n_generated) == 6`` and ``max(rounds_used) == 2``.

The B5 grids (``results/exp_api27b_rq2full`` / ``exp_api27b_rq2full_rep``) used
24 mutants, 4 candidates per round and the B5 round budget of 4: fingerprints
``max(mutants_total) == 24``, ``max(n_generated) == 16``,
``max(rounds_used) == 4``.

Precedence in the runners: explicit flag > preset value > dataclass default.
"""

from __future__ import annotations

PRESETS: dict[str, dict[str, int]] = {
    "published": {
        "max_mutants": 16,
        "candidates_per_round": 3,
        "max_rounds": 2,
        "flaky_runs": 3,
    },
    "published-b5": {
        "max_mutants": 24,
        "candidates_per_round": 4,
        "max_rounds": 4,
        "flaky_runs": 5,
    },
}

PRESET_FINGERPRINTS: dict[str, dict[str, int]] = {
    "published": {"mutants_total": 16, "n_generated": 6, "rounds_used": 2},
    "published-b5": {"mutants_total": 24, "n_generated": 16, "rounds_used": 4},
}
