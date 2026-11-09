"""Analysis exactly as PREREG.md specifies. usage: python3 analyze.py greedy/report.json [sampled/report.json]
Writes ANALYSIS.md + analysis.json next to this file. Pure stdlib; self-tests run on import (python3 analyze.py --selftest)."""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = 10_000
ALPHA = 0.05


# ---------- statistics
def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def mcnemar_exact(b, c):
    """Two-sided exact McNemar = binomial test on the discordant pairs, p=0.5."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def holm(pvals):
    """{name: p} -> {name: adjusted p} (Holm-Bonferroni, monotone)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def bootstrap_diff(ref_vals, cand_vals, seed=0):
    """Task-clustered paired bootstrap CI for mean(cand) - mean(ref). Inputs: per-task values, same task order."""
    rng = random.Random(seed)
    n = len(ref_vals)
    diffs = [c - r for r, c in zip(ref_vals, cand_vals)]
    stats = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return sum(diffs) / n, stats[int(0.025 * B)], stats[int(0.975 * B) - 1]


def _selftest():
    assert abs(mcnemar_exact(0, 6) - 0.03125) < 1e-9 and abs(mcnemar_exact(0, 5) - 0.0625) < 1e-9
    assert mcnemar_exact(3, 3) == 1.0 and mcnemar_exact(0, 0) == 1.0
    lo, hi = wilson(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3
    h = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert abs(h["a"] - 0.03) < 1e-9 and abs(h["c"] - 0.06) < 1e-9 and abs(h["b"] - 0.06) < 1e-9
    d, lo, hi = bootstrap_diff([1] * 50 + [0] * 50, [1] * 50 + [0] * 50)
    assert d == 0 and lo == 0 and hi == 0


_selftest()


# ---------- data
def task_table(model):
    """{task_id: (majority_pass: bool, run_fraction: float, category, unrequested: bool)}"""
    out = {}
    for t in model["tasks"]:
        runs = [r["passed"] for r in t["runs"]]
        k = sum(runs)
        unreq = any(st["unrequested_action"] for r in t["runs"] for st in r["steps"])
        out[t["id"]] = (k * 2 > len(runs), k / len(runs), t["category"], unreq)
    return out


def short(name):
    return name.replace("qwen2.5-1.5b-instruct-fp16.gguf", "F16").replace("qwen1.5b-", "").replace(".gguf", "")


def analyze(path):
    p = json.load(open(path))
    ref = task_table(p["reference"])
    ids = sorted(ref)
    cats = sorted({v[2] for v in ref.values()})
    models = {short(p["reference"]["model"]): ref} | {short(c["model"]): task_table(c) for c in p["candidates"]}
    rows, tests = {}, {}
    for name, tab in models.items():
        k = sum(tab[i][0] for i in ids)
        lo, hi = wilson(k, len(ids))
        row = {"pass": k / len(ids), "ci": (lo, hi), "run_pass": sum(tab[i][1] for i in ids) / len(ids),
               "unreq_tasks": sorted(i for i in ids if tab[i][3]),
               "by_cat": {c: sum(tab[i][0] for i in ids if tab[i][2] == c) / sum(tab[i][2] == c for i in ids) for c in cats}}
        if tab is not ref:
            b = sum(ref[i][0] and not tab[i][0] for i in ids)
            c = sum(not ref[i][0] and tab[i][0] for i in ids)
            d, dlo, dhi = bootstrap_diff([float(ref[i][0]) for i in ids], [float(tab[i][0]) for i in ids])
            rd, rlo, rhi = bootstrap_diff([ref[i][1] for i in ids], [tab[i][1] for i in ids], seed=1)
            row.update({"b": b, "c": c, "diff": d, "diff_ci": (dlo, dhi), "run_diff": rd, "run_diff_ci": (rlo, rhi),
                        "regressed": sorted(i for i in ids if ref[i][0] and not tab[i][0])})
            tests[f"{name} vs F16"] = mcnemar_exact(b, c)
        rows[name] = row
    for q in ("Q6_K", "Q4_K_M", "Q3_K_M"):  # H2: imatrix vs plain at the same level
        a, m = models[q], models[f"imat-{q}"]
        b = sum(a[i][0] and not m[i][0] for i in ids)
        c = sum(not a[i][0] and m[i][0] for i in ids)
        d, dlo, dhi = bootstrap_diff([float(a[i][0]) for i in ids], [float(m[i][0]) for i in ids], seed=2)
        rows[f"imat-{q} vs {q}"] = {"b": b, "c": c, "diff": d, "diff_ci": (dlo, dhi)}
        tests[f"imat-{q} vs {q}"] = mcnemar_exact(b, c)
    adj = holm(tests)
    return {"n_tasks": len(ids), "repeats": p["suite"]["repeats"], "temperature": p["suite"]["temperature"],
            "rows": rows, "p": tests, "p_holm": adj, "cats": cats,
            "verdicts": {short(c["model"]): c["verdicts"] for c in p["candidates"]}}


def hypotheses(a):
    r = a["rows"]
    gap = {q: -r[q]["diff"] for q in ("Q8_0", "Q6_K", "Q4_K_M", "Q3_K_M")}
    h1 = all(gap[x] <= gap[y] + 1e-9 for x, y in zip(list(gap)[:-1], list(gap)[1:]))
    h1_sig = [q for q in gap if a["p_holm"][f"{q} vs F16"] < ALPHA]
    h2 = {q: (r[f"imat-{q} vs {q}"]["diff"], a["p_holm"][f"imat-{q} vs {q}"]) for q in ("Q6_K", "Q4_K_M", "Q3_K_M")}
    ref_unreq = set(r["F16"]["unreq_tasks"])
    h3 = [(m, sorted(set(v["unreq_tasks"]) - ref_unreq)) for m, v in r.items()
          if "diff" in v and "vs" not in m and abs(v["diff"]) <= 0.02 and len(v["unreq_tasks"]) > len(ref_unreq)]
    drops = {c: sum(r["F16"]["by_cat"][c] - r[q]["by_cat"][c] for q in ("Q6_K", "Q4_K_M", "Q3_K_M")) / 3 for c in a["cats"]}
    return {"H1": (h1, gap, h1_sig), "H2": h2, "H3": h3, "H4": drops}


def fmt(a, title):
    r = a["rows"]
    L = [f"## {title}: {a['n_tasks']} tasks × {a['repeats']} run(s), temperature {a['temperature']}", "",
         "| Model | Pass (task) | 95% Wilson CI | Δ vs F16 [95% bootstrap CI] | b / c | McNemar p | Holm p | Tasks w/ unrequested side effect | Verdicts Q/R/S |",
         "|---|---|---|---|---|---|---|---|---|"]
    for m, v in r.items():
        if "vs" in m:
            continue
        if m == "F16":
            L.append(f"| **F16 (ref)** | {v['pass']:.1%} | {v['ci'][0]:.1%}–{v['ci'][1]:.1%} | — | — | — | — | {len(v['unreq_tasks'])} | — |")
            continue
        vd = a["verdicts"][m]
        L.append(f"| {m} | {v['pass']:.1%} | {v['ci'][0]:.1%}–{v['ci'][1]:.1%} | {v['diff']:+.1%} [{v['diff_ci'][0]:+.1%}, {v['diff_ci'][1]:+.1%}] "
                 f"| {v['b']} / {v['c']} | {a['p'][m + ' vs F16']:.3g} | {a['p_holm'][m + ' vs F16']:.3g} | {len(v['unreq_tasks'])} "
                 f"| {vd['quality'][0]}/{vd['regression'][0]}/{vd['safety'][0]} |")
    L += ["", "b = tasks F16 passes and the candidate fails; c = the reverse. Δ is candidate − F16 (task-level majority pass).", "",
          "| imatrix vs plain | Δ (imat − plain) [95% CI] | b / c | McNemar p | Holm p |", "|---|---|---|---|---|"]
    for q in ("Q6_K", "Q4_K_M", "Q3_K_M"):
        v = r[f"imat-{q} vs {q}"]
        L.append(f"| {q} | {v['diff']:+.1%} [{v['diff_ci'][0]:+.1%}, {v['diff_ci'][1]:+.1%}] | {v['b']} / {v['c']} "
                 f"| {a['p'][f'imat-{q} vs {q}']:.3g} | {a['p_holm'][f'imat-{q} vs {q}']:.3g} |")
    L += ["", "| Category | " + " | ".join(m for m in r if "vs" not in m) + " |", "|---|" + "---|" * sum("vs" not in m for m in r)]
    for c in a["cats"]:
        L.append(f"| {c} | " + " | ".join(f"{r[m]['by_cat'][c]:.0%}" for m in r if "vs" not in m) + " |")
    h = hypotheses(a)
    h1, gap, sig = h["H1"]
    L += ["", "### Hypotheses", "",
          f"- **H1** (gap grows as bits drop, Q8≤Q6≤Q4≤Q3): **{'supported' if h1 else 'not supported'}** in ordering. "
          f"Gaps: " + ", ".join(f"{q} {g:+.1%}" for q, g in gap.items()) + f". Significant after Holm: {sig or 'none'}.",
          "- **H2** (imatrix beats plain): " + "; ".join(f"{q} Δ {d:+.1%} (Holm p {pp:.3g})" for q, (d, pp) in h["H2"].items())
          + f". **{'supported' if any(d > 0 and pp < ALPHA for d, pp in h['H2'].values()) else 'not supported'}** (needs a significant positive Δ).",
          f"- **H3** (within 2 points of F16 but more unrequested side-effect tasks): **{'supported' if h['H3'] else 'not supported'}**. "
          + ("; ".join(f"{m}: new {t}" for m, t in h["H3"]) or "no such candidate"),
          "- **H4** (chain/conditional lose most, single least; mean drop over Q6/Q4/Q3 plain): "
          + ", ".join(f"{c} {d:+.1%}" for c, d in sorted(h["H4"].items(), key=lambda kv: -kv[1])) + ". "
          + f"**{'supported' if max(h['H4'], key=h['H4'].get) in ('chain', 'conditional') and min(h['H4'], key=h['H4'].get) == 'single' else 'not supported'}**.",
          "", "Unrequested side-effect tasks per model: " + "; ".join(f"{m}: {v['unreq_tasks'] or '—'}" for m, v in r.items() if "vs" not in m), ""]
    return "\n".join(L)


def main(argv):
    if argv == ["--selftest"]:
        print("selftest ok")
        return
    out, js = ["# Controlled experiment results (analysis per PREREG.md)", ""], {}
    for path in argv:
        a = analyze(path)
        name = "greedy" if a["temperature"] == 0 else "sampled"
        out.append(fmt(a, name))
        js[name] = {k: v for k, v in a.items()}
    open(os.path.join(HERE, "ANALYSIS.md"), "w").write("\n".join(out))
    json.dump(js, open(os.path.join(HERE, "analysis.json"), "w"), indent=1, default=str)
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1:])
