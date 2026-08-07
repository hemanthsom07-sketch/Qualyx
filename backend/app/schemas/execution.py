"""
ExecutionResult schemas — the Backend-side mirror of the Execution
Engine's ExecutionResult contract (execution-engine/src/types.ts).

Field names use the engine's camelCase JSON shape as aliases so the API
response matches the boundary contract from Task 6 §C exactly:
status, failedStepIndex, error, executedStepCount (plus the additional
per-step/timing detail retained from Task 4, which is additive and not
part of the required minimum).

This is NOT a diagnosis contract. No bug/broken-test classification is
represented here — that belongs to Claude 3's Intelligence module.
"""

from pydantic import BaseModel, ConfigDict, Field


class StepResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_index: int = Field(alias="stepIndex")
    type: str
    status: str
    duration_ms: int = Field(alias="durationMs")
    error: str | None = None


class ExecutionResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    steps: list[StepResultOut]
    failed_step_index: int | None = Field(alias="failedStepIndex")
    error: str | None = None
    executed_step_count: int = Field(alias="executedStepCount")
    started_at: str = Field(alias="startedAt")
    finished_at: str = Field(alias="finishedAt")
    duration_ms: int = Field(alias="durationMs")
