import { useState } from "react";
import ReactECharts from "echarts-for-react";
import { Download, FileText } from "lucide-react";
import { useApi } from "../api";
import { Btn, Card, ErrorNote, Loading, PageHeader, Td, Th } from "../components/ui";

const KINDS: [string, string][] = [["bureau", "Bureau-wise"], ["region", "Region-wise"], ["institution", "Institution-wise"], ["ageing", "Ageing"], ["disposal", "Disposal rate"], ["overlaps", "Overlaps"]];

function chartFor(kind: string, header: string[], rows: string[][]) {
  let title = "", unit = "", labels: string[] = [], vals: number[] = [], color = "#14325C";
  if (kind === "bureau" || kind === "disposal") {
    title = "Disposal rate by Bureau"; unit = "%"; color = "#0F9488";
    labels = rows.map((r) => r[0]);
    vals = rows.map((r) => (kind === "bureau" ? (100 * Number(r[3])) / Math.max(1, Number(r[1])) : parseFloat(r[3])));
  } else {
    const idx = header.findIndex((_, i) => i > 0 && rows.every((r) => r[i] !== "" && !isNaN(Number(r[i]))));
    title = header[idx] ?? ""; labels = rows.slice(0, 10).map((r) => r[0]); vals = rows.slice(0, 10).map((r) => Number(r[idx]));
  }
  return {
    title, option: {
      grid: { left: 8, right: 16, top: 16, bottom: 4, containLabel: true }, tooltip: { trigger: "axis", valueFormatter: (v: number) => `${Math.round(v * 10) / 10}${unit}` },
      xAxis: { type: "category", data: labels.map((l) => l.replace("Regional Office", "Regional").slice(0, 22)), axisLabel: { fontSize: 11, interval: 0 } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#EEF0F3" } }, axisLabel: { fontSize: 11, formatter: `{value}${unit}` } },
      series: [{ type: "bar", barWidth: "46%", data: vals.map((v) => Math.round(v * 10) / 10), itemStyle: { color, borderRadius: [4, 4, 0, 0] }, label: { show: true, position: "top", fontSize: 11, formatter: `{c}${unit}` } }],
    },
  };
}

export default function Reports() {
  const [k, setK] = useState("bureau");
  const { data, loading, error } = useApi<any>(`/reports/${k}`, [k]);
  return (
    <>
      <PageHeader title="Reports" subtitle="Export what the monthly review needs, as CSV or PDF."
        actions={<a href="/api/reports/monthly-pack?format=pdf" target="_blank" rel="noreferrer"><Btn kind="amber"><FileText size={16} />Monthly pack (PDF)</Btn></a>} />
      <div className="grid grid-cols-12 gap-6">
        <Card className="col-span-3 !p-3 self-start">
          {KINDS.map(([id, l]) => <button key={id} onClick={() => setK(id)} className={`w-full text-left rounded-lg px-4 py-2.5 text-sm ${k === id ? "bg-navy text-white font-medium" : "hover:bg-slate-50 text-slate-700"}`}>{l}</button>)}
        </Card>
        <Card className="col-span-9 !p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-line">
            <h2 className="text-base font-semibold text-navy">{data?.title ?? "Report"}</h2>
            <div className="flex gap-2">
              <a href={`/api/reports/${k}?format=csv`}><Btn><Download size={15} />CSV</Btn></a>
              <a href={`/api/reports/${k}?format=pdf`} target="_blank" rel="noreferrer"><Btn><Download size={15} />PDF</Btn></a>
            </div>
          </div>
          {error && <div className="p-5"><ErrorNote msg={error} /></div>}
          {loading && !data ? <Loading what="report" /> : data && (
            <>
            <div className="px-5 pt-4"><div className="text-sm font-semibold text-slate-700">{chartFor(k, data.header, data.rows).title}</div>
              <ReactECharts option={chartFor(k, data.header, data.rows).option} style={{ height: 190 }} /></div>
            <table className="w-full border-collapse">
              <thead><tr>{data.header.map((h: string) => <Th key={h}>{h}</Th>)}</tr></thead>
              <tbody>{data.rows.map((r: string[], i: number) => <tr key={i}>{r.map((c, j) => <Td key={j} className={j === 0 ? "font-medium text-slate-800" : ""}>{c}</Td>)}</tr>)}</tbody>
            </table>
            </>
          )}
        </Card>
      </div>
    </>
  );
}
