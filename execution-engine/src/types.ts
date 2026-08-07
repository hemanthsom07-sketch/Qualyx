/**
 * Minimal step and result types for the Task 4 deterministic runner
 * prototype.
 *
 * Scope: exactly the three step types required by Task 4 (navigate,
 * click, fill). This is intentionally NOT the frozen cross-module
 * TestDefinition / ExecutionResult contract — see README.md for the
 * cross-module requirements this milestone surfaces.
 */

export type StepType = "navigate" | "click" | "fill";

/**
 * `id` is an OPTIONAL stable step identifier, originating from Claude 3's
 * Intelligence module (Task 7: generated step.id, deterministic from the
 * Recorder event). The Execution Engine never generates or mutates this
 * value — it only carries it through unchanged so a future diagnosis
 * layer can map a failure back to the exact generated step.
 *
 * Existing steps/tests without an `id` continue to work: it's optional
 * everywhere and simply propagates as `undefined`/absent.
 */
export interface NavigateStep {
  id?: string;
  type: "navigate";
  url: string;
}

export interface ClickStep {
  id?: string;
  type: "click";
  selector: string;
}

export interface FillStep {
  id?: string;
  type: "fill";
  selector: string;
  value: string;
}

export type Step = NavigateStep | ClickStep | FillStep;

export type StepStatus = "passed" | "failed";

export interface StepResult {
  stepIndex: number;
  /** Carried through unchanged from the corresponding input Step, if present. */
  id?: string;
  type: StepType;
  status: StepStatus;
  durationMs: number;
  error?: string;
}

export type ExecutionStatus = "passed" | "failed";

/**
 * ExecutionResult — Backend boundary contract.
 *
 * Required (Task 6 §C): status, failedStepIndex (number | null),
 * error (string | null), executedStepCount.
 *
 * Added in Task 8: failedStepId (string | null) — additive, does not
 * replace failedStepIndex. Identifies the Intelligence-generated stable
 * step ID (see NavigateStep/ClickStep/FillStep `id?`) of the failed
 * step, when that step had one. Never fabricated: if the failed step
 * had no `id`, this is `null`, not a made-up value. On a passing run,
 * this is always `null`.
 *
 * Retained from Task 4 for richer local/CLI use: per-step `steps[]`,
 * `startedAt`/`finishedAt`/`durationMs`. Additive only — nothing from
 * earlier tasks' shape was removed, so existing callers/tests are
 * unaffected.
 *
 * This is NOT a diagnosis contract: no bug/broken-test classification
 * happens here. `error` is the raw failure message from the failing
 * step, nothing more.
 */
export interface ExecutionResult {
  status: ExecutionStatus;
  steps: StepResult[];
  failedStepIndex: number | null;
  failedStepId: string | null;
  error: string | null;
  executedStepCount: number;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
}

export interface RunStepsOptions {
  /** Base URL that relative "navigate" URLs resolve against. */
  baseUrl?: string;
}

/** Thrown by validateSteps() when input does not match the step model. */
export class StepValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StepValidationError";
  }
}
