# T6. Repair per feedback type (RQ3)

| Feedback type | Runs | Ended correct | Ended undetermined | Mean rounds to correct | Runs with a new defect | Invalid replies | Rounds that fell back to the example |
|---|---|---|---|---|---|---|---|
| 1: pass/fail | 20 | 17 (85%) | 1 | 1.412 | 0 (0%) | 0 | 0 |
| 2: one example | 20 | 19 (95%) | 1 | 1 | 0 (0%) | 0 | 0 |
| 3: wrong program | 20 | 19 (95%) | 1 | 1 | 0 (0%) | 0 | 0 |

'New defect': some revision had a defect category that the starting spec did not have (for example, it became too strong). 'Fell back': type 3 found no wrong program and reported the single example instead.
