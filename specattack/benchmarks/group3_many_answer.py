"""Group 3: tasks with many correct answers whose acceptance sets have subtle
edges (array ends, sentinel results, existence preconditions, an average that
integer division gets wrong). Golden specs are written directly and are
quantifier-free (the arrays have N = 4 elements).

Three tasks target conditions that are easy to loosen without noticing
("exactly" versus "at least", repeated smallest or largest values, and the
loser scores that end a badminton game, where the 30-point cap only ends a
close game), so a natural mistake gives a spec that is only too weak. They
replaced tasks the spec writer always got right (any_strictly_between,
any_common_value, any_at_distance and any_between_even_and_odd).

Each task has a golden spec, hand-picked cases and an AI-written Z3
alternative written in a different way; benchmarks/verify.py proves that the
two accept the same outputs."""

from z3 import And, BoolVal, Exists, If, Implies, Int, IntVal, Not, Or, Sum

from speccheck.config import N
from speccheck.tasks import ARRAY, INT, Task


# Z3 helpers

def everything(*_):
    return BoolVal(True)


def zmin(x, y):
    return If(x <= y, x, y)


def zmax(x, y):
    return If(x >= y, x, y)


def total(items):
    items = list(items)
    return Sum(items) if items else IntVal(0)


def all_of(items):
    items = list(items)
    return And(items) if items else BoolVal(True)


def any_of(items):
    items = list(items)
    return Or(items) if items else BoolVal(False)


def count(predicate):
    """Number of indices j in 0..N-1 for which predicate(j) holds."""
    return total(If(predicate(j), 1, 0) for j in range(N))


def pairs():
    """Index pairs i < j."""
    return [(i, j) for i in range(N) for j in range(i + 1, N)]


def array_max(a):
    largest = a[0]
    for j in range(1, N):
        largest = zmax(largest, a[j])
    return largest


def array_min(a):
    smallest = a[0]
    for j in range(1, N):
        smallest = zmin(smallest, a[j])
    return smallest


def index(r):
    return And(0 <= r, r < N)


# golden specs and AI-written Z3 alternatives


def _peak(a, j):
    conditions = []
    if j > 0:
        conditions.append(a[j] >= a[j - 1])
    if j < N - 1:
        conditions.append(a[j] >= a[j + 1])
    return all_of(conditions)


def _array_sum(a):
    return total(a[j] for j in range(N))


def _alt_split_value(a, r):
    others = lambda i, j: [t for t in range(N) if t not in (i, j)]   # noqa: E731
    return any_of(And(a[i] < r, a[j] < r, all_of(a[t] >= r for t in others(i, j))) for i, j in pairs())


def _occurs_exactly_twice(a, v):
    """By pairs of positions: v is at i and j and nowhere else."""
    return any_of(And(a[i] == v, a[j] == v, all_of(a[k] != v for k in range(N) if k not in (i, j)))
                  for i, j in pairs())


def _exactly_twice_golden(a, r):
    return Or(count(lambda j: a[j] == r) == 2,
              And(r == -1, all_of(count(lambda j: a[j] == a[i]) != 2 for i in range(N))))


def _not_extreme_golden(a, r):
    low, high = array_min(a), array_max(a)
    return Or(any_of(And(r == j, a[j] > low, a[j] < high) for j in range(N)),
              And(r == -1, all_of(Or(a[j] == low, a[j] == high) for j in range(N))))


def _alt_not_extreme(a, r):
    def between(v):
        return And(any_of(a[k] < v for k in range(N)), any_of(a[k] > v for k in range(N)))
    return Or(And(index(r), between(a[r])), And(r == -1, all_of(Not(between(a[j])) for j in range(N))))


def _badminton_final(w, l):
    """w-l, winner first, can be the final score of a badminton game."""
    return Or(And(w == 21, 0 <= l, l <= 19), And(22 <= w, w <= 29, l == w - 2), And(w == 30, Or(l == 28, l == 29)))


def _badminton_over(p, q):
    return Or(p >= 30, And(p >= 21, p - q >= 2))


def _alt_badminton_final(w, l):
    """The score ends the game, and the score before the winner's last point did not."""
    return And(l >= 0, l < w, _badminton_over(w, l), Not(_badminton_over(w - 1, l)))


TASKS = [
    Task(
        id="any_peak_index", group=3,
        description="Return the index of any element of the array a that is greater than or equal to each of "
                    "its neighbours (the first and last elements have only one neighbour).",
        params=(("a", ARRAY),), allowed=everything,
        golden_spec=lambda a, r: any_of(And(r == j, _peak(a, j)) for j in range(N)),
        cases=((([1, 3, 2, 4],), 1, True), (([1, 3, 2, 4],), 3, True), (([1, 3, 2, 4],), 0, False),
               (([1, 3, 2, 4],), 2, False), (([5, 5, 5, 5],), 0, True), (([1, 3, 2, 4],), 4, False)),
        ai_z3_alternative=lambda a, r: And(index(r), Implies(r > 0, a[r] >= a[r - 1]), Implies(r < N - 1, a[r] >= a[r + 1])),
    ),
    Task(
        id="any_value_exactly_twice", group=3,
        description="Return any value that occurs exactly twice in the array a, or -1 if no value occurs "
                    "exactly twice.",
        params=(("a", ARRAY),), allowed=everything,
        golden_spec=_exactly_twice_golden,
        cases=((([1, 1, 2, 2],), 1, True), (([1, 1, 2, 2],), 2, True), (([1, 1, 1, 2],), 1, False),
               (([1, 1, 1, 2],), -1, True), (([3, 3, 3, 3],), -1, True), (([1, 2, 1, 2],), 3, False),
               (([1, 1, 2, 2],), -1, False), (([1, 1, 1, 5],), 5, False)),
        ai_z3_alternative=lambda a, r: Or(_occurs_exactly_twice(a, r),
                                          And(r == -1, all_of(Not(_occurs_exactly_twice(a, a[i])) for i in range(N)))),
    ),
    Task(
        id="any_missing_in_range", group=3,
        description="Return any integer x with lo <= x <= hi that does not occur in the array a. You may "
                    "assume hi - lo >= 4.",
        params=(("a", ARRAY), ("lo", INT), ("hi", INT)), allowed=lambda a, lo, hi: hi - lo >= 4,
        golden_spec=lambda a, lo, hi, r: And(lo <= r, r <= hi, all_of(a[j] != r for j in range(N))),
        cases=((([1, 2, 3, 4], 0, 4), 0, True), (([0, 1, 2, 3], 0, 4), 4, True), (([0, 1, 2, 3], 0, 4), 2, False),
               (([0, 1, 2, 3], 0, 4), 5, False), (([9, 9, 9, 9], 0, 4), 9, False)),
        ai_z3_alternative=lambda a, lo, hi, r: Not(Or(r < lo, r > hi, any_of(a[j] == r for j in range(N)))),
    ),
    Task(
        id="any_adjacent_duplicate", group=3,
        description="Return any index i such that a[i] equals a[i + 1], or -1 if no two neighbouring elements "
                    "of the array a are equal.",
        params=(("a", ARRAY),), allowed=everything,
        golden_spec=lambda a, r: Or(any_of(And(r == j, a[j] == a[j + 1]) for j in range(N - 1)),
                                    And(r == -1, all_of(a[j] != a[j + 1] for j in range(N - 1)))),
        cases=((([1, 1, 2, 2],), 0, True), (([1, 1, 2, 2],), 2, True), (([1, 1, 2, 2],), 1, False),
               (([1, 1, 2, 2],), -1, False), (([1, 2, 1, 2],), -1, True), (([1, 2, 1, 2],), 0, False),
               (([3, 3, 3, 3],), 3, False)),
        ai_z3_alternative=lambda a, r: Or(And(0 <= r, r <= N - 2, a[r] == a[r + 1]),
                                          And(r == -1, Not(any_of(a[j] == a[j + 1] for j in range(N - 1))))),
    ),
    Task(
        id="any_index_not_extreme", group=3,
        description="Return the index of any element of the array a that is neither a smallest nor a largest "
                    "element of a, or -1 if every element is a smallest or a largest one.",
        params=(("a", ARRAY),), allowed=everything,
        golden_spec=_not_extreme_golden,
        cases=((([1, 2, 3, 4],), 1, True), (([1, 2, 3, 4],), 2, True), (([1, 2, 3, 4],), 0, False),
               (([1, 1, 4, 4],), -1, True), (([1, 1, 4, 4],), 1, False), (([5, 5, 5, 5],), -1, True),
               (([3, 1, 2, 3],), 2, True), (([3, 1, 2, 3],), 0, False), (([1, 2, 3, 4],), -1, False)),
        ai_z3_alternative=_alt_not_extreme,
    ),
    Task(
        id="any_repeated_value", group=3,
        description="Return any value that occurs at least twice in the array a. You may assume such a value "
                    "exists.",
        params=(("a", ARRAY),), allowed=lambda a: any_of(a[i] == a[j] for i, j in pairs()),
        golden_spec=lambda a, r: count(lambda j: a[j] == r) >= 2,
        cases=((([1, 2, 1, 3],), 1, True), (([1, 2, 1, 3],), 2, False), (([4, 4, 5, 5],), 5, True),
               (([4, 4, 5, 5],), 4, True), (([4, 4, 5, 5],), 6, False)),
        ai_z3_alternative=lambda a, r: any_of(And(a[i] == r, a[j] == r) for i, j in pairs()),
    ),
    Task(
        id="any_split_value", group=3,
        description="Return any integer r such that exactly two elements of the array a are smaller than r. "
                    "You may assume the elements of a are all different.",
        params=(("a", ARRAY),), allowed=lambda a: all_of(a[i] != a[j] for i, j in pairs()),
        golden_spec=lambda a, r: count(lambda j: a[j] < r) == 2,
        cases=((([1, 5, 3, 9],), 4, True), (([1, 5, 3, 9],), 5, True), (([1, 5, 3, 9],), 3, False),
               (([1, 5, 3, 9],), 6, False), (([10, 20, 30, 40],), 25, True)),
        ai_z3_alternative=_alt_split_value,
    ),
    Task(
        id="any_even_in_range", group=3,
        description="Return any even integer x with lo <= x <= hi. You may assume such an integer exists.",
        params=(("lo", INT), ("hi", INT)), allowed=lambda lo, hi: And(lo <= hi, Or(hi - lo >= 1, lo % 2 == 0)),
        golden_spec=lambda lo, hi, r: And(lo <= r, r <= hi, r % 2 == 0),
        cases=(((3, 7), 4, True), ((3, 7), 6, True), ((3, 7), 5, False), ((3, 7), 8, False), ((-3, -1), -2, True),
               ((4, 4), 4, True)),
        ai_z3_alternative=lambda lo, hi, r: And(lo <= r, r <= hi, Exists([Int("q_even")], r == 2 * Int("q_even"))),
    ),
    Task(
        id="badminton_losing_score", group=3,
        description="In a badminton game, a side wins as soon as it has at least 21 points and at least 2 points "
                    "more than the other side, or as soon as it reaches 30 points; no points are played after "
                    "that. The winner finished the game with p points. Return any number of points the loser "
                    "could have finished with. You may assume 21 <= p <= 30.",
        params=(("p", INT),), allowed=lambda p: And(21 <= p, p <= 30),
        golden_spec=_badminton_final,
        cases=(((21,), 0, True), ((21,), 19, True), ((21,), 20, False), ((25,), 23, True), ((25,), 22, False),
               ((30,), 28, True), ((30,), 29, True), ((30,), 27, False), ((22,), 20, True), ((22,), 19, False)),
        ai_z3_alternative=_alt_badminton_final,
    ),
    Task(
        id="any_index_at_least_mean", group=3,
        description="Return the index of any element of the array a that is greater than or equal to the "
                    "average of all elements of a.",
        params=(("a", ARRAY),), allowed=everything,
        golden_spec=lambda a, r: any_of(And(r == j, N * a[j] >= _array_sum(a)) for j in range(N)),
        cases=((([1, 2, 3, 10],), 3, True), (([1, 2, 3, 10],), 2, False), (([2, 2, 2, 3],), 3, True),
               (([2, 2, 2, 3],), 0, False), (([5, 5, 5, 5],), 1, True), (([1, 2, 3, 10],), 4, False)),
        ai_z3_alternative=lambda a, r: And(index(r), N * a[r] >= _array_sum(a)),
    ),
]
