from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.test_definition import TestDefinition
from app.schemas.test_definition import TestDefinitionCreate, TestDefinitionRead

router = APIRouter(tags=["test-definitions"])


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


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
    test_definition = db.get(TestDefinition, test_id)
    if test_definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test definition not found")
    return test_definition
