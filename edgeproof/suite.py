import hashlib
import yaml


def load(path):
    raw = open(path, "rb").read()
    s = yaml.safe_load(raw)
    tools = s["tools"]
    names = {t["name"] for t in tools}
    for t in s["tasks"]:
        t.setdefault("steps", [{"expect": t.pop("expect", {})}])
        t.setdefault("category", "general")
        for st in t["steps"]:
            st["expect"] = normalize_expect(st["expect"])
            for c in st["expect"]["calls"]:
                if c["tool"] not in names:
                    raise ValueError(f"task {t['id']}: unknown tool {c['tool']!r}")
    ids = [t["id"] for t in s["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ids")
    s["sha256"] = hashlib.sha256(raw).hexdigest()
    s.setdefault("system", None)
    s.setdefault("temperature", 0)
    s.setdefault("repeats", 3)
    return s


def normalize_expect(e):
    if "calls" in e:
        return {"calls": list(e["calls"]), "order": e.get("order", "any")}
    if e.get("tool") is None:
        return {"calls": [], "order": "any"}
    return {"calls": [{k: v for k, v in e.items() if k in ("tool", "args", "contains", "value")}], "order": "any"}


def openai_tools(suite):
    return [{"type": "function", "function": {k: t[k] for k in ("name", "description", "parameters")}}
            for t in suite["tools"]]


def side_effect_tools(suite):
    return {t["name"] for t in suite["tools"] if t.get("side_effect")}
