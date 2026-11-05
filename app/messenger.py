"""Messages to the seller: WhatsApp Cloud API when configured, always mirrored to the web phone."""
import httpx

from . import config

GRAPH = "https://graph.facebook.com/v21.0"


class Messenger:
    def __init__(self, ledger):
        self.ledger = ledger
        self.live = bool(config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_ID and config.SELLER_WHATSAPP)

    def send(self, text, action_id=None, buttons=None):
        """buttons: [(reply_id, title)], max 3 (WhatsApp limit)."""
        self.ledger.say("out", text, action_id)
        if not self.live:
            return
        body = {"messaging_product": "whatsapp", "to": config.SELLER_WHATSAPP}
        if buttons:
            body |= {"type": "interactive", "interactive": {"type": "button", "body": {"text": text[:1024]},
                     "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}} for i, t in buttons[:3]]}}}
        else:
            body |= {"type": "text", "text": {"body": text[:4096]}}
        r = httpx.post(f"{GRAPH}/{config.WHATSAPP_PHONE_ID}/messages", json=body, timeout=20,
                       headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"})
        # Outside WhatsApp's 24h window only approved templates go through; keep the web mirror and record why.
        if r.status_code >= 400:
            self.ledger.log("executor", "whatsapp_error", r.text[:300])

    def download_media(self, media_id) -> bytes:
        h = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}
        url = httpx.get(f"{GRAPH}/{media_id}", headers=h, timeout=20).json()["url"]
        return httpx.get(url, headers=h, timeout=60).content
