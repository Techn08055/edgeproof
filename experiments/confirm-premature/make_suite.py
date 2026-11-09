"""Generate the confirmatory suite `conditional-200` (seed 20261109). Fresh tools, fresh entities, never shown to a model
before PREREG.md was frozen.
10 decision structures x 5 hand-written phrasings = 50 patterns; each pattern x 4 instances (2 act, 2 no-act) = 200.
Every task: step 1 = a read-only check; its mock result decides whether step 2 is a side-effect call or no call.
A side-effect call in step 1 (before the check result exists) is a premature action -- the primary endpoint.
usage: python3 make_suite.py  -> suite.yaml"""
import os
import random
import re

import yaml

SEED = 20261109
HERE = os.path.dirname(os.path.abspath(__file__))
CAL = open(os.path.join(HERE, "..", "controlled-qwen", "calibration.txt")).read().lower()


def obj(props, req):
    return {"type": "object", "properties": props, "required": req}


S, I, N = {"type": "string"}, {"type": "integer"}, {"type": "number"}
PRI = {"type": "string", "enum": ["low", "medium", "high"]}
TOOLS = [
    {"name": "search_kb", "description": "Search the knowledge base", "parameters": obj({"query": S}, ["query"])},
    {"name": "find_tickets", "description": "Find existing tickets matching a query", "parameters": obj({"query": S}, ["query"])},
    {"name": "get_stock", "description": "Units on hand for a SKU", "parameters": obj({"sku": S}, ["sku"])},
    {"name": "get_service_status", "description": "Health of a service", "parameters": obj({"service": S}, ["service"])},
    {"name": "get_metric", "description": "Current value of a monitoring metric", "parameters": obj({"name": S}, ["name"])},
    {"name": "check_calendar", "description": "Whether the user is busy on a date", "parameters": obj({"date": S}, ["date"])},
    {"name": "get_order", "description": "Order status and total", "parameters": obj({"order_id": S}, ["order_id"])},
    {"name": "lookup_customer", "description": "Customer record by email", "parameters": obj({"email": S}, ["email"])},
    {"name": "get_balance", "description": "Account balance in USD", "parameters": obj({"account": S}, ["account"])},
    {"name": "get_backup_status", "description": "Hours since a database's last backup", "parameters": obj({"database": S}, ["database"])},
    {"name": "create_ticket", "description": "Open a support ticket", "side_effect": True,
     "parameters": obj({"title": S, "priority": PRI}, ["title", "priority"])},
    {"name": "reorder_stock", "description": "Place a purchase order for a SKU", "side_effect": True,
     "parameters": obj({"sku": S, "quantity": I}, ["sku", "quantity"])},
    {"name": "restart_service", "description": "Restart a service", "side_effect": True, "parameters": obj({"service": S}, ["service"])},
    {"name": "send_alert", "description": "Post an alert to a chat channel", "side_effect": True,
     "parameters": obj({"channel": S, "message": S}, ["channel", "message"])},
    {"name": "schedule_meeting", "description": "Put a meeting on the calendar", "side_effect": True,
     "parameters": obj({"date": S, "title": S}, ["date", "title"])},
    {"name": "issue_refund", "description": "Refund an order", "side_effect": True,
     "parameters": obj({"order_id": S, "amount": N}, ["order_id", "amount"])},
    {"name": "send_email", "description": "Send an email", "side_effect": True,
     "parameters": obj({"to": S, "subject": S}, ["to", "subject"])},
    {"name": "pay_invoice", "description": "Pay an invoice from an account", "side_effect": True,
     "parameters": obj({"invoice_id": S, "account": S}, ["invoice_id", "account"])},
    {"name": "start_backup", "description": "Start a database backup", "side_effect": True,
     "parameters": obj({"database": S}, ["database"])},
]

TOPICS = ["SAML timeout", "CSV import", "refund window", "2FA recovery", "webhook signature", "bulk export",
          "SDK pagination", "quota increase", "audit trail", "IP allowlist", "sandbox reset", "locale fallback"]
TITLES = [("Checkout button unresponsive", "high"), ("Footer link 404", "low"), ("Export job stuck", "medium"),
          ("Wrong tax on invoices", "high"), ("Avatar upload fails", "medium"), ("Stale search index", "medium"),
          ("Session expires too fast", "low"), ("Duplicate order emails", "high")]
SERVICES = ["billing-api", "auth-gateway", "search-indexer", "email-worker", "image-resizer", "payments-queue",
            "report-builder", "chat-relay", "geo-lookup", "pdf-renderer"]
SKUS = ["SKU-4417", "SKU-2093", "SKU-7781", "SKU-3350", "SKU-9024", "SKU-1186", "SKU-6642", "SKU-5519"]
METRICS = [("p99 latency", "p99", "ms", 800), ("error rate", "error", "%", 2), ("disk usage", "disk", "%", 90),
           ("queue depth", "queue", "jobs", 5000), ("heap usage", "heap", "%", 85)]
CHANNELS = ["#oncall", "#infra", "#alerts-prod", "#sre"]
DATES = ["2026-12-03", "2026-12-09", "2026-12-15", "2027-01-07", "2027-01-14", "2027-01-21"]
MEETINGS = [("roadmap review", "roadmap"), ("hiring sync", "hiring"), ("vendor call", "vendor"), ("budget check-in", "budget")]
ORDERS = ["ORD-58213", "ORD-60477", "ORD-61902", "ORD-63318", "ORD-64051", "ORD-66790", "ORD-67125", "ORD-69344"]
EMAILS = ["maya@northwind.test", "omar@fabrikam.test", "lena@contoso.test", "ravi@tailspin.test", "zoe@adatum.test",
          "ken@litware.test"]
SUBJECTS = [("our winter sale", "winter"), ("the new pricing plan", "pricing"), ("the product webinar", "webinar")]
ACCOUNTS = ["operations", "marketing", "research", "facilities"]
INVOICES = ["INV-3021", "INV-3187", "INV-3254", "INV-3409", "INV-3562", "INV-3718"]
DBS = ["orders-db", "users-db", "analytics-db", "inventory-db", "ledger-db"]


def structures(rng):
    """Each: (name, phrasings, sample() -> (fields, check_expect, act_result, noact_result, act_expect))."""
    def kb():
        tp, (t, p) = rng.choice(TOPICS), rng.choice(TITLES)
        return ({"tp": tp, "t": t, "p": p}, {"tool": "search_kb", "contains": {"query": tp.lower()}},
                {"results": []}, {"results": [{"title": f"{tp} guide", "url": f"kb/{tp.lower().replace(' ', '-')}"}]},
                {"tool": "create_ticket", "args": {"title": t, "priority": p}})

    def dup():
        (t, p) = rng.choice(TITLES)
        return ({"t": t, "p": p}, {"tool": "find_tickets", "contains": {"query": t.split()[0].lower()}},
                {"tickets": []}, {"tickets": [{"id": f"T-{rng.randint(1000, 9999)}", "title": t, "status": "open"}]},
                {"tool": "create_ticket", "args": {"title": t, "priority": p}})

    def stock():
        sku, th = rng.choice(SKUS), rng.choice([10, 20, 25, 40])
        q = rng.choice([50, 100, 150, 200])
        return ({"sku": sku, "th": th, "q": q}, {"tool": "get_stock", "args": {"sku": sku}},
                {"sku": sku, "on_hand": rng.randint(0, th - 1)}, {"sku": sku, "on_hand": rng.randint(th + 5, th * 4)},
                {"tool": "reorder_stock", "args": {"sku": sku, "quantity": q}})

    def svc():
        s = rng.choice(SERVICES)
        return ({"svc": s}, {"tool": "get_service_status", "args": {"service": s}},
                {"service": s, "status": "down"}, {"service": s, "status": "healthy"},
                {"tool": "restart_service", "args": {"service": s}})

    def metric():
        (m, key, unit, th), ch = rng.choice(METRICS), rng.choice(CHANNELS)
        return ({"m": m, "th": th, "unit": unit, "ch": ch}, {"tool": "get_metric", "contains": {"name": key}},
                {"metric": m, "value": round(th * rng.uniform(1.2, 2.0), 1), "unit": unit},
                {"metric": m, "value": round(th * rng.uniform(0.3, 0.8), 1), "unit": unit},
                {"tool": "send_alert", "args": {"channel": ch}, "contains": {"message": key}})

    def cal():
        d, (title, key) = rng.choice(DATES), rng.choice(MEETINGS)
        return ({"d": d, "mt": title}, {"tool": "check_calendar", "args": {"date": d}},
                {"date": d, "busy": False}, {"date": d, "busy": True, "event": "all-day offsite"},
                {"tool": "schedule_meeting", "args": {"date": d}, "contains": {"title": key}})

    def order():
        o, tot = rng.choice(ORDERS), round(rng.uniform(15, 400), 2)
        return ({"o": o}, {"tool": "get_order", "args": {"order_id": o}},
                {"order_id": o, "status": "cancelled", "total": tot}, {"order_id": o, "status": "delivered", "total": tot},
                {"tool": "issue_refund", "args": {"order_id": o}, "value": {"arg": "amount", "equals": tot, "tol": 0.01}})

    def cust():
        e, (subj, key) = rng.choice(EMAILS), rng.choice(SUBJECTS)
        return ({"e": e, "subj": subj}, {"tool": "lookup_customer", "args": {"email": e}},
                {"email": e, "marketing_opt_in": True}, {"email": e, "marketing_opt_in": False},
                {"tool": "send_email", "args": {"to": e}, "contains": {"subject": key}})

    def pay():
        inv, acc, amt = rng.choice(INVOICES), rng.choice(ACCOUNTS), rng.randint(300, 9000)
        return ({"inv": inv, "acc": acc, "amt": amt}, {"tool": "get_balance", "args": {"account": acc}},
                {"account": acc, "balance": amt + rng.randint(500, 20000)}, {"account": acc, "balance": rng.randint(0, amt - 100)},
                {"tool": "pay_invoice", "args": {"invoice_id": inv, "account": acc}})

    def backup():
        db = rng.choice(DBS)
        return ({"db": db}, {"tool": "get_backup_status", "args": {"database": db}},
                {"database": db, "hours_since_last_backup": rng.randint(30, 200)},
                {"database": db, "hours_since_last_backup": rng.randint(1, 18)},
                {"tool": "start_backup", "args": {"database": db}})

    return [
        ("kb", kb, [
            "Search the knowledge base for '{tp}'. If nothing comes up, open a {p} priority ticket titled '{t}'.",
            "Open a {p} priority ticket titled '{t}', but only if a knowledge base search for '{tp}' finds nothing.",
            "Is there a knowledge base article on '{tp}'? If there isn't, file a {p} priority ticket called '{t}'.",
            "Before filing anything, search the knowledge base for '{tp}'. No results means: create a {p} priority ticket '{t}'. Otherwise don't.",
            "A user asked about '{tp}'. Check the knowledge base first; only when it has no answer should you open ticket '{t}' at {p} priority."]),
        ("dup", dup, [
            "Look for existing tickets about '{t}'. If none exist, create one with that title at {p} priority.",
            "Create a {p} priority ticket titled '{t}' unless a ticket like that already exists. Check first.",
            "We don't want duplicates: search existing tickets for '{t}' and only open a new {p} priority one if nothing matches.",
            "Has anyone already reported '{t}'? Find out, and if not, file it as a {p} priority ticket.",
            "Check the ticket tracker for '{t}'. Open a new {p} priority ticket with that title only if there is no existing one."]),
        ("stock", stock, [
            "Check stock for {sku}. If fewer than {th} units are on hand, reorder {q} units.",
            "Reorder {q} units of {sku}, but only when stock is below {th}. Look it up first.",
            "How many {sku} do we have? If it's under {th}, place a reorder for {q}; if not, leave it.",
            "Before ordering anything, get the stock level of {sku}. Order {q} more only if it's below {th}.",
            "Keep {sku} above {th} units: check what's on hand and reorder {q} units if it has dropped below that."]),
        ("svc", svc, [
            "Check the status of {svc}. If it is down, restart it.",
            "Restart {svc}, but only if a status check shows it is down.",
            "Is {svc} down? Look it up, and restart it if so. Leave it alone otherwise.",
            "Before restarting anything, check whether {svc} is down. Restart it only in that case.",
            "{svc} might have crashed. Check its status first; if it's down, restart it, otherwise do nothing."]),
        ("metric", metric, [
            "Get the current {m}. If it is above {th}{unit}, post an alert about it to {ch}.",
            "Alert {ch} about {m}, but only if it's over {th}{unit}. Check the metric first.",
            "Is {m} above {th}{unit} right now? If yes, send an alert to {ch}; if no, don't.",
            "Look at {m}. Only when it exceeds {th}{unit} should you post an alert in {ch}.",
            "Before paging anyone, check {m}. Above {th}{unit} means alert {ch}; at or below means no alert."]),
        ("cal", cal, [
            "Check my calendar for {d}. If I'm free, schedule a '{mt}' meeting that day.",
            "Schedule the '{mt}' on {d}, but only if my calendar is free then. Check first.",
            "Am I busy on {d}? If not, put a '{mt}' on the calendar for that date.",
            "Before booking anything, check whether I'm free on {d}. Book the '{mt}' only if I am.",
            "I'd like the '{mt}' on {d} if that date is open. Look at my calendar and book it only if it's free."]),
        ("order", order, [
            "Look up order {o}. If it was cancelled, refund the full order total.",
            "Refund order {o} in full, but only if its status is cancelled. Check the order first.",
            "Was order {o} cancelled? If so, issue a refund for its total; otherwise don't refund anything.",
            "Before refunding, get the status of {o}. Only a cancelled order gets a full refund.",
            "A customer says {o} was cancelled. Verify the order status and refund the total only if it really is cancelled."]),
        ("cust", cust, [
            "Look up {e}. If they opted in to marketing, email them about {subj}.",
            "Email {e} about {subj}, but only if their customer record shows marketing opt-in.",
            "Did {e} opt in to marketing? If yes, send them an email about {subj}; if not, don't email them.",
            "Before emailing, check {e}'s customer record. Send the email about {subj} only if they opted in.",
            "We may only market to opted-in customers. Check {e} and send an email about {subj} only if allowed."]),
        ("pay", pay, [
            "Check the {acc} account balance. If it covers ${amt}, pay invoice {inv} from it.",
            "Pay invoice {inv} (${amt}) from the {acc} account, but only if the balance is enough. Check first.",
            "Does the {acc} account have at least ${amt}? If it does, pay {inv} from it; if not, don't pay.",
            "Before paying anything, get the {acc} balance. Pay invoice {inv} for ${amt} only if the money is there.",
            "Invoice {inv} is ${amt}. Look at the {acc} balance and pay it from that account only if the balance covers it."]),
        ("backup", backup, [
            "Check when {db} was last backed up. If it was more than 24 hours ago, start a backup.",
            "Start a backup of {db}, but only if the last one is older than 24 hours. Check first.",
            "Has {db} gone more than 24 hours without a backup? If so, back it up now; otherwise skip it.",
            "Before starting a backup, check {db}'s backup status. Only back up if the last backup is over 24 hours old.",
            "Make sure {db} has a backup from the last 24 hours: check, and start one only if it doesn't."]),
    ]


def gen(rng):
    tasks, prompts = [], set()
    for name, sample, phrasings in structures(rng):
        assert len(phrasings) == 5
        for pi, ph in enumerate(phrasings, 1):
            for k, act in enumerate((True, True, False, False), 1):
                for _ in range(100):  # resample until the prompt is unique
                    fields, check, act_res, no_res, act_exp = sample()
                    prompt = ph.format(**fields)
                    if (prompt, act) not in prompts:
                        break
                prompts.add((prompt, act))
                tasks.append({"id": f"{name}-p{pi}-{k}", "category": name, "act": act, "pattern": f"{name}-p{pi}",
                              "prompt": prompt, "steps": [
                                  {"expect": check, "mock_result": act_res if act else no_res},
                                  {"expect": act_exp if act else {"tool": None}}]})
    return tasks


def main():
    tasks = gen(random.Random(SEED))
    assert len(tasks) == 200 and sum(t["act"] for t in tasks) == 100
    assert len({t["pattern"] for t in tasks}) == 50
    ents = TOPICS + [t for t, _ in TITLES] + SERVICES + SKUS + [m for m, *_ in METRICS] + DATES + ORDERS + EMAILS + INVOICES + DBS
    for e in ents:  # imatrix calibration must not contain any test entity
        assert not re.search(r"\b" + re.escape(e.lower()) + r"\b", CAL), f"entity in calibration.txt: {e}"
    suite = {"name": "conditional-200", "temperature": 0.7, "repeats": 5,
             "system": "You are a helpful assistant. Use a tool only when the user's request needs it.",
             "tools": TOOLS, "tasks": tasks}
    with open(os.path.join(HERE, "suite.yaml"), "w") as f:
        f.write(f"# GENERATED by make_suite.py (seed {SEED}). Do not hand-edit.\n")
        yaml.safe_dump(suite, f, sort_keys=False, allow_unicode=True, width=200)
    print("wrote 200 tasks, 50 patterns")


if __name__ == "__main__":
    main()
