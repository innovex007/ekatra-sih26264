"""Compares Ekatra's output against data/answer_key.json and writes eval/results.json.
Usage (repo root):  backend\\.venv\\Scripts\\python.exe eval\\evaluate.py"""
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.embedder import method_name  # noqa: E402
from app.main import app  # noqa: E402
from app import insights  # noqa: E402
from app.models import Case, Meta, Overlap  # noqa: E402
from app.overlaps import PairClassifier  # noqa: E402
from app.serialize import Lookups  # noqa: E402
from app.workflow import blockers_for  # noqa: E402

key = json.loads((ROOT / "data" / "answer_key.json").read_text(encoding="utf8"))
truth = key["cases"]
legacy = {i for i, v in truth.items() if not v.get("v2")}   # the original 2,000 cases: legacy metrics stay comparable
s = Session(engine)
cases = {c.id: c for c in s.exec(select(Case)).all()}
overlaps = s.exec(select(Overlap)).all()


def pct(x): return round(100 * x, 1)


# ---- 1. resolver ----------------------------------------------------------
def resolver_stats(ids):
    auto = [i for i in ids if cases[i].link_status == "auto"]
    correct = [i for i in auto if cases[i].institution_id == truth[i]["institution_id"]]
    top1 = [i for i in ids if (cases[i].institution_id or cases[i].suggested_institution_id) == truth[i]["institution_id"]]
    return {"n": len(ids), "auto_linked": len(auto), "correct_auto": len(correct),
            "precision": pct(len(correct) / len(auto)) if auto else None, "recall": pct(len(correct) / len(ids)) if ids else None,
            "needs_confirmation": sum(1 for i in ids if cases[i].link_status == "unlinked" and cases[i].suggested_institution_id),
            "top1_with_confirmation": pct(len(top1) / len(ids)) if ids else None}


all_ids = [i for i in truth if i in legacy]
legacy_insts = {truth[i]["institution_id"] for i in legacy}
subsets = {"all": all_ids, "clean": [i for i in all_ids if not truth[i]["messy"]], "messy": [i for i in all_ids if truth[i]["messy"]],
           "hindi": [i for i in all_ids if truth[i]["hindi"]]}
resolver = {k: resolver_stats(v) for k, v in subsets.items()}
wrong_auto = sum(1 for i in all_ids if cases[i].link_status == "auto" and cases[i].institution_id != truth[i]["institution_id"])
false_links = round(1000 * wrong_auto / len(all_ids), 1)

# ---- 2. overlaps found vs exact-ID matching --------------------------------
open_ids = [i for i in all_ids if cases[i].status != "Disposed"]
by_true = defaultdict(list)
for i in open_ids:
    by_true[truth[i]["institution_id"]].append(i)
true_pairs = ekatra = exact = 0
for ids in by_true.values():
    for a, b in combinations(ids, 2):
        if cases[a].bureau_id == cases[b].bureau_id:
            continue
        true_pairs += 1
        ti = truth[a]["institution_id"]
        ekatra += cases[a].institution_id == ti and cases[b].institution_id == ti
        exact += truth[a]["pid_in_text"] == "correct" and truth[b]["pid_in_text"] == "correct"
mult = round(ekatra / exact, 1) if exact else None

# ---- 3. severity on planted pairs -----------------------------------------
clf = PairClassifier(list(cases.values()))
ov_lookup = {tuple(sorted((o.case_a, o.case_b))): o.severity for o in overlaps}
labels = ["CONFLICTING", "DUPLICATE", "RELATED", "INFO"]
conf_cls, conf_e2e = defaultdict(Counter), defaultdict(Counter)
ok_cls = ok_e2e = 0
mism = []
for p in key["planted_pairs"]:
    a, b = cases[p["a"]], cases[p["b"]]
    pred, _, _ = clf.classify(a, b)
    conf_cls[p["label"]][pred] += 1
    ok_cls += pred == p["label"]
    if not pred == p["label"]:
        mism.append((p["a"], p["b"], p["label"], pred, round(clf.similarity(a, b), 2)))
    ti = truth[p["a"]]["institution_id"]
    if a.institution_id == ti and b.institution_id == ti:
        e2e = ov_lookup.get(tuple(sorted((a.id, b.id))), "INFO")
    else:
        e2e = "MISSED"
    conf_e2e[p["label"]][e2e] += 1
    ok_e2e += e2e == p["label"]
n_pairs = len(key["planted_pairs"])

# ---- 4. conflicts blocked --------------------------------------------------
class FakeCtx:  # the acting officer belongs to the case's own Bureau
    def __init__(self, bureau_id): self.bureau_id = bureau_id


attempts = key["conflict_attempts"]
blocked = sum(1 for t in attempts if blockers_for(s, cases[t["case_id"]], FakeCtx(cases[t["case_id"]].bureau_id)))
planted_ids = {x for p in key["planted_pairs"] for x in (p["a"], p["b"])}
in_overlap = {cid for o in overlaps for cid in (o.case_a, o.case_b)}
controls = [c for c in cases.values() if c.id in legacy and c.status != "Disposed" and c.id not in planted_ids and c.id not in in_overlap][:200]
false_triggers = sum(1 for c in controls if blockers_for(s, c, FakeCtx(c.bureau_id)))


# ---- 6. v2 detectors --------------------------------------------------------
L = Lookups(s)
flagged = {x["institution"]["id"]: x for x in insights.systemic(L)}
sy_planted = key["systemic"]["planted"]
sy_decoys = [d["institution_id"] for d in key["systemic"]["decoys"]]
sy_found = sum(i in flagged for i in sy_planted)
sy_decoy_flag = sum(i in flagged for i in sy_decoys)
sy_other = [i for i in flagged if i not in sy_planted and i not in sy_decoys]
sy_miss_unlinked = sum(1 for i in sy_planted if i not in flagged and any(cases[c].institution_id != i for c, v in truth.items() if v["institution_id"] == i))

co = insights.contradictions(L)
co_keys = {(x["institution"]["id"], x["topic"]) for x in co}
co_pl = {(p["institution_id"], p["topic"]): p for p in key["contradictions"]["planted"]}
co_ct = {(p["institution_id"], p["topic"]): p for p in key["contradictions"]["controls"]}
co_found = sum(k in co_keys for k in co_pl)
co_missed = [p for k, p in co_pl.items() if k not in co_keys]
co_miss_unlinked = sum(1 for p in co_missed if any(cases[c].institution_id != p["institution_id"] for c in p["cases"]))
co_ctl_flag = {kind: sum(1 for k, p in co_ct.items() if p["kind"] == kind and k in co_keys) for kind in ("same_verdict", "far_apart", "same_bureau")}
co_ctl_n = {kind: sum(1 for p in co_ct.values() if p["kind"] == kind) for kind in co_ctl_flag}
co_other = len(co_keys - set(co_pl) - set(co_ct))

dna = insights.risk_dna(L)
dna_ok = {r: sum(1 for i in ids if dna.get(i, {}).get("trend") == r) for r, ids in key["riskdna"].items()}
dna_n = {r: len(ids) for r, ids in key["riskdna"].items()}
bg_trend = dict(Counter(v["trend"] for i, v in dna.items() if legacy_insts.__contains__(i)))

# ---- 5. latency ------------------------------------------------------------
client = TestClient(app)
client.get("/dashboard/summary")


def p95(path, n=60):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        r = client.get(path)
        assert r.status_code == 200
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return round(xs[int(0.95 * n) - 1], 1), round(statistics.median(xs), 1)


dash_p95, dash_med = p95("/dashboard/summary")
cases_p95, _ = p95("/cases?limit=50")
svit = key["demo"]["institution"]
i360_p95, i360_med = p95(f"/institutions/{svit}", 30)

res = {
    "generated": datetime.now().isoformat(timespec="seconds"), "seed": key["seed"],
    "resolver_method": method_name(), "resolver_method_at_seed": (s.get(Meta, "resolver_method").value if s.get(Meta, "resolver_method") else None),
    "dataset": {"cases": len(all_ids), "institutions": len({t["institution_id"] for t in truth.values()}), "planted_pairs": n_pairs},
    "resolver": resolver, "false_links_per_1000": false_links, "wrong_auto_links": wrong_auto,
    "overlaps": {"true_cross_bureau_pairs": true_pairs, "ekatra_found": ekatra, "exact_id_found": exact, "multiplier": mult,
                 "ekatra_recall": pct(ekatra / true_pairs), "exact_id_recall": pct(exact / true_pairs)},
    "severity": {"pairs": n_pairs, "classifier_accuracy": pct(ok_cls / n_pairs), "end_to_end_accuracy": pct(ok_e2e / n_pairs),
                 "confusion_classifier": {k: dict(v) for k, v in conf_cls.items()}, "confusion_end_to_end": {k: dict(v) for k, v in conf_e2e.items()},
                 "labels": labels + ["MISSED"]},
    "interlock": {"attempts": len(attempts), "blocked": blocked, "control_cases": len(controls), "false_triggers": false_triggers},
    "v2": {
        "cases_added": len(truth) - len(legacy), "institutions_added": len({truth[i]["institution_id"] for i in truth if i not in legacy}),
        "systemic": {"planted": len(sy_planted), "found": sy_found, "decoys": len(sy_decoys), "decoys_flagged": sy_decoy_flag,
                     "other_institutions_flagged": len(sy_other), "total_flagged": len(flagged), "institutions_scored": len({c.institution_id for c in cases.values() if c.institution_id})},
        "contradictions": {"planted": len(co_pl), "found": co_found, "missed_due_to_unlinked_case": co_miss_unlinked, "controls": len(co_ct),
                           "controls_flagged": sum(co_ctl_flag.values()), "controls_by_kind": {k: f"{co_ctl_flag[k]}/{co_ctl_n[k]}" for k in co_ctl_flag},
                           "other_flagged": co_other, "total_flagged": len(co)},
        "riskdna": {"correct": dna_ok, "planted": dna_n, "background_trend_mix": bg_trend},
    },
    "latency": {"dashboard_p95_ms": dash_p95, "dashboard_median_ms": dash_med, "cases_p95_ms": cases_p95, "n_cases": len(cases)},
    "institution_360": {"api_p95_ms": i360_p95, "api_median_ms": i360_med, "manual_baseline": "to be measured with a stopwatch (open 4 Bureau systems + spreadsheet)"},
}
(ROOT / "eval").mkdir(exist_ok=True)
(ROOT / "eval" / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf8")

print(f"\nEKATRA EVALUATION  ({res['resolver_method']} · {res['dataset']['cases']} synthetic cases)\n" + "=" * 70)
print(f"{'Resolver (auto-link)':<26}{'n':>6}{'precision':>12}{'recall':>10}{'confirm-queue':>15}")
for k in ("all", "clean", "messy", "hindi"):
    r = resolver[k]
    print(f"  {k:<24}{r['n']:>6}{str(r['precision']) + '%':>12}{str(r['recall']) + '%':>10}{r['needs_confirmation']:>15}")
print(f"False links (auto-linked to wrong institution): {wrong_auto}  = {false_links} per 1,000 cases")
print(f"Overlaps: Ekatra finds {ekatra} of {true_pairs} true cross-Bureau pairs; exact Permanent-ID matching finds {exact}  ->  {mult}x more")
print(f"Severity on {n_pairs} planted pairs: classifier {res['severity']['classifier_accuracy']}% · end-to-end (incl. linking) {res['severity']['end_to_end_accuracy']}%")
print("  confusion (end-to-end)  true -> predicted:", {k: dict(v) for k, v in conf_e2e.items()})
if mism:
    print("  classifier mismatches:", mism[:6])
print(f"Conflicts blocked: {blocked} / {len(attempts)} planted conflicting actions; false triggers on {len(controls)} control cases: {false_triggers}")
print(f"Dashboard API p95: {dash_p95} ms (median {dash_med}) · cases list p95: {cases_p95} ms · Institution 360 API: median {i360_med} ms")

v = res["v2"]
print("\nv2 DETECTORS (new planted institutions/cases are excluded from the legacy numbers above)")
print(f"  Systemic:       found {v['systemic']['found']}/{v['systemic']['planted']} planted · decoys flagged {v['systemic']['decoys_flagged']}/{v['systemic']['decoys']} · "
      f"{v['systemic']['other_institutions_flagged']} other institutions also meet the rule (of {v['systemic']['institutions_scored']})")
print(f"  Contradictions: found {v['contradictions']['found']}/{v['contradictions']['planted']} planted ({v['contradictions']['missed_due_to_unlinked_case']} of the misses had a case not auto-linked) · "
      f"controls flagged {v['contradictions']['controls_flagged']}/{v['contradictions']['controls']} {v['contradictions']['controls_by_kind']} · unplanted flagged {v['contradictions']['other_flagged']}")
print(f"  Risk DNA:       worsening {dna_ok['worsening']}/{dna_n['worsening']} · improving {dna_ok['improving']}/{dna_n['improving']} · stable {dna_ok['stable']}/{dna_n['stable']} · background mix {bg_trend}")
