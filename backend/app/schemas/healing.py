"""
Healing response schema (Phase 4 Stage E).

Mirrors app.services.healing_client.HealingAttemptResult field-for-field
-- the same pattern app/schemas/diagnosis.py already uses to mirror
Intelligence's FailureDiagnosisResult/ExplainedDiagnosis. No decision
logic lives here; this module only shapes the already-decided result
for the API response.

`healed_execution` reuses the existing, unmodified ExecutionResultOut
(the same shape as the top-level execution result) rather than
introducing a new, parallel shape for "what a second execution result
looks like" -- it IS the same kind of thing, just from the second
execute_steps() call. It deliberately does NOT nest a diagnosis or
explanation of its own: the healed run is not re-diagnosed (Stage E
does not attempt a third execution or a second healing cycle), so
`healed_execution.status` is the only field a caller needs to see
whether the healed run passed or failed.
"""

from pydantic import BaseModel, ConfigDict

from app.schemas.execution import ExecutionResultOut


class HealingResultOut(BaseModel):
    """Mirrors HealingAttemptResult exactly -- see that class's docstring."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    reason: str
    generated_step_id: str | None = None
    original_selector: str | None = None
    original_selector_kind: str | None = None
    proposed_selector: str | None = None
    proposed_selector_kind: str | None = None
    applied: bool = False
    confidence: float | None = None
    healed_execution: ExecutionResultOut | None = None
