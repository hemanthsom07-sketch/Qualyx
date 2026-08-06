// Qualyx Demo E-commerce Application — minimal foundation shell.
// Intentionally does not implement registration, login, search,
// product details, cart, or checkout yet. This exists only to
// verify React + TypeScript + Vite + Tailwind render correctly,
// as the controlled target application Qualyx will test against.

function App() {
  return (
    <div className="min-h-screen bg-white text-slate-900 flex items-center justify-center">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Qualyx Demo Store</h1>
        <p className="text-slate-500">Demo application foundation — running</p>
      </div>
    </div>
  );
}

export default App;
