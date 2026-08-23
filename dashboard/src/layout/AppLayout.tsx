import { NavLink, Outlet } from "react-router-dom";

// Qualyx Dashboard — shared app layout/navigation shell.
//
// Establishes the visual foundation for future pages (Projects, Tests,
// History, Analysis) without implementing them yet. Preserves the
// existing dark theme (bg-slate-950/slate-100) and max-w-2xl content
// convention already established by App.tsx / RecordedSessions.tsx.

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm transition-colors ${
    isActive
      ? "bg-slate-800 text-slate-100"
      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
  }`;

function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-semibold tracking-tight">Qualyx</h1>
          <p className="text-slate-400">Dashboard foundation — running</p>
          <nav className="mt-4 flex gap-2">
            <NavLink to="/projects" className={navLinkClass}>
              Projects
            </NavLink>
            {/* Tests/History/Analysis are scoped under a project/test id
                (see routes.tsx) and have no standalone top-level page
                yet, so they're non-navigable placeholders here rather
                than links to a route that doesn't resolve to anything
                useful without an id. */}
            <span className="px-3 py-1.5 rounded-md text-sm text-slate-600 cursor-not-allowed">
              Tests
            </span>
            <span className="px-3 py-1.5 rounded-md text-sm text-slate-600 cursor-not-allowed">
              History
            </span>
            <span className="px-3 py-1.5 rounded-md text-sm text-slate-600 cursor-not-allowed">
              Analysis
            </span>
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
