import { useEffect } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { getTestDefinition, listExecutionRuns } from "../api/client";
import { ExecutionHistoryRecord, executionAnchorId } from "../components/ExecutionHistoryRecord";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 4: read-only execution history, backed by
// GET /tests/{test_id}/executions via the existing (unmodified)
// listExecutionRuns() client function. The test definition is fetched
// separately just to show its name/back-link -- its own loading/error
// state doesn't block the history list from rendering, matching the
// same "independent fetches" pattern ProjectDetailPage already uses.
//
// Stage 10: supports being linked to directly at
// #execution-<run.id> (from RecurringSignaturesList on the Analysis
// page) -- the target record is highlighted and scrolled into view.
// This has to happen in an effect rather than relying on the browser's
// native anchor-scroll, since the list doesn't exist in the DOM until
// after the async fetch resolves.
function TestHistoryPage() {
  const { testId } = useParams<{ testId: string }>();
  const location = useLocation();
  const highlightedId = location.hash ? location.hash.slice(1) : null;

  const testState = useAsync(() => getTestDefinition(testId as string), [testId]);
  const historyState = useAsync(() => listExecutionRuns(testId as string), [testId]);

  useEffect(() => {
    if (!highlightedId || historyState.status !== "success") return;
    document.getElementById(highlightedId)?.scrollIntoView({ block: "center" });
  }, [highlightedId, historyState.status]);

  return (
    <section className="max-w-3xl mx-auto px-6 py-10">
      <Link
        to={`/tests/${testId}`}
        className="text-sm text-slate-400 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 rounded"
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
        <StateBlock tone="error" onRetry={historyState.retry}>
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
              <ExecutionHistoryRecord
                key={run.id}
                run={run}
                highlighted={highlightedId === executionAnchorId(run.id)}
              />
            ))}
        </ul>
      )}
    </section>
  );
}

export default TestHistoryPage;
