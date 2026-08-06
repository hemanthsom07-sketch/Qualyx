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

export interface ExecutionResult {
  status: ExecutionStatus;
  steps: StepResult[];
  failedStepIndex?: number;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
}

/** Thrown by validateSteps() when input does not match the step model. */
export class StepValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StepValidationError";
  }
}
