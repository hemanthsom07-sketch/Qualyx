import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, executeTestDefinition, getTestDefinition } from "../api/client";
import type { ExecutionResultWithDiagnosis } from "../api/types";
import { DiagnosisCard } from "../components/DiagnosisCard";
import { ExecutionSummary } from "../components/ExecutionSummary";
import { ExplanationCard } from "../components/ExplanationCard";
import { HealingCard } from "../components/HealingCard";
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

// Execution is user-triggered (not a mount-time fetch), so it's tracked
// separately from the test-definition load via useAsync -- a distinct,
// explicit state machine rather than overloading useAsync's mount-based
// model. Kept as a plain discriminated union + useState rather than
// pulling in a state-management library, per Stage 3 scope.
type ExecutionState =
  | { status: "idle" }
  | { status: "running" }
  | { status: "success"; data: ExecutionResultWithDiagnosis }
  | { status: "error"; message: string };

// Stage 3: adds the execute workflow on top of Stage 2's test
// discovery/detail page. Deliberately does NOT implement execution
// history or flaky analysis (later stages) -- only the single-run
// execute -> result/diagnosis/explanation/healing experience.
function TestDetailPage() {
  const { testId } = useParams<{ testId: string }>();

  const testState = useAsync(() => getTestDefinition(testId as string), [testId]);
  const [executionState, setExecutionState] = useState<ExecutionState>({ status: "idle" });

  const isRunning = executionState.status === "running";

  async function handleExecute() {
    // Guards against duplicate requests -- the button itself is also
    // disabled while running (belt-and-suspenders, since a fast
    // double-click could otherwise land two clicks before the first
    // re-render disables it).
    if (isRunning || !testId) return;

    setExecutionState({ status: "running" });
    try {
      const data = await executeTestDefinition(testId);
      setExecutionState({ status: "success", data });
    } catch (err) {
      // A failed HTTP/API request (e.g. 502 from the Execution Engine
      // boundary, or 422 validation) is distinct from a *valid*
      // execution response whose `status` happens to be "failed" -- the
      // latter is handled entirely inside the "success" branch below,
      // via ExecutionSummary's own PASS/FAIL badge, not here.
      const message =
        err instanceof ApiError ? err.message : "The execution request failed unexpectedly.";
      setExecutionState({ status: "error", message });
    }
  }

  return (
    <section className="max-w-3xl mx-auto px-6 py-10">
      {testState.status === "success" && (
        <Link
          to={`/projects/${testState.data.project_id}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← Project
        </Link>
      )}

      <div className="mt-3">
        {testState.status === "loading" && <StateBlock>Loading test…</StateBlock>}

        {testState.status === "error" && (
          <StateBlock tone="error">Couldn't load this test: {testState.message}</StateBlock>
        )}

        {testState.status === "success" && (
          <>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-medium">{testState.data.name}</h2>
                {testState.data.description && (
                  <p className="mt-1 text-sm text-slate-400">{testState.data.description}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Link
                  to={`/tests/${testId}/history`}
                  data-testid="view-history-link"
                  className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-slate-100"
                >
                  View history
                </Link>
                <button
                  type="button"
                  onClick={handleExecute}
                  disabled={isRunning}
                  aria-label={isRunning ? "Test is currently running" : "Execute this test"}
                  data-testid="execute-button"
                  className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
                >
                  {isRunning ? "Running…" : "Execute test"}
                </button>
              </div>
            </div>

            <h3 className="mt-6 text-sm font-medium text-slate-400 uppercase tracking-wide mb-3">
              Steps
            </h3>

            {testState.data.content.length === 0 ? (
              <StateBlock>This test has no steps.</StateBlock>
            ) : (
              <ol
                data-testid="step-list"
                className="space-y-2 list-decimal list-inside text-sm text-slate-300"
              >
                {testState.data.content.map((step, index) => (
                  <li
                    key={index}
                    className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2"
                  >
                    {describeStep(step)}
                  </li>
                ))}
              </ol>
            )}

            <div className="mt-8 space-y-4">
              {isRunning && (
                <StateBlock>
                  <span role="status">Running test — this may take a few seconds…</span>
                </StateBlock>
              )}

              {executionState.status === "error" && (
                <StateBlock tone="error">
                  Execution request failed: {executionState.message}
                </StateBlock>
              )}

              {executionState.status === "success" && (
                <>
                  <ExecutionSummary result={executionState.data} />
                  <ExplanationCard explanation={executionState.data.explanation} />
                  <DiagnosisCard diagnosis={executionState.data.diagnosis} />
                  <HealingCard healing={executionState.data.healing} />
                </>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

export default TestDetailPage;
