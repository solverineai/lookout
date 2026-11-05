"""Live check against a Shopify dev store. Skipped unless SHOPIFY_STORE, SHOPIFY_TOKEN and SHOPIFY_TEST_ORDER_ID are set.

Run before the demo: .venv/bin/python -m pytest -q tests/test_shopify_live.py
Use an unshipped test order (placed with Shopify's test gateway). It adds a note, holds and releases the order.
"""
import os

import pytest

from app import config

pytestmark = pytest.mark.skipif(not (config.SHOPIFY_STORE and config.SHOPIFY_TOKEN and os.environ.get("SHOPIFY_TEST_ORDER_ID")),
                                reason="Shopify dev store not configured")


def test_read_note_hold_release_round_trip():
    from app.store import ShopifyStore
    s, oid = ShopifyStore(), os.environ["SHOPIFY_TEST_ORDER_ID"]
    o = s.get_order(oid)
    assert o and o["status"] in ("open", "held"), o
    s.add_note(oid, "Lookout live check")
    assert "Lookout live check" in s.get_order(oid)["notes"][0]
    s.hold(oid, "Lookout live check")
    assert s.get_order(oid)["status"] == "held"
    s.release(oid)
    assert s.get_order(oid)["status"] == "open"
