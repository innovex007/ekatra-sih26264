import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, ShieldCheck, ShieldX } from "lucide-react";
import { api, ApiError, fmtDate, fmtTime, useApi } from "../api";
import InterlockModal, { type InterlockPayload } from "../components/InterlockModal";
import WhyLinked from "../components/WhyLinked";
import { Btn, BureauChip, Card, ErrorNote, Loading, Modal, Select, SeverityChip, SlaChip, StatusChip, bureauColor, ConfidenceDot } from "../components/ui";
import { useMeta } from "../hooks";

const ACTIONS: { key: string; label: string; kind?: "danger" | "primary" }[] = [
  { key: "remark", label: "Add remark" }, { key: "inspection", label: "Inspection" }, { key: "transfer", label: "Transfer" }, { key: "show_cause", label: "Show-cause" }, { key: "dispose", label: "Dispose", kind: "danger" },
];
const VERB: Record<string, string> = { create: "Case created", remark: "Remark", transfer: "Transferred", show_cause: "Show-cause issued", inspection: "Inspection", dispose: "Disposed", escalate: "Escalated", reopen: "Reopened" };

export default function CaseDetail() {
  const id = useParams()["*"] || "PGRC/2026/0457";
  const { data: c, loading, error, reload } = useApi<any>(`/cases/${id}`);
  const meta = useMeta();
  const [action, setAction] = useState<string | null>(null);
  const [remarks, setRemarks] = useState("");
  const [toBureau, setToBureau] = useState("");
  const [fTopic, setFTopic] = useState("");
  const [fVerdict, setFVerdict] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<InterlockPayload | null>(null);
  const [toast, setToast] = useState("");

  if (error) return <ErrorNote msg={error} />;
  if (loading && !c) return <Loading what="case" />;
  if (!c) return null;

  const done = (msg: string) => { setToast(msg); setBlocked(null); setAction(null); setRemarks(""); setFTopic(""); setFVerdict(""); reload(); setTimeout(() => setToast(""), 5000); };
  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const to = meta?.bureaus.find((b) => b.name === toBureau)?.id;
      await api(`/cases/${id}/actions`, { body: { action, remarks, to_bureau_id: to, finding_topic: fTopic || undefined, finding_verdict: fVerdict || undefined } });
      done(`${VERB[action!] ?? action} recorded.`);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 409) { setAction(null); setBlocked(e.detail); } else setErr(e.message);
    } finally { setBusy(false); }
  };
  const confirmLink = async () => { await api(`/cases/${id}/confirm-link`, { body: { institution_id: c.link.suggested.id } }); done("Link confirmed; alias learned."); };

  return (
    <div className="space-y-5">
      {toast && <div className="fixed top-12 right-8 z-40 bg-emerald-600 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2"><CheckCircle2 size={16} />{toast}</div>}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-navy">{c.id}</h1><StatusChip status={c.status} /><SlaChip sla={c.sla} />
              {c.severity && <SeverityChip level={c.severity} />}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600">
              <BureauChip name={c.bureau} /><span>{c.category}</span><span>via {c.source}</span><span>Received {fmtDate(c.received_date)}</span>
              <span>Due {c.due_date ? fmtDate(c.due_date) : "—"}</span><span>Officer: {c.officer}</span>
              <span title="Complainant identity is masked for other Bureaus">Complainant: {c.complainant}</span>
            </div>
          </div>
          <div className="flex gap-2">
            {ACTIONS.map((a) => (
              <Btn key={a.key} kind={a.kind === "danger" ? "danger" : "ghost"} disabled={c.status === "Disposed" && a.key !== "remark"}
                onClick={() => { setAction(a.key); setErr(""); }}>{a.label}</Btn>
            ))}
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-700 max-w-4xl">{c.description}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm bg-slate-50 rounded-lg px-4 py-3">
          <ConfidenceDot link={c.link} />
          <span className="text-slate-500">Institution:</span>
          {c.institution ? <Link className="font-medium text-navy hover:underline" to={`/institutions/${c.institution.id}`}>{c.institution.name}</Link> : <span className="text-slate-400">Unresolved</span>}
          {c.institution && <span className="text-xs text-slate-400">{c.institution.permanent_id} · {c.institution.city}</span>}
          <span className="text-slate-400">· as written: “{c.written}”</span>
          {c.link.suggested && (
            <span className="ml-auto flex items-center gap-3">
              <span className="text-amber-700">Suggested: <b>{c.link.suggested.name}</b> ({Math.round(c.link.confidence * 100)}%)</span>
              <Btn kind="amber" onClick={confirmLink}>Confirm link</Btn>
            </span>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-7">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-navy">Timeline</h2>
            <span className={`text-xs font-medium inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${c.chain_intact ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
              {c.chain_intact ? <ShieldCheck size={14} /> : <ShieldX size={14} />} {c.chain_intact ? "Hash chain intact" : "Chain broken"}
            </span>
          </div>
          <ol className="relative border-l-2 border-slate-100 ml-2 space-y-5">
            {c.timeline.map((t: any) => (
              <li key={t.id} className="pl-6 relative">
                <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-white" style={{ background: bureauColor(t.bureau) }} />
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-slate-800">{VERB[t.action] ?? t.action}</span><BureauChip name={t.bureau} />
                  <span className="text-xs text-slate-400">{fmtTime(t.ts)} · {t.actor}</span>
                </div>
                {t.remarks && <div className="text-sm text-slate-600 mt-0.5">{t.remarks}</div>}
                {t.finding && (
                  <span className={`inline-block mt-1 text-xs font-medium rounded-full px-2.5 py-0.5 ${t.finding.verdict === "non-compliant" ? "bg-sev-conflictBg text-sev-conflict" : t.finding.verdict === "compliant" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                    Finding · {t.finding.topic}: {t.finding.verdict}
                  </span>
                )}
                <div className="text-[10px] font-mono text-slate-300 mt-0.5">#{t.hash} ← {t.prev_hash}</div>
              </li>
            ))}
          </ol>
          {c.transfer_chain.length > 0 && (
            <div className="mt-5 rounded-lg bg-amber-50 text-amber-900 text-xs p-3">Transferred {c.transfer_count} times{c.transfer_count >= 3 ? " – ping-pong alert raised to senior management" : ""}.</div>
          )}
        </Card>
        <div className="col-span-5 space-y-5">
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-navy">Linked cases</h2>
              {c.cluster && <Link className="text-xs text-navy hover:underline" to={`/overlaps?cluster=${c.cluster.id}`}>Open in Overlap Centre →</Link>}
            </div>
            {c.cluster?.lead_bureau && <div className="text-xs bg-emerald-50 text-emerald-700 rounded-lg px-3 py-2 mb-3">Lead Bureau: <b>{c.cluster.lead_bureau}</b></div>}
            {c.linked_cases.length === 0 && <div className="text-sm text-slate-500">No overlapping cases at this institution.</div>}
            <ul className="space-y-3">
              {c.linked_cases.map((l: any) => (
                <li key={l.id} className="rounded-lg border border-line p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Link to={`/cases/${l.id}`} className="font-medium text-navy hover:underline">{l.id}</Link><SeverityChip level={l.link_severity} /><BureauChip name={l.bureau} />
                  </div>
                  <div className="text-xs text-slate-500 mt-1.5">{l.link_reason}</div>
                </li>
              ))}
              {c.info_cases.map((l: any) => (
                <li key={l.id} className="rounded-lg border border-dashed border-line p-3">
                  <div className="flex items-center gap-2 text-sm"><Link to={`/cases/${l.id}`} className="font-medium text-navy hover:underline">{l.id}</Link><SeverityChip level="INFO" /><BureauChip name={l.bureau} /></div>
                  <div className="text-xs text-slate-500 mt-1.5">Same institution, unrelated issue ({l.category}).</div>
                </li>
              ))}
            </ul>
          </Card>
          <WhyLinked why={c.why_linked} linkStatus={c.link.status} caseId={c.id} />
        </div>
      </div>

      <Modal open={!!action} onClose={() => setAction(null)} title={`${ACTIONS.find((a) => a.key === action)?.label ?? ""} · ${c.id}`}>
        {action === "transfer" && (
          <div className="mb-4"><div className="text-sm font-medium mb-1.5">Transfer to</div>
            <Select value={toBureau} onChange={setToBureau} placeholder="Choose Bureau" options={(meta?.bureaus ?? []).map((b) => b.name).filter((n) => n !== c.bureau)} className="w-full" /></div>
        )}
        <label className="text-sm font-medium">Remarks</label>
        <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={3} className="mt-1.5 w-full rounded-lg border border-line p-3 text-sm outline-none focus:border-navy"
          placeholder={action === "dispose" ? "Basis for disposal" : action === "show_cause" ? "Show-cause particulars" : "Remarks for the record"} />
        {["inspection", "show_cause", "dispose"].includes(action ?? "") && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3">
            <div className="text-sm font-medium mb-2">Finding <span className="font-normal text-slate-400">(optional – feeds the contradiction check across Bureaus)</span></div>
            <div className="flex gap-3">
              <Select value={fTopic} onChange={setFTopic} placeholder="Topic" options={meta?.finding_topics ?? []} className="flex-1" />
              <Select value={fVerdict} onChange={setFVerdict} placeholder="Verdict" options={meta?.finding_verdicts ?? []} className="flex-1" />
            </div>
          </div>
        )}
        {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
        {(action === "dispose" || action === "show_cause") && <p className="text-xs text-slate-500 mt-2">This action is checked against linked cases at the same institution before it is applied.</p>}
        <div className="flex gap-3 mt-5">
          <Btn kind={action === "dispose" ? "danger" : "primary"} disabled={busy || (action === "transfer" && !toBureau) || (!!fTopic !== !!fVerdict)} onClick={submit}>Confirm {ACTIONS.find((a) => a.key === action)?.label}</Btn>
          <Btn onClick={() => setAction(null)}>Cancel</Btn>
        </div>
      </Modal>
      <InterlockModal payload={blocked} ownBureau={c.bureau} onClose={() => setBlocked(null)} onDone={done} />
    </div>
  );
}
