"""
Pydantic schemas for the Project entity.

These are backend-internal API schemas for this milestone only. They are
NOT one of the seven frozen cross-module shared contracts (RecordedJourney,
TestDefinition, ExecutionRequest, ExecutionResult, FailureDiagnosis,
HealingProposal, SharedEnums) — Project sits outside that list and has no
cross-module contract dependency yet.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
