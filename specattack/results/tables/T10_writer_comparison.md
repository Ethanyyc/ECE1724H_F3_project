# T10. First-spec labels of the default writer (Exp 1) and a more capable writer (Exp 3) (RQ1 extension)

| Group | Writer | Specs | correct | too weak | too strong | too strict on inputs | empty | did not follow the format | undetermined | LLM error | Mean cost per spec (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-haiku-5-5 (Exp 1) | 30 | 87% (80-90) | 10% | 10% | 3% (0-10) | 0% | 0% | 0% | 13% (10-20) | 0.000575 |
| 1 | claude-opus-5-5 (Exp 3) | 30 | 100% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.01249 |
| 2 | claude-haiku-5-5 (Exp 1) | 30 | 97% (90-100) | 3% (0-10) | 3% (0-10) | 0% | 0% | 0% | 0% | 3% (0-10) | 0.000642 |
| 2 | claude-opus-5-5 (Exp 3) | 30 | 100% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.01033 |
| 3 | claude-haiku-5-5 (Exp 1) | 30 | 93% (90-100) | 7% (0-10) | 0% | 0% | 0% | 0% | 0% | 7% (0-10) | 0.000426 |
| 3 | claude-opus-5-5 (Exp 3) | 30 | 100% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.008791 |
| 4 | claude-haiku-5-5 (Exp 1) | 60 | 72% (65-75) | 23% (20-30) | 23% (20-30) | 5% | 0% | 0% | 0% | 28% (25-35) | 0.00084 |
| 4 | claude-opus-5-5 (Exp 3) | 60 | 100% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.01688 |
| All | claude-haiku-5-5 (Exp 1) | 150 | 84% (82-86) | 13% (12-14) | 12% (10-14) | 3% (2-4) | 0% | 0% | 0% | 16% (14-18) | 0.000664 |
| All | claude-opus-5-5 (Exp 3) | 150 | 100% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.01308 |

Both runs on the same 50 tasks, with the same prompt, repeats and checks; only the writer model differs. Shares as in T2; 'LLM error' is a defect or a format failure.
Tasks with LLM errors only for claude-haiku-5-5 (Exp 1): badminton_losing_score (2/3), badminton_scores_possible (1/3), coin_jar_final (3/3), last_largest_digit_position (1/3), reversal_divisible_by_4 (2/3), reversal_is_larger (2/3), reverse_difference (3/3), reverse_digits (3/3), reverse_digits_signed (3/3), reverse_of_successor (3/3), tennis_game (1/3).
Tasks with LLM errors only for claude-opus-5-5 (Exp 3): none.
Tasks with LLM errors for both (Exp 1 vs Exp 3): none.
