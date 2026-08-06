# Qualyx Execution Engine (Claude 2 — Task 4 Milestone)

Ownership: Claude 2 (Backend, Database, Playwright Execution Engine, Orchestration).

## Scope of this milestone

A small, deterministic, single-pass runner that executes exactly three
step types against a real headless Chromium browser via Playwright:

- `navigate` — go to a URL
- `click` — click an element by selector
- `fill` — fill an input by selector with a value

It fails fast: execution stops at the first failing step. No retries, no
self-healing, no screenshots/video, no distributed execution, no queues.
Those are explicitly out of scope per Task 4 and belong to later
milestones or other modules (Claude 3 owns diagnosis/healing).

This is a **standalone prototype**, invoked via CLI (`src/index.ts`). It
is **not** wired into the backend's HTTP API in this milestone — see
"Backend / Execution Boundary" in the Task 4 report for why, and the
cross-module requirements section for what a future wiring milestone
would need.

## Structure

```
execution-engine/
  package.json
  tsconfig.json
  src/
    types.ts      — Step / StepResult / ExecutionResult type definitions
    validate.ts   — pure, synchronous step-shape validation (no browser)
    runner.ts      — real Playwright execution (fail-fast, sequential)
    index.ts       — CLI entry point
  tests/
    validate.test.ts  — unit tests for validation (no browser)
    runner.test.ts     — integration tests using a real local HTTP server
                         + real headless Chromium (no external network)
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

Where `test.json` looks like:

```json
{
  "steps": [
    { "type": "navigate", "url": "https://example.com" },
    { "type": "fill", "selector": "#email", "value": "user@example.com" },
    { "type": "click", "selector": "#submit" }
  ]
}
```

## Verification actually performed (in the development sandbox)

This sandbox had no outbound network access for installing packages, but
it turned out to already have a global Playwright installation with a
working, launchable Chromium binary pre-provisioned. Using that, the
following was **genuinely executed, not simulated**:

- `npm test` equivalent (`node --import tsx --test tests/*.test.ts`):
  **12/12 tests passed**, including two integration tests that launch
  real headless Chromium against a real local HTTP server (`node:http`,
  localhost only) and perform real `navigate`/`fill`/`click` actions, plus
  a real fail-fast test using a selector that genuinely does not exist on
  the page (asserting the run stops after that step and never attempts
  the third step).
- The CLI (`src/index.ts`) was run directly against a real local server
  and produced a genuine `"status": "passed"` result (exit code 0).
- The CLI was also run against `https://example.com` to sanity-check
  outbound-network failure handling. In this specific sandbox, outbound
  domains are intercepted by an egress proxy that returns a 403
  "host not in allowlist" HTML page rather than refusing the connection —
  so `navigate` reported success (it got *a* page) while the subsequent
  `click` genuinely failed on timeout because the block page has no such
  element. This is disclosed for transparency, not glossed over: it does
  not affect the validity of the localhost-based test suite above, which
  has no external network dependency.

**What could not be verified in the sandbox:** installing Playwright via
`npm install` (the npm registry itself is blocked here — confirmed via a
403 from `registry.npmjs.org`), and downloading a browser binary via
`npx playwright install`. The sandbox happened to already have a
compatible Chromium binary pre-provisioned outside of any project
`node_modules`, which is how real verification was still possible. This
is **not** something to rely on in a clean environment — anyone running
this for real should run `npm install && npx playwright install chromium`
as documented above.

## Known limitations

- Fixed 5-second timeout per step; not configurable yet.
- No screenshot/trace capture (explicitly out of scope for Task 4).
- No structured mapping yet from a `TestDefinition.content` step back to
  a backend-recognized step-level identifier beyond array index — see
  cross-module requirements.
- Not wired to the backend; invoked standalone for this milestone.
