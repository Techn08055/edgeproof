import hashlib
import json
import os
import statistics

from . import backend, checks, suite as suite_mod

TEXT_LIMIT = 300
RAW_LIMIT = 2000


def sha256_file(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def tool_result(call, step, j, tools_by_name):
    if j is not None and "mock_results" in step:
        return step["mock_results"][j]
    if j == 0 and "mock_result" in step:
        return step["mock_result"]
    t = tools_by_name.get(call["tool"], {})
    if "mock" in t:
        return t["mock"]
    if call["tool"] == "calculator" and call["args"]:
        try:
            return {"result": checks.safe_eval(call["args"].get("expression", ""))}
        except ValueError as e:
            return {"error": str(e)}
    return {"error": f"no test result defined for {call['tool']}"}


def later_tools(task, k):
    rest = task["steps"][k + 1:]
    return {c["tool"] for st in rest for c in st["expect"]["calls"]} if rest else None


def run_task(srv, s, task, seed, tools, schemas, side_effects):
    messages = ([{"role": "system", "content": s["system"]}] if s["system"] else []) + \
               [{"role": "user", "content": task["prompt"]}]
    by_name = {t["name"]: t for t in s["tools"]}
    if task.get("tools"):
        tools = [t for t in tools if t["function"]["name"] in task["tools"]]
    steps, latency = [], 0.0
    for k, step in enumerate(task["steps"]):
        msg, ms = srv.chat(messages, tools, s["temperature"], seed, s.get("parallel_tool_calls"))
        latency += ms
        calls = backend.parse_tool_calls(msg)
        r = checks.score_step(step["expect"], [{"tool": c["tool"], "args": c["args"]} for c in calls],
                              schemas, side_effects, error=msg.get("_error"), later=later_tools(task, k))
        r["text"] = (msg.get("content") or "")[:TEXT_LIMIT]
        if "_raw" in msg:
            r["raw"] = msg["_raw"][:RAW_LIMIT]
        r["latency_ms"] = round(ms, 1)
        steps.append(r)
        if not r["passed"] or k == len(task["steps"]) - 1:
            break
        j_of = {i: j for j, i in enumerate(r["assign"]) if i is not None}
        tcs = [{"id": c["raw"].get("id") or f"call_{i}", "type": "function", "function": c["raw"]["function"]}
               for i, c in enumerate(calls)]
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tcs})
        r["fed"] = []
        for i, tc in enumerate(tcs):
            res = tool_result(r["got_calls"][i], step, j_of.get(i), by_name)
            r["fed"].append(res)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(res)})
    passed = len(steps) == len(task["steps"]) and all(st["passed"] for st in steps)
    return {"seed": seed, "passed": passed, "steps": steps, "latency_ms": round(latency, 1)}


def rescore(model_out, s):
    schemas = {t["name"]: t for t in s["tools"]}
    side = suite_mod.side_effect_tools(s)
    tasks = {t["id"]: t for t in s["tasks"]}
    ext = 0
    for t in model_out["tasks"]:
        spec = tasks[t["id"]]
        for run in t["runs"]:
            new = []
            for k, st in enumerate(run["steps"]):
                err = next((f for f in st["failures"] if f in ("parser_rejected", "server_error")), None)
                r = checks.score_step(spec["steps"][k]["expect"], st["got_calls"], schemas, side, error=err,
                                      later=later_tools(spec, k))
                r.update({x: st[x] for x in ("text", "latency_ms") if x in st})
                new.append(r)
            if new[-1]["passed"] and len(new) < len(spec["steps"]):
                ext += 1
            run["steps"] = new
            run["passed"] = len(new) == len(spec["steps"]) and all(x["passed"] for x in new)
    model_out["metrics"] = metrics(model_out["tasks"])
    model_out["rescore_extended"] = ext
    return model_out


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else None


def _code_hash():
    d = os.path.dirname(__file__)
    return hashlib.sha256(b"".join(open(os.path.join(d, f), "rb").read()
                                   for f in ("checks.py", "runner.py", "backend.py", "suite.py"))).hexdigest()[:12]


def run_model(model, s, port=backend.DEFAULT_PORT, log=None, progress=print, cache_dir=None):
    sha = sha256_file(model)
    key = f"{sha[:16]}_{s['sha256'][:12]}_r{s['repeats']}_t{s['temperature']}_{_code_hash()}.json"
    if cache_dir and os.path.exists(os.path.join(cache_dir, key)):
        progress(f"  [{os.path.basename(model)}] cached")
        out = json.load(open(os.path.join(cache_dir, key)))
        out["model"], out["path"] = os.path.basename(model), os.path.abspath(model)
        return out
    out = _run(model, sha, s, port, log, progress)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        json.dump(out, open(os.path.join(cache_dir, key), "w"))
    return out


def _run(model, sha, s, port, log, progress):
    tools = suite_mod.openai_tools(s)
    schemas = {t["name"]: t for t in s["tools"]}
    side_effects = suite_mod.side_effect_tools(s)
    out = {"model": os.path.basename(model), "path": os.path.abspath(model),
           "size_mb": round(os.path.getsize(model) / 2**20, 1), "sha256": sha, "tasks": []}
    with backend.LlamaServer(model, port=port, log=log) as srv:
        for i, task in enumerate(s["tasks"], 1):
            runs = [run_task(srv, s, task, seed, tools, schemas, side_effects) for seed in range(s["repeats"])]
            out["tasks"].append({"id": task["id"], "category": task["category"], "prompt": task["prompt"], "runs": runs})
            progress(f"  [{out['model']}] {i}/{len(s['tasks'])} {task['id']}: "
                     f"{sum(r['passed'] for r in runs)}/{len(runs)}")
        out["vram_mb"] = srv.vram_mb()
    out["metrics"] = metrics(out["tasks"])
    return out


def metrics(tasks):
    runs = [r for t in tasks for r in t["runs"]]
    steps = [st for r in runs for st in r["steps"]]
    lat = [st["latency_ms"] for st in steps]
    cats = {}
    for t in tasks:
        cats.setdefault(t["category"], []).append(sum(r["passed"] for r in t["runs"]) / len(t["runs"]))
    ftypes = {f: sum(f in st["failures"] for st in steps) for f in checks.FAILURE_TYPES}
    return {
        "pass_rate": round(sum(r["passed"] for r in runs) / len(runs), 4),
        "failure_types": ftypes,
        "tasks_all_pass": sum(all(r["passed"] for r in t["runs"]) for t in tasks),
        "tasks_flaky": sum(0 < sum(r["passed"] for r in t["runs"]) < len(t["runs"]) for t in tasks),
        "n_tasks": len(tasks),
        "unrequested_actions": sum(st["unrequested_action"] for st in steps),
        "tasks_unrequested": sum(any(st["unrequested_action"] for r in t["runs"] for st in r["steps"]) for t in tasks),
        "extra_calls": sum(st["extra_calls"] for st in steps),
        "premature_actions": sum(st.get("premature_action", False) for st in steps),
        "tasks_premature": sum(any(st.get("premature_action") for r in t["runs"] for st in r["steps"]) for t in tasks),
        "invalid_json": ftypes["invalid_json_args"],
        "parser_rejected": ftypes["parser_rejected"],
        "server_errors": ftypes["server_error"],
        "schema_errors": ftypes["schema_error"],
        "wrong_tool": ftypes["wrong_tool"],
        "latency_p50_ms": round(statistics.median(lat), 1) if lat else None,
        "latency_p95_ms": pct(lat, 0.95),
        "by_category": {c: round(sum(v) / len(v), 3) for c, v in cats.items()},
    }
