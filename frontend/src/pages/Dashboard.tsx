import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock } from "lucide-react";
import { useApi } from "../api";
import { Card, ErrorNote, Loading, PageHeader, BUREAU_COLOR } from "../components/ui";
import india from "../assets/india.json";

echarts.registerMap("india", india as any);

const KPIS: { key: string; label: string; to: string; tone?: "red" | "amber" }[] = [
  { key: "total", label: "Total cases", to: "/cases" },
  { key: "pending", label: "Pending", to: "/cases?status=Pending" },
  { key: "under_process", label: "Under process", to: "/cases?status=Under%20process" },
  { key: "disposed", label: "Disposed", to: "/cases?status=Disposed" },
  { key: "transferred", label: "Transferred", to: "/cases?status=Transferred" },
  { key: "beyond_timeline", label: "Beyond timeline", to: "/cases?status=Beyond%20timeline", tone: "amber" },
  { key: "open_overlaps", label: "Open overlaps", to: "/overlaps", tone: "red" },
  { key: "conflicts_blocked", label: "Conflicts blocked", to: "/audit", tone: "red" },
];

export default function Dashboard() {
  const { data: d, loading, error } = useApi<any>("/dashboard/summary");
  const nav = useNavigate();
  if (error) return <ErrorNote msg={error} />;
  if (loading || !d) return <Loading what="dashboard" />;

  const bureauOpt = {
    grid: { left: 8, right: 8, top: 24, bottom: 4, containLabel: true }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { data: ["Within timeline", "Beyond timeline"], top: 0, right: 0, itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
    xAxis: { type: "category", data: d.by_bureau.map((b: any) => b.bureau), axisLabel: { fontSize: 11, interval: 0, formatter: (v: string) => v.replace("Regional Office", "Regional") } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#EEF0F3" } }, axisLabel: { fontSize: 11 } },
    series: [
      { name: "Within timeline", type: "bar", stack: "o", barWidth: "46%", data: d.by_bureau.map((b: any) => ({ value: b.open - b.overdue, itemStyle: { color: BUREAU_COLOR[b.bureau] } })) },
      { name: "Beyond timeline", type: "bar", stack: "o", data: d.by_bureau.map((b: any) => b.overdue), itemStyle: { color: "#C62828", borderRadius: [4, 4, 0, 0] } },
    ],
  };
  const ageOpt = {
    grid: { left: 4, right: 12, top: 8, bottom: 4, containLabel: true }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: d.ageing.map((a: any) => a.bucket + " d"), axisLabel: { fontSize: 11 } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#EEF0F3" } }, axisLabel: { fontSize: 11 } },
    series: [{ type: "bar", barWidth: "50%", data: d.ageing.map((a: any, i: number) => ({ value: a.count, itemStyle: { color: ["#93C5FD", "#60A5FA", "#F5A623", "#C62828"][i], borderRadius: [4, 4, 0, 0] } })) }],
  };
  const open: Record<string, number> = Object.fromEntries(d.regions.map((r: any) => [r.region, r.open]));
  const max = Math.max(1, ...Object.values(open));
  const mapOpt = {
    tooltip: { trigger: "item", formatter: (p: any) => `${p.data?.region ?? p.name}<br/><b>${p.data?.value ?? 0}</b> open cases` },
    visualMap: { min: 0, max, left: 4, bottom: 4, itemHeight: 70, itemWidth: 10, text: ["More", "Fewer"], calculable: false, textStyle: { fontSize: 10 }, inRange: { color: ["#E5ECF6", "#14325C"] } },
    series: [{ type: "map", map: "india", roam: false, nameProperty: "name", left: 0, right: 0, top: 0, bottom: 0, itemStyle: { borderColor: "#fff", borderWidth: 0.6 },
      emphasis: { label: { show: false }, itemStyle: { areaColor: "#F5A623" } },
      data: (india as any).features.map((f: any) => ({ name: f.properties.name, region: f.properties.region, value: open[f.properties.region] ?? 0 })) }],
  };

  return (
    <div className="flex flex-col min-h-0 h-[calc(100vh-156px)] min-h-[540px]">
      <PageHeader title="Command Dashboard" subtitle="One live view of every complaint case across every AICTE Bureau." />
      <div className="grid grid-cols-8 gap-3 mb-4 shrink-0">
        {KPIS.map((k) => {
          const hot = k.tone === "red" && d[k.key] > 0;
          return (
            <button key={k.key} onClick={() => nav(k.to)}
              className={`text-left rounded-xl border p-4 shadow-card transition hover:-translate-y-0.5 ${hot ? "bg-sev-conflictBg border-red-200" : k.tone === "amber" ? "bg-white border-line" : "bg-white border-line"}`}>
              <div className="text-[11px] text-slate-500 leading-tight h-7">{k.label}{k.key === "conflicts_blocked" && <span className="block text-[10px] text-slate-400">since last reset</span>}</div>
              <div className={`text-2xl font-semibold tabular-nums ${hot ? "text-sev-conflict" : k.tone === "amber" ? "text-sev-duplicate" : "text-navy"}`}>{d[k.key].toLocaleString()}</div>
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-12 gap-5 flex-1 min-h-0">
        <Card className="col-span-4 flex flex-col min-h-0 !p-5">
          <h2 className="text-sm font-semibold text-navy mb-1">Bureau workload (open cases)</h2>
          <div className="flex-1 min-h-0"><ReactECharts option={bureauOpt} style={{ height: "100%", minHeight: 200 }} /></div>
        </Card>
        <Card className="col-span-4 flex flex-col min-h-0 !p-5">
          <h2 className="text-sm font-semibold text-navy mb-1">Open cases by region</h2>
          <div className="flex-1 min-h-0"><ReactECharts option={mapOpt} style={{ height: "100%", minHeight: 200 }} /></div>
        </Card>
        <div className="col-span-4 flex flex-col gap-5 min-h-0">
          <Card className="!p-5 shrink-0">
            <h2 className="text-sm font-semibold text-navy">Ageing of open cases</h2>
            <ReactECharts option={ageOpt} style={{ height: 112 }} />
          </Card>
          <Card className="!p-5 flex-1 min-h-0 overflow-hidden">
            <h2 className="text-sm font-semibold text-navy mb-2">Needs attention</h2>
            <ul className="space-y-1.5">
              {d.needs_attention.slice(0, 3).map((a: any, i: number) => (
                <li key={i}>
                  <button onClick={() => nav(a.kind === "conflict" ? `/overlaps?cluster=${a.cluster_id}` : `/cases/${a.case_id}`)}
                    className="w-full flex items-center gap-2.5 text-left rounded-lg px-2 py-1.5 hover:bg-slate-50">
                    {a.kind === "conflict" ? <AlertTriangle size={15} className="text-sev-conflict shrink-0" /> : <Clock size={15} className="text-sev-duplicate shrink-0" />}
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px] font-medium text-slate-800 truncate">{a.title}</span>
                      <span className="block text-[11px] text-slate-500 truncate">{a.detail}</span>
                    </span>
                    
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
