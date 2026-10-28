import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { api } from "../api";
import { useMeta } from "../hooks";
import { Btn, BureauChip, Modal, Select, SeverityChip } from "./ui";

export interface InterlockPayload { message: string; blockers: any[]; case_id: string; action: string; cluster_id: number; mode: string }

const ACTION_LABEL: Record<string, string> = { dispose: "Dispose", show_cause: "Issue show-cause", close: "Close" };

export default function InterlockModal({ payload, ownBureau, onClose, onDone }:
  { payload: InterlockPayload | null; ownBureau: string; onClose: () => void; onDone: (msg: string) => void }) {
  const meta = useMeta();
  const [step, setStep] = useState<"choose" | "lead" | "reason">("choose");
  const [lead, setLead] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  if (!payload) return null;

  const involved = Array.from(new Set([...payload.blockers.map((b) => b.bureau), ownBureau]));
  const leadName = lead || payload.blockers[0]?.bureau || involved[0];
  const minChars = meta?.min_reason_chars ?? 10;
  const act = ACTION_LABEL[payload.action] ?? payload.action;

  const close = () => { setStep("choose"); setReason(""); setErr(""); onClose(); };
  const submit = async (outcome: "lead" | "override" | "cancel", done: string) => {
    setBusy(true); setErr("");
    try {
      const bureau_id = meta?.bureaus.find((b) => b.name === leadName)?.id;
      await api(`/cases/${payload.case_id}/actions/override`, { body: { action: payload.action, outcome, reason, bureau_id } });
      setStep("choose"); setReason(""); onDone(done);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={close} wide tone="danger" title={<span className="flex items-center gap-2"><ShieldAlert size={20} /> Action paused – linked case active</span>}>
      <p className="text-sm text-slate-700 leading-relaxed">{payload.message.replace("⛔ Action paused – linked case active. ", "")}</p>
      <div className="mt-4 rounded-lg border border-line divide-y divide-line">
        {payload.blockers.map((b) => (
          <div key={b.case_id} className="flex items-center gap-3 px-4 py-3 text-sm">
            <Link to={`/cases/${b.case_id}`} onClick={close} className="font-medium text-navy hover:underline">{b.case_id}</Link>
            <BureauChip name={b.bureau} />
            <SeverityChip level={b.severity} />
            <span className="text-xs text-slate-500 truncate">{b.last_action ? b.last_action.replace("_", "-") : b.status}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500 mt-3">Attempted: <b>{act}</b> on {payload.case_id}. The interlock only pauses the action; the officer always decides. Every outcome is logged.</p>

      {step === "lead" && (
        <div className="mt-5 rounded-lg bg-slate-50 p-4">
          <div className="text-sm font-medium text-slate-700 mb-2">Lead Bureau for this cluster</div>
          <Select value={leadName} onChange={setLead} placeholder="Choose Bureau" options={involved} className="w-full" />
          <p className="text-xs text-slate-500 mt-2">{act} stays deferred; the Lead Bureau coordinates the joint response.</p>
          <div className="flex gap-3 mt-3">
            <Btn kind="primary" disabled={busy} onClick={() => submit("lead", `Lead Bureau ${leadName} assigned. ${act} deferred for coordination.`)}>Confirm Lead Bureau: {leadName}</Btn>
            <Btn onClick={() => setStep("choose")}>Back</Btn>
          </div>
        </div>
      )}
      {step === "reason" && (
        <div className="mt-5 rounded-lg bg-slate-50 p-4">
          <label className="text-sm font-medium text-slate-700">Reason to continue <span className="text-slate-400 font-normal">(min. {minChars} characters, logged in the audit chain)</span></label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} autoFocus
            className="mt-2 w-full rounded-lg border border-line p-3 text-sm outline-none focus:border-navy" placeholder="e.g. RB confirmed the show-cause is unrelated to this complaint" />
          <div className="flex gap-3 mt-3 items-center">
            <Btn kind="danger" disabled={busy || reason.trim().length < minChars} onClick={() => submit("override", `${act} recorded with override reason.`)}>Continue with reason</Btn>
            <Btn onClick={() => setStep("choose")}>Back</Btn>
            <span className="text-xs text-slate-400 ml-auto">{reason.trim().length}/{minChars}</span>
          </div>
        </div>
      )}
      {err && <div className="mt-3 text-sm text-red-700">{err}</div>}
      {step === "choose" && (
        <div className="flex flex-wrap gap-3 mt-6">
          <Btn kind="primary" onClick={() => setStep("lead")}>Assign Lead Bureau</Btn>
          <Btn onClick={() => setStep("reason")}>Record reason &amp; continue</Btn>
          <Btn disabled={busy} onClick={() => submit("cancel", "Action cancelled.")}>Cancel</Btn>
        </div>
      )}
    </Modal>
  );
}
