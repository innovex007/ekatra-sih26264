import csv
import io
from collections import Counter, defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .sla import effective_status

TYPES = {"bureau": "Bureau-wise", "region": "Region-wise", "institution": "Institution-wise", "ageing": "Ageing",
         "disposal": "Disposal rate", "overlaps": "Overlaps"}


def build(kind: str, L) -> tuple[list, list]:
    """Returns (header, rows)."""
    cases = L.cases
    eff = {c.id: effective_status(c, L.today) for c in cases}
    if kind == "bureau":
        rows = []
        for b in L.bureau.values():
            cs = [c for c in cases if c.bureau_id == b.id]
            rows.append([b.name, len(cs), sum(eff[c.id] != "Disposed" for c in cs), sum(eff[c.id] == "Disposed" for c in cs),
                         sum(eff[c.id] == "Beyond timeline" for c in cs)])
        return ["Bureau", "Total", "Open", "Disposed", "Beyond timeline"], rows
    if kind == "region":
        agg = defaultdict(lambda: [0, 0, 0])
        for c in cases:
            r = L.inst[c.institution_id].region if c.institution_id else "Unlinked"
            agg[r][0] += 1
            agg[r][1] += eff[c.id] != "Disposed"
            agg[r][2] += eff[c.id] == "Beyond timeline"
        return ["Region", "Total", "Open", "Beyond timeline"], [[k, *v] for k, v in sorted(agg.items())]
    if kind == "institution":
        agg = defaultdict(lambda: [0, 0, set()])
        for c in cases:
            if c.institution_id:
                a = agg[c.institution_id]
                a[0] += 1
                a[1] += eff[c.id] != "Disposed"
                a[2].add(c.bureau_id)
        rows = sorted(([L.inst[i].name, L.inst[i].permanent_id, v[0], v[1], len(v[2])] for i, v in agg.items()), key=lambda r: -r[3])
        return ["Institution", "Permanent ID", "Cases", "Open", "Bureaus"], rows[:60]
    if kind == "ageing":
        bk = Counter()
        for c in cases:
            if eff[c.id] != "Disposed":
                a = (L.today - c.received_date).days
                bk["0-7" if a <= 7 else "8-14" if a <= 14 else "15-21" if a <= 21 else ">21"] += 1
        return ["Age (days)", "Open cases"], [[k, bk[k]] for k in ("0-7", "8-14", "15-21", ">21")]
    if kind == "disposal":
        rows = []
        for b in L.bureau.values():
            cs = [c for c in cases if c.bureau_id == b.id]
            d = sum(eff[c.id] == "Disposed" for c in cs)
            rows.append([b.name, len(cs), d, f"{(100 * d / len(cs)) if cs else 0:.1f}%"])
        return ["Bureau", "Cases", "Disposed", "Disposal rate"], rows
    rows = Counter(o.severity for o in L.overlaps)
    return ["Severity", "Linked pairs"], [[k, rows.get(k, 0)] for k in ("CONFLICTING", "DUPLICATE", "RELATED")]


def to_csv(header, rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def to_pdf(title: str, sections: list) -> bytes:
    """sections: [(heading, header, rows)]"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    st = getSampleStyleSheet()
    el = [Paragraph(title, st["Title"]), Paragraph("Prototype · synthetic data", st["Italic"]), Spacer(1, 12)]
    for heading, header, rows in sections:
        el.append(Paragraph(heading, st["Heading3"]))
        t = Table([header] + [[str(x) for x in r] for r in rows], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14325C")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F8FA")])]))
        el += [t, Spacer(1, 12)]
    doc.build(el)
    return buf.getvalue()
