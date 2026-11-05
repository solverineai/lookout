"""Store adapters. Same interface for the in-memory demo store and a real Shopify store.

Every write is followed by a read in the executor (verify), so adapters only need to do the write.
"""
import copy
import itertools

import httpx

from . import config


class MemoryStore:
    """A small synthetic shop. Used by the night simulator and the tests."""

    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.products: dict[str, dict] = {}
        self.stock = {"Seoul": {"BEANIE-M": 0, "SOAP-3": 30, "SOCK-M": 25, "HONEY-250": 40},
                      "Busan": {"BEANIE-M": 4, "SOAP-3": 10, "SOCK-M": 10, "HONEY-250": 0}}
        self._ids = itertools.count(2001)  # simulator uses fixed ids below 2000

    def create_order(self, spec: dict) -> str:
        oid = spec.get("id") or str(next(self._ids))
        self.orders[oid] = {"id": oid, "name": f"#{oid}", "status": "open", "refunded": 0, "notes": [],
                            "tracking": spec.get("tracking", {"stalled_days": 0}),
                            **{k: copy.deepcopy(v) for k, v in spec.items() if k != "id"}}
        return oid

    def get_order(self, oid):
        o = self.orders.get(str(oid))
        return copy.deepcopy(o) if o else None

    def update_address(self, oid, address):
        self.orders[oid]["address"].update(address)

    def hold(self, oid, reason):
        self.orders[oid]["status"] = "held"

    def release(self, oid):
        self.orders[oid]["status"] = "open"

    def cancel(self, oid, reason):
        if self.orders[oid]["status"] == "fulfilled":
            raise ValueError("order already shipped")
        self.orders[oid]["status"] = "cancelled"

    def move_stock(self, sku, qty, from_loc, to_loc):
        if self.stock[from_loc][sku] < qty:
            raise ValueError(f"only {self.stock[from_loc][sku]} {sku} at {from_loc}")
        self.stock[from_loc][sku] -= qty
        self.stock[to_loc][sku] += qty

    def stock_of(self, sku):
        return {loc: s.get(sku, 0) for loc, s in self.stock.items()}

    def add_note(self, oid, text):
        self.orders[oid]["notes"].append(text)

    def refund(self, oid, amount):
        self.orders[oid]["refunded"] += amount

    def reship(self, oid):
        o = self.orders[oid]
        return self.create_order({"customer": o["customer"], "address": o["address"], "items": o["items"], "total": 0})

    def create_product(self, listing):
        pid = f"P{len(self.products) + 1}"
        self.products[pid] = {"id": pid, "status": "draft", **listing}
        return pid

    def publish_product(self, pid):
        self.products[pid]["status"] = "active"

    def get_product(self, pid):
        return copy.deepcopy(self.products.get(pid))


class ShopifyStore:
    """Shopify Admin GraphQL. shortcut: mutations follow the Admin API docs but were not run against a
    dev store in this build; run tests/test_shopify_live.py once SHOPIFY_* is set before the demo."""

    def __init__(self):
        self.url = f"https://{config.SHOPIFY_STORE}/admin/api/{config.SHOPIFY_API_VERSION}/graphql.json"
        self.h = {"X-Shopify-Access-Token": config.SHOPIFY_TOKEN, "Content-Type": "application/json"}

    def gql(self, query, **variables):
        r = httpx.post(self.url, json={"query": query, "variables": variables}, headers=self.h, timeout=30)
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(body["errors"])
        data = body["data"]
        for v in data.values():  # surface userErrors from any mutation
            if isinstance(v, dict) and v.get("userErrors"):
                raise RuntimeError(v["userErrors"])
        return data

    gid = staticmethod(lambda kind, id: id if str(id).startswith("gid://") else f"gid://shopify/{kind}/{id}")

    def get_order(self, oid):
        d = self.gql("""query($id:ID!){order(id:$id){id name note cancelledAt displayFulfillmentStatus
          customer{displayName locale} totalPriceSet{shopMoney{amount}} totalRefundedSet{shopMoney{amount}}
          shippingAddress{name address1 address2 city province zip countryCodeV2 phone}
          lineItems(first:20){nodes{sku title quantity}} fulfillmentOrders(first:5){nodes{id status}}}}""",
                     id=self.gid("Order", oid))["order"]
        if not d:
            return None
        fo = d["fulfillmentOrders"]["nodes"]
        status = ("cancelled" if d["cancelledAt"] else "fulfilled" if d["displayFulfillmentStatus"] == "FULFILLED"
                  else "held" if any(f["status"] == "ON_HOLD" for f in fo) else "open")
        a = d["shippingAddress"] or {}
        return {"id": oid, "name": d["name"], "status": status, "notes": [d["note"] or ""],
                "customer": {"name": (d["customer"] or {}).get("displayName", ""), "lang": (d["customer"] or {}).get("locale", "ko")},
                "address": {"line1": a.get("address1", ""), "line2": a.get("address2", ""), "city": a.get("city", ""), "zip": a.get("zip", "")},
                "items": [{"sku": n["sku"], "title": n["title"], "qty": n["quantity"]} for n in d["lineItems"]["nodes"]],
                "total": float(d["totalPriceSet"]["shopMoney"]["amount"]),
                "refunded": float(d["totalRefundedSet"]["shopMoney"]["amount"]), "_fo": [f["id"] for f in fo]}

    def update_address(self, oid, address):
        a = {k2: address[k] for k, k2 in (("line1", "address1"), ("line2", "address2"), ("city", "city"), ("zip", "zip")) if k in address}
        self.gql("mutation($i:OrderInput!){orderUpdate(input:$i){order{id} userErrors{field message}}}",
                 i={"id": self.gid("Order", oid), "shippingAddress": a})

    def hold(self, oid, reason):
        for fo in self.get_order(oid)["_fo"]:
            self.gql("""mutation($id:ID!,$h:FulfillmentOrderHoldInput!){fulfillmentOrderHold(id:$id,fulfillmentHold:$h)
              {fulfillmentOrder{id} userErrors{field message}}}""", id=fo, h={"reason": "OTHER", "reasonNotes": reason})

    def release(self, oid):
        for fo in self.get_order(oid)["_fo"]:
            self.gql("mutation($id:ID!){fulfillmentOrderReleaseHold(id:$id){fulfillmentOrder{id} userErrors{field message}}}", id=fo)

    def cancel(self, oid, reason):
        self.gql("""mutation($id:ID!){orderCancel(orderId:$id,reason:CUSTOMER,refund:false,restock:true,notifyCustomer:false)
          {orderCancelUserErrors{field message}}}""", id=self.gid("Order", oid))

    def add_note(self, oid, text):
        old = self.get_order(oid)["notes"][0]
        self.gql("mutation($i:OrderInput!){orderUpdate(input:$i){order{id} userErrors{field message}}}",
                 i={"id": self.gid("Order", oid), "note": (old + "\n" + text).strip()})

    def refund(self, oid, amount):
        tx = self.gql("""query($id:ID!){order(id:$id){transactions(first:10){id kind status gateway}}}""",
                      id=self.gid("Order", oid))["order"]["transactions"]
        parent = next(t for t in tx if t["kind"] in ("SALE", "CAPTURE") and t["status"] == "SUCCESS")
        self.gql("mutation($i:RefundInput!){refundCreate(input:$i){refund{id} userErrors{field message}}}",
                 i={"orderId": self.gid("Order", oid), "note": "Lookout refund after seller approval",
                    "transactions": [{"orderId": self.gid("Order", oid), "parentId": parent["id"], "gateway": parent["gateway"],
                                      "kind": "REFUND", "amount": str(amount)}]})

    def create_product(self, listing):
        d = self.gql("""mutation($i:ProductSetInput!){productSet(input:$i,synchronous:true){product{id} userErrors{field message}}}""",
                     i={"title": listing["title"], "descriptionHtml": listing["body_html"], "status": "DRAFT",
                        "tags": listing.get("tags", []),
                        "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
                        "variants": [{"optionValues": [{"optionName": "Title", "name": "Default Title"}], "price": str(listing["price"])}]})
        return d["productSet"]["product"]["id"]

    def publish_product(self, pid):
        self.gql("mutation($p:ProductUpdateInput!){productUpdate(product:$p){product{id} userErrors{field message}}}",
                 p={"id": pid, "status": "ACTIVE"})

    def get_product(self, pid):
        p = self.gql("query($id:ID!){product(id:$id){id title status}}", id=pid)["product"]
        return p and {"id": p["id"], "title": p["title"], "status": p["status"].lower()}

    # Stock moves and reships need location and fulfillment setup per store; the demo store covers them.
    def move_stock(self, sku, qty, from_loc, to_loc):
        raise NotImplementedError("set up inventory locations, then map sku → inventoryItemId")

    def stock_of(self, sku):
        raise NotImplementedError

    def reship(self, oid):
        raise NotImplementedError


def make_store():
    return ShopifyStore() if config.SHOPIFY_STORE and config.SHOPIFY_TOKEN else MemoryStore()
