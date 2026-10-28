import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertOctagon, Building2, FileText, Link2Off, Users } from "lucide-react";
import { api, useApi } from "../api";
import WhyLinked from "../components/WhyLinked";
import { Btn, BureauChip, Card, ErrorNote, Loading, Modal, Select, SeverityChip, StatusChip, Td, Th } from "../components/ui";
import { useMeta } from "../hooks";

export default function OverlapCentre() {
  const meta = useMeta();
  const [sp, setSp] = useSearchParams();
  const [q, setQ] = useState("");
  const [sev, setSev] = useState("");
  const list = useApi<any[]>(`/clusters${sev ? `?severity=${sev}` : ""}`);
  const selected = Number(sp.get("cluster")) || null;
  const items = (list.data ?? []).filter((c) => !q || c.institution.name.toLowerCase().includes(q.toLowerCase()) || c.case_ids.some((i: string) => i.toLowerCase().includes(q.toLowerCase())));
  const activeId = selected ?? items[0]?.id ?? null;
  const detail = useApi<any>(activeId ? `/clusters/${activeId}` : null, [activeId]);
  const [caseSel, setCaseSel] = useState<string | null>(null);
  const [modal, setModal] = useState<"lead" | "unlink" | "reply" | null>(null);
  const [leadSel, setLeadSel] = useState("");
  const [pair, setPair] = useState("");
  const [reason, setReason] = useState("");
  const [reply, setReply] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => { setCaseSel(null); }, [activeId]);

  const d = detail.data;
  const sel = d?.cases.find((x: any) => x.id === caseSel) ?? d?.cases.find((x: any) => x.why_linked?.decision) ?? d?.cases[0];
  const refresh = () => { list.reload(); detail.reload(); };

  const assignLead = async () => {
    const bureau_id = meta?.bureaus.find((b) => b.name === (leadSel || d.bureaus[0]))?.id;
    try { await api(`/clusters/${d.id}/lead`, { body: { bureau_id } }); setModal(null); refresh(); } catch (e: any) { setErr(e.message); }
  };
  const doUnlink = async () => {
    const [a, b] = pair.split("|");
    try { await api(`/clusters/${d.id}/unlink`, { body: { case_a: a, case_b: b, reason } }); setModal(null); setReason(""); refresh(); } catch (e: any) { setErr(e.message); }
  };
  const draft = async () => { const r = await api(`/clusters/${d.id}/joint-reply`, { method: "POST", body: {} }); setReply(r.text); setModal("reply"); };

  return (
    <>
      <div className="rounded-xl bg-sev-conflict text-white px-6 py-4 mb-6 flex items-center gap-3 shadow-card">
        <AlertOctagon size={22} />
        <div>
          <div className="text-lg font-semibold leading-tight">Potential Overlapping Cases – Coordination Required</div>
          <div className="text-sm text-white/80">Cases at the same institution handled by different Bureaus, graded by how likely they are to collide.</div>
        </div>
        <div className="ml-auto text-right text-sm text-white/90">{list.data ? `${list.data.length} clusters · ${list.data.filter((c) => c.severity === "CONFLICTING").length} conflicting` : ""}</div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-4 xl:col-span-3">
          <Card className="!p-4">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search institution or case ID" className="h-10 w-full rounded-lg border border-line px-3 text-sm outline-none focus:border-navy" />
            <Select value={sev} onChange={setSev} placeholder="All severities" options={["CONFLICTING", "DUPLICATE", "RELATED"]} className="w-full mt-2" />
            <ul className="mt-3 space-y-2 max-h-[62vh] overflow-y-auto pr-1">
              {list.loading && !list.data && <Loading what="clusters" />}
              {items.map((c) => (
                <li key={c.id}>
                  <button onClick={() => setSp({ cluster: String(c.id) })}
                    className={`w-full text-left rounded-lg border p-3 transition ${c.id === activeId ? "border-navy bg-slate-50 ring-1 ring-navy" : "border-line hover:bg-slate-50"}`}>
                    <div className="flex items-center justify-between gap-2"><SeverityChip level={c.severity} /><span className="text-xs text-slate-400">#{c.id}</span></div>
                    <div className="text-sm font-medium text-slate-800 mt-2 leading-snug">{c.institution.name}</div>
                    <div className="text-xs text-slate-500 mt-1">{c.case_count} cases · {c.bureaus.join(", ")}</div>
                    {c.lead_bureau && <div className="text-[11px] text-emerald-700 mt-1">Lead: {c.lead_bureau}</div>}
                  </button>
                </li>
              ))}
              {list.data && items.length === 0 && <li className="text-sm text-slate-400 text-center py-6">No clusters match.</li>}
            </ul>
          </Card>
        </div>

        <div className="col-span-8 xl:col-span-9 space-y-5">
          {detail.error && <ErrorNote msg={detail.error} />}
          {!d && !detail.error && <Loading what="cluster" />}
          {d && (
            <>
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3"><h2 className="text-xl font-semibold text-navy">{d.institution_full.name}</h2><SeverityChip level={d.severity} /></div>
                    <div className="text-sm text-slate-500 mt-1">{d.institution_full.permanent_id} · {d.institution_full.city}, {d.institution_full.state} · pincode {d.institution_full.pincode}</div>
                    <div className="flex items-center gap-4 text-sm text-slate-600 mt-2">
                      <span className="inline-flex items-center gap-1.5"><Users size={14} />{d.bureaus.join(" · ")}</span>
                      {d.lead_bureau ? <span className="text-emerald-700 font-medium">Lead Bureau: {d.lead_bureau}</span> : <span className="text-amber-700">No Lead Bureau yet</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Btn kind="primary" onClick={() => { setModal("lead"); setLeadSel(d.lead_bureau ?? d.bureaus[0]); setErr(""); }}>Assign Lead Bureau</Btn>
                    <Btn onClick={() => { setModal("unlink"); setPair(`${d.pairs[0]?.a}|${d.pairs[0]?.b}`); setErr(""); }}><Link2Off size={15} />Unlink (record reason)</Btn>
                    <Btn onClick={draft}><FileText size={15} />Draft joint reply</Btn>
                    <Link to={`/institutions/${d.institution.id}`}><Btn><Building2 size={15} />Institution 360°</Btn></Link>
                  </div>
                </div>
              </Card>
              <Card className="!p-0 overflow-hidden">
                <table className="w-full table-fixed border-collapse">
                  <colgroup><col className="w-[128px]" /><col className="w-[112px]" /><col className="w-[22%]" /><col /><col className="w-[112px]" /><col className="w-[132px]" /></colgroup>
                  <thead><tr><Th>Case ID</Th><Th>Bureau</Th><Th>Name as written</Th><Th>Issue</Th><Th>Status</Th><Th>Severity</Th></tr></thead>
                  <tbody>
                    {d.cases.map((c: any) => (
                      <tr key={c.id} onClick={() => setCaseSel(c.id)} className={`cursor-pointer hover:bg-slate-50 ${sel?.id === c.id ? "bg-slate-50" : ""}`}>
                        <Td className="font-medium text-navy whitespace-nowrap"><Link to={`/cases/${c.id}`} onClick={(e) => e.stopPropagation()} className="hover:underline">{c.id}</Link></Td>
                        <Td><BureauChip name={c.bureau} /></Td>
                        <Td className="text-slate-700 text-[13px]"><div className="line-clamp-3 break-words">{c.written}</div></Td>
                        <Td className="text-slate-600 text-[13px]"><div className="line-clamp-3" title={c.issue}>{c.issue}</div></Td>
                        <Td><StatusChip status={c.status} /></Td>
                        <Td><SeverityChip level={c.severity} /></Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <div className="grid grid-cols-12 gap-5 items-start">
                <div className="col-span-7">
                  {sel && <WhyLinked why={sel.why_linked} linkStatus={sel.link.status} caseId={sel.id} />}
                  <p className="text-xs text-slate-400 mt-2 px-1">Showing {sel?.id}. Click another row to compare how each case was linked.</p>
                </div>
              <Card className="col-span-5 !p-5">
                  <h3 className="text-base font-semibold text-navy mb-3">Why these cases overlap</h3>
                  <ul className="space-y-3">
                    {d.pairs.map((p: any, i: number) => (
                      <li key={i} className="text-sm">
                        <div className="flex items-center gap-2 flex-wrap"><SeverityChip level={p.severity} /><span className="text-xs text-slate-500">{p.a} ↔ {p.b}</span></div>
                        <div className="text-xs text-slate-600 mt-1">{p.reason} <span className="text-slate-400">· issue similarity {p.similarity.toFixed(2)}</span></div>
                      </li>
                    ))}
                  </ul>
                  {d.info_cases.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-line">
                      <div className="text-xs font-semibold text-slate-500 mb-2">Also open at this institution <SeverityChip level="INFO" /></div>
                      {d.info_cases.map((c: any) => <div key={c.id} className="text-xs text-slate-600"><Link to={`/cases/${c.id}`} className="text-navy font-medium hover:underline">{c.id}</Link> · {c.bureau} · {c.category}</div>)}
                    </div>
                  )}
                </Card>
              </div>
            </>
          )}
        </div>
      </div>

      <Modal open={modal === "lead"} onClose={() => setModal(null)} title="Assign Lead Bureau">
        <p className="text-sm text-slate-600 mb-3">The Lead Bureau coordinates the response. Other Bureaus stay paused on conflicting actions until they coordinate or record a reason.</p>
        <Select value={leadSel} onChange={setLeadSel} placeholder="Choose Bureau" options={d?.bureaus ?? []} className="w-full" />
        {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
        <div className="flex gap-3 mt-5"><Btn kind="primary" onClick={assignLead}>Assign</Btn><Btn onClick={() => setModal(null)}>Cancel</Btn></div>
      </Modal>
      <Modal open={modal === "unlink"} onClose={() => setModal(null)} title="Unlink cases (officer decision)">
        <p className="text-sm text-slate-600 mb-3">Use when the automatic link is wrong. The decision is logged with your reason and the pair will not be re-linked.</p>
        <Select value={pair} onChange={setPair} placeholder="Pair" options={(d?.pairs ?? []).map((p: any) => ({ value: `${p.a}|${p.b}`, label: `${p.a} ↔ ${p.b}` }))} className="w-full" />
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} placeholder="Reason (min. 10 characters)" className="mt-3 w-full rounded-lg border border-line p-3 text-sm outline-none focus:border-navy" />
        {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
        <div className="flex gap-3 mt-5"><Btn kind="danger" disabled={reason.trim().length < 10} onClick={doUnlink}>Unlink</Btn><Btn onClick={() => setModal(null)}>Cancel</Btn></div>
      </Modal>
      <Modal open={modal === "reply"} onClose={() => setModal(null)} title="Draft joint reply" wide>
        <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 rounded-lg p-4 font-sans">{reply}</pre>
        <div className="flex gap-3 mt-4"><Btn onClick={() => navigator.clipboard?.writeText(reply)}>Copy</Btn><Btn onClick={() => setModal(null)}>Close</Btn></div>
      </Modal>
    </>
  );
}
