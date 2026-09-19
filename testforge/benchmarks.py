"""Benchmark manifest loading."""

from __future__ import annotations

import json
from pathlib import Path

from .types import TargetSpec

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = PROJECT_ROOT / "benchmarks"


def load_targets() -> list[TargetSpec]:
    manifest = json.loads((BENCH_DIR / "manifest.json").read_text(encoding="utf-8"))
    specs = []
    for entry in manifest["targets"]:
        specs.append(
            TargetSpec(
                target_id=entry["id"],
                module_path=str(BENCH_DIR / "targets" / f"{entry['module']}.py"),
                module_name=entry["module"],
                function_name=entry["function"],
                existing_test_path=str(BENCH_DIR / "existing_tests" / f"test_{entry['module']}.py"),
            )
        )
    return specs


def get_target(target_id: str) -> TargetSpec:
    for spec in load_targets():
        if spec.target_id == target_id:
            return spec
    raise SystemExit(f"unknown target {target_id!r}; run `python -m testforge.cli targets`")


def result_to_dict(res) -> dict:
    """Serialize a VariantResult, materializing its computed properties."""
    from dataclasses import asdict

    data = asdict(res)
    data["ms_all"] = round(res.ms_all, 4)
    data["ms_covered"] = round(res.ms_covered, 4)
    return data
