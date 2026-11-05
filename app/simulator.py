"""The night: orders and messages arrive on a clock. Only the arrivals are scripted; every decision is a real model call."""

APT = "서울 송파구 새봄로 12 새봄마을아파트"


def night(store) -> list[dict]:
    """Seed the store and return the night's events in order."""
    store.create_order({"id": "3017", "customer": {"name": "이*진", "lang": "ko"}, "status": "fulfilled",
                        "address": {"line1": "부산 해운대구 우동로 7", "line2": "1203호", "city": "부산", "zip": "48095"},
                        "items": [{"sku": "SOAP-3", "title": "Eucalyptus soap ×3", "qty": 1}], "total": 24000,
                        "tracking": {"carrier": "CJ", "number": "6841-2219-0457", "stalled_days": 3}})
    store.orders["3017"]["status"] = "fulfilled"
    store.stock["Seoul"]["BEANIE-M"], store.stock["Busan"]["BEANIE-M"] = 0, 4  # the beanie order below must hit an empty shelf
    store.create_order({"id": "3055", "customer": {"name": "Emma W.", "lang": "en"},
                        "address": {"line1": "88 Cecil St", "line2": "Unit 4", "city": "Singapore", "zip": "069533"},
                        "items": [{"sku": "HONEY-250", "title": "Manuka honey 250g", "qty": 2}], "total": 76000})
    return [
        {"kind": "order_created", "order_id": "3101", "order": _order(store, "3101", "박*민", "ko",
            {"line1": "서울 마포구 성미산로 3", "line2": "202호", "city": "서울", "zip": "03990"}, "SOCK-M", "Merino socks M", 19000)},
        {"kind": "order_created", "order_id": "3042", "order": _order(store, "3042", "김*희", "ko",
            {"line1": APT, "line2": "", "city": "서울", "zip": "05510"}, "SOAP-3", "Eucalyptus soap ×3", 24000)},
        {"kind": "order_created", "order_id": "3102", "order": _order(store, "3102", "Yuki T.", "ja",
            {"line1": "東京都渋谷区神南1-2-3", "line2": "401", "city": "Tokyo", "zip": "150-0041"}, "BEANIE-M", "Merino beanie M", 32000),
         "note": "Ships from Seoul. Seoul stock of BEANIE-M is 0; Busan has 4."},
        {"kind": "tracking_update", "order_id": "3017", "tracking": store.orders["3017"]["tracking"]},
        {"kind": "customer_message", "order_id": "3055", "from": "Emma W.",
         "text": "Hi, I ordered the wrong size jar. Please cancel order 3055 and refund me before it ships."},
        {"kind": "customer_message", "order_id": "3042", "from": "김*희", "text": "302동 1104호예요. 확인 부탁드려요!"},
    ]


def _order(store, oid, name, lang, address, sku, title, total):
    spec = {"id": oid, "customer": {"name": name, "lang": lang}, "address": address,
            "items": [{"sku": sku, "title": title, "qty": 1}], "total": total}
    store.create_order(spec)
    return {k: v for k, v in spec.items() if k != "id"}
