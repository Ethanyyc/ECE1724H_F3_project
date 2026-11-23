import pytest
import z3

import benchmarks
from fixtures import sample_specs
from speccheck import config
from speccheck.checks import check_program, check_realizable, check_spec, labels_from
from speccheck.loader import golden_as_spec, load_program, load_spec
from speccheck.z3util import solve


@pytest.mark.parametrize("task_id, code, expected", sample_specs.KNOWN)
def test_known_spec_labels(task_id, code, expected):
    task = benchmarks.get(task_id)
    spec = load_spec(code, task, is_reply=False)
    assert spec.ok, spec.reason
    result = check_spec(task, spec)
    assert set(result["labels"]) == set(expected)
    assert result["cross_check_ok"] is True


def test_every_golden_spec_is_correct():
    for task in benchmarks.ALL_TASKS:
        result = check_spec(task, golden_as_spec(task))
        assert result["labels"] == ["correct"] and result["equivalence"]["status"] == "unsat", task.id


def test_every_many_answer_golden_spec_rejects_some_output_at_every_allowed_input():
    for task in benchmarks.ALL_TASKS:
        if task.one_answer:
            continue
        inputs, q = task.inputs(), z3.Int("out_any")
        assert solve([task.allowed(*inputs), z3.ForAll([q], task.golden(inputs, q))]).status == "unsat", task.id


def _checks(**problems):
    return {name: {"problem": problems.get(name, False)} for name in ("empty", "strict", "strong", "weak")}


def test_labels_definite_problem_wins_over_unknown():
    assert labels_from(_checks(weak=True, strong=None)) == ["too weak"]


def test_labels_unknown_without_problem_is_undetermined():
    assert labels_from(_checks(strong=None)) == ["undetermined"]


def test_labels_all_clean_is_correct():
    assert labels_from(_checks()) == ["correct"]


def test_weak_example_has_intended_output_and_small_values():
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    example = check_spec(task, spec)["checks"]["weak"]["example"]
    values = list(example["inputs"].values()) + [example["output"], example["intended"]]
    assert all(abs(v) <= config.SMALL_MODEL_BOUND for v in values)
    lo, hi, x = example["inputs"]["lo"], example["inputs"]["hi"], example["inputs"]["x"]
    assert example["intended"] == min(max(x, lo), hi)
    assert example["output"] != example["intended"]


def test_weak_example_of_many_answer_task_has_acceptable_output():
    task = benchmarks.get("above_both")
    spec = load_spec(sample_specs.weak_code(task), task, is_reply=False)
    example = check_spec(task, spec)["checks"]["weak"]["example"]
    a, b = example["inputs"]["a"], example["inputs"]["b"]
    assert not (example["output"] > a and example["output"] > b)
    assert example["acceptable"] > a and example["acceptable"] > b


def test_check_program_verdicts():
    task = benchmarks.get("clamp")
    spec = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    assert check_program(task, spec, load_program(sample_specs.PROGRAM_RETURN_LO, task).term)["verdict"] == "success"
    assert check_program(task, spec, load_program(sample_specs.PROGRAM_RETURN_X, task).term)["verdict"] == "fails_spec"
    assert check_program(task, spec, load_program(sample_specs.PROGRAM_GOLDEN_CLAMP, task).term)["verdict"] == "correct"


def test_program_wrong_only_outside_precondition_is_not_a_success():
    # The spec is too strict (it excludes x < lo) and too weak; a program that is wrong
    # only where pre is false must not count as a wrong program that passes the spec.
    task = benchmarks.get("clamp")
    code = ("def pre(lo, hi, x):\n    return And(lo <= hi, x >= lo)\n"
            "def post(lo, hi, x, r):\n    return And(lo <= r, r <= hi, Implies(x <= hi, r == x))\n")
    spec = load_spec(code, task, is_reply=False)
    program = load_program("```python\ndef prog(lo, hi, x):\n    return If(x < lo, hi, If(x > hi, hi, x))\n```", task)
    assert check_program(task, spec, program.term)["verdict"] == "correct"


def test_realizability():
    task = benchmarks.get("clamp")
    unrealizable = load_spec("def pre(lo, hi, x):\n    return lo <= hi\ndef post(lo, hi, x, r):\n    return False\n",
                             task, is_reply=False)
    assert check_realizable(task, unrealizable)["status"] == "sat"
    weak = load_spec(sample_specs.ATTACK_CLAMP_WEAK, task, is_reply=False)
    assert check_realizable(task, weak)["status"] == "unsat"
