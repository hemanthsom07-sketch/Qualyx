import { Navigate } from "react-router-dom";

// Stage 12: the root route previously rendered a static Stage-1
// placeholder ("visit /projects for the placeholder route") that never
// got a real destination once /projects became a fully working page in
// Stage 2 -- it was the single dead-end left in the application, since
// it's the first thing anyone sees opening the Dashboard. /projects is
// already the Dashboard's real, fully-implemented landing page, so this
// just sends the user straight there instead of asking them to
// retype the URL themselves.
function HomePage() {
  return <Navigate to="/projects" replace />;
}

export default HomePage;
