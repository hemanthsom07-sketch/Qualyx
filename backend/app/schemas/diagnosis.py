"""
Diagnosis + Explainability response schemas (Milestone 2A).

These mirror Intelligence's existing dataclasses field-for-field --
intelligence.diagnosis.failure_diagnosis.FailureDiagnosisResult and
intelligence.explainability.engine.ExplainedDiagnosis -- and add NO new
fields beyond what those already produce. No classification or
presentation logic lives here; this module only shapes the same values
for the API response.

Field names are plain snake_case (unlike ExecutionResultOut's camelCase
aliases), because these mirror Intelligence's own Python-native
dataclasses, not a JSON wire contract owned by another language/process
(unlike the Execution Engine, diagnosis/explainability have no JS/TS
counterpart to alias against).

ExecutionResultWithDiagnosisOut is additive: it subclasses the existing,
unmodified ExecutionResultOut (reused, not duplicated) and adds three
new top-level fields, `diagnosis`, `explanation`, and (Phase 4 Stage E)
`healing`. Every field the existing ExecutionResultOut response already
had is unchanged.
"""

from pydantic import BaseModel, ConfigDict

from app.schemas.execution import ExecutionResultOut
from app.schemas.healing import HealingResultOut


class DiagnosisOut(BaseModel):
    """Mirrors FailureDiagnosisResult exactly -- see that class's docstring."""

    model_config = ConfigDict(from_attributes=True)

    has_failure: bool
    classification: str | None
    confidence: float
    correlation_established: bool
    failed_step_id: str | None
    failed_step_index: int | None
    error: str | None
    generated_step_id: str | None
    source_step_id: str | None
    source_event_id: str | None
    evidence: list[str]
    explanation: str


class ExplanationOut(BaseModel):
    """Mirrors ExplainedDiagnosis exactly -- see that class's docstring."""

    model_config = ConfigDict(from_attributes=True)

    has_failure: bool
    classification: str | None
    confidence: float
    confidence_level: str
    headline: str
    explanation: str
    evidence: list[str]


class ExecutionResultWithDiagnosisOut(ExecutionResultOut):
    """
    Additive response shape for POST /tests/{test_id}/execute: every
    field ExecutionResultOut already returned, unchanged, plus three
    new top-level objects: `diagnosis` (raw FailureDiagnosisResult
    mirror), `explanation` (raw ExplainedDiagnosis mirror), and
    (Phase 4 Stage E) `healing` (raw HealingAttemptResult mirror --
    always present on any response, matching diagnosis/explanation's
    own always-present convention; reports status="not_attempted" on a
    passing execution rather than being omitted/null).
    """

    diagnosis: DiagnosisOut
    explanation: ExplanationOut
    healing: HealingResultOut
