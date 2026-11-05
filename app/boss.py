"""Voice Boss: the seller talks to Lookout on WhatsApp. Launch: one description → a multilingual listing."""
import json
import re
import time

from .agent import _fn, S, N
from .policy import HEALTH

BOSS_PROMPT = """You are Lookout, the seller's operations partner, answering on WhatsApp in English
(reply in Korean only if the seller writes Korean). Use tools to answer: brief for "how was last night?", decide pending approvals when the seller says to
(match their words to the numbered pending list or an order number; if unsure which one, ask instead of guessing),
and launch_product when they ask to sell something. Reply in at most three short sentences, plain text, no emoji."""

BOSS_TOOLS = [
    _fn("briefing", "Today's numbers: problems found, fixed, waiting on the seller, model cost.", {}, []),
    _fn("list_pending", "Approvals waiting for the seller, numbered.", {}, []),
    _fn("decide", "Apply the seller's decision to one pending approval.", {"action_id": N, "approve": {"type": "boolean"}}, ["action_id", "approve"]),
    _fn("launch_product", "Draft a new product listing from the seller's description.", {"description": S}, ["description"]),
]

LISTING_SCHEMA = {
    "title": "Listing", "type": "object", "additionalProperties": False,
    "required": ["title", "price_krw", "ko", "en", "ja", "tags"],
    "properties": {
        "title": {"type": "string"}, "price_krw": {"type": "integer"},
        "ko": {"type": "string"}, "en": {"type": "string"}, "ja": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


class Boss:
    def __init__(self, agent):
        self.agent, self.ledger, self.models, self.msg = agent, agent.ledger, agent.models, agent.msg

    def briefing(self):
        start = time.time() - 24 * 3600  # a night crosses midnight; count the last 24 hours
        ex = self.ledger.q("select status from exceptions where opened>=?", start)
        fixed = sum(e["status"] == "fixed" for e in ex)
        return {"found": len(ex), "fixed": fixed, "waiting": sum(e["status"] == "waiting" for e in ex),
                "escalated": sum(e["status"] == "escalated" for e in ex),
                "hours_saved": round(fixed * 20 / 60, 1), "model_cost_usd": round(self.ledger.spent_today(), 4)}

    def list_pending(self):
        """Pending approvals with numbers that never shift: #2 stays #2 after #1 is decided."""
        asked = self.ledger.q("select * from actions where decision='approval' order by id")
        return [{"n": i + 1, "action_id": a["id"], "type": a["type"], "args": json.loads(a["args"])}
                for i, a in enumerate(asked) if a["state"] == "pending"]

    def tool(self, name, args):
        if name == "briefing":
            return self.briefing()
        if name == "list_pending":
            return self.list_pending()
        if name == "decide":
            return self.agent.decide(int(args["action_id"]), bool(args["approve"]), "voice")
        if name == "launch_product":
            return self.launch(args["description"])
        return {"error": f"unknown tool {name}"}

    def ask(self, text: str, direction: str = "in", said: bool = False) -> str:
        """Seller's words (typed, transcribed, or scripted by the autopilot as "in_auto") → tools → one reply."""
        if not said:
            self.ledger.say(direction, text)
        r = self.models.spark("boss", [{"role": "user", "content": text}], tools=BOSS_TOOLS, instructions=BOSS_PROMPT, ref="boss")
        for _ in range(6):
            calls = [o for o in r.output if o.type == "function_call"]
            if not calls:
                break
            outs = [{"type": "function_call_output", "call_id": c.call_id,
                     "output": json.dumps(self.tool(c.name, json.loads(c.arguments or "{}")), ensure_ascii=False, default=str)}
                    for c in calls]
            r = self.models.spark("boss", outs, tools=BOSS_TOOLS, instructions=BOSS_PROMPT, previous_response_id=r.id, ref="boss")
        reply = (r.output_text or "").strip() or "Done."
        self.msg.send(reply)
        return reply

    # ---- chat without a model: answers from the store's own records, and decisions really run
    def ask_offline(self, text: str, direction: str = "in", said: bool = False) -> str:
        if not said:
            self.ledger.say(direction, text)
        reply = self._offline_reply(text.strip())
        self.ledger.log("executor", "chat", f"answered from the records, no model: “{text.strip()[:80]}”")
        self.msg.send(reply)
        return reply

    @staticmethod
    def _describe(p):
        a = p["args"]
        what = {"request_refund": f"refund ₩{int(a.get('amount', 0)):,}", "request_reship": "reship", "publish_product": "publish product"}.get(p["type"], p["type"])
        return f"#{a.get('order_id', a.get('product_id', ''))} {what}"

    def _offline_reply(self, t: str) -> str:
        low = t.lower()
        pend = self.list_pending()
        nums = [int(n) for n in re.findall(r"#?(\d+)", t)]
        everyone = re.search(r"\ball\b|everything|전부|모두", low)
        no = re.search(r"not now|\bno\b|reject|hold|don'?t|skip|보류|하지\s*마|나중", low)
        yes = re.search(r"approve|\byes\b|\bok|go ahead|\bdo\b|refund|reship|send|publish|승인|해", low)
        if (nums or everyone) and (yes or no):
            # a number is a list number or an order number
            targets = pend if everyone and not nums else [p for p in pend if p["n"] in nums or int(p["args"].get("order_id") or 0) in nums]
            if not targets:
                return "Nothing is waiting under that number. Ask \"what's left?\""
            for p in targets:
                self.agent.decide(p["action_id"], not no, "chat")
            left = self.list_pending()
            done = ", ".join(self._describe(p) for p in targets)
            return f"{'Held' if no else 'Done'}: {done}." + (f" {len(left)} decision{'s' if len(left) != 1 else ''} left." if left else " Nothing else is waiting.")
        if re.search(r"left|pending|waiting|decide|approv|남았|대기", low):
            if not pend:
                return "Nothing is waiting for you."
            return "Waiting for you: " + " / ".join(f"{p['n']}. {self._describe(p)}" for p in pend) + f". Say \"approve {pend[0]['n']}\" or \"hold {pend[-1]['n']}\"."
        if re.search(r"how|night|yesterday|today|summary|brief|어땠|어제|오늘", low):
            b = self.briefing()
            yours = self.ledger.q("select order_id, title from exceptions where status='escalated' and opened>=?", time.time() - 24 * 3600)
            out = f"In the last 24 hours {b['found']} orders broke and I fixed {b['fixed']}."
            if pend:
                out += " Waiting for you: " + " / ".join(f"{p['n']}. {self._describe(p)}" for p in pend) + "."
            if yours:
                out += " Yours to handle: " + ", ".join(f"#{y['order_id']}" for y in yours) + "."
            return out
        return "Try: \"how was last night?\", \"what's left?\", \"approve 1\", \"hold 2\"."

    def launch(self, description: str) -> dict:
        """Spark writes ko/en/ja copy → health check → draft product in the store → seller approves publishing."""
        listing = self.models.spark_json("listing", [{"role": "user", "content":
            "Write a product listing for this item. Korean, English and Japanese descriptions, 3–5 sentences each, "
            "factual only, no health or efficacy claims. Price in KRW.\nItem: " + description}], LISTING_SCHEMA, ref="launch")
        copy = " ".join([listing["title"], listing["ko"], listing["en"], listing["ja"]])
        if HEALTH.search(copy):
            self.ledger.log("policy", "gate", "listing blocked: health or efficacy wording", "launch")
            return {"status": "blocked", "rule": "health or efficacy wording"}
        body = "".join(f"<h3>{lang}</h3><p>{listing[lang]}</p>" for lang in ("ko", "en", "ja"))
        pid = self.agent.store.create_product({"title": listing["title"], "body_html": body, "price": listing["price_krw"], "tags": listing["tags"]})
        self.ledger.log("executor", "execute", f"create_product {pid} (draft) · {listing['title']}", "launch")
        return self.agent.exec.call(None, "publish_product", {"product_id": pid, "title": listing["title"], "price": listing["price_krw"]})
