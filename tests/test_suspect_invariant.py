"""TF-01 invariant: kills with zero target coverage are suspect.

2026-10-21 code review (.workbuddy) found that running pytest and a mock
cell concurrently on one machine can pollute a cell into a fake perfect
score: gen=0 / acc=0 / coverage 0% yet killed_final=21/21 and ms_all=1.0,
because Outcome.killed_mutant counts ERROR/TIMEOUT as kills. A mutant can
only be killed by a run that executes its mutated line, so killed>0 with
0% coverage is the pollution signature; such a result is flagged suspect
and the report renderer warns instead of silently trusting the score.
"""

from testforge.benchmarks import result_to_dict
from testforge.report.renderer import render_summary, render_target_report
from testforge.types import VariantResult


def make_polluted():
    """The observed pollution signature: full score, nothing generated,
    zero coverage."""
    return VariantResult(
        target_id="string_utils.slugify",
        variant="B3",
        mutants_total=21,
        killed_final=21,
        n_generated=0,
        n_accepted=0,
        final_suite_passes=True,
        coverage_pct=0.0,
    )


def test_polluted_full_score_is_flagged_and_warns():
    res = make_polluted()
    assert res.ms_all == 1.0
    assert res.is_suspect
    report = render_target_report(res)
    assert "SUSPECT" in report
    assert "Re-run serially" in report
    assert result_to_dict(res)["suspect"] is True
    assert "slugify (SUSPECT)" in render_summary([res])


def test_legitimate_full_kill_with_coverage_is_not_flagged():
    # Strong existing tests can legitimately kill everything in a B0-only
    # run; the discriminator is that the suite covered the target.
    res = VariantResult(
        target_id="t",
        variant="B1",
        mutants_total=21,
        killed_final=21,
        coverage_pct=85.0,
    )
    assert not res.is_suspect
    assert "SUSPECT" not in render_target_report(res)


def test_ordinary_and_empty_results_are_not_flagged():
    assert not VariantResult(target_id="t", variant="B3").is_suspect  # no mutants
    res = VariantResult(
        target_id="t",
        variant="B3",
        mutants_total=21,
        killed_final=3,
        coverage_pct=40.0,
    )
    assert not res.is_suspect
    assert "SUSPECT" not in render_target_report(res)
    assert "(SUSPECT)" not in render_summary([res])
