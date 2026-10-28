import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import { FileDown, Search } from "lucide-react";
import { fmtDate, useApi } from "../api";
import CaseTable from "../components/CaseTable";
import SystemicCard from "../components/SystemicCard";
import ContradictionCard from "../components/ContradictionCard";
import { Btn, Card, ErrorNote, Loading, PageHeader, SeverityChip, BUREAU_COLOR, bureauColor, Bar } from "../components/ui";

export default function Institution360() {
  const { id } = useParams();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const list = useApi<any[]>(`/institutions?q=${encodeURIComponent(q)}`);
  const feat = useApi<any[]>(id ? null : "/clusters?severity=CONFLICTING");   // default: the institution with the newest conflict
  const active = id ? Number(id) : feat.data?.[0]?.institution.id ?? (feat.loading ? null : list.data?.[0]?.id ?? null);
  const d = useApi<any>(active ? `/institutions/${active}` : null, [active]);
  const x = d.data;

  const lanes = Object.keys(BUREAU_COLOR);
  const tl = x?.timeline ?? [];
  const swim = {
    grid: { left: 8, right: 16, top: 10, bottom: 4, containLabel: true },
    tooltip: { formatter: (p: any) => `<b>${p.data[2]}</b><br/>${p.data[3]} · ${p.data[4]}<br/>${p.data[5]}` },
    xAxis: { type: "time", axisLabel: { fontSize: 10 }, splitLine: { show: false } },
    yAxis: { type: "category", data: lanes, inverse: true, axisLabel: { fontSize: 11 }, splitLine: { show: true, lineStyle: { color: "#EEF0F3" } } },
    series: [{ type: "scatter", symbolSize: 11, data: tl.map((t: any) => ({ value: [t.ts, t.bureau, t.case_id, t.action.replace("_", "-"), new Date(t.ts).toLocaleDateString("en-IN"), t.remarks.slice(0, 70)], itemStyle: { color: bureauColor(t.bureau) } })) }],
  };

  return (
    <>
      <PageHeader title="Institution 360°" subtitle="Everything every Bureau knows about one institution, in one place." />
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-3">
          <Card className="!p-4">
            <div className="relative"><Search size={15} className="absolute left-3 top-3 text-slate-400" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name, alias (SVIT), ID, city" className="h-10 w-full rounded-lg border border-line pl-9 pr-3 text-sm outline-none focus:border-navy" /></div>
            <ul className="mt-3 space-y-1 max-h-[66vh] overflow-y-auto pr-1">
              {[...(list.data ?? [])].sort((a, b) => Number(b.id === active) - Number(a.id === active)).map((i) => (
                <li key={i.id}>
                  <button onClick={() => nav(`/institutions/${i.id}`)} className={`w-full text-left rounded-lg px-3 py-2 ${i.id === active ? "bg-navy text-white" : "hover:bg-slate-50"}`}>
                    <div className="text-[13px] font-medium leading-snug">{i.name}</div>
                    <div className={`text-[11px] mt-0.5 flex items-center gap-2 ${i.id === active ? "text-white/70" : "text-slate-500"}`}>
                      {i.city} · {i.open_cases} open {i.has_conflict && <span className="inline-block h-2 w-2 rounded-full bg-sev-conflict" title="Conflict" />}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>
        <div className="col-span-9 space-y-5">
          {d.error && <ErrorNote msg={d.error} />}
          {!x && !d.error && <Loading what="institution" />}
          {x && (
            <>
              <Card>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-navy">{x.institution.name}</h2>
                    <div className="text-sm text-slate-500 mt-1">Permanent ID <b className="text-slate-700">{x.institution.permanent_id}</b> · {x.institution.city}, {x.institution.state} {x.institution.pincode} · {x.institution.region} region · {x.institution.type}</div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      {x.institution.aliases.map((a: string) => <span key={a} className="text-xs bg-slate-100 text-slate-600 rounded-full px-2.5 py-1">{a}</span>)}
                    </div>
                  </div>
                  <a href={`/api/institutions/${x.institution.id}/brief.pdf`} target="_blank" rel="noreferrer"><Btn kind="amber"><FileDown size={16} />Generate Institution Brief</Btn></a>
                </div>
                <div className="grid grid-cols-4 gap-4 mt-5">
                  {[["Open cases", x.stats.open], ["Bureaus involved", x.stats.bureaus], ["Conflicting clusters", x.stats.conflicts], ["Beyond timeline", x.stats.overdue]].map(([l, v]) => (
                    <div key={l as string} className="rounded-lg bg-slate-50 p-4"><div className="text-xs text-slate-500">{l}</div><div className={`text-2xl font-semibold ${l === "Conflicting clusters" && (v as number) > 0 ? "text-sev-conflict" : "text-navy"}`}>{v}</div></div>
                  ))}
                </div>
              </Card>
              {x.systemic && <SystemicCard s={x.systemic} />}
              {x.contradictions.map((c: any, i: number) => <ContradictionCard key={i} c={c} />)}
              <div className="grid grid-cols-12 gap-5">
                <Card className="col-span-8">
                  <h3 className="text-base font-semibold text-navy mb-1">Cross-Bureau timeline</h3>
                  <ReactECharts option={swim} style={{ height: 210 }} />
                  <div className="flex gap-4 mt-1 flex-wrap">{lanes.map((l) => <span key={l} className="text-xs text-slate-600 inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: BUREAU_COLOR[l] }} />{l}</span>)}</div>
                </Card>
                <div className="col-span-4 space-y-5">
                  <Card className="!p-5">
                    <h3 className="text-base font-semibold text-navy mb-3">Open cases by Bureau</h3>
                    <div className="space-y-3">
                      {x.open_by_bureau.map((b: any) => (
                        <div key={b.bureau}><div className="flex justify-between text-sm"><span>{b.bureau}</span><b>{b.count}</b></div><Bar value={b.count} max={Math.max(...x.open_by_bureau.map((o: any) => o.count))} color={bureauColor(b.bureau)} /></div>
                      ))}
                      {x.open_by_bureau.length === 0 && <div className="text-sm text-slate-400">No open cases.</div>}
                    </div>
                  </Card>
                  <Card className="!p-5">
                    <h3 className="text-base font-semibold text-navy mb-3">Clusters</h3>
                    {x.clusters.length === 0 && <div className="text-sm text-slate-400">No overlaps.</div>}
                    {x.clusters.map((c: any) => (
                      <Link key={c.id} to={`/overlaps?cluster=${c.id}`} className="flex items-center justify-between gap-2 py-1.5 hover:bg-slate-50 rounded px-1">
                        <SeverityChip level={c.severity} /><span className="text-xs text-slate-500">{c.case_count} cases · {c.bureaus.join(", ")}</span>
                      </Link>
                    ))}
                  </Card>
                </div>
              </div>
              <Card className="!p-0 overflow-hidden">
                <div className="px-5 py-4 border-b border-line text-base font-semibold text-navy">Cases · {x.stats.total} total <span className="text-xs text-slate-400 font-normal">since {x.cases.length ? fmtDate(x.cases[x.cases.length - 1].received_date) : "—"}</span></div>
                <CaseTable items={x.cases} />
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}
