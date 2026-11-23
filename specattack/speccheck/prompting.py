"""Fill the prompt templates in prompts/."""

from string import Template

from . import config

BASE_RULES = """Rules for the code (code that breaks them is rejected):
- The Z3 functions And, Or, Not, Implies, If, ForAll, Exists, Sum, Int and Ints are already available; do not import anything.
- A variable used in ForAll or Exists must be created first, for example k = Int('k'), and then used as ForAll([k], ...) or Exists([k], ...). The inputs and r are already Z3 variables (the function's parameters); do not create them again.
- Every condition that depends on the inputs (or on r) must be a Z3 formula: combine conditions with And(...), Or(...), Not(...) and Implies(...), and use If(c, x, y) for a value that depends on a condition. Python's and, or, not, if, x if c else y, in, min, max, sorted, all and any do not work on Z3 formulas.
- Everything else may be ordinary Python: local variables, lists (also with append), loops, comprehensions, helper functions, and if statements or conditions that only test loop indices and constants.
- Integers are mathematical integers (no overflow). On formulas, / and // are integer division and % is the remainder, each with a positive integer constant as the divisor. Avoid multiplying two variables: Z3 may then be unable to check the code.
- Write only function definitions at the top level; do not use try or global, do not redefine the Z3 functions or N, and do not give Z3 variables names that start with in_ or out_."""

ARRAY_RULES = """- Arrays: a[i] is element i. Every array has exactly N elements, at indices 0 to N - 1; N = {n} is predefined, so write N rather than {n}. Arrays are Z3 arrays, not Python lists: use a[j] with j in range(N), not len(a), sum(a) or for x in a.
- To talk about all or some indices, declare a variable with i = Int('i') and write ForAll([i], Implies(And(0 <= i, i < N), ...)) or Exists([i], And(0 <= i, i < N, ...)), or use a comprehension over range(N)."""


def language(task):
    rules = BASE_RULES
    if task.has_array:
        rules += "\n" + ARRAY_RULES.format(n=config.N)
    return rules


def _template(name):
    return Template((config.PROMPTS_DIR / name).read_text(encoding="utf-8"))


def _common(task):
    return {
        "description": task.description,
        "inputs": task.describe_inputs(),
        "params": ", ".join(task.param_names),
        "language": language(task),
    }


def spec_writer(task):
    return _template("spec_writer.md").substitute(_common(task))


def repair(task, spec_code, feedback):
    return _template("repair.md").substitute(_common(task), spec_code=spec_code.strip(), feedback=feedback)


def attacker(task, spec_code, hint, history):
    """history: list of (program_code, reason) for earlier failed attempts."""
    if history:
        parts = ["\nYour earlier attempts were rejected:"]
        for number, (code, reason) in enumerate(history, start=1):
            shown = code.strip() if code.strip() else "(no code)"
            parts.append(f"\nAttempt {number}:\n```python\n{shown}\n```\nRejected: {reason}")
        history_text = "\n".join(parts) + "\n"
    else:
        history_text = ""
    return _template("attacker.md").substitute(_common(task), spec_code=spec_code.strip(), hint=hint,
                                               history=history_text)
