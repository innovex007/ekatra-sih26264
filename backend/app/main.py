import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from . import ask as ask_mod
from . import reports as rep
from .config import CATEGORIES, EVAL_RESULTS, REGIONS, STATUSES, rules
from .db import get_session, init_db
from .embedder import method_name
from . import insights
from .hashing import now
from .models import AuditEvent, Bureau, Case, CaseAction, Cluster, Institution, InterlockEvent, Meta, Overlap, Unlink
from .overlaps import RANK, rebuild_overlaps
from .resolver import get_resolver, invalidate
from .serialize import Lookups, case_out, cluster_summary, inst_brief, status_counts, timeline_out, transfer_chain
from .sla import effective_status, sla_info
from .workflow import Ctx, apply_action, audit, blockers_for, interlock_mode, interlock_message, log_action, run_action, verify_audit, verify_case_chain

app = FastAPI(title="Ekatra API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"], allow_methods=["*"], allow_headers=["*"])
init_db()


@app.on_event("startup")
def _warm():  # load the embedding model in the background so the first resolve/ask is fast
    import threading

    def go():
        from .db import session_scope
        with session_scope() as s:
            try:
                get_resolver(s)
            except Exception:  # noqa: BLE001 - empty DB before first seed
                pass
    threading.Thread(target=go, daemon=True).start()


def get_ctx(request: Request, session: Session = Depends(get_session)) -> Ctx:
    return Ctx(session, request.headers.get("x-role", "PGRC officer"))


# ------------------------------------------------------------------ meta
@app.get("/health")
def health():
    return {"status": "ok", "service": "ekatra", "data": "synthetic"}


@app.get("/meta")
def meta(session: Session = Depends(get_session)):
    sd = session.get(Meta, "seed_date")
    return {"bureaus": [{"id": b.id, "name": b.name} for b in session.exec(select(Bureau)).all()], "regions": REGIONS,
            "categories": CATEGORIES, "statuses": STATUSES, "interlock_mode": interlock_mode(session),
            "resolver_method": method_name(), "seed_date": sd.value if sd else None, "min_reason_chars": rules()["interlock"]["min_reason_chars"],
            "finding_topics": rules()["contradiction"]["topics"], "finding_verdicts": rules()["contradiction"]["verdicts"]}


class SettingsIn(BaseModel):
    interlock_mode: Literal["block", "warn"]


@app.put("/settings")
def set_settings(body: SettingsIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    session.merge(Meta(key="interlock_mode", value=body.interlock_mode))
    audit(session, ctx, "settings.interlock_mode", "settings", {"mode": body.interlock_mode})
    session.commit()
    return {"interlock_mode": body.interlock_mode}


# ------------------------------------------------------------------ dashboard
def deadline_cases(L: Lookups):
    cfg = rules()["sla"]
    out = []
    for c in L.cases:
        if c.status == "Disposed":
            continue
        s = sla_info(c, L.today, L.backlog)
        if s["level"] == "risk":
            out.append((c, s))
    out.sort(key=lambda x: x[1]["days_left"])
    return out


@app.get("/dashboard/summary")
def dashboard_summary(session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    sc = status_counts(L)
    clusters = cluster_summary(session, L)
    eff = {c.id: effective_status(c, L.today) for c in L.cases}
    by_bureau = []
    for b in L.bureau.values():
        cs = [c for c in L.cases if c.bureau_id == b.id and eff[c.id] != "Disposed"]
        by_bureau.append({"bureau": b.name, "open": len(cs), "overdue": sum(eff[c.id] == "Beyond timeline" for c in cs)})
    ageing = Counter()
    region = Counter()
    for c in L.cases:
        if eff[c.id] == "Disposed":
            continue
        a = (L.today - c.received_date).days
        ageing["0–7" if a <= 7 else "8–14" if a <= 14 else "15–21" if a <= 21 else ">21"] += 1
        if c.institution_id:
            region[L.inst[c.institution_id].region] += 1
    attention = []
    for cl in [x for x in clusters if x["severity"] == "CONFLICTING"][:4]:
        attention.append({"kind": "conflict", "title": f"{cl['institution']['name']}", "detail": f"{cl['case_count']} linked cases across {', '.join(cl['bureaus'])}",
                          "cluster_id": cl["id"], "severity": cl["severity"]})
    for c, s in deadline_cases(L)[:4]:
        attention.append({"kind": "deadline", "title": c.id, "detail": f"{s['label']} · {s['days_left']} days left", "case_id": c.id})
    return {
        "total": len(L.cases), "pending": sc["Pending"], "under_process": sc["Under process"] + sc["Received"], "disposed": sc["Disposed"],
        "transferred": sc["Transferred"], "beyond_timeline": sc["Beyond timeline"], "open_overlaps": len(clusters),
        "conflicts_blocked": len(session.exec(select(InterlockEvent)).all()),
        "open_conflicts": sum(x["severity"] == "CONFLICTING" for x in clusters),
        "by_bureau": by_bureau, "ageing": [{"bucket": k, "count": ageing[k]} for k in ("0–7", "8–14", "15–21", ">21")],
        "regions": [{"region": r, "open": region[r]} for r in REGIONS], "needs_attention": attention,
    }


# ------------------------------------------------------------------ cases
def filter_cases(L: Lookups, f: dict):
    out = []
    q = (f.get("q") or "").lower().strip()
    for c in L.cases:
        st = effective_status(c, L.today)
        inst = L.inst.get(c.institution_id)
        if f.get("bureau") and L.bname(c.bureau_id) != f["bureau"]: continue
        if f.get("status") and st != f["status"]: continue
        if f.get("category") and c.category != f["category"]: continue
        if f.get("region") and (not inst or inst.region != f["region"]): continue
        if f.get("institution_id") and c.institution_id != f["institution_id"]: continue
        if f.get("date_from") and c.received_date < f["date_from"]: continue
        if f.get("date_to") and c.received_date > f["date_to"]: continue
        if f.get("since_days") and (L.today - c.received_date).days > f["since_days"]: continue
        if f.get("needs_confirm") and not (c.link_status == "unlinked" and c.suggested_institution_id): continue
        if q and q not in c.id.lower() and q not in c.institution_name_as_written.lower() and not (inst and (q in inst.name.lower() or q in inst.permanent_id.lower() or q in inst.acronym.lower())):
            continue
        out.append(c)
    return out


@app.get("/cases")
def list_cases(q: str = "", bureau: str = "", status: str = "", region: str = "", category: str = "", institution_id: Optional[int] = None,
               date_from: Optional[date] = None, date_to: Optional[date] = None, needs_confirm: bool = False, sort: str = "received",
               limit: int = 50, offset: int = 0, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    cs = filter_cases(L, dict(q=q, bureau=bureau, status=status, region=region, category=category, institution_id=institution_id,
                              date_from=date_from, date_to=date_to, needs_confirm=needs_confirm))
    if sort == "sla":
        cs.sort(key=lambda c: (c.status == "Disposed", (c.due_date - L.today).days if c.due_date else 999))
    else:
        cs.sort(key=lambda c: (c.received_date, c.id), reverse=True)
    return {"total": len(cs), "items": [case_out(c, L, ctx) for c in cs[offset:offset + limit]]}


class CaseIn(BaseModel):
    bureau: str
    category: str
    description: str
    institution_name_as_written: str
    source: str = "email"


@app.post("/cases")
def create_case(body: CaseIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    b = session.exec(select(Bureau).where(Bureau.name == body.bureau)).first()
    if not b:
        raise HTTPException(400, "unknown Bureau")
    nums = [int(c.id.split("/")[-1]) for c in session.exec(select(Case).where(Case.bureau_id == b.id)).all() if c.id.startswith(b.code + "/")]
    cid = f"{b.code}/2026/{(max(nums) if nums else 0) + 1:04d}"
    res = get_resolver(session).resolve(body.institution_name_as_written)
    today = date.today()
    c = Case(id=cid, bureau_id=b.id, received_date=today, source=body.source, category=body.category, description=body.description,
             institution_name_as_written=body.institution_name_as_written, status="Received", sla_days=21, due_date=today + timedelta(days=21),
             link_confidence=res["confidence"], link_why=res, complainant_token=f"web{now().timestamp():.0f}"[-12:],
             current_officer_id=ctx.officer_id, last_action="create", next_action="review")
    if res["decision"] == "auto":
        c.institution_id, c.link_status = res["institution_id"], "auto"
    elif res["decision"] == "confirm":
        c.suggested_institution_id = res["institution_id"]
    session.add(c)
    log_action(session, c, ctx, "create", "Case registered in Ekatra")
    audit(session, ctx, "case.create", cid, {"bureau": b.name})
    session.commit()
    rebuild_overlaps(session)
    return {"id": cid, "link": res["decision"], "confidence": res["confidence"]}


class ActionIn(BaseModel):
    action: Literal["remark", "transfer", "show_cause", "inspection", "dispose", "close", "escalate", "reopen"]
    remarks: str = ""
    to_bureau_id: Optional[int] = None
    finding_topic: Optional[str] = None
    finding_verdict: Optional[str] = None


def _finding(topic, verdict):
    cfg = rules()["contradiction"]
    if not topic and not verdict:
        return None
    if topic not in cfg["topics"] or verdict not in cfg["verdicts"]:
        raise HTTPException(422, "A finding needs a valid topic and verdict.")
    return (topic, verdict)


class OverrideIn(BaseModel):
    action: str
    outcome: Literal["override", "lead", "cancel"]
    reason: str = ""
    bureau_id: Optional[int] = None
    finding_topic: Optional[str] = None
    finding_verdict: Optional[str] = None


def _case_or_404(session, case_id: str) -> Case:
    c = session.get(Case, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    return c


def _own_bureau_check(c: Case, ctx: Ctx, action: str):
    if ctx.level != "Senior management" and c.bureau_id != ctx.bureau_id and action != "remark":
        raise HTTPException(403, f"This case is with another Bureau; switch role to act on it (viewing as {ctx.role}).")


@app.post("/cases/{case_id:path}/actions/override")
def override_action(case_id: str, body: OverrideIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    c = _case_or_404(session, case_id)
    _own_bureau_check(c, ctx, body.action)
    bl = blockers_for(session, c, ctx)
    ids = [b["case_id"] for b in bl]
    min_chars = rules()["interlock"]["min_reason_chars"]
    if body.outcome == "cancel":
        session.add(InterlockEvent(case_id=c.id, attempted_action=body.action, blocking_case_ids=ids, outcome="cancelled", reason=body.reason, actor=ctx.actor, ts=now()))
        audit(session, ctx, "interlock.cancelled", c.id, {"action": body.action, "blockers": ids})
        session.commit()
        return {"outcome": "cancelled"}
    if body.outcome == "lead":
        b = session.get(Bureau, body.bureau_id) if body.bureau_id else None
        if not b or not bl:
            raise HTTPException(400, "Lead Bureau and an active cluster are required")
        cl = session.get(Cluster, bl[0]["cluster_id"])
        cl.lead_bureau_id, cl.status = b.id, "coordinated"
        session.add(cl)
        log_action(session, c, ctx, "remark", f"Coordination: {b.name} assigned Lead Bureau for linked cases {', '.join(ids)}. {body.action} deferred. {body.reason}".strip())
        session.add(InterlockEvent(case_id=c.id, attempted_action=body.action, blocking_case_ids=ids, outcome="lead_assigned",
                                   reason=f"Lead Bureau: {b.name}. {body.reason}".strip(), actor=ctx.actor, ts=now()))
        audit(session, ctx, "interlock.lead_assigned", c.id, {"action": body.action, "lead": b.name, "cluster": cl.id, "blockers": ids})
        session.commit()
        return {"outcome": "lead_assigned", "lead_bureau": b.name, "cluster_id": cl.id}
    if len(body.reason.strip()) < min_chars:
        raise HTTPException(422, f"A reason of at least {min_chars} characters is required to continue.")
    apply_action(session, c, ctx, body.action, f"[Override of interlock] {body.reason.strip()}", finding=_finding(body.finding_topic, body.finding_verdict))
    audit(session, ctx, f"case.{body.action}", c.id, {"remarks": "via interlock override", "reason": body.reason.strip()})
    session.add(InterlockEvent(case_id=c.id, attempted_action=body.action, blocking_case_ids=ids, outcome="override_with_reason",
                               reason=body.reason.strip(), actor=ctx.actor, ts=now()))
    audit(session, ctx, "interlock.override", c.id, {"action": body.action, "reason": body.reason.strip(), "blockers": ids})
    session.commit()
    rebuild_overlaps(session)
    return {"outcome": "override_with_reason"}


@app.post("/cases/{case_id:path}/actions")
def post_action(case_id: str, body: ActionIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    c = _case_or_404(session, case_id)
    _own_bureau_check(c, ctx, body.action)
    try:
        state, payload = run_action(session, c, ctx, body.action, body.remarks, body.to_bureau_id, _finding(body.finding_topic, body.finding_verdict))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if state == "blocked":
        raise HTTPException(409, payload)
    return {"ok": True, "status": c.status}


class ConfirmIn(BaseModel):
    institution_id: int


@app.post("/cases/{case_id:path}/confirm-link")
def confirm_link(case_id: str, body: ConfirmIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    c = _case_or_404(session, case_id)
    inst = session.get(Institution, body.institution_id)
    if not inst:
        raise HTTPException(404, "institution not found")
    c.institution_id, c.link_status, c.suggested_institution_id = inst.id, "confirmed", None
    learned = False
    txt = c.institution_name_as_written.strip()
    if txt and txt.lower() not in {a.lower() for a in [inst.name] + list(inst.aliases)}:
        inst.aliases = list(inst.aliases) + [txt]
        session.add(inst)
        learned = True
    session.add(c)
    audit(session, ctx, "link.confirm", c.id, {"institution": inst.name, "alias_learned": txt if learned else None})
    session.commit()
    invalidate()
    rebuild_overlaps(session)
    return {"ok": True, "alias_learned": learned}


@app.get("/cases/{case_id:path}")
def get_case(case_id: str, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    c = _case_or_404(session, case_id)
    L = Lookups(session)
    out = case_out(c, L, ctx)
    out["description"] = c.description
    out["timeline"] = timeline_out(session, c.id)
    out["chain_intact"] = verify_case_chain(session, c.id)
    out["why_linked"] = c.link_why
    linked = []
    for o in L.overlaps:
        if c.id in (o.case_a, o.case_b):
            other = L.by_id[o.case_b if o.case_a == c.id else o.case_a]
            linked.append({**case_out(other, L, ctx), "link_severity": o.severity, "link_reason": o.reason, "issue_similarity": o.issue_similarity})
    linked.sort(key=lambda x: -RANK[x["link_severity"]])
    out["linked_cases"] = linked
    if c.institution_id:
        ids = {x["id"] for x in linked}
        info = [case_out(x, L, ctx) for x in L.cases if x.institution_id == c.institution_id and x.id != c.id and x.status != "Disposed" and x.id not in ids]
        out["info_cases"] = info[:6]
    else:
        out["info_cases"] = []
    cl = session.get(Cluster, out["cluster_id"]) if out["cluster_id"] else None
    out["cluster"] = {"id": cl.id, "severity": cl.severity, "lead_bureau": L.bname(cl.lead_bureau_id) if cl.lead_bureau_id else None, "status": cl.status} if cl else None
    out["transfer_chain"] = transfer_chain(session, c.id) if c.transfer_count else []
    out["interlock_mode"] = interlock_mode(session)
    return out


# ------------------------------------------------------------------ institutions
@app.get("/institutions")
def list_institutions(q: str = "", session: Session = Depends(get_session)):
    L = Lookups(session)
    openc, bur = Counter(), defaultdict(set)
    for c in L.cases:
        if c.institution_id and c.status != "Disposed":
            openc[c.institution_id] += 1
            bur[c.institution_id].add(c.bureau_id)
    conf = {L.by_id[o.case_a].institution_id for o in L.overlaps if o.severity == "CONFLICTING"}
    ql = q.lower().strip()
    out = []
    for i in L.inst.values():
        if ql and ql not in i.name.lower() and ql not in i.permanent_id.lower() and ql not in i.city.lower() and not any(ql in a.lower() for a in i.aliases):
            continue
        out.append({**inst_brief(i), "acronym": i.acronym, "open_cases": openc[i.id], "bureaus": len(bur[i.id]), "has_conflict": i.id in conf})
    out.sort(key=lambda x: (-x["has_conflict"], -x["open_cases"]))
    return out


def institution_360(session, inst_id: int, ctx):
    L = Lookups(session)
    inst = L.inst.get(inst_id)
    if not inst:
        raise HTTPException(404, "institution not found")
    cs = [c for c in L.cases if c.institution_id == inst_id]
    open_cs = [c for c in cs if c.status != "Disposed"]
    ids = {c.id for c in cs}
    acts = session.exec(select(CaseAction).where(CaseAction.case_id.in_(ids))).all() if ids else []
    acts.sort(key=lambda a: a.ts)
    clusters = [x for x in cluster_summary(session, L) if x["institution"]["id"] == inst_id]
    ob = Counter(L.bname(c.bureau_id) for c in open_cs)
    return L, inst, cs, open_cs, acts, clusters, ob


@app.get("/institutions/{inst_id}")
def get_institution(inst_id: int, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L, inst, cs, open_cs, acts, clusters, ob = institution_360(session, inst_id, ctx)
    cs.sort(key=lambda c: c.received_date, reverse=True)
    return {
        "institution": {**inst_brief(inst), "aliases": inst.aliases, "acronym": inst.acronym, "type": inst.type, "district": inst.district, "pincode": inst.pincode},
        "stats": {"total": len(cs), "open": len(open_cs), "bureaus": len(ob), "conflicts": sum(x["severity"] == "CONFLICTING" for x in clusters),
                  "overdue": sum(effective_status(c, L.today) == "Beyond timeline" for c in cs)},
        "open_by_bureau": [{"bureau": k, "count": v} for k, v in ob.most_common()], "clusters": clusters,
        "systemic": next((x for x in insights.systemic(L) if x["institution"]["id"] == inst_id), None),
        "contradictions": [x for x in insights.contradictions(L) if x["institution"]["id"] == inst_id],
        "cases": [case_out(c, L, ctx) for c in cs[:80]],
        "timeline": [{"ts": a.ts.isoformat(), "case_id": a.case_id, "bureau": a.bureau, "action": a.action, "remarks": a.remarks, "actor": a.actor} for a in acts[-120:]],
    }


@app.get("/institutions/{inst_id}/brief.pdf")
def institution_brief(inst_id: int, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L, inst, cs, open_cs, acts, clusters, ob = institution_360(session, inst_id, ctx)
    ov = [o for o in L.overlaps if L.by_id[o.case_a].institution_id == inst_id]
    risk = [(c, s) for c, s in deadline_cases(L) if c.institution_id == inst_id]
    conflicts = [o for o in ov if o.severity == "CONFLICTING"]
    if conflicts:
        o = conflicts[0]
        nxt = f"Convene a coordination call between Bureaus and assign a Lead Bureau before {o.case_a} or {o.case_b} is disposed. Reason: {o.reason}."
    elif risk:
        nxt = f"Prioritise {risk[0][0].id}: {risk[0][1]['days_left']} day(s) left to deadline."
    elif ov:
        nxt = "Review linked cases and consider a joint reply to the complainants."
    else:
        nxt = "No cross-Bureau overlap detected; continue routine monitoring."
    sections = [
        ("Institution profile", ["Field", "Value"], [["Name", inst.name], ["Permanent ID", inst.permanent_id], ["Location", f"{inst.city}, {inst.state} {inst.pincode}"],
                                                    ["Region", inst.region], ["Known aliases", " | ".join(a for a in inst.aliases if a.isascii())],
                                                    ["Cases (open / total)", f"{len(open_cs)} / {len(cs)}"], ["Bureaus involved", ", ".join(ob) or "—"]]),
        ("Open cases across Bureaus", ["Case", "Bureau", "Category", "Received", "Status", "SLA"],
         [[c.id, L.bname(c.bureau_id), c.category, c.received_date, effective_status(c, L.today), sla_info(c, L.today, L.backlog)["label"]] for c in open_cs[:25]]),
        ("Conflicts and overlaps", ["Case A", "Case B", "Severity", "Reason"], [[o.case_a, o.case_b, o.severity, o.reason[:90]] for o in ov] or [["—", "—", "—", "None detected"]]),
        ("Recent timeline", ["Date", "Case", "Bureau", "Action", "Remarks"], [[a.ts.date(), a.case_id, a.bureau, a.action, a.remarks[:70]] for a in acts[-12:]]),
        ("Suggested next step", ["Recommendation"], [[nxt]]),
    ]
    pdf = rep.to_pdf(f"Institution Brief – {inst.name}", sections)
    audit(session, ctx, "report.institution_brief", str(inst_id), {})
    session.commit()
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="brief-{inst.permanent_id}.pdf"'})


class ResolveIn(BaseModel):
    text: str


@app.post("/resolve")
def resolve(body: ResolveIn, session: Session = Depends(get_session)):
    return get_resolver(session).resolve(body.text)


# ------------------------------------------------------------------ overlaps & clusters
@app.get("/overlaps")
def list_overlaps(severity: str = "", session: Session = Depends(get_session)):
    q = select(Overlap)
    if severity:
        q = q.where(Overlap.severity == severity)
    return [o.model_dump(mode="json") for o in session.exec(q).all()]


@app.get("/clusters")
def list_clusters(severity: str = "", session: Session = Depends(get_session)):
    L = Lookups(session)
    cl = cluster_summary(session, L)
    return [c for c in cl if not severity or c["severity"] == severity]


@app.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: int, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    cl = session.get(Cluster, cluster_id)
    summ = next((c for c in cluster_summary(session, L) if c["id"] == cluster_id), None)
    if not cl or not summ:
        raise HTTPException(404, "cluster not found")
    cases = []
    for cid in summ["case_ids"]:
        c = L.by_id[cid]
        o = case_out(c, L, ctx)
        o["issue"] = c.description
        o["why_linked"] = session.get(Case, cid).link_why
        cases.append(o)
    pairs = [{"a": o.case_a, "b": o.case_b, "severity": o.severity, "reason": o.reason, "similarity": o.issue_similarity}
             for o in L.overlaps if o.cluster_id == cluster_id]
    pairs.sort(key=lambda p: -RANK[p["severity"]])
    inst_cases = [case_out(x, L, ctx) for x in L.cases if x.institution_id == cl.institution_id and x.status != "Disposed" and x.id not in set(summ["case_ids"])]
    return {**summ, "institution_full": {**inst_brief(L.inst[cl.institution_id]), "aliases": L.inst[cl.institution_id].aliases, "pincode": L.inst[cl.institution_id].pincode},
            "cases": cases, "pairs": pairs, "info_cases": inst_cases[:6], "joint_reply_text": cl.joint_reply_text}


class LeadIn(BaseModel):
    bureau_id: int


@app.post("/clusters/{cluster_id}/lead")
def set_lead(cluster_id: int, body: LeadIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    cl, b = session.get(Cluster, cluster_id), session.get(Bureau, body.bureau_id)
    if not cl or not b:
        raise HTTPException(404, "not found")
    cl.lead_bureau_id, cl.status = b.id, "coordinated"
    session.add(cl)
    audit(session, ctx, "cluster.lead_assigned", f"cluster:{cl.id}", {"lead": b.name})
    session.commit()
    return {"ok": True, "lead_bureau": b.name}


class UnlinkIn(BaseModel):
    case_a: str
    case_b: str
    reason: str


@app.post("/clusters/{cluster_id}/unlink")
def unlink(cluster_id: int, body: UnlinkIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    if len(body.reason.strip()) < rules()["interlock"]["min_reason_chars"]:
        raise HTTPException(422, "A reason is required to unlink cases.")
    session.add(Unlink(case_a=body.case_a, case_b=body.case_b, reason=body.reason.strip(), actor=ctx.actor, ts=now()))
    audit(session, ctx, "overlap.unlink", f"{body.case_a} ~ {body.case_b}", {"reason": body.reason.strip()})
    session.commit()
    rebuild_overlaps(session)
    return {"ok": True}


@app.post("/clusters/{cluster_id}/joint-reply")
def joint_reply(cluster_id: int, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    cl = session.get(Cluster, cluster_id)
    summ = next((c for c in cluster_summary(session, L) if c["id"] == cluster_id), None)
    if not cl or not summ:
        raise HTTPException(404, "cluster not found")
    inst = L.inst[cl.institution_id]
    lead = L.bname(cl.lead_bureau_id) if cl.lead_bureau_id else "the Lead Bureau (to be assigned)"
    lines = [f"Subject: Joint reply – complaints concerning {inst.name} ({inst.permanent_id}), {inst.city}", "",
             "Sir/Madam,", "", f"AICTE has received the following related complaints concerning the above institution, handled by {', '.join(summ['bureaus'])}:"]
    for cid in summ["case_ids"]:
        c = L.by_id[cid]
        lines.append(f"  • {c.id} ({L.bname(c.bureau_id)}) – {c.category}: {c.description[:110]}")
    lines += ["", f"To avoid inconsistent action, these matters are being examined together under {lead}. "
              "The institution is requested to furnish a single consolidated reply within 15 days. Further action will follow on receipt.",
              "", "[Draft prepared by Ekatra – for officer review; not sent]"]
    cl.joint_reply_text = "\n".join(lines)
    session.add(cl)
    audit(session, ctx, "cluster.joint_reply_drafted", f"cluster:{cl.id}", {})
    session.commit()
    return {"text": cl.joint_reply_text}


# ------------------------------------------------------------------ watchlist, ask, alerts
@app.get("/watchlist")
def watchlist(sort: str = "trend", session: Session = Depends(get_session)):
    L = Lookups(session)
    dna = insights.risk_dna(L)
    w = rules()["watchlist"]["weights"]
    rows = {}
    for c in L.cases:
        if not c.institution_id:
            continue
        r = rows.setdefault(c.institution_id, {"open": 0, "bureaus": set(), "overdue": 0, "cats": Counter(), "cases": 0})
        r["cases"] += 1
        r["cats"][c.category] += 1
        if c.status != "Disposed":
            r["open"] += 1
            r["bureaus"].add(c.bureau_id)
            r["overdue"] += effective_status(c, L.today) == "Beyond timeline"
    for r in rows.values():
        r["repeat"] = sum(v - 1 for v in r["cats"].values() if v > 1)
    mx = {k: max((len(r[k]) if k == "bureaus" else r[k]) for r in rows.values()) or 1 for k in ("open", "bureaus", "overdue", "repeat")}
    out = []
    for iid, r in rows.items():
        parts = {"open": r["open"] / mx["open"], "bureaus": len(r["bureaus"]) / mx["bureaus"], "overdue": r["overdue"] / mx["overdue"], "repeat": r["repeat"] / mx["repeat"]}
        out.append({"institution": inst_brief(L.inst[iid]), "score": round(100 * sum(w[k] * parts[k] for k in parts), 1),
                    "raw": {"open": r["open"], "bureaus": len(r["bureaus"]), "overdue": r["overdue"], "repeat": r["repeat"]},
                    "parts": {k: round(v * w[k] * 100, 1) for k, v in parts.items()},
                    "dna": dna.get(iid, {"trend": "stable", "monthly": [0] * 6, "repeat_categories": 0, "unresolved_ratio": 0.0, "conflicts": 0})})
    if sort == "score":
        out.sort(key=lambda x: -x["score"])
    else:  # worsening first, then by score
        out.sort(key=lambda x: (insights.TREND_RANK[x["dna"]["trend"]], -x["score"]))
    return out[:40]


class AskIn(BaseModel):
    query: str


@app.post("/ask")
def ask(body: AskIn, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    f = ask_mod.parse(body.query, get_resolver(session))
    intent = f.pop("intent", None)
    ff = {k: v for k, v in f.items() if k in ("bureau", "status", "region", "category", "institution_id", "since_days")}
    cs = filter_cases(L, ff)
    if intent in ("conflicts", "duplicates", "overlaps"):
        want = {"conflicts": {"CONFLICTING"}, "duplicates": {"DUPLICATE"}, "overlaps": {"CONFLICTING", "DUPLICATE", "RELATED"}}[intent]
        ids = {cid for o in L.overlaps if o.severity in want for cid in (o.case_a, o.case_b)}
        cs = [c for c in cs if c.id in ids]
    elif intent == "pingpong":
        cs = [c for c in cs if c.transfer_count >= rules()["sla"]["pingpong_transfers"]]
    cs.sort(key=lambda c: c.received_date, reverse=True)
    chips = [{"label": k.replace("_", " "), "value": (f.get("institution_name") if k == "institution_id" else v)} for k, v in f.items() if k != "institution_name"]
    if intent:
        chips.insert(0, {"label": "intent", "value": intent})
    return {"query": body.query, "chips": chips, "total": len(cs), "items": [case_out(c, L, ctx) for c in cs[:50]]}


@app.get("/alerts")
def alerts(type: str = "conflicts", session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    cfg = rules()["sla"]
    def ov_items(sev):
        items = []
        for o in L.overlaps:
            if o.severity == sev:
                a, b = L.by_id[o.case_a], L.by_id[o.case_b]
                items.append({"cluster_id": o.cluster_id, "institution": inst_brief(L.inst.get(a.institution_id)), "case_a": case_out(a, L, ctx), "case_b": case_out(b, L, ctx),
                              "reason": o.reason, "similarity": o.issue_similarity})
        return items
    conflicts, dups = ov_items("CONFLICTING"), ov_items("DUPLICATE")
    dl = [{"case": case_out(c, L, ctx), "days_left": s["days_left"], "risk": s["risk"], "label": s["label"]} for c, s in deadline_cases(L)]
    pp = [{"case": case_out(c, L, ctx), "chain": transfer_chain(session, c.id)} for c in L.cases if c.transfer_count >= cfg["pingpong_transfers"] and c.status != "Disposed"]
    pp.sort(key=lambda x: -x["case"]["transfer_count"])
    sysm, contra = insights.systemic(L), insights.contradictions(L)
    data = {"conflicts": conflicts, "deadline": dl, "pingpong": pp, "duplicates": dups, "systemic": sysm, "contradictions": contra}
    return {"type": type, "items": data.get(type, []), "counts": {k: len(v) for k, v in data.items()}}


# ------------------------------------------------------------------ reports
@app.get("/reports/{kind}")
def report(kind: str, format: str = "json", session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    kinds = list(rep.TYPES) if kind == "monthly-pack" else [kind]
    if any(k not in rep.TYPES for k in kinds):
        raise HTTPException(404, "unknown report")
    built = [(rep.TYPES[k], *rep.build(k, L)) for k in kinds]
    if format == "csv":
        header, rows = built[0][1], built[0][2]
        return Response(rep.to_csv(header, rows), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ekatra-{kind}.csv"'})
    if format == "pdf":
        audit(session, ctx, "report.export", kind, {})
        session.commit()
        title = "Ekatra – Monthly pack" if kind == "monthly-pack" else f"Ekatra – {rep.TYPES[kind]} report"
        return Response(rep.to_pdf(title, built), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="ekatra-{kind}.pdf"'})
    return {"kind": kind, "title": rep.TYPES.get(kind, "Monthly pack"), "header": built[0][1], "rows": [[str(x) for x in r] for r in built[0][2]]}


# ------------------------------------------------------------------ audit & eval & search
@app.get("/audit")
def audit_log(limit: int = 100, offset: int = 0, session: Session = Depends(get_session)):
    total = len(session.exec(select(AuditEvent.id)).all())
    rows = session.exec(select(AuditEvent).order_by(AuditEvent.id.desc()).offset(offset).limit(limit)).all()
    return {"total": total, "items": [{"id": e.id, "ts": e.ts.isoformat(), "actor": e.actor, "role": e.role, "action": e.action, "entity": e.entity,
                                      "payload": json.loads(e.payload_json), "hash": e.hash[:12], "prev_hash": e.prev_hash[:12]} for e in rows]}


@app.post("/audit/verify")
def audit_verify(session: Session = Depends(get_session)):
    return verify_audit(session)


@app.get("/interlock/events")
def interlock_events(session: Session = Depends(get_session)):
    return [e.model_dump(mode="json") for e in session.exec(select(InterlockEvent).order_by(InterlockEvent.id.desc())).all()]


@app.post("/admin/reload")
def admin_reload():
    invalidate()
    return {"ok": True}


@app.get("/eval/results")
def eval_results():
    if not EVAL_RESULTS.exists():
        return {"available": False}
    return {"available": True, **json.loads(EVAL_RESULTS.read_text(encoding="utf8"))}


@app.get("/search")
def search(q: str, session: Session = Depends(get_session), ctx: Ctx = Depends(get_ctx)):
    L = Lookups(session)
    cs = filter_cases(L, {"q": q})[:6]
    return {"cases": [case_out(c, L, ctx) for c in cs], "institutions": list_institutions(q, session)[:5]}
