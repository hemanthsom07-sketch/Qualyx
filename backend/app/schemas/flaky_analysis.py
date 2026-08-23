"""
Phase 5 Stage 2: read-only response schema for
GET /tests/{test_id}/analysis.

Mirrors intelligence.flaky_analysis.engine.FlakyAnalysisResult /
RecurringSignature field-for-field -- no new fields invented, no
confidence score added. Plain snake_case, matching the fact that these
mirror Intelligence's own Python-native dataclasses directly (the same
convention already established by app/schemas/diagnosis.py and
app/schemas/healing.py for FailureDiagnosisResult/HealingAttemptResult,
neither of which has a JS/TS counterpart to alias against either).

No decision logic lives here -- this module only shapes the already-
computed Stage 1 result for the API response.
"""

from pydantic import BaseModel, ConfigDict


class RecurringSignatureOut(BaseModel):
    """Mirrors intelligence.flaky_analysis.engine.RecurringSignature exactly."""

    model_config = ConfigDict(from_attributes=True)

    failed_step_id: str
    classification: str | None
    occurrence_count: int
    first_execution_id: str
    last_execution_id: str


class FlakyAnalysisResultOut(BaseModel):
    """Mirrors intelligence.flaky_analysis.engine.FlakyAnalysisResult exactly."""

    model_config = ConfigDict(from_attributes=True)

    test_definition_id: str
    executions_analyzed: int
    window_description: str
    insufficient_data: bool

    passed_count: int
    failed_count: int

    is_flaky: bool
    flaky_reason: str | None
    consistently_failing: bool

    recurring_signatures: list[RecurringSignatureOut]
    most_frequent_failing_step_id: str | None
    diagnosis_classification_counts: dict[str, int]

    healing_attempted_count: int
    healing_succeeded_count: int
    healing_failed_count: int

    evidence: list[str]
