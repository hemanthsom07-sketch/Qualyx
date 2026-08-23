import { Link, useParams } from "react-router-dom";

import { getProject, listTestDefinitions } from "../api/client";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 2: project header (GET /projects/{id}) + its test definitions
// (GET /projects/{id}/tests), both via the Stage 1 API client. The two
// resources are fetched independently so a failure/empty state in one
// doesn't block the other from rendering.
function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();

  const projectState = useAsync(() => getProject(projectId as string), [projectId]);
  const testsState = useAsync(() => listTestDefinitions(projectId as string), [projectId]);

  return (
    <section className="max-w-4xl mx-auto px-6 py-10">
      <Link to="/projects" className="text-sm text-slate-400 hover:text-slate-200">
        ← Projects
      </Link>

      <div className="mt-3 mb-8">
        {projectState.status === "loading" && (
          <h2 className="text-lg font-medium text-slate-400">Loading project…</h2>
        )}
        {projectState.status === "error" && (
          <StateBlock tone="error">
            Couldn't load this project: {projectState.message}
          </StateBlock>
        )}
        {projectState.status === "success" && (
          <>
            <h2 className="text-lg font-medium">{projectState.data.name}</h2>
            {projectState.data.description && (
              <p className="mt-1 text-sm text-slate-400">
                {projectState.data.description}
              </p>
            )}
          </>
        )}
      </div>

      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-3">
        Tests
      </h3>

      {testsState.status === "loading" && <StateBlock>Loading tests…</StateBlock>}

      {testsState.status === "error" && (
        <StateBlock tone="error">
          Couldn't load tests for this project: {testsState.message}
        </StateBlock>
      )}

      {testsState.status === "success" && testsState.data.length === 0 && (
        <StateBlock>No test definitions yet for this project.</StateBlock>
      )}

      {testsState.status === "success" && testsState.data.length > 0 && (
        <ul data-testid="test-list" className="grid gap-3 sm:grid-cols-2">
          {testsState.data.map((test) => (
            <li key={test.id}>
              <Link
                to={`/tests/${test.id}`}
                data-testid="test-list-item"
                className="block h-full rounded-lg border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 hover:bg-slate-900 transition-colors"
              >
                <h4 className="font-medium text-slate-100">{test.name}</h4>
                <p className="mt-1 text-sm text-slate-400">
                  {test.description ?? `${test.content.length} step(s)`}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ProjectDetailPage;
