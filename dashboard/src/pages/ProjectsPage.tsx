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
//
// Stage 14: visual polish only -- header gains a supporting
// description, cards gain clearer hierarchy/hover/focus states and an
// "Open project ->" affordance, and the empty state gains its own
// "+ Create project" CTA. No new fields: every value shown still comes
// straight from the existing Project type (name, description). The
// create-form's open/closed state is now owned here (rather than
// inside CreateProjectForm) so both the header button and the
// empty-state CTA can open the same form instance.
function ProjectsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const state = useAsync(() => listProjects(), [refreshKey]);

  return (
    <section className="max-w-4xl mx-auto px-6 py-10">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium text-slate-100">Projects</h2>
          <p className="mt-1 text-sm text-slate-400">
            Manage your automated testing projects.
          </p>
        </div>
        <CreateProjectForm
          isOpen={isCreateOpen}
          onOpenChange={setIsCreateOpen}
          onCreated={() => setRefreshKey((key) => key + 1)}
        />
      </div>

      {state.status === "loading" && (
        <StateBlock>Loading projects…</StateBlock>
      )}

      {state.status === "error" && (
        <StateBlock tone="error">
          Couldn't load projects: {state.message}
        </StateBlock>
      )}

      {state.status === "success" && state.data.length === 0 && !isCreateOpen && (
        <div className="rounded-lg border border-dashed border-slate-700 p-10 text-center">
          <h3 className="text-base font-medium text-slate-200">No projects yet</h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">
            Create your first project to start organizing and running automated tests.
          </p>
          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            data-testid="empty-state-create-project"
            className="mt-5 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
          >
            + Create project
          </button>
        </div>
      )}

      {state.status === "success" && state.data.length > 0 && (
        <ul data-testid="project-list" className="grid min-w-0 gap-4 sm:grid-cols-2">
          {state.data.map((project) => (
            <li key={project.id} className="min-w-0">
              <Link
                to={`/projects/${project.id}`}
                data-testid="project-list-item"
                className="group block h-full min-w-0 rounded-lg border border-slate-800 bg-slate-900/50 p-5 transition-colors hover:border-slate-600 hover:bg-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
              >
                <h3 className="truncate font-semibold text-slate-100">{project.name}</h3>
                <p className="mt-1.5 line-clamp-2 min-h-[2.5rem] text-sm text-slate-400">
                  {project.description ?? "No description."}
                </p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-slate-500 transition-colors group-hover:text-emerald-400">
                  Open project
                  <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">
                    →
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ProjectsPage;
