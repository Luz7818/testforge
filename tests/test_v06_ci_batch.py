"""Tests for the v0.6 landing shell: PR gate (diff -> targets -> budgeted
runs -> summary), whole-package batch, and first-class Budget caps."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from testforge.budget import Budget
from testforge.diff_targets import changed_functions, parse_diff
from testforge.pr_gate import run_ci

DIFF = textwrap.dedent(
    """\
    diff --git a/mylib/calc.py b/mylib/calc.py
    index 111..222 100644
    --- a/mylib/calc.py
    +++ b/mylib/calc.py
    @@ -1,5 +1,5 @@
     def add(a, b):
         if a == 0:
             return b
    -    total = a + b
    -    return total
    +    total = a + b
    +    return total
     
     def untouched(x):
         return x
    diff --git a/mylib/calc.py.rej b/mylib/calc.py.rej
    deleted file mode 100644
    diff --git a/README.md b/README.md
    --- a/README.md
    +++ b/README.md
    @@ -1 +1 @@
    -old
    +new
    """
)

CALC_SRC = textwrap.dedent(
    """\
    def add(a, b):
        if a == 0:
            return b
        total = a + b
        return total


    def untouched(x):
        return x
    """
)


# -- diff -> target discovery -------------------------------------------------

def test_parse_diff_maps_new_side_lines_and_skips_other_files():
    files = parse_diff(DIFF)
    assert set(files) == {"mylib/calc.py", "README.md"}
    assert files["mylib/calc.py"] == {4, 5}
    assert files["README.md"] == {1}


def test_changed_functions_only_from_python_source_changes():
    root = Path("/fixture")  # not touched: changed_functions resolves lazily
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "is_file", lambda self, _orig=Path.is_file: self.name.endswith("calc.py"))
        mp.setattr(
            Path, "read_text",
            lambda self, *a, **k: CALC_SRC if self.name == "calc.py" else (_ for _ in ()).throw(OSError(self.name)),
        )
        found = changed_functions(DIFF, root)
    assert [f.qualified for f in found] == ["calc.add"]
    assert found[0].changed_lines == {4, 5}


# -- budget -------------------------------------------------------------------

def test_budget_wall_clock_expires():
    import time as _t

    b3 = Budget(sec=0.05)
    assert not b3.exhausted()
    _t.sleep(0.06)
    assert b3.exhausted()
    assert not Budget().exhausted(10**9)  # unlimited budget never expires


# -- ci end-to-end (mock, offline) --------------------------------------------

def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "mylib").mkdir()
    (tmp_path / "mylib" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "mylib" / "calc.py").write_text(CALC_SRC, encoding="utf-8")
    (tmp_path / "mylib" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8"
    )
    (tmp_path / "pr.diff").write_text(DIFF, encoding="utf-8")
    return tmp_path


def test_ci_runs_changed_targets_and_writes_summary(tmp_path, capsys):
    root = _make_repo(tmp_path)
    import argparse

    ns = argparse.Namespace(
        diff=str(tmp_path / "pr.diff"), base_ref="main", root=str(root),
        mode="mock", variant="B3", max_functions=5,
        budget_sec=0.0, budget_tokens=0, out=str(tmp_path / "ci_out"),
    )
    rc = run_ci(ns)
    assert rc == 0
    summary = (tmp_path / "ci_out" / "summary.md").read_text(encoding="utf-8")
    assert "mylib/calc.py::add" in summary
    assert "Suggested tests" in summary
    results = json.loads((tmp_path / "ci_out" / "results.json").read_text(encoding="utf-8"))
    assert results[0]["target_id"] == "mylib/calc.py::add"
    assert results[0]["final_suite_passes"] is True


def test_ci_with_zero_matched_functions_is_green(tmp_path):
    root = _make_repo(tmp_path)
    (tmp_path / "empty.diff").write_text(
        "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-x\n+y\n",
        encoding="utf-8",
    )
    import argparse

    ns = argparse.Namespace(
        diff=str(tmp_path / "empty.diff"), base_ref="main", root=str(root),
        mode="mock", variant="B3", max_functions=5,
        budget_sec=0.0, budget_tokens=0, out=str(tmp_path / "ci_out2"),
    )
    assert run_ci(ns) == 0
    assert (tmp_path / "ci_out2").is_dir()


def test_ci_budget_stops_generation_but_keeps_score(tmp_path):
    root = _make_repo(tmp_path)
    (tmp_path / "pr.diff").write_text(DIFF, encoding="utf-8")
    import argparse

    ns = argparse.Namespace(
        diff=str(tmp_path / "pr.diff"), base_ref="main", root=str(root),
        mode="mock", variant="B3", max_functions=5,
        budget_sec=0.01, budget_tokens=0,  # expires before round 0: baseline setup already exceeds it
        out=str(tmp_path / "ci_out3"),
    )
    assert run_ci(ns) == 0  # budget exhaustion is not an infra error
    results = json.loads((tmp_path / "ci_out3" / "results.json").read_text(encoding="utf-8"))
    assert results[0]["budget_exceeded"] is True
    assert "ms_all" in results[0]  # final joint evaluation still produced a score


# -- batch --------------------------------------------------------------------

from testforge.batch import discover_targets, run_batch  # noqa: E402


def _make_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "public.py").write_text(
        textwrap.dedent(
            """\
            def alpha(x):
                return x + 1


            def _private(x):
                return x


            def beta(x):
                return x * 2
            """
        ),
        encoding="utf-8",
    )
    (pkg / "sub" / "deep.py").write_text("def gamma(y):\n    return y - 1\n", encoding="utf-8")
    (pkg / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "test_public.py").write_text("def test_alpha():\n    pass\n", encoding="utf-8")
    (pkg / "public.py.bak").write_text("def nope():\n    return 1\n", encoding="utf-8")
    return pkg


def test_batch_discovery_orders_by_existing_coverage_then_name(tmp_path):
    pkg = _make_package(tmp_path)
    specs = discover_targets(pkg)
    ids = [s.target_id for s in specs]
    # no-tests first (deep.gamma), then fewer-tests (beta has 0 test fns via test_public? alpha has 1)
    assert ids[0] == "deep.gamma"
    assert "public.alpha" in ids and "public.beta" in ids
    assert all(not s.target_id.startswith("_") for s in specs)
    alpha = next(s for s in specs if s.target_id == "public.alpha")
    assert alpha.existing_test_path is not None  # test_public.py found next to the module


def test_batch_run_produces_results_and_summary(tmp_path, capsys):
    pkg = _make_package(tmp_path)
    import argparse

    ns = argparse.Namespace(
        package=str(pkg), mode="mock", variant="B3", max_functions=3,
        budget_sec=0.0, budget_tokens=0, out=str(tmp_path / "batch_out"),
    )
    assert run_batch(ns) == 0
    results = json.loads((tmp_path / "batch_out" / "results.json").read_text(encoding="utf-8"))
    assert all("ms_all" in r for r in results)
    summary = (tmp_path / "batch_out" / "batch-summary.md").read_text(encoding="utf-8")
    assert "Mean MS(all)" in summary
