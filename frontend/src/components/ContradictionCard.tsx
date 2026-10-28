import { Link } from "react-router-dom";
import { Scale } from "lucide-react";
import { Card, BureauChip, CaseLink, SeverityChip } from "./ui";
import { fmtDate } from "../api";

export default function ContradictionCard({ c, link }: { c: any; link?: boolean }) {
  return (
    <Card className="!p-5 border-l-4 !border-l-sev-conflict">
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <Scale size={18} className="text-sev-conflict" />
        <h3 className="text-base font-semibold text-navy">Contradicting findings</h3>
        <span className="text-xs font-semibold rounded-full px-2.5 py-1 bg-sev-conflictBg text-sev-conflict uppercase">{c.severity}</span>
        <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2.5 py-1">topic: {c.topic}</span>
        {link && <Link to={`/institutions/${c.institution.id}`} className="text-sm text-navy hover:underline font-medium">{c.institution.name}</Link>}
        <span className="ml-auto text-xs text-slate-500">{c.gap_days} day{c.gap_days === 1 ? "" : "s"} apart</span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {c.sides.map((s: any, i: number) => (
          <div key={i} className={`rounded-lg border p-4 ${s.verdict === "non-compliant" ? "border-red-200 bg-sev-conflictBg/40" : "border-emerald-200 bg-emerald-50/50"}`}>
            <div className="flex items-center gap-2 text-sm"><BureauChip name={s.bureau} /><span className="text-xs text-slate-500">{fmtDate(s.date)} · {s.actor}</span></div>
            <div className={`mt-2 text-lg font-semibold ${s.verdict === "non-compliant" ? "text-sev-conflict" : "text-emerald-700"}`}>{s.verdict}</div>
            <div className="text-xs text-slate-500 mt-1">{s.action.replace("_", "-")} on <CaseLink id={s.case_id} /></div>
          </div>
        ))}
      </div>
      <p className="text-sm text-slate-700 mt-3">{c.explanation}</p>
      <p className="text-xs text-slate-600 mt-1"><b>Suggested action:</b> {c.suggested_action}</p>
      {false && <SeverityChip level="CONFLICTING" />}
    </Card>
  );
}
