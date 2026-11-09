# Pre-registration: controlled quantization experiment (Qwen2.5-1.5B-Instruct)

Written **before any run** on 2026-11-08. The suite, rules and analysis code are frozen once this file is committed;
results that disagree with the hypotheses get reported as-is.

## Design
- **One model family:** Qwen2.5-1.5B-Instruct, official F16 GGUF (sha256 recorded in reports).
- **Every quant made by us** from that F16 with the same llama.cpp build (commit a691b23).
  - **No imatrix:** Q8_0, Q6_K, Q4_K_M, Q3_K_M.
  - **imatrix:** Q6_K, Q4_K_M, Q3_K_M, using `llama-imatrix` on `calibration.txt` (general text plus tool-use transcripts). Its tools, cities, file names and topics **do not overlap** with the test suite (the generator checks this).
- **Suite:** `agent-200`, 200 tasks produced by a seeded generator (`make_suite.py`, seed 20261108). Every expected answer is computed by code from the task's own parameters (city, unit, numbers, path, priority), so the answer key is correct by construction. Categories:

  | Category | Tasks |
  |---|---|
  | single | 40 |
  | args | 50 |
  | no_tool | 25 |
  | negation | 15 |
  | parallel | 20 |
  | chain | 30 |
  | conditional | 20 |
- **Two decoding conditions,** analysed separately and never pooled:
  - **greedy:** temperature 0, 1 run per task.
  - **sampled:** temperature 0.7, 5 runs per task, seeds 0–4.
- **Reference** = F16. Same server flags, system prompt and tool schemas for every model.
- **Rules:** EdgeProof rules v1.0 (unchanged).

## Hypotheses
- **H1** (degradation): the pass-rate gap to F16 grows as bits go down: Q8 ≈ F16, then Q6, Q4, Q3 worse.
- **H2** (imatrix): at the same quant level, imatrix gives a higher pass rate than no imatrix. Strongest prediction at Q3_K_M.
- **H3** (hidden safety): at least one candidate whose pass rate is within 2 points of F16 has *more* tasks with unrequested side-effect calls than F16.
- **H4** (category sensitivity): `chain` and `conditional` lose the most under quantization; `single` loses the least.

## Analysis plan (code: `analyze.py`)
- **Unit of analysis = task.** In the sampled condition, a task "passes" if it passes in ≥3 of 5 runs (majority). Per-run pass fractions are reported separately.
- Pass rate with a **Wilson 95% CI** over tasks.
- **Paired candidate vs reference, per task:**
  - **exact McNemar** (two-sided binomial on the discordant tasks);
  - report b (ref pass → cand fail) and c (ref fail → cand pass);
  - pass-rate difference with a **task-clustered bootstrap 95% CI** (10,000 resamples of whole tasks; in the sampled condition the 5 runs stay together inside each task).
- **H2:** the same paired test between the imatrix and no-imatrix quant at each level.
- **Multiple comparisons:** 7 candidates + 3 imatrix pairs = 10 tests per condition. Holm–Bonferroni at α = 0.05 is applied and reported next to the raw p-values.
- **Safety events:** count of tasks with any unrequested side-effect call, plus the exact task list. Reported as events, not as a rate.
- **Failure types:** counts per model, so model-format failures and server/parser failures are reported separately.

## Known limits (stated in advance)
- Generated tasks are templated, so they are less varied than real user prompts. "Correct by construction" means the answer key matches the template. It does **not** mean the task is a natural or fair request.
- One model family and one backend (llama-server, `--jinja`). Results don't transfer to other families or servers.
- In multi-call replies, only the first call gets the canned `mock_result`; other calls get `{"ok": true}`.
