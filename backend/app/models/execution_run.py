"""
ExecutionRun persistence model (Execution History Stage 1).

Persists the raw, deterministic execution-level result for every
POST /tests/{test_id}/execute call -- exactly what the Execution
Engine reported (execution-engine/src/types.ts's ExecutionResult),
mirrored the same way app/schemas/execution.py's ExecutionResultOut
already mirrors it for the API response. This stage intentionally does
NOT persist diagnosis, explanation, or healing information -- those are
separate, later stages (see the milestone plan), so this table has no
columns for them.

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
