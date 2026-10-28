import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { fmtDate, useApi } from "../api";
import SystemicCard from "../components/SystemicCard";
import ContradictionCard from "../components/ContradictionCard";
import { BureauChip, Card, CaseLink, ErrorNote, Loading, PageHeader, SlaChip, SeverityChip, bureauColor } from "../components/ui";

const TABS = [["conflicts", "Conflicts"], ["contradictions", "Contradicting findings"], ["systemic", "Systemic"], ["deadline", "Deadline risk"], ["pingpong", "Ping-pong"], ["duplicates", "Duplicates"]] as const;

export default function Alerts() {
  const [tab, setTab] = useState<string>("conflicts");
  const { data, loading, error } = useApi<any>(`/alerts?type=${tab}`, [tab]);
  const [seen, setSeen] = useState<Record<string, number>>({});
  useEffect(() => { if (data?.counts) setSeen(data.counts); }, [data]);
  const counts = seen;
  return (
    <>
      <PageHeader title="Alert Centre" subtitle="Conflicts, deadline risk, ping-pong transfers and duplicates that need a human decision." />
      <div className="flex gap-2 mb-5">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`h-10 px-4 rounded-lg text-sm font-medium border ${tab === k ? "bg-navy text-white border-navy" : "bg-white text-slate-700 border-line hover:bg-slate-50"}`}>
            {l} <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${tab === k ? "bg-white/20" : "bg-slate-100"}`}>{counts[k] ?? "·"}</span>
          </button>
        ))}
      </div>
      {error && <ErrorNote msg={error} />}
      {(loading || (data && data.type !== tab)) && <Loading what="alerts" />}
      {data && data.type === tab && (
        <div className="space-y-3">
          {data.items.length === 0 && <Card className="text-center text-sm text-slate-500">Nothing to flag.</Card>}
          {(tab === "conflicts" || tab === "duplicates") && data.items.map((a: any, i: number) => (
            <Card key={i} className="!p-5 flex items-center gap-5">
              <SeverityChip level={tab === "conflicts" ? "CONFLICTING" : "DUPLICATE"} />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-800 truncate">{a.institution?.name}</div>
                <div className="text-sm text-slate-600 mt-0.5 flex flex-wrap items-center gap-2"><CaseLink id={a.case_a.id} /><BureauChip name={a.case_a.bureau} /> ↔ <CaseLink id={a.case_b.id} /><BureauChip name={a.case_b.bureau} /></div>
                <div className="text-xs text-slate-500 mt-1">{a.reason}</div>
              </div>
              <Link to={`/overlaps?cluster=${a.cluster_id}`} className="text-sm text-navy font-medium inline-flex items-center gap-1 hover:underline">Open cluster <ArrowRight size={14} /></Link>
            </Card>
          ))}
          {tab === "systemic" && data.items.slice(0, 15).map((a: any) => <SystemicCard key={a.institution.id} s={a} link />)}
          {tab === "systemic" && data.items.length > 15 && <div className="text-xs text-slate-500 px-1">Showing the 15 highest-scoring of {data.items.length}. Scores combine categories × Bureaus × recency.</div>}
          {tab === "contradictions" && data.items.map((a: any, i: number) => <ContradictionCard key={i} c={a} link />)}
          {tab === "deadline" && data.items.slice(0, 40).map((a: any) => (
            <Card key={a.case.id} className="!p-4 flex items-center gap-5">
              <CaseLink id={a.case.id} /><BureauChip name={a.case.bureau} />
              <div className="flex-1 min-w-0 text-sm text-slate-600 truncate">{a.case.institution?.name ?? a.case.written} · {a.case.category}</div>
              <span className="text-xs text-slate-500">due {fmtDate(a.case.due_date)} · risk {a.risk.toFixed(2)}</span><SlaChip sla={a.case.sla} />
            </Card>
          ))}
          {tab === "pingpong" && data.items.map((a: any) => (
            <Card key={a.case.id} className="!p-5">
              <div className="flex items-center gap-3 mb-3"><CaseLink id={a.case.id} /><span className="text-sm text-slate-600">{a.case.institution?.name}</span>
                <span className="ml-auto text-xs font-semibold text-sev-duplicate bg-sev-duplicateBg rounded-full px-2.5 py-1">{a.case.transfer_count} transfers · senior management alerted</span></div>
              <div className="flex flex-wrap items-center gap-2">
                {a.chain.map((t: any, i: number) => {
                  const to = (t.remarks.match(/→ ([A-Za-z ]+?)\./) ?? [])[1] ?? "";
                  return (
                    <span key={i} className="inline-flex items-center gap-2">
                      {i === 0 && <span className="text-xs rounded-full px-2.5 py-1 text-white" style={{ background: bureauColor(t.from) }}>{t.from}</span>}
                      <ArrowRight size={14} className="text-slate-400" />
                      <span className="text-xs rounded-full px-2.5 py-1 text-white" style={{ background: bureauColor(to) }}>{to}</span>
                    </span>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
