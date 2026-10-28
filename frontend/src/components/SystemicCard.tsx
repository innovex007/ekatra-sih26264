import { Link } from "react-router-dom";
import { Network } from "lucide-react";
import { Card, BureauChip, CaseLink } from "./ui";

export default function SystemicCard({ s, link }: { s: any; link?: boolean }) {
  return (
    <Card className="!p-5 border-l-4 !border-l-sev-duplicate">
      <div className="flex items-start gap-3">
        <div className="h-9 w-9 rounded-full bg-sev-duplicateBg text-sev-duplicate flex items-center justify-center shrink-0"><Network size={18} /></div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h3 className="text-base font-semibold text-navy">Possible systemic issue</h3>
            {link && <Link to={`/institutions/${s.institution.id}`} className="text-sm text-navy hover:underline font-medium truncate">{s.institution.name}</Link>}
            <span className="ml-auto text-xs text-slate-500">score {s.score} · {s.categories.length} categories × {s.bureaus.length} Bureaus</span>
          </div>
          <p className="text-sm text-slate-700 mt-1">{s.explanation}</p>
          <div className="flex flex-wrap gap-2 mt-3">
            {s.categories.map((c: string) => <span key={c} className="text-xs bg-sev-duplicateBg text-sev-duplicate rounded-full px-2.5 py-1">{c}</span>)}
          </div>
          <ul className="mt-3 divide-y divide-line rounded-lg border border-line">
            {s.cases.map((c: any) => (
              <li key={c.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                <CaseLink id={c.id} /><BureauChip name={c.bureau} /><span className="text-slate-600">{c.category}</span>
                <span className="ml-auto text-xs text-slate-400">{c.age_days} day{c.age_days === 1 ? "" : "s"} ago</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-600 mt-3"><b>Suggested action:</b> {s.suggested_action}.</p>
        </div>
      </div>
    </Card>
  );
}
