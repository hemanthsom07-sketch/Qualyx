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

export interface NavigateStep {
  type: "navigate";
  url: string;
}

export interface ClickStep {
  type: "click";
  selector: string;
}

export interface FillStep {
  type: "fill";
  selector: string;
  value: string;
}

export type Step = NavigateStep | ClickStep | FillStep;

export type StepStatus = "passed" | "failed";

export interface StepResult {
  stepIndex: number;
  type: StepType;
  status: StepStatus;
  durationMs: number;
  error?: string;
}

export type ExecutionStatus = "passed" | "failed";

/**
 * ExecutionResult — Task 6 boundary contract with the Backend.
 *
 * Required (Task 6 §C): status, failedStepIndex (number | null),
 * error (string | null), executedStepCount.
 *
 * Retained from Task 4 for richer local/CLI use: per-step `steps[]`,
 * `startedAt`/`finishedAt`/`durationMs`. Additive only — nothing from
 * Task 4's shape was removed, so existing callers/tests are unaffected.
 *
 * This is NOT a diagnosis contract: no bug/broken-test classification
 * happens here. `error` is the raw failure message from the failing
 * step, nothing more.
 */
export interface ExecutionResult {
  status: ExecutionStatus;
  steps: StepResult[];
  failedStepIndex: number | null;
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
