import benchmarks
from fixtures import sample_specs
from speccheck.attacker import attack
from speccheck.checks import check_spec
from speccheck.llm import FakeLLM
from speccheck.loader import load_spec


def _setup():
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    example = check_spec(task, spec)["checks"]["weak"]["example"]
    return task, spec, example


def _scripted(replies):
    return FakeLLM(lambda prompt, tag: replies[int(tag.rsplit("attempt", 1)[1]) - 1])


def test_attack_succeeds_on_third_attempt_with_reasons():
    task, spec, example = _setup()
    llm = _scripted([sample_specs.PROGRAM_RETURN_X, sample_specs.PROGRAM_GOLDEN_CLAMP, sample_specs.PROGRAM_RETURN_LO])
    record = attack(task, spec, spec.code, example, llm, "t:clamp:attack", "test", "a1", "s1")
    assert record["success"] and record["attempts_used"] == 3
    assert [a["rejected_reason"] for a in record["attempts"]] == ["did not pass the spec", "was actually correct", None]
    assert record["program_size"] >= 1 and record["source_size"] > 0
    assert record["witness"]["output"] != record["witness"]["intended"]
    third_prompt = llm.calls[2][1]
    assert "Attempt 1" in third_prompt and "Attempt 2" in third_prompt and "actually correct" in third_prompt
    assert record["no_passing_program"] is None


def test_hint_is_in_the_prompt():
    task, spec, example = _setup()
    llm = _scripted([sample_specs.PROGRAM_RETURN_LO])
    record = attack(task, spec, spec.code, example, llm, "t:clamp:attack", "test", "a1", "s1")
    assert record["hint"] in llm.calls[0][1]
    assert "lo <= r" in llm.calls[0][1]


def test_failed_attack_runs_realizability_query():
    task, spec, example = _setup()
    llm = _scripted(["no code", "def prog(:", sample_specs.PROGRAM_RETURN_X])
    record = attack(task, spec, spec.code, example, llm, "t:clamp:attack", "test", "a1", "s1")
    assert not record["success"]
    assert [a["rejected_reason"] for a in record["attempts"]] == ["did not follow the format",
                                                                  "did not follow the format",
                                                                  "did not pass the spec"]
    assert record["no_passing_program"] == "unsat"
    assert record["cost_usd"] > 0 and record["tokens_thinking"] == 150
