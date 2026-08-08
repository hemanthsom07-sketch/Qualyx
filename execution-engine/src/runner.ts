/**
 * Deterministic step runner.
 *
 * Executes a validated Step[] sequentially against a real Chromium
 * browser via Playwright. Fails fast: stops at the first failing step
 * (deterministic, single-pass — no retries, no self-healing, no
 * screenshots/video, per Task 4 scope restrictions).
 *
 * This module performs REAL browser automation. It does not fabricate
 * a passed/failed result — every StepResult here reflects an actual
 * Playwright action outcome.
 */

import { chromium, type Browser, type Page } from "playwright";
import type {
  ErrorCategory,
  ExecutionResult,
  FailureEvidence,
  FailureEvidenceAction,
  RunStepsOptions,
  Step,
  StepResult,
  StepStatus,
} from "./types.js";

const DEFAULT_STEP_TIMEOUT_MS = 5000;

interface StepOutcome {
  status: StepStatus;
  error?: string;
  /** err.name from the caught error, e.g. "TimeoutError" — used for deterministic categorization. */
  errorName?: string;
}

async function runSingleStep(page: Page, step: Step, baseUrl?: string): Promise<StepOutcome> {
  try {
    switch (step.type) {
      case "navigate": {
        const target = baseUrl && !/^https?:\/\//i.test(step.url) ? new URL(step.url, baseUrl).toString() : step.url;
        await page.goto(target, { timeout: DEFAULT_STEP_TIMEOUT_MS });
        return { status: "passed" };
      }
      case "click": {
        await page.click(step.selector, { timeout: DEFAULT_STEP_TIMEOUT_MS });
        return { status: "passed" };
      }
      case "fill": {
        await page.fill(step.selector, step.value, { timeout: DEFAULT_STEP_TIMEOUT_MS });
        return { status: "passed" };
      }
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const name = err instanceof Error ? err.name : undefined;
    return { status: "failed", error: message, errorName: name };
  }
}

/**
 * Safe, redacted summary of a step's input for evidence purposes.
 * Deliberately never includes FillStep's `value` (may be a password or
 * other sensitive form input) — only structural information (selector,
 * url) that isn't itself a secret.
 */
function buildActionSummary(step: Step): FailureEvidenceAction {
  switch (step.type) {
    case "navigate":
      return { url: step.url };
    case "click":
    case "fill":
      return { selector: step.selector };
  }
}

/**
 * Deterministic error categorization based on empirically-observed
 * Playwright error shapes (see execution-engine/README.md for the
 * exact message samples this was derived from). Only classifies when
 * the evidence genuinely supports it — falls back to "unknown" rather
 * than guessing.
 *
 * Never returns "assertion" or "validation": the current engine has no
 * assertion/validation step type, so there is no real signal that
 * would justify either category today.
 */
function categorizeError(stepType: Step["type"], errorName: string | undefined, message: string): ErrorCategory {
  const isTimeout = errorName === "TimeoutError" || /Timeout \d+ms exceeded/.test(message);

  if (stepType === "navigate") {
    if (/net::ERR_/.test(message)) return "network";
    if (isTimeout) return "navigation";
    return "unknown";
  }

  // click / fill
  if (/waiting for locator\(/.test(message) && isTimeout) return "selector";
  if (/parsing css selector|Unexpected token/i.test(message)) return "selector";
  if (isTimeout) return "timeout";
  return "unknown";
}

/**
 * Runs a validated sequence of steps against a fresh headless Chromium
 * page. Stops at the first failure (deterministic single pass).
 *
 * This is the programmatic entry point other code (the CLI, the
 * stdin/stdout runner used by the Backend, or tests) should call.
 *
 * @param steps validated Step[] (see validate.ts — call validateSteps()
 *              on untrusted input before passing it here)
 * @param optionsOrBaseUrl either a RunStepsOptions object (preferred,
 *              e.g. `{ baseUrl }`) or, for backward compatibility with
 *              Task 4 callers/tests, a bare baseUrl string.
 */
export async function runSteps(
  steps: Step[],
  optionsOrBaseUrl?: RunStepsOptions | string
): Promise<ExecutionResult> {
  const options: RunStepsOptions =
    typeof optionsOrBaseUrl === "string" ? { baseUrl: optionsOrBaseUrl } : optionsOrBaseUrl ?? {};
  const { baseUrl } = options;

  const startedAt = new Date();
  const stepResults: StepResult[] = [];
  let overallStatus: "passed" | "failed" = "passed";
  let failedStepIndex: number | null = null;
  let failedStepId: string | null = null;
  let error: string | null = null;
  let evidence: FailureEvidence | null = null;

  let browser: Browser | undefined;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    for (let index = 0; index < steps.length; index += 1) {
      const step = steps[index];
      const stepStart = Date.now();
      const outcome = await runSingleStep(page, step, baseUrl);
      const durationMs = Date.now() - stepStart;

      stepResults.push({
        stepIndex: index,
        ...(step.id !== undefined ? { id: step.id } : {}),
        type: step.type,
        status: outcome.status,
        durationMs,
        ...(outcome.error ? { error: outcome.error } : {}),
      });

      if (outcome.status === "failed") {
        overallStatus = "failed";
        failedStepIndex = index;
        // Never fabricated: null when the failed step had no id.
        failedStepId = step.id ?? null;
        error = outcome.error ?? "Step failed with no error message";

        // Best-effort, never fabricated: page.url() can itself fail to
        // read in rare edge cases (e.g. context already tearing down).
        let pageUrl: string | null = null;
        try {
          pageUrl = page.url();
        } catch {
          pageUrl = null;
        }

        evidence = {
          failedStepId,
          failedStepIndex: index,
          stepType: step.type,
          action: buildActionSummary(step),
          errorMessage: outcome.error ?? "Step failed with no error message",
          errorCategory: categorizeError(step.type, outcome.errorName, outcome.error ?? ""),
          pageUrl,
          // Never available on a genuine failure with the current engine
          // (Playwright doesn't hand back a Response on a throwing
          // goto) — kept for schema completeness, not fabricated.
          httpStatus: null,
          executedStepCount: stepResults.length,
          stepDurationMs: durationMs,
        };

        break; // fail-fast: deterministic single pass, no retries/healing
      }
    }
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  const finishedAt = new Date();

  return {
    status: overallStatus,
    steps: stepResults,
    failedStepIndex,
    failedStepId,
    error,
    executedStepCount: stepResults.length,
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
    durationMs: finishedAt.getTime() - startedAt.getTime(),
    evidence,
  };
}
