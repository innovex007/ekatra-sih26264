"""H2 – overlap severity engine + clusters (union-find)."""
from collections import defaultdict
from datetime import datetime
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sqlmodel import Session, select

from .config import rules
from .models import Case, Cluster, Overlap, Unlink

RANK = {"CONFLICTING": 3, "DUPLICATE": 2, "RELATED": 1, "INFO": 0}


class PairClassifier:
    def __init__(self, cases):
        self.idx = {c.id: i for i, c in enumerate(cases)}
        self.cfg = rules()["overlap"]
        vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self.X = vec.fit_transform([c.description for c in cases])

    def cosine(self, a, b) -> float:
        return float(self.X[self.idx[a.id]].multiply(self.X[self.idx[b.id]]).sum())

    def similarity(self, a, b) -> float:
        c = self.cfg
        return c["category_weight"] * (a.category == b.category) + c["text_weight"] * self.cosine(a, b)

    def classify(self, a, b):
        """Returns (severity, reason, issue_similarity)."""
        c = self.cfg
        sim = self.similarity(a, b)

        def pending(x): return x.next_action in c["pending_disposal_actions"]
        def enforcing(x): return x.last_action in c["enforcement_actions"] and x.status != "Disposed"

        if a.bureau_id != b.bureau_id and sim >= c["conflicting_min"] and (
                (pending(a) and enforcing(b)) or (pending(b) and enforcing(a))):
            p, e = (a, b) if pending(a) and enforcing(b) else (b, a)
            return "CONFLICTING", f"{p.id} is pending disposal while {e.id} has active enforcement ({e.last_action.replace('_', '-')}) on a similar issue", sim
        if a.complainant_token and a.complainant_token == b.complainant_token:
            return "DUPLICATE", "Same complainant raised a similar matter", sim
        if sim >= c["duplicate_min"]:
            return "DUPLICATE", f"Near-identical issue text (similarity {sim:.2f})", sim
        if sim >= c["related_min"]:
            return "RELATED", f"Related issue at the same institution (similarity {sim:.2f})", sim
        return "INFO", "Same institution, unrelated issue", sim


class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def open_linked(session: Session):
    return [c for c in session.exec(select(Case)).all() if c.status != "Disposed" and c.institution_id]


def rebuild_overlaps(session: Session) -> dict:
    all_cases = session.exec(select(Case)).all()
    clf = PairClassifier(all_cases)
    old = session.exec(select(Overlap)).all()
    old_pair = {(o.case_a, o.case_b): o for o in old}
    case_old_cluster = {}
    for o in old:
        case_old_cluster[o.case_a] = o.cluster_id
        case_old_cluster[o.case_b] = o.cluster_id
    unlinked = {tuple(sorted((u.case_a, u.case_b))) for u in session.exec(select(Unlink)).all()}

    by_inst = defaultdict(list)
    for c in all_cases:
        if c.status != "Disposed" and c.institution_id and c.link_status in ("auto", "confirmed"):
            by_inst[c.institution_id].append(c)

    now = datetime.now().replace(microsecond=0)
    pairs, uf = [], UF()
    for inst_id, cs in by_inst.items():
        for a, b in combinations(sorted(cs, key=lambda x: x.id), 2):
            if tuple(sorted((a.id, b.id))) in unlinked:
                continue
            sev, reason, sim = clf.classify(a, b)
            if sev == "INFO":
                continue
            if a.bureau_id == b.bureau_id and sev != "DUPLICATE":
                continue  # same-Bureau pairs only matter as duplicates
            pairs.append((inst_id, a, b, sev, reason, sim))
            uf.union(a.id, b.id)

    comps = defaultdict(set)
    for _, a, b, *_ in pairs:
        comps[uf.find(a.id)].update((a.id, b.id))
    clusters_old = {c.id: c for c in session.exec(select(Cluster)).all()}
    comp_cluster, used = {}, set()
    inst_of = {c.id: c.institution_id for c in all_cases}
    sev_of = defaultdict(lambda: "RELATED")
    for _, a, b, sev, *_ in pairs:
        r = uf.find(a.id)
        if RANK[sev] > RANK[sev_of[r]] or r not in sev_of:
            sev_of[r] = sev
    for root, members in comps.items():
        cand = sorted({case_old_cluster[m] for m in members if case_old_cluster.get(m) in clusters_old and case_old_cluster[m] not in used and case_old_cluster[m] is not None})
        inst_id = inst_of[next(iter(members))]
        if cand:
            cl = clusters_old[cand[0]]
            cl.institution_id, cl.severity = inst_id, sev_of[root]
        else:
            cl = Cluster(institution_id=inst_id, severity=sev_of[root])
        session.add(cl)
        session.flush()
        used.add(cl.id)
        comp_cluster[root] = cl.id
    for cid, cl in clusters_old.items():
        if cid not in used:
            session.delete(cl)
    for o in old:
        session.delete(o)
    session.flush()
    for inst_id, a, b, sev, reason, sim in pairs:
        prev = old_pair.get((a.id, b.id))
        session.add(Overlap(case_a=a.id, case_b=b.id, severity=sev, reason=reason, issue_similarity=round(sim, 3),
                            created_at=prev.created_at if prev else now, resolved_by=prev.resolved_by if prev else None,
                            cluster_id=comp_cluster[uf.find(a.id)]))
    session.commit()
    return {"pairs": len(pairs), "clusters": len(comps)}
