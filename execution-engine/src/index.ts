/**
 * CLI entry point.
 *
 * Usage:
 *   tsx src/index.ts <path-to-test-json> [baseUrl]
 *
 * Reads a JSON file shaped like:
 *   { "steps": [ { "type": "navigate", "url": "..." }, ... ] }
 *
 * Prints the ExecutionResult as JSON to stdout and exits 0 if the run
 * passed, 1 if it failed or the input was invalid.
 *
 * This is a standalone prototype invocation for Task 4. It is NOT wired
 * into the backend's HTTP API in this milestone (see README.md — "Backend
 * / Execution Boundary" and cross-module requirements).
 */

import { readFile } from "node:fs/promises";
import { validateSteps } from "./validate.js";
import { runSteps } from "./runner.js";
import { StepValidationError } from "./types.js";

async function main(): Promise<void> {
  const [filePath, baseUrl] = process.argv.slice(2);

  if (!filePath) {
    console.error("Usage: tsx src/index.ts <path-to-test-json> [baseUrl]");
    process.exitCode = 1;
    return;
  }

  let parsed: unknown;
  try {
    const raw = await readFile(filePath, "utf-8");
    parsed = JSON.parse(raw);
  } catch (err) {
    console.error(`Failed to read/parse ${filePath}: ${err instanceof Error ? err.message : String(err)}`);
    process.exitCode = 1;
    return;
  }

  const stepsRaw = (parsed as { steps?: unknown })?.steps;

  let steps;
  try {
    steps = validateSteps(stepsRaw);
  } catch (err) {
    if (err instanceof StepValidationError) {
      console.error(`Invalid step definition: ${err.message}`);
      process.exitCode = 1;
      return;
    }
    throw err;
  }

  const result = await runSteps(steps, baseUrl);
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.status === "passed" ? 0 : 1;
}

main().catch((err) => {
  console.error("Unexpected error:", err);
  process.exitCode = 1;
});
