"""The LLM client: prices, the response cache, request settings, and the real-API
code path with a stand-in for the Anthropic client (no network)."""

from types import SimpleNamespace

import pytest

from speccheck import config
from speccheck.llm import LLMClient, LLMResult, cost_of, role_effort


def test_prices_follow_the_price_list():
    assert cost_of("claude-haiku-5-5", 1_000, 2_000) == pytest.approx(0.0011)       # $0.10 in, $0.50 out
    assert cost_of("claude-sonnet-5-5", 1_000_000, 100_000) == pytest.approx(3.0)   # $2 in, $10 out


def test_unknown_model_costs_zero_with_a_warning(capsys):
    assert cost_of("some-other-model", 1_000, 1_000) == 0.0
    assert "no price" in capsys.readouterr().out


def test_configured_models_have_prices():
    assert config.WRITER_MODEL in config.PRICES_PER_MTOK and config.ATTACKER_MODEL in config.PRICES_PER_MTOK


def test_credentials_come_from_the_api_key(monkeypatch):
    from speccheck.llm import has_credentials
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not has_credentials()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert has_credentials()


def test_client_uses_the_configured_timeout_and_retries(monkeypatch):
    import anthropic

    from speccheck.llm import make_anthropic_client
    captured = {}
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: captured.update(kwargs) or "client")
    assert make_anthropic_client() == "client"
    assert captured == {"timeout": config.LLM_TIMEOUT_S, "max_retries": config.LLM_MAX_RETRIES}


def _result(text="ok"):
    return LLMResult(text=text, model="m", model_version="m-1", tokens_in=10, tokens_out=20, tokens_thinking=5,
                     cost_usd=0.001, latency_ms=12.0, stop_reason="end_turn", thinking="adaptive/low")


def test_replay_answers_from_the_saved_reply(tmp_path, monkeypatch):
    client = LLMClient("m", tmp_path, effort="low")
    calls = []
    monkeypatch.setattr(client, "_call", lambda prompt: calls.append(prompt) or _result())
    first = client.complete("hello", tag="a")
    second = client.complete("hello", tag="a")
    assert len(calls) == 1 and not first.cache_hit and second.cache_hit
    assert second.cost_usd == first.cost_usd and second.tokens_out == first.tokens_out
    client.complete("hello", tag="b")
    assert len(calls) == 2   # a different tag is a separate sample


def test_without_replay_every_call_is_fresh_and_overwrites_the_saved_reply(tmp_path, monkeypatch):
    fresh = LLMClient("m", tmp_path, effort="low", replay=False)
    calls = []
    monkeypatch.setattr(fresh, "_call", lambda prompt: calls.append(prompt) or _result(f"v{len(calls)}"))
    fresh.complete("hello", tag="a")
    second = fresh.complete("hello", tag="a")
    assert len(calls) == 2 and not second.cache_hit
    replayed = LLMClient("m", tmp_path, effort="low").complete("hello", tag="a")
    assert replayed.cache_hit and replayed.text == "v2"


def test_each_role_has_its_own_effort_and_cache_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WRITER_THINKING_EFFORT", "low")
    monkeypatch.setattr(config, "ATTACKER_THINKING_EFFORT", "medium")
    writer = LLMClient("m", tmp_path, effort=role_effort("writer"))
    attacker = LLMClient("m", tmp_path, effort=role_effort("attacker"))
    assert writer._request("hi")["output_config"] == {"effort": "low"}
    assert attacker._request("hi")["output_config"] == {"effort": "medium"}
    assert writer._request("hi")["thinking"] == {"type": "adaptive"}
    calls = []
    for client in (writer, attacker):
        monkeypatch.setattr(client, "_call", lambda prompt: calls.append(prompt) or _result())
        client.complete("same prompt", tag="same tag")
    assert len(calls) == 2   # the effort is part of the cache key


def test_unknown_thinking_effort_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        LLMClient("m", tmp_path, effort="minimal")


class StandIn:
    def __init__(self):
        self.requests = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(
            model="claude-test-2026", stop_reason="end_turn",
            content=[SimpleNamespace(type="thinking", thinking="hmm"),
                     SimpleNamespace(type="text", text="```python\ndef pre(a, b):\n    return True\n```")],
            usage=SimpleNamespace(input_tokens=100, output_tokens=300,
                                  output_tokens_details=SimpleNamespace(thinking_tokens=250)))


def test_call_parses_text_usage_and_thinking_tokens(tmp_path):
    client = LLMClient("claude-sonnet-5-5", tmp_path, effort="medium")
    client._client = StandIn()
    result = client.complete("prompt", tag="t")
    assert result.text.startswith("```python")
    assert (result.tokens_in, result.tokens_out, result.tokens_thinking) == (100, 300, 250)
    assert result.model_version == "claude-test-2026" and result.thinking == "adaptive/medium"
    assert result.cost_usd == pytest.approx(cost_of("claude-sonnet-5-5", 100, 300))
    request = client._client.requests[0]
    assert request["thinking"] == {"type": "adaptive"} and request["output_config"] == {"effort": "medium"}
    assert "temperature" not in request and "extra_body" not in request
