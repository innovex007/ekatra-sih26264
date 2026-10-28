import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "../api";

export const ROLES = ["PGRC officer", "RB officer", "Bureau head", "Senior management"] as const;
export type Role = (typeof ROLES)[number];

export default function TopBar({ role, onRole }: { role: Role; onRole: (r: Role) => void }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any>(null);
  const nav = useNavigate();
  useEffect(() => {
    if (q.trim().length < 2) { setRes(null); return; }
    const t = setTimeout(() => api("/search?q=" + encodeURIComponent(q)).then(setRes).catch(() => setRes(null)), 200);
    return () => clearTimeout(t);
  }, [q]);
  const go = (path: string) => { setQ(""); setRes(null); nav(path); };

  return (
    <header className="h-16 shrink-0 bg-white border-b border-line flex items-center gap-6 px-8 relative z-30">
      <div className="relative flex-1 max-w-xl">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search case ID, institution, or Permanent ID"
          className="w-full h-10 pl-9 pr-3 rounded-lg border border-line bg-canvas text-sm outline-none focus:border-navy" />
        {res && (
          <div className="absolute top-12 left-0 right-0 bg-white border border-line rounded-xl shadow-xl p-2 max-h-96 overflow-y-auto">
            {res.cases.map((c: any) => (
              <button key={c.id} onClick={() => go(`/cases/${c.id}`)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 text-sm">
                <b className="text-navy">{c.id}</b> <span className="text-slate-500">· {c.institution?.name ?? c.written}</span>
              </button>
            ))}
            {res.institutions.map((i: any) => (
              <button key={i.id} onClick={() => go(`/institutions/${i.id}`)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 text-sm">
                <b className="text-slate-800">{i.name}</b> <span className="text-slate-500">· {i.permanent_id} · {i.city}</span>
              </button>
            ))}
            {res.cases.length + res.institutions.length === 0 && <div className="text-sm text-slate-400 px-3 py-2">No matches.</div>}
          </div>
        )}
      </div>
      <div className="ml-auto flex items-center gap-4">
        <label className="text-xs text-slate-500" htmlFor="role">Viewing as</label>
        <select id="role" value={role} onChange={(e) => onRole(e.target.value as Role)}
          className="h-10 rounded-lg border border-line bg-white px-3 text-sm outline-none focus:border-navy">
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
        <div className="h-9 w-9 rounded-full bg-navy text-white text-sm font-semibold flex items-center justify-center">{role[0]}</div>
      </div>
    </header>
  );
}
