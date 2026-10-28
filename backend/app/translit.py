"""Devanagari <-> Roman helpers. Common institution words come from a small gazetteer;
proper names go through ITRANS transliteration so the fuzzy matcher sees a Roman form."""
import re

from indic_transliteration import sanscript

DEVA = re.compile(r"[ऀ-ॿ]")

# English word -> canonical Hindi spelling (used by the data generator)
EN2HI = {
    "shri": "श्री", "institute": "इंस्टीट्यूट", "of": "ऑफ", "technology": "टेक्नोलॉजी",
    "engineering": "इंजीनियरिंग", "college": "कॉलेज", "management": "मैनेजमेंट", "science": "साइंस",
    "polytechnic": "पॉलिटेक्निक", "university": "यूनिवर्सिटी", "pharmacy": "फार्मेसी", "and": "एंड",
    "technical": "टेक्निकल", "education": "एजुकेशन", "academy": "एकेडमी", "women": "वीमेन", "for": "फॉर",
    "studies": "स्टडीज", "research": "रिसर्च", "sciences": "साइंसेज", "campus": "कैंपस",
}
# Hindi spellings (incl. common variants) -> English word (used by the resolver)
HI2EN = {v: k for k, v in EN2HI.items()}
HI2EN.update({"इंस्टिट्यूट": "institute", "इन्स्टिट्यूट": "institute", "टेक्नालॉजी": "technology",
              "इंजिनियरिंग": "engineering", "कालेज": "college", "श्रि": "shri", "श्री": "shri"})


def to_devanagari(text: str) -> str:
    out = []
    for w in text.split():
        lw = w.lower().strip(",.")
        if lw in EN2HI:
            out.append(EN2HI[lw])
        else:
            out.append(sanscript.transliterate(lw, sanscript.ITRANS, sanscript.DEVANAGARI))
    return " ".join(out)


def _simplify(roman: str) -> str:
    r = roman.lower().replace("~n", "n").replace("~", "")
    for a, b in (("aa", "a"), ("ii", "i"), ("uu", "u"), ("ee", "i"), ("oo", "u"), ("sh", "s"), ("m", "n")):
        r = r.replace(a, b)
    r = re.sub(r"[^a-z0-9 ]", "", r)
    return re.sub(r"(.)\1+", r"\1", r)


def deva_to_roman(text: str) -> str:
    out = []
    for w in re.split(r"[\s,.\-]+", text):
        if not w:
            continue
        if w in HI2EN:
            out.append(HI2EN[w])
        elif DEVA.search(w):
            out.append(_simplify(sanscript.transliterate(w, sanscript.DEVANAGARI, sanscript.ITRANS)))
        else:
            out.append(w)
    return " ".join(out)
