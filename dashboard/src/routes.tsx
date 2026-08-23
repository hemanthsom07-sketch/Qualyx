import { createBrowserRouter } from "react-router-dom";

import AppLayout from "./layout/AppLayout";
import HomePage from "./pages/HomePage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import TestAnalysisPage from "./pages/TestAnalysisPage";
import TestDetailPage from "./pages/TestDetailPage";
import TestHistoryPage from "./pages/TestHistoryPage";

// Stage 1: routing foundation only. Every route below renders a
// placeholder page (see src/pages/PlaceholderPage.tsx) — real page
// implementations land in later stages.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "projects", element: <ProjectsPage /> },
      { path: "projects/:projectId", element: <ProjectDetailPage /> },
      { path: "tests/:testId", element: <TestDetailPage /> },
      { path: "tests/:testId/history", element: <TestHistoryPage /> },
      { path: "tests/:testId/analysis", element: <TestAnalysisPage /> },
    ],
  },
]);
