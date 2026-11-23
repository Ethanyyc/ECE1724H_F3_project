"""Group 2: array problems in the style of MBPP/HumanEval whose specs need
counting, existence and uniqueness conditions, tie-breaking, sentinel results
or edge positions. One correct answer each. Arrays have N = 4 elements; golden
references read only indices 0..N-1.

count_peaks_with_ends targets a weakness the spec writer showed (peaks at the
ends). Two tasks hold game scores, and their valid inputs or results have to be
worked out from the rules: tennis scores that end a game, which the writer
took to always have a lead of exactly 2, and badminton scores, where it
overlooked that the 30-point cap only ends a game that is close. They replaced
circular_max_pair_index and running_max_increases, which it always got right
(as it did majority_value, kth_smallest and first_unique_index, replaced
earlier).

Each task has a golden program, hand-picked cases and an AI-written Z3
alternative written in a different way; benchmarks/verify.py checks that the
two agree."""

from z3 import And, BoolVal, If, Implies, IntVal, Not, Or, Sum

from speccheck.config import N
from speccheck.tasks import ARRAY, Task


# Z3 helpers

def everything(*_):
    return BoolVal(True)


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


def pairs():
    """Index pairs i < j."""
    return [(i, j) for i in range(N) for j in range(i + 1, N)]


def array_max(a):
    largest = a[0]
    for j in range(1, N):
        largest = zmax(largest, a[j])
    return largest


# golden programs

def _second_largest_distinct(a):
    largest = array_max(a)
    second = largest                     # placeholder until a smaller value is seen
    for j in range(N):
        second = If(a[j] < largest, If(second == largest, a[j], zmax(second, a[j])), second)
    return second


def _won(p, q):
    """p points beat q points in a tennis game: at least 4 points and at least 2 more."""
    return And(p >= 4, p - q >= 2)


def _tennis_final(w, l):
    """w-l, winner first, can be the final score of a tennis game: it wins the game, and the score before the
    winner's last point did not."""
    return And(l >= 0, _won(w, l), Not(_won(w - 1, l)))


def _tennis_finished(p, q):
    return Or(_tennis_final(p, q), _tennis_final(q, p))


def _badminton_final(w, l):
    """w-l, winner first, can be the final score of a badminton game."""
    return Or(And(w == 21, 0 <= l, l <= 19), And(22 <= w, w <= 29, l == w - 2), And(w == 30, Or(l == 28, l == 29)))


def _badminton_scores_possible(a, final=_badminton_final):
    return total(If(Or(final(a[i], a[i + 1]), final(a[i + 1], a[i])), 1, 0) for i in (0, 2))


def _strict_peak(a, j):
    conditions = []
    if j > 0:
        conditions.append(a[j] > a[j - 1])
    if j < N - 1:
        conditions.append(a[j] > a[j + 1])
    return all_of(conditions)


def _longest_equal_run(a):
    current, best = 1, 1
    for j in range(1, N):
        current = If(a[j] == a[j - 1], current + 1, 1)
        best = zmax(best, current)
    return best


def _max_subarray_sum(a):
    current, best = a[0], a[0]
    for j in range(1, N):
        current = zmax(a[j], current + a[j])
        best = zmax(best, current)
    return best


def _left(a, j):
    return total(a[i] for i in range(j))


def _right(a, j):
    return total(a[i] for i in range(j + 1, N))


def _pivot_index(a):
    result = -1
    for j in reversed(range(N)):         # backwards, so the smallest index wins
        result = If(_left(a, j) == _right(a, j), j, result)
    return result


def _run(a, start, length):
    return all_of(a[start + t] == a[start] for t in range(length))


def _segment_sum(a, i, j):
    return total(a[t] for t in range(i, j))


def _segments():
    return [(i, j) for i in range(N) for j in range(i + 1, N + 1)]


# AI-written Z3 alternatives (exactly one answer per allowed input)

def _alt_second_largest_distinct(a, r):
    return And(any_of(a[j] == r for j in range(N)), any_of(a[j] > r for j in range(N)),
               all_of(Implies(And(a[i] > r, a[j] > r), a[i] == a[j]) for i in range(N) for j in range(N)))


def _alt_count_peaks(a, r):
    """All indices minus those with a neighbour at least as large."""
    def neighbours(j):
        return [k for k in (j - 1, j + 1) if 0 <= k < N]
    return r == N - total(If(any_of(a[k] >= a[j] for k in neighbours(j)), 1, 0) for j in range(N))


def _badminton_over(p, q):
    return Or(p >= 30, And(p >= 21, p - q >= 2))


def _alt_badminton_final(w, l):
    """The score ends the game, and the score before the winner's last point did not."""
    return And(l >= 0, l < w, _badminton_over(w, l), Not(_badminton_over(w - 1, l)))


def _alt_longest_equal_run(a, r):
    runs = [(i, length) for length in range(1, N + 1) for i in range(N - length + 1)]
    return And(any_of(And(r == length, _run(a, i, length)) for i, length in runs),
               all_of(Implies(_run(a, i, length), length <= r) for i, length in runs))


def _alt_max_subarray_sum(a, r):
    sums = [_segment_sum(a, i, j) for i, j in _segments()]
    return And(any_of(r == s for s in sums), all_of(s <= r for s in sums))


def _alt_pivot_index(a, r):
    balanced = [_left(a, j) == _right(a, j) for j in range(N)]
    return Or(And(r == -1, all_of(Not(b) for b in balanced)),
              any_of(And(r == j, balanced[j], all_of(Not(balanced[i]) for i in range(j))) for j in range(N)))


TASKS = [
    Task(
        id="second_largest_distinct", group=2,
        description="Return the second largest distinct value in the array a: the largest value in a that is "
                    "strictly smaller than the maximum of a. You may assume a contains at least two different "
                    "values.",
        params=(("a", ARRAY),), allowed=lambda a: any_of(a[i] != a[j] for i, j in pairs()),
        golden_program=_second_largest_distinct,
        cases=((([3, 9, 2, 9],), 3), (([5, 5, 1, 5],), 1), (([-1, -2, -3, -4],), -2), (([7, 7, 7, 8],), 7),
               (([4, 1, 4, 2],), 2)),
        ai_z3_alternative=_alt_second_largest_distinct,
    ),
    Task(
        id="tennis_games_won", group=2,
        description="The array a holds the final scores of two finished tennis games: a[0] and a[1] are the "
                    "points of players A and B in the first game, and a[2] and a[3] in the second. A player wins "
                    "a game as soon as they have at least 4 points and at least 2 points more than the other "
                    "player, and no points are played after that. Return the number of games A won. You may "
                    "assume both scores are possible final scores of such games.",
        params=(("a", ARRAY),), allowed=lambda a: And(_tennis_finished(a[0], a[1]), _tennis_finished(a[2], a[3])),
        golden_program=lambda a: If(a[0] > a[1], 1, 0) + If(a[2] > a[3], 1, 0),
        cases=((([4, 0, 0, 4],), 1), (([4, 2, 5, 3],), 2), (([3, 5, 2, 4],), 0), (([7, 5, 4, 1],), 2),
               (([1, 4, 8, 6],), 1), (([4, 1, 6, 8],), 1)),
        ai_z3_alternative=lambda a, r: r == If(_won(a[0], a[1]), 1, 0) + If(_won(a[2], a[3]), 1, 0),
    ),
    Task(
        id="count_peaks_with_ends", group=2,
        description="Return the number of peaks in the array a. An element is a peak if it is strictly greater "
                    "than each of its neighbours; the first and last elements have only one neighbour each.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=lambda a: total(If(_strict_peak(a, j), 1, 0) for j in range(N)),
        cases=((([1, 3, 2, 4],), 2), (([5, 5, 5, 5],), 0), (([4, 1, 1, 4],), 2), (([1, 2, 3, 4],), 1),
               (([3, 2, 1, 0],), 1), (([1, 2, 2, 1],), 0), (([2, 1, 2, 1],), 2)),
        ai_z3_alternative=_alt_count_peaks,
    ),
    Task(
        id="longest_equal_run", group=2,
        description="Return the length of the longest stretch of consecutive positions of the array a that all "
                    "hold the same value.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_longest_equal_run,
        cases=((([1, 1, 2, 2],), 2), (([3, 3, 3, 1],), 3), (([1, 2, 3, 4],), 1), (([5, 5, 5, 5],), 4),
               (([2, 1, 1, 2],), 2)),
        ai_z3_alternative=_alt_longest_equal_run,
    ),
    Task(
        id="max_subarray_sum", group=2,
        description="Return the largest sum of a non-empty stretch of consecutive elements of the array a.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_max_subarray_sum,
        cases=((([1, -2, 3, 4],), 7), (([-3, -1, -2, -5],), -1), (([2, 2, -10, 3],), 4), (([0, 0, 0, 0],), 0),
               (([5, -1, -1, 5],), 8)),
        ai_z3_alternative=_alt_max_subarray_sum,
    ),
    Task(
        id="pivot_index", group=2,
        description="Return the smallest index i such that the sum of the elements before position i equals "
                    "the sum of the elements after position i (an empty side sums to 0), or -1 if there is no "
                    "such index.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_pivot_index,
        cases=((([2, 5, 1, 1],), 1), (([0, 0, 0, 0],), 0), (([1, 2, 3, 4],), -1), (([4, -4, 0, 0],), 2),
               (([-1, 3, -1, 0],), 1)),
        ai_z3_alternative=_alt_pivot_index,
    ),
    Task(
        id="count_inversions", group=2,
        description="Return the number of pairs of positions i < j in the array a such that a[i] > a[j].",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=lambda a: total(If(a[i] > a[j], 1, 0) for i, j in pairs()),
        cases=((([1, 2, 3, 4],), 0), (([4, 3, 2, 1],), 6), (([2, 1, 2, 1],), 3), (([5, 5, 5, 5],), 0)),
        ai_z3_alternative=lambda a, r: r == len(pairs()) - total(If(a[i] <= a[j], 1, 0) for i, j in pairs()),
    ),
    Task(
        id="count_distinct", group=2,
        description="Return the number of different values that occur in the array a.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=lambda a: total(If(all_of(a[j] != a[i] for i in range(j)), 1, 0) for j in range(N)),
        cases=((([1, 2, 3, 4],), 4), (([1, 1, 1, 1],), 1), (([1, 2, 1, 2],), 2), (([3, 1, 3, 2],), 3)),
        ai_z3_alternative=lambda a, r: r == total(If(all_of(a[j] != a[i] for i in range(j + 1, N)), 1, 0)
                                                  for j in range(N)),
    ),
    Task(
        id="is_mountain", group=2,
        description="Return 1 if the array a strictly increases up to a peak and strictly decreases after it, "
                    "where the peak is neither the first nor the last element; otherwise return 0.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=lambda a: If(Or(And(a[0] < a[1], a[1] > a[2], a[2] > a[3]),
                                       And(a[0] < a[1], a[1] < a[2], a[2] > a[3])), 1, 0),
        cases=((([1, 3, 2, 1],), 1), (([1, 2, 3, 1],), 1), (([1, 2, 2, 1],), 0), (([3, 2, 1, 0],), 0),
               (([1, 2, 3, 4],), 0), (([0, 5, 5, 0],), 0), (([2, 3, 1, 4],), 0)),
        ai_z3_alternative=lambda a, r: And(Or(r == 0, r == 1),
                                           (r == 1) == And(a[0] < a[1], a[2] > a[3], a[1] != a[2])),
    ),
    Task(
        id="badminton_scores_possible", group=2,
        description="In a badminton game, a side wins as soon as it has at least 21 points and at least 2 points "
                    "more than the other side, or as soon as it reaches 30 points; no points are played after "
                    "that. The array a holds two scores: a[0] to a[1], and a[2] to a[3]. Return how many of the "
                    "two could be the final score of a finished game (with either side winning). You may assume "
                    "all elements are non-negative.",
        params=(("a", ARRAY),), allowed=lambda a: all_of(a[j] >= 0 for j in range(N)),
        golden_program=_badminton_scores_possible,
        cases=((([21, 19, 30, 29],), 2), (([21, 20, 30, 8],), 0), (([23, 21, 19, 21],), 2), (([31, 29, 0, 21],), 1),
               (([29, 20, 30, 28],), 1), (([0, 0, 22, 20],), 1), (([30, 27, 32, 30],), 0)),
        ai_z3_alternative=lambda a, r: r == _badminton_scores_possible(a, _alt_badminton_final),
    ),
]
