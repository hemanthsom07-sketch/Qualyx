/**
 * Centralized Backend API client.
 *
 * Covers exactly the endpoints the Dashboard needs, as implemented in
 * backend/app/api/routes/projects.py and
 * backend/app/api/routes/test_definitions.py:
 *
 *   GET  /projects
 *   GET  /projects/{project_id}
 *   GET  /projects/{project_id}/tests
 *   GET  /tests/{test_id}
 *   POST /tests/{test_id}/execute
 *   GET  /tests/{test_id}/executions
 *   GET  /tests/{test_id}/analysis
 *
 * Uses native fetch (the dashboard has no other HTTP abstraction).
 * All non-2xx responses are normalized into a single ApiError so UI
 * code has one error shape to handle regardless of which endpoint
 * failed.
 */

import type {
  ExecutionResultWithDiagnosis,
  ExecutionRun,
  FlakyAnalysisResult,
  Project,
  TestDefinition,
} from "./types";

// Vite env convention -- see .env.example. Falls back to the backend's
// own local-dev default port (matches the CORS allow-list already
// configured backend-side in app/config.py for a Vite dev server).
const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    // FastAPI's default error body is {"detail": "..."} -- surface that
    // when it's a string, otherwise fall back to a generic message
    // rather than assuming a shape that may not hold for every route.
    const message =
      typeof detail === "object" && detail !== null && "detail" in detail && typeof (detail as { detail?: unknown }).detail === "string"
        ? (detail as { detail: string }).detail
        : `Request failed with status ${status}`;
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      // Response body wasn't JSON (or was empty) -- ApiError falls
      // back to a generic message in that case.
    }
    throw new ApiError(response.status, detail);
  }

  // All endpoints this client covers return a JSON body, including on
  // success (no 204 No Content routes among them).
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}

export interface CreateProjectInput {
  name: string;
  description?: string | null;
}

export function createProject(input: CreateProjectInput): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getProject(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}`);
}

// ---------------------------------------------------------------------
// Test definitions
// ---------------------------------------------------------------------

export function listTestDefinitions(projectId: string): Promise<TestDefinition[]> {
  return request<TestDefinition[]>(`/projects/${projectId}/tests`);
}

export function getTestDefinition(testId: string): Promise<TestDefinition> {
  return request<TestDefinition>(`/tests/${testId}`);
}

// ---------------------------------------------------------------------
// Execution
// ---------------------------------------------------------------------

export function executeTestDefinition(
  testId: string
): Promise<ExecutionResultWithDiagnosis> {
  return request<ExecutionResultWithDiagnosis>(`/tests/${testId}/execute`, {
    method: "POST",
  });
}

export function listExecutionRuns(testId: string): Promise<ExecutionRun[]> {
  return request<ExecutionRun[]>(`/tests/${testId}/executions`);
}

// ---------------------------------------------------------------------
// Flaky analysis
// ---------------------------------------------------------------------

export interface GetAnalysisOptions {
  /** Mirrors the backend's `window` query param (default 20, min 3). */
  window?: number;
}

export function getTestAnalysis(
  testId: string,
  options?: GetAnalysisOptions
): Promise<FlakyAnalysisResult> {
  const query = options?.window ? `?window=${options.window}` : "";
  return request<FlakyAnalysisResult>(`/tests/${testId}/analysis${query}`);
}
