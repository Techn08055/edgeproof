"""Readouts exactly as PLAN.md. usage: python3 analyze.py  -> ANALYSIS.md (skips conditions not yet run)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "controlled-qwen"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from analyze import mcnemar_exact  # noqa: E402
from edgeproof import suite as suite_mod  # noqa: E402

NAMES = {"qwen2.5-1.5b-instruct-fp16.gguf": "F16", "qwen1.5b-Q4_K_M.gguf": "Q4", "qwen1.5b-imat-Q4_K_M.gguf": "imat-Q4"}


def load(cond):
    path = (os.path.join(HERE, "..", "confirm-premature", "sampled", "report.json") if cond == "baseline"
            else os.path.join(HERE, cond, "report.json"))
    if not os.path.exists(path):
        return None
    p = json.load(open(path))
    keep = None
    if cond == "baseline":  # same 100-task subset as wait / two_tools
        keep = {t["id"] for t in suite_mod.load(os.path.join(HERE, "suites", "wait.yaml"))["tasks"]}
    out = {}
    for m in [p["reference"]] + p["candidates"]:
        out[NAMES[m["model"]]] = [t for t in m["tasks"] if keep is None or t["id"] in keep]
    return out


def premature_sets(tasks, check_tool):
    par, skip = set(), set()
    for t in tasks:
        chk = check_tool[t["id"]]
        for r in t["runs"]:
            for st in r["steps"]:
                if st.get("premature_action"):
                    (par if chk in [c["tool"] for c in st["got_calls"]] else skip).add(t["id"])
    return par | skip, par, skip


def side_sets(tasks, side):
    return {t["id"] for t in tasks if any(c["tool"] in side for r in t["runs"] for st in r["steps"] for c in st["got_calls"])}


def pair(ref, cand):
    b, c = len(cand - ref), len(ref - cand)
    return f"{b}/{c}, p={mcnemar_exact(b, c):.2g}"


def main():
    base = suite_mod.load(os.path.join(HERE, "..", "confirm-premature", "suite.yaml"))
    side = suite_mod.side_effect_tools(base)
    L = ["# Control experiments (diagnostic; readouts per PLAN.md)", "",
         "Pairs are `candidate-only / F16-only` task counts, with an exact McNemar p.", "",
         "## Premature side-effect attempts on the 100-task conditional subset", "",
         "| Condition | F16 tasks (par / skip) | Q4 tasks (par / skip) | imat-Q4 tasks (par / skip) | Q4 vs F16 | imat-Q4 vs F16 |",
         "|---|---|---|---|---|---|"]
    for cond in ("baseline", "wait", "two_tools"):
        d = load(cond)
        if not d:
            L.append(f"| {cond} | not run | | | | |")
            continue
        chk = {t["id"]: t["steps"][0]["expect"]["calls"][0]["tool"] for t in base["tasks"]}
        s = {k: premature_sets(v, chk) for k, v in d.items()}
        cell = lambda k: f"{len(s[k][0])} ({len(s[k][1])} / {len(s[k][2])})"  # noqa: E731
        L.append(f"| {cond} | {cell('F16')} | {cell('Q4')} | {cell('imat-Q4')} | {pair(s['F16'][0], s['Q4'][0])} "
                 f"| {pair(s['F16'][0], s['imat-Q4'][0])} |")
    d = load("check_only")
    L += ["", "## check_only: user asks only for the check and says not to act", ""]
    if d:
        s = {k: side_sets(v, side) for k, v in d.items()}
        runs = {k: sum(any(c["tool"] in side for st in r["steps"] for c in st["got_calls"]) for t in v for r in t["runs"])
                for k, v in d.items()}
        L += ["| Model | Tasks with any side-effect call (of 100) | Runs with one (of 500) |", "|---|---|---|"]
        L += [f"| {k} | {len(s[k])} | {runs[k]} |" for k in s]
        L += ["", f"Q4 vs F16: {pair(s['F16'], s['Q4'])}; imat-Q4 vs F16: {pair(s['F16'], s['imat-Q4'])}"]
    else:
        L.append("not run")
    d = load("direct")
    L += ["", "## direct: user asks for the action outright", ""]
    if d:
        L += ["| Model | Run pass rate | Runs that only checked instead of acting | Runs with no call |", "|---|---|---|---|"]
        for k, v in d.items():
            runs = [r for t in v for r in t["runs"]]
            checked = sum(all(c["tool"] not in side for c in r["steps"][0]["got_calls"]) and r["steps"][0]["got_calls"] != []
                          for r in runs)
            none = sum(r["steps"][0]["got_calls"] == [] for r in runs)
            L.append(f"| {k} | {sum(r['passed'] for r in runs) / len(runs):.1%} | {checked} | {none} |")
    else:
        L.append("not run")
    open(os.path.join(HERE, "ANALYSIS.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
