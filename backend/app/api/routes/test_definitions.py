import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.execution_run import ExecutionRun
from app.models.project import Project
from app.models.test_definition import TestDefinition
from app.schemas.diagnosis import DiagnosisOut, ExecutionResultWithDiagnosisOut, ExplanationOut
from app.schemas.execution import ExecutionResultOut
from app.schemas.healing import HealingResultOut
from app.schemas.test_definition import ExecutionPayloadCreate, TestDefinitionCreate, TestDefinitionRead
from app.services.diagnosis_client import diagnose_and_explain
from app.services.healing_client import (
    build_healing_result,
    not_attempted_result,
    prepare_healing_attempt,
    HEALING_FAILED,
)
from app.services.execution_client import (
    ExecutionEngineError,
    ExecutionValidationError,
    execute_steps,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["test-definitions"])


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_test_definition_or_404(test_id: str, db: Session) -> TestDefinition:
    test_definition = db.get(TestDefinition, test_id)
    if test_definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test definition not found")
    return test_definition


def _persist_execution_run(db: Session, test_definition_id: str, result: ExecutionResultOut) -> None:
    """
    Execution History Stage 1: persists the raw execution result exactly
    as reported, with no diagnosis/explanation/healing information (see
    app/models/execution_run.py -- those are separate, later stages).

    NON-FATAL by design: a persistence failure here must never turn a
    valid execution response into an HTTP 500, must never retry the
    execution, and must never alter `result` itself. On failure, this
    rolls back the session (so it remains usable for the rest of the
    request/future requests) and logs the failure via the standard
    `logging` module -- no other logging convention exists elsewhere in
    this codebase to follow instead.
    """
    try:
        run = ExecutionRun(
            test_definition_id=test_definition_id,
            status=result.status,
            failed_step_id=result.failed_step_id,
            failed_step_index=result.failed_step_index,
            error=result.error,
            executed_step_count=result.executed_step_count,
            evidence=result.evidence.model_dump(by_alias=True) if result.evidence is not None else None,
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_ms=result.duration_ms,
        )
        db.add(run)
        db.commit()
    except Exception:  # noqa: BLE001 - deliberately broad: persistence
        # must never be allowed to break the execution response,
        # regardless of what specifically went wrong (DB unavailable,
        # constraint violation, etc.).
        db.rollback()
        logger.exception(
            "Failed to persist ExecutionRun for test_definition_id=%s; "
            "the execution response itself is unaffected.",
            test_definition_id,
        )


@router.post(
    "/projects/{project_id}/tests",
    response_model=TestDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_definition(
    project_id: str, payload: TestDefinitionCreate, db: Session = Depends(get_db)
) -> TestDefinition:
    _get_project_or_404(project_id, db)

    test_definition = TestDefinition(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        # exclude_none: don't store a spurious "id": null on steps that
        # were never given a stable id (keeps old-shape content clean).
        # by_alias: store "selectorKind" under that same key, not the
        # Python-side "selector_kind" name.
        content=[step.model_dump(exclude_none=True, by_alias=True) for step in payload.content],
    )
    db.add(test_definition)
    db.commit()
    db.refresh(test_definition)
    return test_definition


@router.post(
    "/projects/{project_id}/tests/from-execution-payload",
    response_model=TestDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_definition_from_execution_payload(
    project_id: str, payload: ExecutionPayloadCreate, db: Session = Depends(get_db)
) -> TestDefinition:
    """
    Ingests Claude 3's Intelligence execution payload
    ({"journeyId": ..., "steps": [...]}, as produced by
    test_generation/execution_payload.py's to_execution_test_payload())
    directly, storing it as a TestDefinition under an existing Project.

    Mapping (per approved integration decision):
        journeyId -> TestDefinition.name (used verbatim, no invented naming)
        steps     -> TestDefinition.content (stable id, type, url,
                     selector, value, and optional selectorKind all
                     preserved; source_step_id/source_event_id are not
                     part of this payload's contract and are not
                     accepted here)

    Reuses the exact same step validation as create_test_definition()
    (the shared `Step` union), and once stored, the resulting
    TestDefinition is executed via the existing, unmodified
    POST /tests/{test_id}/execute path — no separate execution logic.
    """
    _get_project_or_404(project_id, db)

    test_definition = TestDefinition(
        project_id=project_id,
        name=payload.journey_id,
        description=None,
        content=[step.model_dump(exclude_none=True, by_alias=True) for step in payload.steps],
    )
    db.add(test_definition)
    db.commit()
    db.refresh(test_definition)
    return test_definition


@router.get("/projects/{project_id}/tests", response_model=list[TestDefinitionRead])
def list_test_definitions(project_id: str, db: Session = Depends(get_db)) -> list[TestDefinition]:
    _get_project_or_404(project_id, db)

    return list(
        db.query(TestDefinition)
        .filter(TestDefinition.project_id == project_id)
        .order_by(TestDefinition.created_at.desc())
        .all()
    )


@router.get("/tests/{test_id}", response_model=TestDefinitionRead)
def get_test_definition(test_id: str, db: Session = Depends(get_db)) -> TestDefinition:
    return _get_test_definition_or_404(test_id, db)


@router.post("/tests/{test_id}/execute", response_model=ExecutionResultWithDiagnosisOut)
def execute_test_definition(test_id: str, db: Session = Depends(get_db)) -> ExecutionResultWithDiagnosisOut:
    """
    Executes an existing TestDefinition's stored steps via the Execution
    Engine (subprocess boundary — see app/services/execution_client.py),
    then diagnoses and explains the result via Claude 3's Intelligence
    module (in-process boundary — see app/services/diagnosis_client.py).

    Milestone 2A: this endpoint now returns the execution result together
    with `diagnosis` (a direct mirror of
    intelligence.diagnosis.FailureDiagnosisResult) and `explanation` (a
    direct mirror of intelligence.explainability.ExplainedDiagnosis).
    This is an additive response-shape change: every field previously
    returned here is unchanged; `diagnosis` and `explanation` are new
    top-level fields. No diagnosis or explainability logic is duplicated
    here — both are computed entirely by Intelligence's existing,
    unmodified functions; this endpoint only translates and forwards.

    Phase 4 Stage E: on a failed execution, this endpoint now also
    attempts healing (in-process boundary — see
    app/services/healing_client.py) and returns a third additive field,
    `healing`. At most ONE additional execute_steps() call is ever made
    (no loop; the healed steps are only executed once, and their result
    is never re-diagnosed or re-healed). The original, persisted
    TestDefinition is never modified — healing operates entirely on an
    in-memory reconstruction and, if a real evidence-backed candidate
    exists, an in-memory healed copy of it. `healing.status` is only
    ever "healed" when that second execution's own status was "passed";
    "healing_failed" when it was applied but still failed.
    """
    test_definition = _get_test_definition_or_404(test_id, db)

    try:
        result = execute_steps(test_definition.content)
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExecutionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Execution History Stage 1: persist the raw result. Non-fatal --
    # see _persist_execution_run()'s docstring. Deliberately only the
    # ORIGINAL execution result (not a healed re-execution, if any
    # happens below) -- diagnosis/explanation/healing persistence are
    # separate, later stages.
    _persist_execution_run(db, test_definition.id, result)

    diagnosis, explanation = diagnose_and_explain(test_definition.id, test_definition.content, result)

    if diagnosis.has_failure:
        proposal, healed_steps = prepare_healing_attempt(test_definition.id, test_definition.content, diagnosis)
        if healed_steps is None:
            healing_result = build_healing_result(diagnosis, proposal, None)
        else:
            try:
                healed_execution = execute_steps(healed_steps)
            except (ExecutionValidationError, ExecutionEngineError) as exc:
                # Defensive: the healed steps should always be
                # structurally valid (they're the same steps, minus one
                # replaced selector), but if the engine itself errors
                # out entirely on the second call, that is reported as
                # healing_failed rather than letting an unrelated
                # 422/502 leak from the healing attempt and mask the
                # original execution's own response.
                healing_result = build_healing_result(diagnosis, proposal, None)
                healing_result.status = HEALING_FAILED
                healing_result.applied = True
                healing_result.reason = f"The healed steps could not be executed: {exc}"
            else:
                healing_result = build_healing_result(diagnosis, proposal, healed_execution)
    else:
        healing_result = not_attempted_result()

    return ExecutionResultWithDiagnosisOut(
        status=result.status,
        steps=result.steps,
        failed_step_index=result.failed_step_index,
        failed_step_id=result.failed_step_id,
        error=result.error,
        executed_step_count=result.executed_step_count,
        started_at=result.started_at,
        finished_at=result.finished_at,
        duration_ms=result.duration_ms,
        evidence=result.evidence,
        diagnosis=DiagnosisOut.model_validate(diagnosis),
        explanation=ExplanationOut.model_validate(explanation),
        healing=HealingResultOut.model_validate(healing_result),
    )
