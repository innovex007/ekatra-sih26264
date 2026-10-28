"""H1 – 'Same College, Different Name' resolver."""
import re
from typing import Optional

import numpy as np
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from .config import rules
from .embedder import get_embedder
from .translit import DEVA, deva_to_roman

PID_RE = re.compile(r"1-\d{9}")
PIN_RE = re.compile(r"\b\d{6}\b")


def trigrams(s: str) -> set:
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def tri_sim(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def skeleton(s: str) -> str:
    s = s.replace("ph", "f").replace("w", "v").replace("z", "s").replace("q", "k").replace("c", "k").replace("x", "ks")
    s = re.sub(r"(?<=\w)[aeiouy]", "", s)  # keep a leading vowel only
    return re.sub(r"(.)\1+", r"\1", s)


class Resolver:
    def __init__(self, institutions):
        cfg = rules()["resolver"]
        self.cfg = cfg
        self.w = cfg["weights"]
        self.abbr = cfg["abbreviations"]
        self.stop = set(cfg["stopwords"])
        self.embedder = get_embedder()
        self.insts = []
        for inst in institutions:
            names = [inst.name] + list(inst.aliases or [])
            norms = [self.norm(n) for n in names]
            self.insts.append({
                "inst": inst, "names": names, "norms": norms, "tris": [trigrams(n) for n in norms],
                "skels": [skeleton(n) for n in norms], "acr": (inst.acronym or "").lower(),
                "city": self.norm(inst.city), "district": self.norm(inst.district), "pin": inst.pincode,
            })
        self.name_index = {}
        for r in self.insts:
            for n in r["norms"]:
                if len(n.split()) >= 3:
                    self.name_index.setdefault(n, set()).add(r["inst"].id)
        self.loc_tokens = {t for r in self.insts for t in (r["city"] + " " + r["district"]).split()}
        df = {}
        for r in self.insts:
            for t in set(r["norms"][0].split()):
                df[t] = df.get(t, 0) + 1
        n = max(len(self.insts), 1)
        self.generic = {t for t, c in df.items() if c / n > cfg["generic_df"]}
        self.pid_map = {r["inst"].permanent_id: r for r in self.insts}
        self.alias_emb = None
        if self.embedder:
            flat = [(i, nm) for i, r in enumerate(self.insts) for nm in r["norms"]]
            self.alias_idx = np.array([i for i, _ in flat])
            self.alias_emb = self.embedder.encode([nm for _, nm in flat], "query")

    # -- normalisation -------------------------------------------------
    def norm(self, text: str) -> str:
        if DEVA.search(text or ""):
            text = deva_to_roman(text)
        t = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
        toks = [self.abbr.get(w, w) for w in t.split()]
        return " ".join(w for w in toks if w not in self.stop)

    def _acronym_tokens(self, raw: str) -> set:
        s = deva_to_roman(raw) if DEVA.search(raw) else raw
        s = re.sub(r"\b(?:[A-Za-z]\.){2,}[A-Za-z]?\.?", lambda m: re.sub(r"\W", "", m.group()), s)
        return set(re.findall(r"[a-z0-9]+", s.lower()))

    # -- scoring -------------------------------------------------------
    def _name_sim(self, variants, r):
        best, alias = 0.0, r["names"][0]
        for v in variants:
            vt = trigrams(v)
            vd = set(v.split()) - self.generic
            for nm, n, ntri in zip(r["names"], r["norms"], r["tris"]):
                ts = fuzz.token_set_ratio(v, n) / 100 if vd & (set(n.split()) - self.generic) else 0.0
                s = max(JaroWinkler.similarity(v, n), tri_sim(vt, ntri), ts)
                if s > best:
                    best, alias = s, nm
        return best, alias

    def _embed_sim(self, norm_text, r, idx, text_emb):
        if self.alias_emb is not None and text_emb is not None:
            lo, hi = self.cfg["e5_rescale"]
            sims = self.alias_emb[self.alias_idx == idx] @ text_emb
            return float(np.clip((sims.max() - lo) / (hi - lo), 0, 1)), "multilingual-e5-small"
        sk = skeleton(norm_text)
        best = max((max(fuzz.ratio(sk, s), fuzz.token_set_ratio(sk, s)) for s in r["skels"]), default=0) / 100
        return best, "transliteration+phonetic-fuzzy"

    def _emb_text(self, raw: str) -> str:
        nt = self.norm(PID_RE.sub(" ", PIN_RE.sub(" ", raw)))
        return " ".join(t for t in nt.split() if t not in self.loc_tokens) or nt or raw

    def resolve_many(self, texts):
        embs = self.embedder.encode([self._emb_text(t) for t in texts], "query") if self.embedder else [None] * len(texts)
        return [self.resolve(t, e) for t, e in zip(texts, embs)]

    def embed_text(self, text: str):
        return self.embedder.encode([text], "query")[0] if self.embedder else None

    def resolve(self, text: str, text_emb=None) -> dict:
        raw = text or ""
        w, cfg = self.w, self.cfg
        pid = PID_RE.search(raw)
        if pid and pid.group() in self.pid_map:
            r = self.pid_map[pid.group()]
            return self._result(r, 1.0, {"name": self._f(1.0, w["name"], "exact Permanent ID"),
                                         "acronym": self._f(1.0, w["acronym"], "exact Permanent ID"),
                                         "location": self._f(1.0, w["location"], "exact Permanent ID"),
                                         "embedding": self._f(1.0, w["embedding"], "exact Permanent ID")},
                                "auto", [], exact_id=True)
        pins = set(PIN_RE.findall(raw))
        cleaned = PID_RE.sub(" ", PIN_RE.sub(" ", raw))
        norm_text = self.norm(cleaned)
        toks = set(norm_text.split())
        acr_toks = self._acronym_tokens(cleaned)
        if self.embedder and text_emb is None:
            text_emb = self.embed_text(self._emb_text(raw))
        ttri = trigrams(norm_text)
        scored = []
        for idx, r in enumerate(self.insts):
            city_hit = bool(r["city"] and set(r["city"].split()) <= toks) or bool(r["district"] and set(r["district"].split()) <= toks)
            pin_hit = r["pin"] in pins
            acr_hit = bool(r["acr"]) and r["acr"] in acr_toks
            dist_overlap = bool((toks - self.generic) & set(" ".join(r["norms"]).split()) - self.generic)
            if not (pin_hit or city_hit or acr_hit or dist_overlap or max(tri_sim(ttri, t) for t in r["tris"]) >= cfg["prefilter_trigram"]):
                continue
            variants = [norm_text]
            if r["city"]:
                stripped = " ".join(t for t in norm_text.split() if t not in r["city"].split() and t not in r["district"].split())
                if stripped and stripped != norm_text:
                    variants.append(stripped)
            name, alias = self._name_sim(variants, r)
            if acr_hit:
                acr, via = 1.0, f"acronym '{r['acr'].upper()}' found"
            elif name >= cfg["exact_name_counts_as_acronym"]:
                acr, via = 1.0, "full name matches"
            else:
                acr, via = 0.0, "no acronym in text"
            if pin_hit:
                loc, ldet = 1.0, f"pincode {r['pin']} found"
            elif city_hit:
                loc, ldet = 0.5, f"city/district '{r['inst'].city}' found"
            else:
                loc, ldet = 0.0, "no location match"
            emb, method = self._embed_sim(norm_text, r, idx, text_emb)
            score = w["name"] * name + w["acronym"] * acr + w["location"] * loc + w["embedding"] * emb
            scored.append((score, r, {
                "name": self._f(name, w["name"], f"best match: '{alias}'"),
                "acronym": self._f(acr, w["acronym"], via),
                "location": self._f(loc, w["location"], ldet),
                "embedding": self._f(emb, w["embedding"], method),
            }))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return {"decision": "unlinked", "confidence": 0.0, "institution_id": None, "best": None, "candidates": []}
        score, r, factors = scored[0]
        runner = next((s for s, rr, _ in scored[1:] if rr["inst"].id != r["inst"].id), 0.0)
        if score >= cfg["auto_link"] and score - runner >= cfg["min_margin"]:
            decision = "auto"
        elif score >= cfg["confirm_min"]:
            decision = "confirm"
        else:
            decision = "unlinked"
        note = None
        stripped = " ".join(t for t in norm_text.split() if t not in self.loc_tokens)
        known = self.name_index.get(norm_text) or self.name_index.get(stripped)
        if known and len(known) == 1 and r["inst"].id in known and decision != "auto":
            floor = cfg["exact_name_floor"]
            score, decision = max(score, floor), "auto"
            note = f"Exact known name/alias, unique to this institution – confidence floored at {floor}"
        cands = [{"institution_id": rr["inst"].id, "name": rr["inst"].name, "score": round(s, 3)} for s, rr, _ in scored[:5]]
        res = self._result(r, score, factors, decision, cands, runner_up=round(runner, 3))
        if note:
            res["note"] = note
        return res

    @staticmethod
    def _f(value, weight, detail):
        return {"value": round(float(value), 3), "weight": weight, "contribution": round(float(value) * weight, 3), "detail": detail}

    @staticmethod
    def _result(r, score, factors, decision, cands, exact_id=False, runner_up=0.0):
        inst = r["inst"]
        return {
            "decision": decision, "confidence": round(float(score), 3), "institution_id": inst.id,
            "institution_name": inst.name, "permanent_id": inst.permanent_id, "exact_id": exact_id,
            "factors": factors, "candidates": cands, "runner_up": runner_up,
            "best": {"institution_id": inst.id, "name": inst.name},
        }


_cache: dict = {"r": None}


def get_resolver(session, fresh: bool = False) -> Resolver:
    from sqlmodel import select

    from .models import Institution
    if fresh or _cache["r"] is None:
        _cache["r"] = Resolver(session.exec(select(Institution)).all())
    return _cache["r"]


def invalidate():
    _cache["r"] = None
