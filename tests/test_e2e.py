"""End-to-end pipeline test (mock mode, reduced settings) on one target."""
from testforge.agent import ForgeAgent
from testforge.benchmarks import PROJECT_ROOT, load_targets
from testforge.config import ForgeConfig
from testforge.llm import make_client
from testforge.types import CostLedger
from testforge.variants import VARIANTS


def _run(spec, variant_name):
    cfg = ForgeConfig.from_env(mode="mock")
    cfg.candidates_per_round = 3
    cfg.max_rounds = 3
    cfg.max_mutants = 10
    cfg.flaky_runs = 2
    cfg.test_timeout_sec = 10.0
    cfg.workers = 4
    client = make_client(cfg, PROJECT_ROOT)
    ledger = CostLedger(model=cfg.model)
    res = ForgeAgent(cfg, client, ledger).run_target(spec, VARIANTS[variant_name])
    return res, ledger


def test_b3_full_pipeline_improves_or_maintains_ms():
    spec = [s for s in load_targets() if s.target_id == "string_utils.truncate_with_ellipsis"][0]
    b0, _ = _run(spec, "B0")
    b3, ledger = _run(spec, "B3")
    # the loop ran, the final suite passes, and mutation score did not drop
    assert b0.mutants_total == b3.mutants_total > 0
    assert b3.final_suite_passes
    assert b3.n_generated > 0
    assert b3.ms_all >= b0.ms_all
    assert ledger.n_calls >= 1
