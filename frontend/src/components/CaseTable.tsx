import { useNavigate } from "react-router-dom";
import { BureauChip, ConfidenceDot, SlaChip, StatusChip, Td, Th } from "./ui";
import { fmtDate } from "../api";

export default function CaseTable({ items }: { items: any[] }) {
  const nav = useNavigate();
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed border-collapse">
        <colgroup>
          <col className="w-[132px]" /><col /><col className="w-[120px]" /><col className="w-[120px]" /><col className="w-[96px]" />
          <col className="w-[120px]" /><col className="w-[120px]" /><col className="w-[124px]" />
        </colgroup>
        <thead><tr><Th>Case ID</Th><Th>Institution</Th><Th>Bureau</Th><Th>Category</Th><Th>Received</Th><Th>Status</Th><Th>Officer</Th><Th>SLA</Th></tr></thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id} onClick={() => nav(`/cases/${c.id}`)} className="hover:bg-slate-50 cursor-pointer">
              <Td className="font-medium text-navy whitespace-nowrap">{c.id}</Td>
              <Td>
                <div className="flex items-center gap-2 min-w-0">
                  <ConfidenceDot link={c.link} />
                  <div className="min-w-0">
                    <div className="truncate">{c.institution?.name ?? <span className="text-slate-400">Unresolved</span>}</div>
                    <div className="truncate text-xs text-slate-400">as written: {c.written}</div>
                  </div>
                </div>
              </Td>
              <Td><BureauChip name={c.bureau} /></Td>
              <Td className="truncate">{c.category}</Td>
              <Td className="whitespace-nowrap">{fmtDate(c.received_date)}</Td>
              <Td><StatusChip status={c.status} /></Td>
              <Td className="truncate">{c.officer}</Td>
              <Td><SlaChip sla={c.sla} /></Td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={8} className="text-center text-sm text-slate-400 py-12">No cases match these filters.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
