"""v2 detectors: systemic problems, contradicting findings, institutional risk DNA.
All three read the cached Lookups snapshot and take their thresholds from ekatra_rules.yaml."""
from collections import defaultdict
from itertools import combinations

from .config import rules
from .serialize import inst_brief


def _case_line(c, L):
    return {"id": c.id, "bureau": L.bname(c.bureau_id), "category": c.category, "status": c.status,
            "received_date": c.received_date.isoformat(), "age_days": (L.today - c.received_date).days}


# ---------------------------------------------------------------- 1. systemic
def systemic(L) -> list:
    cfg = rules()["systemic"]
    win, ignore = cfg["window_days"], set(cfg["ignore_categories"])
    by_inst = defaultdict(list)
    for c in L.cases:
        if c.status == "Disposed" or not c.institution_id or c.link_status not in ("auto", "confirmed"):
            continue
        age = (L.today - c.received_date).days
        if age <= win and c.category not in ignore:
            by_inst[c.institution_id].append((c, age))
    out = []
    for iid, items in by_inst.items():
        cats = {c.category for c, _ in items}
        bureaus = {c.bureau_id for c, _ in items}
        if len(cats) < cfg["min_categories"] or len(bureaus) < cfg["min_bureaus"]:
            continue
        recency = sum(max(0.0, 1 - age / win) for _, age in items) / len(items)
        score = len(cats) * len(bureaus) * recency
        if score < cfg["min_score"]:
            continue
        span = max(age for _, age in items)
        out.append({
            "institution": inst_brief(L.inst[iid]), "score": round(score, 2), "categories": sorted(cats),
            "bureaus": sorted(L.bname(b) for b in bureaus), "span_days": span, "recency": round(recency, 2),
            "cases": [_case_line(c, L) for c, _ in sorted(items, key=lambda x: x[1])],
            "explanation": f"{len(cats)} different problems reported to {len(bureaus)} Bureaus in {span} days – may indicate the institution is not functioning as approved.",
            "suggested_action": cfg["suggested_action"],
        })
    out.sort(key=lambda x: -x["score"])
    return out


# ---------------------------------------------------------------- 2. contradictions
def contradictions(L) -> list:
    cfg = rules()["contradiction"]
    by = defaultdict(list)
    for f in L.findings:
        c = L.by_id.get(f.case_id)
        if c and c.institution_id and f.finding_verdict in ("compliant", "non-compliant"):
            by[(c.institution_id, f.finding_topic)].append((f, c))
    out = []
    for (iid, topic), items in by.items():
        for (a, ca), (b, cb) in combinations(sorted(items, key=lambda x: x[0].ts), 2):
            if a.bureau == b.bureau or a.finding_verdict == b.finding_verdict:
                continue
            gap = abs((b.ts - a.ts).days)
            if gap > cfg["window_days"]:
                continue
            lead = None
            for cid in (ca.id, cb.id):
                cl = L.clusters.get(L.cluster_of.get(cid))
                if cl and cl.lead_bureau_id:
                    lead = L.bname(cl.lead_bureau_id)
            side = lambda f, c: {"bureau": f.bureau, "actor": f.actor, "case_id": c.id, "date": f.ts.date().isoformat(),
                                 "action": f.action, "verdict": f.finding_verdict, "remarks": f.remarks}
            out.append({
                "institution": inst_brief(L.inst[iid]), "topic": topic, "severity": "high", "gap_days": gap,
                "sides": [side(a, ca), side(b, cb)],
                "explanation": f"{a.bureau} recorded “{a.finding_verdict}” and {b.bureau} recorded “{b.finding_verdict}” on {topic}, {gap} day{'' if gap == 1 else 's'} apart.",
                "suggested_action": f"Refer to the Lead Bureau ({lead})." if lead else "Refer to the Lead Bureau – none assigned yet; assign one first.",
            })
    out.sort(key=lambda x: x["sides"][1]["date"], reverse=True)
    return out


# ---------------------------------------------------------------- 3. risk DNA
TREND_RANK = {"worsening": 0, "stable": 1, "improving": 2}


def risk_dna(L) -> dict:
    cfg = rules()["riskdna"]
    n, bucket = cfg["months"], cfg["bucket_days"]
    cw = rules()["sla"]["category_weight"]
    load = defaultdict(lambda: [0.0] * n)
    count = defaultdict(lambda: [0] * n)
    stats = defaultdict(lambda: {"total": 0, "open": 0, "cats": defaultdict(int)})
    for c in L.cases:
        if not c.institution_id:
            continue
        s = stats[c.institution_id]
        s["total"] += 1
        s["open"] += c.status != "Disposed"
        age = (L.today - c.received_date).days
        if age >= n * bucket:
            continue
        m = n - 1 - age // bucket                      # 0 = oldest month, n-1 = newest
        w = cw.get(c.category, 0.3) + (cfg["conflict_bonus"] if L.sev.get(c.id) in ("CONFLICTING", "DUPLICATE") else 0)
        load[c.institution_id][m] += w
        count[c.institution_id][m] += 1
        s["cats"][c.category] += 1
    conflicts = defaultdict(int)
    for o in L.overlaps:
        if o.severity == "CONFLICTING":
            conflicts[L.by_id[o.case_a].institution_id] += 1
    half = n // 2
    out = {}
    for iid, ld in load.items():
        older, recent = sum(ld[:half]), sum(ld[half:])
        delta = recent - older
        need = max(cfg["min_delta"], cfg["ratio"] * older, cfg["noise_k"] * (older + recent) ** 0.5)
        if delta >= need:
            trend = "worsening"
        elif -delta >= need:
            trend = "improving"
        else:
            trend = "stable"
        s = stats[iid]
        out[iid] = {"trend": trend, "monthly": count[iid], "load": [round(x, 1) for x in ld],
                    "repeat_categories": sum(1 for v in s["cats"].values() if v >= 2),
                    "unresolved_ratio": round(s["open"] / s["total"], 2) if s["total"] else 0.0,
                    "conflicts": conflicts.get(iid, 0)}
    return out
