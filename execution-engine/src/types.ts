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

/**
 * Deterministic error category for a failed step, based on
 * empirically-observed Playwright error shapes (see runner.ts's
 * categorizeError()). Only ever set when the evidence genuinely
 * supports it — never guessed.
 *
 * "assertion" and "validation" are included for schema completeness
 * (a future step type might need them) but the current engine only
 * ever produces navigate/click/fill actions, so it never emits these
 * two today — see README.md.
 */
export type ErrorCategory =
  | "assertion"
  | "selector"
  | "navigation"
  | "timeout"
  | "network"
  | "validation"
  | "unknown";

/**
 * Safe, redacted summary of the failed step's input. Deliberately
 * excludes FillStep's `value` — it may be a password or other
 * sensitive form input, so it is never included in evidence, on
 * failure or otherwise.
 */
export interface FailureEvidenceAction {
  /** Present for a failed "navigate" step. */
  url?: string;
  /** Present for a failed "click" or "fill" step. */
  selector?: string;
}

/**
 * Structured, deterministic evidence about a failed step, intended to
 * give Claude 3's diagnosis layer enough to work with — WITHOUT Claude 2
 * performing any classification of "application bug" vs "broken test"
 * itself. Every field is either a fact directly observable from the
 * Playwright execution, or null when that fact genuinely isn't
 * available. Nothing here is fabricated.
 */
export interface FailureEvidence {
  failedStepId: string | null;
  failedStepIndex: number;
  stepType: StepType;
  action: FailureEvidenceAction;
  errorMessage: string;
  errorCategory: ErrorCategory;
  /** page.url() at the moment of failure, if it could be read. */
  pageUrl: string | null;
  /**
   * HTTP response status for the failed step, if genuinely available.
   * With the current engine, a *failing* navigate never yields a
   * Response object (Playwright throws before one exists on timeout or
   * network error), so this is always null today — kept for schema
   * completeness. Never fabricated.
   */
  httpStatus: number | null;
  executedStepCount: number;
  stepDurationMs: number;
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
 * Added in this task (Execution Evidence Foundation): `evidence`
 * (FailureEvidence | null) — additive. Null on a passing run. On a
 * failing run, a structured, non-fabricated description of what
 * happened, for Claude 3's diagnosis layer to consume. This is NOT a
 * diagnosis: no bug/broken-test/environment classification happens
 * here, only deterministic facts (see FailureEvidence).
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
  evidence: FailureEvidence | null;
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
