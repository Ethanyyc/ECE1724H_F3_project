"""Checks of the golden references against their AI-written Z3 alternatives,
used by the tests (tests/test_golden_independent.py).

1. alternative_status: prove with Z3, over all integers, that the golden
   program meets the alternative and that the alternative allows exactly one
   answer, or that the golden spec is equivalent to the alternative.
2. case_mismatches: hand-picked cases that the alternative disagrees with.
"""

import z3

from speccheck.tasks import as_int
from speccheck.z3util import solve, truth


def alternative_status(task):
    """Z3 check against the task's ai_z3_alternative, or None if it has none."""
    alternative = task.ai_z3_alternative
    if alternative is None:
        return None
    inputs = task.inputs()
    allowed = task.allowed(*inputs)
    if task.one_answer:
        golden = as_int(task.golden_program(*inputs))
        meets = solve([allowed, z3.Not(alternative(*inputs, golden))]).status
        r1, r2 = z3.Int("out_r1"), z3.Int("out_r2")
        unique = solve([allowed, alternative(*inputs, r1), alternative(*inputs, r2), r1 != r2]).status
        return {"meets": meets, "unique": unique, "ok": meets == "unsat" and unique == "unsat"}
    r = z3.Int("out_r")
    equivalent = solve([allowed, z3.Xor(task.golden_spec(*inputs, r), alternative(*inputs, r))]).status
    return {"equivalent": equivalent, "ok": equivalent == "unsat"}


def case_mismatches(task):
    """Hand-picked cases that are not allowed inputs or that the alternative disagrees with
    (an error in the case or in the alternative)."""
    bad = []
    for case in task.cases:
        concrete = task.concrete(case[0])
        if not truth(task.allowed(*concrete)):
            bad.append(("case input not allowed", case))
        elif task.one_answer and not truth(task.ai_z3_alternative(*concrete, z3.IntVal(case[1]))):
            bad.append(("case output", case))
        elif not task.one_answer and truth(task.ai_z3_alternative(*concrete, z3.IntVal(case[1]))) != case[2]:
            bad.append(("case acceptance", case))
    return bad
