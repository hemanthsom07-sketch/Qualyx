"""
Backend <-> Intelligence Diagnosis boundary.

Extends the existing Backend <-> Intelligence import-path pattern
established in app/services/intelligence_client.py (module-scoped
sys.path insertion, guarded against duplicate insertion) rather than
inventing a new integration mechanism — no HTTP service, no registry,
no cache, no persistence.

This module does exactly two things:

1. Reconstructs the MINIMUM LocalGeneratedTest Intelligence's diagnosis
   needs, from Backend's own TestDefinition.content (a bare JSON list
   of step dicts — confirmed contract, see
   app/models/test_definition.py). `source_step_id`/`source_event_id`
   are always None: Backend genuinely does not have them (confirmed
   architectural decision — they are intentionally not stored), and
   they are never fabricated here.

2. Converts Backend's real, confirmed ExecutionResultOut (Pydantic,
   snake_case attributes with camelCase aliases) into Intelligence's
   own ExecutionResult / StepExecutionResult dataclasses (camelCase
   attributes, per the actual, confirmed current
   intelligence/diagnosis/execution_result.py — which has no
   FailureEvidence class and no nested `evidence` field; diagnosis
   there is driven entirely by the single free-text `error` string plus
   failedStepId/failedStepIndex), then calls Intelligence's existing,
   unmodified diagnose_execution_result() — no diagnosis/classification
   logic is duplicated or reimplemented here.

Backend's own richer ExecutionResultOut.evidence (nested action/
errorCategory/etc.) is untouched and still returned in full to API
callers alongside the diagnosis — it is simply not part of what gets
passed into Intelligence's diagnosis today, since Intelligence's real
contract doesn't model it. Nothing here fabricates a field to fill that
gap.
"""

from app.models.test_definition import TestDefinition
from app.schemas.execution import ExecutionResultOut
from app.services.intelligence_client import _ensure_intelligence_importable

_ensure_intelligence_importable()

# Imported only after the path adjustment above. Existing, unmodified
# Intelligence entry points — confirmed field-for-field against the
# actual current source of generated_test.py, execution_result.py, and
# failure_diagnosis.py; nothing here re-implements their logic.
from intelligence.test_generation.generated_test import LocalGeneratedStep, LocalGeneratedTest  # noqa: E402
from intelligence.diagnosis.execution_result import (  # noqa: E402
    ExecutionResult as IntelligenceExecutionResult,
    StepExecutionResult as IntelligenceStepExecutionResult,
)
from intelligence.diagnosis.failure_diagnosis import (  # noqa: E402
    FailureDiagnosisResult,
    diagnose_execution_result,
)


def build_local_generated_test(test_definition: TestDefinition) -> LocalGeneratedTest:
    """
    Reconstructs the minimum LocalGeneratedTest Intelligence's diagnosis
    needs from Backend's stored content.

    Steps with no stored "id" are skipped entirely: LocalGeneratedStep
    requires a step_id argument, and a step with no real stable id has
    nothing genuine to correlate a failedStepId against anyway —
    omitting it costs nothing (Intelligence's own
    find_generated_step_by_id wouldn't match it either way), whereas
    inventing a placeholder id would be fabrication.
    """
    steps: list[LocalGeneratedStep] = []
    for raw_step in test_definition.content:
        step_id = raw_step.get("id")
        if not step_id:
            continue
        steps.append(
            LocalGeneratedStep(
                step_id=step_id,
                kind=raw_step["type"],
                # Confirmed architectural decision: Backend does not
                # store provenance. Never fabricated — always None.
                source_step_id=None,
                source_event_id=None,
                url=raw_step.get("url"),
                selector=raw_step.get("selector"),
                selector_kind=raw_step.get("selectorKind"),
                value=raw_step.get("value"),
            )
        )
    return LocalGeneratedTest(journey_id=test_definition.name, steps=steps)


def to_intelligence_execution_result(result: ExecutionResultOut) -> IntelligenceExecutionResult:
    """
    Converts Backend's real ExecutionResultOut into Intelligence's
    ExecutionResult/StepExecutionResult dataclasses, field for field.

    Backend's own evidence object (nested action/errorCategory/pageUrl/
    etc.) is intentionally not passed through here — Intelligence's real
    ExecutionResult has no `evidence` field to receive it. This is not a
    loss of information for API callers: the full ExecutionResultOut,
    including evidence, is still returned as-is alongside the diagnosis
    (see app/api/routes/test_definitions.py). Fields with no home on the
    Intelligence side (e.g. per-step stepIndex/type/durationMs, which
    IntelligenceStepExecutionResult intentionally doesn't model) are
    likewise simply omitted here, not fabricated or lost from the real
    response.
    """
    steps = [
        IntelligenceStepExecutionResult(id=s.id, status=s.status, error=s.error) for s in result.steps
    ]

    return IntelligenceExecutionResult(
        status=result.status,
        failedStepIndex=result.failed_step_index,
        failedStepId=result.failed_step_id,
        error=result.error,
        executedStepCount=result.executed_step_count,
        steps=steps,
        startedAt=result.started_at,
        finishedAt=result.finished_at,
        durationMs=result.duration_ms,
    )


def diagnose(test_definition: TestDefinition, execution_result: ExecutionResultOut) -> FailureDiagnosisResult:
    """
    Runs Intelligence's existing, unmodified diagnosis on a failed
    execution result.

    Callers must only invoke this when execution_result.status ==
    "failed" — a passing execution should never reach this function
    (enforced at the call site in app/api/routes/test_definitions.py,
    not re-checked here, to keep this function a pure, single-purpose
    conversion+call).
    """
    generated_test = build_local_generated_test(test_definition)
    intelligence_result = to_intelligence_execution_result(execution_result)
    return diagnose_execution_result(generated_test, intelligence_result)