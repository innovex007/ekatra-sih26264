import { LayoutDashboard, ListChecks, Building2, Network, Sparkles, Bell, FileText, ShieldCheck, FlaskConical, Radar } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem { path: string; label: string; icon: LucideIcon; blurb: string }
export interface NavGroup { title: string; items: NavItem[] }

export const NAV: NavGroup[] = [
  { title: "Overview", items: [
    { path: "/", label: "Command Dashboard", icon: LayoutDashboard, blurb: "Every Bureau's complaint load at a glance." } ] },
  { title: "Cases", items: [
    { path: "/cases", label: "Case Tracker", icon: ListChecks, blurb: "All complaint cases across Bureaus, with SLA countdowns." } ] },
  { title: "Institutions", items: [
    { path: "/institutions", label: "Institution 360°", icon: Building2, blurb: "One cross-Bureau view of an institution." },
    { path: "/watchlist", label: "Watchlist", icon: Radar, blurb: "Institutions ranked by open, overdue and repeat complaints." } ] },
  { title: "Intelligence", items: [
    { path: "/overlaps", label: "Overlap Centre", icon: Network, blurb: "Potential Overlapping Cases – Coordination Required." },
    { path: "/ask", label: "Ask Ekatra", icon: Sparkles, blurb: "Ask in English or Hindi; get filtered results." } ] },
  { title: "Alerts & Reports", items: [
    { path: "/alerts", label: "Alert Centre", icon: Bell, blurb: "Conflicts, deadline risk, ping-pong and duplicates." },
    { path: "/reports", label: "Reports", icon: FileText, blurb: "Bureau, region and institution reports with CSV/PDF export." } ] },
  { title: "Governance", items: [
    { path: "/audit", label: "Audit log", icon: ShieldCheck, blurb: "Tamper-evident record of every action and override." },
    { path: "/evaluation", label: "Evaluation", icon: FlaskConical, blurb: "Measured on synthetic data." } ] },
];

export const ALL_ITEMS = NAV.flatMap((g) => g.items);
