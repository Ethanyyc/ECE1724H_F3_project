"""Group 1: integer functions with subtle semantics (rounding direction,
negative numbers, degenerate cases, calendar rules, digits, game rules). One
correct answer each.

Three tasks target weaknesses the spec writer showed (the digits of a negative
number, rounding negative halves, and numbers with fewer than four digits);
they replaced c_remainder5, clamp_unordered and count_leap_years, which it
always got right. tennis_game replaced swap_first_last_digit, a fourth digit
task: its valid inputs, the scores that can occur in a game, have to be worked
out from the rules, and the writer assumed that a game always ends with a lead
of exactly 2 (which rules out 4-0 and 4-1).

Each task has a golden program, hand-picked cases and an AI-written Z3
alternative with exactly one answer per input, written in a different way;
benchmarks/verify.py checks the golden program against the alternative (in the
tests).
"""

from z3 import And, BoolVal, If, Implies, IntVal, Not, Or, Sum

from speccheck.tasks import INT, Task


# Z3 helpers

def everything(*_):
    return BoolVal(True)


def zmin(x, y):
    return If(x <= y, x, y)


def zmax(x, y):
    return If(x >= y, x, y)


def zabs(x):
    return If(x >= 0, x, -x)


def total(items):
    items = list(items)
    return Sum(items) if items else IntVal(0)


def leap(y):
    return Or(And(y % 4 == 0, y % 100 != 0), y % 400 == 0)


# golden programs

def _trunc_div3(x):
    return If(x >= 0, x / 3, -((-x) / 3))


def _digit_sum_signed(x):
    u = zabs(x)
    return total((u / 10 ** i) % 10 for i in range(4))


def _round_quarter_half_away(x):
    return If(x >= 0, (x + 2) / 4, -((-x + 2) / 4))


def _round_half_even(x):
    q = x / 2                                   # floor(x / 2): Z3 integer division by a positive constant
    return If(x % 2 == 0, q, If(q % 2 == 0, q, q + 1))


def _triangle_kind(a, b, c):
    valid = And(a > 0, b > 0, c > 0, a + b > c, a + c > b, b + c > a)
    kind = If(And(a == b, b == c), 3, If(Or(a == b, b == c, a == c), 2, 1))
    return If(valid, kind, 0)


def _days_in_month(m, y):
    return If(m == 2, If(leap(y), 29, 28), If(Or(m == 4, m == 6, m == 9, m == 11), 30, 31))


def _closest_to_zero(a, b):
    return If(zabs(a) < zabs(b), a, If(zabs(b) < zabs(a), b, zmax(a, b)))


def _median_of_four(a, b, c, d):
    return zmin(zmax(zmin(a, b), zmin(c, d)), zmin(zmax(a, b), zmax(c, d)))


def _reverse_digits(x):
    d0, d1, d2, d3 = x % 10, (x / 10) % 10, (x / 100) % 10, x / 1000
    return If(x >= 1000, 1000 * d0 + 100 * d1 + 10 * d2 + d3,
              If(x >= 100, 100 * d0 + 10 * d1 + d2,
                 If(x >= 10, 10 * d0 + d1, x)))


def _won(p, q):
    """p points beat q points in a tennis game: at least 4 points and at least 2 more."""
    return And(p >= 4, p - q >= 2)


def _tennis_score_possible(p, q):
    """p-q can occur in a game: the game is in progress, or its last point has just won it."""
    in_progress = And(Not(_won(p, q)), Not(_won(q, p)))
    a_just_won = And(_won(p, q), Not(_won(p - 1, q)))
    b_just_won = And(_won(q, p), Not(_won(q - 1, p)))
    return And(p >= 0, q >= 0, Or(in_progress, a_just_won, b_just_won))


def _tennis_game(p, q):
    return If(_won(p, q), 1, If(_won(q, p), 2, 0))


# AI-written Z3 alternatives (exactly one answer per allowed input)

def _alt_triangle_kind(a, b, c, r):
    largest = zmax(a, zmax(b, c))
    valid = And(a > 0, b > 0, c > 0, a + b + c > 2 * largest)
    equal_pairs = total([If(a == b, 1, 0), If(b == c, 1, 0), If(a == c, 1, 0)])
    return r == If(Not(valid), 0, If(equal_pairs == 3, 3, If(equal_pairs == 1, 2, 1)))


def _alt_median_of_four(a, b, c, d, r):
    values = (a, b, c, d)
    below = total(If(v < r, 1, 0) for v in values)
    at_most = total(If(v <= r, 1, 0) for v in values)
    return And(Or([r == v for v in values]), below <= 1, at_most >= 2)


def _alt_days_in_month(m, y):
    long_month = Or(m == 1, m == 3, m == 5, m == 7, m == 8, m == 10, m == 12)
    leap_year = Or(y % 400 == 0, And(y % 4 == 0, Not(y % 100 == 0)))
    return If(long_month, 31, If(m == 2, 28 + If(leap_year, 1, 0), 30))


def _alt_tennis_game(p, q, r):
    """r names the winner, if there is one."""
    return And(Or(r == 0, r == 1, r == 2), (r == 1) == And(p >= 4, p >= q + 2), (r == 2) == And(q >= 4, q >= p + 2))


def _alt_reverse_digits(x, r):
    """Moves the last digit of what is left onto the result, four times."""
    result, rest = 0, x
    for _ in range(4):
        result = If(rest > 0, 10 * result + rest % 10, result)
        rest = rest / 10
    return r == result


TASKS = [
    Task(
        id="trunc_div3", group=1,
        description="Return x divided by 3, rounded toward zero (for example, 7 gives 2 and -7 gives -2).",
        params=(("x", INT),), allowed=everything,
        golden_program=_trunc_div3,
        cases=(((7,), 2), ((-7,), -2), ((6,), 2), ((-6,), -2), ((0,), 0), ((-1,), 0), ((2,), 0)),
        ai_z3_alternative=lambda x, r: If(x >= 0, And(3 * r <= x, x < 3 * r + 3), And(3 * r - 3 < x, x <= 3 * r)),
    ),
    Task(
        id="digit_sum_signed", group=1,
        description="Return the sum of the decimal digits of x (for example, 1234 gives 10). You may assume "
                    "-9999 <= x <= 9999.",
        params=(("x", INT),), allowed=lambda x: And(-9999 <= x, x <= 9999),
        golden_program=_digit_sum_signed,
        cases=(((1234,), 10), ((-1234,), 10), ((0,), 0), ((-7,), 7), ((9999,), 36), ((-90,), 9), ((105,), 6),
               ((-1,), 1)),
        # n minus 9 times (n // 10 + n // 100 + n // 1000) is the digit sum of 0 <= n <= 9999
        ai_z3_alternative=lambda x, r: r == zabs(x) - 9 * (zabs(x) / 10 + zabs(x) / 100 + zabs(x) / 1000),
    ),
    Task(
        id="round_half_even", group=1,
        description="Return x / 2 rounded to the nearest integer; when x / 2 is exactly halfway between two "
                    "integers, round to the even one (for example, 5 gives 2, 7 gives 4, and -5 gives -2).",
        params=(("x", INT),), allowed=everything,
        golden_program=_round_half_even,
        cases=(((5,), 2), ((7,), 4), ((-5,), -2), ((-7,), -4), ((4,), 2), ((1,), 0), ((-1,), 0), ((3,), 2),
               ((-3,), -2)),
        ai_z3_alternative=lambda x, r: And(Or(2 * r - x == 0, 2 * r - x == 1, 2 * r - x == -1),
                                           Implies(2 * r - x != 0, r % 2 == 0)),
    ),
    Task(
        id="round_quarter_half_away", group=1,
        description="Return x / 4 rounded to the nearest integer; when x / 4 is exactly halfway between two "
                    "integers, round away from zero (for example, 6 gives 2 and 5 gives 1).",
        params=(("x", INT),), allowed=everything,
        golden_program=_round_quarter_half_away,
        cases=(((6,), 2), ((5,), 1), ((7,), 2), ((2,), 1), ((-6,), -2), ((-5,), -1), ((-7,), -2), ((-2,), -1),
               ((0,), 0), ((1,), 0), ((-1,), 0)),
        ai_z3_alternative=lambda x, r: And(zabs(4 * r - x) <= 2,
                                           Implies(zabs(4 * r - x) == 2, zabs(4 * r) > zabs(x))),
    ),
    Task(
        id="triangle_kind", group=1,
        description="The integers a, b and c are the lengths of three line segments. Return 3 if they form an "
                    "equilateral triangle, 2 if they form an isosceles triangle that is not equilateral, 1 if "
                    "they form a triangle whose three sides all differ, and 0 if they do not form a triangle "
                    "with positive area. You may assume a, b and c are non-negative.",
        params=(("a", INT), ("b", INT), ("c", INT)), allowed=lambda a, b, c: And(a >= 0, b >= 0, c >= 0),
        golden_program=_triangle_kind,
        cases=(((3, 3, 3), 3), ((3, 3, 5), 2), ((5, 3, 3), 2), ((3, 4, 5), 1), ((1, 2, 3), 0), ((2, 2, 5), 0),
               ((0, 0, 0), 0), ((0, 2, 2), 0)),
        ai_z3_alternative=_alt_triangle_kind,
    ),
    Task(
        id="days_in_month", group=1,
        description="Return the number of days in month m of year y in the Gregorian calendar (m = 1 is "
                    "January and m = 12 is December). You may assume 1 <= m <= 12 and y >= 1.",
        params=(("m", INT), ("y", INT)), allowed=lambda m, y: And(1 <= m, m <= 12, y >= 1),
        golden_program=_days_in_month,
        cases=(((1, 2023), 31), ((2, 2023), 28), ((2, 2024), 29), ((2, 1900), 28), ((2, 2000), 29),
               ((4, 2023), 30), ((12, 1), 31)),
        ai_z3_alternative=lambda m, y, r: r == _alt_days_in_month(m, y),
    ),
    Task(
        id="closest_to_zero", group=1,
        description="Return whichever of a and b is closer to zero. If they are equally close to zero but "
                    "different, return the positive one.",
        params=(("a", INT), ("b", INT)), allowed=everything,
        golden_program=_closest_to_zero,
        cases=(((3, -5), 3), ((-3, 5), -3), ((4, -4), 4), ((-4, 4), 4), ((0, 7), 0), ((-2, -2), -2), ((6, 2), 2)),
        ai_z3_alternative=lambda a, b, r: And(Or(r == a, r == b), zabs(r) <= zabs(a), zabs(r) <= zabs(b),
                                              Implies(zabs(a) == zabs(b), And(r >= a, r >= b))),
    ),
    Task(
        id="median_of_four", group=1,
        description="Return the second smallest of the four integers a, b, c and d, where equal values count "
                    "separately (for example, 4, 1, 1, 9 gives 1).",
        params=(("a", INT), ("b", INT), ("c", INT), ("d", INT)), allowed=everything,
        golden_program=_median_of_four,
        cases=(((4, 1, 1, 9), 1), ((4, 1, 3, 2), 2), ((5, 5, 1, 1), 1), ((2, 2, 2, 9), 2), ((9, 8, 7, 6), 7),
               ((-1, -3, 0, -3), -3)),
        ai_z3_alternative=_alt_median_of_four,
    ),
    Task(
        id="tennis_game", group=1,
        description="In a tennis game, player A has won p points and player B has won q points. A player wins "
                    "the game as soon as they have at least 4 points and at least 2 points more than the other "
                    "player, and no points are played after that. Return 1 if A has won, 2 if B has won, and 0 if "
                    "the game is not over. You may assume p and q are possible scores of such a game.",
        params=(("p", INT), ("q", INT)), allowed=_tennis_score_possible,
        golden_program=_tennis_game,
        cases=(((0, 0), 0), ((4, 0), 1), ((4, 2), 1), ((3, 3), 0), ((5, 3), 1), ((4, 5), 0), ((6, 8), 2),
               ((1, 4), 2), ((7, 7), 0)),
        ai_z3_alternative=_alt_tennis_game,
    ),
    Task(
        id="reverse_digits", group=1,
        description="Return the integer whose decimal digits are the digits of x in reverse order; leading "
                    "zeros of the result are dropped (for example, 1200 gives 21). You may assume "
                    "0 <= x <= 9999.",
        params=(("x", INT),), allowed=lambda x: And(0 <= x, x <= 9999),
        golden_program=_reverse_digits,
        cases=(((1234,), 4321), ((1200,), 21), ((5,), 5), ((0,), 0), ((10,), 1), ((907,), 709), ((9999,), 9999)),
        ai_z3_alternative=_alt_reverse_digits,
    ),
]
