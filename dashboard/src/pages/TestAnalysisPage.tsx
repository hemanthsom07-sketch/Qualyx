import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTestAnalysis, getTestDefinition } from "../api/client";
import { AnalysisSummary } from "../components/AnalysisSummary";
import { ClassificationBreakdown } from "../components/ClassificationBreakdown";
import { RecurringSignaturesList } from "../components/RecurringSignaturesList";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Backend contract (backend/app/api/routes/test_definitions.py):
// GET /tests/{id}/analysis?window=N, default 20, rejects N < 3 with a
// 422 (the flaky-analysis engine itself treats fewer than 3 executions
// as insufficient_data, so the route never accepts a window that could
// never produce a verdict). These four presets are all >= 3 by
// construction, so no client-side validation/error handling for that
// case is needed here.
const WINDOW_OPTIONS = [5, 10, 20, 50] as const;
const DEFAULT_WINDOW = 20;

// Stage 5: flaky/recurring analysis, backed by GET /tests/{test_id}/analysis
// via the existing (unmodified) getTestAnalysis() client function.
// insufficient_data is a normal, valid analysis result -- not an error
// state -- and is handled entirely inside AnalysisSummary/this page's
// success branch, not as a separate error UI.
//
// Stage 8 exposes the endpoint's existing `window` query param (already
// supported by getTestAnalysis()'s options since Stage 1, but never
// surfaced in the UI) as a preset selector, so a user can compare the
// flakiness verdict across different amounts of recent history.
function TestAnalysisPage() {
  const { testId } = useParams<{ testId: string }>();
  const [window, setWindow] = useState<number>(DEFAULT_WINDOW);

  const testState = useAsync(() => getTestDefinition(testId as string), [testId]);
  const analysisState = useAsync(
    () => getTestAnalysis(testId as string, { window }),
    [testId, window]
  );

  return (
    <section className="max-w-3xl mx-auto px-6 py-10">
      <Link to={`/tests/${testId}`} className="text-sm text-slate-400 hover:text-slate-200">
        ← Test
      </Link>

      <div className="mt-3 mb-6 flex items-center justify-between gap-4">
        <h2 className="text-lg font-medium">
          Flaky analysis
          {testState.status === "success" && (
            <span className="text-slate-400"> — {testState.data.name}</span>
          )}
        </h2>
        <Link
          to={`/tests/${testId}/history`}
          data-testid="view-history-link"
          className="shrink-0 rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-slate-100"
        >
          View history
        </Link>
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm">
        <label htmlFor="analysis-window" className="text-slate-400">
          Analyze last
        </label>
        <select
          id="analysis-window"
          data-testid="analysis-window-select"
          value={window}
          onChange={(event) => setWindow(Number(event.target.value))}
          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200 focus:border-slate-500 focus:outline-none"
        >
          {WINDOW_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <span className="text-slate-400">executions</span>
      </div>

      {analysisState.status === "loading" && <StateBlock>Loading analysis…</StateBlock>}

      {analysisState.status === "error" && (
        <StateBlock tone="error">Couldn't load analysis: {analysisState.message}</StateBlock>
      )}

      {analysisState.status === "success" && (
        <div className="space-y-4">
          <AnalysisSummary analysis={analysisState.data} />

          {analysisState.data.insufficient_data && (
            <StateBlock>
              There isn't enough execution history yet to reliably determine whether this test
              is flaky. Run it a few more times, or check{" "}
              <Link to={`/tests/${testId}/history`} className="underline hover:text-slate-200">
                execution history
              </Link>{" "}
              to see what's been recorded so far.
            </StateBlock>
          )}

          {Object.keys(analysisState.data.diagnosis_classification_counts).length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-400 uppercase tracking-wide">
                Failure classification breakdown
              </h3>
              <ClassificationBreakdown counts={analysisState.data.diagnosis_classification_counts} />
            </div>
          )}

          {analysisState.data.recurring_signatures.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-400 uppercase tracking-wide">
                Recurring failure signatures
              </h3>
              <RecurringSignaturesList
                signatures={analysisState.data.recurring_signatures}
                testId={testId as string}
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default TestAnalysisPage;
