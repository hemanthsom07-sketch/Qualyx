from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.test_definition import TestDefinition
from app.schemas.recording import RecordingCreate
from app.schemas.test_definition import ExecutionPayloadCreate, TestDefinitionRead
from app.services.intelligence_client import (
    IntelligenceProcessingError,
    build_execution_payload_from_events,
)

router = APIRouter(tags=["recordings"])


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post(
    "/projects/{project_id}/recordings",
    response_model=TestDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recording(
    project_id: str, payload: RecordingCreate, db: Session = Depends(get_db)
) -> TestDefinition:
    """
    Ingests raw Recorder events for a journey, runs them through
    Intelligence's EXISTING, unmodified
    generate_execution_payload_from_real_recorder_events() pipeline
    (see app/services/intelligence_client.py), and stores the resulting
    execution payload as a TestDefinition.

    Deliberately reuses ExecutionPayloadCreate — the same schema/storage
    logic already used by POST /projects/{project_id}/tests/from-execution-payload
    — to validate and map Intelligence's output, so there is exactly one
    place in the Backend that turns an execution payload into stored
    TestDefinition content.

    Mapping: journeyId -> TestDefinition.name, generated steps -> content.
    """
    _get_project_or_404(project_id, db)

    events = [event.model_dump(exclude_none=True) for event in payload.events]

    try:
        execution_payload_dict = build_execution_payload_from_events(payload.journey_id, events)
    except IntelligenceProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Intelligence processing failed: {exc}",
        ) from exc

    if not execution_payload_dict.get("steps"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No steps could be generated from the supplied recording events.",
        )

    validated_payload = ExecutionPayloadCreate.model_validate(execution_payload_dict)

    test_definition = TestDefinition(
        project_id=project_id,
        name=validated_payload.journey_id,
        description=None,
        content=[step.model_dump(exclude_none=True, by_alias=True) for step in validated_payload.steps],
    )
    db.add(test_definition)
    db.commit()
    db.refresh(test_definition)
    return test_definition
