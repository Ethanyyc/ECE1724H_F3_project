"""Turning LLM replies into specs and programs: code extraction, the static
rules and rewrites (validate.py), and the run-time guards (loader.py)."""

import sys

import pytest
import z3

import benchmarks
from fixtures import sample_specs
from speccheck import prompting
from speccheck.checks import check_spec
from speccheck.loader import extract_code, load_program, load_spec
from speccheck.validate import validate
from speccheck.z3util import solve


def spec_of(task_id, post, pre="True"):
    task = benchmarks.get(task_id)
    params = ", ".join(task.param_names)
    code = f"def pre({params}):\n    return {pre}\n\ndef post({params}, r):\n    return {post}\n"
    return task, load_spec(code, task, is_reply=False)


def equivalent(task, spec_formula_builder, expected_builder):
    inputs = task.inputs()
    r = z3.Int("out_r")
    return solve([z3.Xor(spec_formula_builder(*inputs, r), expected_builder(*inputs, r))]).status == "unsat"


def labels_of(task, spec):
    assert spec.ok, spec.reason
    return check_spec(task, spec)["labels"]


def test_extract_code_picks_last_complete_block():
    reply = ("First try:\n```python\ndef pre(a, b):\n    return True\n```\nFinal:\n"
             "```python\ndef pre(a, b):\n    return True\ndef post(a, b, r):\n    return r == a\n```\n")
    assert "r == a" in extract_code(reply, ("pre", "post"))


def test_extract_code_joins_partial_blocks():
    reply = "```python\ndef pre(a, b):\n    return True\n```\n```python\ndef post(a, b, r):\n    return True\n```"
    code = extract_code(reply, ("pre", "post"))
    assert "def pre" in code and "def post" in code


def test_prose_reply_is_a_format_failure():
    spec = load_spec("The answer is the smaller one.", benchmarks.get("min2"))
    assert not spec.ok and "syntax" in spec.reason


def test_reply_with_code_block_loads_and_keeps_function_sources():
    spec = load_spec(sample_specs.fenced(sample_specs.CORRECT["min2"]), benchmarks.get("min2"))
    assert spec.ok
    assert spec.pre_code.startswith("def pre") and spec.post_code.startswith("def post")


def test_python_bool_is_coerced_to_z3():
    spec = load_spec(sample_specs.weak_code(benchmarks.get("min2")), benchmarks.get("min2"), is_reply=False)
    assert spec.ok
    assert z3.is_true(spec.pre(*benchmarks.get("min2").inputs()))


def test_empty_and_constant_sums():
    task = benchmarks.get("sum_arr")
    code = "def pre(a):\n    return Sum([j for j in range(0)]) == 0\ndef post(a, r):\n    return r == Sum([a[j] for j in range(N)])\n"
    spec = load_spec(code, task, is_reply=False)
    assert spec.ok, spec.reason


def test_nested_loops_hit_the_step_limit():
    task = benchmarks.get("abs")
    code = ("def pre(x):\n    t = 0\n    for i in range(60):\n        for j in range(60):\n"
            "            for k in range(60):\n                t = t + 0\n    return True\n"
            "def post(x, r):\n    return True\n")
    spec = load_spec(code, task, is_reply=False)
    assert not spec.ok and "too long" in spec.reason


def test_program_loading():
    task = benchmarks.get("clamp")
    program = load_program(sample_specs.PROGRAM_RETURN_LO, task)
    assert program.ok and program.source_size > 0
    bad = load_program("```python\ndef prog(lo, hi, x):\n    return lo <= x\n```", task)
    assert not bad.ok and "integer" in bad.reason
    free = load_program("```python\ndef prog(lo, hi, x):\n    t = Int('t')\n    return t\n```", task)
    assert not free.ok and "t" in free.reason


def test_program_with_loop_unrolls():
    task = benchmarks.get("argmax_first")
    code = ("```python\ndef prog(a):\n    best = 0\n    for j in range(1, N):\n"
            "        best = If(a[j] > a[best], j, best)\n    return best\n```")
    program = load_program(code, task)
    assert program.ok, program.reason


@pytest.mark.parametrize("task_id", sorted(sample_specs.CORRECT))
def test_sample_correct_specs_load(task_id):
    spec = load_spec(sample_specs.CORRECT[task_id], benchmarks.get(task_id), is_reply=False)
    assert spec.ok, spec.reason


@pytest.mark.parametrize("task_id, code, words", sample_specs.REJECTED)
def test_rejected_code(task_id, code, words):
    spec = load_spec(code, benchmarks.get(task_id), is_reply=False)
    assert not spec.ok
    assert words.lower() in spec.reason.lower(), spec.reason


@pytest.mark.parametrize("task_id, code, expected", sample_specs.PYTHON_IDIOMS)
def test_ordinary_python_is_accepted(task_id, code, expected):
    task = benchmarks.get(task_id)
    spec = load_spec(code, task, is_reply=False)
    assert spec.ok, spec.reason
    result = check_spec(task, spec)
    assert result["labels"] == expected and result["cross_check_ok"] is True


@pytest.mark.parametrize("post", [
    "r == a or r == b",
    "not (r == a)",
    "r in [a, b]",
    "(r == a) if a <= b else (r == b)",
    "r == max(a, b)",
    "r == sorted([a, b])[0]",
    "all([r <= a, r <= b])",
    "any([r == a, r == b])",
])
def test_python_truth_tests_on_formulas_are_rejected(post):
    _, spec = spec_of("min2", post)
    assert not spec.ok and "formula was used where Python needs True or False" in spec.reason, spec.reason


def test_sets_of_formulas_are_rejected():
    _, spec = spec_of("count_distinct", "r == len(set([a[j] for j in range(N)]))")
    assert not spec.ok and "sets" in spec.reason, spec.reason


def test_z3_behaves_normally_after_loading():
    trace = sys.gettrace()
    spec_of("min2", "r == a or r == b")
    spec_of("count_eq", "r == sum(a)")
    x = z3.Int("x")
    assert bool(x == x) and len({x, x}) == 1
    assert "__iter__" not in z3.ArrayRef.__dict__ and sys.gettrace() is trace


def test_chained_comparison_becomes_and():
    task, spec = spec_of("clamp", "lo <= r <= hi")
    assert spec.ok, spec.reason
    assert equivalent(task, spec.post, lambda lo, hi, x, r: z3.And(lo <= r, r <= hi))


def test_chained_comparison_on_plain_numbers_is_a_python_bool():
    task = benchmarks.get("count_eq")
    code = ("def pre(a, k):\n    return True\n\ndef post(a, k, r):\n"
            "    return r == Sum([If(a[j] == k, 1, 0) for j in range(-2, 9) if 0 <= j < N])\n")
    assert labels_of(task, load_spec(code, task, is_reply=False)) == ["correct"]


def test_floor_division_by_positive_constant_becomes_integer_division():
    task, spec = spec_of("abs", "r == x // 2")
    assert spec.ok, spec.reason
    assert equivalent(task, spec.post, lambda x, r: r == x / 2)
    code = "def pre(x):\n    return True\n\ndef post(x, r):\n    y = x\n    y //= 2\n    return r == y\n"
    spec = load_spec(code, task, is_reply=False)
    assert spec.ok and equivalent(task, spec.post, lambda x, r: r == x / 2)


def test_division_keeps_python_meaning_on_plain_numbers():
    task = benchmarks.get("count_eq")
    code = ("def pre(a, k):\n    return True\n\ndef post(a, k, r):\n"
            "    last = N // 2 + 7 % 3 + 1\n    one = 3 / 3\n    t = 5\n    t //= 4\n"
            "    return r == Sum([If(a[j] == k, t, 0) for j in range(last)]) * 1\n")
    assert labels_of(task, load_spec(code, task, is_reply=False)) == ["correct"]


def test_z3_functions_on_plain_values_give_plain_values():
    task = benchmarks.get("count_eq")
    code = ("def pre(a, k):\n    return True\n\ndef post(a, k, r):\n"
            "    js = [j for j in range(N) if And(j >= 0, Not(j > N), Implies(j < 0, False), Or(j < N, False))]\n"
            "    return r == Sum([If(a[j] == k, 1, 0) for j in js]) + Sum([1 for j in range(0)])\n")
    assert labels_of(task, load_spec(code, task, is_reply=False)) == ["correct"]


def test_z3_import_annotations_docstrings_and_main_block_are_ignored():
    spec = load_spec(sample_specs.CORRECT["insert_pos"], benchmarks.get("insert_pos"), is_reply=False)
    assert spec.ok, spec.reason
    code = ("import z3 as Z\n\ndef pre(a, b) -> bool:\n    '''Any inputs.'''\n    return True\n\n"
            "def post(a: int, b: int, r: int):\n    return Z.And(r <= a, r <= b, Z.Or(r == a, r == b))\n\n"
            "if __name__ == '__main__':\n    print(post(1, 2, 1))\n")
    task = benchmarks.get("min2")
    assert labels_of(task, load_spec(code, task, is_reply=False)) == ["correct"]


def test_helper_functions_are_allowed():
    task = benchmarks.get("min2")
    code = ("def smaller(x, y):\n    return If(x <= y, x, y)\n\n"
            "def pre(a, b):\n    def always():\n        return True\n    return always()\n\n"
            "def post(a, b, r):\n    return r == smaller(a, b)\n")
    spec = load_spec(code, task, is_reply=False)
    assert labels_of(task, spec) == ["correct"]
    assert "def smaller" in spec.post_code


@pytest.mark.parametrize("body, words", [
    ("import math\n    return True", "import"),
    ("try:\n        return a > b\n    except Exception:\n        return True", "try"),
    ("global g\n    return True", "global"),
    ("return a.decl() is None", "attribute"),
    ("return __import__('os')", "__"),
    ("And = Or\n    return True", "predefined"),
    ("def N():\n        return 1\n    return True", "predefined"),
    ("def helper(x, acc=[]):\n        return x\n    return True", "default"),
    ("@staticmethod\n    def helper():\n        return 1\n    return True", "decorator"),
])
def test_static_rules(body, words):
    code = f"def pre(a, b):\n    {body}\n\ndef post(a, b, r):\n    return True\n"
    result = validate(code, ("pre", "post"), {"pre": 2, "post": 3})
    assert not result.ok and words.lower() in result.reason.lower(), result.reason


def test_top_level_code_other_than_functions_is_rejected():
    code = "K = 2\ndef pre(a, b):\n    return True\ndef post(a, b, r):\n    return r == K\n"
    result = validate(code, ("pre", "post"), {"pre": 2, "post": 3})
    assert not result.ok and "top level" in result.reason


def test_reserved_variable_names_are_rejected_at_run_time():
    for post in ("Exists([Int('in_b')], r == a)", "Exists(Ints('i out_r'), r == a)"):
        _, spec = spec_of("min2", post)
        assert not spec.ok and "reserved" in spec.reason, spec.reason


def test_z3_constants_are_available():
    task, spec = spec_of("min2", "And(r <= a, r <= b, Or(r == a, r == b, BoolVal(False)), r + IntVal(0) == r)")
    assert labels_of(task, spec) == ["correct"]


def test_nonlinear_arithmetic_is_allowed():
    _, spec = spec_of("min2", "r * r == a * b")
    assert spec.ok, spec.reason


def test_long_ranges_and_formula_bounds_are_rejected():
    _, spec = spec_of("abs", "Sum([1 for j in range(200000)]) > 0")
    assert not spec.ok and "range too long" in spec.reason
    _, spec = spec_of("abs", "Sum([1 for j in range(10000)]) > 0")
    assert spec.ok, spec.reason
    _, spec = spec_of("abs", "Sum([1 for j in range(x)]) > 0")
    assert not spec.ok and "range bounds must be plain integers" in spec.reason


def test_every_prompt_states_the_formula_rule():
    task = benchmarks.get("last_index")
    rule = "do not work on Z3 formulas"
    assert rule in prompting.spec_writer(task)
    assert rule in prompting.attacker(task, "def pre(a, k):\n    return True", "hint", [])
    assert rule in prompting.repair(task, "def pre(a, k):\n    return True", "feedback")
    assert "helper functions" in prompting.spec_writer(task)


def test_comprehension_with_several_for_clauses():
    task = benchmarks.get("count_inversions")
    code = ("def pre(a):\n    return True\n\ndef post(a, r):\n"
            "    return r == Sum([If(a[i] > a[j], 1, 0) for i in range(N) for j in range(i + 1, N) if i != j])\n")
    assert labels_of(task, load_spec(code, task, is_reply=False)) == ["correct"]
    code = ("def pre(a):\n    return True\n\ndef post(a, r):\n"
            "    return Sum([1 for i in range(2) for j in range(2) for k in range(2) for m in range(2)]) == 16\n")
    assert load_spec(code, task, is_reply=False).ok


def test_multiplication_by_loop_variable_is_linear_and_allowed():
    task = benchmarks.get("sum_arr")
    code = ("def pre(a):\n    return True\n\ndef post(a, r):\n"
            "    return r == Sum([a[j] * 1 + 0 * j for j in range(N)])\n")
    spec = load_spec(code, task, is_reply=False)
    assert spec.ok, spec.reason


def test_programs_are_loaded_the_same_way():
    task = benchmarks.get("clamp")
    plain = load_program("def prog(lo, hi, x):\n    return If(x < lo, lo, If(x > hi, hi, x))\n", task, is_reply=False)
    helped = load_program("def low(lo, x):\n    return If(x < lo, lo, x)\n\n"
                          "def prog(lo, hi, x):\n    return If(low(lo, x) > hi, hi, low(lo, x))\n", task, is_reply=False)
    assert plain.ok and helped.ok and helped.source_size > plain.source_size > 0
    bad = load_program("def prog(lo, hi, x):\n    return lo if x < lo else x\n", task, is_reply=False)
    assert not bad.ok and "formula was used" in bad.reason
