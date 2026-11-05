"""Meta model calls. Every call is cost-capped and written to the ledger with tokens, cost and latency."""
import io
import json
import subprocess
import time

import httpx
from openai import OpenAI

from . import config


class CostCapReached(RuntimeError):
    pass


class Models:
    def __init__(self, ledger):
        self.ledger = ledger
        self.spark_client = OpenAI(api_key=config.META_API_KEY or "missing", base_url=config.META_BASE_URL)
        self.glimmer_client = (OpenAI(api_key=config.GLIMMER_API_KEY, base_url=config.GLIMMER_BASE_URL)
                               if config.GLIMMER_API_KEY else None)

    def _check_cap(self):
        if self.ledger.spent_today() >= config.DAILY_COST_CAP:
            self.ledger.log("policy", "cost_cap", f"daily model cap ${config.DAILY_COST_CAP:.2f} reached; call skipped")
            raise CostCapReached()

    # ---- Muse Spark 1.3 through the Responses API
    def spark(self, kind, input, *, tools=None, schema=None, instructions=None, previous_response_id=None, ref=""):
        self._check_cap()
        kw = dict(model=config.SPARK_MODEL, input=input)
        if tools:
            kw.update(tools=tools, parallel_tool_calls=False)
        if schema:
            kw["text"] = {"format": {"type": "json_schema", "name": schema["title"], "schema": schema, "strict": True}}
        if instructions:
            kw["instructions"] = instructions
        if previous_response_id:
            kw["previous_response_id"] = previous_response_id
        t0 = time.time()
        r = self.spark_client.responses.create(**kw)
        ms = int((time.time() - t0) * 1000)
        u = r.usage
        tin, tout = (u.input_tokens, u.output_tokens) if u else (0, 0)
        cost = tin * config.PRICE_IN + tout * config.PRICE_OUT
        self.ledger.log("spark", kind, f"{config.SPARK_MODEL} · {r.id}", ref, tin, tout, cost, ms)
        return r

    def spark_json(self, kind, input, schema, **kw) -> dict:
        r = self.spark(kind, input, schema=schema, **kw)
        return json.loads(r.output_text)

    # ---- Muse Glimmer (open weights) for always-on triage; falls back to Spark when no host is configured
    def glimmer_json(self, kind, system, user, ref="") -> dict:
        if not self.glimmer_client:
            out = self.spark_json(kind, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                                  TRIAGE_SCHEMA, ref=ref)
            self.ledger.log("policy", "fallback", "Glimmer host not configured; triage ran on Spark", ref)
            return out
        t0 = time.time()
        r = self.glimmer_client.chat.completions.create(
            model=config.GLIMMER_MODEL, temperature=1.0, top_p=0.95,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        ms = int((time.time() - t0) * 1000)
        u = r.usage
        self.ledger.log("glimmer", kind, f"{config.GLIMMER_MODEL} (open weights)", ref,
                        u.prompt_tokens if u else 0, u.completion_tokens if u else 0, 0.0, ms)
        return _loose_json(r.choices[0].message.content)

    # ---- Muse Voice Transcribe
    def transcribe(self, audio: bytes, ref="") -> str:
        """Audio in any ffmpeg-readable format (WhatsApp sends OGG/Opus) -> text."""
        self._check_cap()
        wav = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", "-f", "wav", "pipe:1"],
                             input=audio, capture_output=True, check=True).stdout
        seconds = max(0, (len(wav) - 44) / 32000)
        t0 = time.time()
        # shortcut: field names follow a secondary write-up of the batch endpoint; confirm on the first real call
        r = httpx.post(f"{config.META_BASE_URL}/asr/transcribe", timeout=60,
                       headers={"Authorization": f"Bearer {config.META_API_KEY}"},
                       data={"model": config.VOICE_MODEL, "language": "ko"},
                       files={"file": ("voice.wav", io.BytesIO(wav), "audio/wav")})
        r.raise_for_status()
        body = r.json()
        text = body.get("text") or " ".join(s.get("text", "") for s in body.get("segments", []))
        cost = seconds / 3600 * config.VOICE_PRICE_PER_HOUR
        self.ledger.log("voice", "transcribe", f"{seconds:.1f}s → “{text}”", ref, cost=cost, ms=int((time.time() - t0) * 1000))
        return text.strip()


TRIAGE_SCHEMA = {
    "title": "Triage", "type": "object", "additionalProperties": False,
    "required": ["verdict", "type", "reason"],
    "properties": {
        "verdict": {"type": "string", "enum": ["normal", "exception"]},
        "type": {"type": "string", "enum": ["none", "address", "stock", "delay", "cancel", "other"]},
        "reason": {"type": "string"},
    },
}


def _loose_json(text: str) -> dict:
    """Glimmer may wrap JSON in prose; take the outermost object."""
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1])
