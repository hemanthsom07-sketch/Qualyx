import { RouterProvider } from "react-router-dom";

import { router } from "./routes";

// Qualyx Dashboard — Stage 1: routing + API client foundation.
//
// The static header/RecordedSessions shell from the previous foundation
// stage now lives inside AppLayout (header/nav) and HomePage/future
// pages respectively (RecordedSessions itself is untouched and still
// not wired into any route — see src/components/RecordedSessions.tsx).
// App.tsx's only job now is to hand off to the router.
function App() {
  return <RouterProvider router={router} />;
}

export default App;
