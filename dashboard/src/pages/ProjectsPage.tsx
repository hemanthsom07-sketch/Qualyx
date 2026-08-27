import { useState } from "react";
import { Link } from "react-router-dom";

import { listProjects } from "../api/client";
import { CreateProjectForm } from "../components/CreateProjectForm";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 2: real Projects list, backed by GET /projects via the Stage 1
// API client. Data fetching/loading/error state is handled by the
// shared useAsync hook; this component only renders the three
// resulting states.
//
// Stage 6 adds project creation (POST /projects). useAsync has no
// built-in refetch, so a `refreshKey` dependency is used to trigger a
// fresh GET /projects after a successful create -- a real round trip
// to the canonical server state, rather than optimistically splicing
// an unconfirmed project into local state.
function ProjectsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const state = useAsync(() => listProjects(), [refreshKey]);

  return (
    <section className="max-w-4xl mx-auto px-6 py-10">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h2 className="text-lg font-medium">Projects</h2>
        <CreateProjectForm onCreated={() => setRefreshKey((key) => key + 1)} />
      </div>

      {state.status === "loading" && (
        <StateBlock>Loading projects…</StateBlock>
      )}

      {state.status === "error" && (
        <StateBlock tone="error">
          Couldn't load projects: {state.message}
        </StateBlock>
      )}

      {state.status === "success" && state.data.length === 0 && (
        <StateBlock>No projects yet.</StateBlock>
      )}

      {state.status === "success" && state.data.length > 0 && (
        <ul data-testid="project-list" className="grid gap-3 sm:grid-cols-2">
          {state.data.map((project) => (
            <li key={project.id}>
              <Link
                to={`/projects/${project.id}`}
                data-testid="project-list-item"
                className="block h-full rounded-lg border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 hover:bg-slate-900 transition-colors"
              >
                <h3 className="font-medium text-slate-100">{project.name}</h3>
                <p className="mt-1 text-sm text-slate-400">
                  {project.description ?? "No description."}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ProjectsPage;
