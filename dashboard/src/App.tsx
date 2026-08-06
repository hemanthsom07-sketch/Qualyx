// Qualyx Dashboard — minimal foundation shell.
// Intentionally does not implement project management, analytics,
// healing-review UI, or journey visualization yet. This exists only
// to verify React + TypeScript + Vite + Tailwind render correctly.

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Qualyx</h1>
        <p className="text-slate-400">Dashboard foundation — running</p>
      </div>
    </div>
  );
}

export default App;
