from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.test_definition import TestDefinition
from app.schemas.execution import DiagnosisOut, ExecutionResultOut
from app.schemas.test_definition import ExecutionPayloadCreate, TestDefinitionCreate, TestDefinitionRead
from app.services.diagnosis_client import diagnose
from app.services.execution_client import (
    ExecutionEngineError,
    ExecutionValidationError,
    execute_steps,
)

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


@router.post("/tests/{test_id}/execute", response_model=ExecutionResultOut)
def execute_test_definition(test_id: str, db: Session = Depends(get_db)) -> ExecutionResultOut:
    """
    Executes an existing TestDefinition's stored steps via the Execution
    Engine (subprocess boundary — see app/services/execution_client.py).

    On a failed execution, additionally runs Intelligence's existing,
    unmodified diagnosis (app/services/diagnosis_client.py) and attaches
    it as the additive `diagnosis` field. A passing execution never
    invokes diagnosis — `diagnosis` stays None. Backend performs no
    classification itself; it only reports what the execution engine
    and Intelligence's diagnosis each independently determined.
    """
    test_definition = _get_test_definition_or_404(test_id, db)

    try:
        result = execute_steps(test_definition.content)
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExecutionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if result.status == "failed":
        diagnosis_result = diagnose(test_definition, result)
        result.diagnosis = DiagnosisOut.model_validate(diagnosis_result, from_attributes=True)

    return result
