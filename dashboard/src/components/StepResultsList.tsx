import type { StepResult } from "../api/types";
import { statusLabel, statusTone } from "../lib/status";
import { StatusBadge } from "./StatusBadge";

interface StepResultsListProps {
  steps: StepResult[];
}

// Reused for both the original execution and, when present, the healed
// re-execution (see HealingCard) -- one rendering implementation for
// "a list of StepResult", not duplicated per context.
export function StepResultsList({ steps }: StepResultsListProps) {
  if (steps.length === 0) {
    return <p className="text-sm text-slate-500">No step results reported.</p>;
  }

  return (
    <ol data-testid="step-results" className="space-y-2">
      {steps.map((step) => (
        <li
          key={step.stepIndex}
          className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2 text-sm"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-slate-200">
              {step.stepIndex + 1}. {step.type}
              {step.id && <span className="text-slate-500"> ({step.id})</span>}
            </span>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-slate-500">{step.durationMs}ms</span>
              <StatusBadge label={statusLabel(step.status)} tone={statusTone(step.status)} />
            </div>
          </div>
          {step.error && (
            <p className="mt-1 text-red-400 break-words">{step.error}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
