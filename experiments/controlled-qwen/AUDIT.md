# Exploratory audit (post-hoc, NOT pre-registered)

Re-scored with the v3 scorer (optimal call matching, `premature_action`). Pass/fail changed for 0 runs in both conditions versus the pre-registered analysis.

## greedy

### 1. Unrequested side-effect tasks by kind

| Model | prohibited (negation) | premature (right ticket, too early) | wrong_call (ticket never wanted) | total tasks |
|---|---|---|---|---|
| F16 | 1 | 3 | 6 | 10 |
| Q8_0 | 1 | 2 | 3 | 6 |
| Q6_K | 3 | 1 | 2 | 6 |
| Q4_K_M | 0 | 10 | 11 | 21 |
| Q3_K_M | 5 | 0 | 1 | 6 |
| imat-Q6_K | 2 | 1 | 1 | 4 |
| imat-Q4_K_M | 0 | 0 | 5 | 5 |
| imat-Q3_K_M | 3 | 0 | 1 | 4 |

### 2. Tasks with any premature action (dependent call or side effect before the result), paired vs F16

| Model | tasks | only candidate | only F16 | McNemar p | Holm p (7) |
|---|---|---|---|---|---|
| F16 | 24 | — | — | — | — |
| Q8_0 | 20 | 0 | 4 | 0.125 | 0.125 |
| Q6_K | 17 | 0 | 7 | 0.0156 | 0.0625 |
| Q4_K_M | 41 | 17 | 0 | 1.53e-05 | 0.000107 |
| Q3_K_M | 7 | 0 | 17 | 1.53e-05 | 0.000107 |
| imat-Q6_K | 18 | 0 | 6 | 0.0312 | 0.0938 |
| imat-Q4_K_M | 19 | 0 | 5 | 0.0625 | 0.125 |
| imat-Q3_K_M | 16 | 0 | 8 | 0.00781 | 0.0391 |

Premature-action tasks by category: F16: {'conditional': 7, 'chain': 17}; Q8_0: {'conditional': 3, 'chain': 17}; Q6_K: {'conditional': 1, 'chain': 16}; Q4_K_M: {'conditional': 20, 'chain': 21}; Q3_K_M: {'chain': 7}; imat-Q6_K: {'chain': 17, 'conditional': 1}; imat-Q4_K_M: {'chain': 17, 'conditional': 2}; imat-Q3_K_M: {'chain': 16}

### 3. Where Q3 beats F16 (tasks the candidate passes by majority and F16 fails)

- **Q3_K_M**: 11 tasks, by category {'no_tool': 4, 'chain': 3, 'conditional': 4}; F16's failure types on them {'call_when_not_required': 4, 'no_call_when_required': 3, 'premature_action': 4}
- **imat-Q3_K_M**: 13 tasks, by category {'no_tool': 5, 'chain': 4, 'conditional': 4}; F16's failure types on them {'call_when_not_required': 5, 'no_call_when_required': 3, 'premature_action': 5}

## sampled

### 1. Unrequested side-effect tasks by kind

| Model | prohibited (negation) | premature (right ticket, too early) | wrong_call (ticket never wanted) | total tasks |
|---|---|---|---|---|
| F16 | 4 | 8 | 13 | 25 |
| Q8_0 | 4 | 9 | 11 | 24 |
| Q6_K | 5 | 8 | 11 | 24 |
| Q4_K_M | 3 | 10 | 14 | 27 |
| Q3_K_M | 5 | 6 | 1 | 12 |
| imat-Q6_K | 5 | 7 | 12 | 24 |
| imat-Q4_K_M | 2 | 2 | 12 | 16 |
| imat-Q3_K_M | 4 | 0 | 3 | 7 |

### 2. Tasks with any premature action (dependent call or side effect before the result), paired vs F16

| Model | tasks | only candidate | only F16 | McNemar p | Holm p (7) |
|---|---|---|---|---|---|
| F16 | 38 | — | — | — | — |
| Q8_0 | 39 | 3 | 2 | 1 | 1 |
| Q6_K | 38 | 2 | 2 | 1 | 1 |
| Q4_K_M | 46 | 8 | 0 | 0.00781 | 0.0312 |
| Q3_K_M | 26 | 1 | 13 | 0.00183 | 0.011 |
| imat-Q6_K | 36 | 0 | 2 | 0.5 | 1 |
| imat-Q4_K_M | 29 | 0 | 9 | 0.00391 | 0.0195 |
| imat-Q3_K_M | 22 | 0 | 16 | 3.05e-05 | 0.000214 |

Premature-action tasks by category: F16: {'conditional': 17, 'chain': 21}; Q8_0: {'conditional': 16, 'chain': 23}; Q6_K: {'conditional': 15, 'chain': 23}; Q4_K_M: {'conditional': 20, 'chain': 26}; Q3_K_M: {'conditional': 6, 'chain': 20}; imat-Q6_K: {'conditional': 15, 'chain': 21}; imat-Q4_K_M: {'conditional': 9, 'chain': 20}; imat-Q3_K_M: {'chain': 20, 'conditional': 2}

### 3. Where Q3 beats F16 (tasks the candidate passes by majority and F16 fails)

- **Q3_K_M**: 8 tasks, by category {'no_tool': 3, 'chain': 2, 'conditional': 3}; F16's failure types on them {'call_when_not_required': 13, 'premature_action': 17, 'no_call_when_required': 1}
- **imat-Q3_K_M**: 10 tasks, by category {'no_tool': 5, 'chain': 2, 'conditional': 3}; F16's failure types on them {'call_when_not_required': 21, 'premature_action': 18, 'no_call_when_required': 3}

### 4. Per-task pass count out of 5

| Model | 0 | 1 | 2 | 3 | 4 | 5 | mean per-run pass |
|---|---|---|---|---|---|---|---|
| F16 | 41 | 17 | 3 | 10 | 11 | 118 | 68.7% |
| Q8_0 | 48 | 12 | 1 | 10 | 10 | 119 | 67.9% |
| Q6_K | 44 | 13 | 6 | 12 | 11 | 114 | 67.5% |
| Q4_K_M | 50 | 12 | 6 | 5 | 20 | 107 | 65.4% |
| Q3_K_M | 35 | 12 | 12 | 4 | 13 | 124 | 72.0% |
| imat-Q6_K | 45 | 12 | 4 | 10 | 14 | 115 | 68.1% |
| imat-Q4_K_M | 33 | 18 | 9 | 6 | 14 | 120 | 71.0% |
| imat-Q3_K_M | 45 | 6 | 6 | 7 | 11 | 125 | 70.8% |
