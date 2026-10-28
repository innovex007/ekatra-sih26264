import { useState } from "react";
import { Link } from "react-router-dom";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { useApi } from "../api";
import { Card, ErrorNote, Loading, PageHeader } from "../components/ui";

const TREND = {
  worsening: { label: "Worsening", color: "#C62828", bg: "#FDE3E3", Icon: TrendingUp },
  stable: { label: "Stable", color: "#555555", bg: "#EEEEEE", Icon: Minus },
  improving: { label: "Improving", color: "#166534", bg: "#DCFCE7", Icon: TrendingDown },
} as const;

function Spark({ values, color }: { values: number[]; color: string }) {
  const w = 72, h = 28, max = Math.max(1, ...values);
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * (w - 6) + 3},${h - 3 - (v / max) * (h - 8)}`);
  return (
    <svg className="shrink-0" width={w} height={h} role="img" aria-label={`New cases per month, oldest to newest: ${values.join(", ")}`}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r="3" fill={color} />
    </svg>
  );
}

export default function Watchlist() {
  const [sort, setSort] = useState("trend");
  const { data, loading, error } = useApi<any[]>(`/watchlist?sort=${sort}`, [sort]);
  return (
    <>
      <PageHeader title="Watchlist · Institutional Risk DNA" subtitle="Six-month trend, repeat categories, unresolved share and conflicts for each institution."
        actions={
          <div className="inline-flex rounded-lg border border-line overflow-hidden shrink-0">
            {[["trend", "Worsening first"], ["score", "Highest score"]].map(([k, l]) => (
              <button key={k} onClick={() => setSort(k)} className={`h-10 px-4 text-sm ${sort === k ? "bg-navy text-white" : "bg-white text-slate-700 hover:bg-slate-50"}`}>{l}</button>
            ))}
          </div>} />
      {error && <ErrorNote msg={error} />}
      {loading && !data && <Loading what="watchlist" />}
      <Card className="!p-0 overflow-hidden">
        <div className="grid grid-cols-[28px_minmax(0,1fr)_186px_64px_80px_72px_56px] gap-4 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 bg-slate-50/60 border-b border-line">
          <span>#</span><span>Institution</span><span>6-month trend</span><span>Repeat cat.</span><span>Unresolved</span><span>Conflicts</span><span className="text-right">Score</span>
        </div>
        {data?.map((w, i) => {
          const t = TREND[w.dna.trend as keyof typeof TREND];
          return (
            <Link key={w.institution.id} to={`/institutions/${w.institution.id}`}
              className="grid grid-cols-[28px_minmax(0,1fr)_186px_64px_80px_72px_56px] gap-4 items-center px-5 py-3 border-b border-line last:border-0 hover:bg-slate-50">
              <span className="text-sm text-slate-400 tabular-nums">{i + 1}</span>
              <div className="min-w-0"><div className="text-sm font-medium text-slate-800 truncate">{w.institution.name}</div>
                <div className="text-xs text-slate-500 truncate">{w.institution.city} · {w.raw.open} open · {w.raw.bureaus} Bureaus · {w.raw.overdue} beyond timeline</div></div>
              <div className="flex items-center gap-2">
                <Spark values={w.dna.load} color={t.color} />
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold rounded-full px-2 py-0.5" style={{ color: t.color, background: t.bg }}><t.Icon size={11} />{t.label}</span>
              </div>
              <span className="text-sm tabular-nums text-slate-700">{w.dna.repeat_categories}</span>
              <span className="text-sm tabular-nums text-slate-700">{Math.round(w.dna.unresolved_ratio * 100)}%</span>
              <span className={`text-sm tabular-nums ${w.dna.conflicts ? "text-sev-conflict font-semibold" : "text-slate-400"}`}>{w.dna.conflicts}</span>
              <span className="text-right text-lg font-semibold text-navy tabular-nums">{w.score}</span>
            </Link>
          );
        })}
      </Card>
      <p className="text-xs text-slate-400 mt-3">Trend compares weighted new-case load in the last 3 months with the 3 before (category weight, plus extra for cases in a conflicting or duplicate link). Sparkline = that weighted load per month, oldest to newest; a trend must also exceed normal month-to-month noise.</p>
    </>
  );
}
