import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { setApiRole } from "./api";
import Sidebar from "./components/Sidebar";
import TopBar, { type Role } from "./components/TopBar";
import Alerts from "./pages/Alerts";
import Ask from "./pages/Ask";
import Audit from "./pages/Audit";
import CaseDetail from "./pages/CaseDetail";
import CaseTracker from "./pages/CaseTracker";
import Dashboard from "./pages/Dashboard";
import Evaluation from "./pages/Evaluation";
import Institution360 from "./pages/Institution360";
import OverlapCentre from "./pages/OverlapCentre";
import Reports from "./pages/Reports";
import Watchlist from "./pages/Watchlist";

export default function App() {
  const [role, setRole] = useState<Role>("PGRC officer");
  const [api, setApi] = useState<"checking" | "up" | "down">("checking");
  setApiRole(role);

  useEffect(() => {
    fetch("/api/health").then((r) => setApi(r.ok ? "up" : "down")).catch(() => setApi("down"));
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="h-7 shrink-0 bg-amber-100 text-amber-900 text-xs flex items-center justify-center gap-3">
        <span className="font-semibold">Prototype · synthetic data</span>
        <span className="opacity-70">API: {api}</span>
      </div>
      <div className="flex-1 flex min-h-0">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar role={role} onRole={setRole} />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-8">
            <div className="max-w-[1440px] mx-auto min-h-full flex flex-col">
              <Routes key={role}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/cases" element={<CaseTracker />} />
                <Route path="/case" element={<CaseDetail />} />
                <Route path="/cases/*" element={<CaseDetail />} />
                <Route path="/institutions" element={<Institution360 />} />
                <Route path="/institutions/:id" element={<Institution360 />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/overlaps" element={<OverlapCentre />} />
                <Route path="/ask" element={<Ask />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/audit" element={<Audit />} />
                <Route path="/evaluation" element={<Evaluation />} />
                <Route path="*" element={<Dashboard />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
