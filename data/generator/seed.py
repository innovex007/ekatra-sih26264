"""Synthetic dataset generator.  Usage:  python -m data.generator.seed --seed 42"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from sqlmodel import Session  # noqa: E402

from app import resolver as resolver_mod  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.embedder import method_name  # noqa: E402
from app.hashing import GENESIS, action_hash, audit_hash  # noqa: E402
from app.models import AuditEvent, Bureau, Case, CaseAction, Cluster, Institution, Meta, Officer, Overlap  # noqa: E402
from app.overlaps import rebuild_overlaps  # noqa: E402
from app.translit import to_devanagari  # noqa: E402
from data.generator.content import *  # noqa: E402,F403

BUREAUS = [("PGRC", "PGRC"), ("RB", "RB"), ("Approval", "APB"), ("Academic", "ACB"), ("Regional Office", "RO")]
BUREAU_W = [45, 30, 10, 8, 7]
N_CASES, N_INST = 2000, 80
STOP = {"of", "and", "the", "for"}


def acronym_of(name: str) -> str:
    return "".join(w[0] for w in name.replace(".", "").split() if w.lower() not in STOP).upper()


def mutate(word: str, rng: random.Random) -> str:
    if len(word) < 5:
        return word
    i = rng.randrange(1, len(word) - 1)
    op = rng.choice(["del", "swap", "dup", "sub"])
    if op == "del":
        return word[:i] + word[i + 1:]
    if op == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:] if i + 2 <= len(word) else word
    if op == "dup":
        return word[:i] + word[i] + word[i:]
    return word[:i] + rng.choice("aeiou") + word[i + 1:]


def mutate_name(name: str, rng: random.Random) -> str:
    ws = name.split()
    cand = [i for i, w in enumerate(ws) if len(w) >= 6]
    if cand:
        i = rng.choice(cand)
        ws[i] = mutate(ws[i], rng)
    return " ".join(ws)


# ---------------------------------------------------------------- institutions
def build_institutions(rng):
    out, used_names, used_pid = [], set(), set()

    def pid():
        while True:
            p = f"1-48{rng.randrange(10**7):07d}"
            if p not in used_pid:
                used_pid.add(p)
                return p

    def make(prefix, word, suffix_pair, city, hindi, acronym_alias=None, force_acronym=None):
        suffix, old_suffix = suffix_pair
        name = " ".join(x for x in (prefix, word, suffix) if x)
        old = " ".join(x for x in (prefix, word, old_suffix) if x)
        acr = force_acronym or acronym_of(name)
        aliases = [acr, old, mutate_name(name, rng)]
        if acronym_alias:
            aliases[0] = acronym_alias
        if hindi:
            aliases.append(to_devanagari(name))
        c = city
        typ = "Management" if "Management" in suffix else "Pharmacy" if "Pharmacy" in suffix else "Polytechnic" if suffix == "Polytechnic" else "Engineering"
        return Institution(permanent_id=pid(), name=name, aliases=aliases, acronym=acr, state=c[2], district=c[1], city=c[0],
                           pincode=c[4], region=c[3], type=typ)

    city_by = {c[0]: c for c in CITIES}
    svit = make("Shri", "Venkatadri", SUFFIXES[0], city_by["Tirupati"], True, acronym_alias="SVIT")
    svit.aliases[1] = "Shri Venkatadri Engineering College"
    svit.aliases.insert(1, "Sri Venkatadri Inst. of Tech.")
    out.append(svit)
    twin = make("Shri", "Venkateswara", SUFFIXES[0], city_by["Guntur"], False, acronym_alias="SVIT")  # same acronym, different city
    out.append(twin)
    used_names.update({svit.name, twin.name})
    hindi_pick = set(rng.sample(range(2, N_INST), 15))
    while len(out) < N_INST:
        word = rng.choice(NAME_WORDS)
        sfx = rng.choice(SUFFIXES)
        inst = make(rng.choice(PREFIXES), word, sfx, rng.choice(CITIES), len(out) in hindi_pick)
        if inst.name in used_names or inst.acronym in {i.acronym for i in out}:
            continue
        used_names.add(inst.name)
        out.append(inst)
        if len(out) < N_INST - 2 and rng.random() < 0.06:   # look-alike twin: same distinctive word, other city/suffix
            sfx2 = rng.choice([s for s in SUFFIXES if s != sfx])
            t = make(inst.name.split()[0] if inst.name.split()[0] in PREFIXES and PREFIXES.count(inst.name.split()[0]) else "", word, sfx2,
                     rng.choice([c for c in CITIES if c[0] != inst.city]), False)
            if t.name not in used_names and t.acronym not in {i.acronym for i in out}:
                used_names.add(t.name)
                out.append(t)
    return out[:N_INST]


# ---------------------------------------------------------------- name writing
def write_name(inst, kind, rng):
    city, pin = inst.city, inst.pincode
    if kind == "clean":
        t = inst.name
        if rng.random() < 0.7:
            t += f", {city}"
        if rng.random() < 0.2:
            t += f" - {pin}"
    elif kind == "acronym":
        t = inst.acronym + (f", {city}" if rng.random() < 0.8 else "") + (f" {pin}" if rng.random() < 0.25 else "")
    elif kind == "typo":
        t = mutate_name(inst.name, rng) + (f", {city}" if rng.random() < 0.6 else "")
    elif kind == "missing":
        ws = inst.name.split()
        t = " ".join(ws[1:]) if ws[0] in PREFIXES and rng.random() < 0.5 else " ".join(ws[:-2] if len(ws) > 3 else ws[:-1])
        t += f", {city}" if rng.random() < 0.6 else ""
    elif kind == "old":
        t = inst.aliases[1 if inst.name != "Shri Venkatadri Institute of Technology" else 2] + (f", {city}" if rng.random() < 0.6 else "")
    elif kind == "abbr":
        t = (inst.name.replace("Institute", "Inst.").replace("Technology", "Tech.").replace("Engineering", "Engg.")
             .replace("College", "Coll.").replace("Management", "Mgmt.")) + (f", {city}" if rng.random() < 0.5 else "")
    else:  # hindi
        d = to_devanagari(inst.name)
        if rng.random() < 0.5:
            d = d.replace("ी", "ि", 1)
        if rng.random() < 0.3:
            d = d.replace("ऑफ ", "")
        t = d + (", " + to_devanagari(city) if rng.random() < 0.6 else "")
    return t


KINDS = ["clean", "acronym", "typo", "missing", "old", "abbr", "hindi"]
KIND_W = [60, 10, 8, 6, 6, 5, 5]


def add_pid(text, inst, rng, used_pid):
    r = rng.random()
    if r < 0.35:
        return f"{text} (AICTE ID {inst.permanent_id})", "correct"
    if r < 0.40:
        while True:
            p = f"1-48{rng.randrange(10**7):07d}"
            if p not in used_pid:
                return f"{text} (AICTE ID {p})", "wrong"
    return text, "none"



# ---------------------------------------------------------------- v2 plants (own RNG: the core 2,000 cases are untouched)
V2_WORDS = ["Aranya", "Bhaskara", "Chinmaya", "Dhruva", "Eklavya", "Falguni", "Gandiva", "Himavat", "Ishan", "Jaladhara", "Kalinga", "Lohit",
            "Mandara", "Nalanda", "Omkara", "Parijat", "Rajata", "Samudra", "Taraka", "Utkarsh", "Vaishali", "Yashoda", "Zenith", "Abhaya"]
CATS6 = ["Infrastructure", "Faculty", "Fees & refund", "Ragging", "Norms violation", "Admission"]
WORSENING = [[0, 1, 1, 3, 4, 6], [1, 1, 2, 3, 5, 5], [0, 0, 2, 3, 4, 7]]
IMPROVING = [w[::-1] for w in WORSENING]
STABLE = [[2, 2, 2, 2, 2, 2], [3, 2, 2, 3, 2, 2]]
HEAVY, LIGHT = ["Ragging", "Norms violation", "Faculty", "Fees & refund"], ["Other", "Admission", "Infrastructure"]
off_by_bureau_ref = [None]


def plant_v2(seed, sess, insts, cases, actions_spec, key, key_cases, today, bid, bname, cap, taken, special, svit=None):
    from collections import defaultdict
    rng2 = random.Random(seed + 7919)
    BUR = [b[0] for b in BUREAUS]
    code_of = dict(BUREAUS)
    used_names, used_acr, used_pid = {i.name for i in insts}, {i.acronym for i in insts}, {i.permanent_id for i in insts}
    words = iter(rng2.sample(V2_WORDS, 18))

    def new_inst():
        word = next(words)
        while True:
            sfx, prefix, city = rng2.choice(SUFFIXES), rng2.choice(PREFIXES), rng2.choice(CITIES)
            name = " ".join(x for x in (prefix, word, sfx[0]) if x)
            acr = acronym_of(name)
            if name not in used_names and acr not in used_acr:
                break
        used_names.add(name)
        used_acr.add(acr)
        while True:
            pid = f"1-48{rng2.randrange(10**7):07d}"
            if pid not in used_pid:
                used_pid.add(pid)
                break
        old = " ".join(x for x in (prefix, word, sfx[1]) if x)
        return Institution(permanent_id=pid, name=name, aliases=[acr, old, mutate_name(name, rng2)], acronym=acr, state=city[2], district=city[1],
                           city=city[0], pincode=city[4], region=city[3], type="Engineering")

    roles = ["systemic"] * 5 + ["decoy_cat"] * 3 + ["decoy_bureau"] * 2 + ["worsening"] * 3 + ["improving"] * 3 + ["stable"] * 2
    v2 = [new_inst() for _ in roles]
    sess.add_all(v2)
    sess.commit()

    def mk(inst, bureau, cat, age, tag, disposed=False):
        code = code_of[bureau]
        while True:
            cid = f"{code}/2026/{rng2.randint(1, cap[code]):04d}"
            if cid not in taken:
                taken.add(cid)
                break
        kind = rng2.choices(["clean", "abbr", "typo", "acronym"], [75, 10, 10, 5])[0]
        tail = rng2.choice(TAILS).format(b=rng2.choice("ABCDEF"), n=rng2.choice([12, 25, 40, 60]), m=rng2.choice(MONTHS), d=rng2.randint(1, 28),
                                         sem=rng2.choice(SEMS), dept=rng2.choice(DEPTS), ref=rng2.randint(10000, 99999))
        desc = rng2.choice(TEMPLATES[cat]) + " " + tail
        rec = today - timedelta(days=age)
        status = "Disposed" if disposed else ("Beyond timeline" if age > 21 else rng2.choice(["Under process", "Pending"]))
        c = Case(id=cid, bureau_id=bid[bureau], received_date=rec, source=rng2.choices(SOURCES, SOURCE_W)[0], category=cat, description=desc,
                 institution_name_as_written=write_name(inst, kind, rng2), complainant_token=hashlib.sha256(f"v2-{cid}".encode()).hexdigest()[:12],
                 status=status, current_officer_id=rng2.choice(off_by_bureau_ref[0][bid[bureau]]).id, last_action="dispose" if disposed else "remark",
                 next_action="" if disposed else "review", sla_days=21, due_date=rec + timedelta(days=21))
        cases.append(c)
        key_cases[cid] = {"institution_id": inst.id, "permanent_id": inst.permanent_id, "kind": kind, "messy": kind != "clean", "hindi": False,
                          "pid_in_text": "none", "v2": True, "v2_role": tag}
        steps = [(0, bureau, "create", "Complaint received")]
        if disposed:
            steps.append((min(rng2.randint(8, 35), age), bureau, "dispose", "Disposed after reply; complainant informed"))
        actions_spec[cid] = steps
        return c

    out = {"systemic": [], "decoys": [], "worsening": [], "improving": [], "stable": []}
    patterns = {"worsening": list(WORSENING), "improving": list(IMPROVING), "stable": list(STABLE)}
    for role, inst in zip(roles, v2):
        if role == "systemic":
            cats = rng2.sample(CATS6, 4) + [rng2.choice(CATS6)]
            bs = rng2.sample(BUR, 3)
            for k, cat in enumerate(cats):
                mk(inst, bs[k % 3], cat, rng2.randint(5, 60), role)
            out["systemic"].append(inst.id)
        elif role == "decoy_cat":           # many cases, ONE category
            cat, bs = rng2.choice(CATS6), rng2.sample(BUR, 3)
            for k in range(7):
                mk(inst, bs[k % 3], cat, rng2.randint(5, 60), role)
            out["decoys"].append({"institution_id": inst.id, "kind": "one_category"})
        elif role == "decoy_bureau":        # many cases, many categories, ONE Bureau
            b = rng2.choice(BUR)
            for cat in rng2.sample(CATS6, 4) + rng2.sample(CATS6, 2):
                mk(inst, b, cat, rng2.randint(5, 60), role)
            out["decoys"].append({"institution_id": inst.id, "kind": "one_bureau"})
        else:
            pat = patterns[role].pop(0)
            for m, n in enumerate(pat):
                heavy_now = (m >= 3) if role == "worsening" else (m < 3) if role == "improving" else None
                for _ in range(n):
                    cat = rng2.choice(CATS6 + ["Other"]) if heavy_now is None else rng2.choice(HEAVY if heavy_now else LIGHT)
                    age = (5 - m) * 30 + rng2.randint(2, 27)
                    mk(inst, rng2.choice(BUR), cat, age, role, disposed=age > 60 and rng2.random() < 0.85)
            out[role].append(inst.id)
    key["systemic"] = {"planted": out["systemic"], "decoys": out["decoys"]}
    key["riskdna"] = {k: out[k] for k in ("worsening", "improving", "stable")}

    # ---- contradictions + controls, attached to EXISTING cases (adds no cases, so overlaps are unaffected)
    legacy = [c for c in cases if not key_cases[c.id].get("v2")]
    by_inst = defaultdict(list)
    for c in legacy:
        iid = key_cases[c.id]["institution_id"]
        if iid not in special:
            by_inst[iid].append(c)
    order = [i for i in by_inst if len(by_inst[i]) >= 2]
    rng2.shuffle(order)
    topics = ["lab", "faculty", "infrastructure", "fees", "safety"]
    plans = ["contradiction"] * 6 + ["same_verdict"] * 3 + ["far_apart"] * 3 + ["same_bureau"] * 2
    planted, controls = [], []

    def add_step(c, date, topic, verdict):
        age = (today - c.received_date).days
        days = max(0, min((date - c.received_date).days, age))
        actions_spec[c.id].append((days, bname[c.bureau_id], "inspection", f"Inspection finding - {topic}: {verdict}", topic, verdict))

    for plan in plans:
        for iid in list(order):
            cs = by_inst[iid]
            same_b = plan == "same_bureau"
            pairs = [(a, b) for a in cs for b in cs if a.id < b.id and ((a.bureau_id == b.bureau_id) == same_b)]
            if not pairs:
                continue
            A, B = rng2.choice(pairs)
            topic = rng2.choice(topics)
            dA = A.received_date + timedelta(days=rng2.randint(0, (today - A.received_date).days))
            g = rng2.choice([-1, 1]) * rng2.randint(75, 130) if plan == "far_apart" else rng2.randint(-40, 40)
            dB = min(today, max(B.received_date, dA + timedelta(days=g)))
            gap = abs((dB - dA).days)
            if (plan == "far_apart" and gap <= 65) or (plan != "far_apart" and gap > 55):
                continue
            va = rng2.choice(["compliant", "non-compliant"])
            vb = va if plan == "same_verdict" else ("non-compliant" if va == "compliant" else "compliant")
            add_step(A, dA, topic, va)
            add_step(B, dB, topic, vb)
            rec = {"institution_id": iid, "topic": topic, "cases": [A.id, B.id], "verdicts": [va, vb], "gap_days": gap, "kind": plan}
            (planted if plan == "contradiction" else controls).append(rec)
            order.remove(iid)
            break
    key["contradictions"] = {"planted": planted, "controls": controls}
    if svit is not None:   # demo story: SVIT also has faculty and infrastructure complaints at two more Bureaus
        mk(svit, "Academic", "Faculty", 20, "demo_svit")
        mk(svit, "Regional Office", "Infrastructure", 33, "demo_svit")
    return v2


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    t0 = time.time()
    today = date.today()
    (ROOT / "data").mkdir(exist_ok=True)
    init_db(drop=True)
    sess = Session(engine)

    # bureaus & officers
    bureaus = [Bureau(name=n, code=c) for n, c in BUREAUS]
    sess.add_all(bureaus)
    sess.commit()
    bid = {b.name: b.id for b in bureaus}
    bname = {b.id: b.name for b in bureaus}
    officers, ni = [], 0
    for b in bureaus:
        for role in ("Bureau head", "Officer", "Officer", "Officer"):
            officers.append(Officer(name=("Dr. " if role == "Bureau head" else "") + OFFICER_NAMES[ni % len(OFFICER_NAMES)], bureau_id=b.id, role=role))
            ni += 1
    officers += [Officer(name="Secretary (Synthetic)", bureau_id=0, role="Senior management"),
                 Officer(name="Joint Secretary (Synthetic)", bureau_id=0, role="Senior management")]
    sess.add_all(officers)
    sess.commit()
    off_by_bureau = {}
    for o in officers:
        off_by_bureau.setdefault(o.bureau_id, []).append(o)

    insts = build_institutions(rng)
    sess.add_all(insts)
    sess.commit()
    svit = insts[0]
    related_inst = insts[5]
    special = {svit.id, related_inst.id}
    pool = [i for i in insts if i.id not in special]
    hindi_pool = [i for i in pool if any(re.search(r"[ऀ-ॿ]", a) for a in i.aliases)]
    used_pid = {i.permanent_id for i in insts}
    iw = {i.id: rng.lognormvariate(0, 0.6) for i in pool}

    taken, cases, actions_spec, key_cases = set(), [], {}, {}
    key = {"seed": args.seed, "cases": key_cases, "planted_pairs": [], "conflict_attempts": [], "demo": {}}
    seq = {c: 0 for _, c in BUREAUS}
    code_of = {n: c for n, c in BUREAUS}
    cap = {"PGRC": 1100, "RB": 1400, "APB": 520, "ACB": 420, "RO": 380}

    def new_id(bureau, fixed=None):
        code = code_of[bureau]
        if fixed:
            taken.add(f"{code}/2026/{fixed:04d}")
            return f"{code}/2026/{fixed:04d}"
        while True:
            n = rng.randint(1, cap[code])
            cid = f"{code}/2026/{n:04d}"
            if cid not in taken:
                taken.add(cid)
                return cid

    # reserve fixed demo ids
    for b, n in [("PGRC", 457), ("RB", 1182), ("PGRC", 511), ("Approval", 213), ("PGRC", 388), ("Approval", 147),
                 ("Regional Office", 92), ("PGRC", 333), ("PGRC", 602)]:
        taken.add(f"{code_of[b]}/2026/{n:04d}")

    def make_case(cid, bureau, inst, desc, cat, written_kind=None, written=None, age=None, status="Under process",
                  last="remark", nxt="review", token=None, transfers=0, kind_override=None, pid_mode=True):
        kind = kind_override or written_kind or "clean"
        text = written if written is not None else write_name(inst, kind, rng)
        pidm = "none"
        if pid_mode and written is None:
            text, pidm = add_pid(text, inst, rng, used_pid)
        age = rng.randint(2, 60) if age is None else age
        rec = today - timedelta(days=age)
        c = Case(id=cid, bureau_id=bid[bureau], received_date=rec, source=rng.choices(SOURCES, SOURCE_W)[0], category=cat,
                 description=desc, institution_name_as_written=text, complainant_token=token or hashlib.sha256(f"{args.seed}-{cid}".encode()).hexdigest()[:12],
                 status=status, current_officer_id=rng.choice(off_by_bureau[bid[bureau]]).id, last_action=last, next_action=nxt,
                 sla_days=21, due_date=rec + timedelta(days=21), transfer_count=transfers)
        cases.append(c)
        key_cases[cid] = {"institution_id": inst.id, "permanent_id": inst.permanent_id, "kind": kind,
                          "messy": kind != "clean", "hindi": kind == "hindi", "pid_in_text": pidm}
        return c

    def hist(cid, steps):
        actions_spec[cid] = steps  # list of (days_after_receipt, bureau, action, remarks)

    # ------------------------- demo scenarios
    tok1 = hashlib.sha256(b"svit-complainant").hexdigest()[:12]
    c_ = CONFLICT_TOPICS[0]
    a = make_case("PGRC/2026/0457", "PGRC", svit, c_[1], c_[0], written="SVIT, Tirupati - 517502", age=6, status="Pending", last="remark", nxt="dispose", token=tok1)
    hist(a.id, [(0, "PGRC", "create", "Complaint received via CPGRAMS"), (2, "PGRC", "remark", "Called for institution's reply"), (5, "PGRC", "remark", "Reply found unsatisfactory; draft disposal prepared")])
    b = make_case("RB/2026/1182", "RB", svit, c_[2], c_[0], written="Sri Venkatadri Inst. of Tech.", age=9, status="Under process", last="show_cause", nxt="reply")
    hist(b.id, [(0, "RB", "create", "Reference from verification cell"), (4, "RB", "inspection", "Desk verification of laboratory records"), (8, "RB", "show_cause", "Show-cause notice issued on lab norms; reply due in 15 days")])
    d = make_case("PGRC/2026/0511", "PGRC", svit, c_[1] + " Please act urgently.", c_[0], written="श्री वेंकटाद्रि इंस्टिट्यूट ऑफ टेक्नोलॉजी, तिरुपति", age=1,
                  status="Pending", last="remark", nxt="dispose", token=tok1, kind_override="hindi")
    hist(d.id, [(0, "PGRC", "create", "Reminder received; same complainant"), (2, "PGRC", "remark", "Linked to earlier complaint, disposal being drafted")])
    e = make_case("APB/2026/0213", "Approval", svit, "Caution deposit not returned even after two years from course completion.", "Fees & refund",
                  written="Shri Venkatadri Institute of Technology, Tirupati", age=14, status="Under process")
    hist(e.id, [(0, "Approval", "create", "Fee refund grievance received"), (6, "Approval", "remark", "Forwarded to institution for reply")])
    for x, y, lab in [(a, b, "CONFLICTING"), (a, d, "DUPLICATE"), (d, b, "CONFLICTING"), (a, e, "INFO"), (b, e, "INFO"), (d, e, "INFO")]:
        key["planted_pairs"].append({"a": x.id, "b": y.id, "label": lab, "scenario": "demo-1/2/4"})
    key["conflict_attempts"].append({"case_id": a.id, "action": "dispose"})
    key["conflict_attempts"].append({"case_id": d.id, "action": "dispose"})

    rel = [("PGRC", "PGRC/2026/0388", "Hostel fee charged is higher than approved and hostel mess facilities are poor.", 388),
           ("Approval", "APB/2026/0147", "Hostel fees collected exceed the approved fee structure and hostel mess is inadequate.", 0),
           ("Regional Office", "RO/2026/0092", "Students complain of excess hostel fees collected and poor hostel mess facilities; regional inspection requested.", 0)]
    rc = []
    for br, cid, txt, _ in rel:
        c = make_case(cid, br, related_inst, txt, "Fees & refund", written_kind=rng.choice(["clean", "acronym", "abbr"]), age=rng.randint(8, 15))
        hist(cid, [(0, br, "create", "Complaint received"), (3, br, "remark", "Under examination")])
        rc.append(c)
    for i in range(3):
        for j in range(i + 1, 3):
            key["planted_pairs"].append({"a": rc[i].id, "b": rc[j].id, "label": "RELATED", "scenario": "demo-3"})

    pp_inst = rng.choice(pool)
    pp = make_case("PGRC/2026/0333", "Academic", pp_inst, "Faculty qualifications and approval status are disputed; no Bureau has taken ownership of the case.", "Faculty",
                   written_kind="clean", age=19, status="Transferred", last="transfer", nxt="review", transfers=4)
    chain = [("PGRC", "RB"), ("RB", "Approval"), ("Approval", "PGRC"), ("PGRC", "Academic")]
    steps = [(0, "PGRC", "create", "Complaint received")]
    for k, (f, t) in enumerate(chain):
        steps.append((3 + 4 * k, f, "transfer", f"Transferred {f} → {t}. Not within our remit; please examine."))
    hist(pp.id, steps)

    sla_inst = rng.choice(pool)
    sl = make_case("PGRC/2026/0602", "PGRC", sla_inst, "Teachers have not received salary for four months and no response from management.", "Faculty",
                   written_kind="clean", age=16, status="Under process")
    hist(sl.id, [(0, "PGRC", "create", "Complaint received"), (5, "PGRC", "remark", "Reply sought from institution"), (12, "PGRC", "remark", "No reply; reminder sent")])

    key["demo"] = {"conflict": [a.id, b.id], "duplicate": d.id, "related": [c.id for c in rc], "info": e.id, "pingpong": pp.id, "deadline": sl.id,
                   "institution": svit.id, "related_institution": related_inst.id}

    # ------------------------- planted statistical pairs (conflict / duplicate / related / info)
    plant_insts = rng.sample(pool, 47)
    pi = iter(plant_insts)

    def pk():
        return rng.choices(KINDS, KIND_W)[0] if True else "clean"

    def planted_kind(inst):
        k = rng.choices(KINDS[:-1], KIND_W[:-1])[0]
        return k

    for n in range(14):
        inst = next(pi)
        cat, ta, tb = CONFLICT_TOPICS[n % len(CONFLICT_TOPICS)]
        ca = make_case(new_id("PGRC"), "PGRC", inst, ta, cat, written_kind=planted_kind(inst), age=rng.randint(2, 6), status="Pending", last="remark", nxt="dispose")
        cb = make_case(new_id("RB"), "RB", inst, tb, cat, written_kind=planted_kind(inst), age=rng.randint(4, 9), status="Under process", last="show_cause", nxt="reply")
        for c, bn in ((ca, "PGRC"), (cb, "RB")):
            hist(c.id, [(0, bn, "create", "Complaint received")] + ([(2, "RB", "show_cause", "Show-cause issued")] if c is cb else [(2, "PGRC", "remark", "Disposal being drafted")]))
        key["planted_pairs"].append({"a": ca.id, "b": cb.id, "label": "CONFLICTING", "scenario": "planted"})
        key["conflict_attempts"].append({"case_id": ca.id, "action": "dispose"})
    for n in range(11):
        inst = next(pi)
        cat, ta, _ = CONFLICT_TOPICS[n % len(CONFLICT_TOPICS)]
        same_tok = n % 2 == 0
        tk = hashlib.sha256(f"dup{n}".encode()).hexdigest()[:12]
        b1, b2 = ("PGRC", rng.choice(["Approval", "Academic", "PGRC"]))
        ca = make_case(new_id(b1), b1, inst, ta, cat, written_kind=planted_kind(inst), age=rng.randint(5, 18), token=tk)
        cb = make_case(new_id(b2), b2, inst, ta + " Please act urgently.", cat, written_kind=planted_kind(inst), age=rng.randint(2, 10), token=tk if same_tok else None)
        for c, bn in ((ca, b1), (cb, b2)):
            hist(c.id, [(0, bn, "create", "Complaint received")])
        key["planted_pairs"].append({"a": ca.id, "b": cb.id, "label": "DUPLICATE", "scenario": "planted"})
    for n in range(11):
        inst = next(pi)
        cat, ta, tb = RELATED_TOPICS[n % len(RELATED_TOPICS)]
        b2 = rng.choice(["Approval", "Regional Office", "Academic"])
        ca = make_case(new_id("PGRC"), "PGRC", inst, ta, cat, written_kind=planted_kind(inst), age=rng.randint(5, 18))
        cb = make_case(new_id(b2), b2, inst, tb, cat, written_kind=planted_kind(inst), age=rng.randint(5, 18))
        for c, bn in ((ca, "PGRC"), (cb, b2)):
            hist(c.id, [(0, bn, "create", "Complaint received")])
        key["planted_pairs"].append({"a": ca.id, "b": cb.id, "label": "RELATED", "scenario": "planted"})
    for n in range(11):
        inst = next(pi)
        c1, t1, c2, t2 = INFO_TOPICS[n % len(INFO_TOPICS)]
        b2 = rng.choice(["Approval", "Academic", "RB"])
        ca = make_case(new_id("PGRC"), "PGRC", inst, t1, c1, written_kind=planted_kind(inst), age=rng.randint(5, 18))
        cb = make_case(new_id(b2), b2, inst, t2, c2, written_kind=planted_kind(inst), age=rng.randint(5, 18))
        for c, bn in ((ca, "PGRC"), (cb, b2)):
            hist(c.id, [(0, bn, "create", "Complaint received")])
        key["planted_pairs"].append({"a": ca.id, "b": cb.id, "label": "INFO", "scenario": "planted"})

    # ------------------------- random background cases
    n_random = N_CASES - len(cases)
    cats, catw = list(CATEGORY_W), list(CATEGORY_W.values())
    by_inst_cases = {}
    for _ in range(n_random):
        br = rng.choices([b[0] for b in BUREAUS], BUREAU_W)[0]
        kind = rng.choices(KINDS, KIND_W)[0]
        cand = hindi_pool if kind == "hindi" else pool
        inst = rng.choices(cand, [iw[i.id] for i in cand])[0]
        age = rng.randint(1, 180)
        prev = by_inst_cases.get(inst.id)
        if prev and rng.random() < 0.015:   # repeat complainant, same issue
            cat, desc, token = prev.category, prev.description, prev.complainant_token
        else:
            cat = rng.choices(cats, catw)[0]
            desc = rng.choice(TEMPLATES[cat])
            tails = " ".join(t.format(b=rng.choice("ABCDEF"), n=rng.choice([12, 25, 40, 60, 120, 200]), m=rng.choice(MONTHS), d=rng.randint(1, 28),
                                       sem=rng.choice(SEMS), dept=rng.choice(DEPTS), ref=rng.randint(10000, 99999)) for t in rng.sample(TAILS, 3))
            desc = (desc + " " + tails).strip()
            token = None
        disposed = rng.random() < (0.72 if age > 21 else 0.15)
        tr = rng.choices([0, 1, 2, 3], [86, 10, 3.6, 0.4])[0]
        if disposed:
            status, last, nxt = "Disposed", "dispose", ""
        else:
            status = rng.choices(["Received", "Under process", "Pending", "Transferred"], [15, 40, 30, 15])[0]
            if tr and status != "Transferred":
                status = rng.choices([status, "Transferred"], [70, 30])[0]
            if status == "Received":
                tr = 0
            last = "show_cause" if (br == "RB" and rng.random() < 0.25) else "inspection" if rng.random() < 0.06 else "transfer" if status == "Transferred" else "remark"
            nxt = "dispose" if status == "Pending" and rng.random() < 0.3 else "reply" if last == "show_cause" else "review"
            if age > 21:
                status = "Beyond timeline"
        c = make_case(new_id(br), br, inst, desc, cat, written_kind=kind, age=age, status=status, last=last, nxt=nxt, token=token, transfers=tr)
        by_inst_cases[inst.id] = c
        steps = [(0, br, "create", "Complaint received")]
        if status != "Received" or disposed:
            steps.append((min(2, age), br, "remark", "Reply sought from the institution"))
        for k in range(tr):
            fb, tb2 = rng.sample([b[0] for b in BUREAUS], 2)
            steps.append((min(3 + k * 3, age), fb, "transfer", f"Transferred {fb} → {tb2}. Examine in your remit."))
        if last in ("show_cause", "inspection") and not disposed:
            steps.append((min(8, age), br, last, "Enforcement step initiated"))
        if disposed:
            steps.append((min(rng.randint(10, 40), age), br, "dispose", "Disposed after reply; complainant informed"))
        hist(c.id, steps)

    off_by_bureau_ref[0] = off_by_bureau
    v2insts = plant_v2(args.seed, sess, insts, cases, actions_spec, key, key_cases, today, bid, bname, cap, taken, special, svit)
    all_insts = insts + v2insts

    sess.add_all(cases)
    sess.commit()

    # ------------------------- resolve (H1)
    print(f"Resolving {len(cases)} institution names ({method_name()}) ...")
    resolver_mod.invalidate()
    r = resolver_mod.Resolver(all_insts)
    stats = {"auto": 0, "confirm": 0, "unlinked": 0}
    results = r.resolve_many([c.institution_name_as_written for c in cases])
    for c, res in zip(cases, results):
        stats[res["decision"]] += 1
        c.link_confidence = res["confidence"]
        c.link_why = {k: v for k, v in res.items()}
        if res["decision"] == "auto":
            c.institution_id, c.link_status = res["institution_id"], "auto"
        elif res["decision"] == "confirm":
            c.suggested_institution_id, c.link_status = res["institution_id"], "unlinked"
        sess.add(c)
    sess.commit()

    # ------------------------- actions (hash-chained) + audit
    rows, audits, last_h = [], [], GENESIS
    for c in cases:
        prev = GENESIS
        for st in sorted(actions_spec[c.id], key=lambda s: s[0]):
            days, bn, act, rem = st[:4]
            topic, verdict = (st[4], st[5]) if len(st) > 4 else (None, None)
            ts = datetime.combine(c.received_date + timedelta(days=days), datetime.min.time()) + timedelta(hours=rng.randint(9, 17), minutes=rng.randint(0, 59))
            officer = rng.choice(off_by_bureau[bid[bn]])
            a_ = CaseAction(case_id=c.id, ts=ts, actor=officer.name, bureau=bn, action=act, remarks=rem, documents=[], prev_hash=prev,
                         finding_topic=topic, finding_verdict=verdict)
            a_.hash = action_hash(prev, a_)
            prev = a_.hash
            rows.append(a_)
    sess.add_all(rows)
    ts0 = datetime.now().replace(microsecond=0)
    for c in cases:
        ev = AuditEvent(ts=ts0, actor="System (seed)", role="system", action="case.create", entity=c.id,
                        payload_json=json.dumps({"bureau": bname[c.bureau_id], "category": c.category}, sort_keys=True), prev_hash=last_h)
        ev.hash = audit_hash(last_h, ev)
        last_h = ev.hash
        audits.append(ev)
    sess.add_all(audits)
    sess.add(Meta(key="seed_date", value=today.isoformat()))
    sess.add(Meta(key="resolver_method", value=method_name()))
    sess.commit()

    summary = rebuild_overlaps(sess)
    key["resolver_method"] = method_name()
    (ROOT / "data" / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf8")

    # ------------------------- report
    from collections import Counter
    print(f"\nSeeded in {time.time() - t0:.1f}s · {len(insts)} institutions · {len(cases)} cases · {len(rows)} actions · {len(audits)} audit events")
    print("Bureau mix:", dict(Counter(bname[c.bureau_id] for c in cases)))
    print("Status mix:", dict(Counter(c.status for c in cases)))
    print("Auto-link decisions:", stats, "|", summary)
    inst_name = {i.id: i.name for i in insts}
    ov = sess.exec(__import__("sqlmodel").select(Overlap)).all()
    sev_of = {}
    for o in ov:
        for cid in (o.case_a, o.case_b):
            sev_of[cid] = max(sev_of.get(cid, ("", -1)), (o.severity, {"CONFLICTING": 3, "DUPLICATE": 2, "RELATED": 1}[o.severity]), key=lambda t: t[1])
    print("\nDEMO CASES")
    print(f"{'Case ID':<16}{'Scenario':<14}{'Written as':<50}{'Resolved to':<40}{'Conf':<6}{'Link':<9}{'Status':<14}Overlap")
    sc = {a.id: "CONFLICTING", b.id: "CONFLICTING", d.id: "DUPLICATE", e.id: "INFO", pp.id: "PING-PONG", sl.id: "DEADLINE RISK"}
    sc.update({c.id: "RELATED" for c in rc})
    for c in [a, b, d, e, *rc, pp, sl]:
        print(f"{c.id:<16}{sc[c.id]:<14}{c.institution_name_as_written[:48]:<50}{(inst_name.get(c.institution_id) or '— (' + str(c.link_status) + ')')[:38]:<40}"
              f"{c.link_confidence:<6.2f}{c.link_status:<9}{c.status:<14}{sev_of.get(c.id, ('—',))[0]}")
    sess.close()
    import sqlite3
    clean = ROOT / "data" / "ekatra.clean.db"      # snapshot used by reset_demo.ps1 (no re-seed needed)
    src, dst = sqlite3.connect(ROOT / "data" / "ekatra.db"), sqlite3.connect(clean)
    src.backup(dst)
    src.close(); dst.close()
    print(f"Clean snapshot saved: {clean.name}")


if __name__ == "__main__":
    main()
