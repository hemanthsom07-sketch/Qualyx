"""
ExecutionRun persistence model (Execution History Stage 1 + Stage 2).

Persists the raw, deterministic execution-level result for every
POST /tests/{test_id}/execute call -- exactly what the Execution
Engine reported (execution-engine/src/types.ts's ExecutionResult),
mirrored the same way app/schemas/execution.py's ExecutionResultOut
already mirrors it for the API response. Stage 1 intentionally did NOT
persist diagnosis, explanation, or healing information. Stage 2 adds
diagnosis and explanation as complete, verbatim snapshots (see below);
healing persistence remains a separate, later stage (Stage 3), so this
table still has no healing columns.

Belongs to a TestDefinition through a foreign key, following the exact
same id/timestamp/FK conventions already established by
app/models/test_definition.py and app/models/project.py. This is the
"runs" entity Project's own docstring already anticipated
("Project is the top-level entity that recordings, journeys, tests, and
runs will eventually attach to") -- ExecutionRun attaches to
TestDefinition directly (one level down from Project), matching how
execution itself is already scoped to a single TestDefinition, not a
whole Project, everywhere else in this codebase.

evidence is stored as JSON exactly as it arrives from
ExecutionResultOut.evidence.model_dump() (or None on a passing run) --
no reinterpretation, no new shape.

Stage 2: diagnosis/explanation are stored as JSON columns, not separate
tables -- consistent with evidence's own existing precedent above, and
appropriate for what these represent: an immutable, point-in-time
snapshot of app/schemas/diagnosis.py's DiagnosisOut/ExplanationOut
(themselves unmodified by this stage), not an evolving relational
structure. Each column holds the complete schema's fields verbatim
(via .model_dump()) -- no field subset, no new fields invented, no
healing data included.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    test_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_definitions.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    # Task 8 / Execution Evidence Foundation fields, mirrored verbatim
    # from ExecutionResultOut -- null exactly when the execution result
    # itself had them null (a passing run, or a legacy un-id'd step),
    # never fabricated.
    failed_step_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    executed_step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Structured FailureEvidence, stored as JSON exactly as reported;
    # None on a passing run.
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Execution History Stage 2: complete DiagnosisOut/ExplanationOut
    # snapshots, stored as JSON exactly as the live API response
    # produced them (same field set, same values -- see
    # app/api/routes/test_definitions.py's _persist_execution_run()).
    # Nullable for schema robustness, matching `evidence` above, though
    # in the route's current behavior diagnose_and_explain() runs
    # unconditionally, so both are populated on every row today.
    diagnosis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Execution Engine's own reported timing (ISO-format strings, same
    # as ExecutionResultOut.started_at/finished_at -- stored verbatim,
    # not reparsed/reformatted here), plus its own duration_ms.
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    finished_at: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # When this row itself was persisted -- distinct from started_at/
    # finished_at above, which are the Execution Engine's own reported
    # times for the run itself.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
