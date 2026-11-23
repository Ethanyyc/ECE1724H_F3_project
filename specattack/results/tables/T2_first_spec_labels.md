# T2. Labels of first specs (RQ1)

| Label | Group 1 | Group 2 | Group 3 | Group 4 | All |
|---|---|---|---|---|---|
| correct | 87% (80-90) | 97% (90-100) | 93% (90-100) | 72% (65-75) | 84% (82-86) |
| too weak | 10% | 3% (0-10) | 7% (0-10) | 23% (20-30) | 13% (12-14) |
| too strong | 10% | 3% (0-10) | 0% | 23% (20-30) | 12% (10-14) |
| too strict on inputs | 3% (0-10) | 0% | 0% | 5% | 3% (2-4) |
| empty | 0% | 0% | 0% | 0% | 0% |
| did not follow the format | 0% | 0% | 0% | 0% | 0% |
| undetermined | 0% | 0% | 0% | 0% | 0% |
| LLM error (a defect, or did not follow the format) | 13% (10-20) | 3% (0-10) | 7% (0-10) | 28% (25-35) | 16% (14-18) |
| specs per repeat | 10 | 10 | 10 | 20 | 50 |

Mean share over repeats [0, 1, 2], with the minimum and maximum over repeats in parentheses. A spec can have several defect labels, so a column can add up to more than 100%. Undetermined specs (a Z3 query timed out or returned unknown, with no definite problem) are listed separately and are not counted as defects.
'LLM error (a defect, or did not follow the format)': the spec is wrong or its code does not run; each spec counts once.
