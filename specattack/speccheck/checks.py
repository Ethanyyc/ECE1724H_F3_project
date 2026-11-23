"""The four Z3 checks of a spec against the golden spec, the program checks
used by the attacker, and the realizability query for failed attacks.

All results are plain dicts so they can be logged and reused as they are.
"""

import time

import z3

from .tasks import output_var, values_from_dict
from .z3util import concrete_int, int_value, solve

CHECKS = ("empty", "strict", "strong", "weak")
LABEL_OF = {"empty": "empty", "strict": "too strict on inputs", "strong": "too strong", "weak": "too weak"}
CORRECT = "correct"
FORMAT_FAILURE = "did not follow the format"
UNDETERMINED = "undetermined"
TOO_WEAK = LABEL_OF["weak"]
LABEL_ORDER = [CORRECT, "too weak", "too strong", "too strict on inputs", "empty", FORMAT_FAILURE, UNDETERMINED]
DEFECT_LABELS = ["too weak", "too strong", "too strict on inputs", "empty"]


def check_spec(task, spec):
    """Run the four checks and the equivalence cross-check on a loaded spec."""
    start = time.perf_counter()
    inputs = task.inputs()
    r = output_var()
    allowed = task.allowed(*inputs)
    pre = spec.pre(*inputs)
    post = spec.post(*inputs, r)
    gold = task.golden(inputs, r)
    input_terms = task.small_terms(inputs)
    all_terms = task.small_terms(inputs, r)

    checks = {}
    q = solve([allowed, pre], input_terms)
    checks["empty"] = _outcome(q, problem_status="unsat", example=None)

    q = solve([allowed, z3.Not(pre)], input_terms)
    example = {"inputs": task.read_inputs(q.model, inputs)} if q.status == "sat" else None
    checks["strict"] = _outcome(q, problem_status="sat", example=example)

    q = solve([allowed, pre, gold, z3.Not(post)], all_terms)
    example = None
    if q.status == "sat":
        example = {"inputs": task.read_inputs(q.model, inputs), "output": int_value(q.model, r)}
    checks["strong"] = _outcome(q, problem_status="sat", example=example)

    q = solve([allowed, pre, post, z3.Not(gold)], all_terms)
    example = None
    if q.status == "sat":
        values = task.read_inputs(q.model, inputs)
        example = {"inputs": values, "output": int_value(q.model, r)}
        example.update(reference_output(task, values))
    checks["weak"] = _outcome(q, problem_status="sat", example=example)

    eq = solve([allowed, z3.Xor(z3.Implies(pre, post), gold)])
    labels = labels_from(checks)
    cross_check_ok = None
    if eq.status in ("sat", "unsat") and labels != [UNDETERMINED]:
        cross_check_ok = (eq.status == "unsat") == (labels == [CORRECT])
    z3_time = sum(c["time_ms"] for c in checks.values()) + eq.time_ms
    return {
        "checks": checks,
        "equivalence": {"status": eq.status, "time_ms": round(eq.time_ms, 3)},
        "labels": labels,
        "cross_check_ok": cross_check_ok,
        "z3_time_ms": round(z3_time, 3),
        "wall_time_ms": round((time.perf_counter() - start) * 1000, 3),
    }


def try_check_spec(task, spec):
    """check_spec, but an unexpected error (for example a Z3 sort error in an odd
    formula) is returned as a message instead of stopping the experiment.
    Returns (result or None, error message or None)."""
    try:
        return check_spec(task, spec), None
    except Exception as error:   # noqa: BLE001
        return None, f"error while checking the spec: {type(error).__name__}: {error}"


def labels_from(checks):
    """Definite problems first; 'undetermined' only if no check found a definite problem."""
    problems = [LABEL_OF[name] for name in CHECKS if checks[name]["problem"] is True]
    if problems:
        return problems
    if any(checks[name]["problem"] is None for name in CHECKS):
        return [UNDETERMINED]
    return [CORRECT]


def reference_output(task, values):
    """The intended output (one-answer task) or one acceptable output (many-answer task)."""
    concrete = task.concrete(values_from_dict(task, values))
    if task.one_answer:
        return {"intended": concrete_int(task.golden_program(*concrete))}
    alternative = z3.Int("out_acceptable")
    q = solve([task.golden_spec(*concrete, alternative)], [alternative])
    return {"acceptable": int_value(q.model, alternative) if q.status == "sat" else None}


def check_program(task, spec, term):
    """Does the program pass the spec on every allowed input, and is it wrong at
    some allowed input that satisfies the precondition?

    Returns {"verdict": "success" | "fails_spec" | "correct" | "undetermined", ...}.
    """
    inputs = task.inputs()
    allowed = task.allowed(*inputs)
    pre = spec.pre(*inputs)
    terms = task.small_terms(inputs)

    passes = solve([allowed, pre, z3.Not(spec.post(*inputs, term))], terms)
    result = {"passes_status": passes.status, "z3_time_ms": passes.time_ms}
    if passes.status == "sat":
        result.update(verdict="fails_spec", cex={"inputs": task.read_inputs(passes.model, inputs),
                                                  "output": int_value(passes.model, term)})
        return _rounded(result)
    if passes.status != "unsat":
        result.update(verdict="undetermined")
        return _rounded(result)

    wrong = solve([allowed, pre, z3.Not(task.golden(inputs, term))], terms)
    result["wrong_status"] = wrong.status
    result["z3_time_ms"] += wrong.time_ms
    if wrong.status == "sat":
        values = task.read_inputs(wrong.model, inputs)
        witness = {"inputs": values, "output": int_value(wrong.model, term)}
        witness.update(reference_output(task, values))
        result.update(verdict="success", witness=witness)
    elif wrong.status == "unsat":
        result.update(verdict="correct")
    else:
        result.update(verdict="undetermined")
    return _rounded(result)


def check_realizable(task, spec):
    """Status of `allowed ∧ pre ∧ ∀q. ¬post(q)`: sat means no program can pass the spec."""
    inputs = task.inputs()
    q = z3.Int("out_q")
    result = solve([task.allowed(*inputs), spec.pre(*inputs), z3.ForAll([q], z3.Not(spec.post(*inputs, q)))])
    return {"status": result.status, "time_ms": round(result.time_ms, 3)}


def _outcome(query, problem_status, example):
    if query.status in ("sat", "unsat"):
        problem = query.status == problem_status
    else:
        problem = None
    return {"status": query.status, "problem": problem, "example": example if problem else None,
            "time_ms": round(query.time_ms, 3)}


def _rounded(result):
    result["z3_time_ms"] = round(result["z3_time_ms"], 3)
    return result
