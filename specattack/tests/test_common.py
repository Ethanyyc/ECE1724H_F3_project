import pytest

from experiments.common import Progress, clients, format_duration, parser
from speccheck import config
from speccheck.llm import LLMClient


def _clear(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_missing_credentials_stop_with_a_short_message(monkeypatch, tmp_path):
    _clear(monkeypatch)
    args = parser("t").parse_args(["--results-dir", str(tmp_path)])
    with pytest.raises(SystemExit) as stop:
        clients(args)
    assert "No API credentials" in str(stop.value)


def test_api_key_is_enough(monkeypatch, tmp_path):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    args = parser("t").parse_args(["--results-dir", str(tmp_path)])
    writer, attacker = clients(args)
    assert isinstance(writer, LLMClient) and isinstance(attacker, LLMClient)


def test_clients_use_each_role_model_and_effort(monkeypatch, tmp_path):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    writer, attacker = clients(parser("t").parse_args(["--results-dir", str(tmp_path)]))
    assert writer.model == config.WRITER_MODEL and writer.effort == config.WRITER_THINKING_EFFORT
    assert attacker.model == config.ATTACKER_MODEL and attacker.effort == config.ATTACKER_THINKING_EFFORT


def test_saved_replies_are_reused_unless_fresh_is_asked_for(monkeypatch, tmp_path):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    writer, attacker = clients(parser("t").parse_args(["--results-dir", str(tmp_path)]))
    assert writer.replay is True and attacker.replay is True
    writer, attacker = clients(parser("t").parse_args(["--results-dir", str(tmp_path), "--fresh"]))
    assert writer.replay is False and attacker.replay is False


def test_progress_counts_items_and_reports_the_duration(capsys):
    progress = Progress("Exp 1", 50)
    progress.item("trunc_div3-r0: correct")
    progress.finish()
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "[ 1/50]   2% trunc_div3-r0: correct"
    assert lines[1].startswith("Exp 1: done in ")


def test_format_duration():
    assert format_duration(42.4) == "42 s"
    assert format_duration(152) == "2 min 32 s"
