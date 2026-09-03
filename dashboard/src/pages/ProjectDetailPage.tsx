import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, listTestDefinitions } from "../api/client";
import { CreateTestForm } from "../components/CreateTestForm";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 2: project header (GET /projects/{id}) + its test definitions
// (GET /projects/{id}/tests), both via the Stage 1 API client. The two
// resources are fetched independently so a failure/empty state in one
// doesn't block the other from rendering.
//
// Stage 7 adds test creation (POST /projects/{id}/tests). Same
// refresh-key pattern as Stage 6's project creation: useAsync has no
// built-in refetch, so a successful create bumps `refreshKey` to
// trigger a fresh GET rather than optimistically splicing an
// unconfirmed test into local state.
//
// Stage 15: brings the test-card list and empty state up to the same
// visual/interaction standard Stage 14 established for ProjectsPage
// (truncate/line-clamp, hover "Open test ->" affordance, visible
// keyboard focus, polished empty state with its own CTA) -- these two
// pages sit one click apart in the primary navigation flow and had
// drifted out of sync. No new fields: still only test.name/description/
// content.length from the existing TestDefinition type.
function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [refreshKey, setRefreshKey] = useState(0);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const projectState = useAsync(() => getProject(projectId as string), [projectId]);
  const testsState = useAsync(
    () => listTestDefinitions(projectId as string),
    [projectId, refreshKey]
  );

  return (
    <section className="max-w-4xl mx-auto px-6 py-10">
      <Link to="/projects" className="text-sm text-slate-400 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 rounded">
        ← Projects
      </Link>

      <div className="mt-3 mb-8">
        {projectState.status === "loading" && (
          <h2 className="text-lg font-medium text-slate-400">Loading project…</h2>
        )}
        {projectState.status === "error" && (
          <StateBlock tone="error" onRetry={projectState.retry}>
            Couldn't load this project: {projectState.message}
          </StateBlock>
        )}
        {projectState.status === "success" && (
          <>
            <h2 className="text-lg font-medium text-slate-100">{projectState.data.name}</h2>
            {projectState.data.description && (
              <p className="mt-1 text-sm text-slate-400">
                {projectState.data.description}
              </p>
            )}
          </>
        )}
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide">
          Tests
        </h3>
        {projectId && (
          <CreateTestForm
            projectId={projectId}
            isOpen={isCreateOpen}
            onOpenChange={setIsCreateOpen}
            onCreated={() => setRefreshKey((key) => key + 1)}
          />
        )}
      </div>

      {testsState.status === "loading" && <StateBlock>Loading tests…</StateBlock>}

      {testsState.status === "error" && (
        <StateBlock tone="error" onRetry={testsState.retry}>
          Couldn't load tests for this project: {testsState.message}
        </StateBlock>
      )}

      {testsState.status === "success" && testsState.data.length === 0 && !isCreateOpen && (
        <div className="rounded-lg border border-dashed border-slate-700 p-10 text-center">
          <h4 className="text-base font-medium text-slate-200">No tests yet</h4>
          <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">
            Create your first test definition to start running automated checks against this
            project.
          </p>
          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            data-testid="empty-state-create-test"
            className="mt-5 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
          >
            + Create test
          </button>
        </div>
      )}

      {testsState.status === "success" && testsState.data.length > 0 && (
        <ul data-testid="test-list" className="grid min-w-0 gap-4 sm:grid-cols-2">
          {testsState.data.map((test) => (
            <li key={test.id} className="min-w-0">
              <Link
                to={`/tests/${test.id}`}
                data-testid="test-list-item"
                className="group block h-full min-w-0 rounded-lg border border-slate-800 bg-slate-900/50 p-5 transition-colors hover:border-slate-600 hover:bg-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
              >
                <h4 className="truncate font-semibold text-slate-100">{test.name}</h4>
                <p className="mt-1.5 line-clamp-2 min-h-[2.5rem] text-sm text-slate-400">
                  {test.description ?? `${test.content.length} step(s)`}
                </p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-slate-500 transition-colors group-hover:text-emerald-400">
                  Open test
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

export default ProjectDetailPage;
