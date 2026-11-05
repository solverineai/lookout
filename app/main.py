"""Lookout web service: the seller's page, the judge's controls, and webhooks for Shopify and WhatsApp."""
import base64
import hashlib
import hmac
import itertools
import json
import queue
import threading
import time

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from . import config, sample, simulator
from .agent import Agent
from .boss import Boss
from .ledger import Ledger
from .messenger import Messenger
from .models import CostCapReached, Models
from .autopilot import Autopilot
from .store import MemoryStore, make_store

app = FastAPI(title="Lookout")
ledger = Ledger()
models = Models(ledger)
agent = Agent(ledger, models, make_store(), Messenger(ledger))
boss = Boss(agent)

# One worker so model calls and store writes happen in order, never interleaved.
class Jobs:
    """Work runs one at a time, in order. Seller decisions and chat (priority 0) go ahead of arriving orders (1)."""

    def __init__(self):
        self.q, self.seq, self.chat = queue.PriorityQueue(), itertools.count(), 0

    def put(self, item, prio=1):
        if len(item) > 3 and item[3] == "chat":
            self.chat += 1
        self.q.put((prio, next(self.seq), item))

    def get(self):
        return self.q.get()[2]

    def qsize(self):
        return self.q.qsize()

    def empty(self):
        return self.q.empty()

    def task_done(self):
        self.q.task_done()


jobs = Jobs()
busy = threading.Event()


def worker():
    while True:
        fn, args, delay, *tag = jobs.get()
        busy.set()
        try:
            time.sleep(delay)
            fn(*args)
        except CostCapReached:
            agent.msg.send(f"Today's model cost cap (${config.DAILY_COST_CAP:.2f}) is reached, so I paused.")
        except Exception as e:  # keep the worker alive; the ledger shows what failed
            ledger.log("executor", "error", f"{getattr(fn, '__name__', fn)}: {e}")
        finally:
            if tag == ["chat"]:
                jobs.chat -= 1
            busy.clear()
            jobs.task_done()


threading.Thread(target=worker, daemon=True).start()
autopilot = Autopilot(agent, boss, jobs)
LIVE = bool(config.META_API_KEY)
if isinstance(agent.store, MemoryStore):
    sample.load(agent)  # the demo store opens on a preloaded night; live problems are added on top
    if LIVE and config.AUTOPILOT:
        autopilot.start()


def need_live():
    if not LIVE:
        raise HTTPException(503, "This is a sample night. Running it live needs a Meta API key on the server.")


@app.get("/")
def page():
    return FileResponse(config.ROOT / "web" / "index.html")


@app.get("/api/state")
def state():
    b = boss.briefing()
    pend = {p["action_id"]: p["n"] for p in boss.list_pending()}
    start = ledger.q("select coalesce(max(id),0) m from ledger where kind='run_start'")[0]["m"]  # order ids repeat across nights
    msgs = ledger.q("select m.*, a.state from messages m left join actions a on a.id=m.action_id order by m.id desc limit 60")
    return {"brief": b, "busy": busy.is_set() or not jobs.empty(), "thinking": jobs.chat > 0,
            "exceptions": [e | {"actions": ledger.q("select id,type,args,decision,state from actions where exception_id=? order by id", e["id"]),
                                "models": ledger.q("select actor, sum(cost) cost from ledger where id>=? and (ref=? or ref=?) and actor in ('spark','glimmer','voice') and tokens_in>0 group by actor",
                                                   start, f"X{e['id']}", e["order_id"])}
                           for e in ledger.q("select * from exceptions order by opened desc limit 40")],
            "incoming": ledger.q("select at, detail from ledger where kind='verdict' and id>=? order by id desc limit 40", start),
            "messages": [m | {"n": pend.get(m["action_id"])} for m in reversed(msgs)],
            "ledger": ledger.run_rows(),
            "live": {"spark": bool(config.META_API_KEY), "glimmer": bool(config.GLIMMER_API_KEY),
                     "shopify": not isinstance(agent.store, MemoryStore), "whatsapp": agent.msg.live,
                     "autopilot": LIVE and config.AUTOPILOT and isinstance(agent.store, MemoryStore), "sample": not LIVE,
                     "cap": config.DAILY_COST_CAP}}


@app.get("/api/exceptions/{exc_id}")
def exception_detail(exc_id: int):
    """Everything recorded for one problem: the triggering event, every model call, gate decision, store write and decision."""
    rows = ledger.q("select * from exceptions where id=?", exc_id)
    if not rows:
        raise HTTPException(404, "No such problem.")
    e = rows[0]
    actions = ledger.q("select * from actions where exception_id=? order by id", exc_id)
    start = ledger.q("select coalesce(max(id),0) m from ledger where kind='run_start'")[0]["m"]  # order ids repeat across nights
    audit = ledger.q("select * from ledger where id>=? and (ref=? or ref=?) order by id", start, f"X{exc_id}", e["order_id"])
    asks = ledger.q("select * from messages where action_id in (select id from actions where exception_id=?) order by id", exc_id)
    return {"exception": e, "actions": actions, "audit": audit, "asks": asks}


@app.post("/api/night")
def night():
    """Replay one night on the demo store: fresh store, fresh ledger, real model calls."""
    need_live()
    if not isinstance(agent.store, MemoryStore):
        raise HTTPException(409, "The night simulator runs on the demo store. With Shopify connected, place test orders instead.")
    if busy.is_set() or not jobs.empty():
        raise HTTPException(409, "A night is already running.")
    agent.store = agent.exec.store = MemoryStore()
    sample.load(agent)
    agent.msg.send("Got it. I'll watch the orders tonight and only ask you about money.")
    for ev in simulator.night(agent.store):
        jobs.put((agent.handle, (ev,), 2.0))
    return {"queued": jobs.qsize()}


@app.post("/api/events")
async def event(req: Request):
    """Judges break an order themselves: any order fields, any customer message."""
    need_live()
    ev = await req.json()
    if not isinstance(ev, dict) or "kind" not in ev:
        raise HTTPException(400, "Send an event with a kind, e.g. order_created or customer_message.")
    if ev.get("kind") == "order_created" and isinstance(agent.store, MemoryStore):
        ev["order_id"] = agent.store.create_order(ev.get("order", {}))
    jobs.put((agent.handle, (ev,), 0))
    return {"queued": True, "order_id": ev.get("order_id")}


@app.post("/api/decide")
async def decide(req: Request):
    d = await req.json()
    jobs.put((agent.decide, (int(d["action_id"]), bool(d["ok"]), "button"), 0), prio=0)
    return {"queued": True}


@app.post("/api/boss")
async def boss_text(req: Request):
    text = str((await req.json()).get("text", "")).strip()[:500]
    if not text:
        raise HTTPException(400, "Say something to Lookout.")
    ledger.say("in", text)  # show the seller's words at once, even while orders are being worked
    jobs.put((boss.ask if LIVE else boss.ask_offline, (text, "in", True), 0, "chat"), prio=0)
    return {"queued": True}


@app.post("/api/boss/audio")
async def boss_audio(file: UploadFile):
    need_live()
    audio = await file.read()
    if len(audio) > 32_000_000:
        raise HTTPException(413, "Voice notes up to 32 MB.")
    jobs.put((lambda a: boss.ask(models.transcribe(a, ref="boss")), (audio,), 0, "chat"), prio=0)
    return {"queued": True}


# ---- WhatsApp Cloud API webhook
@app.get("/webhooks/whatsapp")
def wa_verify(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and config.WHATSAPP_VERIFY_TOKEN and p.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403)


@app.post("/webhooks/whatsapp")
async def wa_inbound(request: Request):
    raw = await request.body()
    if not config.WHATSAPP_APP_SECRET:
        raise HTTPException(503, "Set WHATSAPP_APP_SECRET to accept WhatsApp webhooks.")
    sig = "sha256=" + hmac.new(config.WHATSAPP_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401)
    for entry in json.loads(raw).get("entry", []):
        for ch in entry.get("changes", []):
            for m in ch.get("value", {}).get("messages", []):
                if m.get("from") != config.SELLER_WHATSAPP:  # only the seller can steer Lookout
                    continue
                if m["type"] == "text":
                    jobs.put((boss.ask, (m["text"]["body"][:500],), 0))
                elif m["type"] == "interactive":
                    rid = m["interactive"].get("button_reply", {}).get("id", "")
                    if rid[:3] in ("ok:", "no:") and rid[3:].isdigit():
                        jobs.put((agent.decide, (int(rid[3:]), rid.startswith("ok:"), "whatsapp"), 0))
                elif m["type"] == "audio":
                    media = m["audio"]["id"]
                    jobs.put((lambda mid: boss.ask(models.transcribe(agent.msg.download_media(mid), ref="boss")), (media,), 0))
    return {"ok": True}


# ---- Shopify webhook (orders/create)
@app.post("/webhooks/shopify")
async def shopify_inbound(request: Request):
    raw = await request.body()
    if not config.SHOPIFY_WEBHOOK_SECRET:
        raise HTTPException(503, "Set SHOPIFY_WEBHOOK_SECRET to accept Shopify webhooks.")
    sig = base64.b64encode(hmac.new(config.SHOPIFY_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(sig, request.headers.get("x-shopify-hmac-sha256", "")):
        raise HTTPException(401)
    o = json.loads(raw)
    a = o.get("shipping_address") or {}
    ev = {"kind": "order_created", "order_id": str(o["id"]), "order": {
        "name": o.get("name"), "customer": {"name": a.get("name", ""), "lang": o.get("customer_locale", "ko")},
        "address": {"line1": a.get("address1", ""), "line2": a.get("address2", ""), "city": a.get("city", ""), "zip": a.get("zip", "")},
        "items": [{"sku": li.get("sku"), "title": li.get("title"), "qty": li.get("quantity")} for li in o.get("line_items", [])],
        "total": o.get("total_price")}}
    jobs.put((agent.handle, (ev,), 0))
    return {"ok": True}
