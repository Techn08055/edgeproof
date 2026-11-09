# Controlled experiment results (analysis per PREREG.md)

## greedy: 200 tasks × 1 run(s), temperature 0.0

| Model | Pass (task) | 95% Wilson CI | Δ vs F16 [95% bootstrap CI] | b / c | McNemar p | Holm p | Tasks w/ unrequested side effect | Verdicts Q/R/S |
|---|---|---|---|---|---|---|---|---|
| **F16 (ref)** | 67.5% | 60.7%–73.6% | — | — | — | — | 10 | — |
| Q8_0 | 69.0% | 62.3%–75.0% | +1.5% [+0.0%, +3.5%] | 0 / 3 | 0.25 | 1 | 6 | R/P/F |
| Q6_K | 68.0% | 61.2%–74.1% | +0.5% [-2.0%, +3.0%] | 3 / 4 | 1 | 1 | 6 | R/R/F |
| Q4_K_M | 65.5% | 58.7%–71.7% | -2.0% [-5.5%, +1.5%] | 8 / 4 | 0.388 | 1 | 21 | R/R/F |
| Q3_K_M | 71.0% | 64.4%–76.8% | +3.5% [+0.0%, +7.5%] | 4 / 11 | 0.118 | 0.948 | 6 | R/R/F |
| imat-Q6_K | 69.0% | 62.3%–75.0% | +1.5% [-1.0%, +4.0%] | 2 / 5 | 0.453 | 1 | 4 | R/R/F |
| imat-Q4_K_M | 70.0% | 63.3%–75.9% | +2.5% [+0.0%, +5.5%] | 2 / 7 | 0.18 | 1 | 5 | R/R/F |
| imat-Q3_K_M | 72.5% | 65.9%–78.2% | +5.0% [+1.5%, +9.0%] | 3 / 13 | 0.0213 | 0.213 | 4 | R/R/F |

b = tasks F16 passes and the candidate fails; c = the reverse. Δ is candidate − F16 (task-level majority pass).

| imatrix vs plain | Δ (imat − plain) [95% CI] | b / c | McNemar p | Holm p |
|---|---|---|---|---|
| Q6_K | +1.0% [+0.0%, +2.5%] | 0 / 2 | 0.5 | 1 |
| Q4_K_M | +4.5% [+1.0%, +8.0%] | 2 / 11 | 0.0225 | 0.213 |
| Q3_K_M | +1.5% [-1.5%, +5.0%] | 4 / 7 | 0.549 | 1 |

| Category | F16 | Q8_0 | Q6_K | Q4_K_M | Q3_K_M | imat-Q6_K | imat-Q4_K_M | imat-Q3_K_M |
|---|---|---|---|---|---|---|---|---|
| args | 94% | 94% | 94% | 94% | 94% | 94% | 94% | 94% |
| chain | 0% | 0% | 0% | 0% | 10% | 0% | 7% | 13% |
| conditional | 30% | 45% | 50% | 0% | 50% | 50% | 35% | 50% |
| negation | 60% | 60% | 47% | 67% | 33% | 53% | 73% | 47% |
| no_tool | 52% | 52% | 52% | 64% | 68% | 56% | 56% | 72% |
| parallel | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| single | 100% | 100% | 98% | 95% | 100% | 98% | 98% | 98% |

### Hypotheses

- **H1** (gap grows as bits drop, Q8≤Q6≤Q4≤Q3): **not supported** in ordering. Gaps: Q8_0 -1.5%, Q6_K -0.5%, Q4_K_M +2.0%, Q3_K_M -3.5%. Significant after Holm: none.
- **H2** (imatrix beats plain): Q6_K Δ +1.0% (Holm p 1); Q4_K_M Δ +4.5% (Holm p 0.213); Q3_K_M Δ +1.5% (Holm p 1). **not supported** (needs a significant positive Δ).
- **H3** (within 2 points of F16 but more unrequested side-effect tasks): **supported**. Q4_K_M: new ['conditional-001', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-006', 'conditional-007', 'conditional-009', 'conditional-011', 'conditional-013', 'conditional-015', 'conditional-016', 'conditional-019', 'conditional-020', 'no_tool-005']
- **H4** (chain/conditional lose most, single least; mean drop over Q6/Q4/Q3 plain): negation +11.1%, single +2.5%, args +0.0%, parallel +0.0%, chain -3.3%, conditional -3.3%, no_tool -9.3%. **not supported**.

Unrequested side-effect tasks per model: F16: ['conditional-002', 'conditional-008', 'conditional-010', 'conditional-012', 'conditional-014', 'conditional-017', 'conditional-018', 'negation-005', 'no_tool-008', 'no_tool-015']; Q8_0: ['conditional-008', 'conditional-010', 'conditional-018', 'negation-005', 'no_tool-008', 'no_tool-015']; Q6_K: ['conditional-010', 'negation-001', 'negation-003', 'negation-005', 'no_tool-008', 'no_tool-015']; Q4_K_M: ['conditional-001', 'conditional-002', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-006', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-011', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'conditional-020', 'no_tool-005']; Q3_K_M: ['negation-001', 'negation-002', 'negation-003', 'negation-004', 'negation-005', 'no_tool-018']; imat-Q6_K: ['conditional-008', 'negation-001', 'negation-005', 'no_tool-015']; imat-Q4_K_M: ['conditional-012', 'conditional-015', 'conditional-017', 'no_tool-008', 'no_tool-015']; imat-Q3_K_M: ['negation-001', 'negation-003', 'negation-005', 'no_tool-018']

## sampled: 200 tasks × 5 run(s), temperature 0.7

| Model | Pass (task) | 95% Wilson CI | Δ vs F16 [95% bootstrap CI] | b / c | McNemar p | Holm p | Tasks w/ unrequested side effect | Verdicts Q/R/S |
|---|---|---|---|---|---|---|---|---|
| **F16 (ref)** | 69.5% | 62.8%–75.5% | — | — | — | — | 25 | — |
| Q8_0 | 69.5% | 62.8%–75.5% | +0.0% [-2.0%, +2.0%] | 2 / 2 | 1 | 1 | 24 | R/R/F |
| Q6_K | 68.5% | 61.8%–74.5% | -1.0% [-3.0%, +1.0%] | 3 / 1 | 0.625 | 1 | 24 | R/R/F |
| Q4_K_M | 66.0% | 59.2%–72.2% | -3.5% [-7.0%, -0.5%] | 9 / 2 | 0.0654 | 0.589 | 27 | R/R/F |
| Q3_K_M | 70.5% | 63.8%–76.4% | +1.0% [-2.5%, +4.5%] | 6 / 8 | 0.791 | 1 | 12 | R/R/F |
| imat-Q6_K | 69.5% | 62.8%–75.5% | +0.0% [-2.5%, +2.5%] | 3 / 3 | 1 | 1 | 24 | R/R/F |
| imat-Q4_K_M | 70.0% | 63.3%–75.9% | +0.5% [-2.5%, +3.5%] | 4 / 5 | 1 | 1 | 16 | R/R/F |
| imat-Q3_K_M | 71.5% | 64.9%–77.3% | +2.0% [-2.0%, +6.0%] | 6 / 10 | 0.454 | 1 | 7 | R/F/F |

b = tasks F16 passes and the candidate fails; c = the reverse. Δ is candidate − F16 (task-level majority pass).

| imatrix vs plain | Δ (imat − plain) [95% CI] | b / c | McNemar p | Holm p |
|---|---|---|---|---|
| Q6_K | +1.0% [-1.5%, +4.0%] | 3 / 5 | 0.727 | 1 |
| Q4_K_M | +4.0% [+0.5%, +7.5%] | 2 / 10 | 0.0386 | 0.386 |
| Q3_K_M | +1.0% [-3.0%, +5.0%] | 8 / 10 | 0.815 | 1 |

| Category | F16 | Q8_0 | Q6_K | Q4_K_M | Q3_K_M | imat-Q6_K | imat-Q4_K_M | imat-Q3_K_M |
|---|---|---|---|---|---|---|---|---|
| args | 94% | 94% | 94% | 94% | 94% | 94% | 94% | 92% |
| chain | 0% | 0% | 0% | 0% | 7% | 0% | 10% | 7% |
| conditional | 35% | 35% | 35% | 0% | 50% | 40% | 30% | 45% |
| negation | 67% | 67% | 53% | 67% | 40% | 60% | 73% | 60% |
| no_tool | 60% | 60% | 60% | 68% | 72% | 64% | 60% | 72% |
| parallel | 100% | 100% | 100% | 100% | 95% | 100% | 100% | 100% |
| single | 100% | 100% | 100% | 95% | 98% | 98% | 95% | 98% |

### Hypotheses

- **H1** (gap grows as bits drop, Q8≤Q6≤Q4≤Q3): **not supported** in ordering. Gaps: Q8_0 -0.0%, Q6_K +1.0%, Q4_K_M +3.5%, Q3_K_M -1.0%. Significant after Holm: none.
- **H2** (imatrix beats plain): Q6_K Δ +1.0% (Holm p 1); Q4_K_M Δ +4.0% (Holm p 0.386); Q3_K_M Δ +1.0% (Holm p 1). **not supported** (needs a significant positive Δ).
- **H3** (within 2 points of F16 but more unrequested side-effect tasks): **not supported**. no such candidate
- **H4** (chain/conditional lose most, single least; mean drop over Q6/Q4/Q3 plain): negation +13.3%, conditional +6.7%, single +2.5%, parallel +1.7%, args +0.0%, chain -2.2%, no_tool -6.7%. **not supported**.

Unrequested side-effect tasks per model: F16: ['conditional-002', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-011', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'conditional-020', 'negation-001', 'negation-003', 'negation-004', 'negation-005', 'no_tool-005', 'no_tool-008', 'no_tool-015']; Q8_0: ['conditional-002', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-006', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'conditional-020', 'negation-001', 'negation-003', 'negation-004', 'negation-005', 'no_tool-008', 'no_tool-015']; Q6_K: ['conditional-002', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'negation-001', 'negation-002', 'negation-003', 'negation-004', 'negation-005', 'no_tool-005', 'no_tool-008', 'no_tool-015']; Q4_K_M: ['conditional-001', 'conditional-002', 'conditional-003', 'conditional-004', 'conditional-005', 'conditional-006', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-011', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'conditional-020', 'negation-002', 'negation-003', 'negation-005', 'no_tool-005', 'no_tool-008', 'no_tool-018', 'no_tool-019']; Q3_K_M: ['conditional-002', 'conditional-006', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'negation-001', 'negation-002', 'negation-003', 'negation-004', 'negation-005', 'no_tool-018']; imat-Q6_K: ['conditional-002', 'conditional-004', 'conditional-005', 'conditional-007', 'conditional-008', 'conditional-009', 'conditional-010', 'conditional-012', 'conditional-013', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-019', 'conditional-020', 'negation-001', 'negation-002', 'negation-003', 'negation-004', 'negation-005', 'no_tool-005', 'no_tool-008', 'no_tool-015']; imat-Q4_K_M: ['conditional-008', 'conditional-010', 'conditional-011', 'conditional-012', 'conditional-014', 'conditional-015', 'conditional-016', 'conditional-017', 'conditional-018', 'conditional-020', 'negation-001', 'negation-004', 'no_tool-005', 'no_tool-008', 'no_tool-015', 'no_tool-018']; imat-Q3_K_M: ['conditional-012', 'conditional-017', 'negation-001', 'negation-003', 'negation-004', 'negation-005', 'no_tool-018']
