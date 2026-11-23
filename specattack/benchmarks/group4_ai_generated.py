"""Group 4: AI-generated very hard tasks (20).

Purpose: more data points for RQ2 and RQ3, which need too-weak specs to attack
and repair. On Groups 1 to 3 the spec writer wrote correct specs for almost
every task, so Group 4 targets the kinds of task on which it did fail. Tasks of
this difficulty are hard to write by hand, so an AI assistant drafted them, and
we reviewed every task ourselves and with Claude Opus 5.5. Every golden
reference is also checked against an AI-written Z3 alternative over all
integers, on hand-picked cases, and by mutation tests.

Group 4 is selected adversarially, so its defect rates are reported apart from
Groups 1 to 3. How it was built:

1. A first version had 5 classic algorithm traps and 15 tasks aimed at the
   failures seen on Groups 1 to 3. In Exp 1 the spec writer got 14 of those 20
   tasks right in every repeat.
2. The failures came from tasks on which a formula for exactly four digits
   looks complete (reversal, palindromes: `1000*d0 + 100*d1 + 10*d2 + d3`).
   Where the wording made it find the first digit, or where an example showed a
   short number, it handled shorter numbers correctly.
3. The second version kept the 6 tasks that failed or relied on such an
   example, with examples that use four-digit numbers only, and added 14 tasks
   on which a fixed-width formula looks complete (reversing, mirroring,
   rotating and comparing digits in base 10 and base 3, a 6-bit two's
   complement representation and an unusual tie-break).
4. The writer still got 15 of those 20 tasks right. It failed where a reversal
   is part of a larger question and on a tie-break, and handled plain
   palindromes and reversals in other bases. The third version kept the 5
   failures and 5 other tasks, and replaced the 10 tasks it always got right
   with tasks where the reversal or the number of digits is hidden inside
   another question (reversing twice; the digit count, divisibility by 4 and
   first digit of a reversal; the reversal written in front of x; reversing
   x + 1; deleting the first digit; a digit position counted from the left)
   and two array tasks with a last-occurrence tie-break.
5. Almost every failure in the third version was on a digit task. This version
   replaces six digit tasks (reverse_and_add, reverse_twice,
   reversal_digit_count, first_digit_of_reversal, prepend_reversal and
   remove_first_digit) with tasks in which a fact has to be worked out from a
   rule: which scores can occur in a table tennis game, when a coin-saving
   process can stop, which rolls a bowling game can have, how far a bishop has
   to travel, how many rows a calendar month needs and how long a Roman numeral
   is. In screening runs the writer failed the first two: it assumed that a
   game ends with a lead of exactly 2, and limited the days of the coin jar to
   1 to 5 although the task asks for 0 on any other input.

Decimal inputs have at most four digits: with five, Z3 needed 13 to over 60
seconds to show that two correct formulas agree. Golden programs split on the
number of digits; the Z3 alternatives use a different algorithm (digit-by-digit
loops, counting, declarative conditions, a divisibility rule).
"""

from z3 import And, BoolVal, If, Implies, IntVal, Not, Or, Sum

from speccheck.config import N
from speccheck.tasks import ARRAY, INT, Task

DIGITS = 4
LARGEST = 10 ** DIGITS - 1


# Z3 helpers

def everything(*_):
    return BoolVal(True)


def zmax(x, y):
    return If(x >= y, x, y)


def zabs(x):
    return If(x >= 0, x, -x)


def total(items):
    items = list(items)
    return Sum(items) if items else IntVal(0)


def all_of(items):
    items = list(items)
    return And(items) if items else BoolVal(True)


def any_of(items):
    items = list(items)
    return Or(items) if items else BoolVal(False)


def array_max(a):
    largest = a[0]
    for j in range(1, N):
        largest = zmax(largest, a[j])
    return largest


def index(r):
    return And(0 <= r, r < N)


# digits

def _digit(x, i, base=10):
    return (x / base ** i) % base


def _by_length(x, value_for_length, base=10, longest=DIGITS):
    """value_for_length(n), where n is the number of digits of x >= 0 (0 has one digit)."""
    value = value_for_length(longest)
    for n in range(longest - 1, 0, -1):
        value = If(x < base ** n, value_for_length(n), value)
    return value


def _reverse_by_length(x, base=10, longest=DIGITS):
    return _by_length(x, lambda n: total(_digit(x, i, base) * base ** (n - 1 - i) for i in range(n)), base, longest)


def _reverse_by_steps(x, steps=DIGITS, base=10):
    """Moves the last digit of what is left onto the result, `steps` times."""
    result, rest = 0, x
    for _ in range(steps):
        result = If(rest > 0, base * result + rest % base, result)
        rest = rest / base
    return result


def _insert_5_at(x, p):
    """x with a digit 5 inserted so that p digits of x follow it."""
    return (x / 10 ** p) * 10 ** (p + 1) + 5 * 10 ** p + x % 10 ** p


def _max_after_inserting_5(x):
    def best(n):
        value = _insert_5_at(x, 0)
        for p in range(1, n + 1):
            value = zmax(value, _insert_5_at(x, p))
        return value
    return _by_length(x, best)


def _alt_max_after_inserting_5(x, r):
    """Greedy: insert 5 before the first digit, from the left, that is smaller than 5; else at the end."""
    def greedy(n):
        left = [_digit(x, n - 1 - j) for j in range(n)]
        value = _insert_5_at(x, 0)
        for j in range(n - 1, -1, -1):
            value = If(left[j] < 5, _insert_5_at(x, n - j), value)
        return value
    return r == _by_length(x, greedy)


def _mirror_concat(x):
    return _by_length(x, lambda n: x * 10 ** n + total(_digit(x, i) * 10 ** (n - 1 - i) for i in range(n)))


def _alt_mirror_concat(x, r):
    """Appends the digits of x to x, last digit first."""
    result, rest = x, x
    for _ in range(DIGITS):
        result = If(rest > 0, 10 * result + rest % 10, result)
        rest = rest / 10
    return r == result


def _rotate_digits_right(x):
    return _by_length(x, lambda n: (x % 10) * 10 ** (n - 1) + x / 10)


def _alt_rotate_digits_right(x, r):
    def rotated(n):
        return _digit(x, 0) * 10 ** (n - 1) + total(_digit(x, i) * 10 ** (i - 1) for i in range(1, n))
    return r == _by_length(x, rotated)


def _bits(u, count=8):
    return total(_digit(u, i, 2) for i in range(count))


def _alt_reversal_divisible_by_4(x, r):
    """Divisibility rule: 100 is a multiple of 4, so only the last two digits of the reversal count, and they
    are the first two digits of x in reverse order."""
    def last_two(n):
        if n == 1:
            return _digit(x, 0)
        return 10 * _digit(x, n - 2) + _digit(x, n - 1)
    return r == If(_by_length(x, last_two) % 4 == 0, 1, 0)


def _last_largest_position(x):
    """Position, counted from the left starting at 1, of the last occurrence of the largest digit."""
    def position(n):
        left = [_digit(x, n - 1 - j) for j in range(n)]
        top = left[0]
        for digit in left[1:]:
            top = zmax(top, digit)
        result = 1
        for j in range(n):
            result = If(left[j] == top, j + 1, result)
        return result
    return _by_length(x, position)


def _alt_last_largest_position(x, r):
    """Counting from the right: the first digit that is at least every digit, turned into a position."""
    def holds(n):
        return any_of(And(r == n - k, all_of(_digit(x, k) >= _digit(x, j) for j in range(n)),
                          all_of(_digit(x, j) < _digit(x, k) for j in range(k)))
                      for k in range(n))
    return _by_length(x, holds)


# arrays

def _occurrences(arr, value, upto=N):
    return total(If(arr[t] == value, 1, 0) for t in range(upto))


def _mode_first_to_reach(a):
    """A value reaches its final count at its last occurrence; among the most frequent values, the one whose
    last occurrence comes first wins."""
    counts = [_occurrences(a, a[i]) for i in range(N)]
    top = counts[0]
    for c in counts[1:]:
        top = zmax(top, c)
    result = a[N - 1]
    for i in range(N - 1, -1, -1):
        last = all_of(a[j] != a[i] for j in range(i + 1, N))
        result = If(And(last, counts[i] == top), a[i], result)
    return result


def _alt_mode_first_to_reach(a, r):
    """Read a from left to right; the leader changes only when a count beats the best count so far."""
    best, leader = 0, a[0]
    for j in range(N):
        running = _occurrences(a, a[j], j + 1)
        leader = If(running > best, a[j], leader)
        best = zmax(best, running)
    return r == leader


def _middle_distance(i):
    """Twice the distance of index i from the middle of the array (between indices 1 and 2)."""
    return zabs(2 * i - (N - 1))


def _index_of_max_nearest_middle(a):
    order = sorted(range(N), key=lambda i: (abs(2 * i - (N - 1)), i))      # 1, 2, 0, 3
    top = array_max(a)
    result = order[-1]
    for i in reversed(order[:-1]):
        result = If(a[i] == top, i, result)
    return result


def _alt_index_of_max_nearest_middle(a, r):
    return And(index(r), all_of(a[r] >= a[j] for j in range(N)),
               all_of(Implies(a[j] == a[r], Or(_middle_distance(r) < _middle_distance(j),
                                               And(_middle_distance(r) == _middle_distance(j), r <= j)))
                      for j in range(N)))


def _increasing_lengths(a):
    """lengths[i]: how many elements, from index i on, strictly increase."""
    lengths = [1] * N
    for i in range(N - 2, -1, -1):
        lengths[i] = If(a[i] < a[i + 1], lengths[i + 1] + 1, 1)
    return lengths


def _longest_run_start(a):
    """Only the first index of a run can have the longest length, so the last index that has it is the answer."""
    lengths = _increasing_lengths(a)
    top = lengths[0]
    for length in lengths[1:]:
        top = zmax(top, length)
    result = 0
    for i in range(N):
        result = If(lengths[i] == top, i, result)
    return result


def _alt_longest_run_start(a, r):
    """r starts a strictly increasing segment that no segment is longer than and no later segment matches."""
    def increasing(s, k):
        return all_of(a[s + t] < a[s + t + 1] for t in range(k - 1))
    segments = [(s, k) for s in range(N) for k in range(1, N - s + 1)]
    return any_of(And(r == s0, increasing(s0, k0),
                      all_of(Not(increasing(s, k)) for s, k in segments if k > k0),
                      all_of(Not(increasing(s, k)) for s, k in segments if k == k0 and s > s0))
                  for s0, k0 in segments)


def _local_min(a, j):
    """a[j] is strictly smaller than each of its neighbours (one neighbour at either end)."""
    conditions = []
    if j > 0:
        conditions.append(a[j] < a[j - 1])
    if j < N - 1:
        conditions.append(a[j] < a[j + 1])
    return all_of(conditions)


def _last_local_min_index(a):
    result = -1
    for j in range(N):
        result = If(_local_min(a, j), j, result)
    return result


def _alt_last_local_min_index(a, r):
    """No neighbour of a[r] is smaller or equal to it, and no later element has that property."""
    def no_smaller_neighbour(j):
        return Not(any_of(a[k] <= a[j] for k in (j - 1, j + 1) if 0 <= k < N))
    found = [no_smaller_neighbour(j) for j in range(N)]
    return Or(And(r == -1, all_of(Not(f) for f in found)),
              any_of(And(r == j, found[j], all_of(Not(found[k]) for k in range(j + 1, N))) for j in range(N)))


# rules

def _tt_won(p, q):
    """p points beat q points in a table tennis game: at least 11 points and at least 2 more."""
    return And(p >= 11, p - q >= 2)


def _tt_score_possible(p, q):
    """p-q can occur in a game: the game is in progress, or its last point has just won it."""
    in_progress = And(Not(_tt_won(p, q)), Not(_tt_won(q, p)))
    a_just_won = And(_tt_won(p, q), Not(_tt_won(p - 1, q)))
    b_just_won = And(_tt_won(q, p), Not(_tt_won(q - 1, p)))
    return And(p >= 0, q >= 0, Or(in_progress, a_just_won, b_just_won))


def _table_tennis_game(p, q):
    return If(_tt_won(p, q), 1, If(_tt_won(q, p), 2, 0))


def _alt_table_tennis_game(p, q, r):
    """r names the winner, if there is one."""
    return And(Or(r == 0, r == 1, r == 2),
               (r == 1) == And(p >= 11, p >= q + 2), (r == 2) == And(q >= 11, q >= p + 2))


JAR = ("A child puts 1, 2 or 3 coins into an empty jar each day, starting on day 1, and stops as soon as the jar "
       "holds at least 10 coins or after the 5th day, whichever comes first.")


def _coin_jar_final(t, d):
    return If(Or(And(d == 4, 10 <= t, t <= 12), And(d == 5, 5 <= t, t <= 12)), 1, 0)


def _alt_coin_jar_final(t, d, r):
    """After d days the jar holds d to 3d coins, and at most 12 because it held at most 9 the day before; the
    child has stopped if it holds 10 or more, or after the 5th day."""
    possible = And(1 <= d, d <= 5, d <= t, t <= 3 * d, t <= 12)
    return r == If(And(possible, Or(t >= 10, d == 5)), 1, 0)


def _bowling_rolls_possible(a):
    """Every roll knocks down 0 to 10 pins, and the two rolls of a frame without a strike at most 10."""
    in_range = all_of(And(0 <= a[j], a[j] <= 10) for j in range(N))
    after_strike = If(a[1] == 10, Or(a[2] == 10, a[2] + a[3] <= 10), a[1] + a[2] <= 10)
    after_open = And(a[0] + a[1] <= 10, Or(a[2] == 10, a[2] + a[3] <= 10))
    return And(in_range, If(a[0] == 10, after_strike, after_open))


def _bowling_first_frame(a):
    return If(a[0] == 10, 10 + a[1] + a[2], If(a[0] + a[1] == 10, 10 + a[2], a[0] + a[1]))


def _alt_bowling_first_frame(a, r):
    """The pins of the frame's own rolls plus a bonus: the next two rolls after a strike, the next one after a
    spare."""
    strike = a[0] == 10
    own = If(strike, a[0], a[0] + a[1])
    bonus = If(strike, a[1] + a[2], If(a[0] + a[1] == 10, a[2], 0))
    return r == own + bonus


def _on_board(*values):
    return all_of(And(0 <= v, v <= 7) for v in values)


def _bishop_moves(r1, c1, r2, c2):
    same_square = And(r1 == r2, c1 == c2)
    same_diagonal = Or(r1 - c1 == r2 - c2, r1 + c1 == r2 + c2)
    same_colour = (r1 + c1 + r2 + c2) % 2 == 0
    return If(same_square, 0, If(same_diagonal, 1, If(same_colour, 2, -1)))


def _alt_bishop_moves(r1, c1, r2, c2, r):
    """A bishop moves along diagonals and keeps its colour; on an 8 by 8 board every square of its colour is at
    most two moves away."""
    same_diagonal = zabs(r1 - r2) == zabs(c1 - c2)
    same_colour = (r1 + c1) % 2 == (r2 + c2) % 2
    return r == If(And(r1 == r2, c1 == c2), 0, If(same_diagonal, 1, If(same_colour, 2, -1)))


ROMAN_TENS = (0, 1, 2, 3, 2, 1)                 # symbols in "", X, XX, XXX, XL, L
ROMAN_UNITS = (0, 1, 2, 3, 2, 1, 2, 3, 4, 2)    # symbols in "", I, II, III, IV, V, VI, VII, VIII, IX


def _lookup(table, i):
    value = table[-1]
    for k in range(len(table) - 2, -1, -1):
        value = If(i == k, table[k], value)
    return value


def _roman_length(x):
    return _lookup(ROMAN_TENS, x / 10) + _lookup(ROMAN_UNITS, x % 10)


def _alt_roman_length(x, r):
    """Greedy: write the largest group of symbols that fits (L, XL, X, IX, V, IV, I) until nothing is left."""
    rest, symbols = x, 0
    for value, length in ((50, 1), (40, 2), (10, 1), (9, 2), (5, 1), (4, 2), (1, 1)):
        symbols = symbols + (rest / value) * length
        rest = rest % value
    return r == symbols


def _z3_between(low, high):
    return lambda x: And(low <= x, x <= high)


def _decimal_task(task_id, description, golden_program, cases, alternative, low=0):
    """A task on one integer 0 <= x <= 9999 (or low <= x)."""
    return Task(
        id=task_id, group=4, description=description, params=(("x", INT),),
        allowed=_z3_between(low, LARGEST), golden_program=golden_program, cases=cases,
        ai_z3_alternative=alternative,
    )


TASKS = [
    # kept: the tasks the writer failed in the second version
    Task(
        id="reverse_digits_signed", group=4,
        description="Return the integer whose decimal digits are those of x in reverse order, with the same "
                    "sign as x; leading zeros of the result are dropped (for example, -1200 gives -21). You may "
                    "assume -9999 <= x <= 9999.",
        params=(("x", INT),), allowed=_z3_between(-LARGEST, LARGEST),
        golden_program=lambda x: If(x < 0, -_reverse_by_length(-x), _reverse_by_length(x)),
        cases=(((1200,), 21), ((-1200,), -21), ((7,), 7), ((0,), 0), ((-5,), -5), ((10,), 1), ((-1234,), -4321),
               ((9999,), 9999), ((-90,), -9)),
        ai_z3_alternative=lambda x, r: r == If(x < 0, -_reverse_by_steps(-x), _reverse_by_steps(x)),
    ),
    Task(
        id="mode_first_to_reach", group=4,
        description="Return the value that occurs most often in the array a. If several values occur equally "
                    "often, return the one whose occurrences reach that number first when a is read from left "
                    "to right.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_mode_first_to_reach,
        cases=((([1, 2, 2, 1],), 2), (([3, 1, 3, 1],), 3), (([5, 6, 7, 8],), 5), (([2, 1, 1, 2],), 1),
               (([4, 4, 4, 1],), 4), (([1, 2, 3, 1],), 1), (([7, 8, 8, 7],), 8)),
        ai_z3_alternative=_alt_mode_first_to_reach,
    ),
    _decimal_task(
        "reverse_difference",
        "Return x minus the integer whose decimal digits are those of x in reverse order, with leading zeros "
        "dropped (for example, 2100 gives 2100 - 12 = 2088). You may assume 0 <= x <= 9999.",
        lambda x: x - _reverse_by_length(x),
        (((2100,), 2088), ((0,), 0), ((7,), 0), ((10,), 9), ((21,), 9), ((12,), -9), ((100,), 99),
         ((1234,), -3087)),
        lambda x, r: r == x - _reverse_by_steps(x),
    ),
    _decimal_task(
        "reversal_is_larger",
        "Return 1 if the integer whose decimal digits are those of x in reverse order, with leading zeros "
        "dropped, is larger than x, and 0 otherwise (for example, 1203 gives 1 because 3021 > 1203). You may "
        "assume 0 <= x <= 9999.",
        lambda x: If(_reverse_by_length(x) > x, 1, 0),
        (((1203,), 1), ((0,), 0), ((7,), 0), ((10,), 0), ((12,), 1), ((21,), 0), ((120,), 0), ((9999,), 0)),
        lambda x, r: r == If(_reverse_by_steps(x) > x, 1, 0),
    ),
    # kept: tasks the writer got right, with traps it has not seen in this form
    _decimal_task(
        "max_after_inserting_5",
        "Return the largest integer that can be obtained by inserting one digit 5 into the decimal representation "
        "of x, at the start, at the end or between two digits (for example, 1234 gives 51234). You may assume "
        "0 <= x <= 9999.",
        _max_after_inserting_5,
        (((73,), 753), ((0,), 50), ((9,), 95), ((4,), 54), ((99,), 995), ((1234,), 51234), ((9999,), 99995),
         ((555,), 5555), ((96,), 965)),
        _alt_max_after_inserting_5,
    ),
    _decimal_task(
        "mirror_digits",
        "Return the integer written with the decimal digits of x followed by the same digits in reverse order "
        "(for example, 1203 gives 12033021). You may assume 0 <= x <= 9999.",
        _mirror_concat,
        (((1203,), 12033021), ((0,), 0), ((7,), 77), ((10,), 1001), ((12,), 1221), ((100,), 100001),
         ((9999,), 99999999)),
        _alt_mirror_concat,
    ),
    _decimal_task(
        "rotate_digits_right",
        "Return the integer obtained by moving the last decimal digit of x to the front; leading zeros of the "
        "result are dropped (for example, 1234 gives 4123 and 1230 gives 123). You may assume 0 <= x <= 9999.",
        _rotate_digits_right,
        (((1234,), 4123), ((1230,), 123), ((0,), 0), ((7,), 7), ((12,), 21), ((10,), 1), ((120,), 12),
         ((123,), 312)),
        _alt_rotate_digits_right,
    ),
    Task(
        id="twos_complement_bits", group=4,
        description="Return the number of 1 bits in the 6-bit two's complement representation of x. You may "
                    "assume -32 <= x <= 31.",
        params=(("x", INT),), allowed=_z3_between(-32, 31),
        golden_program=lambda x: _bits(If(x < 0, x + 64, x), 6),
        cases=(((-1,), 6), ((0,), 0), ((1,), 1), ((-32,), 1), ((31,), 5), ((-2,), 5), ((5,), 2), ((-5,), 5)),
        ai_z3_alternative=lambda x, r: r == _bits(x % 64, 6),                  # Z3's % gives 0..63 for negatives too
    ),
    Task(
        id="index_of_max_nearest_middle", group=4,
        description="Return the index of a largest element of the array a. If several elements are largest, "
                    "return the index closest to the middle of the array, which lies between indices 1 and 2; "
                    "if two such indices are equally close, return the smaller one.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_index_of_max_nearest_middle,
        cases=((([5, 5, 5, 5],), 1), (([9, 1, 1, 9],), 0), (([1, 9, 9, 1],), 1), (([1, 2, 9, 9],), 2),
               (([9, 2, 3, 4],), 0), (([1, 2, 3, 9],), 3), (([9, 9, 1, 1],), 1), (([1, 1, 2, 2],), 2)),
        ai_z3_alternative=_alt_index_of_max_nearest_middle,
    ),
    # third version: the reversal or the number of digits is hidden inside another question
    _decimal_task(
        "reversal_divisible_by_4",
        "Write the decimal digits of x in reverse order and drop any leading zeros. Return 1 if the resulting "
        "integer is divisible by 4, and 0 otherwise (for example, 2134 gives 1 because 4312 = 4 * 1078). You may "
        "assume 0 <= x <= 9999.",
        lambda x: If(_reverse_by_length(x) % 4 == 0, 1, 0),
        (((2134,), 1), ((1234,), 0), ((0,), 1), ((12,), 0), ((21,), 1), ((4,), 1), ((40,), 1), ((100,), 0),
         ((6,), 0), ((1200,), 0), ((2100,), 1)),
        _alt_reversal_divisible_by_4,
    ),
    Task(
        id="reverse_of_successor", group=4,
        description="Return the integer whose decimal digits are those of x + 1 in reverse order, with leading "
                    "zeros dropped (for example, 1233 gives 4321). You may assume 0 <= x <= 9998.",
        params=(("x", INT),), allowed=_z3_between(0, LARGEST - 1),
        golden_program=lambda x: _reverse_by_length(x + 1),
        cases=(((1233,), 4321), ((9,), 1), ((0,), 1), ((99,), 1), ((1199,), 21), ((11,), 21), ((9998,), 9999),
               ((19,), 2)),
        ai_z3_alternative=lambda x, r: r == _reverse_by_steps(x + 1),
    ),
    _decimal_task(
        "last_largest_digit_position",
        "Return the position of the largest decimal digit of x, counting positions from the left starting at 1. "
        "If the largest digit occurs more than once, return the position of its last occurrence (for example, "
        "1931 gives 2 and 9399 gives 4). You may assume 0 <= x <= 9999.",
        _last_largest_position,
        (((1931,), 2), ((9399,), 4), ((5,), 1), ((0,), 1), ((99,), 2), ((909,), 3), ((1234,), 4), ((4321,), 1),
         ((30,), 1), ((1000,), 1)),
        _alt_last_largest_position,
    ),
    # new: a tie-break on the last occurrence
    Task(
        id="longest_increasing_run_start", group=4,
        description="A run is a maximal sequence of consecutive elements of the array a that strictly increase "
                    "from left to right; a single element is a run of length 1. Return the index at which the "
                    "longest run starts. If several runs are equally long, return the start of the last one.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_longest_run_start,
        cases=((([1, 2, 1, 2],), 2), (([4, 3, 2, 1],), 3), (([1, 2, 3, 4],), 0), (([1, 3, 2, 4],), 2),
               (([5, 1, 2, 3],), 1), (([1, 1, 1, 1],), 3), (([2, 3, 1, 0],), 0), (([1, 2, 2, 3],), 2)),
        ai_z3_alternative=_alt_longest_run_start,
    ),
    Task(
        id="last_local_min_index", group=4,
        description="Return the index of the last element of the array a that is strictly smaller than each of "
                    "its neighbours; the first and last elements have only one neighbour each. Return -1 if no "
                    "element is.",
        params=(("a", ARRAY),), allowed=everything,
        golden_program=_last_local_min_index,
        cases=((([3, 1, 2, 0],), 3), (([1, 2, 3, 4],), 0), (([4, 3, 2, 1],), 3), (([2, 2, 2, 2],), -1),
               (([1, 0, 0, 1],), -1), (([0, 5, 0, 5],), 2), (([5, 1, 5, 1],), 3), (([2, 1, 1, 3],), -1)),
        ai_z3_alternative=_alt_last_local_min_index,
    ),
    # fourth version: a fact that has to be worked out from a rule
    Task(
        id="table_tennis_game", group=4,
        description="In a table tennis game, player A has p points and player B has q points. A player wins the "
                    "game as soon as they have at least 11 points and at least 2 points more than the other "
                    "player, and no points are played after that. Return 1 if A has won, 2 if B has won, and 0 if "
                    "the game is not over. You may assume p and q are possible scores of such a game.",
        params=(("p", INT), ("q", INT)), allowed=_tt_score_possible,
        golden_program=_table_tennis_game,
        cases=(((0, 0), 0), ((11, 0), 1), ((11, 9), 1), ((10, 10), 0), ((12, 10), 1), ((11, 12), 0),
               ((14, 16), 2), ((3, 11), 2)),
        ai_z3_alternative=_alt_table_tennis_game,
    ),
    Task(
        id="coin_jar_final", group=4,
        description=JAR + " Return 1 if the child could have stopped after d days with t coins in the jar, and 0 "
                          "otherwise.",
        params=(("t", INT), ("d", INT)), allowed=everything,
        golden_program=_coin_jar_final,
        cases=(((10, 4), 1), ((12, 4), 1), ((9, 4), 0), ((13, 5), 0), ((5, 5), 1), ((12, 5), 1), ((4, 5), 0),
               ((10, 3), 0), ((0, 0), 0), ((11, 6), 0)),
        ai_z3_alternative=_alt_coin_jar_final,
    ),
    Task(
        id="bowling_first_frame", group=4,
        description="The array a holds the first four rolls of a game of ten-pin bowling (the number of pins "
                    "knocked down by each roll), in order. Return the score of the first frame, including any "
                    "strike or spare bonus. You may assume a is a possible sequence of rolls.",
        params=(("a", ARRAY),), allowed=_bowling_rolls_possible,
        golden_program=_bowling_first_frame,
        cases=((([10, 3, 4, 2],), 17), (([10, 10, 10, 10],), 30), (([7, 3, 5, 2],), 15), (([3, 4, 10, 2],), 7),
               (([0, 10, 4, 6],), 14), (([0, 0, 0, 0],), 0), (([10, 10, 4, 6],), 24), (([9, 0, 10, 10],), 9)),
        ai_z3_alternative=_alt_bowling_first_frame,
    ),
    Task(
        id="bishop_moves", group=4,
        description="Squares of a chessboard are given as (row, column) with rows and columns from 0 to 7. "
                    "Return the smallest number of moves a bishop needs to go from square (r1, c1) to square "
                    "(r2, c2), or -1 if it cannot get there. You may assume all four numbers are between 0 and 7.",
        params=(("r1", INT), ("c1", INT), ("r2", INT), ("c2", INT)), allowed=_on_board,
        golden_program=_bishop_moves,
        cases=(((0, 0, 0, 0), 0), ((0, 0, 7, 7), 1), ((0, 0, 0, 2), 2), ((0, 0, 0, 1), -1), ((2, 5, 5, 2), 1),
               ((0, 6, 7, 7), 2), ((3, 4, 4, 4), -1)),
        ai_z3_alternative=_alt_bishop_moves,
    ),
    Task(
        id="calendar_rows", group=4,
        description="A wall calendar shows a month as rows of seven days, Monday to Sunday. The month has n days "
                    "and its first day falls on weekday w (0 is Monday, 6 is Sunday). Return how many rows the "
                    "month needs. You may assume 0 <= w <= 6 and 28 <= n <= 31.",
        params=(("w", INT), ("n", INT)), allowed=lambda w, n: And(0 <= w, w <= 6, 28 <= n, n <= 31),
        golden_program=lambda w, n: (w + n + 6) / 7,
        cases=(((0, 28), 4), ((1, 28), 5), ((6, 30), 6), ((5, 31), 6), ((4, 31), 5), ((6, 29), 5), ((0, 31), 5)),
        ai_z3_alternative=lambda w, n, r: And(7 * r >= w + n, 7 * r < w + n + 7),
    ),
    Task(
        id="roman_numeral_length", group=4,
        description="Return the number of symbols in the Roman numeral for x, written in the standard subtractive "
                    "form (for example, 4 is IV and 9 is IX). You may assume 1 <= x <= 50.",
        params=(("x", INT),), allowed=_z3_between(1, 50),
        golden_program=_roman_length,
        cases=(((1,), 1), ((4,), 2), ((8,), 4), ((9,), 2), ((38,), 7), ((49,), 4), ((50,), 1), ((44,), 4),
               ((27,), 5)),
        ai_z3_alternative=_alt_roman_length,
    ),
]
