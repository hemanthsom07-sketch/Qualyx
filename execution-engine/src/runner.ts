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
import type { ExecutionResult, Step, StepResult, StepStatus } from "./types.js";

const DEFAULT_STEP_TIMEOUT_MS = 5000;

async function runSingleStep(page: Page, step: Step, baseUrl?: string): Promise<{ status: StepStatus; error?: string }> {
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
    return { status: "failed", error: message };
  }
}

/**
 * Runs a validated sequence of steps against a fresh headless Chromium
 * page. Stops at the first failure (deterministic single pass).
 *
 * @param steps validated Step[] (see validate.ts — call validateSteps()
 *              on untrusted input before passing it here)
 * @param baseUrl optional base URL that relative "navigate" URLs resolve against
 */
export async function runSteps(steps: Step[], baseUrl?: string): Promise<ExecutionResult> {
  const startedAt = new Date();
  const stepResults: StepResult[] = [];
  let overallStatus: "passed" | "failed" = "passed";
  let failedStepIndex: number | undefined;

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
        type: step.type,
        status: outcome.status,
        durationMs,
        ...(outcome.error ? { error: outcome.error } : {}),
      });

      if (outcome.status === "failed") {
        overallStatus = "failed";
        failedStepIndex = index;
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
    ...(failedStepIndex !== undefined ? { failedStepIndex } : {}),
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
    durationMs: finishedAt.getTime() - startedAt.getTime(),
  };
}
