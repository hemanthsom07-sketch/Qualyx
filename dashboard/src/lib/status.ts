// Small shared helper: maps the raw status strings the Backend actually
// returns (execution: "passed"/"failed"; step: "passed"/"failed";
// healing: "healed"/"healing_failed"/"not_attempted"/"not_eligible"/
// "no_candidate" -- see backend/tests/test_healing_workflow.py) to a
// visual tone. Never assumes a fixed enum beyond what's observed in the
// backend's own tests -- unrecognized strings fall back to "neutral"
// and are still displayed verbatim by StatusBadge, never hidden.

export type StatusTone = "pass" | "fail" | "neutral";

const PASS_STATUSES = new Set(["passed", "healed"]);
const FAIL_STATUSES = new Set(["failed", "healing_failed"]);

export function statusTone(status: string): StatusTone {
  if (PASS_STATUSES.has(status)) return "pass";
  if (FAIL_STATUSES.has(status)) return "fail";
  return "neutral";
}

// "healing_failed" -> "HEALING FAILED", "not_attempted" -> "NOT ATTEMPTED"
export function statusLabel(status: string): string {
  return status.replace(/_/g, " ").toUpperCase();
}
