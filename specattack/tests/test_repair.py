import pytest

import benchmarks
from fixtures import sample_specs
from experiments.common import NullLogger
from speccheck import repair as repair_module
from speccheck.checks import check_spec
from speccheck.llm import FakeLLM
from speccheck.loader import load_spec
from speccheck.repair import run_repair

CORRECT_CLAMP = sample_specs.fenced(sample_specs.CORRECT["clamp"])
WEAK_CLAMP = sample_specs.fenced(sample_specs.ATTACK_CLAMP_WEAK)


def _start():
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    check = check_spec(task, spec)
    return task, {"spec_id": "clamp-r0", "repeat": 0, "code": spec.code, "checks": check["checks"],
                  "labels": check["labels"]}


def test_invalid_reply_uses_a_round_and_keeps_last_valid_spec():
    task, start = _start()
    writer = FakeLLM(lambda prompt, tag: "nothing" if tag.endswith(":k1") else CORRECT_CLAMP)
    logger = NullLogger()
    record = run_repair(task, start, 2, writer, None, logger)
    assert record["outcome"] == "correct" and record["rounds_to_correct"] == 2
    assert record["rounds"][0]["reply_format_ok"] is False
    assert record["rounds"][0]["labels"] == ["did not follow the format"]
    assert "lo <= r" in writer.calls[1][1] and "did not follow the required format" in writer.calls[1][1]
    revised = [r for kind, r in logger.records if kind == "spec"]
    assert [r["spec_id"] for r in revised] == ["clamp-r0:t2:k1", "clamp-r0:t2:k2"]
    assert revised[1]["parent_spec_id"] == "clamp-r0"


def test_incorrect_after_all_rounds_checks_the_last_revision():
    task, start = _start()
    writer = FakeLLM(lambda prompt, tag: WEAK_CLAMP)
    record = run_repair(task, start, 2, writer, None, NullLogger())
    assert record["outcome"] == "incorrect" and record["rounds_used"] == 3
    assert record["rounds"][-1]["labels"] == ["too weak"]
    assert record["final_labels"] == ["too weak"]


def test_type1_gives_pass_fail_only():
    task, start = _start()
    writer = FakeLLM(lambda prompt, tag: WEAK_CLAMP)
    run_repair(task, start, 1, writer, None, NullLogger())
    assert all("Your spec is wrong." in prompt and "intended output" not in prompt for _, prompt, _ in writer.calls)


def test_type3_uses_program_reuses_exp1_attack_and_attacks_later_rounds():
    task, start = _start()
    writer = FakeLLM(lambda prompt, tag: WEAK_CLAMP)
    attacker = FakeLLM(lambda prompt, tag: sample_specs.PROGRAM_RETURN_LO)
    logger = NullLogger()
    exp1_attack = {"attack_id": "clamp-r0:attack", "success": True, "program_code": "def prog(lo, hi, x):\n    return hi\n"}
    record = run_repair(task, start, 3, writer, attacker, logger, start_attack=exp1_attack)
    assert "return hi" in writer.calls[0][1] and "intended output" not in writer.calls[0][1]
    assert record["rounds"][0]["attack_id"] == "clamp-r0:attack"
    attacks = [r for kind, r in logger.records if kind == "attack"]
    assert len(attacks) == 2   # rounds 2 and 3; none after the last round
    assert [a["context"] for a in attacks] == ["repair_t3_round_2", "repair_t3_round_3"]
    assert "return lo" in writer.calls[1][1]
    assert record["cost_usd"] > 0


def test_type3_falls_back_when_attack_failed():
    task, start = _start()
    writer = FakeLLM(lambda prompt, tag: CORRECT_CLAMP)
    record = run_repair(task, start, 3, writer, None, NullLogger(),
                        start_attack={"attack_id": "x", "success": False, "program_code": None})
    assert record["rounds"][0]["fell_back_to_example"] is True
    assert "intended output" in writer.calls[0][1]


def test_undetermined_revision_stops_the_loop(monkeypatch):
    task, start = _start()
    real = repair_module.try_check_spec

    def fake_check(task_, spec_):
        result, error = real(task_, spec_)
        result["labels"] = ["undetermined"]
        return result, error

    monkeypatch.setattr(repair_module, "try_check_spec", fake_check)
    writer = FakeLLM(lambda prompt, tag: WEAK_CLAMP)
    record = run_repair(task, start, 2, writer, None, NullLogger())
    assert record["outcome"] == "undetermined" and record["rounds_used"] == 1


def test_start_spec_must_be_too_weak():
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.CORRECT["clamp"], task, is_reply=False)
    check = check_spec(task, spec)
    start = {"spec_id": "s", "repeat": 0, "code": spec.code, "checks": check["checks"], "labels": check["labels"]}
    with pytest.raises(ValueError):
        run_repair(task, start, 2, FakeLLM(lambda p, t: CORRECT_CLAMP), None, NullLogger())
