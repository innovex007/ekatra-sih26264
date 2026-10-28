"""Case actions, H3 interlock, audit chain."""
import json
from datetime import date, timedelta
from typing import Optional

from sqlmodel import Session, select

from .config import rules
from .hashing import GENESIS, action_hash, audit_hash, now
from .models import AuditEvent, Bureau, Case, CaseAction, Cluster, InterlockEvent, Meta, Officer, Overlap
from .overlaps import RANK, rebuild_overlaps

ROLE_MAP = {"PGRC officer": ("PGRC", "Officer"), "RB officer": ("RB", "Officer"),
            "Bureau head": ("PGRC", "Bureau head"), "Senior management": (None, "Senior management")}


class Ctx:
    def __init__(self, session: Session, role: str):
        self.role = role if role in ROLE_MAP else "PGRC officer"
        code, self.level = ROLE_MAP[self.role]
        b = session.exec(select(Bureau).where(Bureau.name == code)).first() if code else None
        self.bureau_id = b.id if b else None
        self.bureau_name = b.name if b else "Senior management"
        q = select(Officer).where(Officer.role == self.level)
        if b:
            q = q.where(Officer.bureau_id == b.id)
        o = session.exec(q).first()
        self.officer_id = o.id if o else None
        self.actor = o.name if o else self.role


def interlock_mode(session: Session) -> str:
    m = session.get(Meta, "interlock_mode")
    return m.value if m else rules()["interlock"]["mode"]


def audit(session: Session, ctx: Ctx, action: str, entity: str, payload: dict):
    last = session.exec(select(AuditEvent).order_by(AuditEvent.id.desc())).first()
    ev = AuditEvent(ts=now(), actor=ctx.actor, role=ctx.role, action=action, entity=entity,
                    payload_json=json.dumps(payload, sort_keys=True, default=str), prev_hash=last.hash if last else GENESIS)
    ev.hash = audit_hash(ev.prev_hash, ev)
    session.add(ev)


def log_action(session: Session, case: Case, ctx: Ctx, action: str, remarks: str = "", docs=None, finding=None) -> CaseAction:
    last = session.exec(select(CaseAction).where(CaseAction.case_id == case.id).order_by(CaseAction.id.desc())).first()
    a = CaseAction(case_id=case.id, ts=now(), actor=ctx.actor, bureau=ctx.bureau_name, action=action,
                   remarks=remarks, documents=docs or [], prev_hash=last.hash if last else GENESIS,
                   finding_topic=finding[0] if finding else None, finding_verdict=finding[1] if finding else None)
    a.hash = action_hash(a.prev_hash, a)
    session.add(a)
    return a


def blockers_for(session: Session, case: Case, ctx: Ctx) -> list:
    """Linked open cases with CONFLICTING/DUPLICATE severity, unless the actor's Bureau is the cluster's Lead."""
    cfg = rules()["interlock"]
    ovs = session.exec(select(Overlap).where((Overlap.case_a == case.id) | (Overlap.case_b == case.id))).all()
    ovs = [o for o in ovs if o.severity in cfg["blocking_severities"]]
    if not ovs:
        return []
    cl = session.get(Cluster, ovs[0].cluster_id)
    if cl and cl.lead_bureau_id and cl.lead_bureau_id == ctx.bureau_id:
        return []
    out = []
    for o in sorted(ovs, key=lambda o: -RANK[o.severity]):
        other = session.get(Case, o.case_b if o.case_a == case.id else o.case_a)
        if other and other.status != "Disposed":
            b = session.get(Bureau, other.bureau_id)
            out.append({"case_id": other.id, "bureau": b.name if b else "", "severity": o.severity,
                        "last_action": other.last_action, "status": other.status, "reason": o.reason,
                        "cluster_id": o.cluster_id})
    return out


def interlock_message(case: Case, blockers: list) -> str:
    b = blockers[0]
    what = f" ({b['last_action'].replace('_', '-')} issued)" if b["last_action"] in rules()["overlap"]["enforcement_actions"] else ""
    return (f"⛔ Action paused – linked case active. {b['case_id']} is acting on a related issue at this institution{what}. "
            f"Coordinate first, assign a Lead Bureau, or record a reason to continue.")


def apply_action(session: Session, case: Case, ctx: Ctx, action: str, remarks: str = "", to_bureau_id: Optional[int] = None, finding=None):
    today = date.today()
    if action == "transfer":
        tb = session.get(Bureau, to_bureau_id) if to_bureau_id else None
        if not tb:
            raise ValueError("transfer needs a target Bureau")
        remarks = f"Transferred {ctx.bureau_name if case.bureau_id == ctx.bureau_id else session.get(Bureau, case.bureau_id).name} → {tb.name}. {remarks}".strip()
        case.bureau_id, case.status, case.transfer_count = tb.id, "Transferred", case.transfer_count + 1
        case.next_action = "review"
    elif action in ("show_cause", "inspection"):
        case.status, case.next_action = "Under process", "reply"
    elif action in ("dispose", "close"):
        case.status, case.next_action = "Disposed", ""
    elif action == "reopen":
        case.status, case.next_action = "Under process", "review"
    elif action == "escalate":
        case.status = "Under process"
    case.last_action = "dispose" if action == "close" else action
    if case.status != "Disposed" and case.due_date and today > case.due_date:
        pass  # effective status is computed on read
    log_action(session, case, ctx, action, remarks, finding=finding)
    session.add(case)


def run_action(session: Session, case: Case, ctx: Ctx, action: str, remarks: str = "", to_bureau_id=None, finding=None):
    """Returns ('ok', None) or ('blocked', payload)."""
    cfg = rules()["interlock"]
    if action in cfg["guarded_actions"]:
        bl = blockers_for(session, case, ctx)
        if bl:
            mode = interlock_mode(session)
            msg = interlock_message(case, bl)
            if mode == "block":
                return "blocked", {"detail": "interlock", "message": msg, "blockers": bl, "mode": mode,
                                   "case_id": case.id, "action": action,
                                   "cluster_id": bl[0]["cluster_id"]}
            session.add(InterlockEvent(case_id=case.id, attempted_action=action, blocking_case_ids=[b["case_id"] for b in bl],
                                       outcome="warned", reason="warn-only (pilot) mode", actor=ctx.actor, ts=now()))
            audit(session, ctx, "interlock.warned", case.id, {"action": action, "blockers": [b["case_id"] for b in bl]})
    apply_action(session, case, ctx, action, remarks, to_bureau_id, finding)
    audit(session, ctx, f"case.{action}", case.id, {"remarks": remarks, **({"finding": list(finding)} if finding else {})})
    session.commit()
    rebuild_overlaps(session)
    return "ok", None


def verify_audit(session: Session) -> dict:
    prev, n = GENESIS, 0
    for e in session.exec(select(AuditEvent).order_by(AuditEvent.id)).all():
        n += 1
        if e.prev_hash != prev or e.hash != audit_hash(prev, e):
            return {"intact": False, "events": n, "broken_at": e.id}
        prev = e.hash
    return {"intact": True, "events": n, "broken_at": None}


def verify_case_chain(session: Session, case_id: str) -> bool:
    prev = GENESIS
    for a in session.exec(select(CaseAction).where(CaseAction.case_id == case_id).order_by(CaseAction.id)).all():
        if a.prev_hash != prev or a.hash != action_hash(prev, a):
            return False
        prev = a.hash
    return True
