import os
from collections import Counter, defaultdict
from datetime import date
from types import SimpleNamespace

from sqlalchemy import event
from sqlmodel import Session, select

from .config import DATABASE_URL
from .models import Bureau, Case, CaseAction, Cluster, Institution, Officer, Overlap
from .overlaps import RANK
from .sla import backlog_by_bureau, effective_status, sla_info


_VERSION = [0]
_SNAP = {"key": None, "data": None}


@event.listens_for(Session, "after_commit")
def _bump(_session):
    _VERSION[0] += 1


def _db_mtime() -> int:
    if DATABASE_URL.startswith("sqlite"):
        try:
            return os.stat(DATABASE_URL.replace("sqlite:///", "")).st_mtime_ns
        except OSError:
            return 0
    return 0


def _rows(session, model, skip=(), where=None):
    cols = [c for c in model.__table__.c if c.name not in skip]
    q = select(*cols)
    if where is not None:
        q = q.where(where)
    return [SimpleNamespace(**r) for r in session.execute(q).mappings().all()]


class Lookups:
    """Per-request view over a cached, ORM-free snapshot of the tables (rebuilt after any commit)."""

    def __init__(self, session: Session):
        self.today = date.today()
        key = (_VERSION[0], _db_mtime(), self.today)
        if _SNAP["key"] != key:
            d = SimpleNamespace()
            d.inst = {i.id: i for i in _rows(session, Institution)}
            d.bureau = {b.id: b for b in _rows(session, Bureau)}
            d.officer = {o.id: o for o in _rows(session, Officer)}
            d.cases = _rows(session, Case, skip=("link_why",))
            d.by_id = {c.id: c for c in d.cases}
            d.backlog = backlog_by_bureau(d.cases)
            d.overlaps = _rows(session, Overlap)
            d.findings = _rows(session, CaseAction, skip=("documents", "prev_hash", "hash"), where=CaseAction.finding_topic.is_not(None))
            d.clusters = {c.id: c for c in _rows(session, Cluster)}
            d.sev, d.cluster_of = {}, {}
            for o in d.overlaps:
                for cid in (o.case_a, o.case_b):
                    if RANK[o.severity] > RANK.get(d.sev.get(cid), -1):
                        d.sev[cid] = o.severity
                    d.cluster_of[cid] = o.cluster_id
            _SNAP["key"], _SNAP["data"] = key, d
        self.__dict__.update(_SNAP["data"].__dict__)

    def bname(self, bid): return self.bureau[bid].name if bid in self.bureau else ""


def inst_brief(i: Institution | None):
    return None if not i else {"id": i.id, "name": i.name, "permanent_id": i.permanent_id, "city": i.city, "state": i.state, "region": i.region}


def case_out(c: Case, L: Lookups, ctx) -> dict:
    s = sla_info(c, L.today, L.backlog)
    sug = L.inst.get(c.suggested_institution_id) if c.suggested_institution_id else None
    visible = ctx.level == "Senior management" or c.bureau_id == ctx.bureau_id
    off = L.officer.get(c.current_officer_id)
    return {
        "id": c.id, "bureau": L.bname(c.bureau_id), "bureau_id": c.bureau_id, "category": c.category,
        "received_date": c.received_date.isoformat(), "due_date": c.due_date.isoformat() if c.due_date else None,
        "source": c.source, "status": effective_status(c, L.today), "stored_status": c.status,
        "institution": inst_brief(L.inst.get(c.institution_id)), "written": c.institution_name_as_written,
        "link": {"status": c.link_status, "confidence": c.link_confidence,
                 "suggested": inst_brief(sug) if c.link_status == "unlinked" else None},
        "officer": off.name if off else "", "last_action": c.last_action, "next_action": c.next_action,
        "sla": s, "transfer_count": c.transfer_count, "severity": L.sev.get(c.id),
        "cluster_id": L.cluster_of.get(c.id),
        "complainant": f"Ref {c.complainant_token[:8]}" if visible else "Hidden (other Bureau)",
        "complainant_visible": visible,
    }


def timeline_out(session: Session, case_id: str) -> list:
    return [{"id": a.id, "ts": a.ts.isoformat(), "actor": a.actor, "bureau": a.bureau, "action": a.action,
             "remarks": a.remarks, "hash": a.hash[:12], "prev_hash": a.prev_hash[:12],
             "finding": {"topic": a.finding_topic, "verdict": a.finding_verdict} if a.finding_topic else None}
            for a in session.exec(select(CaseAction).where(CaseAction.case_id == case_id).order_by(CaseAction.id)).all()]


def transfer_chain(session: Session, case_id: str) -> list:
    return [{"ts": a.ts.isoformat(), "from": a.bureau, "remarks": a.remarks}
            for a in session.exec(select(CaseAction).where(CaseAction.case_id == case_id, CaseAction.action == "transfer").order_by(CaseAction.id)).all()]


def cluster_summary(session: Session, L: Lookups) -> list:
    from .models import Cluster
    members = defaultdict(set)
    for o in L.overlaps:
        members[o.cluster_id].update((o.case_a, o.case_b))
    out = []
    for cl in session.exec(select(Cluster)).all():
        ids = sorted(members.get(cl.id, []))
        if not ids:
            continue
        inst = L.inst.get(cl.institution_id)
        out.append({"id": cl.id, "institution": inst_brief(inst), "severity": cl.severity, "case_count": len(ids),
                    "case_ids": ids, "latest": max(L.by_id[i].received_date for i in ids).isoformat(), "bureaus": sorted({L.bname(L.by_id[i].bureau_id) for i in ids}),
                    "lead_bureau": L.bname(cl.lead_bureau_id) if cl.lead_bureau_id else None, "status": cl.status})
    out.sort(key=lambda x: (x["latest"], x["case_count"]), reverse=True)
    out.sort(key=lambda x: -RANK[x["severity"]])  # stable: severity first, then most recent activity
    return out


def status_counts(L: Lookups) -> Counter:
    return Counter(effective_status(c, L.today) for c in L.cases)
