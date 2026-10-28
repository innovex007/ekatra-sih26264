from collections import Counter
from datetime import date, timedelta

from .config import rules


def effective_status(c, today: date) -> str:
    if c.status != "Disposed" and c.due_date and today > c.due_date:
        return "Beyond timeline"
    return c.status


def backlog_by_bureau(cases) -> Counter:
    return Counter(c.bureau_id for c in cases if c.status != "Disposed")


def sla_info(c, today: date, backlog: Counter | None = None) -> dict:
    cfg = rules()["sla"]
    due = c.due_date or (c.received_date + timedelta(days=c.sla_days))
    age = (today - c.received_date).days
    left = (due - today).days
    if c.status == "Disposed":
        return {"day": min(age, c.sla_days), "of": c.sla_days, "days_left": None, "risk": 0.0, "level": "done", "label": "Closed"}
    w = cfg["risk_weights"]
    mx = max(backlog.values()) if backlog else 1
    bl = (backlog or {}).get(c.bureau_id, 0) / mx if mx else 0
    risk = (w["age"] * min(age / c.sla_days, 1.0) + w["transfers"] * min(c.transfer_count / 3, 1.0)
            + w["backlog"] * bl + w["category"] * cfg["category_weight"].get(c.category, 0.3))
    if left < 0:
        level, label = "overdue", f"{-left}d overdue"
    elif risk >= cfg["warn_risk"] or left <= cfg["warn_days_left"]:
        level, label = "risk", f"Day {age} of {c.sla_days}"
    else:
        level, label = "ok", f"Day {age} of {c.sla_days}"
    return {"day": age, "of": c.sla_days, "days_left": left, "risk": round(min(risk, 1.0), 2), "level": level, "label": label}
