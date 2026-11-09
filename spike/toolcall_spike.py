"""Phase-0 spike: does quantization change tool calls? (throwaway, allowed before discovery gate)
usage: python3 toolcall_spike.py [port]  -> llama-server must be running with --jinja
"""
import json, sys, urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8080"
TOOLS = [
    {"type": "function", "function": {"name": "calculator", "description": "Evaluate an arithmetic expression",
     "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city",
     "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "search_docs", "description": "Search the internal documentation",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "create_ticket", "description": "Open a support ticket",
     "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "medium", "high"]}}, "required": ["title", "priority"]}}},
]
# (prompt, expected tool or None, expected args subset)
TASKS = [
    ("What is 17 * 23?", "calculator", {"__value__": 391}),
    ("What's the weather in Kochi in fahrenheit?", "get_weather", {"city": "Kochi", "unit": "fahrenheit"}),
    ("Find the docs about INT8 calibration, just 3 results.", "search_docs", {"limit": 3}),
    ("Open a high priority ticket titled 'GPU OOM on startup'.", "create_ticket", {"priority": "high", "title": "GPU OOM on startup"}),
    ("Hi! How are you today?", None, {}),
    ("Is it raining in Berlin right now?", "get_weather", {"city": "Berlin"}),
    ("Compute (1250 - 380) / 6", "calculator", {"__value__": 145}),
    ("The login page is broken, file a low priority ticket called 'Login 500 error'.", "create_ticket", {"priority": "low", "title": "Login 500 error"}),
    ("Write me a haiku about GPUs.", None, {}),
    ("Search our docs for 'TensorRT plugin' and return 5 hits.", "search_docs", {"limit": 5}),
]

def call(prompt):
    body = {"messages": [{"role": "user", "content": prompt}], "tools": TOOLS, "temperature": 0, "seed": 0}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    msg = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]
    tc = (msg.get("tool_calls") or [None])[0]
    if not tc:
        return None, {}
    try:
        return tc["function"]["name"], json.loads(tc["function"]["arguments"])
    except json.JSONDecodeError:
        return tc["function"]["name"], {"__invalid_json__": tc["function"]["arguments"]}

def check(args, k, v):
    if k == "__value__":  # semantic check: the expression must evaluate to the right number
        expr = str(args.get("expression", ""))
        if not set(expr) <= set("0123456789+-*/(). "):
            return False
        try:
            return abs(eval(expr) - v) < 1e-6  # safe: charset restricted above
        except Exception:
            return False
    return str(args.get(k)).lower() == str(v).lower()

assert check({"expression": "(1250-380)/6"}, "__value__", 145) and not check({"expression": "1250 - 380 / 6"}, "__value__", 145)
ok = 0
for prompt, want_tool, want_args in TASKS:
    tool, args = call(prompt)
    good = tool == want_tool and all(check(args, k, v) for k, v in want_args.items())
    ok += good
    print(f"{'PASS' if good else 'FAIL'}  want={want_tool} got={tool} args={args}  | {prompt}")
print(f"\n{ok}/{len(TASKS)} correct")
