"""Checks of the golden references against their AI-written Z3 alternatives
(benchmarks/verify.py), and a check that they catch realistic mistakes in a
golden reference."""

import dataclasses

import pytest
from z3 import And, If, Or, Sum

import benchmarks
from benchmarks import verify
from speccheck.config import N


def test_every_task_has_an_ai_z3_alternative():
    for task in benchmarks.ALL_TASKS:
        assert task.ai_z3_alternative is not None, task.id


@pytest.mark.parametrize("task", benchmarks.ALL_TASKS, ids=lambda t: t.id)
def test_golden_reference_matches_ai_z3_alternative(task):
    status = verify.alternative_status(task)
    assert status["ok"], status


@pytest.mark.parametrize("task", benchmarks.ALL_TASKS, ids=lambda t: t.id)
def test_hand_picked_cases_match_ai_z3_alternative(task):
    assert verify.case_mismatches(task) == []


def _padded_digits(x):                  # the four digits of x, leading zeros included
    return [(x / 10 ** i) % 10 for i in range(4)]


def _first_longest_run_start(a):        # the first longest run instead of the last
    lengths = [1] * N
    for i in range(N - 2, -1, -1):
        lengths[i] = If(a[i] < a[i + 1], lengths[i + 1] + 1, 1)
    top = lengths[0]
    for length in lengths[1:]:
        top = If(length > top, length, top)
    result = N - 1
    for i in range(N - 1, -1, -1):
        result = If(lengths[i] == top, i, result)
    return result


MUTANTS = {
    "trunc_div3": dict(golden_program=lambda x: x / 3),                                   # rounds down
    "median_of_four": dict(golden_program=lambda a, b, c, d: If(a <= b, a, b)),          # wrong statistic
    "pivot_index": dict(golden_program=lambda a: If(a[0] == Sum([a[1], a[2], a[3]]), 0, -1)),
    "count_distinct": dict(golden_program=lambda a: Sum([If(a[j] != a[0], 1, 0) for j in range(N)]) + 1),
    "any_index_at_least_mean": dict(golden_spec=lambda a, r: And(0 <= r, r < N,             # off by 3
                                                                 4 * a[r] >= Sum([a[j] for j in range(N)]) - 3)),
    "any_adjacent_duplicate": dict(golden_spec=lambda a, r: And(0 <= r, r < N - 1, a[r] == a[r + 1])),
    "count_peaks_with_ends": dict(golden_program=lambda a: Sum([If(And(a[j] > a[j - 1], a[j] > a[j + 1]), 1, 0)
                                                                for j in range(1, N - 1)])),   # ends left out
    "any_value_exactly_twice": dict(golden_spec=lambda a, r: Or(                             # at least twice
        Sum([If(a[j] == r, 1, 0) for j in range(N)]) >= 2,
        And(r == -1, And([Sum([If(a[j] == a[i], 1, 0) for j in range(N)]) != 2 for i in range(N)])))),
    "reverse_difference": dict(golden_program=lambda x: x - Sum([d * 10 ** (3 - i)
                                                                 for i, d in enumerate(_padded_digits(x))])),
    "longest_increasing_run_start": dict(golden_program=_first_longest_run_start),
    "badminton_losing_score": dict(golden_spec=lambda p, r: Or(                             # any score at 30
        And(p == 21, 0 <= r, r <= 19), And(22 <= p, p <= 29, r == p - 2), And(p == 30, 0 <= r, r <= 29))),
    "coin_jar_final": dict(golden_program=lambda t, d: If(Or(And(d == 4, 10 <= t, t <= 12),    # up to 15 on day 5
                                                             And(d == 5, 5 <= t, t <= 15)), 1, 0)),
    "bowling_first_frame": dict(golden_program=lambda a: If(a[0] == 10, 10 + a[1],             # one bonus roll
                                                            If(a[0] + a[1] == 10, 10 + a[2], a[0] + a[1]))),
    "roman_numeral_length": dict(golden_program=lambda x: x / 10 + x % 10),                # no subtraction
    "twos_complement_bits": dict(golden_program=lambda x: Sum([((If(x < 0, -x, x) / 2 ** i) % 2)   # |x|
                                                               for i in range(6)])),
}


@pytest.mark.parametrize("task_id", sorted(MUTANTS))
def test_z3_alternative_catches_a_wrong_golden_reference(task_id):
    original = benchmarks.get(task_id)
    mutant = dataclasses.replace(original, cases=(), **MUTANTS[task_id])
    status = verify.alternative_status(mutant)
    assert status is not None and not status["ok"], "the Z3 check missed the mistake"
