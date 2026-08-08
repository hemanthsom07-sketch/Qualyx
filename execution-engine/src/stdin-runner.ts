/**
 * Stdin/stdout JSON entry point — the Backend ↔ Execution Engine boundary
 * for Task 6.
 *
 * This is a SEPARATE entry point from src/index.ts (the file-based CLI),
 * added specifically so the Python backend can invoke the engine as a
 * subprocess without duplicating any browser-execution logic in Python.
 * src/index.ts is untouched and keeps working exactly as before.
 *
 * Protocol:
 *   stdin  (JSON): { "steps": [...], "baseUrl"?: string }
 *   stdout (JSON): either
 *     - a well-formed ExecutionResult (see types.ts), when the input
 *       steps were valid and execution ran (whether it passed or failed)
 *     - { "error": "validation_error" | "invalid_json", "message": string }
 *       when the input itself could not be validated/parsed
 *
 * Exit codes:
 *   0 — execution ran, status "passed"
 *   1 — execution ran, status "failed" (a normal, well-formed result —
 *       NOT a crash; the backend should still return this as a 200 with
 *       the ExecutionResult body)
 *   2 — input could not be validated (bad JSON or bad step shape) — the
 *       backend should treat this as a client-facing validation error
 *   3 — unexpected internal error in the engine itself — the backend
 *       should treat this as an upstream/engine failure
 *
 * No diagnosis/classification happens here — this only reports what
 * happened, per Task 6 §C.
 */

import { validateSteps } from "./validate.js";
import { runSteps } from "./runner.js";
import { StepValidationError } from "./types.js";

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf-8");
}

async function main(): Promise<void> {
  const raw = await readStdin();

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    process.stdout.write(
      JSON.stringify({
        error: "invalid_json",
        message: err instanceof Error ? err.message : String(err),
      })
    );
    process.exitCode = 2;
    return;
  }

  const { steps: stepsRaw, baseUrl } = (parsed ?? {}) as { steps?: unknown; baseUrl?: string };

  let steps;
  try {
    steps = validateSteps(stepsRaw);
  } catch (err) {
    if (err instanceof StepValidationError) {
      process.stdout.write(JSON.stringify({ error: "validation_error", message: err.message }));
      process.exitCode = 2;
      return;
    }
    throw err;
  }

  const result = await runSteps(steps, baseUrl ? { baseUrl } : undefined);
  process.stdout.write(JSON.stringify(result));
  process.exitCode = result.status === "passed" ? 0 : 1;
}

main().catch((err) => {
  process.stdout.write(
    JSON.stringify({
      error: "unexpected_error",
      message: err instanceof Error ? err.message : String(err),
    })
  );
  process.exitCode = 3;
});
