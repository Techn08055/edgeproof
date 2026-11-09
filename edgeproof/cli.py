import argparse
import datetime
import json
import os
import platform
import subprocess
import sys

from . import backend, report, runner, suite as suite_mod, verdict

EXIT = {"PASS": 0, "REVIEW": 1, "FAIL": 2}


def llama_commit():
    try:
        d = os.path.dirname(backend.find_server())
        return subprocess.run(["git", "-C", d, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="edgeproof")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a suite on reference + candidates and write a report")
    r.add_argument("suite")
    r.add_argument("--reference", required=True)
    r.add_argument("--candidate", required=True, nargs="+")
    r.add_argument("--thresholds", help="YAML with `rules:`; default rules if omitted")
    r.add_argument("--out", default="reports/latest")
    r.add_argument("--repeats", type=int, help="override suite repeats")
    r.add_argument("--temperature", type=float, help="override suite temperature")
    r.add_argument("--port", type=int, default=backend.DEFAULT_PORT)
    r.add_argument("--cache", default=".edgeproof_cache", help="reuse results per (model sha, suite, code); '' disables")
    i = sub.add_parser("init", help="write a starter suite.yaml to edit for your own agent")
    i.add_argument("path", nargs="?", default="suite.yaml")
    i.add_argument("--from", dest="src", default="starter", choices=["starter", "agent-30"])
    j = sub.add_parser("rejudge", help="re-apply rules to a saved report.json (no models needed)")
    j.add_argument("report")
    j.add_argument("--thresholds")
    j.add_argument("--suite", help="also re-score every recorded call with the current scorer")
    j.add_argument("--out", help="write the re-judged report here instead of next to the input")
    a = ap.parse_args(argv)
    if a.cmd == "rejudge":
        return rejudge(a)
    if a.cmd == "init":
        if os.path.exists(a.path):
            sys.exit(f"{a.path} already exists; not overwriting")
        src = os.path.join(os.path.dirname(__file__), "suites", f"{a.src}.yaml")
        open(a.path, "w").write(open(src).read())
        print(f"wrote {a.path}: edit tools + tasks, then: edgeproof run {a.path} --reference REF.gguf --candidate Q4.gguf")
        return 0
    try:
        backend.find_server()
    except FileNotFoundError as e:
        sys.exit(str(e))

    s = suite_mod.load(a.suite)
    if a.repeats:
        s["repeats"] = a.repeats
    if a.temperature is not None:
        s["temperature"] = a.temperature
    rules = verdict.load_rules(a.thresholds)
    os.makedirs(a.out, exist_ok=True)
    log = lambda m: os.path.join(a.out, f"server_{os.path.basename(m)}.log")

    print(f"reference: {a.reference}")
    ref = runner.run_model(a.reference, s, a.port, log(a.reference), cache_dir=a.cache or None)
    cands = []
    for m in a.candidate:
        print(f"candidate: {m}")
        cands.append(runner.run_model(m, s, a.port, log(m), cache_dir=a.cache or None))

    payload = {
        "suite": {"name": s.get("name", os.path.basename(a.suite)), "sha256": s["sha256"],
                  "n_tasks": len(s["tasks"]), "repeats": s["repeats"], "temperature": s["temperature"]},
        "rules": rules, "rules_version": verdict.RULES_VERSION, "reference": ref, "candidates": cands,
        "env": {"gpu": backend.gpu_info(), "llama_cpp": llama_commit(), "python": platform.python_version(),
                "host": platform.platform(), "time": datetime.datetime.now().isoformat(timespec="seconds")},
    }
    judge(payload, rules)
    report.write(a.out, payload)
    return summarize(payload, a.out)


def judge(payload, rules):
    payload["rules"] = rules
    for c in payload["candidates"]:
        c["values"] = verdict.compare(payload["reference"], c)
        c["verdict"], c["verdicts"], c["notes"] = verdict.decide(c["values"], rules)


def rejudge(a):
    payload = json.load(open(a.report))
    if a.suite:
        s = suite_mod.load(a.suite)
        for m in [payload["reference"]] + payload["candidates"]:
            runner.rescore(m, s)
    judge(payload, verdict.load_rules(a.thresholds))
    out = a.out or os.path.dirname(a.report)
    os.makedirs(out, exist_ok=True)
    report.write(out, payload)
    return summarize(payload, out)


def summarize(payload, out):
    ref, cands = payload["reference"], payload["candidates"]

    print(f"\nreference {ref['model']}: pass {ref['metrics']['pass_rate']:.1%}")
    for c in cands:
        v = c["values"]
        g = c["verdicts"]
        print(f"{c['verdict']:6} {c['model']}: QUALITY {g['quality']} · REGRESSION {g['regression']} · SAFETY {g['safety']}"
              f"  | pass {v['pass_rate']:.1%} ({v['pass_rate_drop']:+.1%} drop), regressions {v['regressions']}")
        if v["new_unrequested_tasks"] or v["shared_unrequested_tasks"]:
            print(f"         unrequested side-effect calls: new {v['new_unrequested_tasks']}, also in reference {v['shared_unrequested_tasks']}")
        for n in c["notes"]:
            print(f"         {n['group']}/{n['level']}: {n['metric']}={n['value']} ({n['why']})")
    print(f"report: {os.path.join(out, 'report.html')}")
    return max((EXIT[c["verdict"]] for c in cands), default=0)


if __name__ == "__main__":
    sys.exit(main())
