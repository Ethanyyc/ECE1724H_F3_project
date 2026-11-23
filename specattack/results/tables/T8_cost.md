# T8. Cost per spec and stage (RQ4)

| Stage | Metric | Group 1 | Group 2 | Group 3 | Group 4 | All | Exp 3 (claude-opus-5-5) |
|---|---|---|---|---|---|---|---|
| first spec | LLM cost per spec (USD) | 0.0005746 | 0.0006417 | 0.0004265 | 0.0008398 | 0.0006645 | 0.01308 |
| first spec | input tokens per spec | 799.9 | 996.1 | 945 | 861.1 | 892.6 | 892.6 |
| first spec | output tokens per spec (incl. thinking) | 989.3 | 1084 | 664 | 1507 | 1150 | 475.3 |
| first spec | thinking tokens per spec | 797.5 | 845.4 | 509.2 | 1208 | 913.5 | 151.2 |
| first spec | LLM latency per spec (ms) | 5585 | 6016 | 3947 | 7868 | 6257 | 4802 |
| first spec | Z3 time per checked spec (ms) | 10.37 | 110.1 | 12.76 | 228.1 | 117.9 | 11.01 |
| attack | LLM cost per attack (USD) | 0.005796 | 0.009552 | 0.005141 | 0.00593 | 0.006012 |  |
| attack | attempts per attack | 1 | 1 | 1 | 1 | 1 |  |
| attack | thinking tokens per attack | 0 | 0 | 0 | 0 | 0 |  |
| attack | Z3 time per attack (ms) | 2.168 | 3.617 | 7.873 | 3.725 | 3.9 |  |
| attack | wall time per attack (ms) | 4077 | 7108 | 4125 | 3441 | 3788 |  |
| repair | LLM cost per repair run (USD, incl. attacks) | 0.0009559 | 0.002709 | 0.001881 | 0.00121 | 0.001314 |  |
| repair | thinking tokens per repair run | 1331 | 4167 | 3035 | 1773 | 1952 |  |
| repair | Z3 time per repair run (ms) | 15.32 | 19.56 | 17.05 | 6496 | 4552 |  |
| repair | wall time per repair run (ms) | 8085 | 2.398e+04 | 1.75e+04 | 1.659e+04 | 1.578e+04 |  |

Total LLM cost of Exp 1 and Exp 2: $0.30 (repair runs include the attacks run inside them; the Exp 1 attack reused in type-3 round 1 is counted once, in Exp 1).
Exp 3 (claude-opus-5-5): 150 first specs for $1.96 in total; it writes first specs only (no attacks or repairs), and is not part of the group columns.
Output tokens are the billed output and include thinking tokens; thinking tokens are shown when the API reports them. Costs use the prices in speccheck/config.py.
