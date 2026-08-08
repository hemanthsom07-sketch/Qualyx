# Qualyx Execution Engine (Claude 2 — Task 4 + Task 6 + Task 8 + Execution Evidence Foundation)

Ownership: Claude 2 (Backend, Database, Playwright Execution Engine, Orchestration).

## Scope

A small, deterministic, single-pass runner that executes exactly three
step types against a real headless Chromium browser via Playwright:

- `navigate` — go to a URL
- `click` — click an element by selector
- `fill` — fill an input by selector with a value

Fail-fast: execution stops at the first failing step. No retries, no
self-healing, no screenshots/video, no distributed execution, no queues.
Those remain out of scope — Claude 3 owns diagnosis/healing.

## Two entry points

- **`src/index.ts`** — file-based CLI (Task 4). Unchanged behavior:
  `tsx src/index.ts <path-to-test-json> [baseUrl]`.
- **`src/stdin-runner.ts`** — JSON stdin/stdout entry point (Task 6),
  added specifically so the Python backend can invoke the engine as a
  subprocess without any browser logic living in Python. See "Backend
  boundary protocol" below.

Both call the same programmatic core, `runSteps(steps, options?)` in
`src/runner.ts`, which also still accepts a bare `baseUrl` string for
backward compatibility with Task 4 callers.

## Backend boundary protocol (Task 6)

```
stdin  (JSON): { "steps": [...], "baseUrl"?: string }
stdout (JSON): a well-formed ExecutionResult, OR
               { "error": "validation_error" | "invalid_json", "message": string }

exit codes:
  0 — execution ran, status "passed"
  1 — execution ran, status "failed" (a normal, well-formed result)
  2 — input could not be validated (bad JSON or bad step shape)
  3 — unexpected internal engine error
```

## ExecutionResult contract

```ts
interface ExecutionResult {
  status: "passed" | "failed";
  steps: StepResult[];        // additive detail retained from Task 4
  failedStepIndex: number | null;
  failedStepId: string | null;   // Task 8 — never fabricated
  error: string | null;
  executedStepCount: number;
  startedAt: string;          // additive detail retained from Task 4
  finishedAt: string;         // additive detail retained from Task 4
  durationMs: number;         // additive detail retained from Task 4
  evidence: FailureEvidence | null;   // Execution Evidence Foundation — see below
}
```

`status`, `failedStepIndex`, `error`, and `executedStepCount` are the
Task 6-required minimum. No diagnosis/classification (application bug
vs. broken test) happens here — that's Claude 3's Intelligence module.

## Execution Evidence Foundation

`evidence` is `null` on a passing run. On a failing run, it's a
structured, deterministic description of the failure — never fabricated,
never a diagnosis:

```ts
interface FailureEvidence {
  failedStepId: string | null;      // same value as the top-level field
  failedStepIndex: number;          // same value as the top-level field
  stepType: "navigate" | "click" | "fill";
  action: { url?: string; selector?: string };  // NEVER includes a fill value
  errorMessage: string;
  errorCategory: "assertion" | "selector" | "navigation" | "timeout"
               | "network" | "validation" | "unknown";
  pageUrl: string | null;           // page.url() at the moment of failure
  httpStatus: number | null;        // see note below — currently always null
  executedStepCount: number;
  stepDurationMs: number;
}
```

**Error categorization** is deterministic, derived from empirically
observed Playwright error shapes (not guessed):

| Step type | Signal | Category |
|---|---|---|
| navigate | message matches `net::ERR_*` | `network` |
| navigate | `TimeoutError` (no response ever received) | `navigation` |
| click/fill | `TimeoutError` + message contains `waiting for locator(` | `selector` |
| click/fill | message contains `parsing css selector` / `Unexpected token` | `selector` |
| click/fill | `TimeoutError`, no locator-wait pattern matched | `timeout` |
| anything else | — | `unknown` |

`assertion` and `validation` are part of the type for schema
completeness but are **never produced today** — the engine has no
assertion or validation step type yet, so there is no genuine signal
that would justify either category. Adding one without a real signal
would be fabrication, which this task explicitly avoids.

**`httpStatus` is currently always `null`.** Playwright only returns a
`Response` object from `page.goto()` when the navigation *doesn't*
throw. A failing navigate (timeout or network error) throws before any
`Response` exists, so there is no genuine HTTP status to report for a
failure with the current engine design. The field is kept for schema
completeness/future use rather than omitted, but it is never fabricated.

**Redaction:** `action` only ever exposes `url` (navigate) or `selector`
(click/fill) — a `fill` step's `value` is never included anywhere in
`evidence`, `steps[]`, or logs, since it may be a password or other
sensitive input. This was verified with a real end-to-end test using a
literal password-like value (see "Verification actually performed").

## Structure

```
execution-engine/
  package.json
  tsconfig.json
  src/
    types.ts         — Step / StepResult / ExecutionResult / FailureEvidence / RunStepsOptions
    validate.ts       — pure, synchronous step-shape validation (no browser)
    runner.ts          — real Playwright execution (fail-fast, sequential, evidence collection)
    index.ts            — file-based CLI (Task 4, unchanged)
    stdin-runner.ts      — JSON stdin/stdout entry point (Task 6, unchanged)
  tests/
    validate.test.ts     — unit tests for validation (no browser)
    runner.test.ts         — integration tests: real local HTTP server +
                             real headless Chromium (no external network),
                             including Execution Evidence Foundation tests
    stdin-runner.test.ts    — spawns the real stdin-runner subprocess and
                              exercises the exact protocol the backend uses
```

## Setup

```bash
cd execution-engine
npm install
npx playwright install chromium   # downloads the Chromium browser binary
```

## Run tests

```bash
npm test
```

## Run the CLI prototype directly

```bash
npx tsx src/index.ts path/to/test.json [baseUrl]
```

## Run the stdin/stdout entry point directly (what the backend calls)

```bash
echo '{"steps":[{"type":"navigate","url":"https://example.com"}]}' | npx tsx src/stdin-runner.ts
```

## Verification actually performed (in the development sandbox)

This sandbox had no outbound network access for installing packages via
`npm install`/`npx playwright install` (the npm registry itself returned
a 403 here), but it turned out to already have a global Playwright
install with a working, launchable Chromium binary pre-provisioned.
Using that (symlinked in temporarily, then removed before packaging —
**not part of the deliverable**), the following was genuinely executed:

- **Task 4 + Task 6 full suite:** `node --import tsx --test tests/*.test.ts`
  → **19/19 tests passed**, including:
  - Real navigate/fill/click integration tests against a real local
    `node:http` server + real headless Chromium
  - A real fail-fast test (nonexistent selector → stops after that step)
  - New Task 6 tests asserting `failedStepIndex`/`error`/`executedStepCount`
    on both passing and failing runs
  - New `stdin-runner.test.ts` tests that spawn the actual entry point as
    a real child process and assert on its real stdout/exit code for
    passing (0), failing (1), invalid-steps (2), and invalid-JSON (2) cases
- **One pre-existing Task 4 assertion was updated**, not left broken:
  `runner.test.ts`'s first test asserted `result.failedStepIndex === undefined`
  (via `node:assert/strict`, which is `===`). Task 6 §C requires
  `failedStepIndex` to be an explicit `number | null` rather than an
  optional/undefined field, so `undefined` no longer occurs — the
  assertion was changed to `=== null`, which verifies the identical
  underlying behavior (no failure occurred). This is called out here and
  in the Task 6 report rather than glossed over.
- **Backend ↔ Engine boundary itself:** verified end-to-end with a
  stdlib-only Python harness that replicates `execution_client.py`'s
  exact subprocess call, run against the real `stdin-runner.ts` with real
  Chromium — genuine passed, failed, and validation-error responses were
  observed with the correct exit codes (0, 1, 2). This was necessary
  because the Python backend's own dependencies (`fastapi`, `pydantic`,
  `pytest`) could not be installed in this sandbox (no network) to run
  `pytest` directly — see the Backend README/Task 6 report for that
  limitation.
- **Task 8 stable-ID + Execution Evidence Foundation:** re-ran the full
  suite after these additions → **39/39 tests passed**, including 9 new
  evidence-specific tests exercising: `evidence === null` on success,
  `network` category on a real unreachable host, `navigation` category
  on a genuine navigation timeout (a real TCP server that accepts but
  never responds), `selector` category on both a missing-selector
  timeout and an invalid CSS selector syntax error, `failedStepId`/
  `failedStepIndex` consistency with the top-level fields, backward
  compatibility for id-less steps, and — critically — a real test that
  fills a literal password-like string into a missing selector and
  asserts it never appears anywhere in the serialized result. The same
  stdlib-only Python harness was re-run to confirm the redaction and
  evidence shape survive the real subprocess boundary end-to-end.

**What could not be verified in the sandbox:** a clean `npm install` /
`npx playwright install`. Anyone running this for real should follow the
Setup section above in a normal networked environment.

## Known limitations

- Fixed 5-second timeout per browser step; not configurable yet.
- No screenshot/trace capture (out of scope).
- `TestDefinition.content` step identity is positional (array index) —
  see cross-module requirements in the Task 6 report regarding stable
  step IDs for future diagnosis mapping.
