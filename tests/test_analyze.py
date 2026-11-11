"""Smoke test for experiments/analyze.py on a minimal grid.

TF4-1: commit 290592f changed agg["ms_all"] from a one-element list to a
scalar but missed the markdown aggregate-table consumer at analyze.py:252,
which still subscripted it with [0] — every non-empty grid crashed with
"TypeError: 'float' object is not subscriptable" and REPRODUCE.md Step 4
became unusable. tests/ had zero analyze coverage, so all three gates
stayed green while the analysis chain was broken. This file pins the
minimal non-empty grid path: analyze() must run, render the aggregate
table from scalar means, and emit analysis.md/analysis.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.analyze import analyze  # noqa: E402


def cell(target: str, variant: str, ms_all: float, n_accepted: int = 0) -> dict:
    """One grid cell in the result_payload shape written by the runner."""
    return {
        "target_id": target,
        "variant": variant,
        "ms_all": ms_all,
        "ms_covered": round(ms_all + 0.05, 4),
        "coverage_pct": 90.0,
        "n_generated": 3,
        "n_accepted": n_accepted,
        "rejection_reasons": {},
        "cost": {"model": "mock", "calls": 1, "tokens_in": 100,
                 "tokens_out": 50, "cost_usd": None, "price_source": ""},
    }


def minimal_grid() -> list[dict]:
    """2 targets x 2 variants — the smallest grid that reaches the
    aggregate table (the path that crashed in TF4-1)."""
    rows = []
    for t in ("t_alpha", "t_beta"):
        rows.append(cell(t, "B0", 0.60))
        rows.append(cell(t, "B1", 0.90, n_accepted=2))
    return rows


def test_analyze_minimal_grid_smoke(tmp_path):
    analyze(minimal_grid(), tmp_path)

    md = (tmp_path / "analysis.md").read_text(encoding="utf-8")
    # Aggregate row renders the scalar mean, not a crash (TF4-1: B0 0.60).
    assert "| B0 | 60.0% | 60.0% | 65.0% | 90.0 | 0.00 | — |" in md
    assert "| B1 | 90.0% | 90.0% | 95.0% | 90.0 | 2.00 | — |" in md
    # RQ block present for the B1-B0 pairing.
    assert "### RQ1:" in md

    agg = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))["aggregate"]
    assert agg["B0"]["ms_all"] == 0.6          # scalar, per the 290592f contract
    assert agg["B1"]["ms_all"] == 0.9
    assert agg["B1"]["acc"] == 2.0


def test_analyze_empty_error_grid_smoke(tmp_path):
    """All-errored grid: no variants -> aggregate table has no rows, and the
    error table is rendered instead. Must not raise."""
    rows = [{"target_id": "t_x", "variant": "B0", "error": "boom"}]
    analyze(rows, tmp_path)
    md = (tmp_path / "analysis.md").read_text(encoding="utf-8")
    assert "| t_x | B0 | boom |" in md
    assert "0 targets x 0 variants" in md
