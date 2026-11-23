"""Hand-written spec and program code used by the unit tests. They exercise the
same loader and checks as LLM replies."""

CORRECT = {
    "min2": """
def pre(a, b):
    return True

def post(a, b, r):
    return And(r <= a, r <= b, Or(r == a, r == b))
""",
    "clamp": """
def pre(lo, hi, x):
    return lo <= hi

def post(lo, hi, x, r):
    return And(Implies(x < lo, r == lo), Implies(x > hi, r == hi), Implies(lo <= x <= hi, r == x))
""",
    "count_eq": """
def pre(a, k):
    return True

def post(a, k, r):
    return r == Sum([If(a[j] == k, 1, 0) for j in range(N)])
""",
    "argmax_first": """
def pre(a):
    return True

def post(a, r):
    i = Int('i')
    return And(0 <= r, r < N,
               ForAll([i], Implies(And(0 <= i, i < N), a[i] <= a[r])),
               ForAll([i], Implies(And(0 <= i, i < r), a[i] < a[r])))
""",
    "above_both": """
def pre(a, b):
    return True

def post(a, b, r):
    return And(r > a, r > b)
""",
    "any_index_of_max": """
def pre(a):
    return True

def post(a, r):
    i = Int('i')
    return And(0 <= r, r < N, ForAll([i], Implies(And(0 <= i, i < N), a[i] <= a[r])))
""",
    "insert_pos": """
from z3 import *

def pre(a: list, k: int) -> BoolRef:
    \"\"\"a is sorted.\"\"\"
    return And([a[j] <= a[j + 1] for j in range(N - 1)])

def post(a, k, r):
    return r == Sum(If(a[j] < k, 1, 0) for j in range(N))
""",
    # benchmark tasks
    "trunc_div3": """
def pre(x):
    return True

def post(x, r):
    return If(x >= 0, And(3 * r <= x, x < 3 * r + 3), And(3 * r - 3 < x, x <= 3 * r))
""",
    "median_of_four": """
def pre(a, b, c, d):
    return True

def post(a, b, c, d, r):
    below = Sum([If(a < r, 1, 0), If(b < r, 1, 0), If(c < r, 1, 0), If(d < r, 1, 0)])
    at_most = Sum([If(a <= r, 1, 0), If(b <= r, 1, 0), If(c <= r, 1, 0), If(d <= r, 1, 0)])
    return And(Or(r == a, r == b, r == c, r == d), below <= 1, at_most >= 2)
""",
    "count_inversions": """
def pre(a):
    return True

def post(a, r):
    return r == Sum([If(a[i] > a[j], 1, 0) for i in range(N) for j in range(i + 1, N)])
""",
    "second_largest_distinct": """
def pre(a):
    i, j = Ints('i j')
    return Exists([i, j], And(0 <= i, i < N, 0 <= j, j < N, a[i] != a[j]))

def post(a, r):
    i, j = Ints('i j')
    in_a = Exists([i], And(0 <= i, i < N, a[i] == r))
    some_bigger = Exists([i], And(0 <= i, i < N, a[i] > r))
    bigger_equal = ForAll([i, j], Implies(And(0 <= i, i < N, 0 <= j, j < N, a[i] > r, a[j] > r), a[i] == a[j]))
    return And(in_a, some_bigger, bigger_equal)
""",
    "any_even_in_range": """
def pre(lo, hi):
    return And(lo <= hi, Or(hi - lo >= 1, lo % 2 == 0))

def post(lo, hi, r):
    return And(lo <= r, r <= hi, r % 2 == 0)
""",
    "any_index_at_least_mean": """
def pre(a):
    return True

def post(a, r):
    total = Sum([a[j] for j in range(N)])
    return And(0 <= r, r < N, N * a[r] >= total)
""",
    # Group 4: a correct spec in the style of the spec writer, structured differently from the golden reference
    "reverse_digits_signed": """
def pre(x):
    return And(x >= -9999, x <= 9999)

def post(x, r):
    y = If(x < 0, -x, x)
    rev = 0
    for i in range(4):
        rev = If(y >= 10 ** i, rev * 10 + (y // 10 ** i) % 10, rev)
    return r == If(x < 0, -rev, rev)
""",
    "max_after_inserting_5": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    def best_of(n):
        options = [(x // 10 ** p) * 10 ** (p + 1) + 5 * 10 ** p + x % 10 ** p for p in range(n + 1)]
        return And(Or([r == o for o in options]), And([r >= o for o in options]))
    return If(x < 10, best_of(1), If(x < 100, best_of(2), If(x < 1000, best_of(3), best_of(4))))
""",
    "mode_first_to_reach": """
def pre(a):
    return True

def post(a, r):
    best, leader = 0, a[0]
    for j in range(N):
        seen = Sum([If(a[t] == a[j], 1, 0) for t in range(j + 1)])
        leader = If(seen > best, a[j], leader)
        best = If(seen > best, seen, best)
    return r == leader
""",
    "reverse_difference": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    rev = 0
    for i in range(4):
        rev = If(x >= 10 ** i, rev * 10 + (x // 10 ** i) % 10, rev)
    return r == x - rev
""",
    "reversal_is_larger": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    rev = 0
    for i in range(4):
        rev = If(x >= 10 ** i, rev * 10 + (x // 10 ** i) % 10, rev)
    return r == If(rev > x, 1, 0)
""",
    "mirror_digits": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    result = x
    for i in range(4):
        result = If(x >= 10 ** i, result * 10 + (x // 10 ** i) % 10, result)
    return r == result
""",
    "rotate_digits_right": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    last, rest = x % 10, x // 10
    return r == If(x < 10, x, If(x < 100, last * 10 + rest, If(x < 1000, last * 100 + rest, last * 1000 + rest)))
""",
    "twos_complement_bits": """
def pre(x):
    return And(-32 <= x, x <= 31)

def post(x, r):
    u = x % 64
    return r == Sum([(u // 2 ** i) % 2 for i in range(6)])
""",
    "index_of_max_nearest_middle": """
def pre(a):
    return True

def post(a, r):
    m = a[0]
    for j in range(1, N):
        m = If(a[j] > m, a[j], m)
    return r == If(a[1] == m, 1, If(a[2] == m, 2, If(a[0] == m, 0, 3)))
""",
    "reversal_divisible_by_4": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    rev = 0
    for i in range(4):
        rev = If(x >= 10 ** i, rev * 10 + (x // 10 ** i) % 10, rev)
    return r == If(rev % 4 == 0, 1, 0)
""",
    "reverse_of_successor": """
def pre(x):
    return And(0 <= x, x <= 9998)

def post(x, r):
    y = x + 1
    rev = 0
    for i in range(4):
        rev = If(y >= 10 ** i, rev * 10 + (y // 10 ** i) % 10, rev)
    return r == rev
""",
    "last_largest_digit_position": """
def pre(x):
    return And(0 <= x, x <= 9999)

def post(x, r):
    n = If(x < 10, 1, If(x < 100, 2, If(x < 1000, 3, 4)))
    d = [(x // 10 ** i) % 10 for i in range(4)]
    top = d[0]
    for i in range(1, 4):
        top = If(And(i < n, d[i] > top), d[i], top)
    rightmost = 3
    for i in range(3, -1, -1):
        rightmost = If(And(i < n, d[i] == top), i, rightmost)
    return r == n - rightmost
""",
    "longest_increasing_run_start": """
def pre(a):
    return True

def post(a, r):
    lengths = []
    for s in range(N):
        length = 1
        for k in range(2, N - s + 1):
            length = length + If(And([a[t] < a[t + 1] for t in range(s, s + k - 1)]), 1, 0)
        lengths.append(length)
    best = lengths[0]
    for s in range(1, N):
        best = If(lengths[s] > best, lengths[s], best)
    picks = [And(r == s, lengths[s] == best, And([lengths[t] != best for t in range(s + 1, N)])) for s in range(N)]
    return Or(picks)
""",
    "last_local_min_index": """
def pre(a):
    return True

def post(a, r):
    mins = []
    for j in range(N):
        conds = []
        if j > 0:
            conds.append(a[j] < a[j - 1])
        if j < N - 1:
            conds.append(a[j] < a[j + 1])
        mins.append(And(conds))
    none = And([Not(m) for m in mins])
    picks = [And(r == j, mins[j], And([Not(mins[k]) for k in range(j + 1, N)])) for j in range(N)]
    return Or(And(r == -1, none), Or(picks))
""",
    # game and process rules: a precondition weaker than the possible inputs is still correct
    "tennis_game": """
def pre(p, q):
    return And(p >= 0, q >= 0)

def post(p, q, r):
    a_won = And(p >= 4, p >= q + 2)
    b_won = And(q >= 4, q >= p + 2)
    return And(Implies(a_won, r == 1), Implies(b_won, r == 2), Implies(Not(Or(a_won, b_won)), r == 0))
""",
    "table_tennis_game": """
def pre(p, q):
    return And(p >= 0, q >= 0)

def post(p, q, r):
    a_won = And(p >= 11, p >= q + 2)
    b_won = And(q >= 11, q >= p + 2)
    return And(Implies(a_won, r == 1), Implies(b_won, r == 2), Implies(Not(Or(a_won, b_won)), r == 0))
""",
    "tennis_games_won": """
def pre(a):
    return True

def post(a, r):
    return r == If(a[0] > a[1], 1, 0) + If(a[2] > a[3], 1, 0)
""",
    "badminton_scores_possible": """
def pre(a):
    return And([a[j] >= 0 for j in range(N)])

def post(a, r):
    def over(x, y):
        return Or(x >= 30, And(x >= 21, x - y >= 2))
    def final(w, l):
        # the game is over, and was not over before the winner's last point
        return And(l < w, over(w, l), Not(over(w - 1, l)))
    def possible(x, y):
        return Or(final(x, y), final(y, x))
    return r == If(possible(a[0], a[1]), 1, 0) + If(possible(a[2], a[3]), 1, 0)
""",
    "badminton_losing_score": """
def pre(p):
    return And(21 <= p, p <= 30)

def post(p, r):
    return If(p == 21, And(0 <= r, r <= 19), If(p == 30, Or(r == 28, r == 29), r == p - 2))
""",
    "coin_jar_final": """
def pre(t, d):
    return True

def post(t, d, r):
    stopped_early = And(d == 4, t >= 10, t <= 12)
    stopped_on_day_5 = And(d == 5, t >= 5, t <= 12)
    return r == If(Or(stopped_early, stopped_on_day_5), 1, 0)
""",
}

# (task id, code, expected labels), checked by tests/test_checks.py.
KNOWN = [
    ("min2", """
def pre(a, b):
    return True
def post(a, b, r):
    return And(r <= a, r <= b)
""", ["too weak"]),
    ("clamp", """
def pre(lo, hi, x):
    return lo <= hi
def post(lo, hi, x, r):
    return And(lo <= r, r <= hi)
""", ["too weak"]),
    ("min2", """
def pre(a, b):
    return a != b
def post(a, b, r):
    return And(r <= a, r <= b, Or(r == a, r == b))
""", ["too strict on inputs"]),
    ("min2", """
def pre(a, b):
    return False
def post(a, b, r):
    return And(r <= a, r <= b, Or(r == a, r == b))
""", ["too strict on inputs", "empty"]),
    ("min2", """
def pre(a, b):
    return True
def post(a, b, r):
    return And(r < a, r <= b, Or(r == a, r == b))
""", ["too strong"]),
    ("count_eq", """
def pre(a, k):
    return True
def post(a, k, r):
    return And(r == Sum([If(a[j] == k, 1, 0) for j in range(N)]), r > 0)
""", ["too strong"]),
    ("above_both", """
def pre(a, b):
    return True
def post(a, b, r):
    return And(r > a, r > b, r % 2 == 0)
""", ["too strong"]),
    ("max_arr", """
def pre(a):
    return True
def post(a, r):
    i = Int('i')
    return ForAll([i], Implies(And(0 <= i, i < N), a[i] <= r))
""", ["too weak"]),
    ("clamp", """
def pre(lo, hi, x):
    return lo <= hi
def post(lo, hi, x, r):
    return r == x
""", ["too strong", "too weak"]),
    # benchmark tasks: typical mistakes
    ("trunc_div3", """
def pre(x):
    return True
def post(x, r):
    return r == x / 3
""", ["too strong", "too weak"]),                      # rounds down, not toward zero, for negative x
    ("any_index_at_least_mean", """
def pre(a):
    return True
def post(a, r):
    return And(0 <= r, r < N, a[r] >= Sum([a[j] for j in range(N)]) / N)
""", ["too weak"]),                                    # integer division truncates the average
    ("triangle_kind", """
def pre(a, b, c):
    return True
def post(a, b, c, r):
    valid = And(a > 0, b > 0, c > 0, a + b >= c, a + c >= b, b + c >= a)
    kind = If(And(a == b, b == c), 3, If(Or(a == b, b == c, a == c), 2, 1))
    return r == If(valid, kind, 0)
""", ["too strong", "too weak"]),                      # degenerate triangles such as 1, 1, 2
    ("digit_sum_signed", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    return r == Sum([(x // 10 ** i) % 10 for i in range(4)])
""", ["too strict on inputs"]),                        # assumes x is never negative
    ("any_value_exactly_twice", """
def pre(a):
    return True
def post(a, r):
    c = Sum([If(a[j] == r, 1, 0) for j in range(N)])
    none = And([Sum([If(a[j] == a[i], 1, 0) for j in range(N)]) != 2 for i in range(N)])
    return Or(c >= 2, And(r == -1, none))
""", ["too weak"]),                                    # at least twice: accepts a value that occurs three times
    # Group 4: the mistake each task is designed to provoke
    ("reverse_digits_signed", """
def pre(x):
    return And(x >= -9999, x <= 9999)
def post(x, r):
    y = If(x < 0, -x, x)
    rev = 1000 * (y % 10) + 100 * ((y // 10) % 10) + 10 * ((y // 100) % 10) + y // 1000
    return r == If(x < 0, -rev, rev)
""", ["too strong", "too weak"]),    # every number has four digits
    ("max_after_inserting_5", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    options = [(x // 10 ** p) * 10 ** (p + 1) + 5 * 10 ** p + x % 10 ** p for p in range(5)]
    return And(Or([r == o for o in options]), And([r >= o for o in options]))
""", ["too strong", "too weak"]),    # inserts in front of leading zeros
    ("mode_first_to_reach", """
def pre(a):
    return True
def post(a, r):
    counts = [Sum([If(a[t] == a[i], 1, 0) for t in range(N)]) for i in range(N)]
    mine = Sum([If(a[t] == r, 1, 0) for t in range(N)])
    top = Or([r == a[i] for i in range(N)])
    most = And([mine >= c for c in counts])
    smallest = And([Implies(counts[i] == mine, r <= a[i]) for i in range(N)])
    return And(top, most, smallest)
""", ["too strong", "too weak"]),    # the smallest value on a tie
    ("reverse_difference", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    rev = 1000 * (x % 10) + 100 * ((x // 10) % 10) + 10 * ((x // 100) % 10) + x // 1000
    return r == x - rev
""", ["too strong", "too weak"]),    # every number has four digits
    ("reversal_is_larger", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    rev = 1000 * (x % 10) + 100 * ((x // 10) % 10) + 10 * ((x // 100) % 10) + x // 1000
    return r == If(rev > x, 1, 0)
""", ["too strong", "too weak"]),    # every number has four digits
    ("mirror_digits", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    rev = 1000 * (x % 10) + 100 * ((x // 10) % 10) + 10 * ((x // 100) % 10) + x // 1000
    return r == x * 10000 + rev
""", ["too strong", "too weak"]),    # every number has four digits
    ("rotate_digits_right", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    return r == (x % 10) * 1000 + x // 10
""", ["too strong", "too weak"]),    # the front of a four-digit number
    ("twos_complement_bits", """
def pre(x):
    return And(-32 <= x, x <= 31)
def post(x, r):
    u = If(x < 0, -x, x)
    return r == Sum([(u // 2 ** i) % 2 for i in range(6)])
""", ["too strong", "too weak"]),    # the bits of the absolute value
    ("index_of_max_nearest_middle", """
def pre(a):
    return True
def post(a, r):
    m = a[0]
    for j in range(1, N):
        m = If(a[j] > m, a[j], m)
    return r == If(a[0] == m, 0, If(a[1] == m, 1, If(a[2] == m, 2, 3)))
""", ["too strong", "too weak"]),    # the first largest element
    ("reversal_divisible_by_4", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    rev = 1000 * (x % 10) + 100 * ((x // 10) % 10) + 10 * ((x // 100) % 10) + x // 1000
    return r == If(rev % 4 == 0, 1, 0)
""", ["too strong", "too weak"]),    # every number has four digits
    ("reverse_of_successor", """
def pre(x):
    return And(0 <= x, x <= 9998)
def post(x, r):
    y = x + 1
    return r == 1000 * (y % 10) + 100 * ((y // 10) % 10) + 10 * ((y // 100) % 10) + y // 1000
""", ["too strong", "too weak"]),    # every number has four digits
    ("last_largest_digit_position", """
def pre(x):
    return And(0 <= x, x <= 9999)
def post(x, r):
    left = [x // 1000, (x // 100) % 10, (x // 10) % 10, x % 10]
    top = left[0]
    for d in left[1:]:
        top = If(d > top, d, top)
    position = 1
    for j in range(4):
        position = If(left[j] == top, j + 1, position)
    return r == position
""", ["too strong", "too weak"]),    # positions of a four-digit number
    ("longest_increasing_run_start", """
def pre(a):
    return True
def post(a, r):
    lengths = [1] * N
    for i in range(N - 2, -1, -1):
        lengths[i] = If(a[i] < a[i + 1], lengths[i + 1] + 1, 1)
    best = lengths[0]
    for i in range(1, N):
        best = If(lengths[i] > best, lengths[i], best)
    first = N - 1
    for i in range(N - 1, -1, -1):
        first = If(lengths[i] == best, i, first)
    return r == first
""", ["too strong", "too weak"]),    # the first longest run
    ("last_local_min_index", """
def pre(a):
    return True
def post(a, r):
    last = -1
    for j in range(1, N - 1):
        last = If(And(a[j] < a[j - 1], a[j] < a[j + 1]), j, last)
    return r == last
""", ["too strong", "too weak"]),    # leaves out the end elements
    # game and process rules: mistakes the spec writer made in screening runs
    ("tennis_game", """
def pre(p, q):
    in_progress = And(Or(p < 4, p - q < 2), Or(q < 4, q - p < 2))
    return And(p >= 0, q >= 0, Or(in_progress, And(p >= 4, p - q == 2), And(q >= 4, q - p == 2)))
def post(p, q, r):
    return r == If(And(p >= 4, p - q >= 2), 1, If(And(q >= 4, q - p >= 2), 2, 0))
""", ["too strict on inputs"]),      # a game ends with a lead of exactly 2, so 4-0 is not a possible score
    ("table_tennis_game", """
def pre(p, q):
    in_progress = And(Or(p < 11, p - q < 2), Or(q < 11, q - p < 2))
    return And(p >= 0, q >= 0, Or(in_progress, And(p >= 11, p - q == 2), And(q >= 11, q - p == 2)))
def post(p, q, r):
    return r == If(And(p >= 11, p - q >= 2), 1, If(And(q >= 11, q - p >= 2), 2, 0))
""", ["too strict on inputs"]),      # a game ends with a lead of exactly 2, so 11-0 is not a possible score
    ("tennis_games_won", """
def pre(a):
    def valid(p, q):
        return Or(And(p >= 4, q == p - 2), And(q >= 4, p == q - 2))
    return And(valid(a[0], a[1]), valid(a[2], a[3]))
def post(a, r):
    return r == If(a[0] > a[1], 1, 0) + If(a[2] > a[3], 1, 0)
""", ["too strict on inputs"]),      # a game ends with a lead of exactly 2
    ("badminton_scores_possible", """
def pre(a):
    return And([a[j] >= 0 for j in range(N)])
def post(a, r):
    def valid(w, l):
        return Or(And(w == 30, l <= 29), And(w == 21, l <= 19), And(w >= 22, w <= 29, l == w - 2))
    def possible(x, y):
        return Or(valid(x, y), valid(y, x))
    return r == If(possible(a[0], a[1]), 1, 0) + If(possible(a[2], a[3]), 1, 0)
""", ["too strong", "too weak"]),    # any score of 30 to at most 29 ends a game
    ("badminton_losing_score", """
def pre(p):
    return And(21 <= p, p <= 30)
def post(p, r):
    return If(p == 21, And(0 <= r, r <= 19), If(p == 30, And(0 <= r, r <= 29), r == p - 2))
""", ["too weak"]),                  # at 30 the loser can have any score
    ("coin_jar_final", """
def pre(t, d):
    return And(d >= 1, d <= 5)
def post(t, d, r):
    stopped = Or(And(d == 4, t >= 10, t <= 12), And(d == 5, t >= 5, t <= 12))
    return r == If(stopped, 1, 0)
""", ["too strict on inputs"]),      # leaves out day counts for which the answer is 0
] + [(task_id, code, ["correct"]) for task_id, code in CORRECT.items()]

def _min2_post(body):
    return f"def pre(a, b):\n    return True\ndef post(a, b, r):\n    {body}\n"


# Code that the loader must reject: (task id, code, words expected in the reason).
# Without the guards, the first nine would run without an error and be checked as a
# different formula than the one written (for example `r == a or r == b` as `r == b`).
REJECTED = [
    ("min2", _min2_post("return r == a or r == b"), "formula"),
    ("min2", _min2_post("return r in [a, b]"), "formula"),
    ("min2", _min2_post("if r == a:\n        return True\n    return r == b"), "formula"),
    ("min2", _min2_post("return Or(r == a, r == b) if len({a, b}) == 2 else r == a"), "sets"),
    ("min2", _min2_post("N = 5\n    return r == a"), "predefined"),
    ("min2", _min2_post("return r == a // b"), "divisor"),
    ("abs", "def pre(x):\n    return True\ndef post(x, r):\n    return r == x % -3\n", "divisor"),
    ("count_eq", "def pre(a, k):\n    x = Int('in_a')\n    return x > 0\ndef post(a, k, r):\n    return True\n",
     "reserved"),
    ("min2", _min2_post("t = Int('t')\n    return r == a + t"), "bound"),
    ("min2", _min2_post("return r <= a and r <= b"), "And"),
    ("min2", _min2_post("return r == min(a, b)"), "min"),
    ("min2", "import os\ndef pre(a, b):\n    return True\ndef post(a, b, r):\n    return True\n", "import"),
    ("min2", "def pre(a, b):\n    try:\n        return a > b\n    except Exception:\n        return True\n"
             "def post(a, b, r):\n    return True\n", "try"),
    ("min2", _min2_post("return r.__class__"), "attribute"),
    ("min2", _min2_post("return r.eq(a)"), "attribute"),
    ("min2", "def pre(a, b):\n    while True:\n        pass\n    return True\ndef post(a, b, r):\n    return True\n",
     "too long"),
    ("count_eq", "def pre(a, k):\n    xs = [1]\n    for x in xs:\n        xs.append(x)\n    return True\n"
                 "def post(a, k, r):\n    return True\n", "too long"),
    ("count_eq", "def pre(a, k):\n    return True\ndef post(a, k, r):\n    return r == sum(a)\n", "array"),
    ("min2", "def pre(a, b):\n    return True\n", "missing"),
    ("min2", "def pre(a):\n    return True\ndef post(a, b, r):\n    return True\n", "parameter"),
    ("abs", "def pre(x):\n    return True\ndef post(x, r):\n    return r + 1\n", "Boolean"),
]

# Ordinary Python that the loader must accept, with the labels the checks must give:
# (task id, code, labels). The first nine are first specs from the Exp 1 run of
# November 15 that the earlier, stricter format check rejected.
PYTHON_IDIOMS = [
    ("max_subarray_sum", """
def pre(a):
    return True

def post(a, r):
    candidates = []
    for i in range(N):
        s = a[i]
        candidates.append(s)
        for j in range(i + 1, N):
            s = s + a[j]
            candidates.append(s)
    return And(Or([r == c for c in candidates]),
               And([r >= c for c in candidates]))
""", ["correct"]),
    ("max_subarray_sum", """
def pre(a):
    return True

def post(a, r):
    segs = [Sum([a[k] for k in range(i, j + 1)]) for i in range(N) for j in range(i, N)]
    return And(Or([r == s for s in segs]), And([r >= s for s in segs]))
""", ["correct"]),
    ("pivot_index", """
def pre(a):
    return True

def post(a, r):
    balanced = [
        Sum([0] + [a[j] for j in range(k)]) == Sum([0] + [a[j] for j in range(k + 1, N)])
        for k in range(N)
    ]
    options = []
    for k in range(N):
        earlier_unbalanced = [Not(balanced[j]) for j in range(k)]
        options.append(And(r == k, balanced[k], *earlier_unbalanced))
    none_balanced = And(r == -1, *[Not(b) for b in balanced])
    return Or(none_balanced, *options)
""", ["correct"]),
    ("longest_equal_run", """
def pre(a):
    return True

def post(a, r):
    witnesses = []
    bounds = []
    for s in range(N):
        for l in range(1, N + 1):
            if s + l <= N:
                uni = And([True] + [a[s + k] == a[s] for k in range(1, N) if k < l])
                witnesses.append(And(r == l, uni))
                bounds.append(Implies(uni, r >= l))
    return And(r >= 1, Or(witnesses), And(bounds))
""", ["correct"]),
    ("longest_equal_run", """
def pre(a):
    return True

def post(a, r):
    conds = [(L, And([a[s + t] == a[s] for t in range(L)]))
             for s in range(N) for L in range(1, N - s + 1)]
    return And(
        r >= 1,
        r <= N,
        Or([And(r == L, c) for (L, c) in conds]),
        And([Implies(c, L <= r) for (L, c) in conds])
    )
""", ["correct"]),
    ("any_peak_index", """
def pre(a):
    return True

def post(a, r):
    cases = []
    for j in range(N):
        nbrs = [k for k in range(N) if k - j in (1, -1)]
        cases.append(And(r == j, And([a[j] >= a[k] for k in nbrs])))
    return Or(cases)
""", ["correct"]),
    ("any_peak_index", """
def pre(a):
    return True

def post(a, r):
    conds = []
    for j in range(N):
        nbrs = [a[k] for k in [j - 1, j + 1] if 0 <= k < N]
        conds.append(Implies(r == j, And([a[j] >= v for v in nbrs])))
    return And(0 <= r, r < N, And(conds))
""", ["correct"]),
    ("count_distinct", """
def pre(a):
    return True

def post(a, r):
    terms = []
    for i in range(N):
        conds = [True]
        for j in range(i):
            conds.append(a[j] != a[i])
        terms.append(If(And(conds), 1, 0))
    return r == Sum(terms)
""", ["correct"]),
    ("is_mountain", """
def pre(a):
    return True

def post(a, r):
    conds = []
    for p in range(1, N - 1):
        up = [a[j] < a[j + 1] for j in range(p)]
        down = [a[j] > a[j + 1] for j in range(p, N - 1)]
        conds.append(And(up + down))
    good = Or(conds)
    return If(good, r == 1, r == 0)
""", ["correct"]),
    ("count_inversions", """
def inversions(a):
    return Sum([If(a[i] > a[j], 1, 0) for i in range(N) for j in range(i + 1, N)])

def pre(a):
    return True

def post(a, r):
    return r == inversions(a)
""", ["correct"]),
    ("trunc_div3", """
import z3

def pre(x):
    return True

def post(x, r):
    return z3.If(x >= 0, r == x // 3, r == -((-x) // 3))
""", ["correct"]),
    ("closest_to_zero", """
def pre(a, b):
    return True

def post(a, b, r):
    return r == If(abs(a) < abs(b), a, If(abs(b) < abs(a), b, If(a >= b, a, b)))
""", ["correct"]),
]

ATTACK_CLAMP_WEAK = """
def pre(lo, hi, x):
    return lo <= hi
def post(lo, hi, x, r):
    return And(lo <= r, r <= hi)
"""

PROGRAM_RETURN_X = "```python\ndef prog(lo, hi, x):\n    return x\n```"
PROGRAM_GOLDEN_CLAMP = "```python\ndef prog(lo, hi, x):\n    return If(x < lo, lo, If(x > hi, hi, x))\n```"
PROGRAM_RETURN_LO = "Here is one.\n```python\ndef prog(lo, hi, x):\n    return lo\n```"


def weak_code(task):
    params = ", ".join(task.param_names)
    return f"def pre({params}):\n    return True\n\ndef post({params}, r):\n    return True\n"


def fenced(code):
    return f"```python\n{code.strip()}\n```"
