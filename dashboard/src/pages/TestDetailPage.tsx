import { Link, useParams } from "react-router-dom";

import { getTestDefinition } from "../api/client";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Reads a step's loosely-typed content dict (TestDefinition.content is
// Record<string, unknown>[] -- see ../api/types.ts's comment on why:
// the read path returns raw stored dicts, not the validated step
// union) without assuming any field is present.
function describeStep(step: Record<string, unknown>): string {
  const type = typeof step.type === "string" ? step.type : "step";
  const target =
    (typeof step.url === "string" && step.url) ||
    (typeof step.selector === "string" && step.selector) ||
    null;
  return target ? `${type} — ${target}` : type;
}

// Stage 2: test discovery/detail page, backed by GET /tests/{id} via
// the Stage 1 API client. Deliberately no Execute button or execution
// results yet -- that's a later stage.
function TestDetailPage() {
  const { testId } = useParams<{ testId: string }>();

  const state = useAsync(() => getTestDefinition(testId as string), [testId]);

  return (
    <section className="max-w-2xl mx-auto px-6 py-10">
      {state.status === "success" && (
        <Link
          to={`/projects/${state.data.project_id}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← Project
        </Link>
      )}

      <div className="mt-3">
        {state.status === "loading" && (
          <StateBlock>Loading test…</StateBlock>
        )}

        {state.status === "error" && (
          <StateBlock tone="error">
            Couldn't load this test: {state.message}
          </StateBlock>
        )}

        {state.status === "success" && (
          <>
            <h2 className="text-lg font-medium">{state.data.name}</h2>
            {state.data.description && (
              <p className="mt-1 text-sm text-slate-400">{state.data.description}</p>
            )}

            <h3 className="mt-6 text-sm font-medium text-slate-400 uppercase tracking-wide mb-3">
              Steps
            </h3>

            {state.data.content.length === 0 ? (
              <StateBlock>This test has no steps.</StateBlock>
            ) : (
              <ol
                data-testid="step-list"
                className="space-y-2 list-decimal list-inside text-sm text-slate-300"
              >
                {state.data.content.map((step, index) => (
                  <li key={index} className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2">
                    {describeStep(step)}
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </div>
    </section>
  );
}

export default TestDetailPage;
