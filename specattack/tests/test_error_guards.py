"""Unexpected errors while checking must be recorded, not stop an experiment."""

import benchmarks
from experiments import exp1_first_specs
from experiments.common import NullLogger
from fixtures import sample_specs
from speccheck import attacker as attacker_module
from speccheck.checks import check_spec
from speccheck.llm import FakeLLM
from speccheck.loader import load_spec


def test_check_error_becomes_format_failure(monkeypatch):
    def broken(task, spec):
        raise ValueError("boom")

    monkeypatch.setattr("speccheck.checks.check_spec", broken)
    task = benchmarks.get("min2")
    writer = FakeLLM(lambda prompt, tag: sample_specs.fenced(sample_specs.CORRECT["min2"]))
    logger = NullLogger()
    record, attack_record = exp1_first_specs.run_first_spec(task, 0, writer, None, logger)
    assert record["format_ok"] is False and "boom" in record["format_reason"]
    assert record["labels"] == ["did not follow the format"] and attack_record is None


def test_program_check_error_is_a_rejected_attempt(monkeypatch):
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    example = check_spec(task, spec)["checks"]["weak"]["example"]
    calls = {"n": 0}
    real = attacker_module.check_program

    def flaky(task_, spec_, term):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("odd program")
        return real(task_, spec_, term)

    monkeypatch.setattr(attacker_module, "check_program", flaky)
    llm = FakeLLM(lambda prompt, tag: sample_specs.PROGRAM_RETURN_LO)
    record = attacker_module.attack(task, spec, spec.code, example, llm, "t", "test", "a", "s")
    assert record["attempts"][0]["rejected_reason"] == "did not follow the format"
    assert "odd program" in record["attempts"][0]["format_reason"]
    assert record["success"] and record["attempts_used"] == 2
