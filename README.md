# Lookout

**Grow orders, not headcount.** Lookout runs a small online store's operations overnight: it finds broken orders, fixes them, and asks the seller only about money.

- **Live:** https://lookout-363487335975.us-central1.run.app (no login; orders keep arriving on their own)
- **Demo video (3 min):** https://youtu.be/VsSGUUmOVYQ
- **Code:** https://github.com/solverineai/lookout

Built for the Meta Global AI Developer Hackathon 2026 (Startup track, Build for Your World). Everything in this repository was written during the event, Oct 27 – Nov 4, 2026. No pre-existing code.

## What it does

| | What happens | Meta model |
|---|---|---|
| **Find** | Every order, tracking scan and customer message is classified: normal, or broken (no unit number, out of stock, stalled parcel, cancel request). | Muse Spark 1.3 (the hosted demo); Muse Glimmer 30B when a Glimmer host is set |
| **Fix** | A tool loop reads the order and fixes it: hold, correct the address, move stock, cancel before shipping, tell the customer in their language. | Muse Spark 1.3, Responses API tools |
| **Ask** | Refunds, reships and publishing a product wait for the seller on WhatsApp. One tap, or a voice note. | Muse Voice Transcribe + Spark |
| **Launch** | "이거 팔아 봐" → a listing in Korean, English and Japanese, created as a draft, published after the seller's OK. | Muse Spark 1.3, structured output |

## Why it holds up

- **Policy gate** (`app/policy.py`): money and publishing need approval; health or efficacy wording is blocked.
- **One key per write** (`app/ledger.py`): a retried refund is refused, never paid twice.
- **Checked after writing** (`app/agent.py`): every write is read back from the store; anything unconfirmed is recorded as unknown and not retried blindly.
- **Run ledger**: every model call with tokens, cost and latency, every gate decision, every write.
- **Daily cost cap**: past it, model calls stop and the seller is told.
- Model output is untrusted: tool arguments are checked before anything is claimed or written; webhooks are signature-checked.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" openai httpx python-multipart pytest
cp .env.example .env   # add META_API_KEY at least
.venv/bin/uvicorn app.main:app --port 8000
```

Open http://localhost:8000, press **Run the night**, or break an order yourself. The board shows what needs your OK, what Lookout fixed and what is yours, with one order's full record (store writes, gate decisions, every Spark call with tokens, cost and time) always open beside the lists. Without Shopify or WhatsApp keys, Lookout uses a built-in demo store; the model calls are real either way.

For judges the hosted page (Cloud Run, one always-on instance) runs with `AUTOPILOT=1`: orders and customer messages keep arriving on their own, so the page is live the moment it opens, with no login and nothing to press. A scripted seller answers waiting approvals after a few minutes, and the page and log mark those replies as scripted. Lookout writes to a real Shopify store the same way (`app/store.py`); keys and hosting are in [docs/setup.md](docs/setup.md).

Tests run offline with a scripted model: `.venv/bin/python -m pytest -q`.

## Layout

```
app/main.py       web page, judge controls, Shopify and WhatsApp webhooks, one ordered job queue
app/agent.py      triage, the Spark tool loop, the executor (gate → key → write → read back)
app/boss.py       Voice Boss and Launch
app/models.py     Meta model calls with cost cap and ledger entries
app/store.py      demo store and Shopify Admin GraphQL store
app/simulator.py  a fixed night of arriving orders (arrivals are scripted; every decision is a model call)
app/autopilot.py  the always-on demo shop for judges
web/index.html    the seller's page
```
