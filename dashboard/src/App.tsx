import RecordedSessions from "./components/RecordedSessions";

// Qualyx Dashboard — foundation shell + Recorded Sessions placeholder.
// Intentionally does not implement project management, analytics,
// healing-review UI, or journey visualization yet, and is NOT connected
// to the Backend or Recorder. This exists only to verify React +
// TypeScript + Vite + Tailwind render correctly, and to make the future
// recording workflow understandable via an empty-state placeholder.

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="text-center py-10">
        <h1 className="text-3xl font-semibold tracking-tight">Qualyx</h1>
        <p className="text-slate-400">Dashboard foundation — running</p>
      </header>
      <RecordedSessions />
    </div>
  );
}

export default App;
