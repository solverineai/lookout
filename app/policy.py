"""Policy gate. Declarative rules; every tool call passes through here before it touches a store."""
import re

MONEY = {"refund", "reship", "compensate", "change_price"}
HEALTH = re.compile(r"효능|치료|면역|질병|약효|다이어트 효과|\bcure|\btreats?\b|immun|heals?\b|clinically", re.I)


def gate(action: str, args: dict) -> tuple[str, str]:
    """Return (decision, rule): auto, approval or blocked."""
    text = " ".join(str(v) for v in args.values())
    if HEALTH.search(text):
        return "blocked", "health or efficacy wording"
    if action in MONEY:
        return "approval", "money leaves the store"
    if action == "publish_product":
        return "approval", "listing goes public"
    return "auto", "playbook action, logged"
