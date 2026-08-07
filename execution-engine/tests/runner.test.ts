/**
 * Integration tests for runner.ts.
 *
 * These spin up a real local HTTP server (Node's built-in http module,
 * localhost only, no external network) serving a small static page, and
 * drive it with a REAL headless Chromium instance via Playwright. This
 * is genuine browser automation — no step outcome is fabricated.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import type { AddressInfo } from "node:net";
import { runSteps } from "../src/runner.js";
import { validateSteps } from "../src/validate.js";

const TEST_PAGE_HTML = `
<!doctype html>
<html>
  <body>
    <form>
      <input id="email" type="email" />
      <button id="submit" type="button" onclick="document.getElementById('result').textContent='clicked'">
        Submit
      </button>
      <div id="result"></div>
    </form>
  </body>
</html>
`;

async function withTestServer(fn: (baseUrl: string) => Promise<void>): Promise<void> {
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(TEST_PAGE_HTML);
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  const baseUrl = `http://127.0.0.1:${port}/`;

  try {
    await fn(baseUrl);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

test("runSteps executes a real navigate/click/fill sequence successfully against a real page", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([
      { type: "navigate", url: baseUrl },
      { type: "fill", selector: "#email", value: "user@example.com" },
      { type: "click", selector: "#submit" },
    ]);

    const result = await runSteps(steps);

    assert.equal(result.status, "passed");
    assert.equal(result.steps.length, 3);
    assert.ok(result.steps.every((s) => s.status === "passed"));
    // Task 6 §C requires failedStepIndex to be an explicit `number | null`
    // rather than Task 4's optional/undefined field — updated accordingly
    // (see Task 6 report). The behavior being verified (no failure
    // occurred) is unchanged.
    assert.equal(result.failedStepIndex, null);
    assert.ok(result.durationMs >= 0);
  });
});

test("runSteps fails fast on a selector that does not exist on the page", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([
      { type: "navigate", url: baseUrl },
      { type: "click", selector: "#does-not-exist" },
      { type: "fill", selector: "#email", value: "should-not-run" },
    ]);

    const result = await runSteps(steps);

    assert.equal(result.status, "failed");
    assert.equal(result.failedStepIndex, 1);
    // fail-fast: the third step must never have been attempted
    assert.equal(result.steps.length, 2);
    assert.equal(result.steps[1].status, "failed");
    assert.ok(result.steps[1].error && result.steps[1].error.length > 0);
  });
});

test("runSteps resolves relative navigate URLs against baseUrl", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([{ type: "navigate", url: "/" }]);
    const result = await runSteps(steps, baseUrl);
    assert.equal(result.status, "passed");
  });
});

test("runSteps reports a failed navigate to an unreachable host", async () => {
  const steps = validateSteps([{ type: "navigate", url: "http://127.0.0.1:1/unreachable" }]);
  const result = await runSteps(steps);
  assert.equal(result.status, "failed");
  assert.equal(result.failedStepIndex, 0);
});

// --- Task 6: ExecutionResult contract additions ---

test("runSteps ExecutionResult includes the Task 6 required fields on success", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([{ type: "navigate", url: baseUrl }]);
    const result = await runSteps(steps);

    assert.equal(result.status, "passed");
    assert.equal(result.failedStepIndex, null);
    assert.equal(result.error, null);
    assert.equal(result.executedStepCount, 1);
  });
});

test("runSteps ExecutionResult includes the Task 6 required fields on failure", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([
      { type: "navigate", url: baseUrl },
      { type: "click", selector: "#does-not-exist" },
      { type: "fill", selector: "#email", value: "should-not-run" },
    ]);

    const result = await runSteps(steps);

    assert.equal(result.status, "failed");
    assert.equal(result.failedStepIndex, 1);
    assert.equal(typeof result.error, "string");
    assert.ok(result.error && result.error.length > 0);
    // executedStepCount counts only attempted steps (fail-fast: 2, not 3)
    assert.equal(result.executedStepCount, 2);
  });
});

test("runSteps accepts an options object (new preferred signature) equivalently to a bare baseUrl string", async () => {
  await withTestServer(async (baseUrl) => {
    const steps = validateSteps([{ type: "navigate", url: "/" }]);
    const result = await runSteps(steps, { baseUrl });
    assert.equal(result.status, "passed");
  });
});
