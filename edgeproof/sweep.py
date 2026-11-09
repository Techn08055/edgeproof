import argparse
import csv
import json
import os
import re

COLORS = ["#0969da", "#cf222e", "#1a7f37", "#8250df", "#9a6700"]


def quant_of(name):
    m = re.search(r"(f16|fp16|bf16|q\d_k_[sml]|q\d_k|q\d_\d)", name.lower())
    return m.group(1).upper().replace("FP16", "F16") if m else name


def rows_from(path, family):
    p = json.load(open(path))
    out = []
    for kind, r in [("reference", p["reference"])] + [("candidate", c) for c in p["candidates"]]:
        m = r["metrics"]
        out.append({"family": family, "quant": quant_of(r["model"]), "role": kind,
                    "verdict": r.get("verdict", "REF"), "size_mb": r["size_mb"], "vram_mb": r.get("vram_mb"),
                    "pass_rate": m["pass_rate"], "unrequested_actions": m["unrequested_actions"],
                    "regressions": r.get("values", {}).get("regressions", 0),
                    "p95_ms": m["latency_p95_ms"], **{f"cat_{k}": v for k, v in m["by_category"].items()}})
    return out


def svg(rows, w=720, h=420, pad=60):
    xs = [r["vram_mb"] or r["size_mb"] for r in rows]
    x0, x1 = 0, max(xs) * 1.1
    X = lambda v: pad + (v - x0) / (x1 - x0) * (w - 2 * pad)
    Y = lambda v: h - pad - v * (h - 2 * pad)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="system-ui,sans-serif" font-size="12">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{w/2}" y="24" text-anchor="middle" font-size="15" font-weight="600">Agent tool-call pass rate vs VRAM</text>']
    for t in range(0, 11, 2):
        y = Y(t / 10)
        parts.append(f'<line x1="{pad}" x2="{w-pad}" y1="{y}" y2="{y}" stroke="#eee"/><text x="{pad-8}" y="{y+4}" text-anchor="end">{t*10}%</text>')
    for gb in range(0, int(x1 / 1024) + 1):
        x = X(gb * 1024)
        parts.append(f'<text x="{x}" y="{h-pad+18}" text-anchor="middle">{gb} GB</text>')
    parts.append(f'<text x="{w/2}" y="{h-12}" text-anchor="middle">peak VRAM (llama-server, nvidia-smi)</text>')
    fams = sorted({r["family"] for r in rows})
    for i, f in enumerate(fams):
        c = COLORS[i % len(COLORS)]
        pts = sorted((r["vram_mb"] or r["size_mb"], r["pass_rate"], r["quant"]) for r in rows if r["family"] == f)
        parts.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="{" ".join(f"{X(a)},{Y(b)}" for a, b, _ in pts)}"/>')
        for a, b, q in pts:
            parts.append(f'<circle cx="{X(a)}" cy="{Y(b)}" r="4" fill="{c}"/><text x="{X(a)+6}" y="{Y(b)-6}" fill="{c}">{q}</text>')
        parts.append(f'<rect x="{w-pad-150}" y="{40+i*18}" width="10" height="10" fill="{c}"/><text x="{w-pad-135}" y="{49+i*18}">{f}</text>')
    return "\n".join(parts + ["</svg>"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", help="report.json files; family = dir name before '__'")
    ap.add_argument("--out", default="reports/sweep")
    a = ap.parse_args(argv)
    seen, rows = set(), []
    for p in a.reports:
        for r in rows_from(p, os.path.basename(os.path.dirname(p)).split("__")[0]):
            if (r["family"], r["quant"]) not in seen:
                seen.add((r["family"], r["quant"]))
                rows.append(r)
    os.makedirs(a.out, exist_ok=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k.startswith("cat_"), k))
    with open(os.path.join(a.out, "sweep.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, keys)
        wr.writeheader()
        wr.writerows(rows)
    open(os.path.join(a.out, "chart.svg"), "w").write(svg(rows))
    print(f"{'family':12} {'quant':7} {'verdict':7} {'VRAM MB':>8} {'pass':>6} {'unreq':>5} {'regr':>4}")
    for r in rows:
        print(f"{r['family']:12} {r['quant']:7} {r['verdict']:7} {str(r['vram_mb']):>8} {r['pass_rate']:6.1%} "
              f"{r['unrequested_actions']:5} {r['regressions']:4}")


if __name__ == "__main__":
    main()
