# Control experiments (diagnostic; readouts per PLAN.md)

Pairs are `candidate-only / F16-only` task counts, with an exact McNemar p.

## Premature side-effect attempts on the 100-task conditional subset

| Condition | F16 tasks (par / skip) | Q4 tasks (par / skip) | imat-Q4 tasks (par / skip) | Q4 vs F16 | imat-Q4 vs F16 |
|---|---|---|---|---|---|
| baseline | 16 (13 / 3) | 44 (33 / 15) | 19 (7 / 14) | 28/0, p=7.5e-09 | 7/4, p=0.55 |
| wait | 7 (7 / 1) | 32 (22 / 13) | 13 (5 / 8) | 26/1, p=4.2e-07 | 9/3, p=0.15 |
| two_tools | 31 (31 / 0) | 45 (45 / 4) | 26 (23 / 3) | 14/0, p=0.00012 | 5/10, p=0.3 |

## check_only: user asks only for the check and says not to act

| Model | Tasks with any side-effect call (of 100) | Runs with one (of 500) |
|---|---|---|
| F16 | 0 | 0 |
| Q4 | 0 | 0 |
| imat-Q4 | 0 | 0 |

Q4 vs F16: 0/0, p=1; imat-Q4 vs F16: 0/0, p=1

## direct: user asks for the action outright

| Model | Run pass rate | Runs that only checked instead of acting | Runs with no call |
|---|---|---|---|
| F16 | 93.0% | 0 | 0 |
| Q4 | 94.4% | 1 | 5 |
| imat-Q4 | 94.2% | 0 | 3 |
