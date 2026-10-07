"""Cost-accounting honesty.

v0.1 multiplied exact token counts by hard-coded placeholder unit prices and
reported the product to four decimal places — a seemingly-exact wrong number.
The contract now is:

  * token counts are always exact;
  * a USD figure exists only when a price was explicitly configured, and the
    price's source travels with the results (`price_source`);
  * no price configured -> `cost_usd` is None, and reports render "n/a",
    never a silent $0.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from testforge import config as cfg
from testforge.llm.client import OpenAICompatClient
from testforge.report.renderer import render_summary
from testforge.types import CostLedger, VariantResult

MANAGED = (
    "DEEPSEEK_API_KEY",
    "TESTFORGE_MODEL",
    "TESTFORGE_PRICE_INPUT_PER_M",
    "TESTFORGE_PRICE_OUTPUT_PER_M",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in MANAGED:
        monkeypatch.delenv(key, raising=False)


def test_ledger_without_price_reports_none_and_keeps_tokens_exact():
    led = CostLedger(model="m")
    led.add("a", 10, 5, None)
    led.add("b", 7, 3, None)
    s = led.summary()
    assert s["cost_usd"] is None
    assert s["tokens_in"] == 17 and s["tokens_out"] == 8
    assert s["price_source"] == ""


def test_ledger_with_price_sums_and_records_source():
    led = CostLedger(model="m", price_source="pricing.json: example")
    led.add("a", 1_000_000, 1_000_000, 0.5)
    s = led.summary()
    assert s["cost_usd"] == 0.5
    assert s["price_source"] == "pricing.json: example"


def test_default_config_has_no_placeholder_price():
    c = cfg.ForgeConfig()
    assert c.price_input_per_m is None
    assert c.price_output_per_m is None
    assert c.price_source == ""


def test_env_price_override_sets_provenance(monkeypatch):
    monkeypatch.setenv("TESTFORGE_PRICE_INPUT_PER_M", "0.5")
    monkeypatch.setenv("TESTFORGE_PRICE_OUTPUT_PER_M", "2.0")
    c = cfg.ForgeConfig.from_env()
    assert c.price_input_per_m == 0.5
    assert c.price_output_per_m == 2.0
    assert c.price_source == "TESTFORGE_PRICE_* env override"


def test_pricing_table_entry_sets_provenance(tmp_path, monkeypatch):
    (tmp_path / "pricing.json").write_text(
        json.dumps(
            {
                "prices": [
                    {
                        "model": "test-model",
                        "input_per_m": 1.0,
                        "output_per_m": 2.0,
                        "source": "unit-test",
                        "effective": "2026-01-01",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "PRICING_FILE", tmp_path / "pricing.json")
    monkeypatch.setenv("TESTFORGE_MODEL", "test-model")
    c = cfg.ForgeConfig.from_env()
    assert c.price_input_per_m == 1.0
    assert c.price_output_per_m == 2.0
    assert "unit-test" in c.price_source
    assert "2026-01-01" in c.price_source


def test_pricing_table_without_matching_entry_stays_unpriced(tmp_path, monkeypatch):
    (tmp_path / "pricing.json").write_text(json.dumps({"prices": []}), encoding="utf-8")
    monkeypatch.setattr(cfg, "PRICING_FILE", tmp_path / "pricing.json")
    c = cfg.ForgeConfig.from_env()
    assert c.price_input_per_m is None
    assert c.price_source == ""


def test_repo_pricing_json_is_valid_and_ships_unpriced():
    # The committed pricing.json is the schema documentation; it must parse and
    # must not silently reintroduce a price without provenance.
    data = json.loads(cfg.PRICING_FILE.read_text(encoding="utf-8"))
    for entry in data["prices"]:
        assert {"model", "input_per_m", "output_per_m", "source", "effective"} <= set(entry)


def test_env_retry_hook_overrides_llm_retries(monkeypatch):
    monkeypatch.delenv("TESTFORGE_LLM_RETRIES", raising=False)
    assert cfg.ForgeConfig.from_env().llm_retries == 3
    monkeypatch.setenv("TESTFORGE_LLM_RETRIES", "5")
    assert cfg.ForgeConfig.from_env().llm_retries == 5


def test_client_cost_is_none_without_price():
    c = SimpleNamespace(_cfg=cfg.ForgeConfig())
    assert OpenAICompatClient._cost(c, 1000, 2000) is None


def test_client_cost_computes_from_exact_tokens():
    c = SimpleNamespace(_cfg=cfg.ForgeConfig(price_input_per_m=1.0, price_output_per_m=2.0))
    assert OpenAICompatClient._cost(c, 1_000_000, 1_000_000) == pytest.approx(3.0)


def test_summary_table_shows_na_for_unpriced_rows():
    md = render_summary([VariantResult(target_id="t", variant="B1")])
    assert "n/a" in md
    assert "nan" not in md


def test_result_defaults_are_unpriced():
    r = VariantResult(target_id="t", variant="B1")
    assert r.cost_usd is None
    assert r.price_source == ""


def test_cache_key_changes_with_extra_body(tmp_path):
    """extra_body can flip provider-side behavior (Qwen3 thinking mode), so a
    different extra_body must never replay another setting's cached response."""
    from testforge.llm.client import OpenAICompatClient

    cache = tmp_path / "cache"
    a = SimpleNamespace(_cfg=cfg.ForgeConfig(extra_body=""), _cache_dir=cache)
    b = SimpleNamespace(_cfg=cfg.ForgeConfig(extra_body='{"enable_thinking": false}'),
                        _cache_dir=cache)
    pa = OpenAICompatClient._cache_path(a, "sys", "prompt")
    pb = OpenAICompatClient._cache_path(b, "sys", "prompt")
    assert pa != pb


def test_pace_sleeps_when_interval_not_elapsed(monkeypatch):
    import testforge.llm.client as client_mod

    monkeypatch.setenv("TESTFORGE_MIN_CALL_INTERVAL_SEC", "5")
    slept = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(client_mod.time, "monotonic", lambda: 100.0)
    client_mod._last_real_call_monotonic = 98.0  # last call 2s ago, interval 5s
    OpenAICompatClient._pace(object())
    assert slept and slept[0] == pytest.approx(3.0)
    # A zero/absent interval never sleeps.
    monkeypatch.delenv("TESTFORGE_MIN_CALL_INTERVAL_SEC")
    slept.clear()
    OpenAICompatClient._pace(object())
    assert slept == []


def test_urllib_transport_parses_wire_format(monkeypatch, tmp_path):
    """TESTFORGE_TRANSPORT=urllib must speak the same chat-completions wire
    format and produce the same response shape the SDK path provides."""
    import testforge.llm.client as client_mod

    monkeypatch.setenv("TESTFORGE_TRANSPORT", "urllib")
    cfgx = cfg.ForgeConfig(mode="api", api_key="k", api_base="https://gw.example/v1")
    client = client_mod.OpenAICompatClient(cfgx, tmp_path / "cache")

    captured = {}

    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["ua"] = req.headers.get("User-agent")
        return _FakeResp(json.dumps({
            "choices": [{"message": {"content": "# ==== CANDIDATE 0 ====\nimport pytest\n"},
                          "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }).encode())

    monkeypatch.setattr(client_mod.urllib.request, "urlopen", fake_urlopen)
    resp = client.generate("sys", "prompt", purpose="t")
    assert resp.text.startswith("# ==== CANDIDATE 0 ====")
    assert resp.tokens_in == 11 and resp.tokens_out == 7
    assert resp.cost_usd is None and resp.cached is False
    assert captured["url"] == "https://gw.example/v1/chat/completions"
    assert "chat_template_kwargs" not in captured["body"]  # empty extra_body -> absent
    assert captured["ua"].startswith("testforge/")


def test_urllib_transport_raises_on_http_error(monkeypatch, tmp_path):
    import urllib.error

    import testforge.llm.client as client_mod

    monkeypatch.setenv("TESTFORGE_TRANSPORT", "urllib")
    cfgx = cfg.ForgeConfig(mode="api", api_key="k", api_base="https://gw.example/v1", llm_retries=1)
    client = client_mod.OpenAICompatClient(cfgx, tmp_path / "cache")

    def fake_urlopen(req, timeout):
        import io
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", hdrs=None,
                                     fp=io.BytesIO(b"<html>denied</html>"))

    monkeypatch.setattr(client_mod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="HTTP 403"):
        client.generate("sys", "prompt", purpose="t")
