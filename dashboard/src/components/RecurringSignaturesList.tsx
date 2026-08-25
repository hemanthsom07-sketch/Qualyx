import type { RecurringSignature } from "../api/types";

interface RecurringSignaturesListProps {
  /** recurring_signatures, already confirmed non-empty by the caller. */
  signatures: RecurringSignature[];
}

// Each signature represents a specific step+classification combination
// that recurred across the analyzed window (see
// backend/app/schemas/flaky_analysis.py: RecurringSignatureOut) -- shown
// as one card per signature so the recurring pattern reads clearly,
// rather than a dense table.
export function RecurringSignaturesList({ signatures }: RecurringSignaturesListProps) {
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
            {sig.first_execution_id} → {sig.last_execution_id}
          </p>
        </li>
      ))}
    </ul>
  );
}
