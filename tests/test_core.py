"""Offline tests: a scripted stand-in for the Meta models drives the real agent, gate, executor and ledger."""
import hashlib
import hmac
import json
from types import SimpleNamespace as NS

import pytest

from app import policy
from app.agent import Agent
from app.boss import Boss
from app.ledger import Ledger
from app.messenger import Messenger
from app.store import MemoryStore


def call(name, **args):
    return NS(type="function_call", name=name, arguments=json.dumps(args, ensure_ascii=False), call_id=f"c_{name}")


class FakeModels:
    """Returns scripted Responses-API-shaped objects, one per spark() call."""

    def __init__(self, ledger, script, triage=None, listing=None):
        self.ledger, self.script, self.triage, self.listing, self.seen = ledger, list(script), triage, listing, []

    def spark(self, kind, input, **kw):
        self.seen.append(input)
        step = self.script.pop(0)
        out = step if isinstance(step, list) else []
        return NS(id=f"r{len(self.seen)}", output=out, output_text="" if out else step)

    def spark_json(self, kind, input, schema, **kw):
        return self.listing

    def glimmer_json(self, kind, system, user, ref=""):
        return self.triage


@pytest.fixture
def world(tmp_path):
    ledger = Ledger(str(tmp_path / "t.db"))
    store = MemoryStore()
    store.create_order({"id": "1042", "customer": {"name": "김*희", "lang": "ko"}, "items": [], "total": 24000,
                        "address": {"line1": "서울 새봄로 12 새봄마을아파트", "line2": "", "city": "서울", "zip": "05510"}})
    return ledger, store


def make(world, script, **kw):
    ledger, store = world
    models = FakeModels(ledger, script, **kw)
    return Agent(ledger, models, store, Messenger(ledger)), models


def test_gate_rules():
    assert policy.gate("refund", {"amount": 1})[0] == "approval"
    assert policy.gate("message_customer", {"message": "주소 확인 부탁드려요"})[0] == "auto"
    assert policy.gate("message_customer", {"message": "면역에 좋아요"})[0] == "blocked"
    assert policy.gate("publish_product", {"title": "Soap"})[0] == "approval"


def test_address_fix_runs_writes_and_verifies(world):
    agent, _ = make(world, [
        [call("get_order", order_id="1042")],
        [call("hold_order", order_id="1042", reason="no unit number")],
        [call("notify_customer", order_id="1042", message="동·호수를 알려 주세요", language="ko")],
        "주소에 동·호수가 없어 출고를 멈추고 고객에게 물었어요."],
        triage={"verdict": "exception", "type": "address", "reason": "no unit"})
    out = agent.handle({"kind": "order_created", "order_id": "1042"})
    ledger, store = world
    assert store.get_order("1042")["status"] == "held"
    exc = ledger.q("select * from exceptions where id=?", out["exception_id"])[0]
    assert exc["status"] == "fixed" and "동·호수" in exc["story"]
    assert len(ledger.q("select * from ledger where kind='execute'")) == 2


def test_same_write_never_runs_twice(world):
    agent, _ = make(world, [])
    args = {"order_id": "1042", "line2": "302동 1104호"}
    assert agent.exec.call(1, "update_address", args)["status"] == "done"
    assert agent.exec.call(1, "update_address", args)["status"] == "duplicate"
    ledger, store = world
    assert store.get_order("1042")["address"]["line2"] == "302동 1104호"
    assert len(ledger.q("select * from ledger where kind='skip_duplicate'")) == 1


def test_refund_waits_for_seller_then_runs_once(world):
    agent, _ = make(world, [])
    ledger, store = world
    r = agent.exec.call(ledger.open_exception("cancel", "1042", "cancel"), "request_refund", {"order_id": "1042", "amount": 24000, "reason": "cancel"})
    assert r["status"] == "waiting_for_seller" and store.get_order("1042")["refunded"] == 0
    assert ledger.q("select * from messages where action_id=?", r["action_id"])  # seller was asked
    assert agent.decide(r["action_id"], True, "button")["status"] == "done"
    assert store.get_order("1042")["refunded"] == 24000
    assert agent.decide(r["action_id"], True, "voice")["status"] == "already_decided"
    assert store.get_order("1042")["refunded"] == 24000


def test_bad_tool_arguments_do_not_crash_the_loop(world):
    agent, models = make(world, [[call("hold_order", order_id="1042")], "멈췄어요."],
                         triage={"verdict": "exception", "type": "address", "reason": "x"})
    agent.handle({"kind": "order_created", "order_id": "1042"})  # missing "reason"
    assert "bad arguments" in models.seen[1][0]["output"]


def test_voice_boss_decides_pending_refund(world):
    agent, models = make(world, [])
    ledger, store = world
    r = agent.exec.call(ledger.open_exception("cancel", "1042", "c"), "request_refund", {"order_id": "1042", "amount": 5000, "reason": "c"})
    models.script = [[call("list_pending")], [call("decide", action_id=r["action_id"], approve=True)], "환불했어요."]
    assert Boss(agent).ask("1번 환불해 줘") == "환불했어요."
    assert store.get_order("1042")["refunded"] == 5000


def test_launch_blocks_health_claims_and_asks_before_publishing(world):
    good = {"title": "Eucalyptus soap", "price_krw": 12000, "ko": "유칼립투스 향 비누", "en": "Eucalyptus soap", "ja": "石鹸", "tags": []}
    agent, models = make(world, [], listing=dict(good, en="Boosts your immune system"))
    assert Boss(agent).launch("soap")["status"] == "blocked"
    models.listing = good
    r = Boss(agent).launch("soap")
    _, store = world
    pid = json.loads(agent.ledger.action(id=r["action_id"])["args"])["product_id"]
    assert store.get_product(pid)["status"] == "draft"
    agent.decide(r["action_id"], True, "button")
    assert store.get_product(pid)["status"] == "active"


def test_whatsapp_webhook_rejects_bad_signature(monkeypatch):
    from fastapi.testclient import TestClient
    from app import config, main
    monkeypatch.setattr(config, "WHATSAPP_APP_SECRET", "s3cret")
    c = TestClient(main.app)
    body = b'{"entry": []}'
    assert c.post("/webhooks/whatsapp", content=body, headers={"x-hub-signature-256": "sha256=bad"}).status_code == 401
    good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert c.post("/webhooks/whatsapp", content=body, headers={"x-hub-signature-256": good}).status_code == 200


def test_autopilot_makes_valid_arrivals_and_a_marked_seller_reply(world, monkeypatch):
    import queue
    from app import config
    from app.autopilot import Autopilot
    agent, _ = make(world, [])
    jobs = queue.Queue()
    ap = Autopilot(agent, Boss(agent), jobs, seed=7)
    kinds = {ap.next_event()["kind"] for _ in range(60)}
    assert kinds == {"order_created", "tracking_update", "customer_message"}
    assert ap.followups, "an address problem schedules the customer's reply"
    assert all(agent.store.get_order(e["order_id"]) for _, e in ap.followups)
    # no reply while the approval is fresh; a marked scripted reply once it has waited
    ledger, _ = world
    agent.exec.call(ledger.open_exception("cancel", "1042", "c"), "request_refund", {"order_id": "1042", "amount": 1, "reason": "c"})
    assert ap.seller_reply() is None
    monkeypatch.setattr(config, "SELLER_REPLY_AFTER", 0)
    assert ap.seller_reply() == "approve 1 (refund)"
    ap.tick()
    assert any(fn == ap.boss.ask and args[1] == "in_auto" for fn, args, _ in list(jobs.queue))
    assert ledger.q("select * from ledger where kind='autopilot'")


def test_offline_chat_numbers_stay_put_and_decisions_run(world):
    agent, _ = make(world, [])
    ledger, store = world
    store.create_order({"id": "2", "customer": {"name": "x", "lang": "en"}, "items": [], "total": 9000, "address": {"line1": "a", "line2": "b"}})
    for oid, amt in (("1042", 1000), ("2", 9000)):
        agent.exec.call(ledger.open_exception("cancel", oid, "c"), "request_refund", {"order_id": oid, "amount": amt, "reason": "c"})
    boss = Boss(agent)
    assert "1. #1042" in boss.ask_offline("What's left?") and "2. #2" in boss.ask_offline("What's left?")
    assert boss.ask_offline("approve 1").startswith("Done: #1042")
    assert boss.ask_offline("hold 2").startswith("Held: #2")  # still #2 after #1 was decided
    assert store.get_order("1042")["refunded"] == 1000 and store.get_order("2")["refunded"] == 0


def test_same_move_for_two_orders_runs_twice(world):
    agent, _ = make(world, [])
    ledger, store = world
    move = {"sku": "BEANIE-M", "qty": 1, "from_location": "Busan", "to_location": "Seoul"}
    assert agent.exec.call(ledger.open_exception("stock", "a", "x"), "move_stock", move)["status"] == "done"
    assert agent.exec.call(ledger.open_exception("stock", "b", "x"), "move_stock", move)["status"] == "done"
    assert store.stock_of("BEANIE-M")["Seoul"] == 2
