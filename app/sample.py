"""The night Lookout opens on until a Meta API key is set, so the page explains itself on first open.

The fixes go through the real executor (gate, idempotency key, write, read-back) on the demo store, so the
Approve buttons really work. The problem titles and the one-line summaries are written by hand, not by a
model, and the first log line says so; no model call is invented.
"""
import time

HOUR = 3600
NO_UNIT = "no building or unit number"


def load(agent):
    from .boss import Boss
    led, store, ex = agent.ledger, agent.store, agent.exec
    led.reset()
    led.log("executor", "preloaded", "Preloaded night: titles and summaries are written by hand and no model was called. "
                                     "Store actions below ran through the real executor.")
    night = time.time() - 9 * HOUR

    def order(oid, name, lang, line1, line2, sku, title, total, **kw):
        store.create_order({"id": oid, "customer": {"name": name, "lang": lang}, "address": {"line1": line1, "line2": line2},
                            "items": [{"sku": sku, "title": title, "qty": 1}], "total": total, **kw})

    def problem(at_h, type_, oid, title, evidence, steps, story):
        last_msg = led.q("select coalesce(max(id),0) m from messages")[0]["m"]
        eid = led.open_exception(type_, oid, title, evidence)
        for tool, args in steps:
            ex.call(eid, tool, args)
        at = night + at_h * HOUR
        led.x("update exceptions set opened=?, status=?, story=? where id=?", at, agent.status_of(eid), story, eid)
        led.x("update messages set at=? where id>?", at, last_msg)  # the seller's ask lands at the problem's time
        return eid

    def address_fix(oid, lang, message, unit):
        return [("hold_order", {"order_id": oid, "reason": NO_UNIT}),
                ("notify_customer", {"order_id": oid, "language": lang, "message": message}),
                ("update_address", {"order_id": oid, "line2": unit}),
                ("release_order", {"order_id": oid})]

    order("1042", "김*희", "ko", "서울 송파구 새봄로 12 새봄마을아파트", "", "SOAP-3", "Eucalyptus soap ×3", 24000)
    order("1061", "Wei L.", "zh", "上海市浦东新区张杨路 88 弄 金桥公寓", "", "HONEY-250", "Manuka honey 250g", 38000)
    order("1102", "Yuki T.", "ja", "東京都渋谷区神南1-2-3", "401", "BEANIE-M", "Merino beanie M", 32000)
    order("1110", "Sora K.", "ja", "大阪府大阪市北区梅田2-4-9", "402", "SOCK-M", "Merino socks M", 19000)
    order("1088", "박*민", "ko", "경기 성남시 분당구 정자로 7 느티마을아파트", "", "SOCK-M", "Merino socks M", 19000)
    order("1094", "Noah P.", "en", "21 King St", "Apt 5", "BEANIE-M", "Merino beanie M", 32000)
    order("1120", "Lena K.", "de", "Torstraße 50", "Wohnung 3", "HONEY-250", "Manuka honey 250g", 38000)
    order("1131", "Lucía R.", "es", "Calle de Alcalá 21", "3º B", "SOAP-3", "Eucalyptus soap ×3", 24000)
    order("1017", "이*진", "ko", "부산 해운대구 우동로 7", "1203호", "SOAP-3", "Eucalyptus soap ×3", 24000,
          tracking={"carrier": "CJ", "number": "6841-2219-0457", "stalled_days": 3})
    order("1009", "최*아", "ko", "대구 수성구 달구벌대로 400", "1504호", "SOCK-M", "Merino socks M", 19000,
          tracking={"carrier": "Hanjin", "number": "5120-7734-1186", "stalled_days": 3})
    for oid in ("1017", "1009"):
        store.orders[oid]["status"] = "fulfilled"
    order("1149", "정*우", "ko", "서울 마포구 성미산로 3", "202호", "HONEY-250", "Manuka honey 250g", 38000)
    order("1055", "Emma W.", "en", "88 Cecil St", "Unit 4", "HONEY-250", "Manuka honey 250g ×2", 76000)

    problem(0.7, "address", "1042", "Apartment address has no building or unit number",
            {"kind": "order_created", "order": {"address": {"line1": "서울 송파구 새봄로 12 새봄마을아파트"}}},
            address_fix("1042", "ko", "배송지에 동·호수가 없어 출고를 잠시 멈췄어요. 동·호수를 알려 주시면 바로 보내 드릴게요.", "302동 1104호"),
            "Held the parcel, asked the customer in Korean, and shipped it once she replied with 302동 1104호.")
    problem(1.3, "address", "1061", "Apartment address has no building or unit number",
            {"kind": "order_created", "order": {"address": {"line1": "上海市浦东新区张杨路 88 弄 金桥公寓"}}},
            address_fix("1061", "zh", "您的地址缺少楼号和房间号，我们暂停了发货。请回复告诉我们，我们会马上寄出。", "7号楼 1203室"),
            "Held the parcel, asked in Chinese, patched the address to 7号楼 1203室 and shipped it.")
    problem(2.1, "stock", "1102", "Sold out in Seoul; Busan still has 4",
            {"kind": "order_created", "order": {"address": {"line1": "東京都渋谷区神南1-2-3", "line2": "401"}}},
            [("move_stock", {"sku": "BEANIE-M", "qty": 1, "from_location": "Busan", "to_location": "Seoul"})],
            "Moved one beanie from the Busan shelf so the Tokyo order ships today.")
    problem(2.8, "other", "1110", "Customer corrected the room number",
            {"kind": "customer_message", "text": "部屋番号を間違えました。402ではなく404です。"},
            [("update_address", {"order_id": "1110", "line2": "404"}),
             ("notify_customer", {"order_id": "1110", "language": "ja", "message": "部屋番号を404に修正しました。ご連絡ありがとうございます。"})],
            "Changed the room from 402 to 404 before it shipped and confirmed in Japanese.")
    problem(3.4, "address", "1088", "Apartment address has no building or unit number",
            {"kind": "order_created", "order": {"address": {"line1": "경기 성남시 분당구 정자로 7 느티마을아파트"}}},
            address_fix("1088", "ko", "배송지에 동·호수가 없어 출고를 잠시 멈췄어요. 답장으로 알려 주세요.", "205동 702호"),
            "Same problem, same fix: held, asked, patched to 205동 702호, shipped.")
    problem(4.0, "stock", "1094", "Sold out in Seoul; Busan still has 3",
            {"kind": "order_created", "order": {"address": {"line1": "21 King St", "line2": "Apt 5"}}},
            [("move_stock", {"sku": "BEANIE-M", "qty": 1, "from_location": "Busan", "to_location": "Seoul"})],
            "Moved another beanie from Busan. Two left there; worth a reorder.")
    refund_de = problem(4.6, "cancel", "1120", "Customer asks to cancel before shipping",
            {"kind": "customer_message", "text": "Bitte storniert Bestellung 1120 und erstattet mir das Geld."},
            [("cancel_order", {"order_id": "1120", "reason": "customer asked before shipping"}),
             ("notify_customer", {"order_id": "1120", "language": "de", "message": "Ihre Bestellung ist storniert. Die Erstattung bestätigen wir heute."}),
             ("request_refund", {"order_id": "1120", "amount": 38000, "reason": "cancelled before shipping"})],
            "Cancelled before it shipped and told her in German.")
    agent.decide(led.q("select id from actions where exception_id=? and state='pending'", refund_de)[0]["id"], True, "button")
    problem(5.3, "delay", "1009", "Tracking has not moved for 3 days",
            {"kind": "tracking_update", "tracking": {"carrier": "Hanjin", "number": "5120-7734-1186", "stalled_days": 3}},
            [("notify_customer", {"order_id": "1009", "language": "ko", "message": "배송 조회가 3일째 멈춰 택배사에 확인했어요. 오늘 다시 움직이기 시작했어요."})],
            "The carrier scanned it again this morning, so Lookout just told the customer. No reship needed.")
    problem(6.2, "delay", "1017", "Tracking has not moved for 3 days",
            {"kind": "tracking_update", "tracking": {"carrier": "CJ", "number": "6841-2219-0457", "stalled_days": 3}},
            [("notify_customer", {"order_id": "1017", "language": "ko", "message": "배송 조회가 3일째 멈춰 택배사에 확인을 요청했어요. 내일까지 알려 드릴게요."}),
             ("request_reship", {"order_id": "1017", "reason": "no tracking scan for 3 days"})],
            "Told the customer before she had to ask. A reship costs money, so Lookout asked first.")
    problem(6.8, "other", "1149", "Customer asks if the honey helps immunity",
            {"kind": "customer_message", "text": "이 마누카 꿀 먹으면 면역력이 좋아지나요?"},
            [("notify_customer", {"order_id": "1149", "language": "ko", "message": "마누카 꿀은 면역력에 도움이 돼요."})],
            "A reply made a health claim, so the policy gate stopped it before it was sent. This one is yours.")
    problem(7.5, "cancel", "1055", "Customer asks to cancel before shipping",
            {"kind": "customer_message", "text": "Hi, I ordered the wrong size jar. Please cancel order 1055 and refund me before it ships."},
            [("cancel_order", {"order_id": "1055", "reason": "customer asked before shipping"}),
             ("notify_customer", {"order_id": "1055", "language": "en", "message": "Your order is cancelled. We'll confirm your refund today."}),
             ("request_refund", {"order_id": "1055", "amount": 76000, "reason": "cancelled before shipping"})],
            "Cancelled before it shipped and told her in English.")
    problem(8.2, "cancel", "1131", "Customer asks to cancel before shipping",
            {"kind": "customer_message", "text": "Por favor cancelen el pedido 1131 y devuélvanme el dinero."},
            [("cancel_order", {"order_id": "1131", "reason": "customer asked before shipping"}),
             ("notify_customer", {"order_id": "1131", "language": "es", "message": "Su pedido está cancelado. Confirmaremos el reembolso hoy."}),
             ("request_refund", {"order_id": "1131", "amount": 24000, "reason": "cancelled before shipping"})],
            "Cancelled before it shipped and told her in Spanish.")
    Boss(agent).ask_offline("How was last night?")
