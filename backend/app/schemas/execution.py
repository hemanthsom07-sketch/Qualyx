"""
ExecutionResult schemas — the Backend-side mirror of the Execution
Engine's ExecutionResult contract (execution-engine/src/types.ts).

Field names use the engine's camelCase JSON shape as aliases so the API
response matches the boundary contract exactly: status, failedStepIndex,
error, executedStepCount (Task 6 §C minimum), plus failedStepId (Task 8)
and the additional per-step/timing detail retained from Task 4, which is
additive and not part of the required minimum.

This is NOT a diagnosis contract. No bug/broken-test classification is
represented here — that belongs to Claude 3's Intelligence module.
"""

from pydantic import BaseModel, ConfigDict, Field


class StepResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_index: int = Field(alias="stepIndex")
    # Task 8: the Intelligence-generated stable step id, carried through
    # unchanged if the step had one. Never fabricated.
    id: str | None = None
    type: str
    status: str
    duration_ms: int = Field(alias="durationMs")
    error: str | None = None


class ExecutionResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    steps: list[StepResultOut]
    failed_step_index: int | None = Field(alias="failedStepIndex")
    # Task 8: additive — identifies the failed generated step by its
    # stable id when the step had one. Null (not fabricated) otherwise,
    # and always null on a passing run.
    failed_step_id: str | None = Field(alias="failedStepId")
    error: str | None = None
    executed_step_count: int = Field(alias="executedStepCount")
    started_at: str = Field(alias="startedAt")
    finished_at: str = Field(alias="finishedAt")
    duration_ms: int = Field(alias="durationMs")
