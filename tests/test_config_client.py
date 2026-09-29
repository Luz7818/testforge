"""Tests for config extra-body handling and reasoning-output stripping."""
import json

import pytest

from testforge.config import ForgeConfig
from testforge.llm.client import strip_think


def test_extra_body_empty_by_default():
    assert ForgeConfig().extra_body_dict() == {}


def test_extra_body_parses_json_object():
    cfg = ForgeConfig(extra_body='{"enable_thinking": false}')
    assert cfg.extra_body_dict() == {"enable_thinking": False}


def test_extra_body_rejects_non_object():
    with pytest.raises(ValueError):
        ForgeConfig(extra_body="[1, 2]").extra_body_dict()


def test_extra_body_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        ForgeConfig(extra_body="{not json").extra_body_dict()


def test_strip_think_removes_reasoning_block():
    text = "<think>I should write tests...</think>\n# ==== CANDIDATE 0 ====\nimport pytest\n"
    assert strip_think(text).startswith("# ==== CANDIDATE 0 ====")


def test_strip_think_passes_plain_text_through():
    assert strip_think("# ==== CANDIDATE 0 ====\nimport pytest\n") == (
        "# ==== CANDIDATE 0 ====\nimport pytest\n"
    )


def test_from_env_respects_testforge_mode(monkeypatch):
    # 0.2: --mode is None unless passed explicitly, so the env var works as
    # the default for both the CLI and the experiment runner.
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("TESTFORGE_MODE", "mock")
    assert ForgeConfig.from_env(None).mode == "mock"


def test_testforge_mode_api_without_key_still_stops_before_network(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("TESTFORGE_MODE", "api")
    with pytest.raises(SystemExit):
        ForgeConfig.from_env(None)
