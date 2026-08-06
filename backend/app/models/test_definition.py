"""
TestDefinition persistence model.

Minimal representation for this milestone: a TestDefinition belongs to a
Project and holds a script/step representation for the execution engine
to run later.

NOTE ON SCOPE: this is a backend-internal entity for this milestone, not
the frozen cross-module `TestDefinition` shared contract described in the
Task 2 alignment (which also includes structured steps tied to journey
understanding, generation/version metadata, etc., owned jointly with
Claude 3). This model intentionally does not attempt to satisfy that full
future contract — see the milestone report's "Cross-module requirements"
section.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TestDefinition(Base):
    __tablename__ = "test_definitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Minimal script/step representation for this milestone: a JSON list of
    # step objects (see execution-engine's step model: navigate/click/fill).
    # Stored as JSON rather than a dedicated relational shape, since the
    # real structured-step contract is still to be jointly agreed with
    # Claude 3 (see Task 2's TestDefinition contract discussion).
    content: Mapped[list] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
