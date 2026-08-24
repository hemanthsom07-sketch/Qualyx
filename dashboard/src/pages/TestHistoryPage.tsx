import { Link, useParams } from "react-router-dom";

import { getTestDefinition, listExecutionRuns } from "../api/client";
import { ExecutionHistoryRecord } from "../components/ExecutionHistoryRecord";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 4: read-only execution history, backed by
// GET /tests/{test_id}/executions via the existing (unmodified)
// listExecutionRuns() client function. The test definition is fetched
// separately just to show its name/back-link -- its own loading/error
// state doesn't block the history list from rendering, matching the
// same "independent fetches" pattern ProjectDetailPage already uses.
function TestHistoryPage() {
  const { testId } = useParams<{ testId: string }>();

  const testState = useAsync(() => getTestDefinition(testId as string), [testId]);
  const historyState = useAsync(() => listExecutionRuns(testId as string), [testId]);

  return (
    <section className="max-w-3xl mx-auto px-6 py-10">
      <Link
        to={`/tests/${testId}`}
        className="text-sm text-slate-400 hover:text-slate-200"
      >
        ← Test
      </Link>

      <div className="mt-3 mb-6">
        <h2 className="text-lg font-medium">
          Execution history
          {testState.status === "success" && (
            <span className="text-slate-400"> — {testState.data.name}</span>
          )}
        </h2>
      </div>

      {historyState.status === "loading" && <StateBlock>Loading execution history…</StateBlock>}

      {historyState.status === "error" && (
        <StateBlock tone="error">
          Couldn't load execution history: {historyState.message}
        </StateBlock>
      )}

      {historyState.status === "success" && historyState.data.length === 0 && (
        <StateBlock>This test hasn't been executed yet.</StateBlock>
      )}

      {historyState.status === "success" && historyState.data.length > 0 && (
        // Backend already returns newest-first (created_at descending);
        // sorted again here defensively rather than assumed, since this
        // page's own contract to the user is "newest-first", not
        // "whatever order the response happened to arrive in".
        <ul data-testid="execution-history-list" className="space-y-3">
          {[...historyState.data]
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .map((run) => (
              <ExecutionHistoryRecord key={run.id} run={run} />
            ))}
        </ul>
      )}
    </section>
  );
}

export default TestHistoryPage;
