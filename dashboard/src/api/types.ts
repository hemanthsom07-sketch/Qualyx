/**
 * TypeScript types mirroring the Backend's Pydantic response schemas.
 *
 * Field names/nullability are copied field-for-field from the actual
 * backend source (not invented/simplified):
 *   - backend/app/schemas/project.py
 *   - backend/app/schemas/test_definition.py
 *   - backend/app/schemas/execution.py
 *   - backend/app/schemas/diagnosis.py
 *   - backend/app/schemas/healing.py
 *   - backend/app/schemas/execution_run.py
 *   - backend/app/schemas/flaky_analysis.py
 *
 * Two field-naming conventions exist on the backend side and are
 * preserved here rather than normalized away:
 *   - ExecutionResultOut / StepResultOut / FailureEvidenceOut use
 *     camelCase JSON aliases (mirroring the Execution Engine's TS
 *     contract), so the fields below are camelCase to match the actual
 *     wire shape.
 *   - DiagnosisOut / ExplanationOut / HealingResultOut / FlakyAnalysis*
 *     have no JS/TS counterpart to alias against, so the backend emits
 *     them as plain snake_case, and the fields below match that.
 */

// ---------------------------------------------------------------------
// Project (backend/app/schemas/project.py)
// ---------------------------------------------------------------------

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------
// TestDefinition (backend/app/schemas/test_definition.py)
// ---------------------------------------------------------------------

export interface TestDefinition {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  // Stored steps are returned as plain dicts (TestDefinitionRead.content:
  // list[dict]) -- not re-validated into the Navigate/Click/Fill step
  // union on the read path, so this stays loosely typed here too.
  content: Record<string, unknown>[];
  created_at: string;
}

// ---------------------------------------------------------------------
// Execution (backend/app/schemas/execution.py) -- camelCase aliases
// ---------------------------------------------------------------------

export interface StepResult {
  stepIndex: number;
  id: string | null;
  type: string;
  status: string;
  durationMs: number;
  error: string | null;
}

export interface FailureEvidenceAction {
  // Only one of these is ever present per step type (never both) --
  // mirrors FailureEvidenceActionOut's custom "absent unless present"
  // serializer.
  url?: string;
  selector?: string;
}

export interface FailureEvidence {
  failedStepId: string | null;
  failedStepIndex: number;
  stepType: string;
  action: FailureEvidenceAction;
  errorMessage: string;
  errorCategory: string;
  pageUrl: string | null;
  httpStatus: number | null;
  executedStepCount: number;
  stepDurationMs: number;
}

export interface ExecutionResult {
  status: string;
  steps: StepResult[];
  failedStepIndex: number | null;
  failedStepId: string | null;
  error: string | null;
  executedStepCount: number;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
  evidence: FailureEvidence | null;
}

// ---------------------------------------------------------------------
// Diagnosis + Explanation (backend/app/schemas/diagnosis.py) -- snake_case
// ---------------------------------------------------------------------

export interface Diagnosis {
  has_failure: boolean;
  classification: string | null;
  confidence: number;
  correlation_established: boolean;
  failed_step_id: string | null;
  failed_step_index: number | null;
  error: string | null;
  generated_step_id: string | null;
  source_step_id: string | null;
  source_event_id: string | null;
  evidence: string[];
  explanation: string;
}

export interface Explanation {
  has_failure: boolean;
  classification: string | null;
  confidence: number;
  confidence_level: string;
  headline: string;
  explanation: string;
  evidence: string[];
}

// ---------------------------------------------------------------------
// Healing (backend/app/schemas/healing.py) -- snake_case, nests a full
// ExecutionResult (camelCase) for healed_execution, exactly as the
// backend does.
// ---------------------------------------------------------------------

export interface HealingResult {
  status: string;
  reason: string;
  generated_step_id: string | null;
  original_selector: string | null;
  original_selector_kind: string | null;
  proposed_selector: string | null;
  proposed_selector_kind: string | null;
  applied: boolean;
  confidence: number | null;
  healed_execution: ExecutionResult | null;
}

// ---------------------------------------------------------------------
// POST /tests/{test_id}/execute response
// (backend/app/schemas/diagnosis.py: ExecutionResultWithDiagnosisOut)
// ---------------------------------------------------------------------

export interface ExecutionResultWithDiagnosis extends ExecutionResult {
  diagnosis: Diagnosis;
  explanation: Explanation;
  healing: HealingResult;
}

// ---------------------------------------------------------------------
// GET /tests/{test_id}/executions response
// (backend/app/schemas/execution_run.py: ExecutionRunRead)
//
// diagnosis/explanation/healing are stored+returned as raw JSON dicts
// (persisted snapshots), NOT re-validated Pydantic models -- so they are
// typed as the same shapes above, but nullable, matching the schema.
// ---------------------------------------------------------------------

export interface ExecutionRun {
  id: string;
  test_definition_id: string;
  status: string;
  failed_step_id: string | null;
  failed_step_index: number | null;
  error: string | null;
  executed_step_count: number;
  evidence: FailureEvidence | null;
  diagnosis: Diagnosis | null;
  explanation: Explanation | null;
  healing: HealingResult | null;
  started_at: string;
  finished_at: string;
  duration_ms: number;
  created_at: string;
}

// ---------------------------------------------------------------------
// Flaky analysis (backend/app/schemas/flaky_analysis.py) -- snake_case
// ---------------------------------------------------------------------

export interface RecurringSignature {
  failed_step_id: string;
  classification: string | null;
  occurrence_count: number;
  first_execution_id: string;
  last_execution_id: string;
}

export interface FlakyAnalysisResult {
  test_definition_id: string;
  executions_analyzed: number;
  window_description: string;
  insufficient_data: boolean;

  passed_count: number;
  failed_count: number;

  is_flaky: boolean;
  flaky_reason: string | null;
  consistently_failing: boolean;

  recurring_signatures: RecurringSignature[];
  most_frequent_failing_step_id: string | null;
  diagnosis_classification_counts: Record<string, number>;

  healing_attempted_count: number;
  healing_succeeded_count: number;
  healing_failed_count: number;

  evidence: string[];
}
