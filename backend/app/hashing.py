import hashlib
import json
from datetime import datetime

GENESIS = "0" * 64


def _h(prev: str, payload: dict) -> str:
    return hashlib.sha256((prev + json.dumps(payload, sort_keys=True, default=str)).encode()).hexdigest()


def action_hash(prev: str, a) -> str:
    p = {"case": a.case_id, "ts": a.ts.isoformat(), "actor": a.actor, "bureau": a.bureau,
         "action": a.action, "remarks": a.remarks, "docs": a.documents}
    if getattr(a, "finding_topic", None):  # findings are part of the tamper-evident record
        p["finding"] = [a.finding_topic, a.finding_verdict]
    return _h(prev, p)


def audit_hash(prev: str, e) -> str:
    return _h(prev, {"ts": e.ts.isoformat(), "actor": e.actor, "role": e.role, "action": e.action,
                     "entity": e.entity, "payload": e.payload_json})


def now() -> datetime:
    return datetime.now().replace(microsecond=0)
