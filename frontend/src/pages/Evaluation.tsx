import { FlaskConical } from "lucide-react";
import { useApi } from "../api";
import { Card, EmptyState, ErrorNote, Loading, PageHeader, SeverityChip, Td, Th } from "../components/ui";

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "good" | "warn" }) {
  return (
    <Card className="!p-5">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-3xl font-semibold mt-1 tabular-nums ${tone === "warn" ? "text-sev-duplicate" : "text-navy"}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </Card>
  );
}

export default function Evaluation() {
  const { data: r, loading, error } = useApi<any>("/eval/results");
  if (error) return <ErrorNote msg={error} />;
  if (loading || !r) return <Loading what="evaluation" />;
  if (!r.available) return <><PageHeader title="Evaluation" subtitle="Measured on synthetic data." /><EmptyState icon={FlaskConical} title="No results yet" hint="Run: backend\.venv\Scripts\python.exe eval\evaluate.py" /></>;
  const rs = r.resolver, o = r.overlaps, s = r.severity, il = r.interlock;
  const labels = ["CONFLICTING", "DUPLICATE", "RELATED", "INFO"];
  const cols = [...labels, "MISSED"];
  return (
    <>
      <PageHeader title="Evaluation" subtitle={`Measured on synthetic data · ${r.dataset.cases.toLocaleString()} original cases${r.v2 ? ` + ${r.v2.cases_added} planted for the finalist features` : ""} · name matching: ${r.resolver_method}`} />
      <div className="grid grid-cols-4 gap-5 mb-5">
        <Stat label="Resolver precision (auto-links)" value={`${rs.all.precision}%`} sub={`${rs.all.correct_auto.toLocaleString()} of ${rs.all.auto_linked.toLocaleString()} auto-links correct`} />
        <Stat label="Resolver recall (auto-linked)" value={`${rs.all.recall}%`} sub={`${rs.all.needs_confirmation} more wait for one-click officer confirmation`} />
        <Stat label="More true overlaps than exact-ID" value={`${o.multiplier}×`} sub={`${o.ekatra_found.toLocaleString()} vs ${o.exact_id_found.toLocaleString()} cross-Bureau pairs`} />
        <Stat label="Conflicts blocked" value={`${il.blocked} / ${il.attempts}`} sub={`${il.false_triggers} false triggers on ${il.control_cases} control cases`} />
      </div>
      <div className="grid grid-cols-12 gap-5 mb-5">
        <Card className="col-span-7 !p-0 overflow-hidden">
          <div className="px-5 pt-5 pb-3 text-base font-semibold text-navy">Resolver accuracy by name type</div>
          <table className="w-full border-collapse">
            <thead><tr><Th>Subset</Th><Th>Cases</Th><Th>Precision</Th><Th>Recall</Th><Th>Top-1 after confirmation</Th></tr></thead>
            <tbody>
              {[["all", "All cases"], ["clean", "Clean names"], ["messy", "Messy names (acronym, typo, old, abbreviated, Hindi…)"], ["hindi", "Hindi (Devanagari) script"]].map(([k, l]) => (
                <tr key={k}><Td>{l}</Td><Td>{rs[k].n}</Td><Td className="font-semibold text-navy">{rs[k].precision}%</Td><Td className="font-semibold text-navy">{rs[k].recall}%</Td><Td>{rs[k].top1_with_confirmation}%</Td></tr>
              ))}
            </tbody>
          </table>
        </Card>
        <div className="col-span-5 grid gap-5 content-start">
          <Stat label="False links per 1,000 cases" value={String(r.false_links_per_1000)} sub={`${r.wrong_auto_links} auto-links to the wrong institution`} />
          <div className="grid grid-cols-2 gap-5">
            <Stat label="Dashboard API p95" value={`${r.latency.dashboard_p95_ms} ms`} sub={`${r.latency.n_cases.toLocaleString()} cases`} />
            <Stat label="Institution 360° API" value={`${r.institution_360.api_median_ms} ms`} sub="median, whole picture" />
          </div>
        </div>
      </div>
      <Card className="!p-0 overflow-hidden mb-5">
        <div className="px-5 pt-5 pb-3"><div className="text-base font-semibold text-navy">Severity on {s.pairs} planted pairs</div>
          <div className="text-xs text-slate-500">Classifier alone: {s.classifier_accuracy}% · end to end including name linking: {s.end_to_end_accuracy}%. “MISSED” = a case in the pair was not auto-linked.</div></div>
        <table className="w-full border-collapse">
          <thead><tr><Th>True ↓ / predicted →</Th>{cols.map((c) => <Th key={c}>{c === "MISSED" ? "Missed" : <SeverityChip level={c} />}</Th>)}</tr></thead>
          <tbody>
            {labels.map((l) => (
              <tr key={l}><Td><SeverityChip level={l} /></Td>{cols.map((c) => { const n = s.confusion_end_to_end[l]?.[c] ?? 0; return <Td key={c} className={n ? (c === l ? "font-semibold text-emerald-700" : "font-semibold text-sev-conflict") : "text-slate-300"}>{n}</Td>; })}</tr>
            ))}
          </tbody>
        </table>
      </Card>
      {r.v2 && (
        <>
          <h2 className="text-base font-semibold text-navy mt-8 mb-3">Finalist features (planted on new institutions; excluded from the numbers above)</h2>
          <div className="grid grid-cols-3 gap-5 mb-5">
            <Stat label="Systemic problems found" value={`${r.v2.systemic.found} / ${r.v2.systemic.planted}`} sub={`${r.v2.systemic.decoys_flagged} of ${r.v2.systemic.decoys} decoys flagged · ${r.v2.systemic.other_institutions_flagged} other heavily-complained institutions also meet the rule`} />
            <Stat label="Contradictions found" value={`${r.v2.contradictions.found} / ${r.v2.contradictions.planted}`} sub={`${r.v2.contradictions.controls_flagged} of ${r.v2.contradictions.controls} controls flagged · ${r.v2.contradictions.missed_due_to_unlinked_case} miss(es) had a case not yet auto-linked`} />
            <Stat label="Risk DNA trend correct" value={`${r.v2.riskdna.correct.worsening + r.v2.riskdna.correct.improving + r.v2.riskdna.correct.stable} / ${r.v2.riskdna.planted.worsening + r.v2.riskdna.planted.improving + r.v2.riskdna.planted.stable}`} sub={`worsening ${r.v2.riskdna.correct.worsening}/${r.v2.riskdna.planted.worsening} · improving ${r.v2.riskdna.correct.improving}/${r.v2.riskdna.planted.improving} · stable ${r.v2.riskdna.correct.stable}/${r.v2.riskdna.planted.stable}`} />
          </div>
        </>
      )}
      <p className="text-xs text-slate-400">Time to a full institution picture: Ekatra builds it in {r.institution_360.api_median_ms} ms (API). Manual baseline: {r.institution_360.manual_baseline}. Generated {r.generated}.</p>
    </>
  );
}
