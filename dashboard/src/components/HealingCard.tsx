import type { HealingResult } from "../api/types";
import { statusLabel, statusTone } from "../lib/status";
import { ExecutionSummary } from "./ExecutionSummary";
import { StatusBadge } from "./StatusBadge";

interface HealingCardProps {
  healing: HealingResult;
}

// healing is always present on an /execute response (status
// "not_attempted" on a passing run rather than omitted -- see
// backend/app/schemas/healing.py's docstring), so this always renders,
// but keeps the "nothing happened" case (not_attempted/not_eligible)
// minimal rather than padding it out with empty selector/confidence
// rows that were never populated.
export function HealingCard({ healing }: HealingCardProps) {
  const isMinimalStatus = healing.status === "not_attempted" || healing.status === "not_eligible";

  return (
    <div data-testid="healing-card" className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-medium text-slate-100">Healing</h3>
        <StatusBadge label={statusLabel(healing.status)} tone={statusTone(healing.status)} />
      </div>

      {healing.reason && <p className="mt-2 text-sm text-slate-400">{healing.reason}</p>}

      {!isMinimalStatus && (
        <dl className="mt-3 space-y-1 text-sm">
          {healing.generated_step_id && (
            <Row label="Step" value={healing.generated_step_id} />
          )}
          {healing.original_selector && (
            <Row
              label="Original selector"
              value={
                healing.original_selector_kind
                  ? `${healing.original_selector} (${healing.original_selector_kind})`
                  : healing.original_selector
              }
            />
          )}
          {healing.proposed_selector && (
            <Row
              label="Proposed selector"
              value={
                healing.proposed_selector_kind
                  ? `${healing.proposed_selector} (${healing.proposed_selector_kind})`
                  : healing.proposed_selector
              }
            />
          )}
          <Row label="Applied" value={healing.applied ? "Yes" : "No"} />
          {healing.confidence !== null && (
            <Row label="Confidence" value={healing.confidence.toFixed(2)} />
          )}
        </dl>
      )}

      {healing.healed_execution && (
        <div className="mt-4">
          <ExecutionSummary result={healing.healed_execution} heading="Healed re-execution" />
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-slate-500 shrink-0">{label}:</dt>
      <dd className="text-slate-300 break-words">{value}</dd>
    </div>
  );
}
