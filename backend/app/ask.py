"""Ask Ekatra – keyword/intent parser (English + basic Hindi). No LLM involved."""
import re

BUREAU_WORDS = {"pgrc": "PGRC", "rb": "RB", "approval": "Approval", "apb": "Approval", "academic": "Academic", "acb": "Academic",
                "regional": "Regional Office", "ro": "Regional Office"}
STATUS_WORDS = {"overdue": "Beyond timeline", "late": "Beyond timeline", "delayed": "Beyond timeline", "beyond": "Beyond timeline",
                "pending": "Pending", "disposed": "Disposed", "closed": "Disposed", "transferred": "Transferred",
                "received": "Received", "process": "Under process", "lambit": "Pending", "nipta": "Disposed"}
REGION_WORDS = {"south": "South", "southern": "South", "dakshin": "South", "north": "North", "northern": "North", "uttar": "North",
                "east": "East", "eastern": "East", "purv": "East", "west": "West", "western": "West", "paschim": "West",
                "central": "Central", "madhya": "Central", "northeast": "North-East", "north-east": "North-East"}
CATEGORY_WORDS = {"hostel": "Infrastructure", "infrastructure": "Infrastructure", "lab": "Norms violation", "norms": "Norms violation",
                  "faculty": "Faculty", "teacher": "Faculty", "teachers": "Faculty", "fee": "Fees & refund", "fees": "Fees & refund",
                  "refund": "Fees & refund", "ragging": "Ragging", "admission": "Admission"}
INTENT_WORDS = {"conflict": "conflicts", "conflicts": "conflicts", "conflicting": "conflicts", "overlap": "overlaps", "overlaps": "overlaps",
                "duplicate": "duplicates", "duplicates": "duplicates", "pingpong": "pingpong", "ping-pong": "pingpong"}
FILLER = {"cases", "case", "in", "the", "region", "of", "show", "me", "all", "this", "ki", "ke", "ka", "ko", "hai", "shikayat", "shikayatein",
          "shikayaten", "mamle", "list", "for", "at", "with", "and", "week", "month", "today", "aaj", "is", "hafte", "mahine", "complaints",
          "complaint", "regarding", "about", "bureau", "wale", "wali", "sabhi", "kitne"}


def parse(query: str, resolver=None) -> dict:
    q = query.lower()
    toks = re.findall(r"[a-z0-9\-]+", q)
    f, used = {}, set()
    for t in toks:
        if t in BUREAU_WORDS:
            f["bureau"], _ = BUREAU_WORDS[t], used.add(t)
        elif t in STATUS_WORDS:
            f["status"], _ = STATUS_WORDS[t], used.add(t)
        elif t in REGION_WORDS:
            f["region"], _ = REGION_WORDS[t], used.add(t)
        elif t in CATEGORY_WORDS:
            f["category"], _ = CATEGORY_WORDS[t], used.add(t)
        elif t in INTENT_WORDS:
            f["intent"], _ = INTENT_WORDS[t], used.add(t)
    if re.search(r"this week|is hafte|last 7|week", q):
        f["since_days"] = 7
    elif re.search(r"this month|is mahine|month", q):
        f["since_days"] = 30
    left = [t for t in toks if t not in used and t not in FILLER]
    if left and resolver is not None:
        guess = resolver.resolve(" ".join(left))
        if guess["decision"] in ("auto", "confirm") and guess["confidence"] >= 0.6:
            f["institution_id"] = guess["institution_id"]
            f["institution_name"] = guess["institution_name"]
    return f
