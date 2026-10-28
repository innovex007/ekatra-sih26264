import { useState } from "react";
import { ShieldCheck, ShieldX } from "lucide-react";
import { api, fmtTime, useApi } from "../api";
import { Btn, Card, ErrorNote, Loading, PageHeader, Td, Th } from "../components/ui";
import { clearMetaCache, useMeta } from "../hooks";

export default function Audit() {
  const [page, setPage] = useState(0);
  const { data, loading, error, reload } = useApi<any>(`/audit?limit=50&offset=${page * 50}`, [page]);
  const [v, setV] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const meta = useMeta();
  const [mode, setMode] = useState<string | null>(null);
  const cur = mode ?? meta?.interlock_mode ?? "block";
  const verify = async () => { setBusy(true); try { setV(await api("/audit/verify", { method: "POST", body: {} })); } finally { setBusy(false); } };
  const setInterlock = async (m: string) => { await api("/settings", { method: "PUT", body: { interlock_mode: m } }); clearMetaCache(); setMode(m); reload(); };

  return (
    <>
      <PageHeader title="Audit log" subtitle="Every action, override and link decision is chained by SHA-256, so edits after the fact are detectable."
        actions={<Btn kind="primary" onClick={verify} disabled={busy}><ShieldCheck size={16} />Verify integrity</Btn>} />
      {v && (
        <div className={`mb-5 rounded-xl px-5 py-4 flex items-center gap-3 text-sm font-medium ${v.intact ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
          {v.intact ? <ShieldCheck size={20} /> : <ShieldX size={20} />}
          {v.intact ? `Chain intact – ${v.events.toLocaleString()} events` : `Chain broken at event #${v.broken_at}`}
        </div>
      )}
      <Card className="mb-5 !p-5 flex items-center gap-6">
        <div><div className="text-sm font-semibold text-navy">Interlock mode</div><div className="text-xs text-slate-500">Block pauses conflicting actions; warn-only (pilot) lets them proceed and logs a warning.</div></div>
        <div className="ml-auto inline-flex rounded-lg border border-line overflow-hidden">
          {[["block", "Block"], ["warn", "Warn-only (pilot)"]].map(([k, l]) => (
            <button key={k} onClick={() => setInterlock(k)} className={`h-10 px-4 text-sm ${cur === k ? "bg-navy text-white" : "bg-white text-slate-700 hover:bg-slate-50"}`}>{l}</button>
          ))}
        </div>
      </Card>
      {error && <ErrorNote msg={error} />}
      <Card className="!p-0 overflow-hidden">
        {loading && !data ? <Loading what="audit events" /> : data && (
          <>
            <table className="w-full table-fixed border-collapse">
              <colgroup><col className="w-[70px]" /><col className="w-[120px]" /><col className="w-[170px]" /><col className="w-[190px]" /><col className="w-[150px]" /><col /><col className="w-[110px]" /></colgroup>
              <thead><tr><Th>#</Th><Th>Time</Th><Th>Actor</Th><Th>Action</Th><Th>Entity</Th><Th>Detail</Th><Th>Hash</Th></tr></thead>
              <tbody>
                {data.items.map((e: any) => (
                  <tr key={e.id}>
                    <Td className="text-slate-400">{e.id}</Td><Td className="whitespace-nowrap">{fmtTime(e.ts)}</Td><Td className="truncate">{e.actor}</Td>
                    <Td><span className={`text-xs font-medium rounded px-2 py-1 ${e.action.startsWith("interlock") ? "bg-sev-conflictBg text-sev-conflict" : "bg-slate-100 text-slate-700"}`}>{e.action}</span></Td>
                    <Td className="truncate font-medium text-navy">{e.entity}</Td>
                    <Td className="truncate text-xs text-slate-500" >{Object.entries(e.payload).map(([k, x]) => `${k}: ${Array.isArray(x) ? x.join(", ") : x}`).join(" · ")}</Td>
                    <Td className="font-mono text-[11px] text-slate-400">{e.hash}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between px-5 py-3 text-sm text-slate-500 border-t border-line">
              <span>{data.total.toLocaleString()} events · newest first</span>
              <span className="flex gap-2"><Btn disabled={page === 0} onClick={() => setPage(page - 1)}>Newer</Btn><Btn disabled={(page + 1) * 50 >= data.total} onClick={() => setPage(page + 1)}>Older</Btn></span>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
