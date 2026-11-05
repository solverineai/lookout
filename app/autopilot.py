"""Always-on demo shop: orders and customer messages keep arriving on their own, so a judge who opens the page
sees Lookout working without pressing anything. Arrivals are generated; every decision is a real model call.
The seller's replies are scripted too, and are marked as such everywhere they appear."""
import random
import threading
import time

from . import config

CUSTOMERS = [("김*희", "ko"), ("박*민", "ko"), ("이*진", "ko"), ("Yuki T.", "ja"), ("Sora K.", "ja"),
             ("Emma W.", "en"), ("Noah P.", "en"), ("Lena K.", "de"), ("Lucía R.", "es")]
GOOD_ADDRESS = {"ko": ("서울 마포구 성미산로 3", "202호"), "ja": ("東京都渋谷区神南1-2-3", "401"), "en": ("88 Cecil St", "Unit 4"),
                "de": ("Torstraße 50", "Wohnung 3"), "es": ("Calle de Alcalá 21", "3º B")}
APARTMENTS = ["서울 송파구 새봄로 12 새봄마을아파트", "서울 강서구 마곡로 21 마곡엠밸리아파트", "경기 성남시 분당구 정자로 7 느티마을아파트"]
ITEMS = [("SOCK-M", "Merino socks M", 19000), ("SOAP-3", "Eucalyptus soap ×3", 24000), ("HONEY-250", "Manuka honey 250g", 38000),
         ("BEANIE-M", "Merino beanie M", 32000)]
CANCEL_TEXT = {"ko": "주문 {id} 취소하고 환불해 주세요. 아직 안 보냈죠?", "en": "Please cancel order {id} and refund me, it hasn't shipped yet.",
               "ja": "注文{id}をキャンセルして返金してください。まだ発送されていませんよね？", "de": "Bitte storniert Bestellung {id} und erstattet mir das Geld.",
               "es": "Por favor cancelen el pedido {id} y devuélvanme el dinero."}
VERB = {"request_refund": "refund", "request_reship": "reship", "publish_product": "publish"}


class Autopilot:
    def __init__(self, agent, boss, jobs, seed=None):
        self.agent, self.boss, self.jobs = agent, boss, jobs
        self.rng = random.Random(seed)
        self.followups: list[tuple[float, dict]] = []  # (due time, event)

    # ---- the shop's next arrival
    def next_event(self) -> dict:
        r, store = self.rng.random(), self.agent.store
        name, lang = self.rng.choice(CUSTOMERS)
        sku, title, price = self.rng.choice(ITEMS[:3])
        line1, line2 = GOOD_ADDRESS[lang]
        if r < 0.55:  # most orders are fine and should pass straight through
            return self._order(name, lang, line1, line2, sku, title, price)
        if r < 0.70:
            name, lang = self.rng.choice(CUSTOMERS[:3])
            ev = self._order(name, lang, self.rng.choice(APARTMENTS), "", sku, title, price)
            unit = f"{self.rng.randint(101, 512)}동 {self.rng.randint(2, 25)}{self.rng.randint(1, 4):02d}호"
            self.followups.append((time.time() + self.rng.uniform(240, 420),
                                   {"kind": "customer_message", "order_id": ev["order_id"], "from": name, "text": f"{unit}예요. 확인 부탁드려요!"}))
            return ev
        if r < 0.80:
            store.stock["Seoul"]["BEANIE-M"], store.stock["Busan"]["BEANIE-M"] = 0, max(store.stock["Busan"]["BEANIE-M"], 3)
            ev = self._order(name, lang, line1, line2, "BEANIE-M", "Merino beanie M", 32000)
            ev["note"] = "Ships from Seoul."
            return ev
        if r < 0.90:
            oid = store.create_order({"customer": {"name": name, "lang": lang}, "address": {"line1": line1, "line2": line2},
                                      "items": [{"sku": sku, "title": title, "qty": 1}], "total": price,
                                      "tracking": {"carrier": "CJ", "number": f"{self.rng.randint(1000, 9999)}-{self.rng.randint(1000, 9999)}", "stalled_days": 3}})
            store.orders[oid]["status"] = "fulfilled"
            return {"kind": "tracking_update", "order_id": oid, "tracking": store.orders[oid]["tracking"]}
        ev = self._order(name, lang, line1, line2, sku, title, price)  # an unshipped order whose customer then cancels
        return {"kind": "customer_message", "order_id": ev["order_id"], "from": name, "text": CANCEL_TEXT[lang].format(id=ev["order_id"])}

    def _order(self, name, lang, line1, line2, sku, title, price):
        spec = {"customer": {"name": name, "lang": lang}, "address": {"line1": line1, "line2": line2},
                "items": [{"sku": sku, "title": title, "qty": 1}], "total": price}
        oid = self.agent.store.create_order(spec)
        return {"kind": "order_created", "order_id": oid, "order": spec}

    # ---- the scripted seller: answers the oldest approval after a while, in Korean
    def seller_reply(self) -> str | None:
        pend = self.agent.ledger.pending()
        if not pend or time.time() - pend[0]["created"] < config.SELLER_REPLY_AFTER:
            return None
        return f"approve 1 ({VERB.get(pend[0]['type'], 'ok')})"

    def tick(self):
        if self.jobs.qsize() > 2:  # the worker is behind; don't pile up
            return
        now = time.time()
        due = [e for t, e in self.followups if t <= now]
        self.followups = [(t, e) for t, e in self.followups if t > now]
        for ev in due or [self.next_event()]:
            self.jobs.put((self.agent.handle, (ev,), 0))
        text = self.seller_reply()
        if text:
            self.agent.ledger.log("seller", "autopilot", f"scripted seller reply for the demo: “{text}”")
            self.jobs.put((self.boss.ask, (text, "in_auto"), 0))

    def run(self):
        time.sleep(5)
        while True:
            try:
                self.tick()
            except Exception as e:  # never stop the shop over one bad tick
                self.agent.ledger.log("executor", "error", f"autopilot: {e}")
            time.sleep(config.AUTOPILOT_SECONDS)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
