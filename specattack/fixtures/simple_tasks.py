"""Simple tasks that the unit tests and sample specs use (min2, clamp, count_eq,
...), adapted from the MiniSyGuS tasks of Assignment 3 and MBPP/HumanEval-style
problems. They are not part of the benchmark. Groups follow the benchmark's:
1 integer functions, 2 array problems, 3 many correct answers."""

from z3 import And, BoolVal, If, Sum

from speccheck.config import N
from speccheck.tasks import ARRAY, INT, Task


def _all(*_):
    return BoolVal(True)


def _argmax_first(a):
    best = 0
    for j in range(1, N):
        best = If(a[j] > a[best], j, best)
    return best


def _max_arr(a):
    largest = a[0]
    for j in range(1, N):
        largest = If(a[j] > largest, a[j], largest)
    return largest


def _last_index(a, k):
    index = -1
    for j in range(N):
        index = If(a[j] == k, j, index)
    return index


TASKS = [
    Task(
        id="min2", group=1,
        description="Return the smaller of the two integers a and b.",
        params=(("a", INT), ("b", INT)), allowed=_all,
        golden_program=lambda a, b: If(a <= b, a, b),
        cases=(((3, 7), 3), ((7, 3), 3), ((5, 5), 5), ((-2, 4), -2)),
    ),
    Task(
        id="abs", group=1,
        description="Return the absolute value of the integer x.",
        params=(("x", INT),), allowed=_all,
        golden_program=lambda x: If(x >= 0, x, -x),
        cases=(((5,), 5), ((-5,), 5), ((0,), 0)),
    ),
    Task(
        id="clamp", group=1,
        description="Return x limited to the range [lo, hi]: lo if x is below lo, hi if x is above hi, "
                    "and x otherwise. You may assume lo <= hi.",
        params=(("lo", INT), ("hi", INT), ("x", INT)), allowed=lambda lo, hi, x: lo <= hi,
        golden_program=lambda lo, hi, x: If(x < lo, lo, If(x > hi, hi, x)),
        cases=(((0, 10, 5), 5), ((0, 10, -3), 0), ((0, 10, 12), 10), ((2, 2, 7), 2), ((-5, 5, -5), -5)),
    ),
    Task(
        id="argmax_first", group=2,
        description="Return the index of the first occurrence of the largest element of the array a.",
        params=(("a", ARRAY),), allowed=_all,
        golden_program=_argmax_first,
        cases=((([3, 9, 2, 9],), 1), (([5, 1, 1, 1],), 0), (([1, 2, 3, 4],), 3), (([7, 7, 7, 7],), 0),
               (([-3, -1, -2, -1],), 1)),
    ),
    Task(
        id="max_arr", group=2,
        description="Return the largest element of the array a.",
        params=(("a", ARRAY),), allowed=_all,
        golden_program=_max_arr,
        cases=((([3, 9, 2, 9],), 9), (([-5, -1, -7, -3],), -1), (([4, 4, 4, 4],), 4)),
    ),
    Task(
        id="count_eq", group=2,
        description="Return the number of positions in the array a that hold the value k.",
        params=(("a", ARRAY), ("k", INT)), allowed=_all,
        golden_program=lambda a, k: Sum([If(a[j] == k, 1, 0) for j in range(N)]),
        cases=((([1, 2, 1, 1], 1), 3), (([1, 2, 3, 4], 5), 0), (([7, 7, 7, 7], 7), 4)),
    ),
    Task(
        id="last_index", group=2,
        description="Return the index of the last occurrence of the value k in the array a, "
                    "or -1 if k does not occur in a.",
        params=(("a", ARRAY), ("k", INT)), allowed=_all,
        golden_program=_last_index,
        cases=((([1, 2, 1, 3], 1), 2), (([1, 2, 3, 4], 5), -1), (([5, 5, 5, 5], 5), 3), (([9, 1, 2, 3], 9), 0)),
    ),
    Task(
        id="insert_pos", group=2,
        description="The array a is sorted in non-decreasing order. Return the leftmost position at which "
                    "k can be inserted into a so that a stays sorted. You may assume a is sorted.",
        params=(("a", ARRAY), ("k", INT)), allowed=lambda a, k: And([a[j] <= a[j + 1] for j in range(N - 1)]),
        golden_program=lambda a, k: Sum([If(a[j] < k, 1, 0) for j in range(N)]),
        cases=((([1, 3, 3, 5], 3), 1), (([1, 3, 3, 5], 4), 3), (([1, 3, 3, 5], 0), 0), (([1, 3, 3, 5], 9), 4),
               (([2, 2, 2, 2], 2), 0)),
    ),
    Task(
        id="sum_arr", group=2,
        description="Return the sum of the elements of the array a.",
        params=(("a", ARRAY),), allowed=_all,
        golden_program=lambda a: Sum([a[j] for j in range(N)]),
        cases=((([1, 2, 3, 4],), 10), (([-1, 1, -1, 1],), 0), (([0, 0, 0, -5],), -5)),
    ),
    Task(
        id="above_both", group=3,
        description="Return any integer that is strictly greater than both a and b.",
        params=(("a", INT), ("b", INT)), allowed=_all,
        golden_spec=lambda a, b, r: And(r > a, r > b),
        cases=(((3, 7), 8, True), ((3, 7), 100, True), ((3, 7), 7, False), ((3, 7), 5, False)),
    ),
    Task(
        id="any_index_of_max", group=3,
        description="Return the index of any occurrence of the largest element of the array a.",
        params=(("a", ARRAY),), allowed=_all,
        golden_spec=lambda a, r: And(0 <= r, r < N, And([a[j] <= a[r] for j in range(N)])),
        cases=((([3, 9, 2, 9],), 1, True), (([3, 9, 2, 9],), 3, True), (([3, 9, 2, 9],), 0, False),
               (([3, 9, 2, 9],), 4, False), (([3, 9, 2, 9],), -1, False)),
    ),
]
