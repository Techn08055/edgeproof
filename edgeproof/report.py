import html
import json
import os

COLORS = {"PASS": "#1a7f37", "REVIEW": "#9a6700", "FAIL": "#cf222e"}


def write(out_dir, payload):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(payload, f, indent=2)
    with open(os.path.join(out_dir, "report.html"), "w") as f:
        f.write(render(payload))


def _e(x):
    return html.escape(str(x))


def _call(st):
    if st is None:
        return "—"
    calls = st.get("got_calls") or []
    shown = "<br>".join(f"{_e(c['tool'])} {_e(json.dumps(c['args']))}" for c in calls) or f"<i>{_e(st['text'][:80])}</i>"
    why = f"<br><small>{_e(', '.join(st['failures']))}</small>" if st.get("failures") else ""
    return shown + why


def _badge(v):
    return f"<b style='color:{COLORS[v]}'>{v}</b>"


def _first_fail(task):
    for r in task["runs"]:
        if not r["passed"]:
            return next((s for s in r["steps"] if not s["passed"]), r["steps"][-1])
    return task["runs"][0]["steps"][-1]


def render(p):
    ref = p["reference"]
    ref_tasks = {t["id"]: t for t in ref["tasks"]}
    rows, details = [], []
    for c in p["candidates"]:
        v, d = c["values"], c["verdict"]
        rows.append(
            f"<tr><td>{_e(c['model'])}</td><td>{c['size_mb']:.0f}</td>"
            f"<td>{_badge(d)}</td>" + "".join(f"<td>{_badge(c['verdicts'][g])}</td>" for g in ("quality", "regression", "safety"))
            + f"<td>{v['pass_rate']:.1%}</td>"
            f"<td>{v['pass_rate_drop']:+.1%}</td><td>{v['regressions']}</td><td>{v['tasks_unrequested']}</td>"
            f"<td>{v['invalid_json']} / {v['parser_rejected']} / {v['server_errors']}</td><td>{v['latency_p95_ms']}</td><td>{v['vram_mb'] if v['vram_mb'] is not None else '?'}</td></tr>")
        why = "".join(f"<li>{_e(n['group'])} {_e(n['level'])}: <code>{_e(n['metric'])}</code> = {_e(n['value'])} ({_e(n['why'])})</li>"
                      for n in c["notes"]) or "<li>all rules passed</li>"
        cand_tasks = {t["id"]: t for t in c["tasks"]}
        reg = "".join(
            f"<tr><td>{_e(i)}</td><td>{_e(cand_tasks[i]['prompt'])}</td><td>{_call(ref_tasks[i]['runs'][0]['steps'][-1])}</td>"
            f"<td>{_call(_first_fail(cand_tasks[i]))}</td></tr>" for i in v["regressed_tasks"])
        unreq = (f"<p><b>Unrequested side-effect calls</b>: new vs reference {_e(v['new_unrequested_tasks'])}, "
                 f"also made by reference {_e(v['shared_unrequested_tasks'])}</p>"
                 if v["new_unrequested_tasks"] or v["shared_unrequested_tasks"] else "")
        ft = ", ".join(f"{k} {n}" for k, n in c["metrics"]["failure_types"].items() if n) or "none"
        details.append(f"<h2>{_e(c['model'])} — {_badge(d)}</h2><ul>{why}</ul>{unreq}<p>Failure types (steps): {_e(ft)}</p>"
                       + (f"<table><tr><th>task</th><th>prompt</th><th>reference</th><th>candidate</th></tr>{reg}</table>"
                          if reg else "<p>No regressions vs reference.</p>"))
    ref_fail = "".join(f"<li><code>{_e(t['id'])}</code>: {_e(t['prompt'])} → {_call(_first_fail(t))}</li>"
                       for t in ref["tasks"] if not all(r["passed"] for r in t["runs"]))
    env = p["env"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>EdgeProof report</title>
<style>body{{font:14px/1.5 system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#1f2328}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}td,th{{border:1px solid #d0d7de;padding:4px 8px;text-align:left;vertical-align:top}}
th{{background:#f6f8fa}}code{{background:#f6f8fa;padding:0 3px}}</style></head><body>
<h1>EdgeProof report</h1>
<p>Rules v{_e(p.get('rules_version', '?'))} · Suite <code>{_e(p['suite']['name'])}</code> ({p['suite']['n_tasks']} tasks × {p['suite']['repeats']} repeats) ·
reference <code>{_e(ref['model'])}</code> pass rate {ref['metrics']['pass_rate']:.1%}</p>
<table><tr><th>candidate</th><th>MB</th><th>overall</th><th>quality</th><th>regression</th><th>safety</th><th>pass rate</th><th>Δ vs ref</th><th>regressions</th>
<th>tasks w/ unrequested side effects</th><th>invalid JSON / parser rejected / server errors</th><th>p95 ms</th><th>VRAM MB</th></tr>{''.join(rows)}</table>
{''.join(details)}
<h2>Reference failures</h2><ul>{ref_fail or '<li>none</li>'}</ul>
<h2>Environment</h2><pre>{_e(json.dumps(env, indent=2))}</pre>
</body></html>"""
