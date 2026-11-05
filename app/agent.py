"""Run: Glimmer finds the broken order, Spark fixes it through tools, the gate decides what needs the seller."""
import hashlib
import json

from .policy import gate

READ_TOOLS = {"get_order", "stock_of"}
# tool name -> policy action type
ACTION_TYPE = {"update_address": "update_order", "hold_order": "hold", "release_order": "release",
               "cancel_order": "cancel", "move_stock": "move_stock", "notify_customer": "message_customer",
               "request_refund": "refund", "request_reship": "reship", "publish_product": "publish_product"}


def _fn(name, desc, props, required):
    return {"type": "function", "name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required, "additionalProperties": False}}


S, N = {"type": "string"}, {"type": "number"}
KO = {"type": "string", "description": "A few plain English words the seller reads, e.g. cancelled before shipping"}
TOOLS = [
    _fn("get_order", "Read an order: status, customer, address, items, totals.", {"order_id": S}, ["order_id"]),
    _fn("stock_of", "Stock of a SKU at each location.", {"sku": S}, ["sku"]),
    _fn("update_address", "Fix the shipping address. Only fields the customer confirmed.",
        {"order_id": S, "line1": S, "line2": S, "city": S, "zip": S}, ["order_id"]),
    _fn("hold_order", "Stop the order from shipping until it is fixed.", {"order_id": S, "reason": S}, ["order_id", "reason"]),
    _fn("release_order", "Let a held order ship again.", {"order_id": S}, ["order_id"]),
    _fn("cancel_order", "Cancel an order that has not shipped. Does not refund.", {"order_id": S, "reason": S}, ["order_id", "reason"]),
    _fn("move_stock", "Move units between locations so the order can ship.",
        {"sku": S, "qty": N, "from_location": S, "to_location": S}, ["sku", "qty", "from_location", "to_location"]),
    _fn("notify_customer", "Message the customer in their language. Plain, specific, no promises about money.",
        {"order_id": S, "message": S, "language": S}, ["order_id", "message", "language"]),
    _fn("request_refund", "Ask the seller to approve a refund. Never assume it is approved.",
        {"order_id": S, "amount": N, "reason": KO}, ["order_id", "amount", "reason"]),
    _fn("request_reship", "Ask the seller to approve sending the items again.", {"order_id": S, "reason": KO}, ["order_id", "reason"]),
]

REQUIRED = {t["name"]: t["parameters"]["required"] for t in TOOLS}
REQUIRED["publish_product"] = ["product_id", "title", "price"]

PLAYBOOK = """You run operations for a small online store while the seller sleeps.
Fix the broken order with the tools, then answer with ONE short plain English sentence for the seller
saying what you did (for example: "Held the parcel and asked the customer in Korean for the unit number.").
Rules: read the order first. Hold an order before asking a customer to correct it. Tell the customer before
they have to ask. Cancel only unshipped orders. Anything that moves money (refunds, reships) goes through
request_refund or request_reship and waits for the seller. Never write health or efficacy claims.
If a tool returns waiting_for_seller, stop and summarize."""

TRIAGE_PROMPT = """You watch an online store's event stream. Classify ONE event as JSON:
{"verdict": "normal"|"exception", "type": "none"|"address"|"stock"|"delay"|"cancel"|"other", "reason": "<one line>"}
exception = an order that cannot ship or will disappoint the customer without a person acting:
address missing apartment unit / building number, item out of stock at the shipping location,
tracking with no movement for 3+ days, a customer asking to cancel or change an order,
or a customer reply that answers an open problem (type "other"). Everything else is normal."""


class Executor:
    """Gate → idempotency key → write → read back. Every step lands in the ledger."""

    def __init__(self, ledger, store, messenger):
        self.ledger, self.store, self.msg = ledger, store, messenger

    @staticmethod
    def key(tool, args, exception_id=None):
        # the same write for the same problem runs once; the same move for two different orders is two writes
        digest = hashlib.sha256(json.dumps(args, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]
        return f"{tool}:X{exception_id}:{args.get('order_id') or args.get('sku')}:{digest}"

    def call(self, exception_id, tool, args) -> dict:
        if tool in READ_TOOLS:
            return {"order": self.store.get_order(args["order_id"])} if tool == "get_order" else {"stock": self.store.stock_of(args["sku"])}
        if tool not in ACTION_TYPE:
            return {"error": f"unknown tool {tool}"}
        missing = [k for k in REQUIRED.get(tool, ()) if args.get(k) in (None, "")]
        if missing:  # model output is untrusted: check it before anything is claimed or written
            return {"error": f"bad arguments: missing {', '.join(missing)}"}
        decision, rule = gate(ACTION_TYPE[tool], args)
        key = self.key(tool, args, exception_id)
        old = self.ledger.claim(key, exception_id, tool, args, decision)
        if old:
            self.ledger.log("executor", "skip_duplicate", f"{key} already {old['state']}; not run again", f"X{exception_id}")
            return {"status": "duplicate", "state": old["state"]}
        self.ledger.log("policy", "gate", f"{tool} {args.get('order_id', '')} → {decision} ({rule})", f"X{exception_id}")
        if decision == "blocked":
            self.ledger.set_action(key, "blocked")
            return {"status": "blocked", "rule": rule}
        if decision == "approval":
            self.ledger.set_action(key, "pending")
            a = self.ledger.action(key)
            self.msg.send(self._ask_text(tool, args), a["id"], buttons=[(f"ok:{a['id']}", "Approve"), (f"no:{a['id']}", "Not now")])
            return {"status": "waiting_for_seller", "action_id": a["id"]}
        return self._run(key, exception_id, tool, args)

    def _ask_text(self, tool, a):
        if tool == "publish_product":
            return f"Publish the new product “{a['title']}” at ₩{int(a['price']):,}?"
        name = (self.store.get_order(a["order_id"]) or {}).get("name", a["order_id"])
        what = f"Refund ₩{int(a['amount']):,}" if tool == "request_refund" else "Reship"
        return f"{name}: {what}? Reason: {a.get('reason', '')}"

    def approve(self, action_id, ok: bool, by: str) -> dict:
        a = self.ledger.action(id=action_id)
        if not a or a["state"] != "pending":
            self.ledger.log("executor", "skip_duplicate", f"action {action_id} already {a and a['state']}")
            return {"status": "already_decided"}
        self.ledger.log("seller", "decision", f"{'approve' if ok else 'reject'} {a['type']} via {by}", f"X{a['exception_id'] or ''}")
        if not ok:
            self.ledger.set_action(a["key"], "rejected", decided_by=by)
            return {"status": "rejected"}
        self.ledger.set_action(a["key"], "approved", decided_by=by)
        return self._run(a["key"], a["exception_id"], a["type"], json.loads(a["args"]))

    def _run(self, key, exception_id, tool, args) -> dict:
        oid = args.get("order_id")
        before = self.store.get_order(oid) if oid else None
        stock_before = self.store.stock_of(args["sku"]) if tool == "move_stock" else None
        try:
            out = self._write(tool, args)
            ok = self._verify(tool, args, before, stock_before, out)
        except Exception as e:  # a failed write is recorded, never retried blindly
            self.ledger.set_action(key, "failed", {"error": str(e)})
            self.ledger.log("executor", "failed", f"{tool} {oid or ''}: {e}", f"X{exception_id}")
            return {"status": "failed", "error": str(e)}
        state = "done" if ok else "unknown"
        self.ledger.set_action(key, state, {"out": out})
        self.ledger.log("executor", "execute" if ok else "unknown",
                        f"{tool} {oid or args.get('sku', '')} · {'verified' if ok else 'not confirmed by read-back; not retried'}", f"X{exception_id}")
        return {"status": state, "result": out}

    def _write(self, tool, a):
        s = self.store
        if tool == "update_address":
            s.update_address(a["order_id"], {k: a[k] for k in ("line1", "line2", "city", "zip") if a.get(k)})
        elif tool == "hold_order":
            s.hold(a["order_id"], a["reason"])
        elif tool == "release_order":
            s.release(a["order_id"])
        elif tool == "cancel_order":
            s.cancel(a["order_id"], a["reason"])
        elif tool == "move_stock":
            s.move_stock(a["sku"], int(a["qty"]), a["from_location"], a["to_location"])
        elif tool == "notify_customer":
            s.add_note(a["order_id"], f"[Lookout → customer, {a['language']}] {a['message']}")
        elif tool == "request_refund":
            s.refund(a["order_id"], a["amount"])
        elif tool == "request_reship":
            return {"new_order": s.reship(a["order_id"])}
        elif tool == "publish_product":
            s.publish_product(a["product_id"])
        return None

    def _verify(self, tool, a, before, stock_before, out) -> bool:
        s = self.store
        after = s.get_order(a["order_id"]) if a.get("order_id") else None
        match tool:
            case "update_address":
                return all(after["address"].get(k) == a[k] for k in ("line1", "line2", "city", "zip") if a.get(k))
            case "hold_order":
                return after["status"] == "held"
            case "release_order":
                return after["status"] == "open"
            case "cancel_order":
                return after["status"] == "cancelled"
            case "move_stock":
                return s.stock_of(a["sku"])[a["to_location"]] == stock_before[a["to_location"]] + int(a["qty"])
            case "notify_customer":
                return any(a["message"] in n for n in after["notes"])
            case "request_refund":
                return round(after["refunded"] - before["refunded"], 2) == round(float(a["amount"]), 2)
            case "request_reship":
                return s.get_order(out["new_order"]) is not None
            case "publish_product":
                return (s.get_product(a["product_id"]) or {}).get("status") == "active"
        return False


class Agent:
    def __init__(self, ledger, models, store, messenger):
        self.ledger, self.models, self.store, self.msg = ledger, models, store, messenger
        self.exec = Executor(ledger, store, messenger)

    def handle(self, event: dict) -> dict:
        """One event from the store or a customer → triage → (maybe) resolve."""
        oid = str(event.get("order_id", ""))
        t = self.models.glimmer_json("triage", TRIAGE_PROMPT, json.dumps(event, ensure_ascii=False), ref=oid)
        self.ledger.log("glimmer", "verdict", f"{event.get('kind')} {oid} → {t.get('verdict')}:{t.get('type')} · {t.get('reason')}", oid)
        if t.get("verdict") != "exception":
            return {"verdict": "normal"}
        open_ = self.ledger.q("select * from exceptions where order_id=? and status in ('fixing','waiting') order by id desc limit 1", oid)
        exc_id = open_[0]["id"] if open_ else self.ledger.open_exception(t["type"], oid, t.get("reason", ""), event)
        self.resolve(exc_id, event)
        return {"verdict": "exception", "exception_id": exc_id}

    def resolve(self, exc_id, event, max_steps=10):
        ref = f"X{exc_id}"
        prompt = f"Event: {json.dumps(event, ensure_ascii=False)}\nOpen problem id: {ref}."
        r = self.models.spark("plan", [{"role": "user", "content": prompt}], tools=TOOLS, instructions=PLAYBOOK, ref=ref)
        for _ in range(max_steps):
            calls = [o for o in r.output if o.type == "function_call"]
            if not calls:
                break
            outs = []
            for c in calls:
                try:
                    res = self.exec.call(exc_id, c.name, json.loads(c.arguments or "{}"))
                except (KeyError, ValueError, TypeError) as e:  # model sent bad arguments; tell it, don't crash
                    res = {"error": f"bad arguments: {e}"}
                outs.append({"type": "function_call_output", "call_id": c.call_id, "output": json.dumps(res, ensure_ascii=False, default=str)})
            r = self.models.spark("act", outs, tools=TOOLS, instructions=PLAYBOOK, previous_response_id=r.id, ref=ref)
        self.ledger.update_exception(exc_id, status=self.status_of(exc_id), story=(r.output_text or "").strip())

    def status_of(self, exc_id):
        states = {a["state"] for a in self.ledger.q("select state from actions where exception_id=?", exc_id)}
        if "pending" in states:
            return "waiting"
        if states & {"failed", "unknown", "blocked"}:
            return "escalated"
        return "fixed"

    def decide(self, action_id, ok, by):
        """Seller's answer (button or voice) → run or drop the action, then refresh its problem."""
        res = self.exec.approve(action_id, ok, by)
        a = self.ledger.action(id=action_id)
        if a and a["exception_id"] and res.get("status") in ("done", "rejected", "unknown", "failed"):
            exc = self.ledger.q("select story from exceptions where id=?", a["exception_id"])[0]
            what = {"request_refund": "refund", "request_reship": "reship"}.get(a["type"], "change")
            said = f"You approved the {what}." if ok else f"You chose not now for the {what}."
            self.ledger.update_exception(a["exception_id"], status=self.status_of(a["exception_id"]), story=f"{exc['story']} {said}".strip())
        return res
