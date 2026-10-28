import { Bar, Card } from "./ui";

const LABEL: Record<string, string> = {
  name: "Name similarity", acronym: "Acronym / exact name", location: "Location (pincode / city)", embedding: "Embedding similarity",
};
const DECISION: Record<string, string> = {
  auto: "Auto-linked (≥ 0.90)", confirm: "Officer confirms (0.60–0.89)", unlinked: "Unlinked (< 0.60)",
};

export default function WhyLinked({ why, linkStatus, caseId }: { why: any; linkStatus?: string; caseId?: string }) {
  if (!why?.factors) {
    return <Card><div className="text-sm text-slate-500">No automatic link explanation stored for this case.</div></Card>;
  }
  const decision = linkStatus === "confirmed" ? "Confirmed by an officer" : DECISION[why.decision] ?? why.decision;
  return (
    <Card className="!p-5">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <h3 className="text-base font-semibold text-navy">Why linked?</h3>
        {caseId && <span className="text-xs text-slate-500">{caseId}</span>}
      </div>
      <div className="flex items-center gap-2 mb-4 min-w-0">
        <span className="text-[11px] font-semibold rounded-full px-2.5 py-1 shrink-0"
          style={why.exact_id ? { background: "#DCFCE7", color: "#166534" } : why.note ? { background: "#DBEAFE", color: "#1D4ED8" } : { background: "#FFF6CC", color: "#8A6D00" }}>
          {why.exact_id ? "Exact ID" : why.note ? "Known alias" : `Fuzzy match (score ${Number(why.confidence).toFixed(2)})`}
        </span>
        <p className="text-xs text-slate-500 truncate" title={why.institution_name}>→ {why.institution_name}</p>
      </div>
      <div className="space-y-3">
        {Object.entries(why.factors).map(([k, f]: [string, any]) => (
          <div key={k}>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-700">{LABEL[k] ?? k} <span className="text-xs text-slate-400">× {f.weight}</span></span>
              <span className="font-semibold text-navy tabular-nums">{Math.round(f.value * 100)}%</span>
            </div>
            <Bar value={f.value} color={f.value >= 0.9 ? "#16A34A" : f.value >= 0.5 ? "#F5A623" : "#94A3B8"} />
            <div className="text-xs text-slate-500 mt-1">{f.detail}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-line flex items-center justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500">Confidence</div>
          <div className="text-2xl font-semibold text-navy tabular-nums">{Number(why.confidence).toFixed(2)}</div>
        </div>
        <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-right">{decision}</span>
      </div>
      {why.note && <div className="text-xs text-slate-500 mt-3">{why.note}</div>}
      {why.exact_id && <div className="text-xs text-slate-500 mt-3">Exact Permanent ID found in the complaint text.</div>}
    </Card>
  );
}
