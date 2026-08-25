import { Link, useParams } from "react-router-dom";

import { getTestAnalysis, getTestDefinition } from "../api/client";
import { AnalysisSummary } from "../components/AnalysisSummary";
import { ClassificationBreakdown } from "../components/ClassificationBreakdown";
import { RecurringSignaturesList } from "../components/RecurringSignaturesList";
import { StateBlock } from "../components/StateBlock";
import { useAsync } from "../hooks/useAsync";

// Stage 5: flaky/recurring analysis, backed by GET /tests/{test_id}/analysis
// via the existing (unmodified) getTestAnalysis() client function.
// insufficient_data is a normal, valid analysis result -- not an error
// state -- and is handled entirely inside AnalysisSummary/this page's
// success branch, not as a separate error UI.
function TestAnalysisPage() {
  const { testId } = useParams<{ testId: string }>();

  const testState = useAsync(() => getTestDefinition(testId as string), [testId]);
  const analysisState = useAsync(() => getTestAnalysis(testId as string), [testId]);

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
              <RecurringSignaturesList signatures={analysisState.data.recurring_signatures} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default TestAnalysisPage;
