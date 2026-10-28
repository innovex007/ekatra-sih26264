import { useSearchParams } from "react-router-dom";
import { useApi } from "../api";
import CaseTable from "../components/CaseTable";
import { Btn, Card, ErrorNote, Loading, PageHeader, Select } from "../components/ui";
import { useMeta } from "../hooks";

const PAGE = 25;

export default function CaseTracker() {
  const meta = useMeta();
  const [sp, setSp] = useSearchParams();
  const get = (k: string) => sp.get(k) ?? "";
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); if (k !== "page") n.delete("page"); setSp(n, { replace: true }); };
  const page = Number(get("page") || 0);
  const qs = new URLSearchParams({ q: get("q"), bureau: get("bureau"), status: get("status"), region: get("region"), category: get("category"),
    date_from: get("date_from"), date_to: get("date_to"), needs_confirm: get("needs_confirm") ? "true" : "", sort: get("sort") || "sla",
    limit: String(PAGE), offset: String(page * PAGE) });
  [...qs.keys()].forEach((k) => !qs.get(k) && qs.delete(k));
  const { data, loading, error } = useApi<any>(`/cases?${qs}`);

  return (
    <>
      <PageHeader title="Case Tracker" subtitle="Every complaint case across Bureaus, resolved to one institution record." />
      <Card className="!p-5 mb-5">
        <div className="flex flex-wrap gap-3 items-center">
          <input value={get("q")} onChange={(e) => set("q", e.target.value)} placeholder="Search case ID, institution, Permanent ID"
            className="h-10 w-72 rounded-lg border border-line px-3 text-sm outline-none focus:border-navy" />
          <Select value={get("bureau")} onChange={(v) => set("bureau", v)} placeholder="All Bureaus" options={meta?.bureaus.map((b) => b.name) ?? []} />
          <Select value={get("status")} onChange={(v) => set("status", v)} placeholder="All statuses" options={meta?.statuses ?? []} />
          <Select value={get("region")} onChange={(v) => set("region", v)} placeholder="All regions" options={meta?.regions ?? []} />
          <Select value={get("category")} onChange={(v) => set("category", v)} placeholder="All categories" options={meta?.categories ?? []} />
          <input type="date" value={get("date_from")} onChange={(e) => set("date_from", e.target.value)} title="Received from" className="h-10 rounded-lg border border-line px-2 text-sm" />
          <input type="date" value={get("date_to")} onChange={(e) => set("date_to", e.target.value)} title="Received to" className="h-10 rounded-lg border border-line px-2 text-sm" />
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={!!get("needs_confirm")} onChange={(e) => set("needs_confirm", e.target.checked ? "1" : "")} /> Needs link confirmation
          </label>
          <Select value={get("sort") || "sla"} onChange={(v) => set("sort", v)} placeholder="Sort" options={[{ value: "sla", label: "Sorted by SLA risk" }, { value: "received", label: "Sorted by newest" }]} />
          {[...sp.keys()].length > 0 && <Btn onClick={() => setSp({}, { replace: true })}>Clear</Btn>}
        </div>
      </Card>
      <Card className="!p-0 overflow-hidden">
        {error ? <div className="p-6"><ErrorNote msg={error} /></div> : loading && !data ? <Loading what="cases" /> : (
          <>
            <CaseTable items={data.items} />
            <div className="flex items-center justify-between px-5 py-3 text-sm text-slate-500 border-t border-line">
              <span>{data.total.toLocaleString()} cases · showing {page * PAGE + 1}–{Math.min((page + 1) * PAGE, data.total)}</span>
              <span className="flex gap-2">
                <Btn disabled={page === 0} onClick={() => set("page", String(page - 1))}>Previous</Btn>
                <Btn disabled={(page + 1) * PAGE >= data.total} onClick={() => set("page", String(page + 1))}>Next</Btn>
              </span>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
