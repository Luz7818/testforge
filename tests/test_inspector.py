"""Tests for static analysis of target functions."""
from testforge.analysis import inspect_target
from testforge.benchmarks import load_targets


def test_all_manifest_targets_resolve():
    specs = load_targets()
    assert len(specs) == 18
    for spec in specs:
        info = inspect_target(spec)
        assert info.function_source.strip().startswith("def ")
        assert info.signature.startswith(f"def {spec.function_name}(")


def test_signature_includes_annotations():
    spec = [s for s in load_targets() if s.target_id == "numeric.clamp"][0]
    info = inspect_target(spec)
    assert "low: float" in info.signature
    assert "-> float" in info.signature
    assert {p["name"] for p in info.params} == {"value", "low", "high"}


def test_docstring_extracted():
    spec = [s for s in load_targets() if s.target_id == "string_utils.slugify"][0]
    info = inspect_target(spec)
    assert "URL slug" in (info.docstring or "")
