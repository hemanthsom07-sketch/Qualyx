import { test } from "node:test";
import assert from "node:assert/strict";
import { validateSteps } from "../src/validate.js";
import { StepValidationError } from "../src/types.js";

test("validateSteps accepts a well-formed navigate/click/fill sequence", () => {
  const steps = validateSteps([
    { type: "navigate", url: "https://example.com" },
    { type: "click", selector: "#submit" },
    { type: "fill", selector: "#email", value: "user@example.com" },
  ]);
  assert.equal(steps.length, 3);
  assert.equal(steps[0].type, "navigate");
  assert.equal(steps[1].type, "click");
  assert.equal(steps[2].type, "fill");
});

test("validateSteps rejects a non-array input", () => {
  assert.throws(() => validateSteps({ not: "an array" }), StepValidationError);
});

test("validateSteps rejects an empty array", () => {
  assert.throws(() => validateSteps([]), StepValidationError);
});

test("validateSteps rejects an unknown step type", () => {
  assert.throws(() => validateSteps([{ type: "hover", selector: "#x" }]), StepValidationError);
});

test("validateSteps rejects a navigate step missing url", () => {
  assert.throws(() => validateSteps([{ type: "navigate" }]), StepValidationError);
});

test("validateSteps rejects a click step with empty selector", () => {
  assert.throws(() => validateSteps([{ type: "click", selector: "" }]), StepValidationError);
});

test("validateSteps rejects a fill step missing selector", () => {
  assert.throws(() => validateSteps([{ type: "fill", value: "hi" }]), StepValidationError);
});

test("validateSteps rejects a fill step with non-string value", () => {
  assert.throws(() => validateSteps([{ type: "fill", selector: "#x", value: 123 }]), StepValidationError);
});
