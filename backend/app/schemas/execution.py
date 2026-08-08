"""
ExecutionResult schemas — the Backend-side mirror of the Execution
Engine's ExecutionResult contract (execution-engine/src/types.ts).

Field names use the engine's camelCase JSON shape as aliases so the API
response matches the boundary contract exactly: status, failedStepIndex,
error, executedStepCount (Task 6 §C minimum), plus failedStepId (Task 8)
and evidence (Execution Evidence Foundation), and the additional
per-step/timing detail retained from Task 4. All additive.

This is NOT a diagnosis contract. No bug/broken-test classification is
represented here — that belongs to Claude 3's Intelligence module. This
module only mirrors deterministic facts the execution engine reports.
"""

from pydantic import BaseModel, ConfigDict, Field, model_serializer


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


class FailureEvidenceActionOut(BaseModel):
    """
    Safe, redacted summary of the failed step's input. Deliberately
    excludes a fill step's `value` (may be a password or other
    sensitive form input) — only structural fields are ever present.

    Only one of `url`/`selector` genuinely applies per step type (the
    execution engine's FailureEvidenceAction never sets both). The
    custom serializer below preserves that "absent unless present"
    shape in the API response — e.g. {"selector": "#submit"} — rather
    than FastAPI's default of serializing every declared Optional field,
    which would otherwise add a spurious "url": null alongside it.
    """

    url: str | None = None
    selector: str | None = None

    @model_serializer
    def _serialize(self) -> dict:
        data: dict = {}
        if self.url is not None:
            data["url"] = self.url
        if self.selector is not None:
            data["selector"] = self.selector
        return data


class FailureEvidenceOut(BaseModel):
    """
    Mirrors execution-engine/src/types.ts's FailureEvidence exactly.
    Every field is a deterministic fact reported by the execution
    engine, or null when that fact genuinely wasn't available — nothing
    here is inferred or classified by the backend.
    """

    model_config = ConfigDict(populate_by_name=True)

    failed_step_id: str | None = Field(alias="failedStepId")
    failed_step_index: int = Field(alias="failedStepIndex")
    step_type: str = Field(alias="stepType")
    action: FailureEvidenceActionOut
    error_message: str = Field(alias="errorMessage")
    error_category: str = Field(alias="errorCategory")
    page_url: str | None = Field(alias="pageUrl")
    http_status: int | None = Field(alias="httpStatus")
    executed_step_count: int = Field(alias="executedStepCount")
    step_duration_ms: int = Field(alias="stepDurationMs")


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
    # Execution Evidence Foundation: null on a passing run; a structured,
    # non-fabricated description of the failure on a failing run, for
    # Claude 3's diagnosis layer to consume. Additive.
    evidence: FailureEvidenceOut | None = None