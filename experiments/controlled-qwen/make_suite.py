"""Generate agent-200 (test suite) and calibration.txt (imatrix data) with a fixed seed.
Every expected answer is computed from the task's own parameters, so the answer key is correct by construction.
Test and calibration use disjoint entity pools; this script asserts it.
usage: python3 make_suite.py   (writes suite.yaml + calibration.txt next to this file)"""
import json
import os
import random
import re

import yaml

SEED = 20261108
HERE = os.path.dirname(os.path.abspath(__file__))

TEST_CITIES = ["Chennai", "Tokyo", "Dubai", "London", "Berlin", "Nairobi", "Lima", "Oslo", "Hanoi", "Toronto",
               "Madrid", "Cairo", "Seoul", "Lagos", "Denver", "Perth", "Kochi", "Prague", "Dhaka", "Quito"]
CAL_CITIES = ["Paris", "Mumbai", "Sydney", "Boston", "Rome", "Lisbon", "Vienna", "Manila", "Doha", "Accra"]
TEST_TOPICS = ["CUDA streams", "rate limit", "memory leak", "INT8 calibration", "TensorRT plugin", "driver crash",
               "batch size", "context length", "KV cache", "model export", "flash attention", "thermal throttling",
               "docker setup", "API keys", "log rotation", "backup policy", "GPU drivers", "tokenizer", "mixed precision",
               "unit tests"]
CAL_TOPICS = ["password reset", "billing cycle", "SSO login", "webhook retries", "dark mode", "email digest",
              "invoice export", "timezone settings"]
TEST_FILES = ["config.yaml", "logs/error.log", "notes/todo.md", "data/numbers.txt", "src/main.py", "README.md",
              "settings/app.json", "reports/q3.csv", "deploy/env.sh", "docs/install.md"]
CAL_FILES = ["etc/hosts.conf", "tmp/cache.db", "assets/logo.svg", "build/output.bin", "lib/utils.rb"]
TEST_ISSUES = [("Payments API down", "high"), ("Typo on About page", "low"), ("GPU OOM on startup", "high"),
               ("Login 500 error", "medium"), ("Slow dashboard load", "medium"), ("Broken invoice PDF", "high"),
               ("Missing dark logo", "low"), ("Search returns duplicates", "medium"), ("Printer jammed floor 3", "low"),
               ("VPN drops hourly", "high"), ("Wrong currency symbol", "low"), ("Cache never expires", "medium")]
CAL_ISSUES = [("Elevator noise", "low"), ("Badge reader offline", "medium"), ("Coffee machine leak", "low")]

TOOLS = [
    {"name": "calculator", "description": "Evaluate an arithmetic expression",
     "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}},
    {"name": "get_weather", "description": "Current weather for a city",
     "parameters": {"type": "object", "properties": {"city": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}}, "required": ["city"]}},
    {"name": "search_docs", "description": "Search the internal documentation",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                    "required": ["query"]}},
    {"name": "read_file", "description": "Read a text file from the project",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "create_ticket", "description": "Open a support ticket", "side_effect": True,
     "parameters": {"type": "object", "properties": {"title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]}}, "required": ["title", "priority"]}},
]


def gen(rng):
    tasks = []

    def add(cat, prompt, expect=None, steps=None):
        t = {"id": f"{cat}-{sum(x['category'] == cat for x in tasks) + 1:03d}", "category": cat, "prompt": prompt}
        if steps:
            t["steps"] = steps
        else:
            t["expect"] = expect
        tasks.append(t)

    calc = lambda e, v: {"tool": "calculator", "value": {"arg": "expression", "equals": v}}

    # ---- single (40): pick the right tool
    for _ in range(10):
        a, b = rng.randint(12, 99), rng.randint(3, 49)
        add("single", rng.choice(["What is {a} * {b}?", "Multiply {a} by {b}.", "How much is {a} times {b}?"]).format(a=a, b=b),
            calc(f"{a}*{b}", a * b))
    for c in rng.sample(TEST_CITIES, 10):
        add("single", rng.choice(["How hot is it in {c} today?", "Do I need an umbrella in {c} right now?",
                                  "What's the weather like in {c}?", "Is it windy in {c}?"]).format(c=c),
            {"tool": "get_weather", "args": {"city": c}})
    for tp in rng.sample(TEST_TOPICS, 10):
        add("single", rng.choice(["Look up the documentation on {t}.", "What do our docs say about {t}?",
                                  "Find docs about {t}."]).format(t=tp),
            {"tool": "search_docs", "contains": {"query": tp.lower()}})
    for f in TEST_FILES:
        add("single", rng.choice(["Show me the contents of {f}", "Open the file {f}", "What's inside {f}?"]).format(f=f),
            {"tool": "read_file", "contains": {"path": f}})

    # ---- args (50): exact argument values matter
    for c in rng.sample(TEST_CITIES, 12):
        u = rng.choice(["celsius", "fahrenheit"])
        add("args", rng.choice(["Weather in {c} in {u} please.", "Give me the temperature in {c} in {u}."]).format(c=c, u=u),
            {"tool": "get_weather", "args": {"city": c, "unit": u}})
    for tp in rng.sample(TEST_TOPICS, 12):
        n = rng.choice([1, 2, 3, 5, 7, 10, 20])
        add("args", rng.choice(["Search the docs for '{t}', top {n} results only.", "Find {n} doc pages mentioning '{t}'."])
            .format(t=tp, n=n), {"tool": "search_docs", "args": {"limit": n}, "contains": {"query": tp.lower()}})
    for title, pr in TEST_ISSUES:
        add("args", rng.choice(["Open a {p} priority ticket titled '{t}'.", "File a ticket called '{t}', priority {p}."])
            .format(t=title, p=pr), {"tool": "create_ticket", "args": {"title": title, "priority": pr}})
    for _ in range(14):
        a, b, c = rng.randint(2, 30), rng.randint(2, 30), rng.randint(2, 12)
        kind = rng.choice(["prec", "paren", "pct"])
        if kind == "prec":
            add("args", f"Calculate {a} + {b} * {c}", calc("", a + b * c))
        elif kind == "paren":
            add("args", f"Calculate ({a} + {b}) * {c}", calc("", (a + b) * c))
        else:
            p, base = rng.choice([5, 7.5, 12, 15, 20]), rng.choice([400, 1200, 2400, 860, 5000])
            add("args", f"What is {p}% of {base}?", calc("", p * base / 100))

    # ---- no_tool (25): answer in text; any tool call fails, a ticket is an unrequested side effect
    for p in ["Good morning!", "Thanks, that's all for now.", "Hi there, how are you?", "Bye, have a nice day!",
              "Write a two-line poem about the monsoon.", "Write a haiku about GPUs.", "Tell me a short joke about cats.",
              "Write a limerick about coffee.", "Explain in one sentence what a GPU is.", "What does CPU stand for?",
              "Give me a synonym for 'happy'.", "Translate 'thank you' into French.", "What colour is the sky on a clear day?",
              "Summarise the plot of Cinderella in one sentence.", "Suggest a name for a pet goldfish.",
              "What is the opposite of 'cold'?", "Define the word 'latency' in one line.", "Write a motivational quote.",
              "What's a good title for a blog about gardening?", "Name three primary colours.",
              "Write a one-line birthday wish for my friend.", "Is a tomato a fruit or a vegetable?",
              "What is the capital of France?", "Spell 'necessary' backwards.", "Describe the smell of rain in five words."]:
        add("no_tool", p, {"tool": None})

    # ---- negation (15): user explicitly says not to use a tool
    for title, _ in TEST_ISSUES[:5]:
        add("negation", f"Don't open a ticket about '{title}'. Just tell me how I would report it.", {"tool": None})
    for _ in range(5):
        a, b = rng.randint(2, 20), rng.randint(2, 20)
        add("negation", f"Without using any tools, what is {a} + {b}?", {"tool": None})
    for tp in rng.sample(TEST_TOPICS, 5):
        add("negation", f"No need to search the docs, just explain {tp} in one sentence.", {"tool": None})

    # ---- parallel (20): two independent calls, any order
    for _ in range(8):
        c1, c2 = rng.sample(TEST_CITIES, 2)
        add("parallel", f"What's the weather in {c1} and in {c2}?",
            {"calls": [{"tool": "get_weather", "args": {"city": c1}}, {"tool": "get_weather", "args": {"city": c2}}]})
    for _ in range(6):
        f1, f2 = rng.sample(TEST_FILES, 2)
        add("parallel", f"Read both {f1} and {f2}.",
            {"calls": [{"tool": "read_file", "contains": {"path": f1}}, {"tool": "read_file", "contains": {"path": f2}}]})
    for _ in range(6):
        c, tp = rng.choice(TEST_CITIES), rng.choice(TEST_TOPICS)
        add("parallel", f"Check the weather in {c} and also search the docs for '{tp}'.",
            {"calls": [{"tool": "get_weather", "args": {"city": c}}, {"tool": "search_docs", "contains": {"query": tp.lower()}}]})

    # ---- chain (30): use the tool result for the next call
    for _ in range(10):
        c, t = rng.choice(TEST_CITIES), rng.randint(-5, 40)
        add("chain", f"Get the temperature in {c} in celsius, then use the calculator to convert it to fahrenheit.", steps=[
            {"expect": {"tool": "get_weather", "args": {"city": c}}, "mock_result": {"city": c, "temperature": t, "unit": "celsius"}},
            {"expect": calc("", t * 9 / 5 + 32)}])
    for _ in range(10):
        f = rng.choice(TEST_FILES)
        nums = [rng.randint(1, 99) for _ in range(rng.randint(3, 5))]
        add("chain", f"Read {f} and add up the numbers in it.", steps=[
            {"expect": {"tool": "read_file", "contains": {"path": f}}, "mock_result": {"content": "\n".join(map(str, nums))}},
            {"expect": calc("", sum(nums))}])
    for _ in range(10):
        tp, f = rng.choice(TEST_TOPICS), rng.choice(TEST_FILES)
        add("chain", f"Search the docs for '{tp}', then read the file the result points to.", steps=[
            {"expect": {"tool": "search_docs", "contains": {"query": tp.lower()}},
             "mock_result": {"results": [{"title": tp, "file": f}]}},
            {"expect": {"tool": "read_file", "contains": {"path": f}}}])

    # ---- conditional (20): act only if the condition holds
    for title, pr in rng.sample(TEST_ISSUES, 10):
        tp = rng.choice(TEST_TOPICS)
        add("conditional", f"Search the docs for '{tp}'. If nothing is found, open a {pr} priority ticket titled '{title}'.",
            steps=[{"expect": {"tool": "search_docs", "contains": {"query": tp.lower()}}, "mock_result": {"results": []}},
                   {"expect": {"tool": "create_ticket", "args": {"title": title, "priority": pr}}}])
    for title, pr in rng.sample(TEST_ISSUES, 10):
        tp, f = rng.choice(TEST_TOPICS), rng.choice(TEST_FILES)
        add("conditional", f"Search the docs for '{tp}'. Only open a {pr} priority ticket titled '{title}' if nothing is found.",
            steps=[{"expect": {"tool": "search_docs", "contains": {"query": tp.lower()}},
                    "mock_result": {"results": [{"title": tp, "file": f}]}},
                   {"expect": {"tool": None}}])
    return tasks


def calibration(rng):
    """General prose + tool-use transcripts using only CAL_* entities (never the test pool)."""
    lines = []
    prose = ("Quantization reduces the number of bits used to store model weights. Larger models are often more robust "
             "to quantization than smaller ones. A good assistant answers directly when no tool is needed, and only calls "
             "a tool when the request requires external information or an action. ")
    for i in range(40):
        c, tp, f = rng.choice(CAL_CITIES), rng.choice(CAL_TOPICS), rng.choice(CAL_FILES)
        title, pr = rng.choice(CAL_ISSUES)
        a, b = rng.randint(2, 99), rng.randint(2, 99)
        lines += [prose,
                  f"User: What's the weather in {c}?\nAssistant: <tool_call>{json.dumps({'name': 'get_weather', 'arguments': {'city': c}})}</tool_call>",
                  f"User: Search the docs for {tp}.\nAssistant: <tool_call>{json.dumps({'name': 'search_docs', 'arguments': {'query': tp}})}</tool_call>",
                  f"User: Open {f}\nAssistant: <tool_call>{json.dumps({'name': 'read_file', 'arguments': {'path': f}})}</tool_call>",
                  f"User: Open a {pr} ticket titled '{title}'.\nAssistant: <tool_call>{json.dumps({'name': 'create_ticket', 'arguments': {'title': title, 'priority': pr}})}</tool_call>",
                  f"User: What is {a} * {b}?\nAssistant: <tool_call>{json.dumps({'name': 'calculator', 'arguments': {'expression': f'{a}*{b}'}})}</tool_call>",
                  "User: Write a short poem about autumn leaves.\nAssistant: Leaves drift down in amber light, / the year exhales and settles for the night.",
                  "User: Don't open a ticket, just tell me how to report a bug.\nAssistant: Describe the steps to reproduce it, what you expected, and what happened instead, then send it to the support team."]
    return "\n\n".join(lines)


def main():
    rng = random.Random(SEED)
    tasks = gen(rng)
    assert len(tasks) == 200, len(tasks)
    counts = {c: sum(t["category"] == c for t in tasks) for c in dict.fromkeys(t["category"] for t in tasks)}
    assert counts == {"single": 40, "args": 50, "no_tool": 25, "negation": 15, "parallel": 20, "chain": 30,
                      "conditional": 20}, counts
    cal = calibration(random.Random(SEED + 1))
    test_text = json.dumps(tasks).lower()
    for ent in CAL_CITIES + CAL_TOPICS + CAL_FILES + [t for t, _ in CAL_ISSUES]:
        assert ent.lower() not in test_text, f"calibration entity leaks into test suite: {ent}"
    for ent in TEST_CITIES + TEST_TOPICS + TEST_FILES + [t for t, _ in TEST_ISSUES]:
        assert not re.search(r"\b" + re.escape(ent.lower()) + r"\b", cal.lower()), f"test entity leaks into calibration: {ent}"
    suite = {"name": "agent-200", "temperature": 0, "repeats": 1,
             "system": "You are a helpful assistant. Use a tool only when the user's request needs it.",
             "tools": TOOLS, "tasks": tasks}
    with open(os.path.join(HERE, "suite.yaml"), "w") as f:
        f.write(f"# GENERATED by make_suite.py (seed {SEED}). Do not hand-edit; change the generator.\n")
        yaml.safe_dump(suite, f, sort_keys=False, allow_unicode=True, width=200)
    open(os.path.join(HERE, "calibration.txt"), "w").write(cal)
    print(counts, f"calibration {len(cal)} chars")


if __name__ == "__main__":
    main()
