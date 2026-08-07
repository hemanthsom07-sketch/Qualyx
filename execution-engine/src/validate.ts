/**
 * Step validation — pure, synchronous, no browser/Playwright dependency.
 *
 * This validates SHAPE only (matches the backend's mirrored step schema
 * in app/schemas/test_definition.py). It performs no execution and makes
 * no claim about whether a step would actually succeed against a real
 * page — that's runner.ts's job.
 */

import type { Step } from "./types.js";
import { StepValidationError } from "./types.js";

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

/**
 * Extracts an optional stable step `id` if present and valid, otherwise
 * undefined. Never fabricates one. A present-but-invalid `id` (wrong
 * type) is rejected rather than silently dropped, so a caller doesn't
 * mistake malformed input for "no id provided".
 */
function extractOptionalId(step: Record<string, unknown>, index: number): string | undefined {
  if (step.id === undefined) {
    return undefined;
  }
  if (typeof step.id !== "string" || step.id.length === 0) {
    throw new StepValidationError(`Step ${index}: "id", if present, must be a non-empty string`);
  }
  return step.id;
}

function validateStep(raw: unknown, index: number): Step {
  if (typeof raw !== "object" || raw === null) {
    throw new StepValidationError(`Step ${index}: expected an object, got ${typeof raw}`);
  }

  const step = raw as Record<string, unknown>;
  const id = extractOptionalId(step, index);

  switch (step.type) {
    case "navigate":
      if (!isNonEmptyString(step.url)) {
        throw new StepValidationError(`Step ${index} (navigate): "url" must be a non-empty string`);
      }
      return { ...(id !== undefined ? { id } : {}), type: "navigate", url: step.url };

    case "click":
      if (!isNonEmptyString(step.selector)) {
        throw new StepValidationError(`Step ${index} (click): "selector" must be a non-empty string`);
      }
      return { ...(id !== undefined ? { id } : {}), type: "click", selector: step.selector };

    case "fill":
      if (!isNonEmptyString(step.selector)) {
        throw new StepValidationError(`Step ${index} (fill): "selector" must be a non-empty string`);
      }
      if (typeof step.value !== "string") {
        throw new StepValidationError(`Step ${index} (fill): "value" must be a string`);
      }
      return { ...(id !== undefined ? { id } : {}), type: "fill", selector: step.selector, value: step.value };

    default:
      throw new StepValidationError(
        `Step ${index}: unknown step type "${String(step.type)}" (expected navigate | click | fill)`
      );
  }
}

/**
 * Validates a raw, untyped list of steps into a typed Step[].
 * Throws StepValidationError on the first invalid step found.
 */
export function validateSteps(raw: unknown): Step[] {
  if (!Array.isArray(raw)) {
    throw new StepValidationError("Expected an array of steps");
  }
  if (raw.length === 0) {
    throw new StepValidationError("Step list must not be empty");
  }
  return raw.map((step, index) => validateStep(step, index));
}
