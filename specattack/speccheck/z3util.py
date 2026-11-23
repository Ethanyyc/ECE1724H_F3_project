"""Small helpers around the Z3 Python API."""

import time
from dataclasses import dataclass
from typing import Optional

import z3

from . import config

z3.set_param("smt.random_seed", config.Z3_SEED)
z3.set_param("sat.random_seed", config.Z3_SEED)


@dataclass
class QueryResult:
    status: str                      # "sat", "unsat", "unknown" or "timeout"
    model: Optional[z3.ModelRef]
    time_ms: float


def _check(constraints, timeout_ms):
    solver = z3.Solver()
    solver.set("timeout", int(timeout_ms))
    solver.add(*constraints)
    start = time.perf_counter()
    answer = solver.check()
    elapsed = (time.perf_counter() - start) * 1000
    if answer == z3.sat:
        return QueryResult("sat", solver.model(), elapsed)
    if answer == z3.unsat:
        return QueryResult("unsat", None, elapsed)
    reason = solver.reason_unknown().lower()
    status = "timeout" if ("timeout" in reason or "canceled" in reason) else "unknown"
    return QueryResult(status, None, elapsed)


def solve(constraints, small_terms=(), timeout_ms=None):
    """Decide the conjunction of `constraints`.

    If `small_terms` is given, Z3 first looks for a model with every term in
    [-SMALL_MODEL_BOUND, SMALL_MODEL_BOUND], so that examples are readable. A
    model found that way is a model of the unbounded query too, so the verdict
    is unchanged; otherwise the query is rerun without bounds.
    """
    timeout_ms = config.Z3_TIMEOUT_MS if timeout_ms is None else timeout_ms
    constraints = list(constraints)
    spent = 0.0
    if small_terms:
        bound = config.SMALL_MODEL_BOUND
        bounds = [z3.And(t >= -bound, t <= bound) for t in small_terms]
        first = _check(constraints + bounds, min(config.SMALL_MODEL_TIMEOUT_MS, timeout_ms))
        spent = first.time_ms
        if first.status == "sat":
            return first
    result = _check(constraints, timeout_ms)
    result.time_ms += spent
    return result


def int_value(model, term):
    value = model.eval(term, model_completion=True)
    if z3.is_int_value(value):
        return value.as_long()
    return concrete_int(value)


def concrete_int(expr):
    """The integer value of a ground integer expression."""
    expr = expr if isinstance(expr, z3.ExprRef) else z3.IntVal(expr)
    simplified = z3.simplify(expr)
    if z3.is_int_value(simplified):
        return simplified.as_long()
    holder = z3.Int("__value")
    result = _check([holder == expr], config.Z3_TIMEOUT_MS)
    if result.status != "sat":
        raise ValueError(f"cannot evaluate {expr}")
    return result.model.eval(holder, model_completion=True).as_long()


def truth(formula):
    """True, False or None (undecided) for a ground formula."""
    if _check([z3.Not(formula)], config.Z3_TIMEOUT_MS).status == "unsat":
        return True
    if _check([formula], config.Z3_TIMEOUT_MS).status == "unsat":
        return False
    return None


def _children(expr):
    if z3.is_quantifier(expr):
        return [expr.body()]
    if z3.is_app(expr):
        return list(expr.children())
    return []


def _walk(expr):
    seen = set()
    stack = [expr]
    while stack:
        node = stack.pop()
        key = node.get_id()
        if key in seen:
            continue
        seen.add(key)
        yield node
        stack.extend(_children(node))


def term_size(expr):
    """Number of distinct subterms (the expression is a DAG after unrolling)."""
    return sum(1 for _ in _walk(expr))


def free_constants(expr):
    """Names of uninterpreted constants that occur free in `expr`."""
    names = set()
    for node in _walk(expr):
        if z3.is_const(node) and node.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            names.add(node.decl().name())
    return names
