import type { ExecutionResult } from "../api/types";
import { statusLabel, statusTone } from "../lib/status";
import { FailureEvidenceCard } from "./FailureEvidenceCard";
import { StatusBadge } from "./StatusBadge";
import { StepResultsList } from "./StepResultsList";

interface ExecutionSummaryProps {
  result: ExecutionResult;
  /** Distinguishes an original run from a healed re-execution in the heading. */
  heading?: string;
}

// Renders exactly the fields ExecutionResult/ExecutionResultOut
// actually provides (see backend/app/schemas/execution.py) -- overall
// status, timing, executed step count, failed step identity, the full
// step list, and failure evidence when present. Reused for both the
// top-level execution and, via HealingCard, the nested healed_execution.
export function ExecutionSummary({ result, heading = "Execution result" }: ExecutionSummaryProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-medium text-slate-100">{heading}</h3>
        <StatusBadge label={statusLabel(result.status)} tone={statusTone(result.status)} />
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-400 sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Duration</dt>
          <dd className="text-slate-300">{result.durationMs}ms</dd>
        </div>
        <div>
          <dt className="text-slate-500">Steps executed</dt>
          <dd className="text-slate-300">{result.executedStepCount}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Started</dt>
          <dd className="text-slate-300">{new Date(result.startedAt).toLocaleTimeString()}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Finished</dt>
          <dd className="text-slate-300">{new Date(result.finishedAt).toLocaleTimeString()}</dd>
        </div>
      </dl>

      {result.failedStepId !== null && (
        <p className="mt-3 text-sm text-slate-400">
          Failed step: <span className="text-slate-200">{result.failedStepId}</span>
          {result.failedStepIndex !== null && ` (index ${result.failedStepIndex})`}
        </p>
      )}
      {result.error && <p className="mt-1 text-sm text-red-400 break-words">{result.error}</p>}

      <h4 className="mt-4 mb-2 text-xs font-medium text-slate-500 uppercase tracking-wide">
        Steps
      </h4>
      <StepResultsList steps={result.steps} />

      {result.evidence && (
        <div className="mt-4">
          <FailureEvidenceCard evidence={result.evidence} />
        </div>
      )}
    </div>
  );
}
