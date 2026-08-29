import { Link } from "react-router-dom";

import type { RecurringSignature } from "../api/types";
import { executionAnchorId } from "./ExecutionHistoryRecord";

interface RecurringSignaturesListProps {
  /** recurring_signatures, already confirmed non-empty by the caller. */
  signatures: RecurringSignature[];
  /** Used to build links into this test's Execution History. */
  testId: string;
}

// Each signature represents a specific step+classification combination
// that recurred across the analyzed window (see
// backend/app/schemas/flaky_analysis.py: RecurringSignatureOut) -- shown
// as one card per signature so the recurring pattern reads clearly,
// rather than a dense table.
//
// Stage 10: first_execution_id/last_execution_id are now links into
// Execution History rather than inert text -- the same execution ids
// already exist as ExecutionRun.id there, they just had nothing to
// point at (ExecutionHistoryRecord didn't display or anchor its own id
// until this stage).
export function RecurringSignaturesList({ signatures, testId }: RecurringSignaturesListProps) {
  return (
    <ul data-testid="recurring-signatures" className="space-y-2">
      {signatures.map((sig, index) => (
        <li
          key={`${sig.failed_step_id}-${index}`}
          className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2 text-sm"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-slate-200">{sig.failed_step_id}</span>
            <span className="text-slate-400">
              {sig.occurrence_count}&times; recurring
            </span>
          </div>
          {sig.classification && (
            <p className="mt-1 text-slate-400">Classification: {sig.classification}</p>
          )}
          <p className="mt-1 text-slate-500">
            <Link
              to={`/tests/${testId}/history#${executionAnchorId(sig.first_execution_id)}`}
              className="underline hover:text-slate-300"
            >
              {sig.first_execution_id}
            </Link>{" "}
            →{" "}
            <Link
              to={`/tests/${testId}/history#${executionAnchorId(sig.last_execution_id)}`}
              className="underline hover:text-slate-300"
            >
              {sig.last_execution_id}
            </Link>
          </p>
        </li>
      ))}
    </ul>
  );
}
