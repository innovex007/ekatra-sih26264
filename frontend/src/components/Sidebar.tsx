import { NavLink } from "react-router-dom";
import { NAV } from "../nav";

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 bg-navy text-white flex flex-col h-full overflow-y-auto">
      <div className="px-6 py-6">
        <div className="text-xl font-bold tracking-[0.2em]">EKATRA</div>
        <div className="text-xs text-white/60 mt-1">एकत्र · gathered in one place</div>
      </div>
      <nav className="px-3 pb-6 space-y-5">
        {NAV.map((g) => (
          <div key={g.title}>
            <div className="px-3 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/50">{g.title}</div>
            {g.items.map(({ path, label, icon: Icon }) => (
              <NavLink key={path} to={path} end={path === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive ? "bg-amber-ekatra text-navy font-semibold" : "text-white/80 hover:bg-white/10"}`}>
                <Icon size={17} /> {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
