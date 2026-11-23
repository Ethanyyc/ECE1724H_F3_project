"""Turn an LLM reply into usable spec or program functions.

Steps: extract the code block; check, normalize and rewrite it without running
it (validate.py); run it in a namespace that holds only the Z3 functions, N and
a few harmless built-ins; build the formulas on symbolic inputs; and reject
formulas with the wrong sort or with free variables that are not inputs (an
undeclared variable would silently change the meaning of the spec).

Every run of the model's code is guarded (`_guard`), because Python quietly
computes the wrong thing on Z3 formulas in a few places:
- a truth test on a formula (if, while, and, or, not, in, min, max, all, any,
  ...) raises; Python would decide `x == y` by comparing the two expressions'
  syntax, not their values;
- hashing a formula (sets, dict keys) raises; Python would treat different
  expressions as different values;
- iterating over a Z3 array raises; it would never end;
- the number of executed lines of the model's code is limited.
"""

import ast
import builtins
import re
import sys
import types
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Optional

import z3

from . import config
from .tasks import OUTPUT_NAME, RESERVED_PREFIXES, as_int, output_var
from .validate import validate
from .z3util import free_constants

CODE_BLOCK = re.compile(r"```[ \t]*([A-Za-z0-9_+.-]*)[^\n]*\n(.*?)```", re.DOTALL)
PYTHON_TAGS = ("", "python", "py", "python3")
CODE_NAME = "<llm-code>"
MAX_RANGE_LENGTH = 100_000
MAX_RANGE_BOUND = 1_000_000
MAX_STEPS = 200_000              # executed lines of the model's code per call
SAFE_BUILTINS = {name: getattr(builtins, name) for name in (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "int", "len", "list", "map", "max", "min",
    "reversed", "set", "sorted", "sum", "tuple", "zip")}
SAFE_BUILTINS["print"] = lambda *args, **kwargs: None
FORMULA_IN_CONDITION = (
    "a Z3 formula was used where Python needs True or False (if, while, and, or, not, x if c else y, in, "
    "min, max, sorted, all, any or similar); these do not work on formulas, so build every condition on "
    "the inputs with If, And, Or, Not and Implies")


class StepLimit(Exception):
    pass


@dataclass
class LoadedSpec:
    ok: bool
    reason: str
    code: str
    pre_code: str = ""
    post_code: str = ""                  # post and any helper functions
    pre: Optional[Callable] = None       # inputs -> Z3 Bool
    post: Optional[Callable] = None      # inputs, r -> Z3 Bool


@dataclass
class LoadedProgram:
    ok: bool
    reason: str
    code: str
    term: Optional[z3.ArithRef] = None   # the program on the task's symbolic inputs
    source_size: int = 0                 # AST nodes of all its functions


def extract_code(reply, required):
    """The Python code in a reply: the last code block that defines every
    required function, else all Python code blocks joined, else the whole reply."""
    blocks = [body for tag, body in CODE_BLOCK.findall(reply) if tag.lower() in PYTHON_TAGS]
    if not blocks:
        return reply.strip()
    complete = [b for b in blocks if all(re.search(rf"^\s*def\s+{name}\s*\(", b, re.M) for name in required)]
    if complete:
        return complete[-1].strip()
    return "\n\n".join(b.strip() for b in blocks)


def load_spec(text, task, is_reply=True):
    code = extract_code(text, ("pre", "post")) if is_reply else text.strip()
    k = len(task.params)
    namespace, reason, _ = _run(code, ("pre", "post"), {"pre": k, "post": k + 1})
    if namespace is None:
        return LoadedSpec(False, reason, code)
    pre_fn, post_fn = _guarded(namespace["pre"]), _guarded(namespace["post"])

    def pre(*inputs):
        return _boolean(pre_fn(*inputs), "pre")

    def post(*args):
        return _boolean(post_fn(*args), "post")

    inputs = task.inputs()
    input_names = {term.decl().name() for term in inputs}
    try:
        pre_formula = pre(*inputs)
        post_formula = post(*inputs, output_var())
    except Exception as error:   # noqa: BLE001 - any failure here is a format failure
        return LoadedSpec(False, f"error while building the formulas: {_describe(error)}", code)
    extra = (free_constants(pre_formula) - input_names) | (free_constants(post_formula) - input_names - {OUTPUT_NAME})
    if extra:
        names = ", ".join(sorted(extra))
        return LoadedSpec(False, f"the formulas use variable(s) {names} that are neither inputs nor bound by ForAll/Exists", code)
    segments = _segments(code)
    helpers = [source for name, source in segments.items() if name not in ("pre", "post")]
    post_code = "\n\n".join([segments.get("post", "")] + helpers)
    return LoadedSpec(True, "", code, segments.get("pre", ""), post_code, pre, post)


def load_program(text, task, is_reply=True):
    code = extract_code(text, ("prog",)) if is_reply else text.strip()
    namespace, reason, size = _run(code, ("prog",), {"prog": len(task.params)})
    if namespace is None:
        return LoadedProgram(False, reason, code)
    inputs = task.inputs()
    try:
        value = _guarded(namespace["prog"])(*inputs)
    except Exception as error:   # noqa: BLE001
        return LoadedProgram(False, f"error while building the program: {_describe(error)}", code)
    try:
        term = as_int(value)
    except TypeError as error:
        return LoadedProgram(False, f"prog must return an integer expression (use If(condition, 1, 0) for yes/no results): {error}", code)
    extra = free_constants(term) - {t.decl().name() for t in inputs}
    if extra:
        return LoadedProgram(False, f"the program uses variable(s) {', '.join(sorted(extra))} that are not inputs", code)
    return LoadedProgram(True, "", code, term, size)


def golden_as_spec(task):
    """The golden reference viewed as a spec: pre = allowed inputs, post = golden spec."""
    return LoadedSpec(True, "", "<golden>", "", "", task.allowed,
                      lambda *args: task.golden(list(args[:-1]), args[-1]))


# running the model's code

def _run(code, required, arity):
    result = validate(code, required, arity)
    if not result.ok:
        return None, result.reason, 0
    namespace = _namespace()
    try:
        compiled = compile(result.tree, CODE_NAME, "exec")
        with _guard():
            exec(compiled, namespace)   # noqa: S102 - checked code, restricted namespace, guarded
    except Exception as error:   # noqa: BLE001
        return None, f"error while defining the functions: {_describe(error)}", 0
    return namespace, "", result.size


def _guarded(function):
    def call(*args):
        with _guard():
            return function(*args)
    return call


def _formula_truth(self):
    if z3.is_true(self):
        return True
    if z3.is_false(self):
        return False
    raise TypeError(FORMULA_IN_CONDITION)


def _formula_hash(self):
    raise TypeError("Z3 formulas cannot be put in sets or used as dict keys; Python would compare the "
                    "expressions, not their values")


def _array_iteration(self):
    raise TypeError("a Z3 array cannot be iterated or turned into a list; use a[j] with j in range(N)")


@contextmanager
def _guard():
    steps = [MAX_STEPS]

    def count(frame, event, arg):
        if event == "line":
            steps[0] -= 1
            if steps[0] < 0:
                raise StepLimit(f"the code runs too long (more than {MAX_STEPS:,} steps)")
        return count

    def trace(frame, event, arg):
        return count if frame.f_code.co_filename == CODE_NAME else None

    saved_trace = sys.gettrace()
    saved = {"bool": z3.AstRef.__bool__, "hash": z3.AstRef.__hash__, "iter": z3.ArrayRef.__dict__.get("__iter__")}
    z3.AstRef.__bool__ = _formula_truth
    z3.AstRef.__hash__ = _formula_hash
    z3.ArrayRef.__iter__ = _array_iteration
    sys.settrace(trace)
    try:
        yield
    finally:
        sys.settrace(saved_trace)
        z3.AstRef.__bool__ = saved["bool"]
        z3.AstRef.__hash__ = saved["hash"]
        if saved["iter"] is None:
            del z3.ArrayRef.__iter__
        else:
            z3.ArrayRef.__iter__ = saved["iter"]


def _namespace():
    return {
        "__builtins__": SAFE_BUILTINS,
        "And": _and,
        "Or": _or,
        "Not": _not,
        "Implies": _implies,
        "If": _if,
        "ForAll": z3.ForAll,
        "Exists": z3.Exists,
        "Sum": _sum,
        "Int": _int,
        "Ints": _ints,
        "BoolVal": z3.BoolVal,
        "IntVal": z3.IntVal,
        "range": _range,
        "N": config.N,
        "__chain": _chain,
        "__div": _div,
        "__floordiv": _floordiv,
        "__mod": _mod,
    }


# the functions in the namespace; on plain Python values they return plain values

def _items(args):
    if len(args) == 1 and isinstance(args[0], (list, tuple, types.GeneratorType)):
        return list(args[0])
    return list(args)


def _plain(items):
    return all(isinstance(item, bool) for item in items)


def _and(*args):
    items = _items(args)
    return all(items) if _plain(items) else z3.And(*items)


def _or(*args):
    items = _items(args)
    return any(items) if _plain(items) else z3.Or(*items)


def _not(value):
    return (not value) if isinstance(value, bool) else z3.Not(value)


def _implies(a, b):
    if isinstance(a, bool) and isinstance(b, bool):
        return (not a) or b
    return z3.Implies(a, b)


def _if(condition, then, otherwise):
    if isinstance(condition, bool):
        return then if condition else otherwise
    return z3.If(condition, then, otherwise)


def _sum(*args):
    items = _items(args)
    if not any(isinstance(item, z3.ExprRef) for item in items):
        if any(isinstance(item, bool) or not isinstance(item, int) for item in items):
            raise TypeError("Sum takes integers")
        return sum(items)
    return z3.Sum(items)


def _check_variable_name(name):
    if not isinstance(name, str):
        raise TypeError("Int takes the variable's name as a string, as in Int('i')")
    if name.startswith(RESERVED_PREFIXES):
        raise ValueError(f"the variable name {name} is reserved (names may not start with in_ or out_)")


def _int(name):
    _check_variable_name(name)
    return z3.Int(name)


def _ints(names):
    variables = z3.Ints(names)
    for variable in variables:
        _check_variable_name(variable.decl().name())
    return variables


def _range(*args):
    for value in args:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("range bounds must be plain integers, not formulas (to talk about all or some "
                            "values of a formula, use ForAll or Exists)")
        if abs(value) > MAX_RANGE_BOUND:
            raise ValueError("range bound too large")
    values = range(*args)
    if len(values) > MAX_RANGE_LENGTH:
        raise ValueError("range too long")
    return values


def _is_formula(value):
    return isinstance(value, z3.ExprRef)


def _chain(*parts):
    """a < b < c, rewritten as _chain(a < b, b < c)."""
    return z3.And(*parts) if any(_is_formula(part) for part in parts) else all(parts)


def _divisor(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("integer division and remainder of a formula need a positive integer constant as the divisor")
    return value


def _div(x, y):
    if _is_formula(x) or _is_formula(y):
        return x / _divisor(y)       # Z3 integer division: rounds down for a positive divisor, like Python's //
    return x / y


def _floordiv(x, y):
    if _is_formula(x) or _is_formula(y):
        return x / _divisor(y)
    return x // y


def _mod(x, y):
    if _is_formula(x) or _is_formula(y):
        return x % _divisor(y)       # in [0, y) for a positive divisor, like Python's %
    return x % y


def _boolean(value, name):
    if isinstance(value, bool):
        return z3.BoolVal(value)
    if isinstance(value, z3.BoolRef):
        return value
    raise TypeError(f"{name} must return a Boolean formula, got {type(value).__name__}")


def _describe(error):
    return f"{type(error).__name__}: {error}"


def _segments(code):
    tree = ast.parse(code)
    return {node.name: ast.get_source_segment(code, node) or "" for node in tree.body if isinstance(node, ast.FunctionDef)}
