"""Benchmark tasks: description, allowed inputs and golden references."""

from dataclasses import dataclass
from typing import Callable, Optional

import z3

from . import config

INT = "int"
ARRAY = "array"
INPUT_PREFIX = "in_"
OUTPUT_NAME = "out_r"
RESERVED_PREFIXES = ("in_", "out_")


@dataclass(frozen=True)
class Task:
    """One benchmark task.

    params: ((name, INT or ARRAY), ...), in the order of the function's arguments.
    allowed: inputs -> Z3 Bool, the valid inputs stated in the description.
    golden_program (one-answer tasks): inputs -> Z3 Int.
    golden_spec (many-answer tasks): inputs, r -> Z3 Bool.
    cases: hand-picked checks of the golden reference.
        one-answer: (inputs, expected_output)
        many-answer: (inputs, output, accepted)
        where inputs is a tuple with one Python int or list per parameter.
    ai_z3_alternative: a second Z3 formula for the task, written by an AI
        assistant in a different way from the golden reference
        (benchmarks/verify.py checks that the two agree);
        one-answer: inputs, r -> Bool with exactly one r per allowed input;
        many-answer: inputs, r -> Bool equivalent to the golden spec.
    """

    id: str
    group: int
    description: str
    params: tuple
    allowed: Callable
    golden_program: Optional[Callable] = None
    golden_spec: Optional[Callable] = None
    cases: tuple = ()
    ai_z3_alternative: Optional[Callable] = None

    def __post_init__(self):
        if (self.golden_program is None) == (self.golden_spec is None):
            raise ValueError(f"{self.id}: give exactly one of golden_program and golden_spec")
        for name, kind in self.params:
            if kind not in (INT, ARRAY):
                raise ValueError(f"{self.id}: unknown type {kind} for {name}")
            if name.startswith(RESERVED_PREFIXES) or name == "r":
                raise ValueError(f"{self.id}: parameter name {name} is reserved")

    @property
    def one_answer(self):
        return self.golden_program is not None

    @property
    def param_names(self):
        return [name for name, _ in self.params]

    @property
    def has_array(self):
        return any(kind == ARRAY for _, kind in self.params)

    def inputs(self):
        """Symbolic inputs, named with the reserved prefix so LLM code cannot capture them."""
        return [_symbolic(name, kind) for name, kind in self.params]

    def golden(self, inputs, r):
        """Z3 formula: the golden spec accepts output r for these inputs."""
        if self.golden_program is not None:
            return r == as_int(self.golden_program(*inputs))
        return self.golden_spec(*inputs, r)

    def small_terms(self, inputs, r=None):
        """Integer terms to bound when looking for readable examples."""
        terms = []
        for (_, kind), term in zip(self.params, inputs):
            if kind == INT:
                terms.append(term)
            else:
                terms.extend(term[i] for i in range(config.N))
        if r is not None:
            terms.append(r)
        return terms

    def concrete(self, values):
        """Z3 terms for concrete input values (ints, and lists of N ints for arrays)."""
        if len(values) != len(self.params):
            raise ValueError(f"{self.id}: expected {len(self.params)} input values")
        return [_concrete(kind, value) for (_, kind), value in zip(self.params, values)]

    def read_inputs(self, model, inputs):
        """Concrete input values from a Z3 model: {name: int or list of N ints}."""
        from .z3util import int_value
        values = {}
        for (name, kind), term in zip(self.params, inputs):
            if kind == INT:
                values[name] = int_value(model, term)
            else:
                values[name] = [int_value(model, term[i]) for i in range(config.N)]
        return values

    def describe_inputs(self):
        """Input description used in prompts."""
        parts = []
        for name, kind in self.params:
            if kind == INT:
                parts.append(f"{name}: integer")
            else:
                last = config.N - 1
                parts.append(f"{name}: integer array with N = {config.N} elements, {name}[0] to {name}[{last}]")
        return "; ".join(parts)


def output_var():
    return z3.Int(OUTPUT_NAME)


def as_int(value):
    if isinstance(value, bool):
        raise TypeError("expected an integer, got a Boolean")
    if isinstance(value, int):
        return z3.IntVal(value)
    if isinstance(value, z3.ArithRef) and value.is_int():
        return value
    raise TypeError(f"expected an integer expression, got {value!r}")


def _symbolic(name, kind):
    if kind == INT:
        return z3.Int(INPUT_PREFIX + name)
    return z3.Array(INPUT_PREFIX + name, z3.IntSort(), z3.IntSort())


def _concrete(kind, value):
    if kind == INT:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"expected an int, got {value!r}")
        return z3.IntVal(value)
    if len(value) != config.N:
        raise ValueError(f"expected {config.N} array elements, got {len(value)}")
    array = z3.K(z3.IntSort(), z3.IntVal(0))
    for index, element in enumerate(value):
        array = z3.Store(array, index, element)
    return array


def values_from_dict(task, values):
    """Input values as a tuple in parameter order, from {name: value}."""
    return tuple(values[name] for name in task.param_names)
