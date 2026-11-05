"""Settings from the environment (and a local .env file). Keys stay on the server."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_dotenv(ROOT / ".env")
env = os.environ.get

META_API_KEY = env("META_API_KEY", "")
META_BASE_URL = env("META_BASE_URL", "https://api.meta.ai/v1")
SPARK_MODEL = env("SPARK_MODEL", "muse-spark-1.3")
VOICE_MODEL = env("VOICE_MODEL", "muse-voice-transcribe-1.0")

# Glimmer is open weights: any OpenAI-compatible host (Fireworks, Together, a local Ollama).
GLIMMER_BASE_URL = env("GLIMMER_BASE_URL", "https://api.fireworks.ai/inference/v1")
GLIMMER_API_KEY = env("GLIMMER_API_KEY", "")
GLIMMER_MODEL = env("GLIMMER_MODEL", "accounts/fireworks/models/muse-glimmer-30b")

SHOPIFY_STORE = env("SHOPIFY_STORE", "")  # e.g. lookout-demo.myshopify.com
SHOPIFY_TOKEN = env("SHOPIFY_TOKEN", "")
SHOPIFY_API_VERSION = env("SHOPIFY_API_VERSION", "2026-10")

WHATSAPP_TOKEN = env("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = env("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", "")
SELLER_WHATSAPP = env("SELLER_WHATSAPP", "")  # seller's number, digits only
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", "")  # verifies X-Hub-Signature-256 on webhooks
SHOPIFY_WEBHOOK_SECRET = env("SHOPIFY_WEBHOOK_SECRET", "")  # verifies X-Shopify-Hmac-Sha256

DAILY_COST_CAP = float(env("DAILY_COST_CAP", "1.00"))

# Always-on demo shop for judges (see app/autopilot.py)
AUTOPILOT = env("AUTOPILOT", "0") == "1"
AUTOPILOT_SECONDS = float(env("AUTOPILOT_SECONDS", "150"))
SELLER_REPLY_AFTER = float(env("SELLER_REPLY_AFTER", "480"))  # seconds an approval waits before the scripted seller answers
DB_PATH = env("DB_PATH", str(ROOT / "lookout.db"))

# Spark 1.3 list prices per token (dev.meta.ai pricing, checked 2026-10-28)
PRICE_IN, PRICE_OUT = 1.25e-6, 4.25e-6
VOICE_PRICE_PER_HOUR = 0.18
