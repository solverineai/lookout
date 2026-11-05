# Setup: keys, accounts and hosting

Everything below needs James's own accounts. Put every value in `.env` (git-ignored). Steps marked "check" follow the providers' docs but were not tried in this build.

## 1. Meta Model API (required)
1. dev.meta.ai → API keys → create a key.
2. `.env`: `META_API_KEY=...`
3. Check: `.venv/bin/uvicorn app.main:app --port 8000`, open http://localhost:8000, press Break one → No unit number. The Log should show `spark` rows with tokens and cost.

Free credits are active on the account ($150). Set a spend alert on the Billing page. While free credits are in use, Meta may use the content to improve products, so send only synthetic data.

## 2. Muse Glimmer host (optional, for the open-weights path)
Without it, triage runs on Spark and the Log says so.
1. Fireworks (account exists) → API key. Check that `accounts/fireworks/models/muse-glimmer-30b` is listed.
2. `.env`: `GLIMMER_API_KEY=...` (and `GLIMMER_MODEL` if the id differs).

## 3. Shopify dev store (for real store writes in the video)
1. partners.shopify.com → create a Partner account → Stores → Add store → Development store.
2. In the store: Settings → Apps and sales channels → Develop apps → Create an app.
   Admin API scopes: `read_orders`, `write_orders`, `read_merchant_managed_fulfillment_orders`, `write_merchant_managed_fulfillment_orders`, `read_products`, `write_products`, `read_inventory`, `write_inventory`.
   Install the app and copy the Admin API access token.
3. Settings → Payments → enable the test gateway ("Bogus Gateway"). Place a few test orders from the storefront.
4. Settings → Notifications → Webhooks → `Order creation`, JSON, URL `https://<your host>/webhooks/shopify`. Copy the signing secret.
5. `.env`: `SHOPIFY_STORE=<name>.myshopify.com`, `SHOPIFY_TOKEN=...`, `SHOPIFY_WEBHOOK_SECRET=...`
6. Check: `SHOPIFY_TEST_ORDER_ID=<an unshipped test order id> .venv/bin/python -m pytest -q tests/test_shopify_live.py`

Judges never need the storefront or its password. With Shopify set, the always-on demo shop turns off; run the Shopify part for the video only.

## 4. WhatsApp Cloud API (optional, for the real phone in the video)
1. developers.facebook.com → Create app (Business) → add WhatsApp. Use the test number.
2. Add the seller's phone as a recipient and verify it.
3. Copy the temporary access token and the phone number ID. App settings → Basic → App secret.
4. Webhooks: callback URL `https://<your host>/webhooks/whatsapp`, a verify token you choose, subscribe to `messages`.
5. `.env`: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `SELLER_WHATSAPP` (digits only).
6. The seller must message the test number first: WhatsApp only allows free-form replies within 24 hours of the seller's last message.

## 5. Hosting for judges (Nov 4 to 8)
Any host that runs a Docker image behind HTTPS works (Fly.io, Render, Railway, Cloud Run). One small instance is enough.
```
docker build -t lookout . && docker run -p 8000:8000 --env-file .env -e AUTOPILOT=1 -e DAILY_COST_CAP=10 lookout
```
- `AUTOPILOT=1`: the demo shop runs by itself, a new arrival every 150 s (`AUTOPILOT_SECONDS`), and the scripted seller answers approvals after 8 minutes (`SELLER_REPLY_AFTER`).
- Keep a volume at `/data` so the log survives restarts.
- Check the cost per arrival in the Log on day one and adjust `AUTOPILOT_SECONDS` so five days stay well inside the credit.
