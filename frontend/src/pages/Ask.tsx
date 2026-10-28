import { useEffect, useRef, useState } from "react";
import { Mic, Search, Sparkles } from "lucide-react";
import { api } from "../api";
import CaseTable from "../components/CaseTable";
import { Btn, Card, ErrorNote, PageHeader } from "../components/ui";

const EXAMPLES = ["overdue RB cases in Southern region", "conflicts this week", "SVIT ki shikayatein", "pending PGRC fee cases in North", "duplicates", "ping-pong cases"];

export default function Ask() {
  const [q, setQ] = useState(EXAMPLES[0]);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const rec = useRef<any>(null);
  const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

  const run = async (text: string) => {
    setQ(text); setBusy(true); setErr("");
    try { setRes(await api("/ask", { body: { query: text } })); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  useEffect(() => { run(EXAMPLES[0]); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  const mic = () => {
    if (!SR) return;
    if (listening) { rec.current?.stop(); return; }
    const r = new SR();
    r.lang = "en-IN"; r.interimResults = false;
    r.onresult = (e: any) => run(e.results[0][0].transcript);
    r.onend = () => setListening(false);
    rec.current = r; setListening(true); r.start();
  };

  return (
    <>
      <PageHeader title="Ask Ekatra" subtitle="Ask in English or Hindi. Parsed by keyword rules on this machine – no AI service involved." />
      <Card className="mb-5">
        <form onSubmit={(e) => { e.preventDefault(); q.trim() && run(q); }} className="flex gap-3">
          <div className="relative flex-1"><Search size={17} className="absolute left-4 top-3.5 text-slate-400" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. overdue RB cases in Southern region" autoFocus
              className="h-12 w-full rounded-xl border border-line pl-11 pr-4 text-base outline-none focus:border-navy" /></div>
          {SR && <Btn onClick={mic} className={`!h-12 ${listening ? "!bg-red-50 !text-sev-conflict" : ""}`}><Mic size={18} />{listening ? "Listening…" : "Speak"}</Btn>}
          <Btn type="submit" kind="primary" className="!h-12 px-6" disabled={busy}><Sparkles size={16} />Ask</Btn>
        </form>
        <div className="flex flex-wrap gap-2 mt-4">
          {EXAMPLES.map((e) => <button key={e} onClick={() => run(e)} className="text-sm rounded-full border border-line bg-slate-50 px-3.5 py-1.5 text-slate-700 hover:bg-slate-100">{e}</button>)}
        </div>
      </Card>
      {err && <ErrorNote msg={err} />}
      {res && (
        <>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-sm text-slate-500 mr-1">Understood as</span>
            {res.chips.length === 0 && <span className="text-sm text-slate-400">no filters recognised – showing all cases</span>}
            {res.chips.map((c: any, i: number) => <span key={i} className="text-sm rounded-full bg-navy text-white px-3 py-1"><span className="opacity-60">{c.label}:</span> {c.value}</span>)}
            <span className="ml-auto text-sm text-slate-500">{res.total} matching cases</span>
          </div>
          <Card className="!p-0 overflow-hidden"><CaseTable items={res.items} /></Card>
        </>
      )}
    </>
  );
}
