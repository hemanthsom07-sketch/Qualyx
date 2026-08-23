"""
Execution History Stage 4: read-only response schema for
GET /tests/{test_id}/executions.

Mirrors app.models.execution_run.ExecutionRun field-for-field -- the
complete persisted historical snapshot, nothing more, nothing less.
Follows the exact same from_attributes=True / plain-field convention
already established by TestDefinitionRead
(app/schemas/test_definition.py) rather than introducing a new pattern.

diagnosis/explanation/healing are returned as plain dict (JSON) fields,
exactly as they were persisted (see
app/api/routes/test_definitions.py's _persist_execution_run()) -- they
are NOT re-validated against DiagnosisOut/ExplanationOut/HealingResultOut
here. Those Pydantic models describe the live /execute response at the
moment it was produced; this schema describes the historical read path,
which simply returns the already-faithful JSON snapshot stored at that
time. No new fields are introduced beyond what ExecutionRun already
persists, and no database internals (e.g. SQLAlchemy relationship
objects) are exposed.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExecutionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    test_definition_id: str
    status: str
    failed_step_id: str | None
    failed_step_index: int | None
    error: str | None
    executed_step_count: int
    evidence: dict | None
    diagnosis: dict | None
    explanation: dict | None
    healing: dict | None
    started_at: str
    finished_at: str
    duration_ms: int
    created_at: datetime
