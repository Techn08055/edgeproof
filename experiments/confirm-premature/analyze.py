"""Confirmatory analysis exactly as PREREG.md. usage: python3 analyze.py sampled/report.json greedy/report.json
Writes ANALYSIS.md. Self-test on synthetic data runs on import."""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "controlled-qwen"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from analyze import bootstrap_diff, holm, mcnemar_exact, wilson  # noqa: E402

REF, PRIMARY, SECONDARY = "F16", "Q4_K_M", "imat-Q4_K_M"
MIN_EFFECT = 0.05  # practically meaningful: >= 5 points more tasks with a premature action


def short(name):
    return {"qwen2.5-1.5b-instruct-fp16.gguf": "F16"}.get(name, name.replace("qwen1.5b-", "").replace(".gguf", ""))


def table(model):
    """{task: (any_premature, premature_runs, n_runs, pass_runs, category)}"""
    return {t["id"]: (any(st.get("premature_action") for r in t["runs"] for st in r["steps"]),
                      sum(any(st.get("premature_action") for st in r["steps"]) for r in t["runs"]),
                      len(t["runs"]), sum(r["passed"] for r in t["runs"]), t["category"]) for t in model["tasks"]}


def paired(a, b, ids, seed=0):
    """b vs a on the any-premature indicator: (only_b, only_a, p, diff, lo, hi)."""
    only_b = sum(b[i][0] and not a[i][0] for i in ids)
    only_a = sum(a[i][0] and not b[i][0] for i in ids)
    d, lo, hi = bootstrap_diff([float(a[i][0]) for i in ids], [float(b[i][0]) for i in ids], seed=seed)
    return only_b, only_a, mcnemar_exact(only_b, only_a), d, lo, hi


def decide(p, d, lo):
    if p < 0.05 and d >= MIN_EFFECT and lo > 0:
        return "CONFIRMED"
    if p < 0.05 and d < 0:
        return "CONTRADICTED (effect in the opposite direction)"
    return "NOT CONFIRMED"


def analyze(sampled, greedy, act_of):
    m = {short(x["model"]): table(x) for x in [sampled["reference"]] + sampled["candidates"]}
    g = {short(x["model"]): table(x) for x in [greedy["reference"]] + greedy["candidates"]} if greedy else None
    ids = sorted(m[REF])
    out = {"n": len(ids)}
    b, c, p, d, lo, hi = paired(m[REF], m[PRIMARY], ids)
    out["primary"] = {"only_q4": b, "only_f16": c, "p": p, "diff": d, "ci": (lo, hi), "decision": decide(p, d, lo)}
    sec = {f"{SECONDARY} vs {REF}": paired(m[REF], m[SECONDARY], ids, 1),
           f"{SECONDARY} vs {PRIMARY}": paired(m[PRIMARY], m[SECONDARY], ids, 2)}
    adj = holm({k: v[2] for k, v in sec.items()})
    out["secondary"] = {k: {"only_second": v[0], "only_first": v[1], "p": v[2], "p_holm": adj[k], "diff": v[3],
                            "ci": (v[4], v[5])} for k, v in sec.items()}
    cats = sorted({v[4] for v in m[REF].values()})
    per = {}
    for cat in cats:
        ci = [i for i in ids if m[REF][i][4] == cat]
        per[cat] = {k: sum(m[k][i][0] for i in ci) for k in m}
    out["by_structure"] = per
    out["structures_q4_higher"] = sum(v[PRIMARY] > v[REF] for v in per.values())
    out["structures_q4_lower"] = sum(v[PRIMARY] < v[REF] for v in per.values())
    out["models"] = {}
    for k, t in m.items():
        runs = sum(v[2] for v in t.values())
        acts = [i for i in ids if act_of[i]]
        noacts = [i for i in ids if not act_of[i]]
        out["models"][k] = {
            "tasks_premature": sum(v[0] for v in t.values()), "ci": wilson(sum(v[0] for v in t.values()), len(ids)),
            "premature_per_100_runs": 100 * sum(v[1] for v in t.values()) / runs,
            "pass_run_act": sum(t[i][3] for i in acts) / sum(t[i][2] for i in acts),
            "pass_run_noact": sum(t[i][3] for i in noacts) / sum(t[i][2] for i in noacts),
            "pass_dist": dict(sorted(collections.Counter(v[3] for v in t.values()).items()))}
    if g:
        gb, gc, gp, gd, glo, ghi = paired(g[REF], g[PRIMARY], ids, 3)
        out["greedy"] = {"only_q4": gb, "only_f16": gc, "p": gp, "diff": gd, "ci": (glo, ghi),
                         "tasks": {k: sum(v[0] for v in t.values()) for k, t in g.items()}}
    return out


def fmt(a):
    pr = a["primary"]
    L = ["# Confirmatory study: premature side-effect actions (analysis per PREREG.md)", "",
         f"## Primary endpoint (sampled, T=0.7, 5 runs; {a['n']} tasks)", "",
         f"Tasks with >=1 premature action: Q4_K_M only **{pr['only_q4']}**, F16 only **{pr['only_f16']}**. "
         f"Δ = {pr['diff']:+.1%} [95% CI {pr['ci'][0]:+.1%}, {pr['ci'][1]:+.1%}], exact McNemar p = {pr['p']:.3g}.", "",
         f"**Decision: {pr['decision']}** (rule: p < 0.05 and Δ ≥ +{MIN_EFFECT:.0%} and CI lower bound > 0).", "",
         f"Spread: Q4_K_M higher than F16 in {a['structures_q4_higher']}/10 structures, lower in {a['structures_q4_lower']} "
         "(pre-registered robustness: higher in ≥ 6 of 10, else 'concentrated').", "",
         "## Per model (sampled)", "",
         "| Model | Tasks w/ premature action [95% CI] | Premature runs / 100 | Run pass, act tasks | Run pass, no-act tasks | Tasks by passes 0..5 |",
         "|---|---|---|---|---|---|"]
    for k, v in a["models"].items():
        L.append(f"| {k} | {v['tasks_premature']} [{v['ci'][0]:.0%}–{v['ci'][1]:.0%}] | {v['premature_per_100_runs']:.1f} "
                 f"| {v['pass_run_act']:.1%} | {v['pass_run_noact']:.1%} | {v['pass_dist']} |")
    L += ["", "## Secondary (Holm over these 2)", "", "| Comparison | only 2nd / only 1st | Δ [95% CI] | p | Holm p |", "|---|---|---|---|---|"]
    for k, v in a["secondary"].items():
        L.append(f"| {k} | {v['only_second']} / {v['only_first']} | {v['diff']:+.1%} [{v['ci'][0]:+.1%}, {v['ci'][1]:+.1%}] "
                 f"| {v['p']:.3g} | {v['p_holm']:.3g} |")
    names = list(a["models"])
    L += ["", "## Tasks with a premature action, by decision structure (20 tasks each)", "",
          "| Structure | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for cat, v in a["by_structure"].items():
        L.append(f"| {cat} | " + " | ".join(str(v[n]) for n in names) + " |")
    if "greedy" in a:
        gr = a["greedy"]
        L += ["", "## Secondary: greedy (T=0, 1 run)", "",
              f"Q4_K_M only {gr['only_q4']}, F16 only {gr['only_f16']}, Δ {gr['diff']:+.1%} "
              f"[{gr['ci'][0]:+.1%}, {gr['ci'][1]:+.1%}], p = {gr['p']:.3g}. Tasks: {gr['tasks']}. "
              f"Same direction as primary: **{'yes' if (gr['diff'] > 0) == (pr['diff'] > 0) else 'no'}**."]
    return "\n".join(L) + "\n"


def _fake(name, prem, runs=5):
    return {"model": name, "tasks": [{"id": f"t{i}", "category": f"s{i % 10}", "runs": [
        {"passed": not (p and r == 0), "steps": [{"premature_action": bool(p and r == 0)}]} for r in range(runs)]}
        for i, p in enumerate(prem)]}


def _selftest():
    act = {f"t{i}": i % 2 == 0 for i in range(200)}
    f16 = [i < 20 for i in range(200)]
    q4 = [i < 50 for i in range(200)]
    rep = {"reference": _fake("qwen2.5-1.5b-instruct-fp16.gguf", f16),
           "candidates": [_fake("qwen1.5b-Q4_K_M.gguf", q4), _fake("qwen1.5b-imat-Q4_K_M.gguf", f16)]}
    a = analyze(rep, None, act)
    assert (a["primary"]["only_q4"], a["primary"]["only_f16"]) == (30, 0) and a["primary"]["decision"] == "CONFIRMED"
    assert abs(a["primary"]["diff"] - 0.15) < 1e-9 and a["models"]["F16"]["premature_per_100_runs"] == 2.0
    rep["candidates"][0] = _fake("qwen1.5b-Q4_K_M.gguf", [i < 22 for i in range(200)])
    assert analyze(rep, None, act)["primary"]["decision"] == "NOT CONFIRMED"
    rep["candidates"][0] = _fake("qwen1.5b-Q4_K_M.gguf", [False] * 200)
    assert analyze(rep, None, act)["primary"]["decision"].startswith("CONTRADICTED")


_selftest()


def main(argv):
    from edgeproof import suite as suite_mod
    act = {t["id"]: t["act"] for t in suite_mod.load(os.path.join(HERE, "suite.yaml"))["tasks"]}
    sampled = json.load(open(argv[0]))
    greedy = json.load(open(argv[1])) if len(argv) > 1 else None
    text = fmt(analyze(sampled, greedy, act))
    open(os.path.join(HERE, "ANALYSIS.md"), "w").write(text)
    print(text)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        print("selftest ok")
    else:
        main(sys.argv[1:])
