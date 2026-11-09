"""EXPLORATORY audit (not pre-registered), written after the reviews. Reads the v3 re-scored reports.
usage: python3 audit.py  -> AUDIT.md
1. Every unrequested side-effect event, classified:
     prohibited  = the prompt explicitly forbids it (negation tasks)
     premature   = the ticket would be correct later, but was opened before the search result came back
     wrong_call  = a ticket the task never wants (no_tool, conditional-with-hit, ...)
2. Premature-action tasks per model, paired against F16 (exact McNemar, Holm over the 7 candidates).
3. Tasks Q3 / imat-Q3 pass that F16 fails, and why F16 failed them.
4. Per-task pass-count distribution (sampled), so 3/5 isn't hidden behind a majority PASS."""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from edgeproof import suite as suite_mod  # noqa: E402
from analyze import holm, mcnemar_exact, short  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
S = suite_mod.load(os.path.join(HERE, "suite.yaml"))
SPEC = {t["id"]: t for t in S["tasks"]}
SIDE = suite_mod.side_effect_tools(S)


def classify(tid, k):
    spec = SPEC[tid]
    if spec["category"] == "negation":
        return "prohibited"
    later = {c["tool"] for st in spec["steps"][k + 1:] for c in st["expect"]["calls"]}
    return "premature" if later & SIDE else "wrong_call"


assert classify("negation-001", 0) == "prohibited" and classify("no_tool-001", 0) == "wrong_call"
assert classify("conditional-001", 0) == "premature" and classify("conditional-011", 0) == "wrong_call"


def events(m):
    """{task: set of classes} over all runs."""
    out = collections.defaultdict(set)
    for t in m["tasks"]:
        for r in t["runs"]:
            for k, st in enumerate(r["steps"]):
                if st["unrequested_action"]:
                    out[t["id"]].add(classify(t["id"], k))
    return out


def premature_tasks(m):
    return {t["id"] for t in m["tasks"] if any(st.get("premature_action") for r in t["runs"] for st in r["steps"])}


def main():
    L = ["# Exploratory audit (post-hoc, NOT pre-registered)", "",
         "Re-scored with the v3 scorer (optimal call matching, `premature_action`). "
         "Pass/fail changed for 0 runs in both conditions versus the pre-registered analysis.", ""]
    for cond in ("greedy", "sampled"):
        p = json.load(open(os.path.join(HERE, f"{cond}-v3", "report.json")))
        models = [p["reference"]] + p["candidates"]
        ids = [t["id"] for t in p["reference"]["tasks"]]
        L += [f"## {cond}", "", "### 1. Unrequested side-effect tasks by kind", "",
              "| Model | prohibited (negation) | premature (right ticket, too early) | wrong_call (ticket never wanted) | total tasks |",
              "|---|---|---|---|---|"]
        for m in models:
            ev = events(m)
            cnt = collections.Counter(c for cs in ev.values() for c in cs)
            L.append(f"| {short(m['model'])} | {cnt['prohibited']} | {cnt['premature']} | {cnt['wrong_call']} | {len(ev)} |")
        ref_p = premature_tasks(p["reference"])
        L += ["", "### 2. Tasks with any premature action (dependent call or side effect before the result), paired vs F16", "",
              "| Model | tasks | only candidate | only F16 | McNemar p | Holm p (7) |", "|---|---|---|---|---|---|",
              f"| F16 | {len(ref_p)} | — | — | — | — |"]
        rows, ps = [], {}
        for m in p["candidates"]:
            mp = premature_tasks(m)
            b, c = len(mp - ref_p), len(ref_p - mp)
            ps[short(m["model"])] = mcnemar_exact(b, c)
            rows.append((short(m["model"]), len(mp), b, c))
        adj = holm(ps)
        L += [f"| {n} | {k} | {b} | {c} | {ps[n]:.3g} | {adj[n]:.3g} |" for n, k, b, c in rows]
        by_cat = {short(m["model"]): collections.Counter(SPEC[t]["category"] for t in premature_tasks(m)) for m in models}
        L += ["", "Premature-action tasks by category: " + "; ".join(f"{n}: {dict(c)}" for n, c in by_cat.items()), ""]

        ref = {t["id"]: t for t in p["reference"]["tasks"]}
        L += ["### 3. Where Q3 beats F16 (tasks the candidate passes by majority and F16 fails)", ""]
        for m in p["candidates"]:
            if "Q3" not in m["model"]:
                continue
            maj = lambda t: sum(r["passed"] for r in t["runs"]) * 2 > len(t["runs"])  # noqa: E731
            gains = [t["id"] for t in m["tasks"] if maj(t) and not maj(ref[t["id"]])]
            why = collections.Counter(f for i in gains for r in ref[i]["runs"] for st in r["steps"] for f in st["failures"])
            cats = collections.Counter(SPEC[i]["category"] for i in gains)
            L.append(f"- **{short(m['model'])}**: {len(gains)} tasks, by category {dict(cats)}; "
                     f"F16's failure types on them {dict(why)}")
        if cond == "sampled":
            L += ["", "### 4. Per-task pass count out of 5", "", "| Model | 0 | 1 | 2 | 3 | 4 | 5 | mean per-run pass |",
                  "|---|---|---|---|---|---|---|---|"]
            for m in models:
                d = collections.Counter(sum(r["passed"] for r in t["runs"]) for t in m["tasks"])
                mean = sum(k * v for k, v in d.items()) / (5 * len(ids))
                L.append(f"| {short(m['model'])} | " + " | ".join(str(d[k]) for k in range(6)) + f" | {mean:.1%} |")
        L.append("")
    open(os.path.join(HERE, "AUDIT.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
