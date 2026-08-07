from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.test_definition import TestDefinition
from app.schemas.execution import ExecutionResultOut
from app.schemas.test_definition import TestDefinitionCreate, TestDefinitionRead
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
        content=[step.model_dump() for step in payload.content],
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

    This endpoint does not diagnose or classify failures; it only reports
    what the execution engine reported. Diagnosis/healing is Claude 3's
    domain, added in a later milestone.
    """
    test_definition = _get_test_definition_or_404(test_id, db)

    try:
        return execute_steps(test_definition.content)
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExecutionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
