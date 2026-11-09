import ast
import json
import operator
import jsonschema

MAX_POW_EXP = 64
MAX_POW_BASE = 1e6
MAX_MATCH_CALLS = 10
VALUE_TOL = 1e-6

FAILURE_TYPES = (
    "server_error", "parser_rejected", "invalid_json_args", "schema_error", "no_call_when_required",
    "call_when_not_required", "wrong_tool", "bad_args", "missing_call", "extra_call", "premature_action",
    "duplicate_call", "wrong_order",
)

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Mod: operator.mod}


def safe_eval(expr):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > MAX_POW_EXP or abs(a) > MAX_POW_BASE):  # untrusted input: no 9**9**9
                raise ValueError("exponent too large")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("not arithmetic")
    try:
        return ev(ast.parse(str(expr).replace("^", "**"), mode="eval"))
    except (SyntaxError, ZeroDivisionError, TypeError, OverflowError) as e:
        raise ValueError(str(e))


def _norm(v):
    if isinstance(v, str):
        return v.strip().lower().removeprefix("./")
    return v


def args_match(exp, args):
    for k, v in (exp.get("args") or {}).items():
        if _norm(args.get(k)) != _norm(v):
            return False
    for k, sub in (exp.get("contains") or {}).items():
        if str(sub).lower() not in str(args.get(k, "")).lower():
            return False
    val = exp.get("value")
    if val:
        try:
            return abs(safe_eval(args.get(val["arg"], "")) - val["equals"]) <= val.get("tol", VALUE_TOL)
        except ValueError:
            return False
    return True


def _schema_ok(call, schemas):
    try:
        jsonschema.validate(call["args"], schemas[call["tool"]]["parameters"])
        return True
    except (jsonschema.ValidationError, KeyError):
        return False


def _best_match(want, got_calls):
    # shortcut: only the first MAX_MATCH_CALLS calls are matched, switch to Hungarian if replies get longer
    n = min(len(got_calls), MAX_MATCH_CALLS)
    full = [[got_calls[i]["tool"] == e["tool"] and got_calls[i]["args"] is not None and args_match(e, got_calls[i]["args"])
             for i in range(n)] for e in want]
    best = [None]

    def rec(k, used, assign):
        if k == len(want):
            idx = [i for i in assign if i is not None]
            key = (sum(i is not None and full[j][i] for j, i in enumerate(assign)), len(idx), idx == sorted(idx))
            if best[0] is None or key > best[0][0]:
                best[0] = (key, list(assign))
            return
        rec(k + 1, used, assign + [None])
        for i in range(n):
            if i not in used and got_calls[i]["tool"] == want[k]["tool"]:
                rec(k + 1, used | {i}, assign + [i])

    rec(0, frozenset(), [])
    return best[0][1], full


def score_step(expect, got_calls, schemas, side_effects, error=None, later=None):
    want = expect["calls"]
    r = {"want_calls": [c["tool"] for c in want], "got_calls": got_calls, "failures": [],
         "unrequested_action": False, "premature_action": False, "extra_calls": 0, "missing_calls": 0}
    if error:
        r["failures"].append(error)
        r["passed"] = False
        return r

    fails = r["failures"]
    for c in got_calls:
        if c["args"] is None:
            fails.append("invalid_json_args")
        elif not _schema_ok(c, schemas):
            fails.append("schema_error")

    assign, full = _best_match(want, got_calls)
    for j, i in enumerate(assign):
        if i is None:
            r["missing_calls"] += 1
        elif not full[j][i]:
            fails.append("bad_args")
    r["assign"] = assign
    matched = [i for i in assign if i is not None]

    extra = [c for i, c in enumerate(got_calls) if i not in matched]
    r["extra_calls"] = len(extra)
    r["unrequested_action"] = any(c["tool"] in side_effects for c in extra)
    early = [c for c in extra if later is not None and (c["tool"] in later or c["tool"] in side_effects)]
    r["premature_action"] = bool(early)
    seen = [(c["tool"], json.dumps(c["args"], sort_keys=True)) for c in got_calls]
    if len(seen) != len(set(seen)):
        fails.append("duplicate_call")

    if want and not got_calls:
        fails.append("no_call_when_required")
    elif not want and got_calls:
        fails.append("call_when_not_required")
    elif r["missing_calls"] and extra and not any(c["tool"] in {e["tool"] for e in want} for c in got_calls):
        fails.append("wrong_tool")
    else:
        if r["missing_calls"]:
            fails.append("missing_call")
        if early:
            fails.append("premature_action")
        if len(extra) > len(early):
            fails.append("extra_call")
    if expect.get("order") == "strict" and matched != sorted(matched):
        fails.append("wrong_order")

    r["failures"] = list(dict.fromkeys(fails))
    r["passed"] = not r["failures"]
    return r
