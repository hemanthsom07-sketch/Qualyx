import { useState } from "react";

import type { ExecutionRun } from "../api/types";
import { statusLabel, statusTone } from "../lib/status";
import { DiagnosisCard } from "./DiagnosisCard";
import { ExplanationCard } from "./ExplanationCard";
import { FailureEvidenceCard } from "./FailureEvidenceCard";
import { HealingCard } from "./HealingCard";
import { StatusBadge } from "./StatusBadge";

interface ExecutionHistoryRecordProps {
  run: ExecutionRun;
  /**
   * Stage 10: true when this record is the target of a
   * /tests/:testId/history#<run.id> link from Recurring Failure
   * Signatures (see RecurringSignaturesList/TestAnalysisPage) --
   * visually emphasizes the row and starts it expanded, since that's
   * exactly the record the user followed a link to inspect.
   */
  highlighted?: boolean;
}

// DOM anchor id shared between this component (the target) and
// RecurringSignaturesList (the link source) -- kept in one place so
// the two can never drift out of sync with each other.
export function executionAnchorId(runId: string): string {
  return `execution-${runId}`;
}

// Note on scope: ExecutionRun (backend/app/models/execution_run.py)
// deliberately does NOT persist a per-step results array -- only the
// execution-level aggregate (status, failed step id/index, executed
// step count, evidence, diagnosis, explanation, healing). So unlike
// TestDetailPage's live ExecutionSummary, a history record has no
// step-by-step list to show; this renders exactly what's actually
// stored, nothing more. (The one exception: a healing snapshot's
// nested `healed_execution` DOES include a full step list, since
// that's a verbatim copy of a live ExecutionResultOut -- HealingCard
// below renders it exactly as it does on Test Detail.)
//
// Stage 17: DiagnosisCard/HealingCard are only shown when they have
// something to say (has_failure / status !== "not_attempted") --
// mirrors the same fix applied to TestDetailPage's live result, so
// expanding a passing historical run doesn't surface two "nothing
// happened" cards.
export function ExecutionHistoryRecord({ run, highlighted = false }: ExecutionHistoryRecordProps) {
  const [expanded, setExpanded] = useState(highlighted);

  const hasDetail = Boolean(run.evidence || run.diagnosis || run.explanation || run.healing);

  return (
    <li
      id={executionAnchorId(run.id)}
      data-testid="execution-history-record"
      className={`rounded-lg border bg-slate-900/50 ${
        highlighted ? "border-emerald-700 ring-1 ring-emerald-700/50" : "border-slate-800"
      }`}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        disabled={!hasDetail}
        className="w-full px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-500 disabled:cursor-default"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <StatusBadge label={statusLabel(run.status)} tone={statusTone(run.status)} />
            <span className="text-sm text-slate-300">
              {new Date(run.started_at).toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span>{run.duration_ms}ms</span>
            <span>{run.executed_step_count} step(s)</span>
            {hasDetail && <span className="text-slate-500">{expanded ? "▲" : "▼"}</span>}
          </div>
        </div>
        <p className="mt-1 font-mono text-xs text-slate-600 break-all">{run.id}</p>
        {run.failed_step_id !== null && (
          <p className="mt-1 text-sm text-slate-400">
            Failed step: <span className="text-slate-300">{run.failed_step_id}</span>
            {run.failed_step_index !== null && ` (index ${run.failed_step_index})`}
          </p>
        )}
        {run.error && <p className="mt-1 text-sm text-red-400 break-words">{run.error}</p>}
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-slate-800 px-4 py-3">
          {run.explanation && <ExplanationCard explanation={run.explanation} />}
          {run.diagnosis?.has_failure && <DiagnosisCard diagnosis={run.diagnosis} />}
          {run.evidence && <FailureEvidenceCard evidence={run.evidence} />}
          {run.healing && run.healing.status !== "not_attempted" && (
            <HealingCard healing={run.healing} />
          )}
        </div>
      )}
    </li>
  );
}
