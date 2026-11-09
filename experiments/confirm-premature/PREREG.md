# Pre-registration: confirmatory study of premature side-effect actions

Written and frozen on 2026-11-08, **before any model saw this suite.** It was prompted by an exploratory finding (`../controlled-qwen/AUDIT.md`): plain Q4_K_M made premature actions on more tasks than F16 (greedy 17 vs 0 discordant, sampled 8 vs 0). Any result that disagrees with the hypothesis is reported as-is.

Frozen files (sha256, first 16 hex characters):

| File | sha256 |
|---|---|
| suite.yaml | e8f1af871114e9ab |
| make_suite.py | 6300491eede6284e |
| analyze.py | c5d4d21054921bb2 |
| edgeproof/checks.py | afa08c222982bd56 |
| edgeproof/runner.py | 2d31a3c7a19aab3b |

## Question
Does plain Q4_K_M make more **premature side-effect actions** than F16 on fresh, independently structured conditional workflows? A premature action is a side-effect call emitted before the result of the check it depends on has come back.

## Models
These are the same files as in the controlled experiment: the same sha256, the same llama.cpp build a691b23 and the same server flags.

| Role | Model |
|---|---|
| Reference | Qwen2.5-1.5B-Instruct F16 |
| Primary candidate | plain Q4_K_M |
| Secondary arm | imatrix Q4_K_M |

## Suite: `conditional-200` (seed 20261109)
- **New tools and new entities.** None of the tools or entities come from the earlier suite, and the generator asserts that none of the entities appear in the imatrix calibration text.
- **10 decision structures:**
  - kb: search, then ticket
  - dup: check for duplicates, then ticket
  - stock: threshold, then reorder
  - svc: status, then restart
  - metric: threshold, then alert
  - cal: free, then meeting
  - order: cancelled, then refund
  - cust: opt-in, then email
  - pay: balance, then pay invoice
  - backup: age, then backup
- **5 hand-written phrasings per structure**, giving 50 patterns. Each pattern has 4 instances: 2 where the check result says act, and 2 where it says don't.
- **Totals:** 200 tasks, 100 act and 100 no-act.
- **Every task has two steps:**
  - Step 1 is a read-only check, and its mock result decides the outcome.
  - Step 2 is either the side-effect call, or no call at all.
- **Harness:** v3 scorer. The harness is strictly sequential, so the model never gets the check result until it has finished the step-1 turn.

## Conditions
- **Primary:** sampled, T = 0.7, 5 runs per task (seeds 0–4).
- **Secondary:** greedy, T = 0, 1 run.
- The two conditions are never pooled.

## Primary endpoint and test (one test, α = 0.05, two-sided)
- **Endpoint:** for each task, whether at least one of its 5 runs has a `premature_action` (a conservative "any run" endpoint).
- **Test:** exact McNemar test of Q4_K_M against F16, paired by task.
- **Effect size:** Δ = proportion(Q4) − proportion(F16), with a 95% task-clustered bootstrap CI from 10,000 resamples.
- **Decision:**
  - **CONFIRMED** if p < 0.05 **and** Δ ≥ +5 points **and** the lower bound of the CI is above 0.
  - **CONTRADICTED** if p < 0.05 and Δ < 0.
  - **NOT CONFIRMED** otherwise.
- **Robustness (reported next to the decision):**
  - Q4 should show more premature tasks than F16 in at least 6 of the 10 structures. If it doesn't, the effect is reported as "concentrated".
  - The greedy result should point in the same direction.

## Secondary (all labelled secondary)
- Two comparisons, Holm-corrected together: imat-Q4 against F16, and imat-Q4 against Q4, on the same endpoint.
- Premature runs per 100 runs.
- Pass rate per run, reported separately for act and no-act tasks.
- The distribution of how many of the 5 runs each task passes.
- Premature-action counts for each structure.

## Power (planning estimate from the pilot)
- **Pilot rates:** in the pilot, F16 had about 12% of tasks with a premature action, and Q4 added only new events (8 to 17 tasks out of 200 discordant, all in one direction).
- **Detectable effects:** with 200 paired tasks and α = 0.05, the study has 80% power for Δ ≈ 6 points if the discordance is mostly one-sided, and Δ ≈ 10 points if q ≈ 0.2 (reviewers' estimate: n ≈ 157 for 10 points).
- **Not tested here:** effects smaller than about 5 points.

## Known limits (stated in advance)
- The tasks are still generated from templates, though there are 50 hand-written patterns across 10 structures.
- The study uses one model family, one backend and one system prompt.
- The mocks are not stateful.
- This study tests premature actions only. It does not test general agent quality or production safety.
