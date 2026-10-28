import { useEffect, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Clock, X } from "lucide-react";
import { Link } from "react-router-dom";

export const SEVERITY = {
  CONFLICTING: { fg: "#C62828", bg: "#FDE3E3" },
  DUPLICATE: { fg: "#C25E00", bg: "#FFEEDD" },
  RELATED: { fg: "#8A6D00", bg: "#FFF6CC" },
  INFO: { fg: "#555555", bg: "#EEEEEE" },
} as const;
export type Severity = keyof typeof SEVERITY;

export const BUREAU_COLOR: Record<string, string> = {
  PGRC: "#2F6FDE", RB: "#7B3FC4", Approval: "#0F9488", Academic: "#3C9A3C", "Regional Office": "#5B6B7F",
};
export const bureauColor = (b: string) => BUREAU_COLOR[b] ?? "#5B6B7F";

const STATUS_STYLE: Record<string, [string, string]> = {
  Received: ["#334155", "#E2E8F0"], "Under process": ["#1D4ED8", "#DBEAFE"], Pending: ["#92400E", "#FEF3C7"],
  Transferred: ["#6B21A8", "#F3E8FF"], Disposed: ["#166534", "#DCFCE7"], "Beyond timeline": ["#B91C1C", "#FEE2E2"],
};

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`bg-white border border-line rounded-xl shadow-card p-6 ${className}`}>{children}</section>;
}

export function SeverityChip({ level }: { level: string | null | undefined }) {
  if (!level) return <span className="text-xs text-slate-400">—</span>;
  const c = SEVERITY[level as Severity] ?? SEVERITY.INFO;
  return <span className="text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap" style={{ color: c.fg, background: c.bg }}>{level}</span>;
}

export function StatusChip({ status }: { status: string }) {
  const [fg, bg] = STATUS_STYLE[status] ?? STATUS_STYLE.Received;
  return <span className="text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap" style={{ color: fg, background: bg }}>{status}</span>;
}

export function BureauChip({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 whitespace-nowrap">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: bureauColor(name) }} />{name}
    </span>
  );
}

export function SlaChip({ sla }: { sla: { level: string; label: string } }) {
  const m: Record<string, [string, string]> = {
    ok: ["#166534", "#DCFCE7"], risk: ["#92400E", "#FEF3C7"], overdue: ["#B91C1C", "#FEE2E2"], done: ["#64748B", "#F1F5F9"],
  };
  const [fg, bg] = m[sla.level] ?? m.ok;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap" style={{ color: fg, background: bg }}>
      {sla.level !== "done" && <Clock size={12} />}{sla.label}
    </span>
  );
}

export function ConfidenceDot({ link }: { link: { status: string; confidence: number; suggested?: any } }) {
  const color = link.status === "unlinked" ? (link.suggested ? "#F59E0B" : "#94A3B8") : "#16A34A";
  const label = link.status === "unlinked" ? (link.suggested ? "Needs officer confirmation" : "Unlinked") : link.status === "confirmed" ? "Confirmed by officer" : "Auto-linked";
  return <span title={`${label} · confidence ${link.confidence.toFixed(2)}`} className="inline-block h-2.5 w-2.5 rounded-full shrink-0" style={{ background: color }} />;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-6 mb-6 shrink-0">
      <div>
        <h1 className="text-2xl font-semibold text-navy">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, hint }: { icon: LucideIcon; title: string; hint: string }) {
  return (
    <Card className="flex flex-col items-center justify-center text-center py-16">
      <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-4"><Icon size={22} className="text-navy" /></div>
      <div className="text-base font-semibold text-slate-800">{title}</div>
      <div className="text-sm text-slate-500 mt-1 max-w-md">{hint}</div>
    </Card>
  );
}

export function Loading({ what = "data" }: { what?: string }) {
  return <div className="text-sm text-slate-400 py-10 text-center">Loading {what}…</div>;
}

export function ErrorNote({ msg }: { msg: string }) {
  return <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">{msg}</div>;
}

export function Btn({ children, onClick, kind = "ghost", disabled, className = "", type = "button" }:
  { children: ReactNode; onClick?: () => void; kind?: "primary" | "ghost" | "danger" | "amber"; disabled?: boolean; className?: string; type?: "button" | "submit" }) {
  const k = {
    primary: "bg-navy text-white hover:bg-[#0f2747]", ghost: "bg-white text-slate-700 border border-line hover:bg-slate-50",
    danger: "bg-sev-conflict text-white hover:bg-red-800", amber: "bg-amber-ekatra text-navy font-semibold hover:brightness-95",
  }[kind];
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`h-10 px-4 rounded-lg text-sm font-medium whitespace-nowrap shrink-0 inline-flex items-center justify-center gap-2 transition disabled:opacity-40 disabled:cursor-not-allowed ${k} ${className}`}>
      {children}
    </button>
  );
}

export function Select({ value, onChange, options, placeholder, className = "" }:
  { value: string; onChange: (v: string) => void; options: (string | { value: string; label: string })[]; placeholder: string; className?: string }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className={`h-10 rounded-lg border border-line bg-white px-3 text-sm outline-none focus:border-navy ${className}`}>
      <option value="">{placeholder}</option>
      {options.map((o) => typeof o === "string" ? <option key={o}>{o}</option> : <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

export function Modal({ open, onClose, title, children, wide, tone }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean; tone?: "danger" }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-6" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}
        className={`bg-white rounded-2xl shadow-2xl w-full ${wide ? "max-w-2xl" : "max-w-lg"} max-h-[90vh] overflow-y-auto`}>
        <div className={`flex items-start justify-between gap-4 px-6 py-5 border-b ${tone === "danger" ? "bg-sev-conflictBg border-red-200 rounded-t-2xl" : "border-line"}`}>
          <h2 className={`text-lg font-semibold ${tone === "danger" ? "text-sev-conflict" : "text-navy"}`}>{title}</h2>
          <button onClick={onClose} aria-label="Close" className="text-slate-500 hover:text-slate-800"><X size={18} /></button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export function CaseLink({ id }: { id: string }) {
  return <Link to={`/cases/${id}`} className="font-medium text-navy hover:underline whitespace-nowrap">{id}</Link>;
}

export function Th({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <th className={`text-left text-xs font-semibold uppercase tracking-wide text-slate-500 px-3 py-3 border-b border-line bg-slate-50/60 ${className}`}>{children}</th>;
}
export function Td({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <td className={`px-3 py-3 text-sm border-b border-line align-middle ${className}`}>{children}</td>;
}

export function Bar({ value, color = "#14325C", max = 1 }: { value: number; color?: string; max?: number }) {
  return (
    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }} />
    </div>
  );
}
