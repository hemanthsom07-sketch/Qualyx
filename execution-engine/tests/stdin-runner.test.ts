/**
 * Tests for src/stdin-runner.ts — the Backend ↔ Execution Engine
 * subprocess boundary (Task 6 §E).
 *
 * These spawn the actual compiled/executed entry point as a real child
 * process and communicate with it exactly the way the Python backend
 * will: write JSON to stdin, read JSON + exit code from stdout.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import type { AddressInfo } from "node:net";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ENTRY_POINT = path.join(__dirname, "..", "src", "stdin-runner.ts");

interface SubprocessResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

function runStdinRunner(payload: unknown): Promise<SubprocessResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ["--import", "tsx", ENTRY_POINT], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
    child.on("error", reject);
    child.on("close", (exitCode) => resolve({ exitCode, stdout, stderr }));

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

async function withTestServer(fn: (baseUrl: string) => Promise<void>): Promise<void> {
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end('<html><body><input id="email"/><button id="go">Go</button></body></html>');
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  try {
    await fn(`http://127.0.0.1:${port}/`);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

test("stdin-runner: exit code 0 and full ExecutionResult on a passing run", async () => {
  await withTestServer(async (baseUrl) => {
    const { exitCode, stdout } = await runStdinRunner({
      steps: [
        { type: "navigate", url: baseUrl },
        { type: "fill", selector: "#email", value: "user@example.com" },
      ],
    });

    assert.equal(exitCode, 0);
    const result = JSON.parse(stdout);
    assert.equal(result.status, "passed");
    assert.equal(result.failedStepIndex, null);
    assert.equal(result.error, null);
    assert.equal(result.executedStepCount, 2);
  });
});

test("stdin-runner: exit code 1 and failed ExecutionResult with failedStepIndex on a failing run", async () => {
  await withTestServer(async (baseUrl) => {
    const { exitCode, stdout } = await runStdinRunner({
      steps: [
        { type: "navigate", url: baseUrl },
        { type: "click", selector: "#does-not-exist" },
      ],
    });

    assert.equal(exitCode, 1);
    const result = JSON.parse(stdout);
    assert.equal(result.status, "failed");
    assert.equal(result.failedStepIndex, 1);
    assert.ok(typeof result.error === "string" && result.error.length > 0);
    assert.equal(result.executedStepCount, 2);
  });
});

test("stdin-runner: exit code 2 and validation error payload on malformed steps", async () => {
  const { exitCode, stdout } = await runStdinRunner({
    steps: [{ type: "hover", selector: "#x" }],
  });

  assert.equal(exitCode, 2);
  const payload = JSON.parse(stdout);
  assert.equal(payload.error, "validation_error");
  assert.ok(typeof payload.message === "string" && payload.message.length > 0);
});

test("stdin-runner: exit code 2 on invalid JSON input", async () => {
  const child = spawn(process.execPath, ["--import", "tsx", ENTRY_POINT], {
    stdio: ["pipe", "pipe", "pipe"],
  });
  let stdout = "";
  child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
  child.stdin.write("{not valid json");
  child.stdin.end();

  const exitCode: number | null = await new Promise((resolve) => child.on("close", resolve));

  assert.equal(exitCode, 2);
  const payload = JSON.parse(stdout);
  assert.equal(payload.error, "invalid_json");
});

// --- Task 8: stable step IDs survive the real stdin/stdout subprocess boundary ---

test("stdin-runner: a generated step id survives the boundary and comes back as failedStepId on failure", async () => {
  await withTestServer(async (baseUrl) => {
    const { exitCode, stdout } = await runStdinRunner({
      steps: [
        { id: "gen-nav-1", type: "navigate", url: baseUrl },
        { id: "gen-click-abc", type: "click", selector: "#does-not-exist" },
      ],
    });

    assert.equal(exitCode, 1);
    const result = JSON.parse(stdout);
    assert.equal(result.status, "failed");
    assert.equal(result.failedStepIndex, 1);
    assert.equal(result.failedStepId, "gen-click-abc");
    assert.equal(result.steps[0].id, "gen-nav-1");
    assert.equal(result.steps[1].id, "gen-click-abc");
  });
});

test("stdin-runner: failedStepId is null on a passing run even when steps have ids", async () => {
  await withTestServer(async (baseUrl) => {
    const { exitCode, stdout } = await runStdinRunner({
      steps: [{ id: "gen-nav-1", type: "navigate", url: baseUrl }],
    });

    assert.equal(exitCode, 0);
    const result = JSON.parse(stdout);
    assert.equal(result.status, "passed");
    assert.equal(result.failedStepId, null);
  });
});

test("stdin-runner: steps without ids still work end-to-end (backward compatibility)", async () => {
  await withTestServer(async (baseUrl) => {
    const { exitCode, stdout } = await runStdinRunner({
      steps: [{ type: "navigate", url: baseUrl }],
    });

    assert.equal(exitCode, 0);
    const result = JSON.parse(stdout);
    assert.equal(result.status, "passed");
    assert.equal(result.failedStepId, null);
    assert.equal(result.steps[0].id, undefined);
  });
});
